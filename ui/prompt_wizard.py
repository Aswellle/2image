"""
ui/prompt_wizard.py  v3
──────────────────────────────────────────────────────────────
重构要点（v3）：

① 全局滚轮滚动
   非模态窗口用 <Enter>/<Leave> 在 canvas 容器上动态注册 bind_all，
   鼠标进入左侧参数区即可滚动，离开后还原，不干扰主窗口。

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
   · 负面词库说明：10pt 亮黄色，不再是模糊暗色。
   · 窗口默认 1040×860，可缩放，min=780×640。
"""
import random
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from services.prompt_assistant import (
    generate_prompt, apply_template,
    NEGATIVE_LIBRARY, TEMPLATES, get_templates_by_category,
    prompt_budget_info, _trim_to_budget,
)
from config.fonts import F
from config.theme import DARK_THEME as C
from config.i18n import _


# ══════════════════════════════════════════════════════════════
#   维度预设数据
# ══════════════════════════════════════════════════════════════
STYLE_P = [
    "写实摄影 (Photorealistic)", "电影感 (Cinematic)",
    "动漫插画 (Anime/Illustration)", "油画 (Oil Painting)",
    "水彩 (Watercolor)", "赛博朋克 (Cyberpunk)",
    "奇幻艺术 (Fantasy Art)", "极简主义 (Minimalist)",
    "复古胶片 (Vintage Film)", "3D 渲染 (3D Render)",
    "波普艺术 (Pop Art)", "黑白摄影 (Black & White)",
    "自定义…",
]
MOOD_P = [
    "温柔浪漫 (Romantic)", "神秘深邃 (Mysterious)",
    "史诗壮观 (Epic)", "清新自然 (Fresh & Natural)",
    "忧郁诗意 (Melancholic)", "活泼欢快 (Cheerful)",
    "冷峻帅气 (Cool & Calm)", "温暖治愈 (Warm & Healing)",
    "紧张刺激 (Intense)", "梦幻唯美 (Dreamy)",
    "孤独静谧 (Solitary)", "欢庆喜悦 (Festive)",
    "自定义…",
]
DETAIL_P = [
    "柔滑细腻皮肤 (Smooth porcelain skin)",
    "毛发清晰可见 (Ultra-detailed hair strands)",
    "服装纹理细致 (Fabric texture detail)",
    "金属反光质感 (Metallic reflective surface)",
    "水面涟漪细节 (Water ripple details)",
    "自然植被纹理 (Organic botanical texture)",
    "砖石建筑细节 (Stone and brick texture)",
    "光线粒子感 (Volumetric light particles)",
    "自定义…",
]
COMP_P = [
    "三分法构图 (Rule of thirds)",
    "中心构图 (Center composition)",
    "对称构图 (Symmetrical)",
    "引导线构图 (Leading lines)",
    "框架构图 (Frame within frame)",
    "对角线构图 (Diagonal)",
    "黄金螺旋 (Golden spiral)",
    "留白构图 (Negative space)",
    "俯瞰鸟瞰 (Bird's eye view)",
    "低角度仰拍 (Low angle worm's eye)",
    "自定义…",
]
LIGHT_P = [
    "黄金时刻柔光 (Golden hour soft light)",
    "蓝调时刻 (Blue hour)",
    "霓虹灯夜景 (Neon night lighting)",
    "伦勃朗光 (Rembrandt lighting)",
    "逆光剪影 (Backlit silhouette)",
    "柔和自然光 (Soft natural window light)",
    "戏剧性侧光 (Dramatic side lighting)",
    "环境光 (Ambient environmental lighting)",
    "工作室三点布光 (Studio three-point lighting)",
    "体积光丁达尔 (Volumetric Tyndall rays)",
    "自定义…",
]
CAMERA_P = [
    "85mm 人像定焦 f/1.4 浅景深",
    "35mm 街拍 f/2.8 自然透视",
    "50mm 标准 f/1.8 接近人眼",
    "24mm 广角 f/4 环境感强",
    "200mm 长焦 f/2.8 压缩背景",
    "微距镜头 f/8 超近距特写",
    "鱼眼镜头 180° 夸张透视",
    "移轴镜头 miniature 效果",
    "自定义…",
]
QUALITY_P = [
    "8K 超高清 (8K Ultra HD)",
    "HDR 高动态范围 (HDR)",
    "RAW 摄影质感 (RAW photography)",
    "杂志封面品质 (Magazine cover quality)",
    "专业修图精修 (Professional retouched)",
    "电影级色调 (Cinematic color grade)",
    "超锐细节 (Ultra sharp details)",
    "无噪点纯净 (Noise-free clean)",
    "自定义…",
]
NEG_KEYS = list(NEGATIVE_LIBRARY.keys())

