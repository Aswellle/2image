"""
services/stats_export.py — 统计数据导出
────────────────────────────────────────
统计看板的两种导出物：

  · build_stats_csv(path)    多分区 CSV（utf-8-sig，Excel 直接打开）
  · render_share_image(path) 分享图 PNG（深色卡片，汇总+趋势+分布）

两个函数都是纯读端：只消费 repository / budget 的现成数据，
不触碰任何磁盘状态；字体加载失败时逐级回退到 load_default。
"""

from __future__ import annotations

import csv
import os
from datetime import datetime

from config.i18n import _

_IMG_W, _IMG_H = 1280, 900
_MARGIN = 48


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# ── CSV ──────────────────────────────────────────────────────────
def build_stats_csv(path: str) -> int:
    """导出统计看板数据为多分区 CSV，返回写入的数据行数（不含表头标题行）。

    utf-8-sig 带 BOM，Excel 打开中文不乱码；分区之间空行分隔。
    """
    from data.repository import get_generation_streak, get_stats
    from services.generation.budget import estimate_history_cost
    from services.generation.provider_manifest import ALL_MANIFESTS

    stats = get_stats()
    est = estimate_history_cost()

    rows = 0
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow([_("stats_export_brand_line", date=_today_str())])

        # ── 汇总 ──
        w.writerow([_("stats_export_sec_summary")])
        w.writerow([_("stats_export_metric"), _("stats_export_value")])
        for label, val in [
            (_("stats_total_images"), stats["total"]),
            (_("stats_favorites"), stats["favorites"]),
            (_("stats_fav_rate"), f"{round(stats['favorites'] / max(stats['total'], 1) * 100)}%"),
            (_("stats_today"), stats["today"]),
            (_("stats_last_7d"), stats["week"]),
            (_("stats_last_30d"), stats.get("month", 0)),
            (_("stats_export_streak"), get_generation_streak()),
        ]:
            w.writerow([label, val])
            rows += 1

        # ── 近 7 天 ──
        w.writerow([])
        w.writerow([_("stats_daily_title")])
        w.writerow([_("stats_export_day"), _("stats_export_images")])
        for day, cnt in stats["daily"]:
            w.writerow([day, cnt])
            rows += 1

        # ── 接口使用分布 ──
        w.writerow([])
        w.writerow([_("stats_provider_dist")])
        w.writerow([_("stats_export_provider"), _("stats_export_count")])
        for p in stats["providers"]:
            w.writerow([p["provider"], p["cnt"]])
            rows += 1

        # ── 成本估算 ──
        w.writerow([])
        w.writerow([_("stats_cost_title"), _("stats_cost_note")])
        w.writerow([_("stats_export_provider"), _("stats_export_images"), _("stats_export_usd")])
        for pid, info in sorted(est["by_provider"].items(), key=lambda kv: -kv[1]["usd"]):
            m = ALL_MANIFESTS.get(pid)
            w.writerow([m.name if m else pid, info["count"], info["usd"]])
            rows += 1
        w.writerow([_("stats_cost_total_num"), est["paid_count"], est["total"]])

        # ── 标签热度 ──
        w.writerow([])
        w.writerow([_("stats_top_tags")])
        w.writerow([_("stats_export_tag"), _("stats_export_count")])
        for tag, cnt in stats["top_tags"]:
            w.writerow([tag, cnt])
            rows += 1
    return rows


