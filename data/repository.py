"""
data/repository.py — SQLite 历史记录存取层
─────────────────────────────────────────────
支持：增删改查、标签过滤、收藏、统计、年度热力图、旧版 JSON 迁移
"""
import os
import sqlite3
import time
import threading
import uuid
from datetime import datetime, timedelta

from config.settings import DB_FILE

_ID_LOCK = threading.Lock()


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_FILE, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


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
                tags        TEXT    DEFAULT '',
                is_img2img INTEGER DEFAULT 0,
                source_img  TEXT    DEFAULT ''
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_id ON history(id DESC)")
        # 升级旧库：自动补充新列
        for col_def in [
            "ALTER TABLE history ADD COLUMN nickname    TEXT    DEFAULT NULL",
            "ALTER TABLE history ADD COLUMN favorited  INTEGER DEFAULT 0",
            "ALTER TABLE history ADD COLUMN tags        TEXT    DEFAULT ''",
            "ALTER TABLE history ADD COLUMN is_img2img INTEGER DEFAULT 0",
            "ALTER TABLE history ADD COLUMN source_img  TEXT    DEFAULT ''",
        ]:
            try:
                c.execute(col_def)
            except sqlite3.OperationalError:
                pass
        c.commit()


# ─── 写入 ─────────────────────────────────────────────────────
def add_entry(prompt: str, translated: str, image_path: str,
              provider: str, is_img2img: bool = False,
              source_img: str = "") -> dict:
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 用 UUID 保证多线程下唯一性
    with _ID_LOCK:
        eid = int(time.time() * 1_000_000) + hash(uuid.uuid4().hex[:6]) % 1000
    with _conn() as c:
        c.execute(
            "INSERT INTO history"
            "(id,timestamp,prompt,translated,image_path,provider,"
            " nickname,favorited,tags,is_img2img,source_img)"
            " VALUES (?,?,?,?,?,?,NULL,0,'',?,?)",
            (eid, ts, prompt, translated, image_path, provider,
             1 if is_img2img else 0, source_img)
        )
        c.commit()
    return {"id": eid, "timestamp": ts, "prompt": prompt,
            "translated": translated, "image_path": image_path,
            "provider": provider, "nickname": None,
            "favorited": 0, "tags": "",
            "is_img2img": is_img2img, "source_img": source_img}


# ─── 读取 ─────────────────────────────────────────────────────
def get_all_entries(keyword: str = "",
                    only_favorites: bool = False,
                    tag_filter: str = "") -> list:
    clauses, params = [], []
    if only_favorites:
        clauses.append("favorited = 1")
    if keyword:
        clauses.append("(prompt LIKE ? OR nickname LIKE ?)")
        params += [f"%{keyword}%", f"%{keyword}%"]
    if tag_filter:
        clauses.append(
            "(tags = ? OR tags LIKE ? OR tags LIKE ? OR tags LIKE ?)"
        )
        params += [
            tag_filter,
            f"{tag_filter},%",
            f"%,{tag_filter},%",
            f"%,{tag_filter}",
        ]
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with _conn() as c:
        rows = c.execute(
            f"SELECT * FROM history {where} ORDER BY id DESC", params
        ).fetchall()
    return [dict(r) for r in rows]


def get_entry(entry_id: int):
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM history WHERE id=?", (entry_id,)
        ).fetchone()
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
    cleaned = ",".join(
        t.strip() for t in tags.split(",") if t.strip()
    )
    with _conn() as c:
        c.execute("UPDATE history SET tags=? WHERE id=?", (cleaned, entry_id))
        c.commit()


# ─── 统计 ─────────────────────────────────────────────────────
def get_all_tags() -> list:
    with _conn() as c:
        rows = c.execute(
            "SELECT DISTINCT tags FROM history WHERE tags IS NOT NULL AND tags != ''"
        ).fetchall()
    tag_set = set()
    for row in rows:
        for t in row[0].split(","):
            t = t.strip()
            if t:
                tag_set.add(t)
    return sorted(tag_set)


