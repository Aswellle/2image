"""
data/search.py — Full-text search with SQLite FTS5
──────────────────────────────────────────────────
DATA-003 改造：
  - FTS 索引由 AFTER INSERT/DELETE/UPDATE 触发器增量维护，
    不再在每次搜索前全量重建（旧实现每次搜索 O(N) 重建，比 LIKE 还慢）。
  - setup 时检测索引与主表行数不一致才做一次回填（升级旧库）。
  - 提供fts_ids() 供 repository 拉丁字母关键词走 FTS 前缀查询；
    CJK 关键词仍走 LIKE（unicode61 分词器不切中文，FTS 会漏配）。
"""

import logging
import re
import threading


logger = logging.getLogger(__name__)
_FTS_LOCK = threading.Lock()
_FTS_READY = False

# FTS 查询专用：判断关键词是否纯拉丁（可安全走 FTS 前缀查询）
_LATIN_RE = re.compile(r"^[\x20-\x7e]+$")


def _fts_table_exists(conn) -> bool:
    """Check if FTS5 virtual table exists."""
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='history_fts'"
        ).fetchone()
        return row is not None
    except Exception:
        return False


def setup_fts5(conn) -> None:
    """Create FTS5 virtual table + sync triggers; backfill once if stale."""
    global _FTS_READY
    with _FTS_LOCK:
        try:
            if _fts_table_exists(conn):
                # 旧版表含 tags 列且从未随 INSERT 维护（不可信），
                # 丢弃重建为 3 列新架构，由触发器接管。
                cols = [r[1] for r in conn.execute(
                    "PRAGMA table_info(history_fts)").fetchall()]
                if "tags" in cols:
                    conn.execute("DROP TABLE history_fts")
            if not _fts_table_exists(conn):
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS history_fts USING fts5(
                        prompt,
                        translated,
                        provider
                    )
                """)
            _FTS_READY = True
        except Exception as exc:
            logger.warning("FTS5 setup failed: %s", exc)
            return

        _create_triggers(conn)
        _backfill_if_stale(conn)


def _create_triggers(conn) -> None:
    """Incremental index maintenance — replaces per-search full rebuild.

    用普通 DELETE FROM history_fts WHERE rowid=old.id 维护删除/更新，
    而非 FTS5 特殊 'delete' 命令 —— 后者要求值与索引完全一致，脆弱。
    """
    stmts = [
        """CREATE TRIGGER IF NOT EXISTS history_fts_ins
           AFTER INSERT ON history BEGIN
               INSERT INTO history_fts(rowid, prompt, translated, provider)
               VALUES (new.id, COALESCE(new.prompt,''),
                       COALESCE(new.translated,''), COALESCE(new.provider,''));
           END""",
        """CREATE TRIGGER IF NOT EXISTS history_fts_del
           AFTER DELETE ON history BEGIN
               DELETE FROM history_fts WHERE rowid = old.id;
           END""",
        """CREATE TRIGGER IF NOT EXISTS history_fts_upd
           AFTER UPDATE OF prompt, translated, provider ON history BEGIN
               DELETE FROM history_fts WHERE rowid = old.id;
               INSERT INTO history_fts(rowid, prompt, translated, provider)
               VALUES (new.id, COALESCE(new.prompt,''),
                       COALESCE(new.translated,''), COALESCE(new.provider,''));
           END""",
    ]
    for sql in stmts:
        try:
            conn.execute(sql)
        except Exception as exc:
            logger.warning("FTS trigger setup failed: %s", exc)


def _backfill_if_stale(conn) -> None:
    """One-time rebuild when index row count diverges from history (old DB)."""
    try:
        hist = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        fts = conn.execute("SELECT COUNT(*) FROM history_fts").fetchone()[0]
        if hist != fts:
            sync_fts(conn)
    except Exception as exc:
        logger.warning("FTS backfill check failed: %s", exc)


def sync_fts(conn) -> None:
    """Full rebuild of the FTS index (setup-time backfill only)."""
    global _FTS_READY
    if not _FTS_READY:
        return
    try:
        conn.execute("DELETE FROM history_fts")
        conn.execute("""
            INSERT INTO history_fts(rowid, prompt, translated, provider)
            SELECT id, COALESCE(prompt,''), COALESCE(translated,''),
                   COALESCE(provider,'')
            FROM history
        """)
        conn.commit()
    except Exception as exc:
        logger.warning("FTS sync failed: %s", exc)


def fts_query_expr(keyword: str) -> str | None:
    """Build a safe FTS5 MATCH expression for a latin keyword.

    Returns None for CJK/empty keywords (unicode61 can't segment CJK —
    caller should fall back to LIKE).  Each whitespace-separated token
    becomes a quoted prefix query joined with OR.
    """
    if not keyword or not _LATIN_RE.match(keyword):
        return None
    tokens = [t for t in keyword.split() if t]
    if not tokens:
        return None
    return " OR ".join('"' + t.replace('"', '""') + '"*' for t in tokens)


def fts_ids(conn, keyword: str, limit: int = 500) -> list[int] | None:
    """Search via FTS5 prefix query. Returns entry ids, [] for no match,
    or None when FTS is unavailable / keyword unsuitable (caller → LIKE)."""
    global _FTS_READY
    expr = fts_query_expr(keyword)
    if not _FTS_READY or expr is None:
        return None
    try:
        rows = conn.execute(
            "SELECT rowid FROM history_fts WHERE history_fts MATCH ? "
            "ORDER BY rank LIMIT ?",
            (expr, limit)
        ).fetchall()
        return [r[0] for r in rows]
    except Exception as exc:
        logger.debug("FTS query failed (%s) — falling back to LIKE", exc)
        return None


def search_entries(keyword: str, limit: int = 50) -> list[int]:
    """Search entries by keyword. Returns list of matching entry IDs."""
    from data.repository import _conn
    conn = _conn()
    if not keyword or not keyword.strip():
        return []

    ids = fts_ids(conn, keyword, limit)
    if ids is not None:
        return ids

    # LIKE fallback (CJK keywords, FTS unavailable)
    try:
        rows = conn.execute(
            "SELECT id FROM history WHERE prompt LIKE ? OR translated LIKE ? OR provider LIKE ? LIMIT ?",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit)
        ).fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []
