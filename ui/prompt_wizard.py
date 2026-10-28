"""
ui/prompt_wizard.py  v3
──────────────────────────────────────────────────────────────
重构要点（v3）：

② 左右分区可拖动分隔条
   改用 tk.PanedWindow（orient=horizontal）替代两个固定宽度 Frame，
   内置 sash 拖动调整左右分区宽度，sash 宽 7px，悬停变双向箭头光标。

③ 参数区布局全面重设计
   · _DimRow 改为 grid 布局：
       列 0 = 固定宽图标+文字标签（11pt bold）
       列 1 = ttk.Combobox 自动填满剩余宽度（columnconfigure weight=1）
     彻底解决下拉框宽度不足、文字被截断的问题。
   · 自定义输入展开时的指导文字：("Arial",10,"italic") fg="#89b4fa"（亮蓝）
     在深色背景上对比度高、清晰可辨。
   · 节标题：12pt bold 白色，行距宽松。
   · 窗口默认 1040×860，可缩放，min=780×640。
"""

import random
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from services.prompt_assistant import (
    generate_prompt,
    apply_template,
    TEMPLATES,
    get_templates_by_category,
    prompt_budget_info,
    _trim_to_budget,
)
from config.fonts import F
from config.theme import DARK_THEME as C
from config.i18n import _
from ui.button_states import set_enabled
from ui.wizard_llm import LLMWizard


# ══════════════════════════════════════════════════════════════
#   维度预设数据（模块级只存键名，取词延迟到界面构建/使用时，
#   避免模块导入早于 init_language 把文案冻结在默认语言）
# ══════════════════════════════════════════════════════════════
_CUSTOM_KEY = "wizard_custom_option"


def _presets(keys):
    """键名列表 → 当前语言文案列表。"""
    return [_(k) for k in keys]


STYLE_P = [
    "preset_style_1",
    "preset_style_2",
    "preset_style_3",
    "preset_style_4",
    "preset_style_5",
    "preset_style_6",
    "preset_style_7",
    "preset_style_8",
    "preset_style_9",
    "preset_style_10",
    "preset_style_11",
    "preset_style_12",
    "wizard_custom_option",
]
MOOD_P = [
    "preset_mood_1",
    "preset_mood_2",
    "preset_mood_3",
    "preset_mood_4",
    "preset_mood_5",
    "preset_mood_6",
    "preset_mood_7",
    "preset_mood_8",
    "preset_mood_9",
    "preset_mood_10",
    "preset_mood_11",
    "preset_mood_12",
    "wizard_custom_option",
]
DETAIL_P = [
    "preset_detail_1",
    "preset_detail_2",
    "preset_detail_3",
    "preset_detail_4",
    "preset_detail_5",
    "preset_detail_6",
    "preset_detail_7",
    "preset_detail_8",
    "wizard_custom_option",
]
COMP_P = [
    "preset_comp_1",
    "preset_comp_2",
    "preset_comp_3",
    "preset_comp_4",
    "preset_comp_5",
    "preset_comp_6",
    "preset_comp_7",
    "preset_comp_8",
    "preset_comp_9",
    "preset_comp_10",
    "wizard_custom_option",
]
LIGHT_P = [
    "preset_light_1",
    "preset_light_2",
    "preset_light_3",
    "preset_light_4",
    "preset_light_5",
    "preset_light_6",
    "preset_light_7",
    "preset_light_8",
    "preset_light_9",
    "preset_light_10",
    "wizard_custom_option",
]
CAMERA_P = [
    "preset_camera_1",
    "preset_camera_2",
    "preset_camera_3",
    "preset_camera_4",
    "preset_camera_5",
    "preset_camera_6",
    "preset_camera_7",
    "preset_camera_8",
    "wizard_custom_option",
]
QUALITY_P = [
    "preset_quality_1",
    "preset_quality_2",
    "preset_quality_3",
    "preset_quality_4",
    "preset_quality_5",
    "preset_quality_6",
    "preset_quality_7",
    "preset_quality_8",
    "wizard_custom_option",
]
_RAND_POOLS = {
    "style": [k for k in STYLE_P if k != _CUSTOM_KEY],
    "mood": [k for k in MOOD_P if k != _CUSTOM_KEY],
    "detail": [k for k in DETAIL_P if k != _CUSTOM_KEY],
    "composition": [k for k in COMP_P if k != _CUSTOM_KEY],
    "lighting": [k for k in LIGHT_P if k != _CUSTOM_KEY],
    "camera": [k for k in CAMERA_P if k != _CUSTOM_KEY],
    "quality": [k for k in QUALITY_P if k != _CUSTOM_KEY],
}