# ── 分享图 ───────────────────────────────────────────────────────
def _load_font(size: int, bold: bool = False, mono: bool = False):
    """PIL 字体：中文取系统微软雅黑（加粗取雅黑 Bold），数字取打包 JetBrains Mono。

    Windows-only 应用；任一字体缺失逐级回退，绝不因字体让导出崩掉。
    """
    from PIL import ImageFont
    from config.fonts import _bundled_font_path

    if mono:
        p = _bundled_font_path("JetBrainsMono-Regular.ttf")
        if p:
            return ImageFont.truetype(p, size)
    candidates = []
    if bold:
        candidates.append("C:/Windows/Fonts/msyhbd.ttc")
    candidates.append("C:/Windows/Fonts/msyh.ttc")
    for p in candidates:
        if os.path.isfile(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _fmt_usd(v: float) -> str:
    return f"${v:.2f}"


def render_share_image(path: str) -> str:
    """渲染统计分享卡片 PNG（1280×900 深色主题），返回图片路径。

    内容：标题栏 + 6 格汇总 + 近 7 天柱状图 + 接口/标签 Top-3 + 成本脚注。
    """
    from PIL import Image, ImageDraw
    from config.theme import DARK_THEME as C
    from data.repository import get_generation_streak, get_stats
    from services.generation.budget import estimate_history_cost

    stats = get_stats()
    est = estimate_history_cost()
    streak = get_generation_streak()

    bg, panel, card = C["bg"], C["panel"], C["card"]
    sep, txt, sub, ok, warn = C["sep"], C["text"], C["text_muted"], C["ok"], C["warn"]
    purple, purple_soft = C["purple"], C["purple_soft"]

    img = Image.new("RGB", (_IMG_W, _IMG_H), bg)
    d = ImageDraw.Draw(img)

    f_brand = _load_font(22, mono=True)
    f_title = _load_font(42, bold=True)
    f_small = _load_font(17)
    f_small_b = _load_font(17, bold=True)
    f_val = _load_font(38, mono=True)
    f_lbl = _load_font(16)
    f_sec = _load_font(22, bold=True)

    def _text_w(draw, text, font) -> int:
        try:
            return draw.textbbox((0, 0), text, font=font)[2]
        except Exception:
            return len(text) * 10

    # ── 标题栏 ──
    d.text((_MARGIN, 44), "2image", font=f_brand, fill=ok)
    d.text((_MARGIN, 74), _("stats_export_share_title"), font=f_title, fill=txt)
    d.text(
        (_IMG_W - _MARGIN - _text_w(d, _today_str(), f_small), 58),
        _today_str(),
        font=f_small,
        fill=sub,
    )
    d.line([(_MARGIN, 138), (_IMG_W - _MARGIN, 138)], fill=sep, width=1)

    # ── 汇总 3×2 ──
    fav_rate = f"{round(stats['favorites'] / max(stats['total'], 1) * 100)}%"
    tiles = [
        (str(stats["total"]), _("stats_total_images")),
        (str(stats["favorites"]), _("stats_favorites")),
        (fav_rate, _("stats_fav_rate")),
        (str(stats["today"]), _("stats_today")),
        (str(stats["week"]), _("stats_last_7d")),
        (str(stats.get("month", 0)), _("stats_last_30d")),
    ]
    tw, th, gap = 373, 118, 16
    for i, (val, lbl) in enumerate(tiles):
        cx = _MARGIN + (i % 3) * (tw + gap)
        cy = 162 + (i // 3) * (th + gap)
        d.rounded_rectangle([cx, cy, cx + tw, cy + th], radius=10, fill=card, outline=sep, width=1)
        vx = cx + (tw - _text_w(d, val, f_val)) // 2
        d.text((vx, cy + 24), val, font=f_val, fill="white")
        lx = cx + (tw - _text_w(d, lbl, f_lbl)) // 2
        d.text((lx, cy + 76), lbl, font=f_lbl, fill=sub)

    # ── 左下：近 7 天柱状图 ──
    panel_l = (_MARGIN, 448, _MARGIN + 560, 812)
    d.rounded_rectangle(panel_l, radius=10, fill=panel, outline=sep, width=1)
    d.text((_MARGIN + 20, 466), _("stats_daily_title"), font=f_sec, fill=txt)
    if streak >= 2:
        streak_txt = _("stats_streak", n=streak)
        d.text(
            (_MARGIN + 20 + _text_w(d, _("stats_daily_title"), f_sec) + 14, 472),
            streak_txt,
            font=f_small,
            fill=purple_soft,
        )
    daily = stats["daily"] or []
    base_y = 770
    area = 200
    max_c = max((c for _, c in daily), default=0) or 1
    bar_w, bar_gap = 46, 22
    x0 = _MARGIN + 34
    for i, (day, cnt) in enumerate(daily):
        bx = x0 + i * (bar_w + bar_gap)
        if cnt:
            bh = max(6, int(area * cnt / max_c))
            fill = purple if i == len(daily) - 1 else ok
            d.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=fill)
            cnt_t = str(cnt)
            d.text(
                (bx + (bar_w - _text_w(d, cnt_t, f_small_b)) // 2, base_y - bh - 22), cnt_t, font=f_small_b, fill=txt
            )
        else:
            d.rectangle([bx, base_y - 3, bx + bar_w, base_y], fill=sep)
        d.text((bx + (bar_w - _text_w(d, day, f_lbl)) // 2, base_y + 10), day, font=f_lbl, fill=sub)

    # ── 右下：接口 Top-3 ──
    panel_r_x0 = _MARGIN + 560 + 16
    panel_r = (panel_r_x0, 448, _IMG_W - _MARGIN, 812)
    d.rounded_rectangle(panel_r, radius=10, fill=panel, outline=sep, width=1)
    d.text((panel_r_x0 + 20, 466), _("stats_provider_dist"), font=f_sec, fill=txt)
    provs = stats["providers"][:3]
    max_p = max((p["cnt"] for p in provs), default=0) or 1
    py = 512
    bar_area = panel_r[2] - panel_r_x0 - 40 - _text_w(d, "999", f_small_b) - 24
    for p in provs:
        name = p["provider"].split("/")[0]  # 卡片只留品牌段，防长模型名溢出
        d.text((panel_r_x0 + 20, py), name, font=f_small_b, fill=txt)
        bw = int(bar_area * p["cnt"] / max_p)
        d.rounded_rectangle([panel_r_x0 + 20, py + 30, panel_r_x0 + 20 + max(bw, 6), py + 52], radius=4, fill=ok)
        cnt_t = str(p["cnt"])
        d.text((panel_r[2] - 20 - _text_w(d, cnt_t, f_small_b), py + 32), cnt_t, font=f_small_b, fill=sub)
        py += 92

    # ── 脚注：成本估算 + 标签 ──
    foot_y = 838
    if est["by_provider"]:
        cost_line = _("stats_export_foot_cost", usd=_fmt_usd(est["total"]))
        d.text((_MARGIN, foot_y), cost_line, font=f_small, fill=warn)
    tags_txt = "  ".join(f"#{t}" for t, _ in stats["top_tags"][:5])
    if tags_txt:
        d.text((_IMG_W - _MARGIN - _text_w(d, tags_txt, f_small), foot_y), tags_txt, font=f_small, fill=purple_soft)
    credit = _("stats_export_foot_credit")
    d.text(((_IMG_W - _text_w(d, credit, f_lbl)) // 2, _IMG_H - 34), credit, font=f_lbl, fill=sub)

    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    img.save(path, "PNG")
    return path
