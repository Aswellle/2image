"""
ui/phrase_panel.py  v2
──────────────────────
提示词片段库对话框（Toplevel，非模态）。

  v2 新增 ── 词条悬浮说明提示框（_PhraseTooltip）
    · 鼠标悬停 300ms 后淡入（避免快速划过触发闪烁）
    · 10 帧 × 25ms 丝滑淡入动画，缓出曲线（先快后慢）
    · 悬浮窗：紫色细边框 + 深色背景 + 词条英文高亮标题 + 中文正文
    · wraplength=280，最大宽度约 300px，不会遮挡太多内容
    · 鼠标离开 / 点击 → 立即消失（0 延迟）
    · 全局唯一：同时只有一个提示框可见
    · 位置自动贴近鼠标右下 14px，并防止超出屏幕边界
"""
import tkinter as tk
from tkinter import messagebox, ttk

from services.phrase_library import (
    get_all_phrases, add_custom_phrase,
    delete_custom_phrase, is_builtin, get_phrase_desc,
)
from config.fonts import F
from config.theme import DARK_THEME as C
from config.i18n import _


_CAT_COLORS = {
    "✨ 画质增强": "#065f46",
    "💡 光影效果": "#92400e",
    "🎨 艺术风格": "#7c3aed",
    "📐 构图方式": "#0f3460",
    "📷 镜头参数": "#1d4ed8",
    "🌙 氛围情绪": "#9f1239",
    "👤 人物细节": "#0369a1",
}