_RAND_POOLS = {
    "style":       [x for x in STYLE_P   if "自定义" not in x],
    "mood":        [x for x in MOOD_P    if "自定义" not in x],
    "detail":      [x for x in DETAIL_P  if "自定义" not in x],
    "composition": [x for x in COMP_P    if "自定义" not in x],
    "lighting":    [x for x in LIGHT_P   if "自定义" not in x],
    "camera":      [x for x in CAMERA_P  if "自定义" not in x],
    "quality":     [x for x in QUALITY_P if "自定义" not in x],
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
    LABEL_W = 9   # 标签列字符宽度（约 8 个汉字）

    def __init__(self, canvas_ref, parent: tk.Frame,
                 label: str, presets: list, guide: str = ""):
        self._canvas    = canvas_ref  # 用于滚轮绑定
        self.var        = tk.StringVar(value=presets[0])
        self._custom_v  = tk.StringVar()
        self._presets   = presets
        self._guide     = guide

        # ── 主行容器 ──────────────────────────────────────────
        self._outer = tk.Frame(parent, bg=C["bg"])
        self._outer.pack(fill="x", pady=(0, 2))
        self._outer.columnconfigure(1, weight=1)

        # 标签
        lbl = tk.Label(self._outer, text=label,
                       font=F["btn"], fg=C["sub"],
                       bg=C["bg"], anchor="e", width=self.LABEL_W)
        lbl.grid(row=0, column=0, sticky="e", padx=(0, 8))

        # 下拉框 —— sticky="ew" + columnconfigure weight=1 使其填满
        self._cb = ttk.Combobox(self._outer, textvariable=self.var,
                                values=presets, state="readonly",
                                font=F["input"])
        self._cb.grid(row=0, column=1, sticky="ew")
        self._cb.bind("<<ComboboxSelected>>", self._on_select)

        # ── 自定义展开区（初始隐藏）─────────────────────────────
        self._expand = tk.Frame(parent, bg=C["bg"])
        # 输入框
        cef = tk.Frame(self._expand, bg=C["entry"])
        cef.pack(fill="x", padx=(self.LABEL_W * 8 + 8, 0), pady=(3, 0))
        self._centry = tk.Entry(cef, textvariable=self._custom_v,
                                bg=C["entry"], fg=C["text"],
                                insertbackground="white",
                                font=F["input"], bd=0, relief="flat")
        self._centry.pack(fill="x", padx=10, ipady=6)
        # 指导文字（亮蓝色，italic，清晰）
        if guide:
            tk.Label(self._expand,
                     text=f"💡  {guide}",
                     font=F["body_i"],
                     bg=C["bg"], fg=C["guide"],
                     anchor="w", wraplength=520, justify="left"
                     ).pack(anchor="w",
                            padx=(self.LABEL_W * 8 + 8, 0),
                            pady=(3, 0))

        # 绑定滚轮到本行所有子控件（非模态窗口 Enter/Leave 方案）
        self._bind_scroll(lbl, self._cb)

    def _bind_scroll(self, *widgets):
        """把滚动事件从子控件传递到 canvas_ref，使悬停任意控件均可滚动。"""
        def _fwd(e):
            self._canvas.event_generate("<MouseWheel>", delta=e.delta, when="now")
        def _fwd4(e): self._canvas.event_generate("<Button-4>", when="now")
        def _fwd5(e): self._canvas.event_generate("<Button-5>", when="now")
        for w in widgets:
            w.bind("<MouseWheel>", _fwd, add="+")
            w.bind("<Button-4>",   _fwd4, add="+")
            w.bind("<Button-5>",   _fwd5, add="+")

    def _on_select(self, _=None):
        if self.var.get() == "自定义…":
            self._expand.pack(fill="x", after=self._outer, pady=(0, 4))
            self._centry.focus_set()
        else:
            self._expand.pack_forget()

    # ── 公共接口 ──────────────────────────────────────────────
    def get_value(self) -> str:
        v = self.var.get()
        return self._custom_v.get().strip() if v == "自定义…" else v

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

    def __init__(self, parent_app):
        super().__init__(parent_app.root)
        self.app         = parent_app
        self._history    = []        # [(label, positive, negative)]
        self._generating = False
        self._anim_id    = None
        self._sel_tid    = None      # 已选模板 ID
        self._scroll_cv  = None      # 当前可滚动 canvas 引用

        self.title(_("wizard_title") + " — 专业版")
        self.geometry("1040x860")
        self.configure(bg=C["bg"])
        self.minsize(780, 640)
        self.resizable(True, True)

        # 居中
        self.update_idletasks()
        rx, ry = parent_app.root.winfo_x(), parent_app.root.winfo_y()
        rw, rh = parent_app.root.winfo_width(), parent_app.root.winfo_height()
        self.geometry(
            f"1040x860+{max(0,rx+(rw-1040)//2)}+{max(0,ry+(rh-860)//2)}")

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.lift(); self.focus_force()

    # ══════════════════════════════════════════════════════════
    #   顶层布局
    # ══════════════════════════════════════════════════════════
    def _build(self):
        # ── 标题栏 ─────────────────────────────────────────────
        hdr = tk.Frame(self, bg=C["purple"], height=52)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text=_("wizard_title") + "  专业版",
                 font=F["disp"], bg=C["purple"], fg="white"
                 ).pack(side="left", padx=16, pady=10)
        tk.Label(hdr, text="参数模式精细调控 · 模板模式一键出图",
                 font=F["body"], bg=C["purple"], fg="#d0b8ff"
                 ).pack(side="left", padx=4)

        # ── Tab 切换栏 ─────────────────────────────────────────
        tab_bar = tk.Frame(self, bg=C["acc"], height=42)
        tab_bar.pack(fill="x"); tab_bar.pack_propagate(False)
        self._tab_param_btn = tk.Button(
            tab_bar, text=_("wizard_param_tab"),
            font=F["btn"],
            bg=C["hl"], fg="white",
            bd=0, padx=22, cursor="hand2",
            command=self._show_param_tab)
        self._tab_param_btn.pack(side="left", fill="y")
        self._tab_tmpl_btn = tk.Button(
            tab_bar, text=_("wizard_template_tab"),
            font=F["btn"],
            bg=C["acc"], fg=C["sub"],
            bd=0, padx=22, cursor="hand2",
            command=self._show_tmpl_tab)
        self._tab_tmpl_btn.pack(side="left", fill="y")

        # ── 主体：PanedWindow（左右可拖动分隔）─────────────────
        self._paned = tk.PanedWindow(
            self, orient="horizontal",
            sashwidth=7,
            sashcursor="sb_h_double_arrow",
            sashrelief="flat",
            bg=C["sash"],
            handlesize=0,
        )
        self._paned.pack(fill="both", expand=True)

        self._left_host  = tk.Frame(self._paned, bg=C["bg"])
        self._right_host = tk.Frame(self._paned, bg=C["panel"])
        self._paned.add(self._left_host,  minsize=420, stretch="always")
        self._paned.add(self._right_host, minsize=280, stretch="always")
        # 在窗口显示后设置初始分隔位置
        self.after(50, lambda: self._paned.sash_place(0, 630, 0))

        # 构建左面板（含两种 Tab）
        self._build_left(self._left_host)
        # 构建右面板（结果区）
        self._build_right_panel(self._right_host)

        # 默认显示参数 Tab
        self._param_frame.pack(fill="both", expand=True)

    # ══════════════════════════════════════════════════════════
    #   左面板：滚动宿主 + Tab 内容
    # ══════════════════════════════════════════════════════════
    def _build_left(self, parent):
        # 可滚动容器
        scroll_host = tk.Frame(parent, bg=C["bg"])
        scroll_host.pack(fill="both", expand=True)

        self._left_canvas = tk.Canvas(
            scroll_host, bg=C["bg"], bd=0, highlightthickness=0)
        vsb = ttk.Scrollbar(scroll_host, orient="vertical",
                            command=self._left_canvas.yview)
        self._left_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._left_canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(self._left_canvas, bg=C["bg"])
        _win  = self._left_canvas.create_window(
            (0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: self._left_canvas.configure(
                       scrollregion=self._left_canvas.bbox("all")))
        self._left_canvas.bind(
            "<Configure>",
            lambda e: self._left_canvas.itemconfig(_win, width=e.width))

        # ── 滚轮：Enter 进入区域时注册 bind_all，Leave 时注销 ──
        # 非模态窗口的安全做法：只在鼠标进入左侧区域时劫持滚轮
        cv = self._left_canvas
        def _enable(e):
            def _safe_scroll(delta_fn):
                try: delta_fn()
                except tk.TclError: pass
            self.bind_all("<MouseWheel>",
                lambda e: _safe_scroll(lambda: cv.yview_scroll(int(-1*(e.delta/120)), "units")))
            self.bind_all("<Button-4>",
                lambda e: _safe_scroll(lambda: cv.yview_scroll(-1, "units")))
            self.bind_all("<Button-5>",
                lambda e: _safe_scroll(lambda: cv.yview_scroll( 1, "units")))
        def _disable(e):
            self.unbind_all("<MouseWheel>")
            self.unbind_all("<Button-4>")
            self.unbind_all("<Button-5>")
        scroll_host.bind("<Enter>", _enable)
        scroll_host.bind("<Leave>", _disable)
        self._left_canvas.bind("<Enter>", _enable)
        self._left_canvas.bind("<Leave>", _disable)

        # 两个 Tab 内容框
        self._param_frame = tk.Frame(inner, bg=C["bg"])
        self._tmpl_frame  = tk.Frame(inner, bg=C["bg"])

        self._build_param_tab(self._param_frame)
        self._build_tmpl_tab(self._tmpl_frame)

    # ══════════════════════════════════════════════════════════
    #   参数模式 Tab（全面重设计）
    # ══════════════════════════════════════════════════════════
    def _build_param_tab(self, parent):
        PX = 18

        # ── 主题关键词 ─────────────────────────────────────────
        self._sec_label(parent, "🎯  主题关键词（必填）", PX)
        kf = tk.Frame(parent, bg=C["entry"],
                      highlightbackground=C["ok"],
                      highlightthickness=1)
        kf.pack(fill="x", padx=PX, pady=(6, 0))
        self.kw_var = tk.StringVar()
        kw_ent = tk.Entry(kf, textvariable=self.kw_var,
                          bg=C["entry"], fg=C["text"],
                          insertbackground="white",
                          font=F["label_lg"], bd=0, relief="flat")
        kw_ent.pack(fill="x", padx=12, ipady=10)
        kw_ent.bind("<Return>", lambda e: self._generate_param())
        kw_ent.bind("<FocusIn>",  lambda _: kf.config(highlightbackground=C["entry"]), add="+")
        kw_ent.bind("<FocusOut>", lambda _: kf.config(highlightbackground=C["ok"]),    add="+")
        # 示例提示
        tk.Label(parent,
                 text="  示例：东亚少女  海边咖啡馆  黄昏  白色长裙",
                 font=F["body_i"], bg=C["bg"],
                 fg=C["guide"], anchor="w"
                 ).pack(fill="x", padx=PX, pady=(5, 0))

        self._hdivider(parent, PX)

        # ── 7 个维度参数 ───────────────────────────────────────
        self._sec_label(parent, "🎛  可选维度参数", PX)
        cv_ref = self._left_canvas   # 传给 _DimRow 用于滚轮转发

        dim_host = tk.Frame(parent, bg=C["bg"])
        dim_host.pack(fill="x", padx=PX, pady=(6, 0))

        self._dim_style  = _DimRow(cv_ref, dim_host, "🎨 风格", STYLE_P,
            guide="填写绘画风格，如：水墨画风、复古漫画、科幻写实")
        self._dim_mood   = _DimRow(cv_ref, dim_host, "🌙 氛围", MOOD_P,
            guide="填写情绪基调，如：压抑沉重、喜庆热闹、梦幻迷离")
        self._hdivider_thin(dim_host)
        self._dim_detail = _DimRow(cv_ref, dim_host, "🔍 细节", DETAIL_P,
            guide="填写关键细节，如：雨滴挂在睫毛上、锈迹斑斑的金属板")
        self._dim_comp   = _DimRow(cv_ref, dim_host, "📐 构图", COMP_P,
            guide="填写画面布局，如：主体偏左 1/3、强调前景后景层次")
        self._dim_light  = _DimRow(cv_ref, dim_host, "💡 光影", LIGHT_P,
            guide="填写光源，如：烛光从下方打亮脸部、雨后阳光穿破云层")
        self._dim_cam    = _DimRow(cv_ref, dim_host, "📷 镜头", CAMERA_P,
            guide="填写镜头参数，如：400mm 望远 f/5.6、GoPro 超广角")
        self._dim_qual   = _DimRow(cv_ref, dim_host, "✨ 画质", QUALITY_P,
            guide="填写画质描述，如：胶片颗粒感、印刷品半调网点")

        self._hdivider(parent, PX)

        # ── 负面提示词 ─────────────────────────────────────────
        self._sec_label(parent, "🚫  负面提示词", PX)

        # 词库选择行
        neg_sel = tk.Frame(parent, bg=C["bg"])
        neg_sel.pack(fill="x", padx=PX, pady=(6, 0))
        tk.Label(neg_sel, text="词库类型：",
                 font=F["btn"], bg=C["bg"], fg=C["sub"]
                 ).pack(side="left")
        self._neg_cat_var = tk.StringVar(value=NEG_KEYS[0])
        neg_cb = ttk.Combobox(neg_sel, textvariable=self._neg_cat_var,
                              values=NEG_KEYS, state="readonly",
                              font=F["input"], width=20)
        neg_cb.pack(side="left", padx=(6, 0))
        neg_cb.bind("<<ComboboxSelected>>", self._on_neg_select)

        # 词库内容框（可编辑）
        neg_box_f = tk.Frame(parent, bg=C["neg_bg"],
                             highlightbackground="#7f1d1d",
                             highlightthickness=1)
        neg_box_f.pack(fill="x", padx=PX, pady=(6, 0))
        self._neg_var = tk.StringVar()
        tk.Entry(neg_box_f, textvariable=self._neg_var,
                 bg=C["neg_bg"], fg=C["neg_fg"],
                 insertbackground=C["neg_fg"],
                 font=F["body"], bd=0, relief="flat"
                 ).pack(fill="x", padx=10, ipady=7)

        # 负面词指导说明
        tk.Label(parent,
                 text="  💡  可在框内直接增删词条；选「无负面词」则不附加负面提示词",
                 font=F["body_i"], bg=C["bg"],
                 fg=C["guide"], anchor="w"
                 ).pack(fill="x", padx=PX, pady=(5, 0))

        self._on_neg_select()   # 初始化内容

        self._hdivider(parent, PX)

        # ── 额外补充 ───────────────────────────────────────────
        self._sec_label(parent, "📝  额外补充（可选）", PX)
        ef = tk.Frame(parent, bg=C["entry"],
                      highlightbackground=C["ok"], highlightthickness=1)
        ef.pack(fill="x", padx=PX, pady=(6, 0))
        self.extra_var = tk.StringVar()
        _ee = tk.Entry(ef, textvariable=self.extra_var,
                       bg=C["entry"], fg=C["text"], insertbackground="white",
                       font=F["input"], bd=0, relief="flat")
        _ee.pack(fill="x", padx=10, ipady=7)
        _ee.bind("<FocusIn>",  lambda _: ef.config(highlightbackground=C["entry"]), add="+")
        _ee.bind("<FocusOut>", lambda _: ef.config(highlightbackground=C["ok"]),    add="+")
        tk.Label(parent,
                 text="  💡  如：不要水印、主体面朝右边、禁止出现文字",
                 font=F["body_i"], bg=C["bg"],
                 fg=C["guide"], anchor="w"
                 ).pack(fill="x", padx=PX, pady=(5, 0))

        self._hdivider(parent, PX)

        # ── 操作按钮行 ─────────────────────────────────────────
        btn_row = tk.Frame(parent, bg=C["bg"])
        btn_row.pack(fill="x", padx=PX, pady=(6, 16))

        self._gen_btn = tk.Button(
            btn_row, text=_("wizard_generate_btn"),
            font=F["h2"], bg=C["purple"], fg="white",
            bd=0, padx=22, pady=9, cursor="hand2",
            activebackground=C["dpurp"],
            command=self._generate_param)
        self._gen_btn.pack(side="left")

        tk.Button(btn_row, text="🎲 随机全部维度",
                  font=F["body"], bg=C["acc"], fg="white",
                  bd=0, padx=12, pady=9, cursor="hand2",
                  command=self._random_all
                  ).pack(side="left", padx=(10, 0))

        tk.Button(btn_row, text=_("btn_reset"),
                  font=F["body"], bg=C["panel"], fg=C["sub"],
                  bd=0, padx=10, pady=9, cursor="hand2",
                  command=self._reset_params
                  ).pack(side="left", padx=(8, 0))

        self._param_status = tk.Label(
            btn_row, text="",
            font=F["body"], bg=C["bg"], fg=C["warn"])
        self._param_status.pack(side="left", padx=12)

    # ── 节标题 ─────────────────────────────────────────────────
    @staticmethod
    def _sec_label(parent, text: str, px: int = 16):
        tk.Label(parent, text=text,
                 font=F["h2"], bg=C["bg"],
                 fg=C["text"], anchor="w"
                 ).pack(fill="x", padx=px, pady=(14, 0))

    @staticmethod
    def _hdivider(parent, px: int = 16):
        tk.Frame(parent, bg=C["sep"], height=1
                 ).pack(fill="x", padx=px, pady=(10, 0))

    @staticmethod
    def _hdivider_thin(parent):
        tk.Frame(parent, bg="#1e2d4a", height=1
                 ).pack(fill="x", pady=4)

    # ── 负面词库切换 ──────────────────────────────────────────
    def _on_neg_select(self, _=None):
        cat = self._neg_cat_var.get()
        self._neg_var.set(NEGATIVE_LIBRARY.get(cat, ""))

    # ── 随机 / 重置 ───────────────────────────────────────────
    def _random_all(self):
        for key, dim in [
            ("style",       self._dim_style),
            ("mood",        self._dim_mood),
            ("detail",      self._dim_detail),
            ("composition", self._dim_comp),
            ("lighting",    self._dim_light),
            ("camera",      self._dim_cam),
            ("quality",     self._dim_qual),
        ]:
            dim.set_random(_RAND_POOLS[key])
        self._neg_cat_var.set(random.choice(NEG_KEYS))
        self._on_neg_select()

    def _reset_params(self):
        for dim in [self._dim_style, self._dim_mood, self._dim_detail,
                    self._dim_comp, self._dim_light, self._dim_cam,
                    self._dim_qual]:
            dim.reset()
        self._neg_cat_var.set(NEG_KEYS[0]); self._on_neg_select()
        self.extra_var.set("")

    # ══════════════════════════════════════════════════════════
    #   模板模式 Tab
    # ══════════════════════════════════════════════════════════
    def _build_tmpl_tab(self, parent):
        PX = 18
        self._sec_label(parent, "🎯  主题关键词（用于填充模板）", PX)
        tf = tk.Frame(parent, bg=C["entry"],
                      highlightbackground=C["ok"], highlightthickness=1)
        tf.pack(fill="x", padx=PX, pady=(6, 0))
        self.tmpl_kw_var = tk.StringVar()
        tk.Entry(tf, textvariable=self.tmpl_kw_var,
                 bg=C["entry"], fg=C["text"], insertbackground="white",
                 font=F["label_lg"], bd=0, relief="flat"
                 ).pack(fill="x", padx=12, ipady=10)
        tk.Label(parent,
                 text="  💡  输入图片主题，如：咖啡美食、职场干货、旅行风景",
                 font=F["body_i"], bg=C["bg"],
                 fg=C["guide"], anchor="w"
                 ).pack(fill="x", padx=PX, pady=(5, 8))

        self._hdivider(parent, PX)

        # 模板卡片列表
        cats = get_templates_by_category()
        cat_colors = {
            "小红书":    "#be185d",
            "情绪爆款":  "#b45309",
            "知识干货":  "#1d4ed8",
            "通用自媒体":"#065f46",
        }
        self._tmpl_cards = {}

        for cat, items in cats.items():
            cat_color = cat_colors.get(cat, C["acc"])
            # 分类条
            ch = tk.Frame(parent, bg=cat_color, height=32)
            ch.pack(fill="x", padx=PX, pady=(10, 0)); ch.pack_propagate(False)
            tk.Label(ch, text=f"  {cat}",
                     font=F["btn"],
                     bg=cat_color, fg="white").pack(side="left", pady=5)

            for tid, t in items:
                card = tk.Frame(parent, bg=C["card"],
                                highlightbackground=C["sep"],
                                highlightthickness=1, cursor="hand2")
                card.pack(fill="x", padx=PX, pady=(3, 0))
                self._tmpl_cards[tid] = (card, cat_color)

                top = tk.Frame(card, bg=C["card"]); top.pack(fill="x", padx=10, pady=(8,2))
                tk.Label(top, text=t["name"],
                         font=F["btn"],
                         bg=C["card"], fg=C["text"]).pack(side="left")
                tk.Label(top, text=t["size_hint"],
                         font=F["small_b"],
                         bg=C["card"], fg=C["gold"]).pack(side="right")
                tk.Label(card, text=t["desc"],
                         font=F["body"], bg=C["card"], fg=C["sub"],
                         anchor="w").pack(anchor="w", padx=10, pady=(0,3))
                tk.Label(card, text=f"💡  {t['tips']}",
                         font=F["small_i"],
                         bg=C["card"], fg=C["guide"],
                         anchor="w").pack(anchor="w", padx=10, pady=(0,7))

                for w in [card] + list(card.winfo_children()):
                    w.bind("<Button-1>", lambda e, i=tid: self._select_tmpl(i))

        self._hdivider(parent, PX)

        btn2 = tk.Frame(parent, bg=C["bg"])
        btn2.pack(fill="x", padx=PX, pady=(10, 16))
        self._tmpl_apply_btn = tk.Button(
            btn2, text="📋  应用选中模板（无需 AI）",
            font=F["h2"], bg="#065f46", fg="white",
            bd=0, padx=20, pady=9, cursor="hand2",
            activebackground="#047857",
            command=self._apply_template)
        self._tmpl_apply_btn.pack(side="left")
        self._tmpl_status = tk.Label(
            btn2, text="← 先点击上方模板卡片选中",
            font=F["body_i"], bg=C["bg"], fg=C["guide"])
        self._tmpl_status.pack(side="left", padx=14)

    def _select_tmpl(self, tid: str):
        if self._sel_tid and self._sel_tid in self._tmpl_cards:
            old_card, _ = self._tmpl_cards[self._sel_tid]
            old_card.config(bg=C["card"], highlightbackground=C["sep"])
            for w in old_card.winfo_children():
                try: w.config(bg=C["card"])
                except Exception: pass
        self._sel_tid = tid
        card, cat_color = self._tmpl_cards[tid]
        card.config(bg=C["card_hl"], highlightbackground=cat_color)
        for w in card.winfo_children():
            try: w.config(bg=C["card_hl"])
            except Exception: pass
        t = TEMPLATES[tid]
        self._tmpl_status.config(
            text=f"✅  已选：{t['name']}  |  {t['size_hint']}", fg=C["ok"])

    # ── Tab 切换 ──────────────────────────────────────────────
    def _show_param_tab(self):
        self._tmpl_frame.pack_forget()
        self._param_frame.pack(fill="both", expand=True)
        self._tab_param_btn.config(bg=C["hl"], fg="white")
        self._tab_tmpl_btn.config(bg=C["acc"], fg=C["sub"])
        # 重置滚动到顶部
        self._left_canvas.yview_moveto(0)

    def _show_tmpl_tab(self):
        self._param_frame.pack_forget()
        self._tmpl_frame.pack(fill="both", expand=True)
        self._tab_tmpl_btn.config(bg=C["hl"], fg="white")
        self._tab_param_btn.config(bg=C["acc"], fg=C["sub"])
        self._left_canvas.yview_moveto(0)

    # ══════════════════════════════════════════════════════════
    #   右面板：结果区（不随内容滚动，固定布局）
    # ══════════════════════════════════════════════════════════
    def _build_right_panel(self, parent):
        # ── 顶部固定工具栏（填充按钮始终可见）────────────────────
        top_bar = tk.Frame(parent, bg="#0d2847", height=48)
        top_bar.pack(fill="x"); top_bar.pack_propagate(False)
        self._fill_btn = tk.Button(
            top_bar,
            text=_("wizard_use_btn"),
            font=F["btn"],
            bg=C["ok"], fg="#0a1a0a",
            bd=0, padx=18, pady=7,
            cursor="hand2",
            activebackground="#3aad8a",
            command=self._use_prompt)
        self._fill_btn.pack(side="left", padx=14, pady=8)
        tk.Label(top_bar,
                 text="↑ 生成后点此立即填充，或先在文本框手动微调再点",
                 font=F["small_i"],
                 bg="#0d2847", fg="#7aa8d8"
                 ).pack(side="left", padx=6)

        # ── 正面提示词 ─────────────────────────────────────────
        # 标签行：标题 + 实时词数/字符指示器
        pos_hdr = tk.Frame(parent, bg=C["panel"])
        pos_hdr.pack(fill="x", padx=14, pady=(10, 0))
        tk.Label(pos_hdr, text="📋  正面提示词（可编辑）",
                 font=F["btn"], bg=C["panel"], fg=C["ok"]
                 ).pack(side="left")
        # 实时词数/字符指示器
        self._budget_lbl = tk.Label(
            pos_hdr,
            text="",
            font=F["mono_sm_b"],
            bg=C["panel"], fg=C["sub"],
            padx=8)
        self._budget_lbl.pack(side="right")

        pos_f = tk.Frame(parent, bg=C["entry"])
        pos_f.pack(fill="both", expand=True, padx=14, pady=(4, 0))
        self._pos_box = tk.Text(
            pos_f, font=F["input"],
            bg=C["entry"], fg=C["ok"],
            insertbackground=C["ok"],
            wrap="word", bd=0, padx=10, pady=8, relief="flat")
        self._pos_box.pack(fill="both", expand=True)
        self._pos_box.insert("1.0", "AI 生成或选中模板后\n正面提示词显示在这里…")
        self._pos_box.config(fg="#3a5a4a")

        # 绑定实时词数更新
        self._pos_box.bind("<<Modified>>", self._on_pos_modified)

        # ── Token 预算控制条（正面提示词下方）─────────────────
        budget_bar = tk.Frame(parent, bg="#0a1a2e")
        budget_bar.pack(fill="x", padx=14, pady=(2, 0))

        # 左：兼容性说明
        self._compat_lbl = tk.Label(
            budget_bar,
            text="",
            font=F["small"], bg="#0a1a2e", fg=C["sub"],
            anchor="w")
        self._compat_lbl.pack(side="left", padx=4, pady=3)

        # 右：智能压缩按钮
        self._trim_btn = tk.Button(
            budget_bar,
            text="✂️ 智能压缩",
            font=F["small_b"],
            bg="#1e3a6a", fg="#93c5fd",
            bd=0, padx=8, pady=2,
            cursor="hand2",
            state="disabled",
            command=self._smart_trim)
        self._trim_btn.pack(side="right", padx=4, pady=2)

        # ── 负面提示词 ─────────────────────────────────────────
        tk.Label(parent, text="🚫  负面提示词（可编辑）",
                 font=F["btn"], bg=C["panel"], fg=C["neg_fg"]
                 ).pack(anchor="w", padx=14, pady=(12, 4))
        neg_f = tk.Frame(parent, bg=C["neg_bg"])
        neg_f.pack(fill="both", expand=True, padx=14)
        self._out_neg_box = tk.Text(
            neg_f, font=F["body"],
            bg=C["neg_bg"], fg=C["neg_fg"],
            insertbackground=C["neg_fg"],
            wrap="word", bd=0, padx=10, pady=6, relief="flat")
        self._out_neg_box.pack(fill="both", expand=True)
        self._out_neg_box.insert("1.0", "负面提示词将显示在这里…")
        self._out_neg_box.config(fg="#5a2a2a")

        tk.Frame(parent, bg=C["sep"], height=1
                 ).pack(fill="x", padx=14, pady=8)

        # ── 操作按钮 ───────────────────────────────────────────
        act = tk.Frame(parent, bg=C["panel"])
        act.pack(fill="x", padx=14)
        self._use_btn = tk.Button(
            act, text=_("wizard_use_btn"),
            font=F["body_b"], bg=C["acc"], fg=C["ok"],
            bd=0, padx=12, pady=6, cursor="hand2",
            activebackground="#1a4a7a",
            command=self._use_prompt)
        self._use_btn.pack(side="left")
        tk.Button(act, text="📋 复制正面",
                  font=F["body"], bg=C["acc"], fg="white",
                  bd=0, padx=8, pady=8, cursor="hand2",
                  command=lambda: self._copy_box(self._pos_box)
                  ).pack(side="left", padx=(8, 0))
        tk.Button(act, text="📋 复制负面",
                  font=F["body"], bg="#7f1d1d", fg="white",
                  bd=0, padx=8, pady=8, cursor="hand2",
                  command=lambda: self._copy_box(self._out_neg_box)
                  ).pack(side="left", padx=(6, 0))

        act2 = tk.Frame(parent, bg=C["panel"])
        act2.pack(fill="x", padx=14, pady=(8, 0))
        tk.Button(act2, text="🗑 清空结果",
                  font=F["body"], bg=C["panel"], fg=C["sub"],
                  bd=0, padx=10, pady=6, cursor="hand2",
                  command=self._clear_result
                  ).pack(side="left")

        # 状态标签
        self._status_lbl = tk.Label(
            parent, text="",
            font=F["body"], bg=C["panel"], fg=C["warn"],
            wraplength=320, justify="left")
        self._status_lbl.pack(anchor="w", padx=14, pady=(8, 0))

        tk.Frame(parent, bg=C["sep"], height=1
                 ).pack(fill="x", padx=14, pady=(10, 6))

        # ── 历史记录 ───────────────────────────────────────────
        tk.Label(parent, text="📖  本次会话历史",
                 font=F["body_b"], bg=C["panel"], fg=C["sub"]
                 ).pack(anchor="w", padx=14)
        self._hist_var = tk.StringVar()
        self._hist_cb  = ttk.Combobox(
            parent, textvariable=self._hist_var,
            state="readonly", font=F["small"])
        self._hist_cb.pack(fill="x", padx=14, pady=(4, 14))
        self._hist_cb.bind("<<ComboboxSelected>>", self._load_history)

    # ══════════════════════════════════════════════════════════
    #   生成逻辑
    # ══════════════════════════════════════════════════════════
    def _generate_param(self):
        if self._generating: return
        kw = self.kw_var.get().strip()
        if not kw:
            messagebox.showwarning("提示", "请先填写主题关键词！", parent=self)
            return

        style    = self._dim_style.get_value()
        mood     = self._dim_mood.get_value()
        detail   = self._dim_detail.get_value()
        comp     = self._dim_comp.get_value()
        light    = self._dim_light.get_value()
        camera   = self._dim_cam.get_value()
        quality  = self._dim_qual.get_value()
        negative = self._neg_var.get().strip()
        extra    = self.extra_var.get().strip()

        self._set_generating(True)
        label = f"[参数] {kw[:20]}"

        def _run():
            try:
                pos, neg = generate_prompt(
                    keywords=kw, cfg=self.app.cfg,
                    style=style, mood=mood,
                    detail=detail, composition=comp,
                    lighting=light, camera=camera,
                    quality=quality, negative=negative,
                    extra=extra, log_cb=self.app._log,
                )
                self.after(0, lambda: self._on_done(pos, negative, label))
            except Exception as ex:
                self.after(0, lambda e=str(ex): self._on_error(e))

        threading.Thread(target=_run, daemon=True).start()

    def _apply_template(self):
        if not self._sel_tid:
            messagebox.showinfo("提示", "请先点击选中一个模板！", parent=self)
            return
        kw  = self.tmpl_kw_var.get().strip() or "a subject"
        t   = TEMPLATES[self._sel_tid]
        pos, neg = apply_template(self._sel_tid, kw, log_cb=self.app._log)
        self._on_done(pos, neg, f"[模板] {t['name']}")
        self._tmpl_status.config(
            text=f"✅  已生成！推荐：{t['size_hint']}", fg=C["ok"])

    # ── 状态管理 ──────────────────────────────────────────────
    def _set_generating(self, on: bool):
        self._generating = on
        if on:
            self._gen_btn.config(state="disabled",
                                  text=_("btn_generating"), bg="#4a2a7a")
            self._start_anim()
        else:
            self._gen_btn.config(state="normal",
                                  text=_("wizard_generate_btn"), bg=C["purple"])
            self._stop_anim()

    def _on_done(self, positive: str, negative: str, label: str):
        self._stop_anim()
        self._generating = False
        try:
            self._gen_btn.config(state="normal",
                                  text=_("wizard_generate_btn"), bg=C["purple"])
        except Exception: pass
        self._param_status.config(text="✅ 生成成功！", fg=C["ok"])
        self._status_lbl.config(text="✅ 生成完成", fg=C["ok"])
        self.after(3000, lambda: self._param_status.config(text=""))
        self.after(3000, lambda: self._status_lbl.config(text=""))
        self._set_result(positive, negative)
        self._history.insert(0, (label, positive, negative))
        self._history = self._history[:8]
        self._hist_cb.config(values=[h[0] for h in self._history])
        self.app._log(f"✨ 提示词助手: {positive[:60]}…")

    def _on_error(self, err: str):
        self._stop_anim()
        self._generating = False
        try:
            self._gen_btn.config(state="normal",
                                  text=_("wizard_generate_btn"), bg=C["purple"])
        except Exception: pass
        self._param_status.config(text="❌ 失败", fg=C["hl"])
        self._status_lbl.config(text=f"❌ {err[:100]}", fg=C["hl"])
        self.app._log(f"✗ 提示词助手: {err}")

    def _set_result(self, pos: str, neg: str):
        self._pos_box.delete("1.0", "end")
        self._pos_box.insert("1.0", pos)
        self._pos_box.config(fg=C["ok"])
        self._out_neg_box.delete("1.0", "end")
        self._out_neg_box.insert("1.0", neg if neg else "（无负面提示词）")
        self._out_neg_box.config(fg=C["neg_fg"] if neg else C["guide"])
        # 触发词数指示器更新
        self._update_budget_display()

    def _on_pos_modified(self, _event=None):
        """正面提示词文本框内容变更时触发词数指示器刷新。"""
        try:
            self._pos_box.edit_modified(False)   # 必须重置，否则只触发一次
        except Exception:
            pass
        self.after(50, self._update_budget_display)   # 轻微延迟，确保内容已更新

    def _update_budget_display(self):
        """
        实时更新 Token 预算指示器：
        · 右上角标签：词数/字符数 + 颜色编码
        · 预算条：模型兼容性说明
        · 智能压缩按钮：仅在 >80 词时激活
        """
        try:
            pos = self._pos_box.get("1.0", "end-1c").strip()
        except Exception:
            return

        # 占位文本时不显示计数
        if not pos or "显示在这里" in pos or "AI 生成" in pos:
            self._budget_lbl.config(text="", fg=C["sub"])
            self._compat_lbl.config(text="")
            self._trim_btn.config(state="disabled")
            return

        info = prompt_budget_info(pos)

        # ── 词数/字符标签 ───────────────────────────────────────
        self._budget_lbl.config(
            text=info["label"],
            fg=info["color"]
        )

        # ── 兼容性说明 ──────────────────────────────────────────
        if info["status"] == "optimal":
            compat_text = "兼容: FLUX.1-schnell  SDXL  SD 2.1  SD 1.5  ✅ 全兼容"
            compat_color = "#4a7a4a"
        elif info["status"] == "acceptable":
            compat_text = "兼容: FLUX.1-schnell ✅   SDXL/SD ⚠️ 末尾可能被截断"
            compat_color = "#7a6a20"
        else:
            compat_text = "❌ 过长 — SDXL/SD 超出77 token硬限制，末尾内容将被丢弃"
            compat_color = "#7a2020"

        self._compat_lbl.config(text=compat_text, fg=compat_color)

        # ── 智能压缩按钮 ────────────────────────────────────────
        if info["status"] == "too_long":
            self._trim_btn.config(
                state="normal",
                text=f"✂️ 智能压缩（→ {len(info['trimmed'].split())} 词）",
                bg="#7c1d1d", fg="#fca5a5")
        elif info["status"] == "acceptable":
            self._trim_btn.config(
                state="normal",
                text=f"✂️ 建议压缩（→ 约72词）",
                bg="#4a3810", fg="#fbbf24")
        else:
            self._trim_btn.config(
                state="disabled",
                text="✂️ 智能压缩",
                bg="#1e3a6a", fg="#93c5fd")

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
        w_after  = len(trimmed.split())
        self._pos_box.delete("1.0", "end")
        self._pos_box.insert("1.0", trimmed)
        self._pos_box.config(fg=C["ok"])
        self._update_budget_display()
        self._status_lbl.config(
            text=f"✂️ 已压缩：{w_before} 词 → {w_after} 词（全模型兼容）",
            fg=C["ok"])
        self.after(4000, lambda: self._status_lbl.config(text=""))

    # ── 进度动画 ──────────────────────────────────────────────
    _DOTS = ["", ".", "..", "..."]

    def _start_anim(self):
        self._anim_step = 0
        self._anim_tick()

    def _anim_tick(self):
        if not self._generating: return
        dots = self._DOTS[self._anim_step % 4]
        try:
            self._param_status.config(text=f"AI 生成中{dots}", fg=C["warn"])
        except Exception: pass
        self._anim_step += 1
        self._anim_id = self.after(400, self._anim_tick)

    def _stop_anim(self):
        if self._anim_id:
            self.after_cancel(self._anim_id); self._anim_id = None

    # ── 结果操作 ──────────────────────────────────────────────
    def _use_prompt(self):
        pos = self._pos_box.get("1.0", "end").strip()
        if not pos or "显示在这里" in pos:
            messagebox.showinfo("提示", "请先生成或选择模板！", parent=self)
            return
        self.app.pt.delete("1.0", "end")
        self.app.pt.insert("1.0", pos)
        self.app._log(f"✨ 使用助手提示词: {pos[:60]}…")
        self._status_lbl.config(text="✅ 已填入主输入框！可切回主界面微调后生成", fg=C["ok"])
        self.after(3000, lambda: self._status_lbl.config(text=""))
        # 顶部一键填充按钮短暂高亮反馈
        try:
            self._fill_btn.config(bg="#3aad8a", text="✅ 已填充！")
            self.after(1200, lambda: self._fill_btn.config(
                bg=C["ok"], text=_("wizard_use_btn")))
        except Exception: pass
        # 主输入框背景短暂闪绿
        try:
            orig = self.app.pt.cget("bg")
            self.app.pt.config(bg="#1a3a2a")
            self.app.root.after(300, lambda: self.app.pt.config(bg=orig))
        except Exception: pass

    def _copy_box(self, box: tk.Text):
        text = box.get("1.0", "end").strip()
        if text and "显示在这里" not in text:
            self.clipboard_clear(); self.clipboard_append(text)
            self._status_lbl.config(text="📋 已复制！", fg=C["ok"])
            self.after(2000, lambda: self._status_lbl.config(text=""))

    def _clear_result(self):
        self._pos_box.delete("1.0", "end")
        self._pos_box.insert("1.0", "AI 生成或选中模板后\n正面提示词显示在这里…")
        self._pos_box.config(fg="#3a5a4a")
        self._out_neg_box.delete("1.0", "end")
        self._out_neg_box.insert("1.0", "负面提示词将显示在这里…")
        self._out_neg_box.config(fg="#5a2a2a")
        self._status_lbl.config(text="")

    def _load_history(self, _=None):
        idx = self._hist_cb.current()
        if 0 <= idx < len(self._history):
            _, pos, neg = self._history[idx]
            self._set_result(pos, neg)

    def _on_close(self):
        self._stop_anim()
        try:
            self.unbind_all("<MouseWheel>")
            self.unbind_all("<Button-4>")
            self.unbind_all("<Button-5>")
        except Exception: pass
        self.app._prompt_wizard = None
        self.destroy()
