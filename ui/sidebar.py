"""
ui/sidebar.py — History sidebar extracted from App  v5.1
─────────────────────────────────────────────────
"""
import threading
import os
import tkinter as tk
from tkinter import ttk, messagebox
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageTk
from config.fonts import F
from config.theme import DARK_THEME as C, TAG_PALETTE, tag_color
from config.i18n import _
from data.repository import (get_all_entries, get_all_tags, count_entries,
                             get_stats, update_tags, rename_entry,
                             toggle_favorite, delete_entry, clear_all_entries)
from ui.app_protocol import SidebarProtocol
THUMB_SIZE   = 90

# ══════════════════════════════════════════════════════════════
#   Fix-1: 平滑淡入气泡提示
# ══════════════════════════════════════════════════════════════
class _Tooltip:
    """
    鼠标悬停气泡提示。
    · 悬停 450ms 后开始显示（避免误触产生闪烁）
    · 约 16ms/帧、共 8 帧，平滑淡入到不透明
    · 鼠标离开 / 点击按钮时立即消除
    """
    def __init__(self, widget: tk.Widget, text: str, delay_ms: int = 450):
        self._w     = widget
        self._text  = text
        self._delay = delay_ms
        self._tip   = None
        self._job   = None
        self._alpha = 0.0
        widget.bind("<Enter>",       self._schedule,  add="+")
        widget.bind("<Leave>",       self._cancel,    add="+")
        widget.bind("<ButtonPress>", self._cancel,    add="+")

    def _schedule(self, _=None):
        self._cancel_job()
        self._job = self._w.after(self._delay, self._show)

    def _cancel(self, _=None):
        self._cancel_job()
        self._destroy_tip()

    def _cancel_job(self):
        if self._job:
            try: self._w.after_cancel(self._job)
            except Exception: pass
            self._job = None

    def _destroy_tip(self):
        if self._tip:
            try: self._tip.destroy()
            except Exception: pass
            self._tip = None

    def _show(self):
        self._job = None
        if self._tip: return
        try:
            # 气泡出现在控件正下方，偏右 4px
            wx = self._w.winfo_rootx() + 4
            wy = self._w.winfo_rooty() + self._w.winfo_height() + 6
            tip = tk.Toplevel(self._w)
            tip.wm_overrideredirect(True)
            tip.wm_attributes("-topmost", True)
            # 初始完全透明，后续渐显
            try: tip.wm_attributes("-alpha", 0.0)
            except Exception: pass
            tip.wm_geometry(f"+{wx}+{wy}")

            frm = tk.Frame(tip, bg="#1e3a5f",
                           highlightbackground="#4a7adf",
                           highlightthickness=1)
            frm.pack()
            tk.Label(frm, text=self._text,
                     font=F["small"], bg="#1e3a5f",
                     fg="#eaeaea", padx=9, pady=5).pack()

            self._tip   = tip
            self._alpha = 0.0
            self._fade_in()
        except Exception:
            self._tip = None

    def _fade_in(self):
        if not self._tip: return
        self._alpha = min(1.0, self._alpha + 0.15)
        try:
            self._tip.wm_attributes("-alpha", self._alpha)
        except Exception:
            self._tip = None; return
        if self._alpha < 1.0:
            self._w.after(16, self._fade_in)   # ~60 fps


