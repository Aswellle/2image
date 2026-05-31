"""
data/repository.py — SQLite 历史记录存取层  v3
─────────────────────────────────────────────
v3 新增：
  tags     TEXT  — 逗号分隔的标签列表（如 "人物,写实,黄金时刻"）
  + update_tags()      — 更新单条记录的标签
  + get_all_tags()     — 获取数据库中所有唯一标签（排序）
  + get_stats()        — 统计看板数据（Provider 分布、每日趋势、标签热度）
  + get_all_entries()  — 新增 tag_filter 参数支持按标签过滤
"""
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta

from config.settings import DB_FILE

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
    sql = f"SELECT * FROM history {where} ORDER BY id DESC"
    if limit > 0:
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    with _conn() as c:
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_entry(entry_id: int):
    with _conn() as c:
        row = c.execute("SELECT * FROM history WHERE id=?", (entry_id,)).fetchone()
    return dict(row) if row else None


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
    """Set tags for an entry. tags is comma-separated string."""
    with _conn() as c:
        # Also update the legacy CSV column for backward compat
        cleaned = ",".join(sorted(set(t.strip() for t in tags.split(",") if t.strip())))
        c.execute("UPDATE history SET tags = ? WHERE id = ?", (cleaned, entry_id))

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

        # 近 7 天每日数量
        daily = []
        for i in range(6, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            cnt = c.execute(
                "SELECT COUNT(*) FROM history WHERE timestamp LIKE ?",
                (f"{d}%",)
            ).fetchone()[0]
            daily.append((d[5:], cnt))   # "MM-DD"

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
    if remove_file:
        entry = get_entry(entry_id)
        if entry:
            p = entry.get("image_path", "")
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
    with _conn() as c:
        c.execute("DELETE FROM history WHERE id=?", (entry_id,))
        c.commit()


def clear_all_entries() -> None:
    with _conn() as c:
        c.execute("DELETE FROM history"); c.commit()


def count_entries() -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM history").fetchone()[0]


# ─── 旧版 JSON 迁移 ───────────────────────────────────────────
def migrate_from_json(json_path: str) -> int:
    import json
    if not os.path.exists(json_path):
        return 0
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            records = json.load(f)
        count = 0
        with _conn() as c:
            for r in records:
                try:
                    c.execute(
                        "INSERT OR IGNORE INTO history"
                        "(id,timestamp,prompt,translated,image_path,provider,nickname,favorited,tags)"
                        " VALUES (?,?,?,?,?,?,NULL,0,'')",
                        (r.get("id", int(time.time()*1000)), r.get("timestamp",""),
                         r.get("prompt",""), r.get("translated",""),
                         r.get("image_path",""), r.get("provider",""))
                    )
                    count += 1
                except Exception: pass
            c.commit()
        os.rename(json_path, json_path + ".migrated")
        return count
    except Exception: return 0


# ─── 年度热力图数据 ────────────────────────────────────────────
def get_year_heatmap(year: int) -> dict:
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
