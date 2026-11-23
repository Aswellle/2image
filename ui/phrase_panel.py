"""
ui/phrase_panel.py  v2
──────────────────────
提示词片段库对话框（Toplevel，非模态）。

  v2 新增 ── 词条悬浮说明提示框（_PhraseTooltip）
    · 悬停延迟与淡入时长见 ui/tooltip.py（与侧栏气泡提示共用）
    · 悬浮窗：紫色细边框 + 深色背景 + 词条英文高亮标题 + 中文正文
    · wraplength=280，最大宽度约 300px，不会遮挡太多内容
    · 鼠标离开 / 点击 → 立即消失（0 延迟）
    · 全局唯一：同时只有一个提示框可见
    · 位置自动贴近鼠标右下 14px，并防止超出屏幕边界
"""

import re

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from services.phrase_library import (
    get_phrase_usage,
    phrase_category_display,
    phrase_matches,
    record_phrase_use,
    get_all_phrases,
    add_category,
    add_custom_phrase,
    delete_custom_phrase,
    is_builtin,
    get_custom_desc,
    get_phrase_desc,
    set_custom_desc,
)
from data.repository import get_phrase_stats
from config.fonts import F
from config.theme import DARK_THEME as C
from ui.icons import glyph, icon_font
from config.i18n import _
from ui.tooltip import DELAY_MS as TIP_DELAY_MS
from ui.tooltip import attach_tooltip
from ui.tooltip import FADE_FRAME_MS, FADE_FRAMES, MAX_ALPHA as TIP_MAX_ALPHA
from config.ui_geometry import fit_to_workarea, scaled
from ui.tooltip import fade_alpha


_CAT_COLORS = {
    "✨ 画质增强": C["keep_bg"],
    "💡 光影效果": "#92400e",
    "🎨 艺术风格": C["purple"],
    "📐 构图方式": C["acc"],
    "📷 镜头参数": C["cmp_a"],
    "🌙 氛围情绪": C["cmp_b"],
    "👤 人物细节": "#0369a1",
}