# ══════════════════════════════════════════════════════════════
class HistorySidebar:
    """History sidebar panel extracted from App."""

    def __init__(self, parent: tk.Frame, app: SidebarProtocol):
        self.app = app
        self.parent = parent

        self._thumbs: dict = {}
        self._fav_only      = False
        self._inline_frame  = None

        self._tag_filter = ""
        self._hist_gen = 0
        self._card_widgets: dict = {}
        self._scroll_widgets = set()
        self._search_timer = None
        self._filter_timer = None
        self._thumb_pool = ThreadPoolExecutor(max_workers=4)

        self._build(parent)

    # ══════════════════════════════════════════════════════════
    #   侧栏构建
    # ══════════════════════════════════════════════════════════
    def _build(self, L):
        lh = tk.Frame(L, bg=C["acc"]); lh.pack(fill="x")
        tk.Label(lh, text="📒 " + _("menu_history").strip(), font=F["btn"],
                 bg=C["acc"], fg="white").pack(side="left", padx=10, pady=8)
        tk.Button(lh, text=_("btn_export"), bg=C["hl"], fg="white", bd=0,
                  font=F["body"], padx=8, pady=2, cursor="hand2",
                  command=self.app._export).pack(side="right", padx=8, pady=8)

        sf = tk.Frame(L, bg=C["panel"], pady=4); sf.pack(fill="x", padx=6)
        self.sv = tk.StringVar()
        def _on_search(*_):
            if self._search_timer:
                self.app.root.after_cancel(self._search_timer)
            self._search_timer = self.app.root.after(250, self.app._refresh_hist)
        self.sv.trace("w", _on_search)
        tk.Entry(sf, textvariable=self.sv, bg=C["entry"], fg=C["text"],
                 insertbackground="white", font=F["body"],
                 bd=0, relief="flat").pack(fill="x", ipady=5, padx=2)
        tk.Label(sf, text=_("search_placeholder"), font=F["small"],
                 bg=C["panel"], fg="#6a7a9a").pack(anchor="w", padx=4)

        flt = tk.Frame(L, bg=C["panel"]); flt.pack(fill="x", padx=6, pady=(0, 2))
        self._btn_all = tk.Button(flt, text=_("btn_show_all"), font=F["small_b"],
            bg=C["acc"], fg="white", bd=0, padx=10, pady=3, cursor="hand2",
            relief="flat", command=self._filter_all)
        self._btn_all.pack(side="left", padx=(0, 4))
        self._btn_fav = tk.Button(flt, text=_("btn_favorites_only"), font=F["small_b"],
            bg=C["panel"], fg=C["star_off"], bd=0, padx=10, pady=3, cursor="hand2",
            relief="flat", command=self._filter_fav)
        self._btn_fav.pack(side="left")

        self._tag_bar_outer = tk.Frame(L, bg=C["panel"])
        self._tag_bar_outer.pack(fill="x", padx=6, pady=(0, 3))
        self._tag_bar_lbl   = tk.Label(self._tag_bar_outer, text=_("btn_tag") + ":",
            font=F["small"], bg=C["panel"], fg=C["sub"])
        self._tag_bar_inner = tk.Frame(self._tag_bar_outer, bg=C["panel"])
        self.app.root.after(150, self._refresh_tag_chips)

        hf2 = tk.Frame(L, bg=C["panel"]); hf2.pack(fill="both", expand=True, padx=2, pady=2)
        self.hc = tk.Canvas(hf2, bg=C["panel"], bd=0, highlightthickness=0)
        sb = ttk.Scrollbar(hf2, orient="vertical", command=self.hc.yview)
        self.hc.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); self.hc.pack(side="left", fill="both", expand=True)
        self.hi = tk.Frame(self.hc, bg=C["panel"])
        self._hw = self.hc.create_window((0, 0), window=self.hi, anchor="nw")
        self.hi.bind("<Configure>", lambda e: self.hc.configure(scrollregion=self.hc.bbox("all")))
        self.hc.bind("<Configure>", lambda e: self.hc.itemconfig(self._hw, width=e.width))
        self._scroll_widgets = set()
        self._bind_scroll(self.hc); self._bind_scroll(self.hi)

        tk.Button(L, text=_("btn_reset"), bg=C["acc"], fg=C["text"],
                  bd=0, pady=5, font=F["body"], cursor="hand2",
                  command=self.app._reset_view).pack(fill="x", padx=6, pady=(0, 3))
        tk.Button(L, text=_("btn_clear_history"), bg="#2a1018", fg=C["hl"],
                  bd=0, pady=5, font=F["body"], cursor="hand2",
                  command=self._clear_hist).pack(fill="x", padx=6, pady=(0, 6))

    def _refresh_tag_chips(self):
        for w in self._tag_bar_inner.winfo_children(): w.destroy()
        tags = get_all_tags()
        if not tags:
            self._tag_bar_lbl.pack_forget(); self._tag_bar_inner.pack_forget(); return
        self._tag_bar_lbl.pack(side="left", padx=(0, 4))
        self._tag_bar_inner.pack(side="left", fill="x", expand=True)
        all_active = (self._tag_filter == "")
        tk.Button(self._tag_bar_inner, text=_("btn_show_all"), font=F["tiny_b"],
                  bg=C["hl"] if all_active else C["acc"], fg="white",
                  bd=0, padx=6, pady=2, cursor="hand2",
                  command=lambda: self._set_tag_filter("")
                  ).pack(side="left", padx=(0, 2), pady=2)
        for tag in tags[:8]:
            active = (self._tag_filter == tag)
            bg = tag_color(tag)
            tk.Button(self._tag_bar_inner, text=tag, font=F["tiny_b"],
                      bg=bg if active else C["acc"], fg="white",
                      bd=0, padx=6, pady=2, cursor="hand2",
                      command=lambda t=tag: self._set_tag_filter(t)
                      ).pack(side="left", padx=(0, 2), pady=2)

    def _set_tag_filter(self, tag: str):
        self._tag_filter = tag
        self._refresh_tag_chips(); self._debounced_refresh()

    def _bind_scroll(self, widget):
        if widget in self._scroll_widgets: return
        self._scroll_widgets.add(widget)
        widget.bind("<MouseWheel>",
                    lambda e: self.hc.yview_scroll(int(-1*(e.delta/120)), "units"), add="+")
        widget.bind("<Button-4>", lambda e: self.hc.yview_scroll(-1, "units"), add="+")
        widget.bind("<Button-5>", lambda e: self.hc.yview_scroll( 1, "units"), add="+")

    def _update_card_wraplength(self, _sidebar_w: int):
        wl = max(80, _sidebar_w - THUMB_SIZE - 44)
        try:
            for card in self.hi.winfo_children():
                for inn in card.winfo_children():
                    for right in inn.winfo_children():
                        for lbl in right.winfo_children():
                            if isinstance(lbl, tk.Label):
                                lbl.config(wraplength=wl)
        except Exception: pass

    def _card_wraplength(self, _sidebar_w: int):
        return max(80, _sidebar_w - THUMB_SIZE - 44)

    # ── 防抖刷新 ─────────────────────────────────────────────
    def _debounced_refresh(self):
        if self._filter_timer:
            self.app.root.after_cancel(self._filter_timer)
        self._filter_timer = self.app.root.after(150, self._do_refresh)

    def _do_refresh(self):
        self._filter_timer = None
        self.app._refresh_hist()
        self.app._refresh_tag_stats()

    def _filter_all(self):
        self._fav_only   = False
        self._tag_filter = ""          # ← Bug4 修复：清除标签过滤器
        self._btn_all.config(bg=C["acc"], fg="white")
        self._btn_fav.config(bg=C["panel"], fg=C["star_off"])
        self._refresh_tag_chips()      # ← 同步刷新标签栏高亮状态
        self._debounced_refresh()

    def _filter_fav(self):
        self._fav_only = True
        self._btn_fav.config(bg=C["star_on"], fg="white")
        self._btn_all.config(bg=C["panel"], fg=C["sub"])
        self._debounced_refresh()

    # ══════════════════════════════════════════════════════════
    #   历史卡片
    # ══════════════════════════════════════════════════════════
    def _refresh_hist(self, load_all: bool = False):
        self._thumbs.clear()
        # Fix-5: 每次刷新递增代号，使旧线程的回调自动失效
        self._hist_gen += 1
        cur_gen = self._hist_gen
        # 清空卡片注册表（将在 _card() 中重新注册）
        self._card_widgets.clear()
        # 重建后 _prev_sel_id 同步到当前 sel_id，避免下次 _update_sidebar_selection
        # 误操作已不存在的旧卡片
        self._prev_sel_id = self.app.sel_id

        for w in self.hi.winfo_children(): w.destroy()
        self._scroll_widgets.discard(self.hi)
        kw    = self.sv.get().strip()
        items = get_all_entries(keyword=kw, only_favorites=self._fav_only,
                                tag_filter=self._tag_filter)
        HIST_PAGE_SIZE = 100
        if not load_all:
            _has_more = len(items) > HIST_PAGE_SIZE
            if _has_more:
                items = items[:HIST_PAGE_SIZE]
        else:
            _has_more = False
        if not items:
            msg = ("暂无收藏" if self._fav_only else
                   f"🏷 无「{self._tag_filter}」标签" if self._tag_filter else
                   "无匹配" if kw else "暂无记录")
            tk.Label(self.hi, text=msg, font=F["body"],
                     bg=C["panel"], fg=C["sub"]).pack(pady=30)
            return
        for e in items:
            self._card(e, cur_gen)
        if _has_more:
            more_btn = tk.Button(self.hi, text=_("btn_show_more", count=count_entries()),
                                 font=F["body"], bg=C["acc"], fg=C["text"],
                                 bd=0, padx=12, pady=6, cursor="hand2",
                                 command=lambda: self._refresh_hist(load_all=True))
            more_btn.pack(fill="x", padx=8, pady=4)

    def _card(self, e: dict, gen: int):
        """
        渲染单条历史卡片。
        gen: 当前 _hist_gen 值，传给 _load_thumb 以支持过期检测。
        Fix-1: 每个操作图标均绑定 _Tooltip 悬浮说明。
        """
        sel    = (e["id"] == self.app.sel_id)
        is_fav = bool(e.get("favorited", 0))
        cbg    = C["card_sel"] if sel else (C["card_fav"] if is_fav else C["panel"])
        border = C["hl"] if sel else (C["star_on"] if is_fav else "#2a3a5a")
        wl     = self._card_wraplength(self.app._sidebar_w)

        card = tk.Frame(self.hi, bg=cbg, highlightbackground=border, highlightthickness=1)
        card.pack(fill="x", padx=5, pady=3)
        inn  = tk.Frame(card, bg=cbg); inn.pack(fill="x", padx=8, pady=8)

        # ── 缩略图（Fix-6: 外套固定像素 Frame + pack_propagate=False）──
        # tk.Label(width=N, height=N) 在无图片时 N 是字符单位（≈630px），
        # 会把 right 挤成 0px 宽，导致标题/信息不可见。
        # 用 Frame 固定像素尺寸，Label 填满 Frame，彻底消除字符单位问题。
        _thumb_f = tk.Frame(inn, bg=cbg, width=THUMB_SIZE, height=THUMB_SIZE)
        _thumb_f.pack(side="left", padx=(0, 10))
        _thumb_f.pack_propagate(False)   # 不让子控件撑大 Frame
        thumb_lbl = tk.Label(_thumb_f, bg=cbg, relief="flat", bd=0)
        thumb_lbl.pack(fill="both", expand=True)
        # Fix-5: 传入 gen 参数
        self._load_thumb(e.get("image_path", ""), thumb_lbl, gen)
        thumb_lbl.bind("<Button-1>",
                       lambda ev, en=e: (self.app._load_entry(en), "break")[1])
        self._bind_scroll(_thumb_f)
        self._bind_scroll(thumb_lbl)

        right = tk.Frame(inn, bg=cbg); right.pack(side="left", fill="both", expand=True)

        title = self.app._display_title(e)
        title_lbl = tk.Label(right, text=title, font=F["body_b"],
                             bg=cbg, fg=C["text"], wraplength=wl, justify="left", anchor="nw")
        title_lbl.pack(anchor="nw", fill="x")
        title_lbl.bind("<Button-1>",
                       lambda ev, en=e: (self.app._load_entry(en), "break")[1])
        self._bind_scroll(title_lbl)

        ts   = e.get("timestamp", "")[:16]
        prov = e.get("provider", "")
        sub_lbl = tk.Label(right, text=f"{ts}\n{prov}",
                           font=F["mono_sm"], bg=cbg, fg=C["sub"],
                           wraplength=wl, justify="left", anchor="nw")
        sub_lbl.pack(anchor="nw", pady=(2, 0), fill="x")
        sub_lbl.bind("<Button-1>",
                     lambda ev, en=e: (self.app._load_entry(en), "break")[1])
        self._bind_scroll(sub_lbl)

        # ── 标签芯片 ─────────────────────────────────────────
        tags_str  = e.get("tags", "") or ""
        tags_list = [t.strip() for t in tags_str.split(",") if t.strip()]
        if tags_list:
            tf = tk.Frame(right, bg=cbg); tf.pack(anchor="nw", pady=(3, 0), fill="x")
            for tag in tags_list[:4]:
                tc = tag_color(tag)
                tl = tk.Label(tf, text=tag, font=F["tiny_b"],
                              bg=tc, fg="white", padx=5, pady=1)
                tl.pack(side="left", padx=(0, 3))
                tl.bind("<Button-1>", lambda ev, t=tag: self._set_tag_filter(t))
                self._bind_scroll(tl)
            self._bind_scroll(tf)

        # ── 操作按钮行（Fix-1: 每个按钮绑定 _Tooltip）─────────
        btn_row = tk.Frame(right, bg=cbg); btn_row.pack(anchor="nw", pady=(6, 0))
        self._bind_scroll(btn_row)

        # ✏ 重命名
        edit_btn = tk.Button(btn_row, text="✏", font=F["input"],
                             bg=cbg, fg=C["sub"], bd=0, padx=4, cursor="hand2",
                             activebackground=C["acc"],
                             command=lambda en=e, r=right, t=title_lbl:
                                 self._rename_inline(en, card, r, t))
        edit_btn.pack(side="left", padx=(0, 2))
        _Tooltip(edit_btn, _("btn_rename"))

        # ★ 收藏
        star_fg  = C["star_on"] if is_fav else C["star_off"]
        star_txt = "★" if is_fav else "☆"
        star_tip = "取消收藏" if is_fav else "添加到收藏"
        star_btn = tk.Button(btn_row, text=star_txt, font=F["label"],
                             bg=cbg, fg=star_fg, bd=0, padx=4, cursor="hand2",
                             activebackground=C["acc"],
                             command=lambda en=e: self._toggle_fav(en))
        star_btn.pack(side="left", padx=(0, 2))
        _Tooltip(star_btn, star_tip)

        # 🏷 标签
        tag_btn = tk.Button(btn_row, text="🏷", font=F["input"],
                            bg=cbg, fg=C["sub"], bd=0, padx=4, cursor="hand2",
                            activebackground=C["acc"],
                            command=lambda en=e: self._open_tag_editor(en))
        tag_btn.pack(side="left", padx=(0, 2))
        _Tooltip(tag_btn, _("btn_tag"))

        # ⚖ 对比
        cmp_btn = tk.Button(btn_row, text="⚖", font=F["input"],
                            bg=cbg, fg="#a78bfa", bd=0, padx=4, cursor="hand2",
                            activebackground="#4a1d96",
                            command=lambda en=e: self.app._set_cmp_from_entry(en))
        cmp_btn.pack(side="left", padx=(0, 2))
        _Tooltip(cmp_btn, "设为右侧对比图")

        # 🗑 删除
        del_btn = tk.Button(btn_row, text="🗑", font=F["input"],
                            bg=cbg, fg="#e05555", bd=0, padx=4, cursor="hand2",
                            activebackground=C["hl"],
                            command=lambda en=e: self._del_entry(en["id"]))
        del_btn.pack(side="left")
        _Tooltip(del_btn, _("btn_delete"))

        for w in [card, inn, right]:
            # "break" 阻止事件向父控件冒泡，确保 _load_entry 每次点击只调用一次
            w.bind("<Button-1>",
                   lambda ev, en=e: (self.app._load_entry(en), "break")[1])
            self._bind_scroll(w)

        # ── 右键菜单（快速操作，减少操作层级）────────────────
        def _show_ctx(ev, en=e):
            """弹出右键上下文菜单"""
            menu = tk.Menu(self.app.root, tearoff=0,
                           bg=C["panel"], fg=C["text"],
                           activebackground=C["acc"],
                           activeforeground="white",
                           font=F["body"])

            # 📋 复制提示词
            def _copy_prompt():
                self.app.root.clipboard_clear()
                self.app.root.clipboard_append(en["prompt"])
                self.app._st("📋 提示词已复制", "ok")

            # 📁 复制图片路径
            def _copy_path():
                p = en.get("image_path", "")
                if p:
                    self.app.root.clipboard_clear()
                    self.app.root.clipboard_append(p)
                    self.app._st("📁 路径已复制", "ok")

            # 🔁 一键重新生成（填入输入框并立即生成）
            def _regen():
                self.app.pt.delete("1.0", "end")
                self.app.pt.insert("1.0", en["prompt"])
                self.app._gen()

            # 🔍 在查看器中打开
            def _open_viewer_ctx():
                p = en.get("image_path", "")
                if p and os.path.exists(p):
                    self.app.cur_path   = p
                    with open(p, "rb") as _fh:
                        self.app._cur_bytes = _fh.read()
                    self.app._open_viewer()

            # ➕ 加入生成队列
            def _add_to_queue():
                sz    = self.app.szv.get()
                psel  = self.app.pv.get()
                pord  = None if psel == _("provider_auto") else [psel]
                self.app._queue_panel.add_task(en["prompt"], sz, pord)
                self.app._switch_to_queue_tab()
                self.app._st("📋 已加入队列", "ok")

            menu.add_command(label="📋  复制提示词",      command=_copy_prompt)
            menu.add_command(label="📁  复制图片路径",    command=_copy_path)
            menu.add_separator()
            menu.add_command(label="🔁  一键重新生成",    command=_regen)
            menu.add_command(label="🔍  在查看器中打开",  command=_open_viewer_ctx)
            menu.add_separator()
            menu.add_command(label="➕  加入生成队列",    command=_add_to_queue)
            menu.add_separator()
            menu.add_command(label="🗑  删除此记录",
                             command=lambda en_=en: self._del_entry(en_["id"]),
                             foreground="#e05555")
            menu.post(ev.x_root, ev.y_root)
            menu.bind("<FocusOut>", lambda _: menu.destroy())

        for w in [card, inn, right, _thumb_f, thumb_lbl, title_lbl, sub_lbl]:
            w.bind("<Button-3>", _show_ctx)

        # ── 卡片颜色注册表（轻量选中态切换，无需重建列表）──────
        # 收集所有使用 cbg 的控件（用于选中/取消选中时更新背景色）
        _cbg_widgets = [inn, right, title_lbl, sub_lbl, btn_row,
                        edit_btn, star_btn, tag_btn, cmp_btn, del_btn, _thumb_f]
        if tags_list:
            # tf 是 right 的子 Frame，bg 也是 cbg
            for _w in right.winfo_children():
                if isinstance(_w, tk.Frame) and _w not in _cbg_widgets:
                    _cbg_widgets.append(_w)

        def _sel_updater(is_selected, _is_fav, _card=card,
                         _cbg_w=list(_cbg_widgets)):
            new_cbg    = (C["card_sel"] if is_selected
                          else (C["card_fav"] if _is_fav else C["panel"]))
            new_border = (C["hl"]       if is_selected
                          else (C["star_on"] if _is_fav else "#2a3a5a"))
            try:
                _card.config(highlightbackground=new_border)
                for w in _cbg_w:
                    try: w.config(bg=new_cbg)
                    except Exception: pass
            except Exception: pass

        self._card_widgets[e["id"]] = {"fn": _sel_updater, "is_fav": is_fav}

    # ══════════════════════════════════════════════════════════
    #   轻量选中态切换（不重建列表，零闪烁）
    # ══════════════════════════════════════════════════════════
    def _update_sidebar_selection(self, new_id: int):
        """
        仅修改前一张和新一张卡片的背景色/边框色，
        完全不销毁/重建任何 widget，彻底消除与 viewer 的竞态。
        """
        old_id = getattr(self, "_prev_sel_id", None)
        # 取消旧选中态
        if old_id is not None and old_id != new_id:
            cd = self._card_widgets.get(old_id)
            if cd:
                try: cd["fn"](False, cd["is_fav"])
                except Exception: pass
        # 设置新选中态
        cd = self._card_widgets.get(new_id)
        if cd:
            try: cd["fn"](True, cd["is_fav"])
            except Exception: pass
        self._prev_sel_id = new_id

    # ══════════════════════════════════════════════════════════
    #   彻底修复：缩略图异步加载（双重校验防 widget ID 复用污染）
    # ══════════════════════════════════════════════════════════
    def _load_thumb(self, path: str, label: tk.Label, gen: int):
        """
        安全异步加载缩略图。
        双重校验机制：
          1. gen 代号：_refresh_hist 每次递增，旧批次线程发现代号不匹配则放弃
          2. widget token：在 label 上记录本批次唯一 token，_apply 回调时再次
             验证 label 上的 token 是否仍与启动时相同，避免 Tkinter widget
             内部 ID 被销毁/重建后复用导致旧图片覆盖到新卡片的 Label 上。
        所有 UI 操作严格在主线程通过 after(0, ...) 执行。
        """
        import uuid as _uuid
        # 为本次加载生成唯一 token，写入 label 对象属性
        token = _uuid.uuid4().hex
        label._thumb_token = token   # type: ignore[attr-defined]

        def _worker():
            try:
                if path and os.path.exists(path):
                    img = Image.open(path)
                    img.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
                    canvas_img = Image.new("RGBA", (THUMB_SIZE, THUMB_SIZE), (13, 27, 42, 255))
                    ox = (THUMB_SIZE - img.width)  // 2
                    oy = (THUMB_SIZE - img.height) // 2
                    canvas_img.paste(img.convert("RGBA"), (ox, oy))

                    def _apply(ci=canvas_img, tok=token, lbl=label, g=gen):
                        # 双重校验：gen 代号 + widget token
                        if self._hist_gen != g:
                            return
                        try:
                            # winfo_exists() 返回 False 说明 widget 已被销毁
                            if not lbl.winfo_exists():
                                return
                            # token 不一致说明这个 label 已被新卡片的 _load_thumb 重新使用
                            if getattr(lbl, "_thumb_token", None) != tok:
                                return
                            ph = ImageTk.PhotoImage(ci)
                            self._thumbs[path] = ph
                            lbl.config(image=ph, text="",
                                       width=THUMB_SIZE, height=THUMB_SIZE)
                        except tk.TclError:
                            pass

                    self.app.root.after(0, _apply)

                else:
                    def _apply_empty(tok=token, lbl=label, g=gen):
                        if self._hist_gen != g:
                            return
                        try:
                            if not lbl.winfo_exists():
                                return
                            if getattr(lbl, "_thumb_token", None) != tok:
                                return
                            lbl.config(text="🖼", font=F["display"],
                                       width=6, height=3)
                        except tk.TclError:
                            pass
                    self.app.root.after(0, _apply_empty)

            except Exception:
                pass

        self._thumb_pool.submit(_worker)


    # ══════════════════════════════════════════════════════════
    #   标签编辑器
    # ══════════════════════════════════════════════════════════
    def _open_tag_editor(self, entry: dict):
        title_str   = self.app._display_title(entry)
        cur_tags    = [t.strip() for t in (entry.get("tags") or "").split(",") if t.strip()]
        all_db_tags = [t for t in get_all_tags() if t not in cur_tags]

        win = tk.Toplevel(self.app.root)
        win.title(f"🏷 编辑标签 — {title_str[:30]}")
        win.configure(bg=C["bg"]); win.resizable(False, False); win.grab_set()
        win.update_idletasks()
        x = self.app.root.winfo_x() + (self.app.root.winfo_width()  - 440) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - 460) // 2
        win.geometry(f"440x460+{max(0,x)}+{max(0,y)}")

        hdr = tk.Frame(win, bg=C["acc"]); hdr.pack(fill="x")
        tk.Label(hdr, text="🏷  编辑标签", font=F["h2"],
                 bg=C["acc"], fg="white").pack(side="left", padx=14, pady=8)
        tk.Label(hdr, text=f"「{title_str[:24]}」",
                 font=F["body"], bg=C["acc"], fg="#c0d8ff").pack(side="right", padx=14)

        body = tk.Frame(win, bg=C["bg"]); body.pack(fill="both", expand=True, padx=14, pady=10)
        tk.Label(body, text="当前标签（点击移除）",
                 font=F["body_b"], bg=C["bg"], fg=C["sub"]).pack(anchor="w")
        cur_f    = tk.Frame(body, bg=C["bg"], height=36); cur_f.pack(fill="x", pady=(4, 8))
        live_tags = list(cur_tags)

        def _rebuild_cur():
            for w in cur_f.winfo_children(): w.destroy()
            if not live_tags:
                tk.Label(cur_f, text=_("status_no_records"), font=F["small_i"],
                         bg=C["bg"], fg=C["sub"]).pack(side="left"); return
            for tag in live_tags:
                tc = tag_color(tag)
                fr = tk.Frame(cur_f, bg=tc); fr.pack(side="left", padx=(0, 4))
                tk.Label(fr, text=tag, font=F["small_b"],
                         bg=tc, fg="white", padx=5, pady=2).pack(side="left")
                tk.Button(fr, text="✕", font=F["tiny"], bg=tc, fg="white", bd=0,
                          padx=2, pady=1, cursor="hand2",
                          command=lambda t=tag: (_remove(t))).pack(side="left")

        def _remove(tag):
            if tag in live_tags: live_tags.remove(tag)
            _rebuild_cur()

        def _add(tag):
            if tag and tag not in live_tags: live_tags.append(tag)
            _rebuild_cur()

        _rebuild_cur()

        tk.Frame(body, bg=C["sep"], height=1).pack(fill="x", pady=(0, 6))
        tk.Label(body, text="从历史标签选择", font=F["body_b"],
                 bg=C["bg"], fg=C["sub"]).pack(anchor="w")
        sug_f = tk.Frame(body, bg=C["bg"]); sug_f.pack(fill="x", pady=(4, 8))
        if all_db_tags:
            for tag in all_db_tags[:16]:
                tk.Button(sug_f, text=tag, font=F["small"],
                          bg=C["acc"], fg="white", bd=0, padx=7, pady=2, cursor="hand2",
                          command=lambda t=tag: _add(t)
                          ).pack(side="left", padx=(0, 4), pady=2)
        else:
            tk.Label(sug_f, text="（无历史标签）", font=F["small_i"],
                     bg=C["bg"], fg=C["sub"]).pack(side="left")

        tk.Frame(body, bg=C["sep"], height=1).pack(fill="x", pady=(0, 6))
        tk.Label(body, text="新建标签", font=F["body_b"],
                 bg=C["bg"], fg=C["sub"]).pack(anchor="w")
        nr = tk.Frame(body, bg=C["bg"]); nr.pack(fill="x", pady=(4, 0))
        nv = tk.StringVar()
        nef = tk.Frame(nr, bg=C["entry"]); nef.pack(side="left", fill="x", expand=True)
        ne  = tk.Entry(nef, textvariable=nv, bg=C["entry"], fg=C["text"],
                       insertbackground="white", font=F["body"], bd=0, relief="flat")
        ne.pack(fill="x", padx=8, ipady=5)

        def _confirm_new(ev=None):
            val = nv.get().strip()
            if val: _add(val); nv.set("")

        tk.Button(nr, text=_("btn_confirm"), font=F["body"],
                  bg=C["ok"], fg="#0a1a0a", bd=0, padx=12, pady=5,
                  cursor="hand2", command=_confirm_new).pack(side="left", padx=(6, 0))
        ne.bind("<Return>", _confirm_new)

        bot = tk.Frame(win, bg=C["panel"]); bot.pack(fill="x", side="bottom")

        def _save():
            update_tags(entry["id"], ",".join(live_tags))
            self.app._refresh_hist(); self._refresh_tag_chips(); self.app._refresh_tag_stats()
            self.app._log(f"🏷 更新标签 id={entry['id']} → {','.join(live_tags)}")
            win.destroy()

        tk.Button(bot, text="✅  " + _("btn_save").strip(), font=F["btn"],
                  bg=C["ok"], fg="#0a1a0a", bd=0, padx=22, pady=8,
                  cursor="hand2", command=_save).pack(side="right", padx=14, pady=10)
        tk.Button(bot, text=_("btn_cancel"), font=F["body"],
                  bg=C["panel"], fg=C["sub"], bd=0, padx=14, pady=8,
                  cursor="hand2", command=win.destroy).pack(side="right", pady=10)

    # ══════════════════════════════════════════════════════════
    #   重命名 / 收藏 / 删除
    # ══════════════════════════════════════════════════════════
    def _rename_inline(self, entry, card, right, title_lbl):
        if self._inline_frame is not None:
            try: self._inline_frame.destroy()
            except Exception: pass
            self._inline_frame = None
        cbg    = card.cget("bg")
        inline = tk.Frame(right, bg=cbg)
        inline.pack(anchor="nw", fill="x", pady=(4, 0))
        self._inline_frame = inline
        nick_var = tk.StringVar(value=entry.get("nickname") or "")
        ent = tk.Entry(inline, textvariable=nick_var, width=18,
                       bg=C["entry"], fg=C["text"], insertbackground="white",
                       font=F["body"], bd=1, relief="solid",
                       highlightbackground=C["acc"], highlightthickness=1)
        ent.pack(fill="x", ipady=4); ent.focus_set(); ent.icursor("end")
        tip = tk.Label(inline, text=f"0/{self.app.MAX_NICK_LEN} 字",
                       font=F["tiny"], bg=cbg, fg=C["sub"]); tip.pack(anchor="e")
        def _on_key(*_):
            v = nick_var.get()
            if len(v) > self.app.MAX_NICK_LEN: nick_var.set(v[:self.app.MAX_NICK_LEN])
            tip.config(text=f"{len(nick_var.get())}/{self.app.MAX_NICK_LEN} 字")
        nick_var.trace("w", _on_key); _on_key()
        btn2 = tk.Frame(inline, bg=cbg); btn2.pack(fill="x", pady=(3, 0))
        def _confirm():
            nn = nick_var.get().strip()
            if not messagebox.askyesno("确认", f'重命名为：「{nn or "(清除)"}」？', parent=self.app.root): return
            rename_entry(entry["id"], nn)
            try: inline.destroy(); self._inline_frame = None
            except Exception: pass
            disp = nn if nn else (entry["prompt"][:self.app.MAX_NICK_LEN] + ("…" if len(entry["prompt"]) > self.app.MAX_NICK_LEN else ""))
            title_lbl.config(text=disp)
        def _cancel():
            try: inline.destroy(); self._inline_frame = None
            except Exception: pass
        tk.Button(btn2, text=_("btn_confirm"), font=F["small"], bg=C["ok"], fg="#0a1a0a",
                  bd=0, padx=8, pady=2, cursor="hand2", command=_confirm).pack(side="left", padx=(0, 4))
        tk.Button(btn2, text=_("btn_cancel"), font=F["small"], bg=C["panel"], fg=C["sub"],
                  bd=0, padx=8, pady=2, cursor="hand2", command=_cancel).pack(side="left")
        ent.bind("<Return>", lambda ev: _confirm())
        ent.bind("<Escape>", lambda ev: _cancel())

    def _toggle_fav(self, entry):
        is_fav = bool(entry.get("favorited", 0))
        title  = self.app._display_title(entry)
        if is_fav:
            if not messagebox.askyesno("取消收藏", f'从喜爱列表移除？\n\n「{title}」', parent=self.app.root): return
            toggle_favorite(entry["id"], False)
        else:
            if not messagebox.askyesno("添加收藏", f'收藏到喜爱列表？\n\n「{title}」', parent=self.app.root): return
            toggle_favorite(entry["id"], True)
        self.app._refresh_hist()

    def _del_entry(self, eid):
        if not messagebox.askyesno(_("dlg_confirm_delete"),
                _("dlg_confirm_delete"),
                parent=self.app.root): return
        delete_entry(eid, remove_file=True)
        if self.app.sel_id == eid: self.app.sel_id = None; self.app._reset_view()
        else: self.app._refresh_hist()

    def _clear_hist(self):
        n = count_entries()
        if not n: return
        if messagebox.askyesno(_("dlg_confirm_clear"), f"清空全部 {n} 条记录？\n（不删除磁盘图片文件）"):
            clear_all_entries(); self.app._refresh_hist()