# ══════════════════════════════════════════════════════════════
#   _DimRow  v3 —— grid 布局，下拉框自动填满宽度
# ══════════════════════════════════════════════════════════════
class _DimRow:
    """
    一行维度参数。布局使用 grid：
      列 0  图标+标签（固定宽，右对齐）
      列 1  ttk.Combobox（weight=1，自动填满剩余宽度）
    选"自定义…"时在本行下方展开：
      · 全宽输入框（Entry）
      · 指导文字（亮蓝色，10pt italic，清晰可辨）
    """

    LABEL_W = 9  # 标签列字符宽度（约 8 个汉字）

    def __init__(self, canvas_ref, parent: tk.Frame, label: str, presets: list, guide: str = ""):
        self._canvas = canvas_ref  # optional scroll target
        self.var = tk.StringVar(value=presets[0])
        self._custom_v = tk.StringVar()
        self._presets = presets
        self._guide = guide

        # ── 主行容器 ──────────────────────────────────────────
        self._outer = tk.Frame(parent, bg=C["bg"])
        self._outer.pack(fill="x", pady=(0, 2))
        self._outer.columnconfigure(1, weight=1)

        # 标签
        lbl = tk.Label(self._outer, text=label, font=F["btn"], fg=C["sub"], bg=C["bg"], anchor="e", width=self.LABEL_W)
        lbl.grid(row=0, column=0, sticky="e", padx=(0, 8))

        # 下拉框 —— sticky="ew" + columnconfigure weight=1 使其填满
        self._cb = ttk.Combobox(self._outer, textvariable=self.var, values=presets, state="readonly", font=F["input"])
        self._cb.grid(row=0, column=1, sticky="ew")
        self._cb.bind("<<ComboboxSelected>>", self._on_select)

        # ── 自定义展开区（初始隐藏）─────────────────────────────
        self._expand = tk.Frame(parent, bg=C["bg"])
        # 输入框
        cef = tk.Frame(self._expand, bg=C["entry"])
        cef.pack(fill="x", padx=(self.LABEL_W * 8 + 8, 0), pady=(3, 0))
        self._centry = tk.Entry(
            cef,
            textvariable=self._custom_v,
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self._centry.pack(fill="x", padx=10, ipady=6)
        # 指导文字（亮蓝色，italic，清晰）
        if guide:
            tk.Label(
                self._expand,
                text=f"💡  {guide}",
                font=F["body_i"],
                bg=C["bg"],
                fg=C["guide"],
                anchor="w",
                wraplength=520,
                justify="left",
            ).pack(anchor="w", padx=(self.LABEL_W * 8 + 8, 0), pady=(3, 0))

        # Bind scrolling only when the row belongs to a scrollable host.
        if self._canvas is not None:
            self._bind_scroll(lbl, self._cb)

    def _bind_scroll(self, *widgets):
        """把滚动事件从子控件传递到 canvas_ref，使悬停任意控件均可滚动。"""

        def _fwd(e):
            self._canvas.event_generate("<MouseWheel>", delta=e.delta, when="now")

        def _fwd4(e):
            self._canvas.event_generate("<Button-4>", when="now")

        def _fwd5(e):
            self._canvas.event_generate("<Button-5>", when="now")

        for w in widgets:
            w.bind("<MouseWheel>", _fwd, add="+")
            w.bind("<Button-4>", _fwd4, add="+")
            w.bind("<Button-5>", _fwd5, add="+")

    def _on_select(self, _=None):
        if self.var.get() == _("wizard_custom_option"):
            self._expand.pack(fill="x", after=self._outer, pady=(0, 4))
            self._centry.focus_set()
        else:
            self._expand.pack_forget()

    # ── 公共接口 ──────────────────────────────────────────────
    def get_value(self) -> str:
        v = self.var.get()
        return self._custom_v.get().strip() if v == _("wizard_custom_option") else v

    def set_random(self, pool: list):
        self.var.set(random.choice(pool))
        self._expand.pack_forget()

    def reset(self):
        self.var.set(self._presets[0])
        self._custom_v.set("")
        self._expand.pack_forget()


# ══════════════════════════════════════════════════════════════
#   主窗口
# ══════════════════════════════════════════════════════════════
class PromptWizard(tk.Toplevel):
    _TEMPLATE_IDLE = "idle"
    _TEMPLATE_PREVIEWING = "previewing"
    _TEMPLATE_PENDING_FILL = "pending-fill"

    # 键名存类属性，取词在 _set_template_state 运行时进行
    _TEMPLATE_BADGES = {
        _TEMPLATE_IDLE: ("wizard_badge_idle", "#64748b"),
        _TEMPLATE_PREVIEWING: ("wizard_badge_previewing", "#f0a500"),
        _TEMPLATE_PENDING_FILL: ("wizard_badge_pending_fill", C["ok"]),
    }

    def __init__(self, parent_app):
        super().__init__(parent_app.root)
        self.app = parent_app
        self._history = []  # [(label, positive)]
        self._generating = False
        self._anim_id = None
        self._sel_tid = None  # 已选模板 ID
        self._template_state = self._TEMPLATE_IDLE

        self.title(_("wizard_title") + " — " + _("wizard_pro_suffix"))
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        window_w = min(1040, max(780, screen_w - 80))
        window_h = min(860, max(680, screen_h - 48))
        self.geometry(f"{window_w}x{window_h}")
        self.configure(bg=C["bg"])
        self.minsize(780, 680)
        self.resizable(True, True)

        # 居中，并为窗口装饰预留空间，避免底部操作栏落到屏幕外。
        self.update_idletasks()
        rx, ry = parent_app.root.winfo_x(), parent_app.root.winfo_y()
        rw, rh = parent_app.root.winfo_width(), parent_app.root.winfo_height()
        max_x = max(0, screen_w - window_w)
        max_y = max(0, screen_h - window_h - 40)
        x = min(max(0, rx + (rw - window_w) // 2), max_x)
        y = min(max(0, ry + (rh - window_h) // 2), max_y)
        self.geometry(f"{window_w}x{window_h}+{x}+{y}")

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.lift()
        self.focus_force()

    # ══════════════════════════════════════════════════════════
    #   顶层布局
    # ══════════════════════════════════════════════════════════
    def _build(self):
        # ── 标题栏 ─────────────────────────────────────────────
        hdr = tk.Frame(self, bg=C["acc"], height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(
            hdr, text=_("wizard_title") + "  " + _("wizard_pro_suffix"), font=F["disp"], bg=C["acc"], fg="white"
        ).pack(side="left", padx=16, pady=10)
        tk.Label(hdr, text=_("wizard_subtitle"), font=F["body"], bg=C["acc"], fg=C["text_inverse"]).pack(
            side="left", padx=4
        )

        # ── Tab 切换栏 ─────────────────────────────────────────
        tab_bar = tk.Frame(self, bg=C["acc"], height=42)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)
        self._tab_param_btn = tk.Button(
            tab_bar,
            text=_("wizard_param_tab"),
            font=F["btn"],
            bg=C["hl"],
            fg="white",
            bd=0,
            padx=22,
            cursor="hand2",
            command=self._show_param_tab,
        )
        self._tab_param_btn.pack(side="left", fill="y")
        self._tab_tmpl_btn = tk.Button(
            tab_bar,
            text=_("wizard_template_tab"),
            font=F["btn"],
            bg=C["acc"],
            fg=C["text_inverse"],
            bd=0,
            padx=22,
            cursor="hand2",
            command=self._show_tmpl_tab,
        )
        self._tab_tmpl_btn.pack(side="left", fill="y")

        # 右侧：密钥配置按钮 + 状态指示
        self._key_status_btn = tk.Button(
            tab_bar, text="", font=F["small_b"], bd=0, padx=14, cursor="hand2", command=self._open_llm_wizard
        )
        self._key_status_btn.pack(side="right", fill="y", padx=(0, 6))
        self._update_key_status_btn()

        # ── 主体：PanedWindow（左右可拖动分隔）─────────────────
        self._paned = tk.PanedWindow(
            self,
            orient="horizontal",
            sashwidth=7,
            sashcursor="sb_h_double_arrow",
            sashrelief="flat",
            bg=C["sash"],
            handlesize=0,
        )
        self._paned.pack(fill="both", expand=True)

        self._left_host = tk.Frame(self._paned, bg=C["bg"])
        self._right_host = tk.Frame(self._paned, bg=C["panel"])
        self._paned.add(self._left_host, minsize=420, stretch="always")
        self._paned.add(self._right_host, minsize=280, stretch="always")
        # 在窗口显示后设置初始分隔位置
        self.after(50, lambda: self._paned.sash_place(0, 630, 0))

        # 构建左面板（参数页固定、模板页可滚动）
        self._build_left(self._left_host)
        # 构建右面板（结果区）
        self._build_right_panel(self._right_host)

        # 默认显示参数 Tab
        self._param_host.pack(fill="both", expand=True)

    # ══════════════════════════════════════════════════════════
    #   左面板：固定参数页 + 可滚动模板页
    # ══════════════════════════════════════════════════════════
    def _build_left(self, parent):
        self._param_host = tk.Frame(parent, bg=C["bg"])
        self._param_host.rowconfigure(0, weight=1)
        self._param_host.columnconfigure(0, weight=1)
        self._param_frame = tk.Frame(self._param_host, bg=C["bg"])
        self._param_frame.grid(row=0, column=0, sticky="nsew")
        self._build_param_tab(self._param_frame)
        self._build_param_floating_action(self._param_host)

        self._tmpl_host = tk.Frame(parent, bg=C["bg"])
        self._left_canvas = tk.Canvas(self._tmpl_host, bg=C["bg"], bd=0, highlightthickness=0)
        vsb = ttk.Scrollbar(self._tmpl_host, orient="vertical", command=self._left_canvas.yview)
        self._left_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._left_canvas.pack(side="left", fill="both", expand=True)

        self._tmpl_frame = tk.Frame(self._left_canvas, bg=C["bg"])
        window_id = self._left_canvas.create_window((0, 0), window=self._tmpl_frame, anchor="nw")
        self._tmpl_frame.bind(
            "<Configure>", lambda _event: self._left_canvas.configure(scrollregion=self._left_canvas.bbox("all"))
        )
        self._left_canvas.bind("<Configure>", lambda event: self._left_canvas.itemconfig(window_id, width=event.width))

        def _scroll(event):
            if event.delta:
                self._left_canvas.yview_scroll(int(-event.delta / 120), "units")
            elif event.num == 4:
                self._left_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self._left_canvas.yview_scroll(1, "units")
            return "break"

        self._template_scroll = _scroll
        self._left_canvas.bind("<MouseWheel>", _scroll)
        self._left_canvas.bind("<Button-4>", _scroll)
        self._left_canvas.bind("<Button-5>", _scroll)
        self._build_tmpl_tab(self._tmpl_frame)
        self._build_template_floating_action(parent)

    def _build_param_floating_action(self, parent):
        bar = tk.Frame(parent, bg=C["entry"], height=58)
        bar.grid(row=1, column=0, sticky="ew")
        bar.grid_propagate(False)

        self._gen_btn = tk.Button(
            bar,
            text=_("wizard_generate_btn"),
            font=F["h2"],
            bg=C["purple"],
            fg="white",
            bd=0,
            padx=22,
            pady=9,
            cursor="hand2",
            activebackground=C["dpurp"],
            command=self._generate_param,
        )
        self._gen_btn.pack(side="left", padx=(18, 10), pady=10)

        tk.Button(
            bar,
            text=_("wizard_random_all"),
            font=F["body"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=12,
            pady=9,
            cursor="hand2",
            command=self._random_all,
        ).pack(side="left", pady=10)
        tk.Button(
            bar,
            text=_("btn_reset"),
            font=F["body"],
            bg=C["panel"],
            fg=C["sub"],
            bd=0,
            padx=10,
            pady=9,
            cursor="hand2",
            command=self._reset_params,
        ).pack(side="left", padx=(8, 0), pady=10)

        self._param_status = tk.Label(bar, text="", font=F["body"], bg=C["entry"], fg=C["warn"])
        self._param_status.pack(side="left", padx=12)

    def _build_template_floating_action(self, parent):
        """左栏底部固定的模板应用条，不随模板列表滚动。"""
        self._tmpl_action_bar = tk.Frame(parent, bg=C["entry"], height=58)
        self._tmpl_action_bar.pack_propagate(False)

        self._tmpl_apply_btn = tk.Button(
            self._tmpl_action_bar,
            text=_("wizard_apply_template_btn"),
            font=F["body_b"],
            bg=C["surface_disabled"],
            fg=C["text_disabled"],
            bd=0,
            padx=14,
            pady=7,
            cursor="hand2",
            state="disabled",
            activebackground="#047857",
            command=self._apply_template,
        )
        self._tmpl_apply_btn.pack(side="left", padx=12, pady=10)

        self._tmpl_status = tk.Label(
            self._tmpl_action_bar, text="", font=F["small_i"], bg=C["entry"], fg=C["guide"], anchor="w"
        )
        self._tmpl_status.pack(side="left", fill="x", expand=True, padx=(0, 12))

    # ══════════════════════════════════════════════════════════
    #   参数模式 Tab（全面重设计）
    # ══════════════════════════════════════════════════════════
    def _build_param_tab(self, parent):
        PX = 18

        # ── 主题关键词 ─────────────────────────────────────────
        self._sec_label(parent, _("wizard_label_keyword_required"), PX)
        kf = tk.Frame(parent, bg=C["entry"], highlightbackground=C["ok"], highlightthickness=1)
        kf.pack(fill="x", padx=PX, pady=(6, 0))
        self.kw_var = tk.StringVar()
        kw_ent = tk.Entry(
            kf,
            textvariable=self.kw_var,
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["label_lg"],
            bd=0,
            relief="flat",
        )
        kw_ent.pack(fill="x", padx=12, ipady=10)
        kw_ent.bind("<Return>", lambda e: self._generate_param())
        kw_ent.bind("<FocusIn>", lambda _: kf.config(highlightbackground=C["entry"]), add="+")
        kw_ent.bind("<FocusOut>", lambda _: kf.config(highlightbackground=C["ok"]), add="+")
        # 示例提示
        tk.Label(
            parent, text=_("wizard_example_keywords"), font=F["body_i"], bg=C["bg"], fg=C["guide"], anchor="w"
        ).pack(fill="x", padx=PX, pady=(5, 0))

        self._hdivider(parent, PX)

        # ── 7 个维度参数（P1-25 渐进披露：默认只展示风格/氛围）──
        self._sec_label(parent, _("wizard_label_dimensions"), PX)
        cv_ref = None

        dim_host = tk.Frame(parent, bg=C["bg"])
        dim_host.pack(fill="x", padx=PX, pady=(6, 0))

        self._dim_style = _DimRow(cv_ref, dim_host, _("wizard_label_style"), _presets(STYLE_P), guide=_("wizard_guide_style"))
        self._dim_mood = _DimRow(cv_ref, dim_host, _("wizard_label_mood"), _presets(MOOD_P), guide=_("wizard_guide_mood"))

        # 高级维度宿主：默认收起，点击「更多精细控制」展开
        self._adv_host = tk.Frame(dim_host, bg=C["bg"])
        self._hdivider_thin(self._adv_host)
        self._dim_detail = _DimRow(
            cv_ref, self._adv_host, _("wizard_label_detail"), _presets(DETAIL_P), guide=_("wizard_guide_detail")
        )
        self._dim_comp = _DimRow(
            cv_ref, self._adv_host, _("wizard_label_composition"), _presets(COMP_P), guide=_("wizard_guide_composition")
        )
        self._dim_light = _DimRow(
            cv_ref, self._adv_host, _("wizard_label_lighting"), _presets(LIGHT_P), guide=_("wizard_guide_lighting")
        )
        self._dim_cam = _DimRow(
            cv_ref, self._adv_host, _("wizard_label_camera"), _presets(CAMERA_P), guide=_("wizard_guide_camera")
        )
        self._dim_qual = _DimRow(
            cv_ref, self._adv_host, _("wizard_label_quality"), _presets(QUALITY_P), guide=_("wizard_guide_quality")
        )

        self._adv_open = False
        self._adv_toggle = tk.Button(
            dim_host,
            text="▸ " + _("prompt_more_controls"),
            font=F["body"],
            bg=C["bg"],
            fg=C["guide"],
            bd=0,
            cursor="hand2",
            anchor="w",
            command=self._toggle_advanced_dims,
        )
        self._adv_toggle.pack(fill="x", pady=(4, 0))

        self._hdivider(parent, PX)

        # ── 额外补充 ───────────────────────────────────────────
        self._sec_label(parent, _("wizard_label_extra"), PX)
        ef = tk.Frame(parent, bg=C["entry"], highlightbackground=C["ok"], highlightthickness=1)
        ef.pack(fill="x", padx=PX, pady=(6, 0))
        self.extra_var = tk.StringVar()
        _ee = tk.Entry(
            ef,
            textvariable=self.extra_var,
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        _ee.pack(fill="x", padx=10, ipady=7)
        _ee.bind("<FocusIn>", lambda _: ef.config(highlightbackground=C["entry"]), add="+")
        _ee.bind("<FocusOut>", lambda _: ef.config(highlightbackground=C["ok"]), add="+")
        tk.Label(parent, text=_("wizard_example_extra"), font=F["body_i"], bg=C["bg"], fg=C["guide"], anchor="w").pack(
            fill="x", padx=PX, pady=(5, 0)
        )

    # ── 节标题 ─────────────────────────────────────────────────
    def _toggle_advanced_dims(self):
        """P1-25: 展开/收起高级维度（细节/构图/光影/镜头/画质）。"""
        self._adv_open = not self._adv_open
        if self._adv_open:
            self._adv_host.pack(fill="x")
            self._adv_toggle.config(text="▾ " + _("prompt_more_controls"))
        else:
            self._adv_host.pack_forget()
            self._adv_toggle.config(text="▸ " + _("prompt_more_controls"))

    @staticmethod
    def _sec_label(parent, text: str, px: int = 16):
        tk.Label(parent, text=text, font=F["h2"], bg=C["bg"], fg=C["text"], anchor="w").pack(
            fill="x", padx=px, pady=(14, 0)
        )

    @staticmethod
    def _hdivider(parent, px: int = 16):
        tk.Frame(parent, bg=C["sep"], height=1).pack(fill="x", padx=px, pady=(10, 0))

    @staticmethod
    def _hdivider_thin(parent):
        tk.Frame(parent, bg=C["divider"], height=1).pack(fill="x", pady=4)

    # ── 随机 / 重置 ───────────────────────────────────────────
    def _random_all(self):
        for key, dim in [
            ("style", self._dim_style),
            ("mood", self._dim_mood),
            ("detail", self._dim_detail),
            ("composition", self._dim_comp),
            ("lighting", self._dim_light),
            ("camera", self._dim_cam),
            ("quality", self._dim_qual),
        ]:
            dim.set_random(_presets(_RAND_POOLS[key]))

    def _reset_params(self):
        for dim in [
            self._dim_style,
            self._dim_mood,
            self._dim_detail,
            self._dim_comp,
            self._dim_light,
            self._dim_cam,
            self._dim_qual,
        ]:
            dim.reset()
        self.extra_var.set("")

    # ══════════════════════════════════════════════════════════
    #   模板模式 Tab
    # ══════════════════════════════════════════════════════════
    def _build_tmpl_tab(self, parent):
        PX = 18
        self._sec_label(parent, _("wizard_label_keyword_template"), PX)
        tf = tk.Frame(parent, bg=C["entry"], highlightbackground=C["ok"], highlightthickness=1)
        tf.pack(fill="x", padx=PX, pady=(6, 0))
        self.tmpl_kw_var = tk.StringVar()
        tk.Entry(
            tf,
            textvariable=self.tmpl_kw_var,
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["label_lg"],
            bd=0,
            relief="flat",
        ).pack(fill="x", padx=12, ipady=10)
        tk.Label(
            parent, text=_("wizard_example_template_keywords"), font=F["body_i"], bg=C["bg"], fg=C["guide"], anchor="w"
        ).pack(fill="x", padx=PX, pady=(5, 8))

        self._hdivider(parent, PX)

        # 模板卡片列表
        cats = get_templates_by_category()
        cat_colors = {
            "小红书": "#be185d",
            "情绪爆款": "#b45309",
            "知识干货": "#1d4ed8",
            "通用自媒体": "#065f46",
        }
        _cat_translate = {
            "小红书": _("wizard_cat_xiaohongshu"),
            "情绪爆款": _("wizard_cat_emotional"),
            "知识干货": _("wizard_cat_knowledge"),
            "通用自媒体": _("wizard_cat_general"),
        }
        self._tmpl_cards = {}

        for cat, items in cats.items():
            cat_color = cat_colors.get(cat, C["acc"])
            # 分类条
            ch = tk.Frame(parent, bg=cat_color, height=32)
            ch.pack(fill="x", padx=PX, pady=(10, 0))
            ch.pack_propagate(False)
            tk.Label(ch, text=f"  {_cat_translate.get(cat, cat)}", font=F["btn"], bg=cat_color, fg="white").pack(
                side="left", pady=5
            )

            for tid, t in items:
                card = tk.Frame(
                    parent, bg=C["card"], highlightbackground=C["sep"], highlightthickness=1, cursor="hand2"
                )
                card.pack(fill="x", padx=PX, pady=(3, 0))
                self._tmpl_cards[tid] = (card, cat_color)

                top = tk.Frame(card, bg=C["card"])
                top.pack(fill="x", padx=10, pady=(8, 2))
                tk.Label(top, text=t["name"], font=F["btn"], bg=C["card"], fg=C["text"]).pack(side="left")
                tk.Label(top, text=t["size_hint"], font=F["small_b"], bg=C["card"], fg=C["gold"]).pack(side="right")
                tk.Label(card, text=t["desc"], font=F["body"], bg=C["card"], fg=C["sub"], anchor="w").pack(
                    anchor="w", padx=10, pady=(0, 3)
                )
                tk.Label(
                    card, text=f"💡  {t['tips']}", font=F["small_i"], bg=C["card"], fg=C["guide"], anchor="w"
                ).pack(anchor="w", padx=10, pady=(0, 7))

                # Tk 事件不会从 Label 自动冒泡到父 Frame，需把标题行及其
                # 子标签一并绑定，确保卡片任何可见位置点击都可以选中。
                clickable = (
                    [card, top] + list(top.winfo_children()) + [w for w in card.winfo_children() if w is not top]
                )
                for w in clickable:
                    w.bind("<Button-1>", lambda e, i=tid: self._select_tmpl(i))
                    w.bind("<MouseWheel>", self._template_scroll, add="+")
                    w.bind("<Button-4>", self._template_scroll, add="+")
                    w.bind("<Button-5>", self._template_scroll, add="+")

    def _select_tmpl(self, tid: str):
        if self._sel_tid and self._sel_tid in self._tmpl_cards:
            old_card, _ = self._tmpl_cards[self._sel_tid]
            old_card.config(bg=C["card"], highlightbackground=C["sep"])
            for w in old_card.winfo_children():
                try:
                    w.config(bg=C["card"])
                except Exception:
                    pass
        self._sel_tid = tid
        card, cat_color = self._tmpl_cards[tid]
        card.config(bg=C["card_hl"], highlightbackground=cat_color)
        for w in card.winfo_children():
            try:
                w.config(bg=C["card_hl"])
            except Exception:
                pass
        t = TEMPLATES[tid]
        kw = self.tmpl_kw_var.get().strip() or "a subject"
        pos, _ = apply_template(tid, kw, log_cb=self.app._log)
        self._set_result(pos)
        self._set_template_state(self._TEMPLATE_PREVIEWING)
        self._tmpl_status.config(text=_("wizard_previewing", name=t["name"]), fg=C["ok"])

    # ── Tab 切换 ──────────────────────────────────────────────
    def _show_param_tab(self):
        self._param_host.pack(fill="both", expand=True)
        self._tmpl_host.pack_forget()
        self._tmpl_action_bar.pack_forget()
        self._tab_param_btn.config(bg=C["hl"], fg="white")
        self._tab_tmpl_btn.config(bg=C["acc"], fg=C["text_inverse"])

    def _show_tmpl_tab(self):
        self._param_host.pack_forget()
        self._tmpl_action_bar.pack(side="bottom", fill="x")
        self._tmpl_host.pack(fill="both", expand=True)
        self._tab_tmpl_btn.config(bg=C["hl"], fg="white")
        self._tab_param_btn.config(bg=C["acc"], fg=C["text_inverse"])
        self._left_canvas.yview_moveto(0)

    # ══════════════════════════════════════════════════════════
    #   右面板：结果区（不随内容滚动，固定布局）
    # ══════════════════════════════════════════════════════════
    def _build_right_panel(self, parent):
        # ── 顶部固定工具栏（填充按钮始终可见）────────────────────
        top_bar = tk.Frame(parent, bg=C["entry"], height=48)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)
        self._fill_btn = tk.Button(
            top_bar,
            text=_("wizard_use_btn"),
            font=F["btn"],
            bg=C["surface_disabled"],
            fg=C["text_disabled"],
            bd=0,
            padx=18,
            pady=7,
            cursor="hand2",
            state="disabled",
            activebackground="#3aad8a",
            command=self._use_prompt,
        )
        self._fill_btn.pack(side="left", padx=14, pady=8)
        self._template_badge = tk.Label(
            top_bar, text="", font=F["small_b"], bg=C["entry"], fg=C["text_disabled"], padx=8
        )
        self._template_badge.pack(side="right", padx=14)
        self._set_template_state(self._TEMPLATE_IDLE)

        # ── 正面提示词 ─────────────────────────────────────────
        # 标签行：标题 + 实时词数/字符指示器
        pos_hdr = tk.Frame(parent, bg=C["panel"])
        pos_hdr.pack(fill="x", padx=14, pady=(10, 0))
        tk.Label(pos_hdr, text="📋  正面提示词（可编辑）", font=F["btn"], bg=C["panel"], fg=C["ok"]).pack(side="left")
        # 实时词数/字符指示器
        self._budget_lbl = tk.Label(pos_hdr, text="", font=F["mono_sm_b"], bg=C["panel"], fg=C["sub"], padx=8)
        self._budget_lbl.pack(side="right")
        self._clear_btn = tk.Button(
            pos_hdr,
            text=_("wizard_clear_content"),
            font=F["small_b"],
            bg=C["surface_disabled"],
            fg=C["text_disabled"],
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            state="disabled",
            activebackground="#991b1b",
            command=self._clear_template_content,
        )
        self._clear_btn.pack(side="right", padx=(0, 8))

        pos_f = tk.Frame(parent, bg=C["entry"])
        pos_f.pack(fill="both", expand=True, padx=14, pady=(4, 0))
        self._pos_box = tk.Text(
            pos_f,
            font=F["input"],
            bg=C["entry"],
            fg=C["ok"],
            insertbackground=C["ok"],
            wrap="word",
            bd=0,
            padx=10,
            pady=8,
            relief="flat",
        )
        self._pos_box.pack(fill="both", expand=True)
        self._pos_box.insert("1.0", _("wizard_placeholder_prompt"))
        self._pos_box.config(fg=C["keep_bg"])

        # 绑定实时词数更新
        self._pos_box.bind("<<Modified>>", self._on_pos_modified)

        # ── Token 预算控制条（正面提示词下方）─────────────────
        budget_bar = tk.Frame(parent, bg=C["empty"])
        budget_bar.pack(fill="x", padx=14, pady=(2, 0))

        # 右：智能压缩按钮
        self._trim_btn = tk.Button(
            budget_bar,
            text=_("wizard_smart_trim"),
            font=F["small_b"],
            bg=C["card"],
            fg=C["guide"],
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            state="disabled",
            command=self._smart_trim,
        )
        self._trim_btn.pack(side="right", padx=4, pady=2)

        # ── 操作按钮 ───────────────────────────────────────────
        act = tk.Frame(parent, bg=C["panel"])
        act.pack(fill="x", padx=14)
        self._use_btn = tk.Button(
            act,
            text=_("wizard_use_btn"),
            font=F["body_b"],
            bg=C["surface_disabled"],
            fg=C["text_disabled"],
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            state="disabled",
            activebackground="#1a4a7a",
            command=self._use_prompt,
        )
        self._use_btn.pack(side="left")
        tk.Button(
            act,
            text=_("wizard_copy_positive"),
            font=F["body"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=8,
            pady=8,
            cursor="hand2",
            command=lambda: self._copy_box(self._pos_box),
        ).pack(side="left", padx=(8, 0))

        # 状态标签
        self._status_lbl = tk.Label(
            parent, text="", font=F["body"], bg=C["panel"], fg=C["warn"], wraplength=320, justify="left"
        )
        self._status_lbl.pack(anchor="w", padx=14, pady=(8, 0))

        tk.Frame(parent, bg=C["sep"], height=1).pack(fill="x", padx=14, pady=(10, 6))

        # ── 历史记录 ───────────────────────────────────────────
        tk.Label(parent, text=_("wizard_label_session_history"), font=F["body_b"], bg=C["panel"], fg=C["sub"]).pack(
            anchor="w", padx=14
        )
        self._hist_var = tk.StringVar()
        self._hist_cb = ttk.Combobox(parent, textvariable=self._hist_var, state="readonly", font=F["small"])
        self._hist_cb.pack(fill="x", padx=14, pady=(4, 14))
        self._hist_cb.bind("<<ComboboxSelected>>", self._load_history)

    # ══════════════════════════════════════════════════════════
    #   生成逻辑
    # ══════════════════════════════════════════════════════════
    def _generate_param(self):
        if self._generating:
            return
        kw = self.kw_var.get().strip()
        if not kw:
            messagebox.showwarning("提示", _("wizard_warn_no_keyword"), parent=self)
            return

        style = self._dim_style.get_value()
        mood = self._dim_mood.get_value()
        detail = self._dim_detail.get_value()
        comp = self._dim_comp.get_value()
        light = self._dim_light.get_value()
        camera = self._dim_cam.get_value()
        quality = self._dim_qual.get_value()
        extra = self.extra_var.get().strip()

        self._set_generating(True)
        label = _("wizard_label_param_prefix", text=kw[:20])

        def _run():
            try:
                pos, _ = generate_prompt(
                    keywords=kw,
                    cfg=self.app.cfg,
                    style=style,
                    mood=mood,
                    detail=detail,
                    composition=comp,
                    lighting=light,
                    camera=camera,
                    quality=quality,
                    extra=extra,
                    log_cb=self.app._log,
                )
                self.after(0, lambda: self._on_done(pos, label))
            except Exception as ex:
                self.after(0, lambda e=str(ex): self._on_error(e))

        threading.Thread(target=_run, daemon=True).start()

    def _apply_template(self):
        if self._template_state != self._TEMPLATE_PREVIEWING or not self._sel_tid:
            return
        kw = self.tmpl_kw_var.get().strip() or "a subject"
        t = TEMPLATES[self._sel_tid]
        pos, _ignored = apply_template(self._sel_tid, kw, log_cb=self.app._log)
        self._on_done(pos, _("wizard_label_template_prefix", text=t["name"]))
        self._set_template_state(self._TEMPLATE_PENDING_FILL)
        self._tmpl_status.config(text=_("wizard_applied", name=t["name"]), fg=C["ok"])

    def _set_template_state(self, state: str):
        self._template_state = state
        badge_key, badge_fg = self._TEMPLATE_BADGES[state]
        badge_text = _(badge_key)
        is_previewing = state == self._TEMPLATE_PREVIEWING
        is_pending_fill = state == self._TEMPLATE_PENDING_FILL

        for widget_name in ("_template_badge",):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.config(text=badge_text, fg=badge_fg)

        if state == self._TEMPLATE_IDLE:
            status = getattr(self, "_tmpl_status", None)
            if status is not None:
                status.config(text="")

        apply_btn = getattr(self, "_tmpl_apply_btn", None)
        if apply_btn is not None:
            if is_previewing:
                set_enabled(apply_btn, True, bg=C["keep_bg"], fg="white")
            else:
                set_enabled(apply_btn, False, bg=C["surface_disabled"])

        for widget_name in ("_fill_btn", "_use_btn"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                if is_pending_fill:
                    set_enabled(widget, True, bg=C["ok"], fg="#0a1a0a")
                else:
                    set_enabled(widget, False, bg="#334155")

        for widget_name in ("_clear_btn",):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                if is_pending_fill:
                    set_enabled(widget, True, bg=C["dis_bg"], fg=C["neg_fg"])
                else:
                    set_enabled(widget, False, bg=C["surface_disabled"])

    # ── 状态管理 ──────────────────────────────────────────────
    def _set_generating(self, on: bool):
        self._generating = on
        if on:
            set_enabled(self._gen_btn, False, text=_("btn_generating"), bg=C["dpurp"])
            self._start_anim()
        else:
            set_enabled(self._gen_btn, True, text=_("wizard_generate_btn"), bg=C["purple"])
            self._stop_anim()

    def _on_done(self, positive: str, label: str):
        self._stop_anim()
        self._generating = False
        try:
            self._gen_btn.config(state="normal", text=_("wizard_generate_btn"), bg=C["purple"])
        except Exception:
            pass
        self._param_status.config(text=_("wizard_gen_success"), fg=C["ok"])
        self._status_lbl.config(text=_("wizard_gen_done"), fg=C["ok"])
        self.after(3000, lambda: self._param_status.config(text=""))
        self.after(3000, lambda: self._status_lbl.config(text=""))
        self._set_result(positive)
        self._set_template_state(self._TEMPLATE_IDLE)
        self._history.insert(0, (label, positive))
        self._history = self._history[:8]
        self._hist_cb.config(values=[h[0] for h in self._history])
        self.app._log(f"✨ 提示词助手: {positive[:60]}…")

    def _on_error(self, err: str):
        self._stop_anim()
        self._generating = False
        try:
            self._gen_btn.config(state="normal", text=_("wizard_generate_btn"), bg=C["purple"])
        except Exception:
            pass
        self._param_status.config(text=_("wizard_gen_failed"), fg=C["hl"])
        self._status_lbl.config(text=f"❌ {err[:100]}", fg=C["hl"])
        self.app._log(f"✗ 提示词助手: {err}")
        # 缺少密钥时自动弹出配置向导
        if "需要配置 API Key" in err or "API Key" in err:
            self.after(200, self._open_llm_wizard)

    def _set_result(self, pos: str):
        self._pos_box.delete("1.0", "end")
        self._pos_box.insert("1.0", pos)
        self._pos_box.config(fg=C["ok"])
        # 触发词数指示器更新
        self._update_budget_display()

    def _clear_template_content(self):
        self._pos_box.delete("1.0", "end")
        self._pos_box.insert("1.0", _("wizard_placeholder_prompt"))
        self._pos_box.config(fg=C["keep_bg"])
        self._set_template_state(self._TEMPLATE_IDLE)
        self._update_budget_display()
        self._status_lbl.config(text=_("wizard_cleared"), fg=C["sub"])
        self.after(2000, lambda: self._status_lbl.config(text=""))

    def _on_pos_modified(self, _event=None):
        """正面提示词文本框内容变更时触发词数指示器刷新。"""
        try:
            self._pos_box.edit_modified(False)  # 必须重置，否则只触发一次
        except Exception:
            pass
        self.after(50, self._update_budget_display)  # 轻微延迟，确保内容已更新

    def _update_budget_display(self):
        """
        实时更新 Token 预算指示器：
        · 右上角标签：词数/字符数
        · 智能压缩按钮：仅在 >80 词时激活
        """
        try:
            pos = self._pos_box.get("1.0", "end-1c").strip()
        except Exception:
            return

        # 占位文本时不显示计数
        if not pos or "显示在这里" in pos or "AI 生成" in pos:
            self._budget_lbl.config(text="", fg=C["sub"])
            set_enabled(self._trim_btn, False)
            return

        info = prompt_budget_info(pos)

        # ── 词数/字符标签 ───────────────────────────────────────
        self._budget_lbl.config(text=info["label"], fg=info["color"])

        # ── 智能压缩按钮 ────────────────────────────────────────
        if info["status"] == "too_long":
            set_enabled(
                self._trim_btn, True,
                text=_("wizard_trim_to_count", count=len(info["trimmed"].split())),
                bg=C["dis_bg"], fg=C["neg_fg"],
            )
        elif info["status"] == "acceptable":
            set_enabled(self._trim_btn, True, text=_("wizard_trim_suggest"), bg=C["neg_bg"], fg=C["gold"])
        else:
            set_enabled(self._trim_btn, False, text=_("wizard_smart_trim"), bg=C["card"], fg=C["guide"])

    def _smart_trim(self):
        """智能压缩按钮处理器：将提示词截断到预算以内。"""
        try:
            pos = self._pos_box.get("1.0", "end-1c").strip()
        except Exception:
            return
        if not pos:
            return
        trimmed = _trim_to_budget(pos, 72)
        w_before = len(pos.split())
        w_after = len(trimmed.split())
        self._pos_box.delete("1.0", "end")
        self._pos_box.insert("1.0", trimmed)
        self._pos_box.config(fg=C["ok"])
        self._update_budget_display()
        self._status_lbl.config(text=_("wizard_trimmed", before=w_before, after=w_after), fg=C["ok"])
        self.after(4000, lambda: self._status_lbl.config(text=""))

    # ── 进度动画 ──────────────────────────────────────────────
    _DOTS = ["", ".", "..", "..."]

    def _start_anim(self):
        self._anim_step = 0
        self._anim_tick()

    def _anim_tick(self):
        if not self._generating:
            return
        dots = self._DOTS[self._anim_step % 4]
        try:
            self._param_status.config(text=_("wizard_generating", dots=dots), fg=C["warn"])
        except Exception:
            pass
        self._anim_step += 1
        self._anim_id = self.after(400, self._anim_tick)

    def _stop_anim(self):
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None

    # ── 结果操作 ──────────────────────────────────────────────
    def _use_prompt(self):
        if self._template_state != self._TEMPLATE_PENDING_FILL:
            return
        pos = self._pos_box.get("1.0", "end").strip()
        if not pos or "显示在这里" in pos:
            return
        self.app.pt.delete("1.0", "end")
        self.app.pt.insert("1.0", pos)
        self.app._log(f"✨ 使用助手提示词: {pos[:60]}…")
        self._set_template_state(self._TEMPLATE_IDLE)
        self._status_lbl.config(text=_("wizard_filled_main"), fg=C["ok"])
        self.after(3000, lambda: self._status_lbl.config(text=""))
        # 主输入框背景短暂闪绿
        try:
            orig = self.app.pt.cget("bg")
            self.app.pt.config(bg=C["card_fav"])
            self.app.root.after(300, lambda: self.app.pt.config(bg=orig))
        except Exception:
            pass

    def _copy_box(self, box: tk.Text):
        text = box.get("1.0", "end").strip()
        if text and "显示在这里" not in text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._status_lbl.config(text=_("wizard_copied"), fg=C["ok"])
            self.after(2000, lambda: self._status_lbl.config(text=""))

    def _load_history(self, _=None):
        idx = self._hist_cb.current()
        if 0 <= idx < len(self._history):
            _, pos = self._history[idx]
            self._set_result(pos)
            self._set_template_state(self._TEMPLATE_IDLE)

    def _on_close(self):
        self._stop_anim()
        self.app._prompt_wizard = None
        self.destroy()

    # ══════════════════════════════════════════════════════════
    #   LLM 密钥配置入口
    # ══════════════════════════════════════════════════════════
    def _open_llm_wizard(self):
        """打开 AI 提示词助手模型密钥配置向导。"""

        def _on_save(new_cfg):
            self.app.cfg.update(new_cfg)
            self._update_key_status_btn()

        LLMWizard(self, self.app.cfg, on_save=_on_save)

    def _update_key_status_btn(self):
        """根据当前密钥配置状态更新标签栏右侧按钮的文字和颜色。"""
        sf_ok = bool(self.app.cfg.get("sf_key", "").strip())
        hf_ok = bool(self.app.cfg.get("hf_token", "").strip())
        if sf_ok:
            text, bg, fg = _("wizard_model_configured"), "#064e3b", "#6ee7b7"
        elif hf_ok:
            text, bg, fg = _("wizard_backup_only"), "#1e3a5f", "#93c5fd"
        else:
            text, bg, fg = _("wizard_configure_key"), "#7c1d1d", "#fca5a5"
        try:
            self._key_status_btn.config(text=text, bg=bg, fg=fg, activebackground=bg, activeforeground=fg)
        except Exception:
            pass