# ══════════════════════════════════════════════════════════════
#   词条悬浮说明提示框
# ══════════════════════════════════════════════════════════════
class _PhraseTooltip:
    """
    词条中文说明悬浮窗。

    使用方式：
        tip = _PhraseTooltip(root, chip_frame, phrase, desc)
        # 保存到列表防止 GC：self._tips.append(tip)
    """

    _current: "_PhraseTooltip | None" = None   # 当前可见的唯一实例

    # ── 动画常量 ─────────────────────────────────────────────
    _DELAY_MS  = 300    # 悬停多久后开始淡入
    _FRAMES    = 10     # 淡入总帧数
    _FRAME_MS  = 25     # 每帧间隔（ms）
    _MAX_ALPHA = 0.96   # 最终不透明度

    def __init__(self, root: tk.Misc, widget: tk.Widget,
                 phrase: str, desc: str):
        self._root    = root
        self._widget  = widget
        self._phrase  = phrase
        self._desc    = desc

        self._win     = None    # Toplevel
        self._show_id = None    # after ID：延迟显示计时器
        self._fade_id = None    # after ID：淡入动画计时器

        # 绑定到传入的 widget
        widget.bind("<Enter>",    self._on_enter,  add="+")
        widget.bind("<Leave>",    self._on_leave,  add="+")
        widget.bind("<Button-1>", self._on_click,  add="+")

    # ── 绑定额外 widget（如同一张卡片内的 Label）───────────────
    def attach(self, widget: tk.Widget):
        widget.bind("<Enter>",    self._on_enter, add="+")
        widget.bind("<Leave>",    self._on_leave, add="+")
        widget.bind("<Button-1>", self._on_click, add="+")

    # ── 事件处理 ─────────────────────────────────────────────
    def _on_enter(self, _=None):
        # 关闭当前可见的其他提示
        cur = _PhraseTooltip._current
        if cur and cur is not self:
            cur._close()
        _PhraseTooltip._current = self
        self._cancel()
        if self._desc:
            self._show_id = self._root.after(self._DELAY_MS, self._open)

    def _on_leave(self, _=None):
        self._close()

    def _on_click(self, _=None):
        self._close()

    # ── 取消定时器 ────────────────────────────────────────────
    def _cancel(self):
        for attr in ("_show_id", "_fade_id"):
            jid = getattr(self, attr)
            if jid:
                try: self._root.after_cancel(jid)
                except Exception: pass
            setattr(self, attr, None)

    # ── 关闭（立即消失）──────────────────────────────────────
    def _close(self):
        self._cancel()
        if self._win:
            try:   self._win.destroy()
            except Exception: pass
            self._win = None
        if _PhraseTooltip._current is self:
            _PhraseTooltip._current = None

    # ── 创建并定位提示窗 ──────────────────────────────────────
    def _open(self):
        self._show_id = None
        if not self._desc: return
        try:
            if not self._widget.winfo_exists(): return
        except Exception: return

        # 若已有旧窗先销毁
        if self._win:
            try: self._win.destroy()
            except Exception: pass

        tip = tk.Toplevel(self._root)
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        tip.attributes("-alpha", 0.0)       # 完全透明起步
        tip.configure(bg="#0d0d1f")
        self._win = tip

        # ── 外框（紫色细边框）──────────────────────────────
        border = tk.Frame(tip, bg="#7c3aed",
                          highlightbackground="#7c3aed",
                          highlightthickness=1)
        border.pack(fill="both", expand=True)

        # 词条英文标题栏
        title_bar = tk.Frame(border, bg="#1e1b4b")
        title_bar.pack(fill="x")
        tk.Label(title_bar,
                 text=f"  {self._phrase}",
                 font=F["badge"],
                 bg="#1e1b4b", fg="#c4b5fd",
                 padx=6, pady=6, anchor="w"
                 ).pack(fill="x")

        # 分隔线
        tk.Frame(border, bg="#4c1d95", height=1).pack(fill="x")

        # 中文说明正文
        tk.Label(border,
                 text=self._desc,
                 font=F["body"],
                 bg="#0d0d1f", fg="#e2e8f0",
                 wraplength=280,
                 justify="left",
                 padx=11, pady=9,
                 anchor="nw"
                 ).pack(fill="both", expand=True)

        # ── 定位：贴近鼠标右下，防超出屏幕 ───────────────────
        tip.update_idletasks()
        tw = tip.winfo_reqwidth()
        th = tip.winfo_reqheight()
        try:
            px = self._widget.winfo_pointerx() + 14
            py = self._widget.winfo_pointery() + 14
            sw = tip.winfo_screenwidth()
            sh = tip.winfo_screenheight()
            if px + tw > sw - 6: px = self._widget.winfo_pointerx() - tw - 14
            if py + th > sh - 6: py = self._widget.winfo_pointery() - th - 14
            px = max(2, px); py = max(2, py)
        except Exception:
            px, py = 100, 100
        tip.geometry(f"+{px}+{py}")

        # ── 启动淡入动画 ───────────────────────────────────────
        self._fade_step(tip, 0)

    def _fade_step(self, tip: tk.Toplevel, step: int):
        """缓出曲线淡入：progress^0.55，前期快后期慢，共 _FRAMES 帧。"""
        if self._win is not tip: return
        progress = step / (self._FRAMES - 1) if self._FRAMES > 1 else 1.0
        alpha = min(self._MAX_ALPHA, progress ** 0.55 * self._MAX_ALPHA)
        try:
            tip.attributes("-alpha", alpha)
        except Exception:
            return
        if step < self._FRAMES - 1:
            self._fade_id = self._root.after(
                self._FRAME_MS,
                lambda: self._fade_step(tip, step + 1))
        else:
            self._fade_id = None


