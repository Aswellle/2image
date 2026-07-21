"""
ui/stats_dashboard.py — 统计仪表板
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime, date as _date, timedelta as _td
import math as _math

from config.fonts import F
from config.theme import C, TAG_PALETTE, tag_color
from config.i18n import _
from data.repository import get_stats, get_year_heatmap, get_available_years, get_year_stats


class StatsDashboard:
    """统计仪表板 Toplevel 窗口。"""

    def __init__(self, parent: tk.Tk, app):
        self.app = app

        # ── 颜色常量 ────────────────────────────────────────────
        BG       = "#111827"
        PANEL    = "#1a2540"
        BORDER   = "#1e3a5a"
        TXT      = "#e2e8f0"
        SUB      = "#94a3b8"
        OK       = "#4ecca3"
        WARN     = "#f0a500"
        HL       = "#e94560"
        ACC      = "#1d4ed8"

        # 热力图 5+1 级颜色（深色主题青绿渐变）
        # Level 0 = #2d4270：比面板背景 #1a2540 明显亮的蓝色，
        # 对比度 1.54x，零值格子清晰可辨，配合细边框形成网格感
        HEAT = ["#2d4270", "#0e3d2e", "#0a6647", "#0ea86e", "#4ecca3", "#a7f3d0"]

        CN_MONTHS = ["1月","2月","3月","4月","5月","6月",
                     "7月","8月","9月","10月","11月","12月"]
        CN_WEEKS  = ["一","二","三","四","五","六","日"]  # Mon=0…Sun=6

        def _heat_level(cnt: int) -> int:
            if cnt == 0: return 0
            if cnt == 1: return 1
            if cnt <= 3: return 2
            if cnt <= 6: return 3
            if cnt <= 9: return 4
            return 5

        # ── 窗口 ────────────────────────────────────────────────
        win = tk.Toplevel(parent)
        win.title("📊 生成统计看板")
        win.configure(bg=BG)
        win.resizable(True, True)
        win.minsize(1000, 660)
        win.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width()  - 1100) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 760)  // 2
        win.geometry(f"1100x760+{max(0,x)}+{max(0,y)}")

        # ── 顶部标题栏 ──────────────────────────────────────────
        hdr = tk.Frame(win, bg="#0f1e38", height=52)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="📊  生成统计看板",
                 font=F["disp"], bg="#0f1e38", fg=TXT,
                 padx=20).pack(side="left", pady=12)
        refresh_btn = tk.Button(
            hdr, text="🔄 刷新数据",
            font=F["body_b"],
            bg=HL, fg="white", bd=0, padx=14, pady=4,
            cursor="hand2", relief="flat",
            command=lambda: (win.destroy(), self.app._show_stats()))
        refresh_btn.pack(side="right", padx=16, pady=10)
        # 刷新时间
        now_str = datetime.now().strftime("%H:%M:%S")
        tk.Label(hdr, text=f"更新于 {now_str}",
                 font=F["small"], bg="#0f1e38", fg=SUB
                 ).pack(side="right", padx=4, pady=10)

        tk.Frame(win, bg=BORDER, height=1).pack(fill="x")

        # ── 双栏主布局（左：主内容  右：年份选择）──────────────
        body = tk.Frame(win, bg=BG); body.pack(fill="both", expand=True)

        # 右侧年份面板（固定宽 86px）
        right_rail = tk.Frame(body, bg="#0d1626", width=86)
        right_rail.pack(side="right", fill="y")
        right_rail.pack_propagate(False)
        tk.Frame(body, bg=BORDER, width=1).pack(side="right", fill="y")

        # 左：可滚动内容
        left = tk.Frame(body, bg=BG); left.pack(side="left", fill="both", expand=True)
        scroll_fo = tk.Frame(left, bg=BG); scroll_fo.pack(fill="both", expand=True)
        main_cv  = tk.Canvas(scroll_fo, bg=BG, bd=0, highlightthickness=0)
        vsb = ttk.Scrollbar(scroll_fo, orient="vertical", command=main_cv.yview)
        main_cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        main_cv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(main_cv, bg=BG)
        _cwin = main_cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: main_cv.configure(
            scrollregion=main_cv.bbox("all")))
        main_cv.bind("<Configure>", lambda e: main_cv.itemconfig(_cwin, width=e.width))

        def _scroll(ev):
            try: main_cv.yview_scroll(int(-1 * (ev.delta / 120)), "units")
            except tk.TclError: pass
        def _scroll_lin(ev):
            try: main_cv.yview_scroll(-1 if ev.num == 4 else 1, "units")
            except tk.TclError: pass
        win.bind_all("<MouseWheel>", _scroll)
        win.bind_all("<Button-4>",   _scroll_lin)
        win.bind_all("<Button-5>",   _scroll_lin)
        win.protocol("WM_DELETE_WINDOW", lambda: (
            win.unbind_all("<MouseWheel>"),
            win.unbind_all("<Button-4>"),
            win.unbind_all("<Button-5>"),
            win.destroy()))

        PX = 24  # 水平内边距

        # ── 辅助：分区标题 ──────────────────────────────────────
        def _sec_title(icon: str, text: str, sub: str = ""):
            fr = tk.Frame(inner, bg="#182032",
                          highlightbackground=BORDER, highlightthickness=1)
            fr.pack(fill="x", padx=PX, pady=(20, 0))
            row = tk.Frame(fr, bg="#182032"); row.pack(fill="x", padx=14, pady=8)
            tk.Label(row, text=f"{icon}  {text}",
                     font=F["h2"],
                     bg="#182032", fg=TXT).pack(side="left")
            if sub:
                tk.Label(row, text=sub,
                         font=F["small_i"],
                         bg="#182032", fg=SUB).pack(side="left", padx=10)

        # ════════════════════════════════════════════════════════
        #   ① 汇总数字卡片
        # ════════════════════════════════════════════════════════
        stats = get_stats()

        cards_f = tk.Frame(inner, bg=BG)
        cards_f.pack(fill="x", padx=PX, pady=(20, 0))
        for i in range(5): cards_f.columnconfigure(i, weight=1)

        card_data = [
            ("🖼",  "总生成图片",  stats["total"],        "#0c2f5c", "#93c5fd"),
            ("⭐",  "已收藏",      stats["favorites"],    "#3b0764", "#c4b5fd"),
            ("☀",  "今日生成",    stats["today"],        "#052e16", "#6ee7b7"),
            ("📅",  "近 7 天",     stats["week"],         "#451a03", "#fcd34d"),
            ("📆",  "近 30 天",    stats.get("month", 0), "#1e1b4b", "#a5b4fc"),
        ]
        for col, (icon, label, value, bg_c, txt_c) in enumerate(card_data):
            cell = tk.Frame(cards_f, bg=bg_c,
                            highlightbackground=BORDER,
                            highlightthickness=1)
            cell.grid(row=0, column=col, padx=5, pady=4, sticky="nsew")
            tk.Label(cell, text=icon,
                     font=F["disp_lg"], bg=bg_c, fg=txt_c
                     ).pack(pady=(12, 2))
            tk.Label(cell, text=str(value),
                     font=F["display_b"], bg=bg_c, fg="white"
                     ).pack(pady=0)
            tk.Label(cell, text=label,
                     font=F["body"], bg=bg_c, fg=txt_c
                     ).pack(pady=(2, 12))

        # ════════════════════════════════════════════════════════
        #   ② GitHub 风格全年热力图
        # ════════════════════════════════════════════════════════
        _sec_title("🔥", "全年生成热力图", "悬浮格子查看当日详情")

        # 热力图外框容器
        hmap_outer = tk.Frame(inner, bg=PANEL,
                              highlightbackground=BORDER, highlightthickness=1)
        hmap_outer.pack(fill="x", padx=PX, pady=(8, 0))

        # 年份信息栏（热力图顶部）
        hmap_info = tk.Frame(hmap_outer, bg=PANEL)
        hmap_info.pack(fill="x", padx=16, pady=(10, 4))
        self._hmap_year_lbl = tk.Label(
            hmap_info, text="",
            font=F["btn"], bg=PANEL, fg=TXT)
        self._hmap_year_lbl.pack(side="left")
        self._hmap_stat_lbl = tk.Label(
            hmap_info, text="",
            font=F["small"], bg=PANEL, fg=SUB)
        self._hmap_stat_lbl.pack(side="left", padx=12)

        # Canvas 外层（加一层 Frame 让 canvas 自适应宽度）
        hmap_cv_host = tk.Frame(hmap_outer, bg=PANEL)
        hmap_cv_host.pack(fill="x", padx=10, pady=(0, 4))

        # 热力图尺寸常量
        CELL_S   = 12    # 格子尺寸
        GAP_S    = 3     # 间距
        STEP_S   = CELL_S + GAP_S   # 15px per cell
        WLABEL_W = 32    # 左侧星期标签宽度
        TOP_M    = 24    # 顶部月份标签高度
        BOT_M    = 28    # 底部图例高度
        # 53 周 × 15 + 32 + 20 右边距
        HMAP_W   = WLABEL_W + 53 * STEP_S + 20
        HMAP_H   = TOP_M + 7 * STEP_S + GAP_S + BOT_M

        hmap_cv = tk.Canvas(
            hmap_cv_host,
            bg=PANEL, bd=0, highlightthickness=0,
            width=HMAP_W, height=HMAP_H)
        hmap_cv.pack(anchor="w", pady=(2, 6))

        # 悬浮提示框（单例，复用）
        tip_win  = [None]
        tip_lbl  = [None]
        tip_after = [None]

        def _show_tip(x_root, y_root, text):
            _hide_tip()
            tw = tk.Toplevel(win)
            tw.overrideredirect(True)
            tw.attributes("-topmost", True)
            tw.configure(bg="#0f172a")
            fr = tk.Frame(tw, bg="#7c3aed", highlightthickness=1)
            fr.pack(fill="both", expand=True)
            tk.Label(fr, text=text,
                     font=F["small"],
                     bg="#0d1626", fg=TXT,
                     padx=10, pady=5
                     ).pack()
            tw.update_idletasks()
            tw.geometry(f"+{x_root+14}+{y_root+14}")
            tip_win[0] = tw

        def _hide_tip(_=None):
            if tip_after[0]:
                try: win.after_cancel(tip_after[0])
                except Exception: pass
                tip_after[0] = None
            if tip_win[0]:
                try: tip_win[0].destroy()
                except Exception: pass
                tip_win[0] = None

        # ── 绘制热力图 ──────────────────────────────────────────
        def _draw_heatmap(year: int):
            hmap_cv.delete("all")
            _hide_tip()

            heatmap_data = get_year_heatmap(year)
            ystats       = get_year_stats(year)
            total_year   = ystats["total"]

            # 更新年份标签
            self._hmap_year_lbl.config(text=f"{year} 年  全年生成 {total_year} 张")
            bm = ystats.get("best_month")
            bd = ystats.get("best_day")
            stat_parts = []
            if bm:
                m_num = int(bm["m"][5:7])
                stat_parts.append(f"最活跃月份: {m_num}月 ({bm['cnt']}张)")
            if bd:
                stat_parts.append(f"最高单日: {bd['d'][5:]} ({bd['cnt']}张)")
            self._hmap_stat_lbl.config(text="  ·  ".join(stat_parts))

            jan1 = _date(year, 1, 1)
            dow  = jan1.weekday()           # Mon=0
            grid_start = jan1 - _td(days=dow)

            # 月份标签
            for m in range(1, 13):
                first = _date(year, m, 1)
                offset = (first - grid_start).days
                col_idx = offset // 7
                x = WLABEL_W + col_idx * STEP_S
                hmap_cv.create_text(
                    x, TOP_M - 8,
                    text=CN_MONTHS[m - 1],
                    fill=SUB,
                    font=F["tiny"],
                    anchor="sw")

            # 星期标签（只显示 一 三 五 —— 奇数行）
            for row_i in range(7):
                if row_i % 2 == 0:      # 0=一 2=三 4=五 6=日
                    y = TOP_M + row_i * STEP_S + CELL_S // 2
                    hmap_cv.create_text(
                        WLABEL_W - 6, y,
                        text=CN_WEEKS[row_i],
                        fill=SUB,
                        font=F["tiny"],
                        anchor="e")

            # 绘制格子
            dec31 = _date(year, 12, 31)
            d = grid_start
            cell_ids = {}   # canvas_id → (date_str, cnt)

            while d <= dec31 or d.weekday() != 0:
                if d > dec31: break
                offset  = (d - grid_start).days
                col_idx = offset // 7
                row_idx = d.weekday()   # Mon=0 … Sun=6
                date_str = d.strftime("%Y-%m-%d")
                cnt = heatmap_data.get(date_str, 0)
                level = _heat_level(cnt)

                x0 = WLABEL_W + col_idx * STEP_S
                y0 = TOP_M    + row_idx * STEP_S
                x1 = x0 + CELL_S
                y1 = y0 + CELL_S

                # 是否当天
                is_today = (d == _date.today())
                # 今日：紫色高亮边框
                # 零值格子：加细暗边框，形成可见网格感（参考 GitHub 热力图网格）
                # 有数据格子：无边框（颜色自身足够醒目）
                if is_today:
                    outline = "#7c3aed"
                    width   = 1.5
                elif level == 0:
                    outline = "#1e3560"   # 比填充色 #2d4270 略暗，形成微细边界
                    width   = 0.5
                else:
                    outline = ""
                    width   = 0

                cid = hmap_cv.create_rectangle(
                    x0, y0, x1, y1,
                    fill=HEAT[level],
                    outline=outline,
                    width=width,
                    tags="cell")

                if d.year == year:     # 只记录属于该年的格子
                    cell_ids[cid] = (date_str, cnt)

                d += _td(days=1)

            # hover 事件
            def _on_enter(ev):
                cid = hmap_cv.find_withtag("current")
                if not cid: return
                info = cell_ids.get(cid[0])
                if info is None: return
                ds, cnt = info
                wday_i = _date.fromisoformat(ds).weekday()
                tip_text = (
                    f"{ds}  星期{CN_WEEKS[wday_i]}\n"
                    f"生成: {cnt} 张图片"
                    if cnt else
                    f"{ds}  星期{CN_WEEKS[wday_i]}\n"
                    f"暂无生成记录"
                )
                def _do_show():
                    _show_tip(ev.x_root, ev.y_root, tip_text)
                if tip_after[0]:
                    try: win.after_cancel(tip_after[0])
                    except Exception: pass
                tip_after[0] = win.after(300, _do_show)

            def _on_leave(ev):
                if tip_after[0]:
                    try: win.after_cancel(tip_after[0])
                    except Exception: pass
                    tip_after[0] = None
                _hide_tip()

            hmap_cv.tag_bind("cell", "<Enter>", _on_enter)
            hmap_cv.tag_bind("cell", "<Leave>", _on_leave)

            # 图例
            legend_y = TOP_M + 7 * STEP_S + GAP_S + 8
            legend_x = WLABEL_W
            hmap_cv.create_text(legend_x, legend_y + CELL_S // 2,
                                text="较少", fill=SUB, font=F["tiny"], anchor="e")
            lx = legend_x + 4
            for lv, lc in enumerate(HEAT):
                hmap_cv.create_rectangle(
                    lx + lv * (CELL_S + 2), legend_y,
                    lx + lv * (CELL_S + 2) + CELL_S, legend_y + CELL_S,
                    fill=lc, outline="")
            end_x = lx + len(HEAT) * (CELL_S + 2) + 6
            hmap_cv.create_text(end_x, legend_y + CELL_S // 2,
                                text="较多", fill=SUB, font=F["tiny"], anchor="w")

        # 年份按钮组（右侧面板）
        available_years = get_available_years()
        _sel_year = [datetime.now().year]

        def _build_year_buttons():
            for w in right_rail.winfo_children():
                w.destroy()
            tk.Label(right_rail, text="年份",
                     font=F["small_b"], bg="#0d1626", fg=SUB,
                     pady=10).pack(fill="x")
            tk.Frame(right_rail, bg=BORDER, height=1).pack(fill="x")
            for yr in available_years:
                is_sel = (yr == _sel_year[0])
                btn = tk.Button(
                    right_rail, text=str(yr),
                    font=(F["_sans"], 11, "bold" if is_sel else ""),
                    bg=ACC if is_sel else "#0d1626",
                    fg="white" if is_sel else SUB,
                    bd=0, pady=10, cursor="hand2", relief="flat",
                    activebackground="#1e40af",
                    command=lambda y=yr: _select_year(y))
                btn.pack(fill="x")
                tk.Frame(right_rail, bg=BORDER, height=1).pack(fill="x")

        def _select_year(yr: int):
            _sel_year[0] = yr
            _build_year_buttons()
            _draw_heatmap(yr)

        _build_year_buttons()
        hmap_cv_host.after(80, lambda: _draw_heatmap(_sel_year[0]))

        # ════════════════════════════════════════════════════════
        #   ③ 接口使用分布（优化版）
        # ════════════════════════════════════════════════════════
        _sec_title("📡", "接口使用分布")
        pf = tk.Frame(inner, bg=BG); pf.pack(fill="x", padx=PX, pady=(8, 0))

        BAR_COLORS = [OK, "#60a5fa", "#a78bfa", "#fb923c",
                      "#f472b6", "#34d399", "#fbbf24", "#f87171"]

        if stats["providers"]:
            max_c = max(p["cnt"] for p in stats["providers"]) or 1
            for i, p in enumerate(stats["providers"]):
                # 固定四列：名称 → 比例条 → 调用次数徽章 → 百分比。
                # grid 的固定列宽能确保无论名称长短，每根横条都从同一个 x
                # 坐标开始；次数与百分比也不再互相挤占。
                row = tk.Frame(pf, bg=BG, height=46)
                row.pack(fill="x", pady=3)
                row.pack_propagate(False)
                row.grid_columnconfigure(0, minsize=260)
                row.grid_columnconfigure(1, weight=1)
                row.grid_columnconfigure(2, minsize=66)
                row.grid_columnconfigure(3, minsize=58)
                row.grid_rowconfigure(0, weight=1)

                prov_name = p["provider"]
                # 接口名拆分：provider/model 两段显示；即使供应商或模型名
                # 长度不同，也总是占同一块固定名称列。
                parts = prov_name.split("/")
                model_part = parts[-1] if len(parts) > 1 else prov_name
                prefix_part = "/".join(parts[:-1]) if len(parts) > 1 else ""

                name_fr = tk.Frame(row, bg="#141e30")
                name_fr.grid(row=0, column=0, sticky="nsew")
                name_fr.grid_rowconfigure(0, weight=1)
                name_fr.grid_rowconfigure(1, weight=1)
                tk.Label(name_fr,
                         text=prefix_part,
                         font=F["tiny"], bg="#141e30", fg="#4a6a9a",
                         anchor="e", padx=8
                         ).grid(row=0, column=0, sticky="sew")
                tk.Label(name_fr,
                         text=model_part,
                         font=F["body_b"], bg="#141e30", fg=TXT,
                         anchor="e", padx=8, wraplength=244
                         ).grid(row=1, column=0, sticky="new")

                ratio = p["cnt"] / max_c
                bar_color = BAR_COLORS[i % len(BAR_COLORS)]
                bar_host = tk.Frame(row, bg="#1a2540", height=24)
                bar_host.grid(row=0, column=1, sticky="ew", padx=(8, 8), pady=11)
                bar_host.grid_propagate(False)
                bar_fill = tk.Frame(bar_host, bg=bar_color)
                bar_fill.place(relx=0, rely=0, relwidth=ratio, relheight=1.0)

                # 次数是独立的固定宽度徽章，不再浮在进度条末端。
                count_badge = tk.Label(row, text=f"{p['cnt']} 次",
                                       font=F["badge"], bg=bar_color,
                                       fg="#0a1a0a", anchor="center", padx=6)
                count_badge.grid(row=0, column=2, sticky="ew", padx=(0, 6), pady=9)

                pct = p["cnt"] / max(stats["total"], 1) * 100
                tk.Label(row, text=f"{pct:.0f}%",
                         font=F["small"], bg=BG, fg=SUB,
                         anchor="w"
                         ).grid(row=0, column=3, sticky="w")
        else:
            tk.Label(pf, text=_("status_no_records"), font=F["body"],
                     bg=BG, fg=SUB).pack(anchor="w", pady=12)

        # ════════════════════════════════════════════════════════
        #   ④ 标签热度 Top-10（精修版）
        # ════════════════════════════════════════════════════════
        _sec_title("🏷", "标签热度 Top-10")
        tf = tk.Frame(inner, bg=BG); tf.pack(fill="x", padx=PX, pady=(8, 36))

        if stats["top_tags"]:
            max_tc = stats["top_tags"][0][1] or 1
            RANK_COLORS = ["#f59e0b", "#94a3b8", "#b45309"] + ["#475569"] * 10
            for rank, (tag, cnt) in enumerate(stats["top_tags"], 1):
                tc = tag_color(tag)
                row = tk.Frame(tf, bg="#141e30",
                               highlightbackground=BORDER,
                               highlightthickness=1)
                row.pack(fill="x", pady=3)

                # 排名
                tk.Label(row, text=f"#{rank}",
                         font=F["mono_lg"],
                         bg="#141e30", fg=RANK_COLORS[rank - 1],
                         width=3, anchor="e", padx=6, pady=8
                         ).pack(side="left")

                # 标签徽章
                badge = tk.Frame(row, bg=tc)
                badge.pack(side="left", padx=8, pady=5)
                tk.Label(badge, text=f"  {tag}  ",
                         font=F["body_b"],
                         bg=tc, fg="white", pady=4
                         ).pack()

                # 进度条（弹性）
                bar_host = tk.Frame(row, bg="#1a2540", height=20)
                bar_host.pack(side="left", fill="x", expand=True, pady=7)
                bar_host.pack_propagate(False)
                ratio = cnt / max_tc
                tk.Frame(bar_host, bg=tc, height=20
                         ).place(relx=0, rely=0, relwidth=ratio, relheight=1.0)

                # 次数 + 百分比
                pct_v = cnt / max(sum(c for _, c in stats["top_tags"]), 1) * 100
                tk.Label(row, text=f"{cnt}次  {pct_v:.0f}%",
                         font=F["mono_sm"],
                         bg="#141e30", fg=SUB,
                         width=11, anchor="w"
                         ).pack(side="left", padx=8)
        else:
            tk.Label(tf,
                     text="暂未使用标签  —  在历史记录卡片中点击 🏷 添加",
                     font=F["body_i"],
                     bg=BG, fg=SUB
                     ).pack(anchor="w", pady=16)