def _template_var_names(phrase: str) -> list[str]:
    """提取词条中的 {{变量}} 占位符名（去重保序）。

    变量名支持任意非花括号内容（含中文），追加时弹对话框逐项填写。
    """
    names: list[str] = []
    for m in re.finditer(r"\{\{([^{}]+)\}\}", phrase):
        n = m.group(1).strip()
        if n and n not in names:
            names.append(n)
    return names


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

    _current: "_PhraseTooltip | None" = None  # 当前可见的唯一实例

    # ── 动画常量（与侧栏气泡提示共用，见 ui/tooltip.py）────────
    _DELAY_MS = TIP_DELAY_MS
    _FRAMES = FADE_FRAMES
    _FRAME_MS = FADE_FRAME_MS
    _MAX_ALPHA = TIP_MAX_ALPHA

    def __init__(self, root: tk.Misc, widget: tk.Widget, phrase: str, desc: str, stats_fn=None):
        self._root = root
        self._widget = widget
        self._phrase = phrase
        self._desc = desc
        self._stats_fn = stats_fn  # 懒查询生成记录使用概况：悬停时才调用

        self._win = None  # Toplevel
        self._show_id = None  # after ID：延迟显示计时器
        self._fade_id = None  # after ID：淡入动画计时器

        # 绑定到传入的 widget
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<Button-1>", self._on_click, add="+")

    # ── 绑定额外 widget（如同一张卡片内的 Label）───────────────
    def attach(self, widget: tk.Widget):
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
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
                try:
                    self._root.after_cancel(jid)
                except Exception:
                    pass
            setattr(self, attr, None)

    # ── 关闭（立即消失）──────────────────────────────────────
    def _close(self):
        self._cancel()
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None
        if _PhraseTooltip._current is self:
            _PhraseTooltip._current = None

    # ── 创建并定位提示窗 ──────────────────────────────────────
    def _open(self):
        self._show_id = None
        if not self._desc:
            return
        try:
            if not self._widget.winfo_exists():
                return
        except Exception:
            return

        # 若已有旧窗先销毁
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass

        tip = tk.Toplevel(self._root)
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        tip.attributes("-alpha", 0.0)  # 完全透明起步
        tip.configure(bg=C["inset"])
        self._win = tip

        # ── 外框（紫色细边框）──────────────────────────────
        border = tk.Frame(tip, bg=C["purple"], highlightbackground=C["purple"], highlightthickness=1)
        border.pack(fill="both", expand=True)

        # 词条英文标题栏
        title_bar = tk.Frame(border, bg="#1e1b4b")
        title_bar.pack(fill="x")
        tk.Label(
            title_bar,
            text=f"  {self._phrase}",
            font=F["badge"],
            bg="#1e1b4b",
            fg=C["purple_soft"],
            padx=6,
            pady=6,
            anchor="w",
        ).pack(fill="x")

        # 分隔线
        tk.Frame(border, bg=C["purple_deep"], height=1).pack(fill="x")

        # 中文说明正文（可追加生成记录使用概况）
        desc_text = self._desc
        if self._stats_fn:
            try:
                extra = self._stats_fn(self._phrase)
            except Exception:
                extra = ""
            if extra:
                desc_text = f"{desc_text}\n\n{extra}"
        tk.Label(
            border,
            text=desc_text,
            font=F["body"],
            bg=C["inset"],
            fg=C["text"],
            wraplength=280,
            justify="left",
            padx=11,
            pady=9,
            anchor="nw",
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
            if px + tw > sw - 6:
                px = self._widget.winfo_pointerx() - tw - 14
            if py + th > sh - 6:
                py = self._widget.winfo_pointery() - th - 14
            px = max(2, px)
            py = max(2, py)
        except Exception:
            px, py = 100, 100
        tip.geometry(f"+{px}+{py}")

        # ── 启动淡入动画 ───────────────────────────────────────
        self._fade_step(tip, 0)

    def _fade_step(self, tip: tk.Toplevel, step: int):
        """缓出曲线淡入（曲线与帧数见 ui/tooltip.py）。"""
        if self._win is not tip:
            return
        try:
            tip.attributes("-alpha", fade_alpha(step))
        except Exception:
            return
        if step < self._FRAMES - 1:
            self._fade_id = self._root.after(self._FRAME_MS, lambda: self._fade_step(tip, step + 1))
        else:
            self._fade_id = None


# ══════════════════════════════════════════════════════════════
#   主面板
# ══════════════════════════════════════════════════════════════
class PhrasePanel(tk.Toplevel):
    """提示词片段库面板（非模态）。"""

    def __init__(self, parent_app):
        super().__init__(parent_app.root)
        self.app = parent_app
        self._phrases = {}
        self._cur_cat = None
        self._chip_btns = []
        self._tips: list[_PhraseTooltip] = []  # 持有引用防 GC
        self._usage_cache: dict[str, str] = {}  # 悬停使用概况缓存：同词条只扫一次历史表

        self.title(_("phrase_title"))
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.minsize(scaled(self, 640), scaled(self, 460))

        # 窗口几何按缩放系数放大并钳制屏幕
        self.update_idletasks()
        pw, ph = fit_to_workarea(self, scaled(self, 820), scaled(self, 560))
        rx = parent_app.root.winfo_x() + (parent_app.root.winfo_width() - pw) // 2
        ry = parent_app.root.winfo_y() + (parent_app.root.winfo_height() - ph) // 2
        self.geometry(f"{pw}x{ph}+{max(0, rx)}+{max(0, ry)}")

        self._build()
        self.bind("<Escape>", lambda _e: self._on_close())
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.lift()
        self.focus_force()

    # ── 构建 UI ──────────────────────────────────────────────
    def _build(self):
        # ── 顶部标题栏 ────────────────────────────────────────
        hdr = tk.Frame(self, bg=C["purple"])
        hdr.pack(fill="x")
        tk.Label(hdr, text=_("phrase_title"), font=F["h1"], bg=C["purple"], fg="white").pack(
            side="left", padx=14, pady=10
        )
        tk.Label(hdr, text=_("phrase_hint"), font=F["small"], bg=C["purple"], fg=C["purple_soft"]).pack(
            side="left", padx=4
        )

        # ── 搜索栏 ────────────────────────────────────────────
        sf = tk.Frame(self, bg=C["panel"])
        sf.pack(fill="x")
        tk.Label(sf, text=glyph("search"), font=icon_font(11), bg=C["panel"], fg=C["sub"]).pack(
            side="left", padx=(10, 4), pady=8
        )
        self._sv = tk.StringVar()
        self._sv.trace("w", lambda *_: self._apply_search())
        _sef = tk.Frame(sf, bg=C["entry"], highlightbackground=C["ok"], highlightthickness=1)
        _sef.pack(side="left", pady=6, padx=(0, 8))
        _se = tk.Entry(
            _sef,
            textvariable=self._sv,
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
            width=28,
        )
        _se.pack(fill="x", padx=4, ipady=4)
        _se.bind("<FocusIn>", lambda _: _sef.config(highlightbackground=C["entry"]), add="+")
        _se.bind("<FocusOut>", lambda _: _sef.config(highlightbackground=C["ok"]), add="+")
        tk.Button(
            sf,
            text=_("btn_clear_search"),
            font=F["small"],
            bg=C["panel"],
            fg=C["sub"],
            bd=0,
            padx=8,
            cursor="hand2",
            command=lambda: self._sv.set(""),
        ).pack(side="left")

        # ── 主体（左右分栏）──────────────────────────────────
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True)

        # 左：分类列表（宽度走缩放体系：高 DPI 下相对宽度不缩水；
        # 英文分类名最长约 175px，200px 基准宽可完整显示）
        left = tk.Frame(body, bg=C["panel"], width=scaled(self, 200))
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Label(left, text=_("lbl_category"), font=F["body_b"], bg=C["panel"], fg=C["sub"]).pack(
            anchor="w", padx=10, pady=(8, 4)
        )
        tk.Frame(left, bg=C["sep"], height=1).pack(fill="x")
        # 底部固定：新建分类入口（先于弹性列表 pack，占住底边不被挤出）
        add_cat_f = tk.Frame(left, bg=C["panel"])
        add_cat_f.pack(side="bottom", fill="x")
        tk.Frame(add_cat_f, bg=C["sep"], height=1).pack(fill="x")
        tk.Button(
            add_cat_f,
            text=_("phrase_new_category"),
            font=F["small_b"],
            bg=C["panel"],
            fg=C["sub"],
            bd=0,
            padx=10,
            pady=7,
            cursor="hand2",
            anchor="w",
            command=self._new_category,
        ).pack(fill="x", padx=4, pady=(2, 4))
        self._cat_frame = tk.Frame(left, bg=C["panel"])
        self._cat_frame.pack(fill="both", expand=True)

        # 右：词条区（可滚动）
        right = tk.Frame(body, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)
        chip_host = tk.Frame(right, bg=C["bg"])
        chip_host.pack(fill="both", expand=True, padx=8, pady=8)

        self._chip_cv = tk.Canvas(chip_host, bg=C["bg"], bd=0, highlightthickness=0)
        vsb = ttk.Scrollbar(chip_host, orient="vertical", command=self._chip_cv.yview)
        self._chip_cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._chip_cv.pack(side="left", fill="both", expand=True)

        self._chip_inner = tk.Frame(self._chip_cv, bg=C["bg"])
        _cw = self._chip_cv.create_window((0, 0), window=self._chip_inner, anchor="nw")
        self._chip_inner.bind("<Configure>", lambda e: self._chip_cv.configure(scrollregion=self._chip_cv.bbox("all")))
        # 词条文本换行宽度随窗口宽度自适应（三列布局），宽窗口不再提前折行
        self._chip_lbls: list[tk.Label] = []
        self._chip_wl = 200
        self._wrap_pad = 70  # 预扣右侧按钮区 + 内边距；搜索模式另有分类标注会更宽

        def _on_chip_resize(e):
            self._chip_cv.itemconfig(_cw, width=e.width)
            wl = max(130, (e.width - 40) // 3 - self._wrap_pad)
            if wl != self._chip_wl:
                self._chip_wl = wl
                for lbl in self._chip_lbls:
                    lbl.config(wraplength=wl)

        self._chip_cv.bind("<Configure>", _on_chip_resize)
        # 鼠标滚轮
        for seq, delta in (("<MouseWheel>", None), ("<Button-4>", -1), ("<Button-5>", 1)):
            if delta is None:
                self._chip_cv.bind(seq, lambda e: self._chip_cv.yview_scroll(int(-1 * (e.delta / 120)), "units"))
            else:
                self._chip_cv.bind(seq, lambda e, d=delta: self._chip_cv.yview_scroll(d, "units"))

        # ── 底部：添加自定义词条 ──────────────────────────────
        bot = tk.Frame(self, bg=C["panel"])
        bot.pack(fill="x")
        tk.Frame(bot, bg=C["sep"], height=1).pack(fill="x")
        add_row = tk.Frame(bot, bg=C["panel"])
        add_row.pack(fill="x", padx=10, pady=8)
        tk.Label(add_row, text=_("lbl_new_phrase"), font=F["body_b"], bg=C["panel"], fg=C["sub"]).pack(side="left")
        nef = tk.Frame(add_row, bg=C["entry"], highlightbackground=C["ok"], highlightthickness=1)
        nef.pack(side="left", fill="x", expand=True, padx=(4, 6))
        self._new_phrase_var = tk.StringVar()
        _ne = tk.Entry(
            nef,
            textvariable=self._new_phrase_var,
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        _ne.pack(fill="x", padx=8, ipady=5)
        _ne.bind("<FocusIn>", lambda _: nef.config(highlightbackground=C["entry"]), add="+")
        _ne.bind("<FocusOut>", lambda _: nef.config(highlightbackground=C["ok"]), add="+")
        self._add_btn = tk.Button(
            add_row,
            text=_("btn_add_to_category"),
            font=F["body"],
            bg=C["ok"],
            fg=C["ok_fg"],
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._add_phrase,
        )
        self._add_btn.pack(side="left")
        tk.Button(
            add_row,
            text=_("phrase_export_btn"),
            font=F["body"],
            bg=C["panel"],
            fg=C["sub"],
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._export_phrases,
        ).pack(side="right")
        tk.Button(
            add_row,
            text=_("phrase_import_btn"),
            font=F["body"],
            bg=C["panel"],
            fg=C["sub"],
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._import_phrases,
        ).pack(side="right", padx=(0, 8))

        self._reload()

    # ── 数据 & 分类刷新 ─────────────────────────────────────
    def refresh(self):
        """公共刷新入口：供词库面板外的模块（侧栏一键收藏等）触发重载。"""
        self._reload()

    def _reload(self):
        self._phrases = get_all_phrases()
        # 按使用频次降序稳定排序（同频保持原序）：高频词条置顶少翻找
        usage = get_phrase_usage()
        for cat, items in self._phrases.items():
            items.sort(key=lambda phrase: -usage.get(phrase, 0))
        self._rebuild_cats()
        cats = list(self._phrases.keys())
        if cats:
            self._select_cat(cats[0])

    def _rebuild_cats(self, searching: bool = False):
        for w in self._cat_frame.winfo_children():
            w.destroy()
        for cat in self._phrases.keys():
            color = _CAT_COLORS.get(cat, C["acc"])
            cat_label = phrase_category_display(cat)
            # 跨分类搜索期间不显示任何选中分类：结果横跨所有分类，
            # 残留高亮会让用户误以为结果来自该分类
            is_sel = cat == self._cur_cat and not searching
            tk.Button(
                self._cat_frame,
                text=cat_label,
                font=(F["_sans"], 10, "bold" if is_sel else ""),
                bg=color if is_sel else C["panel"],
                fg="white",
                bd=0,
                padx=10,
                pady=7,
                anchor="w",
                justify="left",
                # 超长自定义/导入分类名自动换行，不再被固定宽左栏裁切
                wraplength=scaled(self, 168),
                cursor="hand2",
                relief="flat",
                command=lambda c=cat: self._select_cat(c),
            ).pack(fill="x")
            cnt = len(self._phrases.get(cat, []))
            tk.Label(
                self._cat_frame, text=_("lbl_count_items", n=cnt), font=F["tiny"], bg=C["panel"], fg=C["sub"]
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
        # 搜索结果携带 (分类, 词条) 对：删除操作需要真实归属分类；
        # 词条说明（中英双语）也参与匹配
        results = [(cat, p) for cat, phrases in self._phrases.items() for p in phrases if phrase_matches(p, kw)]
        self._rebuild_cats(searching=True)
        self._render_chips(results, search_mode=True)

    # ── 词条渲染（含悬浮说明绑定）───────────────────────────
    def _render_chips(self, phrases: list, search_mode: bool = False):
        # 清理旧 tooltip（立即关闭任何可见的）
        for tip in self._tips:
            try:
                tip._close()
            except Exception:
                pass
        self._tips.clear()

        for w in self._chip_inner.winfo_children():
            w.destroy()
        self._chip_btns.clear()
        self._chip_lbls.clear()
        self._chip_cv.yview_moveto(0)

        # 搜索模式下无「当前分类」上下文：禁用新增按钮，防止写入用户看不到的分类
        if getattr(self, "_add_btn", None) is not None:
            self._add_btn.config(state="disabled" if search_mode else "normal")
        # 搜索模式卡片内有分类标注，换行宽度需多预留其宽度
        self._wrap_pad = 150 if search_mode else 70
        # 按当前画布实际宽度即时重算，不依赖下次 Configure 事件
        cv_w = self._chip_cv.winfo_width()
        if cv_w > 1:
            self._chip_wl = max(130, (cv_w - 40) // 3 - self._wrap_pad)

        if not phrases:
            if search_mode:
                # 搜索空态就近给出恢复动作：一键清除搜索
                box = tk.Frame(self._chip_inner, bg=C["bg"])
                box.pack(pady=24, anchor="w", padx=16)
                tk.Label(
                    box, text=_("empty_no_match_results"), font=(F["_sans"], 11, "italic"), bg=C["bg"], fg=C["sub"]
                ).pack(anchor="w")
                tk.Button(
                    box,
                    text=_("btn_clear_search"),
                    font=F["body"],
                    bg=C["panel"],
                    fg=C["sub"],
                    bd=0,
                    padx=10,
                    pady=5,
                    cursor="hand2",
                    command=lambda: self._sv.set(""),
                ).pack(anchor="w", pady=(10, 0))
            else:
                tk.Label(
                    self._chip_inner,
                    text=_("empty_no_phrases"),
                    font=(F["_sans"], 11, "italic"),
                    bg=C["bg"],
                    fg=C["sub"],
                ).pack(pady=24, anchor="w", padx=16)
            return

        base_color = _CAT_COLORS.get(self._cur_cat, C["acc"]) if not search_mode else C["acc"]
        HL_BG = C["card_hl"]  # 悬停背景色

        # 常规模式为词条列表（归属当前分类）；搜索模式为 (分类, 词条) 对
        if search_mode:
            pairs = list(phrases)
        else:
            cat_now = self._cur_cat or ""
            pairs = [(cat_now, p) for p in phrases]

        for i, (cat, phrase) in enumerate(pairs):
            row_idx, col_idx = divmod(i, 3)
            self._chip_inner.columnconfigure(col_idx, weight=1)

            # 搜索模式：边框与追加按钮按词条真实归属分类着色，颜色即来源提示
            color = _CAT_COLORS.get(cat, C["acc"]) if search_mode else base_color

            # ── 卡片主框 ──────────────────────────────────
            chip = tk.Frame(self._chip_inner, bg=C["card"], highlightbackground=color, highlightthickness=1)
            chip.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="ew")

            # ── 分类归属标注（仅搜索模式）──────────────────
            cat_lbl = None
            if search_mode:
                cat_lbl = tk.Label(
                    chip, text=phrase_category_display(cat), font=F["tiny"], bg=C["card"], fg=C["sub"], anchor="w"
                )
                cat_lbl.pack(side="left", padx=(8, 2))

            # ── 词条文字 label ─────────────────────────────
            lbl = tk.Label(
                chip,
                text=phrase,
                font=F["body"],
                bg=C["card"],
                fg=C["text"],
                wraplength=self._chip_wl,
                justify="left",
                anchor="w",
            )
            lbl.pack(side="left", fill="x", expand=True, padx=8, pady=6)
            self._chip_lbls.append(lbl)

            # ── 追加按钮 ───────────────────────────────────
            append_btn = tk.Button(
                chip,
                text=glyph("add"),
                font=icon_font(10),
                bg=color,
                fg="white",
                bd=0,
                padx=6,
                pady=3,
                cursor="hand2",
                command=lambda p=phrase: self._append_to_input(p),
            )
            append_btn.pack(side="right", padx=4, pady=4)
            attach_tooltip(append_btn, "tip_append_phrase")

            # ── 删除按钮（仅自定义词条）───────────────────
            if not is_builtin(cat, phrase):

                def _del(c=cat, p=phrase):
                    if messagebox.askyesno(
                        _("dlg_delete_phrase_title"),
                        _("dlg_delete_phrase_body", name=p),
                        parent=self,
                        default=messagebox.NO,
                    ):
                        delete_custom_phrase(c, p)
                        self._reload()

                del_phrase_btn = tk.Button(
                    chip,
                    text=glyph("trash"),
                    font=icon_font(9),
                    bg=C["card"],
                    fg=C["neg_fg"],
                    bd=0,
                    padx=4,
                    cursor="hand2",
                    command=_del,
                )
                del_phrase_btn.pack(side="right", padx=2, pady=4)
                attach_tooltip(del_phrase_btn, "tip_delete_phrase")

                # ── 说明编辑按钮（仅自定义词条；内置说明随应用分发不可改）──
                edit_desc_btn = tk.Button(
                    chip,
                    text=glyph("edit"),
                    font=icon_font(9),
                    bg=C["card"],
                    fg=C["sub"],
                    bd=0,
                    padx=4,
                    cursor="hand2",
                    command=lambda p=phrase: self._edit_phrase_desc(p),
                )
                edit_desc_btn.pack(side="right", padx=(0, 2), pady=4)
                attach_tooltip(edit_desc_btn, "tip_edit_phrase_desc")

            # ── 点击整行也追加 ────────────────────────────
            hit_widgets = (chip, lbl, cat_lbl) if cat_lbl is not None else (chip, lbl)
            for w in hit_widgets:
                w.bind("<Button-1>", lambda e, p=phrase: self._append_to_input(p))

            # ── 悬停高亮（chip + 内部所有 Label）─────────
            def _enter(_, f=chip, c=color):
                f.config(bg=HL_BG, highlightbackground=c)
                for ch in f.winfo_children():
                    if isinstance(ch, tk.Label):
                        ch.config(bg=HL_BG)

            def _leave(_, f=chip, c=color):
                f.config(bg=C["card"], highlightbackground=c)
                for ch in f.winfo_children():
                    if isinstance(ch, tk.Label):
                        ch.config(bg=C["card"])

            for w in hit_widgets:
                w.bind("<Enter>", _enter, add="+")
                w.bind("<Leave>", _leave, add="+")

            # ── 悬浮说明 Tooltip ──────────────────────────
            desc = get_phrase_desc(phrase)
            if not desc:
                # 自定义词条给一个通用占位说明
                desc = _("desc_custom_phrase")
            # 以 PhrasePanel 窗口自身作为 root，确保 after 调度在正确线程
            tip = _PhraseTooltip(
                root=self,
                widget=chip,
                phrase=phrase,
                desc=desc,
                stats_fn=self._phrase_usage_line,
            )
            # 同时挂到 lbl，覆盖 lbl 内部的 Enter/Leave
            tip.attach(lbl)
            if cat_lbl is not None:
                tip.attach(cat_lbl)
            self._tips.append(tip)  # 防 GC

            self._chip_btns.append(chip)

        # 底部汇总说明
        if not search_mode:
            tk.Label(
                self._chip_inner, text=_("phrase_footer", n=len(phrases)), font=F["small_i"], bg=C["bg"], fg=C["sub"]
            ).grid(row=(len(phrases) - 1) // 3 + 1, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 4))
        else:
            tk.Label(
                self._chip_inner,
                text=_("phrase_search_count", n=len(phrases)),
                font=F["small_i"],
                bg=C["bg"],
                fg=C["sub"],
            ).grid(row=(len(phrases) - 1) // 3 + 1, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 4))

    # ── 追加词条 ─────────────────────────────────────────────
    def _phrase_usage_line(self, phrase: str) -> str:
        """词条在生成记录中的使用概况（悬浮说明追加行）；无记录返回空串。

        结果按词条缓存（命中与未命中都记）：面板会话内同一词条只扫描一次。
        """
        if phrase in self._usage_cache:
            return self._usage_cache[phrase]
        try:
            stats = get_phrase_stats(phrase)
        except Exception:
            return ""
        line = _("phrase_usage_line", count=stats["count"], last=stats["last"][:10]) if stats else ""
        self._usage_cache[phrase] = line
        return line

    def _append_to_input(self, phrase: str):
        # 模板词条（含 {{变量}} 占位符）先弹填充对话框，填好再追加
        var_names = _template_var_names(phrase)
        if var_names:
            self._open_vars_dialog(phrase, var_names)
            return
        self._insert_phrase_text(phrase)
        record_phrase_use(phrase)
        self.app._log(f"📚 追加词条: {phrase}")

    def _insert_phrase_text(self, text: str):
        """把（可能已填充变量的）词条文本追加进主输入框，带闪烁反馈。"""
        try:
            cur = self.app.pt.get("1.0", "end-1c").strip()
            sep = ", " if cur and not cur.endswith(",") else ""
            self.app.pt.insert("end", f"{sep}{text}")
            # 闪烁反馈
            orig = self.app.pt.cget("bg")
            self.app.pt.config(bg=C["card_fav"])
            self.app.root.after(250, lambda: self.app.pt.config(bg=orig))
            # 同步更新字符计数器
            try:
                self.app._update_char_count()
            except Exception:
                pass
        except Exception:
            pass

    def _open_vars_dialog(self, phrase: str, var_names: list[str]):
        """模板变量填充对话框：逐项填写 {{变量}} 后追加到主输入框。"""
        dlg = tk.Toplevel(self)
        dlg.title(_("phrase_vars_title"))
        dlg.configure(bg=C["panel"])
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        tk.Label(
            dlg, text=_("phrase_vars_hint"), font=F["small"], bg=C["panel"], fg=C["sub"], wraplength=340, justify="left"
        ).pack(padx=14, pady=(12, 6), anchor="w")
        # 词条原文预览（等宽小字，占位符一目了然）
        tk.Label(
            dlg,
            text=phrase,
            font=F["small"],
            bg=C["inset"],
            fg=C["text"],
            wraplength=340,
            justify="left",
            padx=8,
            pady=6,
        ).pack(fill="x", padx=14)

        entries: dict[str, tk.Entry] = {}
        for name in var_names:
            row = tk.Frame(dlg, bg=C["panel"])
            row.pack(fill="x", padx=14, pady=(8, 0))
            tk.Label(row, text=name, font=F["body_b"], bg=C["panel"], fg=C["ok"], width=14, anchor="w").pack(
                side="left"
            )
            wrap = tk.Frame(row, bg=C["entry"], highlightbackground=C["ok"], highlightthickness=1)
            wrap.pack(side="left", fill="x", expand=True)
            ent = tk.Entry(
                wrap, bg=C["entry"], fg=C["text"], insertbackground="white", font=F["input"], bd=0, relief="flat"
            )
            ent.pack(fill="x", padx=6, ipady=4)
            entries[name] = ent

        def _confirm(_event=None):
            values: dict[str, str] = {}
            for name, ent in entries.items():
                v = ent.get().strip()
                if not v:
                    messagebox.showwarning(_("dlg_tip"), _("phrase_vars_missing"), parent=dlg)
                    ent.focus_set()
                    return
                values[name] = v
            filled = re.sub(r"\{\{([^{}]+)\}\}", lambda m: values.get(m.group(1).strip(), m.group(0)), phrase)
            dlg.destroy()
            self._insert_phrase_text(filled)
            record_phrase_use(phrase)
            self.app._log(f"📚 追加词条: {filled}")

        def _cancel(_=None):
            dlg.destroy()

        btns = tk.Frame(dlg, bg=C["panel"])
        btns.pack(fill="x", padx=14, pady=12)
        tk.Button(
            btns,
            text=_("phrase_vars_append"),
            font=F["body_b"],
            bg=C["ok"],
            fg=C["ok_fg"],
            bd=0,
            padx=14,
            pady=5,
            cursor="hand2",
            command=_confirm,
        ).pack(side="right")
        tk.Button(
            btns,
            text=_("btn_cancel"),
            font=F["body"],
            bg=C["panel"],
            fg=C["sub"],
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=_cancel,
        ).pack(side="right", padx=(0, 8))

        dlg.bind("<Return>", _confirm)
        dlg.bind("<Escape>", _cancel)
        dlg.protocol("WM_DELETE_WINDOW", _cancel)
        if entries:
            entries[var_names[0]].focus_set()
        # 居中于词库面板
        dlg.update_idletasks()
        dw, dh = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
        px = self.winfo_x() + max(0, (self.winfo_width() - dw) // 2)
        py = self.winfo_y() + max(0, (self.winfo_height() - dh) // 2)
        dlg.geometry(f"{dw}x{dh}+{px}+{py}")

    def _new_category(self):
        """新建自定义分类：命名后立即可在下方添加词条。"""
        dlg = tk.Toplevel(self)
        dlg.title(_("phrase_new_category"))
        dlg.configure(bg=C["panel"])
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)

        tk.Label(
            dlg,
            text=_("phrase_new_category_hint"),
            font=F["small"],
            bg=C["panel"],
            fg=C["sub"],
            wraplength=280,
            justify="left",
        ).pack(padx=14, pady=(12, 8), anchor="w")
        wrap = tk.Frame(dlg, bg=C["entry"], highlightbackground=C["ok"], highlightthickness=1)
        wrap.pack(fill="x", padx=14)
        ent = tk.Entry(
            wrap, bg=C["entry"], fg=C["text"], insertbackground="white", font=F["input"], bd=0, relief="flat"
        )
        ent.pack(fill="x", padx=6, ipady=4)

        def _confirm(_event=None):
            name = ent.get().strip()
            if not name:
                messagebox.showwarning(_("dlg_tip"), _("phrase_category_empty"), parent=dlg)
                return
            if not add_category(name):
                messagebox.showwarning(_("dlg_tip"), _("phrase_category_exists"), parent=dlg)
                return
            dlg.destroy()
            self._reload()
            self._select_cat(name)
            self.app._log(f"📚 新建分类: {name}")

        def _cancel(_=None):
            dlg.destroy()

        btns = tk.Frame(dlg, bg=C["panel"])
        btns.pack(fill="x", padx=14, pady=12)
        tk.Button(
            btns,
            text=_("phrase_category_create"),
            font=F["body_b"],
            bg=C["ok"],
            fg=C["ok_fg"],
            bd=0,
            padx=14,
            pady=5,
            cursor="hand2",
            command=_confirm,
        ).pack(side="right")
        tk.Button(
            btns,
            text=_("btn_cancel"),
            font=F["body"],
            bg=C["panel"],
            fg=C["sub"],
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=_cancel,
        ).pack(side="right", padx=(0, 8))
        dlg.bind("<Return>", _confirm)
        dlg.bind("<Escape>", _cancel)
        dlg.protocol("WM_DELETE_WINDOW", _cancel)
        ent.focus_set()
        dlg.update_idletasks()
        px = self.winfo_x() + max(0, (self.winfo_width() - dlg.winfo_width()) // 2)
        py = self.winfo_y() + max(0, (self.winfo_height() - dlg.winfo_height()) // 2)
        dlg.geometry(f"+{px}+{py}")

    def _edit_phrase_desc(self, phrase: str):
        """编辑自定义词条的说明文本（显示在悬浮提示里；随导出文件迁移）。"""
        dlg = tk.Toplevel(self)
        dlg.title(_("phrase_desc_title"))
        dlg.configure(bg=C["panel"])
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(True, True)
        dlg.minsize(scaled(self, 420), scaled(self, 280))

        tk.Label(dlg, text=phrase, font=F["body_b"], bg=C["panel"], fg=C["ok"], wraplength=390, justify="left").pack(
            padx=14, pady=(12, 6), anchor="w"
        )
        tk.Label(
            dlg,
            text=_("phrase_desc_hint"),
            font=F["small_i"],
            bg=C["panel"],
            fg=C["sub"],
            wraplength=390,
            justify="left",
        ).pack(padx=14, pady=(0, 6), anchor="w")
        body = tk.Frame(dlg, bg=C["entry"], highlightbackground=C["ok"], highlightthickness=1)
        body.pack(fill="both", expand=True, padx=14)
        txt = tk.Text(
            body,
            wrap="word",
            font=F["body"],
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            bd=0,
            padx=8,
            pady=6,
            relief="flat",
            height=6,
        )
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", get_custom_desc(phrase))

        def _save(_event=None):
            set_custom_desc(phrase, txt.get("1.0", "end-1c"))
            dlg.destroy()
            self.app._toast(_("phrase_desc_saved"), "success")

        def _cancel(_=None):
            dlg.destroy()

        btns = tk.Frame(dlg, bg=C["panel"])
        btns.pack(fill="x", padx=14, pady=12)
        tk.Button(
            btns,
            text=_("phrase_desc_save"),
            font=F["body_b"],
            bg=C["ok"],
            fg=C["ok_fg"],
            bd=0,
            padx=14,
            pady=5,
            cursor="hand2",
            command=_save,
        ).pack(side="right")
        tk.Button(
            btns,
            text=_("btn_cancel"),
            font=F["body"],
            bg=C["panel"],
            fg=C["sub"],
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=_cancel,
        ).pack(side="right", padx=(0, 8))
        dlg.bind("<Escape>", _cancel)
        dlg.protocol("WM_DELETE_WINDOW", _cancel)
        dlg.bind("<Control-s>", _save)
        txt.focus_set()
        # 居中于词库面板
        dlg.update_idletasks()
        px = self.winfo_x() + max(0, (self.winfo_width() - dlg.winfo_width()) // 2)
        py = self.winfo_y() + max(0, (self.winfo_height() - dlg.winfo_height()) // 2)
        dlg.geometry(f"+{px}+{py}")

    def _add_phrase(self):
        phrase = self._new_phrase_var.get().strip()
        if not phrase:
            messagebox.showwarning(_("dlg_tip"), _("dlg_enter_phrase"), parent=self)
            return
        if not self._cur_cat:
            messagebox.showwarning(_("dlg_tip"), _("dlg_select_category"), parent=self)
            return
        if not add_custom_phrase(self._cur_cat, phrase):
            # 重复（自定义或内置同分类）：明确告知而不是静默清空输入框
            messagebox.showinfo(_("dlg_tip"), _("phrase_dup_exists"), parent=self)
            return
        self._new_phrase_var.set("")
        self._reload()
        self.app._log(f"📚 新建词条: [{self._cur_cat}] {phrase}")

    def _export_phrases(self):
        """自定义词库导出为 JSON 文件（换机/备份）。"""
        from services.phrase_library import export_custom

        path = filedialog.asksaveasfilename(
            title=_("phrase_export_btn"),
            defaultextension=".json",
            initialfile="phrase_library.json",
            filetypes=[("JSON", "*.json")],
            parent=self,
        )
        if not path:
            return
        total = export_custom(path)
        messagebox.showinfo(_("dlg_tip"), _("phrase_export_done", total=total, path=path), parent=self)
        self.app._log(f"📚 词库导出: {total} 条 → {path}")

    def _import_phrases(self):
        """从 JSON 文件合并导入自定义词条（已存在/内置的跳过）。"""
        from services.phrase_library import import_custom

        path = filedialog.askopenfilename(
            title=_("phrase_import_btn"),
            filetypes=[("JSON", "*.json")],
            parent=self,
        )
        if not path:
            return
        try:
            added, skipped = import_custom(path)
        except Exception:
            messagebox.showerror(_("dlg_tip"), _("phrase_import_invalid"), parent=self)
            return
        self._reload()
        messagebox.showinfo(_("dlg_tip"), _("phrase_import_done", added=added, skipped=skipped), parent=self)
        self.app._log(f"📚 词库导入: +{added} 条（跳过 {skipped}）")

    def _on_close(self):
        # 关闭所有悬浮窗
        for tip in self._tips:
            try:
                tip._close()
            except Exception:
                pass
        self._tips.clear()
        try:
            self.app._phrase_panel = None
        except Exception:
            pass
        self.destroy()
