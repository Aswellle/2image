"""
data/repository.py — SQLite 历史记录存取层  v4
─────────────────────────────────────────────
v4 新增（Phase 1 安全重构）：
  - delete_entry() 使用 file_ownership.safe_delete_file() 防止路径穿越
  - migrate_from_json() 改为事务 + report，失败不丢旧数据
  - save_image_file() 改用 UUID 文件名防碰撞
  - 原子文件写入（tempfile + os.replace）

v3 新增：
  tags     TEXT  — 逗号分隔的标签列表
"""
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from config.settings import DB_FILE, IMAGES_DIR
from services.generation.file_ownership import safe_delete_file

# 每个线程持有独立连接，避免跨线程共享和连接泄漏
_thread_local = threading.local()


def _conn() -> sqlite3.Connection:
    if not hasattr(_thread_local, "conn"):
        conn = sqlite3.connect(DB_FILE, check_same_thread=True, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-8000")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys = ON")
        _thread_local.conn = conn
    return _thread_local.conn


# ─── 初始化 ───────────────────────────────────────────────────
def init_db() -> None:
    """建表，并对旧库自动补列（升级兼容）。"""
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id          INTEGER PRIMARY KEY,
                timestamp   TEXT    NOT NULL,
                prompt      TEXT    NOT NULL,
                translated  TEXT    DEFAULT '',
                image_path  TEXT    DEFAULT '',
                provider    TEXT    DEFAULT '',
                nickname    TEXT    DEFAULT NULL,
                favorited   INTEGER DEFAULT 0,
                tags        TEXT    DEFAULT ''
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_id ON history(id DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON history(timestamp)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_favorited ON history(favorited)")
        # 标签规范化：junction tables
        c.execute("""
            CREATE TABLE IF NOT EXISTS tag (
                id   INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS entry_tag (
                entry_id INTEGER REFERENCES history(id) ON DELETE CASCADE,
                tag_id   INTEGER REFERENCES tag(id) ON DELETE CASCADE,
                PRIMARY KEY (entry_id, tag_id)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_entry_tag_tag ON entry_tag(tag_id)")
        # 升级旧库：自动补充新列
        for col_def in [
            "ALTER TABLE history ADD COLUMN nickname  TEXT    DEFAULT NULL",
            "ALTER TABLE history ADD COLUMN favorited INTEGER DEFAULT 0",
            "ALTER TABLE history ADD COLUMN tags      TEXT    DEFAULT ''",
        ]:
            try:
                c.execute(col_def)
            except sqlite3.OperationalError:
                pass
        c.commit()
        _migrate_tags_from_csv()

def _migrate_tags_from_csv():
    """Migrate tags from CSV column to junction tables (one-time)."""
    with _conn() as c:
        # Check if migration already done
        cnt = c.execute("SELECT COUNT(*) FROM tag").fetchone()[0]
        if cnt > 0:
            return  # already migrated

        rows = c.execute("SELECT id, tags FROM history WHERE tags IS NOT NULL AND tags != ''").fetchall()
        migrated = 0
        for row in rows:
            entry_id = row["id"]
            tags_csv = row["tags"]
            for tag_name in tags_csv.split(","):
                tag_name = tag_name.strip()
                if not tag_name:
                    continue
                c.execute("INSERT OR IGNORE INTO tag (name) VALUES (?)", (tag_name,))
                tag_id = c.execute("SELECT id FROM tag WHERE name = ?", (tag_name,)).fetchone()[0]
                c.execute("INSERT OR IGNORE INTO entry_tag (entry_id, tag_id) VALUES (?, ?)",
                          (entry_id, tag_id))
                migrated += 1
        c.commit()
        return migrated

# ─── 写入 ─────────────────────────────────────────────────────
def add_entry(prompt: str, translated: str, image_path: str, provider: str) -> dict:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO history"
            "(timestamp,prompt,translated,image_path,provider,nickname,favorited,tags)"
            " VALUES (?,?,?,?,?,NULL,0,'')",
            (ts, prompt, translated, image_path, provider)
        )
        c.commit()
        eid = cur.lastrowid
    return {"id": eid, "timestamp": ts, "prompt": prompt, "translated": translated,
            "image_path": image_path, "provider": provider,
            "nickname": None, "favorited": 0, "tags": ""}


# ─── 读取 ─────────────────────────────────────────────────────
def get_all_entries(keyword: str = "",
                    only_favorites: bool = False,
                    tag_filter: str = "",
                    limit: int = 0,
                    offset: int = 0) -> list:
    clauses, params = [], []
    if only_favorites:
        clauses.append("favorited = 1")
    if keyword:
        clauses.append("(prompt LIKE ? OR nickname LIKE ?)")
        params += [f"%{keyword}%", f"%{keyword}%"]
    if tag_filter:
        clauses.append("""
            id IN (
                SELECT et.entry_id FROM entry_tag et
                JOIN tag t ON et.tag_id = t.id
                WHERE t.name = ?
            )
        """)
        params.append(tag_filter)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    # CTE computes all tag aggregations in one pass, then LEFT JOIN replaces
    # the previous per-row correlated subquery (N+1 → 1 query).
    sql = (
        "WITH tag_agg AS ("
        "  SELECT et.entry_id, GROUP_CONCAT(t.name, ',') AS tags"
        "  FROM entry_tag et JOIN tag t ON et.tag_id = t.id"
        "  GROUP BY et.entry_id"
        ") "
        "SELECT h.id, h.timestamp, h.prompt, h.translated, h.image_path, "
        "h.provider, h.nickname, h.favorited, COALESCE(ta.tags, '') AS tags "
        "FROM history h "
        f"LEFT JOIN tag_agg ta ON ta.entry_id = h.id {where} ORDER BY h.id DESC"
    )
    if limit > 0:
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    with _conn() as c:
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_entry(entry_id: int):
    with _conn() as c:
        row = c.execute("SELECT * FROM history WHERE id=?", (entry_id,)).fetchone()
        if row is None:
            return None
        entry = dict(row)
        # Derive tags from junction table; legacy history.tags column is always ""
        tags_row = c.execute(
            "SELECT GROUP_CONCAT(t.name, ',') AS tags "
            "FROM entry_tag et JOIN tag t ON et.tag_id = t.id "
            "WHERE et.entry_id = ?",
            (entry_id,)
        ).fetchone()
        entry["tags"] = (tags_row["tags"] or "") if tags_row else ""
    return entry


# ─── 更新 ─────────────────────────────────────────────────────
def rename_entry(entry_id: int, nickname: str) -> None:
    nick = nickname.strip() if nickname else None
    with _conn() as c:
        c.execute("UPDATE history SET nickname=? WHERE id=?", (nick, entry_id))
        c.commit()


def toggle_favorite(entry_id: int, favorited: bool) -> None:
    with _conn() as c:
        c.execute("UPDATE history SET favorited=? WHERE id=?",
                  (1 if favorited else 0, entry_id))
        c.commit()


def update_tags(entry_id: int, tags: str) -> None:
    """Set tags for an entry. tags is comma-separated string.
    Junction tables (tag, entry_tag) are the single source of truth.
    The legacy history.tags CSV column is no longer written.
    """
    with _conn() as c:
        cleaned = ",".join(sorted(set(t.strip() for t in tags.split(",") if t.strip())))

        # Remove old junction entries
        c.execute("DELETE FROM entry_tag WHERE entry_id = ?", (entry_id,))

        # Insert new tags
        for tag_name in cleaned.split(","):
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            c.execute("INSERT OR IGNORE INTO tag (name) VALUES (?)", (tag_name,))
            tag_id = c.execute("SELECT id FROM tag WHERE name = ?", (tag_name,)).fetchone()[0]
            c.execute("INSERT OR IGNORE INTO entry_tag (entry_id, tag_id) VALUES (?, ?)",
                      (entry_id, tag_id))
        c.commit()


# ─── 统计 ─────────────────────────────────────────────────────
def get_all_tags() -> list:
    with _conn() as c:
        rows = c.execute(
            "SELECT t.name, COUNT(et.entry_id) as cnt FROM tag t "
            "JOIN entry_tag et ON t.id = et.tag_id "
            "GROUP BY t.id ORDER BY cnt DESC"
        ).fetchall()
        return [row["name"] for row in rows]


def get_stats() -> dict:
    """
    统计看板数据，返回 dict：
      total        — 总生成数
      favorites    — 收藏数
      today        — 今日生成数
      week         — 近 7 天生成数
      providers    — list of {provider, cnt}
      daily        — list of ("MM-DD", cnt)，最近 7 天
      top_tags     — list of (tag, cnt)，最多 10 个
    """
    with _conn() as c:
        today_str = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        row = c.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN favorited=1 THEN 1 ELSE 0 END) as favorites,
                SUM(CASE WHEN timestamp >= ? THEN 1 ELSE 0 END) as week,
                SUM(CASE WHEN timestamp >= ? THEN 1 ELSE 0 END) as month,
                SUM(CASE WHEN timestamp LIKE ? THEN 1 ELSE 0 END) as today
            FROM history
        """, (week_ago, month_ago, f"{today_str}%")).fetchone()

        total = row["total"]
        favorites = row["favorites"]
        today = row["today"]
        week = row["week"]
        month = row["month"]

        # Provider 分布
        prov_rows = c.execute(
            "SELECT provider, COUNT(*) as cnt FROM history"
            " WHERE provider != ''"
            " GROUP BY provider ORDER BY cnt DESC LIMIT 10"
        ).fetchall()

        # 近 7 天每日数量（单次 GROUP BY 替代 7 个独立查询）
        week_start = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
        daily_rows = c.execute(
            "SELECT substr(timestamp, 1, 10) AS day, COUNT(*) AS cnt "
            "FROM history WHERE timestamp >= ? GROUP BY day",
            (week_start,)
        ).fetchall()
        daily_map = {r["day"]: r["cnt"] for r in daily_rows}
        daily = []
        for i in range(6, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily.append((d[5:], daily_map.get(d, 0)))   # "MM-DD"

        # Tags 热度 — use junction tables
        tag_rows = c.execute(
            "SELECT t.name, COUNT(et.entry_id) as cnt FROM tag t "
            "JOIN entry_tag et ON t.id = et.tag_id "
            "GROUP BY t.id ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        top_tags = [(r["name"], r["cnt"]) for r in tag_rows]

    return {
        "total":     total,
        "favorites": favorites,
        "today":     today,
        "week":      week,
        "month":     month,
        "providers": [{"provider": r[0], "cnt": r[1]} for r in prov_rows],
        "daily":     daily,
        "top_tags":  top_tags,
    }


# ─── 删除 ─────────────────────────────────────────────────────
def delete_entry(entry_id: int, remove_file: bool = True) -> None:
    """删除记录，remove_file=True 时同步删除磁盘图片。"""
    entry = get_entry(entry_id)
    if entry:
        p = entry.get("image_path", "")
        if p:
            try:
                safe_delete_file(p)
            except (ValueError, FileNotFoundError, OSError) as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "Failed to delete image for entry %s: %s", entry_id, exc
                )

    with _conn() as c:
        c.execute("DELETE FROM history WHERE id=?", (entry_id,))
        c.commit()



def clear_all_entries(remove_files: bool = False) -> dict:
    """
    Clear history records.

    Args:
        remove_files: If True, also delete associated image files.

    Returns:
        Summary dict with counts of records and files processed.
    """
    result = {"records": 0, "files_removed": 0, "files_failed": 0}

    if remove_files:
        # Collect all image paths before deleting records
        entries = []
        with _conn() as c:
            rows = c.execute(
                "SELECT id, image_path FROM history WHERE image_path != ''"
            ).fetchall()
            entries = [dict(r) for r in rows]

    with _conn() as c:
        count = c.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        c.execute("DELETE FROM history")
        c.commit()
        result["records"] = count

    if remove_files:
        for entry in entries:
            try:
                if safe_delete_file(entry["image_path"]):
                    result["files_removed"] += 1
            except (ValueError, OSError):
                result["files_failed"] += 1

    return result


def count_entries() -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM history").fetchone()[0]


def migrate_from_json(json_path: str) -> dict:
    """
    Migrate records from old JSON format to SQLite.

    Uses a transaction: if any critical error occurs, rolls back.
    Partial failures are recorded but don't lose the original file.

    Returns:
        dict with counts: {"migrated": N, "failed": N, "total": N}
    """
    import json
    import logging

    logger = logging.getLogger(__name__)
    result = {"migrated": 0, "failed": 0, "total": 0}

    if not os.path.exists(json_path):
        return result

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            records = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to read JSON migration source: %s", exc)
        return result

    if not isinstance(records, list):
        logger.error("JSON migration source is not a list")
        return result

    result["total"] = len(records)
    migration_errors: list[str] = []

    try:
        with _conn() as c:
            for r in records:
                try:
                    c.execute(
                        "INSERT OR IGNORE INTO history"
                        "(id, timestamp, prompt, translated, image_path,"
                        " provider, nickname, favorited, tags)"
                        " VALUES (?,?,?,?,?,?,NULL,0,'')",
                        (
                            r.get("id", int(time.time() * 1000)),
                            r.get("timestamp", ""),
                            r.get("prompt", ""),
                            r.get("translated", ""),
                            r.get("image_path", ""),
                            r.get("provider", ""),
                        ),
                    )
                    result["migrated"] += 1
                except Exception as exc:
                    result["failed"] += 1
                    migration_errors.append(str(exc))

            c.commit()

        # Only rename the original file if ALL records migrated successfully
        if result["failed"] == 0:
            os.rename(json_path, json_path + ".migrated")
            logger.info(
                "Migration complete: %d/%d records. Original renamed.",
                result["migrated"], result["total"],
            )
        else:
            logger.warning(
                "Migration partial: %d/%d records, %d failed. "
                "Original NOT renamed to preserve data.",
                result["migrated"], result["total"], result["failed"],
            )
    except Exception as exc:
        logger.error("Migration transaction failed: %s", exc)
        result["failed"] = result["total"] - result["migrated"]

    return result
    """
    返回指定年全年每天的生成数量。

    Returns
    -------
    dict  { "YYYY-MM-DD": count }
    仅包含 count > 0 的日期；不在该年的日期不包含。
    """
    start = f"{year}-01-01"
    end   = f"{year}-12-31 23:59:59"
    with _conn() as c:
        rows = c.execute(
            "SELECT substr(timestamp,1,10) as day, COUNT(*) as cnt "
            "FROM history "
            "WHERE timestamp >= ? AND timestamp <= ? "
            "GROUP BY day",
            (start, end)
        ).fetchall()
    return {row[0]: row[1] for row in rows}


def get_available_years() -> list:
    """
    返回数据库中存在生成记录的所有年份列表（降序）。
    至少包含当前年份。
    """
    from datetime import datetime as _dt
    current_year = _dt.now().year
    with _conn() as c:
        rows = c.execute(
            "SELECT DISTINCT substr(timestamp,1,4) as yr "
            "FROM history WHERE yr != '' ORDER BY yr DESC"
        ).fetchall()
    years = [int(r[0]) for r in rows if r[0].isdigit()]
    if current_year not in years:
        years.insert(0, current_year)
    return sorted(set(years), reverse=True)


def get_year_stats(year: int) -> dict:
    """返回指定年的汇总统计（总数 / 最活跃月份 / 最活跃单日）。"""
    start = f"{year}-01-01"
    end   = f"{year}-12-31 23:59:59"
    with _conn() as c:
        total = c.execute(
            "SELECT COUNT(*) FROM history WHERE timestamp >= ? AND timestamp <= ?",
            (start, end)
        ).fetchone()[0]
        # 最活跃月
        month_rows = c.execute(
            "SELECT substr(timestamp,1,7) as m, COUNT(*) as cnt "
            "FROM history WHERE timestamp >= ? AND timestamp <= ? "
            "GROUP BY m ORDER BY cnt DESC LIMIT 1",
            (start, end)
        ).fetchone()
        # 最活跃单日
        day_rows = c.execute(
            "SELECT substr(timestamp,1,10) as d, COUNT(*) as cnt "
            "FROM history WHERE timestamp >= ? AND timestamp <= ? "
            "GROUP BY d ORDER BY cnt DESC LIMIT 1",
            (start, end)
        ).fetchone()
    return {
        "year":       year,
        "total":      total,
        "best_month": dict(month_rows) if month_rows else None,
        "best_day":   dict(day_rows)   if day_rows   else None,
    }

# ─── 测试辅助 ─────────────────────────────────────────────────
_test_db_path: str = None

def _set_test_db(path: str = ":memory:") -> None:
    """切换到测试数据库（仅用于单元测试）。
    调用后需重置 _thread_local 连接。
    """
    global DB_FILE, _test_db_path
    import threading
    _test_db_path = path
    DB_FILE = path
    # 重置所有线程的数据库连接
    if hasattr(_thread_local, "conn"):
        try:
            _thread_local.conn.close()
        except Exception:
            pass
        del _thread_local.conn