# ══════════════════════════════════════════════════════════════
#   主面板
# ══════════════════════════════════════════════════════════════
class PhrasePanel(tk.Toplevel):
    """提示词片段库面板（非模态）。"""

    def __init__(self, parent_app):
        super().__init__(parent_app.root)
        self.app        = parent_app
        self._phrases   = {}
        self._cur_cat   = None
        self._chip_btns = []
        self._tips: list[_PhraseTooltip] = []  # 持有引用防 GC

        self.title(_("phrase_title"))
        self.geometry("820x560")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.minsize(640, 460)

        self.update_idletasks()
        rx = parent_app.root.winfo_x() + (parent_app.root.winfo_width()  - 820) // 2
        ry = parent_app.root.winfo_y() + (parent_app.root.winfo_height() - 560) // 2
        self.geometry(f"820x560+{max(0,rx)}+{max(0,ry)}")

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.lift(); self.focus_force()

    # ── 构建 UI ──────────────────────────────────────────────
    def _build(self):
        # ── 顶部标题栏 ────────────────────────────────────────
        hdr = tk.Frame(self, bg="#7c3aed")
        hdr.pack(fill="x")
        tk.Label(hdr, text=_("phrase_title"),
                 font=F["h1"], bg="#7c3aed", fg="white"
                 ).pack(side="left", padx=14, pady=10)
        tk.Label(hdr,
                 text="点击词条追加到输入框  ·  🖱 悬停词条查看中文说明",
                 font=F["small"], bg="#7c3aed", fg="#d0b8ff"
                 ).pack(side="left", padx=4)

        # ── 搜索栏 ────────────────────────────────────────────
        sf = tk.Frame(self, bg=C["panel"])
        sf.pack(fill="x")
        tk.Label(sf, text="🔍", font=F["input"],
                 bg=C["panel"], fg=C["sub"]
                 ).pack(side="left", padx=(10, 4), pady=8)
        self._sv = tk.StringVar()
        self._sv.trace("w", lambda *_: self._apply_search())
        _sef = tk.Frame(sf, bg=C["entry"],
                        highlightbackground=C["ok"], highlightthickness=1)
        _sef.pack(side="left", pady=6, padx=(0, 8))
        _se = tk.Entry(_sef, textvariable=self._sv,
                       bg=C["entry"], fg=C["text"],
                       insertbackground="white",
                       font=F["input"], bd=0, relief="flat", width=28)
        _se.pack(fill="x", padx=4, ipady=4)
        _se.bind("<FocusIn>",  lambda _: _sef.config(highlightbackground=C["entry"]), add="+")
        _se.bind("<FocusOut>", lambda _: _sef.config(highlightbackground=C["ok"]),    add="+")
        tk.Button(sf, text="✕ 清空搜索",
                  font=F["small"], bg=C["panel"], fg=C["sub"],
                  bd=0, padx=8, cursor="hand2",
                  command=lambda: self._sv.set("")
                  ).pack(side="left")

        # ── 主体（左右分栏）──────────────────────────────────
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True)

        # 左：分类列表
        left = tk.Frame(body, bg=C["panel"], width=170)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Label(left, text="分类",
                 font=F["body_b"],
                 bg=C["panel"], fg=C["sub"]
                 ).pack(anchor="w", padx=10, pady=(8, 4))
        tk.Frame(left, bg=C["sep"], height=1).pack(fill="x")
        self._cat_frame = tk.Frame(left, bg=C["panel"])
        self._cat_frame.pack(fill="both", expand=True)

        # 右：词条区（可滚动）
        right = tk.Frame(body, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)
        chip_host = tk.Frame(right, bg=C["bg"])
        chip_host.pack(fill="both", expand=True, padx=8, pady=8)

        self._chip_cv = tk.Canvas(chip_host, bg=C["bg"],
                                   bd=0, highlightthickness=0)
        vsb = ttk.Scrollbar(chip_host, orient="vertical",
                             command=self._chip_cv.yview)
        self._chip_cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._chip_cv.pack(side="left", fill="both", expand=True)

        self._chip_inner = tk.Frame(self._chip_cv, bg=C["bg"])
        _cw = self._chip_cv.create_window(
            (0, 0), window=self._chip_inner, anchor="nw")
        self._chip_inner.bind(
            "<Configure>",
            lambda e: self._chip_cv.configure(
                scrollregion=self._chip_cv.bbox("all")))
        self._chip_cv.bind(
            "<Configure>",
            lambda e: self._chip_cv.itemconfig(_cw, width=e.width))
        # 鼠标滚轮
        for seq, delta in (("<MouseWheel>", None),
                           ("<Button-4>", -1), ("<Button-5>", 1)):
            if delta is None:
                self._chip_cv.bind(
                    seq,
                    lambda e: self._chip_cv.yview_scroll(
                        int(-1 * (e.delta / 120)), "units"))
            else:
                self._chip_cv.bind(
                    seq,
                    lambda e, d=delta: self._chip_cv.yview_scroll(d, "units"))

        # ── 底部：添加自定义词条 ──────────────────────────────
        bot = tk.Frame(self, bg=C["panel"])
        bot.pack(fill="x")
        tk.Frame(bot, bg=C["sep"], height=1).pack(fill="x")
        add_row = tk.Frame(bot, bg=C["panel"])
        add_row.pack(fill="x", padx=10, pady=8)
        tk.Label(add_row, text="➕ 新建词条：",
                 font=F["body_b"],
                 bg=C["panel"], fg=C["sub"]
                 ).pack(side="left")
        nef = tk.Frame(add_row, bg=C["entry"],
                       highlightbackground=C["ok"], highlightthickness=1)
        nef.pack(side="left", fill="x", expand=True, padx=(4, 6))
        self._new_phrase_var = tk.StringVar()
        _ne = tk.Entry(nef, textvariable=self._new_phrase_var,
                       bg=C["entry"], fg=C["text"],
                       insertbackground="white",
                       font=F["input"], bd=0, relief="flat")
        _ne.pack(fill="x", padx=8, ipady=5)
        _ne.bind("<FocusIn>",  lambda _: nef.config(highlightbackground=C["entry"]), add="+")
        _ne.bind("<FocusOut>", lambda _: nef.config(highlightbackground=C["ok"]),    add="+")
        tk.Button(add_row, text="添加到当前分类",
                  font=F["body"], bg=C["ok"], fg="#0a1a0a",
                  bd=0, padx=12, pady=4, cursor="hand2",
                  command=self._add_phrase
                  ).pack(side="left")

        self._reload()

    # ── 数据 & 分类刷新 ─────────────────────────────────────
    def _reload(self):
        self._phrases = get_all_phrases()
        self._rebuild_cats()
        cats = list(self._phrases.keys())
        if cats:
            self._select_cat(cats[0])

    def _rebuild_cats(self):
        for w in self._cat_frame.winfo_children():
            w.destroy()
        for cat in self._phrases.keys():
            color  = _CAT_COLORS.get(cat, C["acc"])
            is_sel = (cat == self._cur_cat)
            tk.Button(
                self._cat_frame, text=cat,
                font=(F["_sans"], 10, "bold" if is_sel else ""),
                bg=color if is_sel else C["panel"],
                fg="white", bd=0, padx=10, pady=7,
                anchor="w", cursor="hand2", relief="flat",
                command=lambda c=cat: self._select_cat(c)
            ).pack(fill="x")
            cnt = len(self._phrases.get(cat, []))
            tk.Label(self._cat_frame,
                     text=f"  {cnt} 条",
                     font=F["tiny"], bg=C["panel"], fg=C["sub"]
                     ).pack(anchor="e", padx=8)

    def _select_cat(self, cat: str):
        self._cur_cat = cat
        self._sv.set("")
        self._rebuild_cats()
        self._render_chips(self._phrases.get(cat, []))

    def _apply_search(self):
        kw = self._sv.get().strip().lower()
        if not kw:
            if self._cur_cat:
                self._render_chips(self._phrases.get(self._cur_cat, []))
            return
        results = [p for phrases in self._phrases.values()
                   for p in phrases if kw in p.lower()]
        self._render_chips(results, search_mode=True)

    # ── 词条渲染（含悬浮说明绑定）───────────────────────────
    def _render_chips(self, phrases: list, search_mode: bool = False):
        # 清理旧 tooltip（立即关闭任何可见的）
        for tip in self._tips:
            try: tip._close()
            except Exception: pass
        self._tips.clear()

        for w in self._chip_inner.winfo_children():
            w.destroy()
        self._chip_btns.clear()
        self._chip_cv.yview_moveto(0)

        if not phrases:
            tk.Label(self._chip_inner,
                     text="（暂无词条）" if not search_mode else "（无匹配结果）",
                     font=(F["_sans"], 11, "italic"),
                     bg=C["bg"], fg=C["sub"]
                     ).pack(pady=24, anchor="w", padx=16)
            return

        color = (_CAT_COLORS.get(self._cur_cat, C["acc"])
                 if not search_mode else C["acc"])
        HL_BG = "#243a60"   # 悬停背景色

        for i, phrase in enumerate(phrases):
            row_idx, col_idx = divmod(i, 3)
            self._chip_inner.columnconfigure(col_idx, weight=1)

            # ── 卡片主框 ──────────────────────────────────
            chip = tk.Frame(self._chip_inner, bg=C["card"],
                            highlightbackground=color,
                            highlightthickness=1)
            chip.grid(row=row_idx, column=col_idx,
                      padx=5, pady=5, sticky="ew")

            # ── 词条文字 label ─────────────────────────────
            lbl = tk.Label(chip, text=phrase,
                           font=F["body"],
                           bg=C["card"], fg=C["text"],
                           wraplength=200, justify="left", anchor="w")
            lbl.pack(side="left", fill="x", expand=True, padx=8, pady=6)

            # ── 追加按钮 ───────────────────────────────────
            append_btn = tk.Button(
                chip, text="➕", font=F["body"],
                bg=color, fg="white", bd=0, padx=6, pady=3,
                cursor="hand2",
                command=lambda p=phrase: self._append_to_input(p))
            append_btn.pack(side="right", padx=4, pady=4)

            # ── 删除按钮（仅自定义词条）───────────────────
            if not is_builtin(self._cur_cat or "", phrase):
                def _del(cat=self._cur_cat, p=phrase):
                    if messagebox.askyesno(
                            "删除词条", f'删除「{p}」？', parent=self):
                        delete_custom_phrase(cat, p)
                        self._reload()
                tk.Button(chip, text="🗑", font=F["small"],
                          bg=C["card"], fg="#e05555", bd=0, padx=4,
                          cursor="hand2", command=_del
                          ).pack(side="right", padx=2, pady=4)

            # ── 点击整行也追加 ────────────────────────────
            for w in (chip, lbl):
                w.bind("<Button-1>",
                       lambda e, p=phrase: self._append_to_input(p))

            # ── 悬停高亮（chip + 内部所有 Label）─────────
            def _enter(_, f=chip, c=color):
                f.config(bg=HL_BG,
                         highlightbackground=c)
                for ch in f.winfo_children():
                    if isinstance(ch, tk.Label):
                        ch.config(bg=HL_BG)

            def _leave(_, f=chip, c=color):
                f.config(bg=C["card"],
                         highlightbackground=c)
                for ch in f.winfo_children():
                    if isinstance(ch, tk.Label):
                        ch.config(bg=C["card"])

            for w in (chip, lbl):
                w.bind("<Enter>", _enter, add="+")
                w.bind("<Leave>", _leave, add="+")

            # ── 悬浮说明 Tooltip ──────────────────────────
            desc = get_phrase_desc(phrase)
            if not desc:
                # 自定义词条给一个通用占位说明
                desc = (
                    "🔧 自定义词条\n\n"
                    "点击「➕」将此词条追加到主输入框末尾，\n"
                    "与其他词条用逗号自动分隔。"
                )
            # 以 PhrasePanel 窗口自身作为 root，确保 after 调度在正确线程
            tip = _PhraseTooltip(
                root=self,
                widget=chip,
                phrase=phrase,
                desc=desc,
            )
            # 同时挂到 lbl，覆盖 lbl 内部的 Enter/Leave
            tip.attach(lbl)
            self._tips.append(tip)          # 防 GC

            self._chip_btns.append(chip)

        # 底部汇总说明
        if not search_mode:
            tk.Label(self._chip_inner,
                     text=(f"共 {len(phrases)} 条词条  "
                           "·  点击词条追加到输入框  "
                           "·  🖱 悬停查看中文说明"),
                     font=F["small_i"],
                     bg=C["bg"], fg=C["sub"]
                     ).grid(row=(len(phrases) - 1) // 3 + 1,
                            column=0, columnspan=3,
                            sticky="w", padx=8, pady=(8, 4))

    # ── 追加词条 ─────────────────────────────────────────────
    def _append_to_input(self, phrase: str):
        try:
            cur = self.app.pt.get("1.0", "end-1c").strip()
            sep = ", " if cur and not cur.endswith(",") else ""
            self.app.pt.insert("end", f"{sep}{phrase}")
            # 闪烁反馈
            orig = self.app.pt.cget("bg")
            self.app.pt.config(bg="#1a3a1a")
            self.app.root.after(250,
                                lambda: self.app.pt.config(bg=orig))
            self.app._log(f"📚 追加词条: {phrase}")
            # 同步更新字符计数器
            try: self.app._update_char_count()
            except Exception: pass
        except Exception:
            pass

    def _add_phrase(self):
        phrase = self._new_phrase_var.get().strip()
        if not phrase:
            messagebox.showwarning("提示", "请输入词条内容",
                                   parent=self); return
        if not self._cur_cat:
            messagebox.showwarning("提示", "请先选择分类",
                                   parent=self); return
        add_custom_phrase(self._cur_cat, phrase)
        self._new_phrase_var.set("")
        self._reload()
        self.app._log(f"📚 新建词条: [{self._cur_cat}] {phrase}")

    def _on_close(self):
        # 关闭所有悬浮窗
        for tip in self._tips:
            try: tip._close()
            except Exception: pass
        self._tips.clear()
        try:   self.app._phrase_panel = None
        except Exception: pass
        self.destroy()