def get_stats() -> dict:
    with _conn() as c:
        total     = c.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        favorites = c.execute("SELECT COUNT(*) FROM history WHERE favorited=1").fetchone()[0]
        today_str = datetime.now().strftime("%Y-%m-%d")
        today     = c.execute(
            "SELECT COUNT(*) FROM history WHERE timestamp LIKE ?",
            (f"{today_str}%",)
        ).fetchone()[0]
        week_ago  = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        week      = c.execute(
            "SELECT COUNT(*) FROM history WHERE timestamp >= ?",
            (week_ago,)
        ).fetchone()[0]
        prov_rows = c.execute(
            "SELECT provider, COUNT(*) as cnt FROM history"
            " WHERE provider != '' GROUP BY provider ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        daily = []
        for i in range(6, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            cnt = c.execute(
                "SELECT COUNT(*) FROM history WHERE timestamp LIKE ?",
                (f"{d}%",)
            ).fetchone()[0]
            daily.append((d[5:], cnt))
        tag_rows = c.execute(
            "SELECT tags FROM history WHERE tags IS NOT NULL AND tags != ''"
        ).fetchall()
    tag_counts: dict = {}
    for row in tag_rows:
        for t in row[0].split(","):
            t = t.strip()
            if t:
                tag_counts[t] = tag_counts.get(t, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:10]
    return {
        "total":     total,
        "favorites": favorites,
        "today":     today,
        "week":      week,
        "providers": [{"provider": r[0], "cnt": r[1]} for r in prov_rows],
        "daily":     daily,
        "top_tags":  top_tags,
    }


# ─── 删除 ─────────────────────────────────────────────────────
def delete_entry(entry_id: int, remove_file: bool = True) -> None:
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
        records = json.load(open(json_path, "r", encoding="utf-8"))
        count = 0
        with _conn() as c:
            for r in records:
                try:
                    c.execute(
                        "INSERT OR IGNORE INTO history"
                        "(id,timestamp,prompt,translated,image_path,provider,"
                        " nickname,favorited,tags)"
                        " VALUES (?,?,?,?,?,?,NULL,0,'')",
                        (r.get("id", int(time.time()*1000)),
                         r.get("timestamp",""),
                         r.get("prompt",""),
                         r.get("translated",""),
                         r.get("image_path",""),
                         r.get("provider",""))
                    )
                    count += 1
                except Exception:
                    pass
            c.commit()
        os.rename(json_path, json_path + ".migrated")
        return count
    except Exception:
        return 0


# ─── 年度热力图数据 ────────────────────────────────────────────
def get_year_heatmap(year: int) -> dict:
    start = f"{year}-01-01"
    end   = f"{year}-12-31 23:59:59"
    with _conn() as c:
        rows = c.execute(
            "SELECT substr(timestamp,1,10) as day, COUNT(*) as cnt "
            "FROM history WHERE timestamp >= ? AND timestamp <= ? "
            "GROUP BY day",
            (start, end)
        ).fetchall()
    return {row[0]: row[1] for row in rows}


def get_available_years() -> list:
    current_year = datetime.now().year
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
    start = f"{year}-01-01"
    end   = f"{year}-12-31 23:59:59"
    with _conn() as c:
        total = c.execute(
            "SELECT COUNT(*) FROM history WHERE timestamp >= ? AND timestamp <= ?",
            (start, end)
        ).fetchone()[0]
        month_rows = c.execute(
            "SELECT substr(timestamp,1,7) as m, COUNT(*) as cnt "
            "FROM history WHERE timestamp >= ? AND timestamp <= ? "
            "GROUP BY m ORDER BY cnt DESC LIMIT 1",
            (start, end)
        ).fetchone()
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


# ─── 向后兼容 Facade ──────────────────────────────────────────────────────
class HistoryRepository:
    """兼容旧代码的类包装，不改变原有函数式 API。"""
    add_entry         = staticmethod(add_entry)
    delete_entry      = staticmethod(delete_entry)
    get_all_entries   = staticmethod(get_all_entries)
    get_entry         = staticmethod(get_entry)
    rename_entry      = staticmethod(rename_entry)
    toggle_favorite   = staticmethod(toggle_favorite)
    update_tags       = staticmethod(update_tags)
    get_all_tags      = staticmethod(get_all_tags)
    get_stats         = staticmethod(get_stats)
    clear_all_entries = staticmethod(clear_all_entries)
    count_entries     = staticmethod(count_entries)
    migrate_from_json = staticmethod(migrate_from_json)
    get_year_heatmap  = staticmethod(get_year_heatmap)
    get_available_years = staticmethod(get_available_years)
    get_year_stats    = staticmethod(get_year_stats)
    init_db           = staticmethod(init_db)
