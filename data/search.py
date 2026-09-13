"""
data/search.py — Full-text search with SQLite FTS5
──────────────────────────────────────────────────
Provides fast history search without full table scans.
Uses a simpler manual sync approach for reliability.
"""

import logging
import threading


logger = logging.getLogger(__name__)
_FTS_LOCK = threading.Lock()


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
    """Create FTS5 virtual table if it doesn't exist."""
    global _FTS_READY
    with _FTS_LOCK:
        if _fts_table_exists(conn):
            _FTS_READY = True
            return
        try:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS history_fts USING fts5(
                    prompt,
                    translated,
                    provider,
                    tags
                )
            """)
            _FTS_READY = True
        except Exception as exc:
            logger.warning("FTS5 setup failed: %s", exc)



def sync_fts(conn) -> None:
    """Manually sync FTS index with history table."""
    global _FTS_READY
    if not _FTS_READY:
        return
    try:
        conn.execute("DELETE FROM history_fts")
        conn.execute("""
            INSERT INTO history_fts(rowid, prompt, translated, provider, tags)
            SELECT id, COALESCE(prompt,''), COALESCE(translated,''),
                   COALESCE(provider,''), COALESCE(tags,'')
            FROM history
        """)
        conn.commit()
    except Exception as exc:
        logger.warning("FTS5 sync failed: %s", exc)


def search_entries(keyword: str, limit: int = 50) -> list[int]:
    """Search entries by keyword. Returns list of matching entry IDs."""
    from data.repository import _conn
    conn = _conn()
    if not keyword or not keyword.strip():
        return []

    # Try FTS5 first
    global _FTS_READY
    if _FTS_READY:
        try:
            # Sync before search to ensure fresh results
            sync_fts(conn)
            rows = conn.execute(
                "SELECT rowid FROM history_fts WHERE history_fts MATCH ? ORDER BY rank LIMIT ?",
                (keyword, limit)
            ).fetchall()
            if rows:
                return [r[0] for r in rows]
        except Exception:
            pass

    # Fallback to LIKE
    try:
        rows = conn.execute(
            "SELECT id FROM history WHERE prompt LIKE ? OR translated LIKE ? OR provider LIKE ? LIMIT ?",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit)
        ).fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []
