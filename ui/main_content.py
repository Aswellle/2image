"""
ui/main_content.py — Main content / right-panel extracted from App.
────────────────────────────────────────────────────────────────
Mechanical extraction from ui/app.py v5.1.
All App-level methods and state accessed through self.app.
"""

import io
import os
import random
import threading
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

from PIL import Image, ImageTk

from config.fonts import F
from config.theme import C, TAG_PALETTE, tag_color
from config.i18n import _
from ui.button_states import set_enabled
from ui.canvas_image import draw_image
from data.repository import get_all_entries, get_stats
from services.providers import (
    FREE_PROVIDERS,
    IMG2IMG_PROVIDERS,
    PAID_PROVIDERS,
    display_name_for,
    provider_id_for,
)
from services.image_service import generate_image, save_image_file
from ui.batch_panel import BatchPanel
from ui.queue_panel import QueuePanel
from ui.app_protocol import MainContentProtocol


# ══════════════════════════════════════════════════════════════
#   Provider 下拉框显示名
# ══════════════════════════════════════════════════════════════
def _provider_display(provider_id: str) -> str:
    """Stable ID -> dropdown label. Module-level alias so tests can patch it."""
    return display_name_for(provider_id)


# Short labels for the compact img2img hint strip. Keyed by stable ID so
# they never depend on the (translatable) display name.
_I2I_SHORT_LABELS: dict[str, str] = {
    "bfl_flux": "BFL FLUX",
    "fal_flux": "fal.ai FLUX",
    "gemini": "Gemini",
    "gemini_nano_banana_pro": "Nano Banana Pro",
    "minimax_image": "MiniMax",
    "openai_image": "GPT-Image",
    "stability_ai": "Stability AI",
    "volcengine_ark": "Seedream",
}


def _i2i_short_label(provider_id: str) -> str:
    """Compact label for the i2i hint; falls back to the display name."""
    return _I2I_SHORT_LABELS.get(provider_id, _provider_display(provider_id))


# ══════════════════════════════════════════════════════════════
#   自定义强度滑块（Canvas 渐变轨道 + 可拖拽圆形手柄）
# ══════════════════════════════════════════════════════════════
class _StrengthSlider:
    """
    Canvas 绘制的强度滑块。
    范围 0.1~0.9；轨道颜色渐变：蓝（微调） → 紫（融合） → 红（重构）。
    """

    W = 260
    H = 58
    TX = 12
    TW = 236
    TY = 22
    TH = 6
    HR = 9  # 手柄半径
    # 三段渐变颜色锚点
    _STOPS = [(0.1, "#1d4ed8"), (0.5, "#7c3aed"), (0.9, "#dc2626")]

    def __init__(self, parent: tk.Frame, variable: tk.DoubleVar, *, w: int = 0, h: int = 0, marks: bool = True):
        # Allow compact mode: pass w/h to override defaults
        if w and h:
            self.W = w
            self.H = h
            self.TX = 10
            self.TW = w - 20
            self.TY = max(12, h // 3)
            self.TH = 5
            self.HR = 7
        else:
            self.W = self.__class__.W
            self.H = self.__class__.H
            self.TX = self.__class__.TX
            self.TW = self.__class__.TW
            self.TY = self.__class__.TY
            self.TH = self.__class__.TH
            self.HR = self.__class__.HR
        self.marks = marks
        self.var = variable
        self.cv = tk.Canvas(
            parent, width=self.W, height=self.H, bg="#0a1628", bd=0, highlightthickness=0, cursor="hand2"
        )
        self._gradient = self._build_gradient(60)
        self._draw()
        self.cv.bind("<ButtonPress-1>", self._on_press)
        self.cv.bind("<B1-Motion>", self._on_drag)
        self.var.trace("w", lambda *_: self._draw())

    def pack(self, **kw):
        self.cv.pack(**kw)

    def grid(self, **kw):
        self.cv.grid(**kw)

    # ── 工具 ──────────────────────────────────────────────────
    def _val_to_x(self, v: float) -> int:
        return int(self.TX + (v - 0.1) / 0.8 * self.TW)

    def _x_to_val(self, x: int) -> float:
        v = 0.1 + (x - self.TX) / self.TW * 0.8
        return round(max(0.1, min(0.9, v)), 2)

    @staticmethod
    def _lerp(c1: str, c2: str, t: float) -> str:
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        return f"#{int(r1 + (r2 - r1) * t):02x}{int(g1 + (g2 - g1) * t):02x}{int(b1 + (b2 - b1) * t):02x}"

    def _build_gradient(self, n: int) -> list:
        stops = self._STOPS
        colors = []
        for i in range(n):
            t = i / (n - 1)  # 0..1 对应 0.1..0.9
            # 找区间
            for j in range(len(stops) - 1):
                v0, c0 = stops[j]
                v1, c1 = stops[j + 1]
                seg_t0 = (v0 - 0.1) / 0.8
                seg_t1 = (v1 - 0.1) / 0.8
                if t <= seg_t1:
                    local = (t - seg_t0) / (seg_t1 - seg_t0)
                    colors.append(self._lerp(c0, c1, local))
                    break
            else:
                colors.append(stops[-1][1])
        return colors

    # ── 绘制 ──────────────────────────────────────────────────
    def _draw(self):
        cv = self.cv
        cv.delete("all")
        W, TX, TW, TY, TH, HR = self.W, self.TX, self.TW, self.TY, self.TH, self.HR
        val = self.var.get()
        hx = self._val_to_x(val)
        n = len(self._gradient)
        sw = TW / n  # 每段宽度

        # ── 渐变轨道 ──────────────────────────────────────────
        for i, col in enumerate(self._gradient):
            x0 = TX + i * sw
            x1 = x0 + sw + 1
            cv.create_rectangle(x0, TY, x1, TY + TH, fill=col, outline="")

        # ── 手柄 ─────────────────────────────────────────────
        cy = TY + TH // 2
        cv.create_oval(hx - HR - 1, cy - HR - 1, hx + HR + 1, cy + HR + 1, fill="#0a1628", outline="#5c6470", width=1)
        cv.create_oval(hx - HR, cy - HR, hx + HR, cy + HR, fill="white", outline="#4a7adf", width=2)

        # ── 数值标签（仅完整滑块显示，紧凑模式已在外部显示数值）────
        if self.marks:
            cv.create_text(hx, TY - 5, text=f"{val:.1f}", font=F["small_b"], fill=C["ok"], anchor="s")

        # ── 锚点刻度 + 标签（轨道下方，紧凑模式下省略）──────────
        if self.marks:
            for mv, mt in [
                (0.1, _("strength_fine_tune")),
                (0.5, _("strength_blend")),
                (0.9, _("strength_reconstruct")),
            ]:
                mx = self._val_to_x(mv)
                cv.create_line(mx, TY + TH, mx, TY + TH + 4, fill="#3a5a8a", width=1)
                cv.create_text(mx, TY + TH + 14, text=mt, font=F["small"], fill="#4a6a9a", anchor="n")

    # ── 事件 ──────────────────────────────────────────────────
    def _on_press(self, e):
        self.var.set(self._x_to_val(e.x))

    def _on_drag(self, e):
        self.var.set(self._x_to_val(e.x))


class MainContent:
    """Right-panel main content: input, preview, variants, queue, log."""

    def __init__(self, parent: tk.Frame, app: MainContentProtocol):
        self.app = app
        self.parent = parent

        # ── State initialized before _build ───────────────────
        self.variant_n_var = tk.IntVar(value=5)
        self._batch_params = None

        # Preview state
        self._prev_orig = None
        self._prev_photo = None
        self._prev_item = None
        self._prev_outline = None

        # Compare state
        self._cmp_orig = None
        self._cmp_photo = None
        self._cmp_mode = False

        # 生成模式："t2i" 文生图 | "i2i" 图生图
        self._gen_mode = "t2i"
        # 切入图生图模式前的接口选择（切回文生图时恢复）
        self._pre_i2i_provider: str | None = None
        # 图生图参考图状态
        self._ref_image: bytes | None = None
        self._ref_strength = tk.DoubleVar(value=0.6)
        self._ref_thumb_photo = None  # 预览缩略图 PhotoImage（防 GC）

        # Resize timers
        self._prev_resize_timer = None
        self._cmp_resize_timer = None
        self._ref_resize_timer = None

        self._build(parent)

    # ══════════════════════════════════════════════════════════
    #   右侧主区
    # ══════════════════════════════════════════════════════════

    def _build(self, R):
        # ── ttk 暗色主题配置（全局，对整个 Tk 实例生效）─────────────
        style = ttk.Style()
        style.theme_use("clam")

        # ── Notebook / Tab ────────────────────────────────────────
        style.configure(
            "TNotebook", background=C["bg"], borderwidth=0, bordercolor=C["sep"], lightcolor=C["bg"], darkcolor=C["bg"]
        )
        style.configure(
            "TNotebook.Tab",
            background=C["panel"],
            foreground=C["sub"],
            padding=[12, 4],
            font=F["small_b"],
            bordercolor=C["sep"],
            lightcolor=C["panel"],
            darkcolor=C["panel"],
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", C["acc"]), ("active", C["hl"])],
            foreground=[("selected", "white"), ("active", "white")],
            lightcolor=[("selected", C["acc"])],
            darkcolor=[("selected", C["acc"])],
        )

        # ── Combobox 字段及箭头区完整状态映射 ────────────────────────
        # 覆盖 clam 主题默认状态，防止 focus/hover 时字段变回系统色
        style.configure(
            "TCombobox",
            fieldbackground=C["entry"],
            background=C["acc"],
            foreground=C["text"],
            arrowcolor=C["text"],
            selectbackground=C["acc"],
            selectforeground="white",
            insertcolor=C["text"],
            bordercolor=C["sep"],
            lightcolor=C["entry"],
            darkcolor=C["entry"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[
                ("readonly", "focus", C["entry"]),
                ("readonly", "!focus", C["entry"]),
                ("focus", C["entry"]),
                ("!focus", C["entry"]),
                ("disabled", C["panel"]),
            ],
            foreground=[
                ("readonly", C["text"]),
                ("focus", C["text"]),
                ("disabled", C["sub"]),
            ],
            selectbackground=[
                ("focus", C["acc"]),
                ("!focus", C["acc"]),
            ],
            selectforeground=[
                ("focus", "white"),
                ("!focus", "white"),
            ],
            background=[
                ("active", C["hl"]),  # 箭头按钮 hover
                ("!active", C["acc"]),  # 箭头按钮常态
            ],
            arrowcolor=[
                ("disabled", C["sub"]),
                ("active", "white"),
                ("!active", C["text"]),
            ],
        )

        # ── 弹出下拉列表（Listbox）颜色 ───────────────────────────
        # ttk.Combobox 的弹出框是 tk.Listbox，须用 option_add 设置
        self.app.root.option_add("*TCombobox*Listbox.background", C["entry"])
        self.app.root.option_add("*TCombobox*Listbox.foreground", C["text"])
        self.app.root.option_add("*TCombobox*Listbox.selectBackground", C["acc"])
        self.app.root.option_add("*TCombobox*Listbox.selectForeground", "white")
        self.app.root.option_add("*TCombobox*Listbox.relief", "flat")
        self.app.root.option_add("*TCombobox*Listbox.borderWidth", "0")
        # 增大弹出 Listbox 的行高和字体，让长名称清晰可读
        self.app.root.option_add("*TCombobox*Listbox.font", F["body"])
        self.app.root.option_add("*TCombobox*Listbox.selectBorderWidth", "0")
        tk.Label(R, text=_("app_input_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(
            anchor="w", pady=(12, 4), padx=14
        )

        pf = tk.Frame(R, bg=C["entry"])
        pf.pack(fill="x", padx=14, pady=(0, 0))
        self.pt = tk.Text(
            pf,
            height=4,
            font=F["label"],
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            wrap="word",
            bd=0,
            padx=10,
            pady=8,
            relief="flat",
        )
        self.pt.pack(fill="x")
        self.pt.bind("<Control-Return>", lambda e: (self.app._gen(), "break")[1])

        # ── 输入框底部辅助条：字数统计 + 一键复制 ─────────────
        _pt_foot = tk.Frame(R, bg="#0d1a30")
        _pt_foot.pack(fill="x", padx=14)

        self._char_lbl = tk.Label(_pt_foot, text=_("lbl_chars", n=0), font=F["mono_tiny"], bg="#0d1a30", fg=C["text_muted"])
        self._char_lbl.pack(side="left", padx=6, pady=2)

        tk.Button(
            _pt_foot,
            text=_("btn_copy_prompt"),
            font=F["tiny"],
            bg="#1e3060",
            fg="#93c5fd",
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._copy_prompt,
        ).pack(side="right", padx=4, pady=2)

        # Bug3 修复：
        # · 旧代码用 self.after() —— App 不是 tk.Widget，静默失败
        # · 旧代码只绑 <KeyRelease> —— 对粘贴、程序写入等无效
        # · 正确方案：绑定 <<Modified>> 虚拟事件（Tkinter 标准文本变更接口），
        #   每次回调后必须 edit_modified(False) 重置标志，否则只触发一次
        def _on_text_modified(event=None):
            try:
                # 重置 Modified 标志（否则后续变更不再触发事件）
                self.pt.edit_modified(False)
            except Exception:
                pass
            self._update_char_count()

        self.pt.bind("<<Modified>>", _on_text_modified)

        # ── 生成行 ────────────────────────────────────────────
        opt = tk.Frame(R, bg=C["bg"])
        opt.pack(fill="x", padx=14, pady=(0, 4))
        tk.Label(opt, text=_("lbl_size"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        sz_default = self.app.cfg.get("default_size", "1024x1024").replace("×", "x")
        self.szv = tk.StringVar(value=sz_default)
        ttk.Combobox(
            opt,
            textvariable=self.szv,
            width=12,
            state="readonly",
            values=[
                "512x512",
                "768x768",
                "1024x1024",
                "1024x576",
                "1280x720",
                "1920x1080",
                "576x1024",
                "720x1280",
                "768x1024",
            ],
        ).pack(side="left", padx=(2, 8))
        tk.Label(opt, text=_("lbl_provider"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self.pv = tk.StringVar(value=_("provider_auto"))
        # 下拉框展示 display name，pv 保存的也是 display name；
        # 传给路由/派发前需用 provider_id_for() 转成 stable id。
        # v8 把注册表改成 stable id 作 key 后，这里曾直接塞 key，
        # 导致用户在下拉框里看到 bria_ai / gemini_nano_banana_pro 这类内部 ID。
        self._t2i_provider_list = (
            [_("provider_auto"), _("provider_free_section")]
            + [_provider_display(n) for n in FREE_PROVIDERS]
            + [_("provider_paid_section")]
            + [_provider_display(n) for n in PAID_PROVIDERS]
        )
        self._provider_cb = ttk.Combobox(
            opt,
            textvariable=self.pv,
            width=32,
            state="readonly",
            values=self._t2i_provider_list,
            postcommand=self._expand_provider_popup,
        )
        self._provider_cb.pack(side="left", padx=(2, 8))
        self.gb = tk.Button(
            opt,
            text=_("btn_generate"),
            font=F["btn"],
            bg=C["hl"],
            fg="white",
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            activebackground="#c73652",
            command=self.app.gen_controller.generate_or_cancel,
        )
        self.gb.pack(side="left")

        # ── 工具行 ────────────────────────────────────────────
        opt2 = tk.Frame(R, bg=C["bg"])
        opt2.pack(fill="x", padx=14, pady=(0, 6))
        tk.Button(
            opt2,
            text=_("btn_phrase_lib"),
            font=F["body_b"],
            bg="#065f46",
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.app._open_phrase_panel,
        ).pack(side="left")
        tk.Button(
            opt2,
            text=_("btn_prompt_wizard"),
            font=F["body_b"],
            bg="#7c3aed",
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.app._open_prompt_wizard,
        ).pack(side="left", padx=(6, 0))
        # 分组间隔须明显大于组内间距（组内 6px），否则分隔线两侧与普通
        # 按钮间距相同，读起来仍是同一串控件，分隔线没起到分组作用。
        tk.Frame(opt2, bg=C["sep"], width=1).pack(side="left", fill="y", padx=12, pady=4)
        tk.Label(opt2, text=_("lbl_variant_count"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")

        # ── 圆形 ➖ / 数字 / ➕ 控件（Issue-1 修复：大点击面积）────
        def _dec_n():
            v = max(1, self.variant_n_var.get() - 1)
            self.variant_n_var.set(v)
            _n_lbl.config(text=str(v))

        def _inc_n():
            v = min(6, self.variant_n_var.get() + 1)
            self.variant_n_var.set(v)
            _n_lbl.config(text=str(v))

        _n_grp = tk.Frame(opt2, bg=C["bg"])
        _n_grp.pack(side="left", padx=(2, 4))
        tk.Button(
            _n_grp,
            text="⊖",
            font=F["btn"],
            bg=C["acc"],
            fg="#a0c8ff",
            bd=0,
            width=2,
            pady=2,
            cursor="hand2",
            activebackground=C["hl"],
            activeforeground="white",
            command=_dec_n,
        ).pack(side="left")
        _n_lbl = tk.Label(
            _n_grp,
            text=str(self.variant_n_var.get()),
            font=F["body_b"],
            bg=C["entry"],
            fg=C["ok"],
            width=2,
            pady=2,
            relief="flat",
        )
        _n_lbl.pack(side="left", padx=2)
        tk.Button(
            _n_grp,
            text="⊕",
            font=F["btn"],
            bg=C["acc"],
            fg="#a0c8ff",
            bd=0,
            width=2,
            pady=2,
            cursor="hand2",
            activebackground="#4ecca3",
            activeforeground="#0a1a0a",
            command=_inc_n,
        ).pack(side="left")

        self._variant_gen_btn = tk.Button(
            opt2,
            text=_("btn_variant_gen"),
            font=F["body_b"],
            bg="#4a1d96",
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.app._gen_variants,
        )
        self._variant_gen_btn.pack(side="left")
        self._variant_gen_btn_bg = "#4a1d96"  # 恢复用：禁用态会覆盖 bg
        # 唯一留在主界面的快捷键说明：Ctrl+Enter 在输入框内触发，
        # 没有对应菜单项，用户无从得知。其余快捷键由菜单栏承载。
        # 它是补充信息，窗口变窄时先让位给按钮（英文界面下这条要占 137px，
        # 硬留着会把「变体生成」挤掉）。
        self._shortcut_lbl = tk.Label(
            opt2, text=_("shortcut_hint"), font=F["small"], bg=C["bg"], fg=C["text_muted"]
        )
        self._shortcut_lbl.pack(side="left", padx=6)
        opt2.bind("<Configure>", self._on_tools_row_resize)

        # ── 生成模式切换行（分段控件样式）───────────────────────────
        # 用一个带描边的容器把两个按钮"焊"在一起，视觉上读作一个控件
        # 而不是两个各自为政的按钮；两态都复用已有的强调色体系
        # （t2i=C["hl"] 全局主色，i2i=#1d4ed8，与图生图侧栏/参考图按钮同色系）。
        # 注意：图生图的参考图控制面板不在这一行下方展开——它固定在
        # 预览 Tab 内部（_build_preview_tab 的 _prev_host 第 0 列），
        # 见 _build_i2i_ref_column。这样切换模式不会让下方状态栏 /
        # Notebook 整体下移，详见 _switch_mode 的说明。
        mode_row = tk.Frame(R, bg=C["bg"])
        mode_row.pack(fill="x", padx=14, pady=(0, 3))
        self._mode_row = mode_row

        _seg = tk.Frame(mode_row, bg=C["sep"], highlightbackground=C["sep"], highlightthickness=1)
        _seg.pack(side="left")
        self._mode_t2i_btn = tk.Button(
            _seg,
            text=_("mode_t2i"),
            font=F["small_b"],
            bg=C["hl"],
            fg="white",
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            relief="flat",
            activebackground="#c73652",
            activeforeground="white",
            command=lambda: self._switch_mode("t2i"),
        )
        self._mode_t2i_btn.pack(side="left", padx=(1, 0), pady=1)
        self._mode_i2i_btn = tk.Button(
            _seg,
            text=_("mode_i2i"),
            font=F["small_b"],
            bg=C["panel"],
            fg=C["sub"],
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            relief="flat",
            activebackground="#1e3a5f",
            activeforeground="white",
            command=lambda: self._switch_mode("i2i"),
        )
        self._mode_i2i_btn.pack(side="left", padx=(1, 1), pady=1)

        # 状态栏
        self.stv = tk.StringVar(value=_("status_ready"))
        self.stl = tk.Label(
            R, textvariable=self.stv, font=F["body"], bg=C["panel"], fg=C["ok"], anchor="w", padx=10, pady=5
        )
        self.stl.pack(fill="x", padx=14, pady=(0, 4))
        # 进度条常驻占位（pack 一次不再撤下）：避免生成开始/结束时
        # Notebook 区域整体上下跳动两次
        self.pb = ttk.Progressbar(R, mode="indeterminate")
        self.pb.pack(fill="x", padx=14, pady=(0, 4))

        # ── Notebook（外围加强调色线框，便于视觉定位边界）────────
        _nb_border = tk.Frame(
            R, bg=C["bg"], highlightbackground=C["sash"], highlightcolor=C["sash_hl"], highlightthickness=2
        )
        _nb_border.pack(fill="both", expand=True, padx=12, pady=(4, 8))

        self._nb = ttk.Notebook(_nb_border)
        self._nb.pack(fill="both", expand=True, padx=1, pady=1)

        self.imf = tk.Frame(self._nb, bg=C["panel"])
        self._nb.add(self.imf, text=_("tab_preview"))
        self._build_preview_tab()

        self._var_frame = tk.Frame(self._nb, bg="#0a0f1a")
        self._nb.add(self._var_frame, text=_("tab_variants"))
        self._batch_panel = BatchPanel(self._var_frame, self.app)
        self._batch_panel.pack(fill="both", expand=True)

        # ── 📋 顺序生成队列 Tab ───────────────────────────────
        self._queue_frame = tk.Frame(self._nb, bg="#1a1a2e")
        self._nb.add(self._queue_frame, text=_("tab_queue"))
        self._queue_panel = QueuePanel(self._queue_frame, self.app)
        self._queue_panel.pack(fill="both", expand=True)

        lf2 = tk.Frame(self._nb, bg=C["bg"])
        self._nb.add(lf2, text=_("tab_debug_log"))
        self.logt = scrolledtext.ScrolledText(
            lf2, font=F["mono"], bg="#080818", fg="#4ecca3", insertbackground="white", bd=0, state="disabled"
        )
        self.logt.pack(fill="both", expand=True, padx=4, pady=4)
        tk.Button(
            lf2,
            text=_("btn_clear_log"),
            font=F["body"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self.app._clr_log,
        ).pack(anchor="e", padx=4, pady=2)

    # ══════════════════════════════════════════════════════════
    #   标签统计（已移除独立行；统计数据仍可在顶部菜单统计看板中查看）
    # ══════════════════════════════════════════════════════════
    def _refresh_tag_stats(self):
        pass  # row removed; kept as no-op for callers (sidebar, queue_panel, app)

    # ══════════════════════════════════════════════════════════
    #   预览 Tab（含对比）— Fix-2: 补充 _cmp_label_b.pack()
    # ══════════════════════════════════════════════════════════
    def _build_preview_tab(self):
        tb = tk.Frame(self.imf, bg="#0d1b2a", height=36)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        tk.Button(
            tb,
            text=_("btn_open_viewer"),
            font=F["small_b"],
            bg=C["hl"],
            fg="white",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.app._open_viewer,
        ).pack(side="left", padx=6, pady=4)
        tk.Button(
            tb,
            text=_("btn_save"),
            font=F["small"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.app._save,
        ).pack(side="left", padx=2, pady=4)
        tk.Button(
            tb,
            text=_("btn_copy_path"),
            font=F["small"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.app._copy_path,
        ).pack(side="left", padx=2, pady=5)
        tk.Button(
            tb,
            text=_("btn_regenerate"),
            font=F["small"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.app._gen,
        ).pack(side="left", padx=2, pady=5)
        tk.Frame(tb, bg=C["sep"], width=1).pack(side="left", fill="y", padx=6, pady=6)
        self._cmp_btn = tk.Button(
            tb,
            text=_("btn_pick_compare"),
            font=F["small"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._pick_compare_image,
        )
        self._cmp_btn.pack(side="left", padx=2, pady=5)
        self._cmp_clear_btn = tk.Button(
            tb,
            text=_("btn_clear_compare"),
            font=F["small"],
            bg=C["dis_bg"],
            fg="white",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._clear_compare,
            state="disabled",
        )
        self._cmp_clear_btn.pack(side="left", padx=2, pady=5)
        # 次要提示：窗口够宽时才显示。它是解释性文字，优先级低于按钮，
        # 但 pack(side="right") 会先占住右侧空间——窄窗口下被压到几像素、
        # 内容不可读却仍在抢位。改为按工具栏实际宽度决定是否显示。
        self._dblclick_hint = tk.Label(
            tb, text=_("preview_dblclick_hint"), font=F["small"], bg="#0d1b2a", fg=C["sub"]
        )
        self._dblclick_hint.pack(side="right", padx=10)
        tb.bind("<Configure>", self._on_preview_toolbar_resize)

        # ── 预览主体 ──────────────────────────────────────────
        # 列 0：图生图参考图侧栏（默认收起 minsize=0）
        # 列 1：主预览画布（一直存在，t2i/i2i 通用）
        # 列 2/3：对比分隔线 / 对比图（仅"选取对比图"后才 grid）
        # 切换模式只改变列 0 的宽度，不影响 Notebook/imf 本身的整体尺寸。
        self._prev_host = tk.Frame(self.imf, bg="#111827")
        self._prev_host.pack(fill="both", expand=True)
        self._prev_host.columnconfigure(0, weight=0, minsize=0)
        self._prev_host.columnconfigure(1, weight=1)
        self._prev_host.columnconfigure(3, weight=1)
        self._prev_host.rowconfigure(0, weight=1)

        self._build_i2i_ref_column()  # 列 0，_switch_mode 按需 grid / grid_remove

        # 左半（A — 当前图）
        left_wrap = tk.Frame(self._prev_host, bg="#111827")
        left_wrap.grid(row=0, column=1, sticky="nsew")

        # Fix-2: A 侧横幅（初始隐藏，activate 时 pack）
        self._cmp_label_a = tk.Label(
            left_wrap, text="A →  " + _("compare_current"), font=F["small_b"], bg=C["cmp_a"], fg="white"
        )
        # 注：初始不 pack，在 _set_compare_image 中动态 pack

        self._prev_cv = tk.Canvas(left_wrap, bg="#111827", bd=0, highlightthickness=0)
        self._prev_cv.pack(fill="both", expand=True)
        self._prev_photo = None
        self._prev_item = None
        self._prev_outline = None
        self._prev_orig = None
        self._prev_ph = self._prev_cv.create_text(
            400,
            200,
            text=_("preview_placeholder_detailed"),
            font=F["body"],
            fill="#9ab4cc",
            anchor="center",
            justify="center",
        )
        self._prev_cv.bind("<Configure>", self._on_prev_resize)
        self._prev_cv.bind("<Double-Button-1>", lambda e: self.app._open_viewer())
        self._prev_cv.bind("<MouseWheel>", lambda e: "break")
        self._prev_cv.bind("<Button-4>", lambda e: "break")
        self._prev_cv.bind("<Button-5>", lambda e: "break")

        # 分隔线（对比时才 grid）
        self._cmp_divider = tk.Frame(self._prev_host, bg="#4a1d96", width=3)

        # 右半（B — 对比图）
        self._cmp_right_wrap = tk.Frame(self._prev_host, bg="#111827")

        # Fix-2: B 侧横幅 —— 在此 pack，跟随 _cmp_right_wrap 一同显示/隐藏
        self._cmp_label_b = tk.Label(
            self._cmp_right_wrap, text="B →  " + _("compare_image"), font=F["small_b"], bg=C["cmp_b"], fg="white"
        )
        self._cmp_label_b.pack(fill="x")  # ← Fix-2 补充此行

        self._cmp_cv = tk.Canvas(self._cmp_right_wrap, bg="#0a0f1a", bd=0, highlightthickness=0)
        self._cmp_cv.pack(fill="both", expand=True)
        self._cmp_cv.create_text(80, 50, text=_("compare_pick_hint"), font=F["input"], fill=C["text_muted"], anchor="center")
        self._cmp_cv.bind("<Configure>", self._on_cmp_resize)

    # ── 对比逻辑 ─────────────────────────────────────────────
    def _pick_compare_image(self):
        # DATA-003: 只取最近 200 张，避免大历史库全量加载
        entries = get_all_entries(limit=200)
        if not entries:
            messagebox.showinfo(_("dlg_tip"), _("dlg_compare_empty"))
            return

        win = tk.Toplevel(self.app.root)
        win.title(_("btn_pick_compare"))
        win.configure(bg=C["bg"])
        win.resizable(True, True)
        win.minsize(700, 500)
        win.update_idletasks()
        ww, wh = 980, 720
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - ww) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - wh) // 2
        win.geometry(f"{ww}x{wh}+{max(0, x)}+{max(0, y)}")
        win.grab_set()

        # ── 标题栏 ───────────────────────────────────────────
        hdr = tk.Frame(win, bg=C["acc"])
        hdr.pack(fill="x")
        tk.Label(hdr, text=_("compare_pick_title"), font=F["h2"], bg=C["acc"], fg="white").pack(
            side="left", padx=14, pady=10
        )
        tk.Button(
            hdr,
            text="📁 " + _("btn_export").strip(),
            font=F["body"],
            bg=C["hl"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: self._pick_cmp_file(win),
        ).pack(side="right", padx=12, pady=8)
        tk.Label(hdr, text=_("compare_recent_count", n=len(entries)), font=F["small"], bg=C["acc"], fg="#93c5fd").pack(
            side="right", padx=4
        )

        # ── 可滚动网格区域 ────────────────────────────────────
        outer = tk.Frame(win, bg=C["bg"])
        outer.pack(fill="both", expand=True)
        cv = tk.Canvas(outer, bg=C["bg"], bd=0, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(cv, bg=C["bg"])
        _w2 = cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfig(_w2, width=e.width))

        # 滚轮：绑到 win 级别，在窗口内任意位置均可滚动
        def _wheel(ev):
            try:
                cv.yview_scroll(int(-1 * (ev.delta / 120)), "units")
            except tk.TclError:
                pass

        def _wheel_linux(ev):
            try:
                cv.yview_scroll(-1 if ev.num == 4 else 1, "units")
            except tk.TclError:
                pass

        win.bind_all("<MouseWheel>", _wheel)
        win.bind_all("<Button-4>", _wheel_linux)
        win.bind_all("<Button-5>", _wheel_linux)
        win.protocol(
            "WM_DELETE_WINDOW",
            lambda: (
                win.unbind_all("<MouseWheel>"),
                win.unbind_all("<Button-4>"),
                win.unbind_all("<Button-5>"),
                win.destroy(),
            ),
        )

        # ── 网格参数 ──────────────────────────────────────────
        COLS = 4
        THUMB = 160  # 缩略图尺寸

        # Bug2 修复：
        # 旧代码 _tc = {} 是方法内局部变量，所有线程回调执行完毕后
        # Python GC 发现无活跃引用即释放 _tc，连带释放其中所有
        # PhotoImage —— Tkinter 的 C 层不计入 Python 引用计数，
        # 因此 Label 图像变黑。
        # 修复：将缓存绑定到 win 对象，生命周期与窗口相同。
        win._photo_cache = {}  # {path: PhotoImage}，跟随窗口存活

        # 有界线程池加载缩略图：此前每图起一个 daemon 线程，
        # 长历史（200 条）一次弹窗即 churn 200 线程
        _thumb_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cmp-thumb")

        def _shutdown_pool(event=None):
            if event is not None and getattr(event, "widget", None) is not win:
                return  # 子控件销毁事件不处理
            _thumb_pool.shutdown(wait=False)

        win.bind("<Destroy>", _shutdown_pool)

        def _select(path, dialog):
            dialog.unbind_all("<MouseWheel>")
            dialog.unbind_all("<Button-4>")
            dialog.unbind_all("<Button-5>")
            if path and os.path.exists(path):
                with open(path, "rb") as _fh:
                    data = _fh.read()
                self._set_compare_image(data)
            dialog.destroy()

        for i, e in enumerate(entries):
            path = e.get("image_path", "")
            ri, ci = divmod(i, COLS)
            inner.columnconfigure(ci, weight=1)

            # 格子容器
            cell = tk.Frame(inner, bg=C["panel"], highlightbackground="#2a3a5a", highlightthickness=1)
            cell.grid(row=ri, column=ci, padx=5, pady=5, sticky="nsew")
            cell.columnconfigure(0, weight=1)

            # 缩略图标签（居中，固定占位）
            img_host = tk.Frame(cell, bg="#0f172a", width=THUMB, height=THUMB)
            img_host.pack(padx=8, pady=(8, 0))
            img_host.pack_propagate(False)
            lbl = tk.Label(img_host, bg="#0f172a", text="⏳", font=F["disp_lg"], fg=C["text_muted"])
            lbl.pack(expand=True)

            # 异步加载缩略图
            # PhotoImage 必须在主线程创建（Tcl 限制），
            # 并存入 win._photo_cache 防止被 GC 回收。
            def _load_t(p=path, l=lbl):
                def _worker():
                    try:
                        if p and os.path.exists(p):
                            img = Image.open(p)
                            img.thumbnail((THUMB - 8, THUMB - 8), Image.LANCZOS)
                            canvas_img = Image.new("RGB", (THUMB - 8, THUMB - 8), (15, 23, 42))
                            ox = (canvas_img.width - img.width) // 2
                            oy = (canvas_img.height - img.height) // 2
                            canvas_img.paste(img, (ox, oy))

                            # 回到主线程创建 PhotoImage（Tkinter 单线程规则）
                            # 同时写入 win._photo_cache，与窗口共存亡，不被 GC
                            def _apply(ci=canvas_img, l_=l, p_=p):
                                try:
                                    if not l_.winfo_exists():
                                        return
                                    ph = ImageTk.PhotoImage(ci)  # 主线程创建
                                    win._photo_cache[p_] = ph  # 防 GC
                                    l_.config(image=ph, text="", width=THUMB - 8, height=THUMB - 8)
                                except Exception:
                                    pass

                            win.after(0, _apply)
                        else:

                            def _empty(l_=l):
                                try:
                                    if l_.winfo_exists():
                                        l_.config(text="🖼", font=F["display"])
                                except Exception:
                                    pass

                            win.after(0, _empty)
                    except Exception:
                        pass

                _thumb_pool.submit(_worker)

            _load_t()

            # 标题（显示更多字符，换行显示）
            title = self.app._display_title(e)
            ts = e.get("timestamp", "")[:16]
            prov = (e.get("provider") or "")[-22:]

            tk.Label(
                cell,
                text=title[:36],
                font=F["body_b"],
                bg=C["panel"],
                fg=C["text"],
                wraplength=THUMB + 10,
                justify="center",
            ).pack(pady=(6, 0), padx=6)
            tk.Label(
                cell, text=f"{ts}\n{prov}", font=F["mono_tiny"], bg=C["panel"], fg=C["sub"], justify="center"
            ).pack(pady=(2, 0))

            # 选取按钮
            tk.Button(
                cell,
                text=_("btn_pick_this"),
                font=F["body_b"],
                bg="#7c3aed",
                fg="white",
                bd=0,
                padx=14,
                pady=5,
                cursor="hand2",
                activebackground="#5b21b6",
                command=lambda p=path: _select(p, win),
            ).pack(pady=(6, 10))

    def _pick_cmp_file(self, dialog):
        path = filedialog.askopenfilename(
            title=_("compare_pick_file_title"),
            filetypes=[(_("filetype_images"), "*.png *.jpg *.jpeg *.webp"), (_("filetype_all"), "*.*")],
        )
        if path:
            with open(path, "rb") as _fh:
                data = _fh.read()
            self._set_compare_image(data)
        dialog.destroy()

    def _set_compare_image(self, data: bytes):
        self._cmp_orig = Image.open(io.BytesIO(data))
        self._cmp_mode = True
        self._prev_host.columnconfigure(1, weight=1)
        self._prev_host.columnconfigure(3, weight=1)
        # 显示 A 侧横幅（pack 在 canvas 上方）
        self._cmp_label_a.pack(fill="x", before=self._prev_cv)
        # 显示分隔线 & B 侧（列 2 / 3——列 0 留给图生图参考图侧栏）
        self._cmp_divider.grid(row=0, column=2, sticky="ns")
        self._cmp_right_wrap.grid(row=0, column=3, sticky="nsew")
        set_enabled(self._cmp_clear_btn, True)
        self._render_cmp()

    def _clear_compare(self):
        self._cmp_orig = None
        self._cmp_mode = False
        self._cmp_label_a.pack_forget()
        self._cmp_divider.grid_remove()
        self._cmp_right_wrap.grid_remove()
        set_enabled(self._cmp_clear_btn, False)

    def _render_cmp(self):
        if self._cmp_orig is None:
            return
        self._cmp_cv.update_idletasks()
        cw = self._cmp_cv.winfo_width() or 300
        ch = self._cmp_cv.winfo_height() or 400
        img = self._cmp_orig.copy()
        img.thumbnail((cw - 4, ch - 4), Image.LANCZOS)
        self._cmp_photo = ImageTk.PhotoImage(img)
        self._cmp_cv.delete("all")
        draw_image(self._cmp_cv, cw // 2, ch // 2, self._cmp_photo, "#0a0f1a")

    def _on_cmp_resize(self, event):
        if hasattr(self, "_cmp_resize_timer") and self._cmp_resize_timer:
            self.app.root.after_cancel(self._cmp_resize_timer)
        self._cmp_resize_timer = self.app.root.after(50, self._render_cmp)

    def _set_cmp_from_entry(self, e: dict):
        path = e.get("image_path", "")
        if path and os.path.exists(path):
            with open(path, "rb") as _fh:
                data = _fh.read()
            self._set_compare_image(data)
            self._nb.select(0)
            self.app._st(_("status_compare_set", title=self.app._display_title(e)), "ok")

    def _on_tools_row_resize(self, event=None):
        """工具行变窄时收起 Ctrl+Enter 提示，保证按钮不被挤压。

        提示是补充信息，按钮是操作入口。英文界面下提示占 137px，
        不收起时「变体生成」会被压到不可读。
        """
        lbl = getattr(self, "_shortcut_lbl", None)
        if lbl is None:
            return
        width = event.width if event is not None else lbl.master.winfo_width()
        need = lbl.winfo_reqwidth() + 12 + 660  # 提示 + 按钮组固定宽度
        if width >= need:
            if not lbl.winfo_ismapped():
                lbl.pack(side="left", padx=6)
        elif lbl.winfo_ismapped():
            lbl.pack_forget()

    def _on_preview_toolbar_resize(self, event=None):
        """工具栏变窄时收起次要提示，把宽度让给按钮。

        提示文字需要约 150px 才能完整显示；工具栏不足时它会挤占按钮空间，
        自己也被压成几像素的残片——两头不讨好。按钮是可操作内容，优先保留。
        """
        hint = getattr(self, "_dblclick_hint", None)
        if hint is None:
            return
        width = event.width if event is not None else hint.master.winfo_width()
        # 工具栏里按钮占用的固定宽度（实测 579px），提示完整显示另需约 156px。
        # 两者相加留出余量后，工具栏宽度不足就收起提示。
        need = hint.winfo_reqwidth() + 10 + 590
        if width >= need:
            if not hint.winfo_ismapped():
                hint.pack(side="right", padx=10)
        elif hint.winfo_ismapped():
            hint.pack_forget()

    def _on_prev_resize(self, event):
        if hasattr(self, "_prev_resize_timer") and self._prev_resize_timer:
            self.app.root.after_cancel(self._prev_resize_timer)
        self._prev_resize_timer = self.app.root.after(50, self._render_preview)

    def _on_ref_resize(self, event):
        """参考图缩略图 Canvas 尺寸随图生图侧栏动画过渡实时变化，
        用与 _on_prev_resize 相同的防抖节流重绘，避免动画期间抖动。"""
        if getattr(self, "_ref_resize_timer", None):
            self.app.root.after_cancel(self._ref_resize_timer)
        self._ref_resize_timer = self.app.root.after(
            30, self._update_ref_thumb if self._ref_image is not None else self._draw_ref_placeholder
        )

    def _render_preview(self):
        if self._prev_orig is None:
            return
        self._prev_cv.update_idletasks()
        cw = self._prev_cv.winfo_width() or 600
        ch = self._prev_cv.winfo_height() or 400
        img = self._prev_orig.copy()
        img.thumbnail((cw - 4, ch - 4), Image.LANCZOS)
        self._prev_photo = ImageTk.PhotoImage(img)
        self._prev_cv.delete("prev")
        self._prev_cv.itemconfig(self._prev_ph, text="")
        self._prev_item, self._prev_outline = draw_image(
            self._prev_cv, cw // 2, ch // 2, self._prev_photo, "#111827",
            tags=("prev",), outline_tags=("prev",),
        )

    def _set_preview(self, data: bytes):
        self._prev_orig = Image.open(io.BytesIO(data))
        self._render_preview()

    def _show_file(self, path: str):
        if path and os.path.exists(path):
            with open(path, "rb") as _fh:
                data = _fh.read()
            self.app._cur_bytes = data
            self._set_preview(data)

    def _update_char_count(self):
        """更新输入框字符计数标签（公开，供 PhrasePanel 等外部调用）。"""
        try:
            txt = self.pt.get("1.0", "end-1c")  # end-1c 排除末尾隐式换行
            n = len(txt)
            color = C["ok"] if n < 200 else C["warn"] if n < 400 else C["hl"]
            self._char_lbl.config(text=_("lbl_chars", n=n), fg=color)
        except Exception:
            pass

    def _copy_prompt(self):
        """将提示词文本框内容复制到系统剪贴板，并在字数标签短暂显示反馈。"""
        try:
            text = self.pt.get("1.0", "end-1c").strip()
            if not text:
                return
            self.app.root.clipboard_clear()
            self.app.root.clipboard_append(text)
            # 短暂显示 "✓ 已复制"，1.5s 后恢复字数统计
            self._char_lbl.config(text=_("copied_feedback"), fg=C["ok"])
            self.app.root.after(1500, self._update_char_count)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════
    #   生成模式切换 + 图生图参考图侧栏
    # ══════════════════════════════════════════════════════════
    _I2I_COL_W = 260  # 图生图参考图侧栏的宽度下限（预览 Tab 第 0 列）

    def _build_i2i_ref_column(self):
        """构建图生图参考图侧栏——预览 Tab 内 _prev_host 的第 0 列。

        对标 Automatic1111 img2img / ComfyUI 载入图像节点等主流图生图
        工具"左侧输入图 + 参数，右侧结果预览"的双栏布局。这一列默认不
        grid（t2i 模式下宽度为 0），由 _switch_mode 按需 grid /
        grid_remove，因此它的展开/收起只影响预览 Tab 内部的列宽度
        分配，不会牵动 Notebook 或状态栏的整体尺寸。

        # 图生图侧栏使用网格分配空间：上传、清除、强度和说明占固定行，
        # 参考图预览与紧凑接口摘要各自使用剩余空间，避免接口列表挤掉控件。
        """
        _BG = "#0d1d35"
        col = tk.Frame(self._prev_host, bg=_BG, highlightbackground="#1e3a5f", highlightthickness=1)
        self._i2i_ref_col = col
        # 注意：此处不 grid，由 _switch_mode 控制

        hdr = tk.Frame(col, bg="#122a4d")
        hdr.pack(side="top", fill="x")
        tk.Label(hdr, text=_("i2i_ref_title"), font=F["small_b"], bg="#122a4d", fg="white", anchor="w").pack(
            fill="x", padx=12, pady=8
        )

        body = tk.Frame(col, bg=_BG)
        body.pack(fill="both", expand=True, padx=10, pady=4)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1, minsize=36)
        body.rowconfigure(5, weight=1, minsize=42)

        # ── 参考图预览：最高优先级，可随可用高度伸缩 ─────────────
        self._ref_prev_cv = tk.Canvas(
            body,
            width=200,
            height=76,
            bg="#0a1525",
            bd=0,
            highlightthickness=1,
            highlightbackground="#1e3a5f",
            cursor="hand2",
        )
        self._ref_prev_cv.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        self._ref_prev_cv.bind("<Button-1>", lambda _: self._pick_ref_image())
        self._ref_prev_cv.bind("<Configure>", self._on_ref_resize)
        self._draw_ref_placeholder()

        btn_row = tk.Frame(body, bg=_BG)
        btn_row.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        self._ref_pick_btn = tk.Button(
            btn_row,
            text=_("btn_upload_ref"),
            font=F["small_b"],
            bg="#1d4ed8",
            fg="white",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            activebackground="#2563eb",
            command=self._pick_ref_image,
        )
        self._ref_pick_btn.pack(side="left", fill="x", expand=True)
        self._ref_clear_btn = tk.Button(
            btn_row,
            text=_("btn_clear"),
            font=F["small"],
            bg="#2a1018",
            fg="#f87171",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            state="disabled",
            command=self._clear_ref_image,
        )
        self._ref_clear_btn.pack(side="left", padx=(6, 0))

        str_row = tk.Frame(body, bg=_BG)
        str_row.grid(row=2, column=0, sticky="ew", pady=(0, 2))
        tk.Label(str_row, text=_("lbl_strength"), font=F["small_b"], bg=_BG, fg="#7dd3fc").pack(
            side="left", padx=(0, 8)
        )
        self._strength_slider = _StrengthSlider(str_row, self._ref_strength, w=120, h=30, marks=False)
        self._strength_slider.pack(side="left")
        self._strength_val_lbl = tk.Label(
            str_row, text=f"{self._ref_strength.get():.1f}", font=F["small_b"], bg=_BG, fg=C["ok"], width=3, anchor="w"
        )
        self._strength_val_lbl.pack(side="left", padx=(8, 0))
        self._ref_strength.trace("w", lambda *_: self._strength_val_lbl.config(text=f"{self._ref_strength.get():.1f}"))

        tk.Label(
            body,
            text=_("strength_description"),
            font=F["tiny"],
            bg="#102743",
            fg="#a8c7e8",
            anchor="w",
            padx=7,
            pady=3,
            wraplength=220,
            justify="left",
            highlightbackground="#1e4a72",
            highlightthickness=1,
        ).grid(row=3, column=0, sticky="ew", pady=(0, 3))

        # ── 低优先级信息：接口清单只使用预览剩余空间 ───────────
        self._ref_hint_frame = tk.Frame(body, bg=_BG)
        self._ref_hint_frame.grid(row=5, column=0, sticky="nsew")
        self._ref_hint_title = tk.Label(
            self._ref_hint_frame,
            text="",
            font=F["tiny"],
            bg=_BG,
            fg=C["text_muted"],
            anchor="nw",
            justify="left",
            wraplength=224,
        )
        self._ref_hint_title.pack(fill="x")
        # 图生图接口在紧凑侧栏中只显示为摘要，避免多行列表挤掉上传与强度控件。
        self._ref_hint_rows: list = []

    def _i2i_selectable_providers(self) -> list:
        """支持图生图、且能在现有向导里配置 Key 的接口。

        真实条件是「向导里有没有该接口的 Key 配置卡片」，而不是
        「属于免费/付费分类」。两者并不等价：volcengine_ark 属于
        commercial，但 wizard_paid.py 已有完整卡片，用户配好即可用；
        fal_flux 同属 commercial 却没有任何配置入口，选中只会得到
        一个无从下手的报错。

        因此以 WIZARD_CONFIGURED 为准。新增向导卡片时在注册表登记，
        这里无需改动。
        """
        from services.providers import WIZARD_CONFIGURED

        return [n for n in IMG2IMG_PROVIDERS if n in WIZARD_CONFIGURED]

    def _update_ref_hint(self, i2i_list: list):
        """把图生图可用接口名称以竖向分行方式填入侧栏提示区。
        每次调用先销毁旧行再重建，保证列表长度变化时不会残留旧标签。
        """
        _BG = "#0d1d35"
        for lbl in self._ref_hint_rows:
            lbl.destroy()
        self._ref_hint_rows.clear()

        if not i2i_list:
            self._ref_hint_title.config(text=_("i2i_no_providers"), fg="#f87171")
            return

        # 提示区展示的是 stable id，需先映射成简短标签。
        # （历史实现直接对 id 做 display-name 的 replace，全部落空。）
        names = [_i2i_short_label(pid) for pid in i2i_list]
        self._ref_hint_title.config(
            text=(
                _("i2i_available_providers", n=len(names)) + "\n" + " · ".join(names[:3]) + "\n" + " · ".join(names[3:])
            ),
            fg="#86efac",
        )

    def _expand_provider_popup(self):
        """postcommand：把弹出 Listbox 撑到最长条目的实际像素宽。

        ttk.Combobox 的 width 只控制输入框字符数，弹出框（内部 tk.Listbox）
        的列宽由 Tk 固定为 20，与 values 无关。旧实现试图通过重排 values
        让 Tk 重算列宽——实测无效，Listbox 的 -width 恒为 20，长名称仍被
        截断。唯一有效途径是直接配置 popdown 里那个 Listbox 的 -width。
        """
        try:
            cb = self._provider_cb
            vals = cb.cget("values") or []
            if not vals:
                return
            # 终端列宽：CJK 与 emoji 占 2 列，其余占 1 列
            widest = max(vals, key=lambda v: sum(2 if ord(ch) > 0x2E80 else 1 for ch in v))
            cols = sum(2 if ord(ch) > 0x2E80 else 1 for ch in widest) + 2
            popdown = cb.tk.call("ttk::combobox::PopdownWindow", cb._w)
            cb.tk.call(popdown + ".f.l", "configure", "-width", str(cols))
        except Exception:
            pass  # 弹出框尚未创建或平台实现不同：退回 Tk 默认宽度

    def _switch_mode(self, mode: str):
        """切换文生图/图生图。

        图生图的参考图侧栏固定在预览 Tab 内部（_prev_host 第 0 列），
        而不是插在主布局里的额外一行——切换模式只改变这一列的宽度
        （0 ↔ _I2I_COL_W），预览/变体/队列/调试日志几个 Notebook Tab
        以及查看器窗口的整体尺寸完全不受影响，不会因为切换模式而
        整体跳动或改变可用画布区域的高度。

        列宽是瞬时切换的：预览画布会因此收到一次 <Configure>，由
        _on_prev_resize 的 50ms 防抖合并成一次重绘。逐帧改列宽做不到
        ——侧栏的自然宽度（约 278px）大于 _I2I_COL_W，grid 会把
        minsize 顶回去，除非关掉 propagate 并手工维护高度。

        图生图模式下，接口下拉框会被强制收窄为真正支持图生图的接口
        （见 _i2i_selectable_providers）——此前选中其他接口时参考图会
        被静默忽略，退化成纯文生图。批量生成 / 加入队列两个入口在
        图生图模式下被锁定，因为这两条链路目前都不会传递参考图。
        """
        prev_mode = self._gen_mode
        self._gen_mode = mode
        if mode == prev_mode:
            return

        if mode == "t2i":
            self._mode_t2i_btn.config(bg=C["hl"], fg="white")
            self._mode_i2i_btn.config(bg=C["panel"], fg=C["sub"])

            self._provider_cb.config(values=self._t2i_provider_list)
            if self._pre_i2i_provider is not None:
                self.pv.set(self._pre_i2i_provider)
                self._pre_i2i_provider = None

            self._set_batch_i2i_lock(False)
            # 收起：先把列宽归零再移出网格。列宽归零后预览画布立即拿到
            # 全部宽度，_on_prev_resize 的 50ms 防抖只重绘一次。
            self._prev_host.columnconfigure(0, minsize=0)
            self._i2i_ref_col.grid_remove()
        else:
            self._mode_t2i_btn.config(bg=C["panel"], fg=C["sub"])
            self._mode_i2i_btn.config(bg="#1d4ed8", fg="white")

            self._i2i_ref_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

            i2i_list = self._i2i_selectable_providers()
            self._update_ref_hint(i2i_list)

            # pv 保存的是 display name，i2i_list 是 stable id，比较前统一映射。
            i2i_display = [_provider_display(n) for n in i2i_list]
            self._pre_i2i_provider = self.pv.get()
            self._provider_cb.config(values=i2i_display)
            if self.pv.get() not in i2i_display and i2i_display:
                self.pv.set(i2i_display[0])

            self._set_batch_i2i_lock(True)
            # 展开：侧栏自然宽度由内容决定（约 278px），列 minsize 只需
            # 覆盖到它；预览画布的 <Configure> 随后触发一次防抖重绘。
            self._prev_host.columnconfigure(0, minsize=self._I2I_COL_W)

    def _set_batch_i2i_lock(self, locked: bool):
        """批量生成 / 加入队列在图生图模式下暂不支持参考图，锁定这两个
        入口并给出提示，避免用户以为批量结果也套用了参考图。"""
        if locked:
            set_enabled(
                self._variant_gen_btn, False,
                bg=C["dis_bg"], text=_("btn_variant_gen") + _("i2i_not_supported"),
            )
        else:
            set_enabled(
                self._variant_gen_btn, True,
                bg=self._variant_gen_btn_bg, text=_("btn_variant_gen"),
            )
        if hasattr(self, "_queue_panel"):
            self._queue_panel.set_img2img_lock(locked)

    def _draw_ref_placeholder(self):
        """在参考图预览 Canvas 上绘制占位符（尺寸取实际渲染宽高，
        侧栏展开动画期间会随每一帧的宽度实时重绘）。"""
        cv = self._ref_prev_cv
        cv.delete("all")
        w = cv.winfo_width() or 200
        h = cv.winfo_height() or 160
        if h < 68:
            cv.create_text(w // 2, h // 2, text=_("ref_upload_hint"), font=F["tiny"], fill=C["text_muted"])
            return
        # 图标按图形对象算 3:1（#4a8ac0 在此底色上 4.96:1），
        # 提示文字是正文，用与队列空态一致的前景色
        cv.create_text(w // 2, h // 2 - 16, text="🖼", font=(F["_sans"], 30), fill="#4a8ac0")
        cv.create_text(w // 2, h // 2 + 22, text=_("ref_upload_hint"), font=F["small"], fill=C["text_muted"])

    def _update_ref_thumb(self):
        """将参考图字节渲染为预览缩略图（尺寸取实际渲染宽高）。"""
        if self._ref_image is None:
            self._draw_ref_placeholder()
            return
        try:
            cv = self._ref_prev_cv
            w = cv.winfo_width() or 200
            h = cv.winfo_height() or 160
            img = Image.open(io.BytesIO(self._ref_image))
            img.thumbnail((max(w - 8, 1), max(h - 8, 1)), Image.LANCZOS)
            self._ref_thumb_photo = ImageTk.PhotoImage(img)
            cv.delete("all")
            cv.create_image(w // 2, h // 2, image=self._ref_thumb_photo, anchor="center")
        except Exception:
            self._draw_ref_placeholder()

    def _pick_ref_image(self):
        """弹出文件选择器，读取参考图字节并更新预览和 UI 状态。"""
        path = filedialog.askopenfilename(
            title=_("ref_pick_title"),
            filetypes=[(_("filetype_images"), "*.png *.jpg *.jpeg *.webp *.bmp"), (_("filetype_all"), "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "rb") as _fh:
                self._ref_image = _fh.read()
            set_enabled(self._ref_clear_btn, True)
            self._ref_pick_btn.config(text=_("btn_change_ref"))
            self._update_ref_thumb()
            self.app._cur_bytes = self._ref_image
            self._set_preview(self._ref_image)
        except Exception as e:
            self._ref_image = None
            self._ref_pick_btn.config(text=_("ref_read_failed"))
            self.app._st(_("err_ref_read", detail=e), "err")

    def _clear_ref_image(self):
        """清除参考图，恢复占位符。"""
        self._ref_image = None
        self._ref_thumb_photo = None
        set_enabled(self._ref_clear_btn, False)
        self._ref_pick_btn.config(text=_("btn_upload_ref"))
        self._draw_ref_placeholder()
