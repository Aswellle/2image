"""
ui/wizard_paid.py  v3
──────────────────────
付费接口配置向导。

v3 新增：
  · GPT-Image 模型选择 — 支持 gpt-image-1/1.5/2/2.5-flare/2.5-sunburst
  · 火山引擎豆包 — 豆包 Seedream 3.0/4.0 文生图 + SeedEdit 3.0 图生图
  · 模型下拉使用人类可读名称（内部映射到 model ID）
"""

import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from typing import Callable

from config.fonts import F
from config.i18n import _
from config.model_catalog import (
    ARK_IMAGE_DEFAULT,
    ARK_IMAGE_MODELS,
    ARK_IMAGE_NAMES,
    BFL_IMAGE_NAMES,
    BFL_TXT2IMG_DEFAULT,
    GPT_IMAGE_DEFAULT,
    GPT_IMAGE_NAMES,
    MINIMAX_IMAGE_DEFAULT,
    MINIMAX_IMAGE_MODELS,
    MINIMAX_IMAGE_NAMES,
    RECRAFT_DEFAULT,
    RECRAFT_IMAGE_NAMES,
    RECRAFT_MODELS,
    XAI_IMAGE_DEFAULT,
    XAI_IMAGE_MODELS,
    XAI_IMAGE_NAMES,
)
from config.theme import DARK_THEME as C
from services.generation.budget import parse_budget_input
from services.providers.replicate_flux import MODEL_ORDER as REPLICATE_MODEL_ORDER
from services.providers.replicate_flux import REPLICATE_IMAGE_NAMES
from config.ui_geometry import scaled
from ui.components import bind_wraplength
from ui.tooltip import attach_tooltip
from ui.icons import glyph, icon_font


class PaidWizard(tk.Toplevel):
    """付费接口（OpenAI / Stability AI / Replicate / xAI / 豆包）配置窗口。"""

    def __init__(self, parent: tk.Tk, cfg: dict, on_save: Callable[[dict], None]):
        super().__init__(parent)
        self.transient(parent)  # 模态归属主窗：grab 期间点击外部不会推到主窗后面
        self.cfg = cfg.copy()  # 编辑副本，避免未保存的修改污染主配置
        self.on_save = on_save
        self._closing = False
        self._dirty = False
        self.title(_("wizard_paid_title"))
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.minsize(scaled(self, 680), scaled(self, 560))
        self.focus_set()
        self.update_idletasks()
        # 窗口几何按缩放系数放大并钳制屏幕
        w = scaled(self, 820)
        sh = self.winfo_screenheight()
        h = min(scaled(self, 720), sh - 80)
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        self._build()
        for _var in [
            self.oai_var,
            self.gpt_image_model_var,
            self.gpt_image_quality_var,
            self.stab_var,
            self.stab_model_var,
            self.repl_var,
            self.repl_model_var,
            self.ark_var,
            self.ark_model_var,
            self.bfl_var,
            self.bfl_model_var,
            self.xai_var,
            self.xai_model_var,
            self.ideo_var,
            self.fal_var,
            self.recraft_var,
            self.recraft_model_var,
            self.recraft_style_var,
            self.mm_var,
            self.mm_model_var,
            self.paid_opt_var,
            self.budget_var,
        ]:
            _var.trace("w", lambda *_: setattr(self, "_dirty", True))
        self.bind("<Escape>", lambda _e: self._on_close())
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.grab_set()

    def _on_close(self):
        """关闭窗口前先解绑 bind_all，防止 Canvas 销毁后仍触发 TclError。"""
        if self._dirty and not self._closing:
            if not messagebox.askyesno(
                _("wz_close_title"), _("wz_close_msg"), parent=self, icon="warning", default=messagebox.NO
            ):
                return
        self._closing = True
        try:
            self.unbind_all("<MouseWheel>")
            self.unbind_all("<Button-4>")
            self.unbind_all("<Button-5>")
        except tk.TclError:
            pass
        self.destroy()

    def _build(self):
        PX = 24

        # 副标题独占标题下方整行并按行宽折行（高 DPI 下同行布局会
        # 超出固定窗宽被裁，堆叠后任意缩放/语言都稳健）
        hdr = tk.Frame(self, bg=C["paid"])
        hdr.pack(fill="x")
        tk.Label(hdr, text=_("wizard_paid_header_title"), font=F["title"], bg=C["paid"], fg="white").pack(
            anchor="w", padx=20, pady=(14, 2)
        )
        hdr_sub = tk.Label(
            hdr,
            text=_("wizard_paid_header_subtitle"),
            font=F["body_b"],
            bg=C["paid"],
            fg=C["purple_soft"],
            anchor="w",
            justify="left",
        )
        hdr_sub.pack(fill="x", padx=20, pady=(0, 10))
        bind_wraplength(hdr, [hdr_sub], padx_total=40, floor=200)

        bot = tk.Frame(self, bg=C["panel"])
        bot.pack(fill="x", side="bottom")
        tk.Button(
            bot,
            text=_("wizard_paid_btn_save"),
            font=F["h2"],
            bg=C["ok"],
            fg=C["ok_fg"],
            bd=0,
            padx=24,
            pady=10,
            cursor="hand2",
            command=self._save,
        ).pack(side="right", padx=20, pady=12)
        tk.Button(
            bot,
            text=_("btn_close"),
            font=F["body"],
            bg=C["panel"],
            fg=C["sub"],
            bd=0,
            padx=16,
            pady=10,
            cursor="hand2",
            command=self._on_close,
        ).pack(side="right", pady=12)

        fo = tk.Frame(self, bg=C["bg"])
        fo.pack(fill="both", expand=True)
        cv = tk.Canvas(fo, bg=C["bg"], bd=0, highlightthickness=0)
        vsb = ttk.Scrollbar(fo, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(cv, bg=C["bg"])
        cwin = cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfig(cwin, width=e.width))

        def _scroll_win(e):
            if self._closing:
                return
            try:
                cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except tk.TclError:
                pass

        def _scroll_up(e):
            if self._closing:
                return
            try:
                cv.yview_scroll(-1, "units")
            except tk.TclError:
                pass

        def _scroll_dn(e):
            if self._closing:
                return
            try:
                cv.yview_scroll(1, "units")
            except tk.TclError:
                pass

        self.bind_all("<MouseWheel>", _scroll_win)
        self.bind_all("<Button-4>", _scroll_up)
        self.bind_all("<Button-5>", _scroll_dn)

        # ══ 1. OpenAI GPT-Image ══
        self._section(inner, "💡", _("wizard_paid_openai_section_title"), _("wizard_paid_openai_section_sub"), PX)
        self._info_card(
            inner,
            [
                _("wizard_paid_openai_info_1"),
                _("wizard_paid_openai_info_2"),
                _("wizard_paid_openai_info_3"),
                _("wizard_paid_openai_info_4"),
                _("wizard_paid_openai_info_5"),
            ],
            PX,
        )
        row1 = tk.Frame(inner, bg=C["bg"])
        row1.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(row1, text=_("wizard_paid_openai_key_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef1 = tk.Frame(row1, bg=C["entry"])
        ef1.pack(fill="x", pady=(4, 0))
        self.oai_var = tk.StringVar(value=self.cfg.get("openai_key", ""))
        self.oai_ent = tk.Entry(
            ef1,
            textvariable=self.oai_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.oai_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef1, self.oai_ent)

        opt1 = tk.Frame(inner, bg=C["bg"])
        opt1.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(opt1, text=_("wizard_paid_model_label"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self._gpt_image_name_to_id = {v: k for k, v in GPT_IMAGE_NAMES.items()}
        self.gpt_image_model_var = tk.StringVar(
            value=GPT_IMAGE_NAMES.get(self.cfg.get("gpt_image_model", GPT_IMAGE_DEFAULT), GPT_IMAGE_DEFAULT)
        )
        ttk.Combobox(
            opt1,
            textvariable=self.gpt_image_model_var,
            width=30,
            state="readonly",
            values=list(GPT_IMAGE_NAMES.values()),
        ).pack(side="left", padx=(6, 20))
        tk.Label(opt1, text=_("wizard_paid_quality_label"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self.gpt_image_quality_var = tk.StringVar(value=self.cfg.get("gpt_image_quality", "auto"))
        ttk.Combobox(
            opt1,
            textvariable=self.gpt_image_quality_var,
            width=12,
            state="readonly",
            values=["auto", "low", "medium", "high"],
        ).pack(side="left", padx=(6, 20))

        btns1 = tk.Frame(inner, bg=C["bg"])
        btns1.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns1, _("wizard_paid_openai_register_btn"), "https://platform.openai.com/account/billing")
        self._link_btn(btns1, _("wizard_paid_openai_key_btn"), "https://platform.openai.com/api-keys")
        self._divider(inner)

        # ══ 2. Stability AI ══
        self._section(inner, "🎨", _("wizard_paid_stability_section_title"), _("wizard_paid_stability_section_sub"), PX)
        self._info_card(
            inner,
            [
                _("wizard_paid_stability_info_1"),
                _("wizard_paid_stability_info_2"),
            ],
            PX,
        )
        row2 = tk.Frame(inner, bg=C["bg"])
        row2.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(row2, text=_("wizard_paid_stability_key_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(
            anchor="w"
        )
        ef2 = tk.Frame(row2, bg=C["entry"])
        ef2.pack(fill="x", pady=(4, 0))
        self.stab_var = tk.StringVar(value=self.cfg.get("stability_key", ""))
        self.stab_ent = tk.Entry(
            ef2,
            textvariable=self.stab_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.stab_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef2, self.stab_ent)
        opt2 = tk.Frame(inner, bg=C["bg"])
        opt2.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(opt2, text=_("wizard_paid_stability_model_label"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(
            side="left"
        )
        self.stab_model_var = tk.StringVar(value=self.cfg.get("stability_model", "core"))
        ttk.Combobox(
            opt2, textvariable=self.stab_model_var, width=18, state="readonly", values=["core", "ultra", "sd3.5-large"]
        ).pack(side="left", padx=(6, 0))
        tk.Label(opt2, text=_("wizard_paid_stability_model_hint"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(
            side="left", padx=8
        )
        btns2 = tk.Frame(inner, bg=C["bg"])
        btns2.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns2, _("wizard_paid_stability_register_btn"), "https://platform.stability.ai/")
        self._link_btn(btns2, _("wizard_paid_stability_key_btn"), "https://platform.stability.ai/account/keys")
        self._divider(inner)

        # ══ 3. Replicate ══
        self._section(inner, "🔮", _("wizard_paid_replicate_section_title"), _("wizard_paid_replicate_section_sub"), PX)
        self._info_card(
            inner,
            [
                _("wizard_paid_replicate_info_1"),
                _("wizard_paid_replicate_info_2"),
                _("wizard_paid_replicate_info_3"),
            ],
            PX,
        )
        row3 = tk.Frame(inner, bg=C["bg"])
        row3.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(row3, text=_("wizard_paid_replicate_key_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(
            anchor="w"
        )
        ef3 = tk.Frame(row3, bg=C["entry"])
        ef3.pack(fill="x", pady=(4, 0))
        self.repl_var = tk.StringVar(value=self.cfg.get("replicate_key", ""))
        self.repl_ent = tk.Entry(
            ef3,
            textvariable=self.repl_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.repl_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef3, self.repl_ent)
        opt3 = tk.Frame(inner, bg=C["bg"])
        opt3.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(opt3, text=_("wizard_paid_model_label"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self._replicate_name_to_id = {v: k for k, v in REPLICATE_IMAGE_NAMES.items()}
        self.repl_model_var = tk.StringVar(
            value=REPLICATE_IMAGE_NAMES.get(self.cfg.get("replicate_model", "flux-2-pro"), "flux-2-pro")
        )
        ttk.Combobox(
            opt3,
            textvariable=self.repl_model_var,
            width=26,
            state="readonly",
            values=[REPLICATE_IMAGE_NAMES.get(m, m) for m in REPLICATE_MODEL_ORDER],
        ).pack(side="left", padx=(6, 0))
        btns3 = tk.Frame(inner, bg=C["bg"])
        btns3.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns3, _("wizard_paid_replicate_register_btn"), "https://replicate.com/")
        self._link_btn(btns3, _("wizard_paid_replicate_token_btn"), "https://replicate.com/account/api-tokens")
        self._divider(inner)

        # ══ 4. 火山引擎豆包 (v3 新增) ══
        self._section(inner, "🫘", _("wizard_paid_ark_section_title"), _("wizard_paid_ark_section_sub"), PX)
        self._info_card(
            inner,
            [
                _("wizard_paid_ark_info_1"),
                _("wizard_paid_ark_info_2"),
                _("wizard_paid_ark_info_3"),
                _("wizard_paid_ark_info_4"),
                _("wizard_paid_ark_info_5"),
            ],
            PX,
        )
        row4 = tk.Frame(inner, bg=C["bg"])
        row4.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(row4, text=_("wizard_paid_ark_key_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef4 = tk.Frame(row4, bg=C["entry"])
        ef4.pack(fill="x", pady=(4, 0))
        self.ark_var = tk.StringVar(value=self.cfg.get("volcengine_key", ""))
        self.ark_ent = tk.Entry(
            ef4,
            textvariable=self.ark_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.ark_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef4, self.ark_ent)
        opt4 = tk.Frame(inner, bg=C["bg"])
        opt4.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(opt4, text=_("wizard_paid_model_label"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self._ark_name_to_id = {v: k for k, v in ARK_IMAGE_NAMES.items()}
        self.ark_model_var = tk.StringVar(
            value=ARK_IMAGE_NAMES.get(self.cfg.get("ark_model", ARK_IMAGE_DEFAULT), ARK_IMAGE_DEFAULT)
        )
        ttk.Combobox(
            opt4,
            textvariable=self.ark_model_var,
            width=28,
            state="readonly",
            values=[ARK_IMAGE_NAMES.get(m, m) for m in ARK_IMAGE_MODELS],
        ).pack(side="left", padx=(6, 0))
        tk.Label(opt4, text=_("wizard_paid_ark_model_hint"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(
            side="left", padx=8
        )
        btns4 = tk.Frame(inner, bg=C["bg"])
        btns4.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns4, _("wizard_paid_ark_register_btn"), "https://www.volcengine.com/")
        self._link_btn(
            btns4, _("wizard_paid_ark_key_btn"), "https://console.volcengine.com/ark/region:ark+cn-beijing/overview"
        )
        self._divider(inner)

        # ══ 5. Black Forest Labs ══
        self._section(inner, "🌲", _("wizard_paid_bfl_section_title"), _("wizard_paid_bfl_section_sub"), PX)
        self._info_card(
            inner,
            [
                _("wizard_paid_bfl_info_1"),
                _("wizard_paid_bfl_info_2"),
                _("wizard_paid_bfl_info_3"),
            ],
            PX,
        )
        row5 = tk.Frame(inner, bg=C["bg"])
        row5.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(row5, text=_("wizard_paid_bfl_key_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef5 = tk.Frame(row5, bg=C["entry"])
        ef5.pack(fill="x", pady=(4, 0))
        self.bfl_var = tk.StringVar(value=self.cfg.get("bfl_key", ""))
        self.bfl_ent = tk.Entry(
            ef5,
            textvariable=self.bfl_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.bfl_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef5, self.bfl_ent)
        opt5 = tk.Frame(inner, bg=C["bg"])
        opt5.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(opt5, text=_("wizard_paid_model_label"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self._bfl_name_to_id = {v: k for k, v in BFL_IMAGE_NAMES.items()}
        self.bfl_model_var = tk.StringVar(
            value=BFL_IMAGE_NAMES.get(self.cfg.get("bfl_model", BFL_TXT2IMG_DEFAULT), BFL_TXT2IMG_DEFAULT)
        )
        ttk.Combobox(
            opt5,
            textvariable=self.bfl_model_var,
            width=24,
            state="readonly",
            values=list(BFL_IMAGE_NAMES.values()),
        ).pack(side="left", padx=(6, 0))
        btns5 = tk.Frame(inner, bg=C["bg"])
        btns5.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns5, _("wizard_paid_bfl_register_btn"), "https://dashboard.bfl.ai")
        self._link_btn(btns5, _("wizard_paid_bfl_key_btn"), "https://dashboard.bfl.ai/get-started")
        self._divider(inner)

        # ══ 6. xAI Grok Imagine ══
        self._section(inner, "🤖", _("wizard_paid_xai_section_title"), _("wizard_paid_xai_section_sub"), PX)
        self._info_card(
            inner,
            [
                _("wizard_paid_xai_info_1"),
                _("wizard_paid_xai_info_2"),
                _("wizard_paid_xai_info_3"),
            ],
            PX,
        )
        self.xai_var = self._key_field(inner, _("wizard_paid_xai_key_label"), self.cfg.get("xai_key", ""), PX)
        opt6 = tk.Frame(inner, bg=C["bg"])
        opt6.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(opt6, text=_("wizard_paid_model_label"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self._xai_name_to_id = {v: k for k, v in XAI_IMAGE_NAMES.items()}
        self.xai_model_var = tk.StringVar(
            value=XAI_IMAGE_NAMES.get(self.cfg.get("xai_model", XAI_IMAGE_DEFAULT), XAI_IMAGE_DEFAULT)
        )
        ttk.Combobox(
            opt6,
            textvariable=self.xai_model_var,
            width=26,
            state="readonly",
            values=[XAI_IMAGE_NAMES.get(m, m) for m in XAI_IMAGE_MODELS],
        ).pack(side="left", padx=(6, 0))
        btns6 = tk.Frame(inner, bg=C["bg"])
        btns6.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns6, _("wizard_paid_xai_register_btn"), "https://x.ai/api")
        self._link_btn(btns6, _("wizard_paid_xai_key_btn"), "https://console.x.ai")
        self._divider(inner)

        # ══ 7. Ideogram v4（商业）══
        self._section(inner, "🅰", _("wizard_paid_ideogram_section_title"), _("wizard_paid_ideogram_section_sub"), PX)
        self._info_card(
            inner,
            [
                _("wizard_paid_ideogram_info_1"),
                _("wizard_paid_ideogram_info_2"),
                _("wizard_paid_ideogram_info_3"),
            ],
            PX,
        )
        self.ideo_var = self._key_field(
            inner, _("wizard_paid_ideogram_key_label"), self.cfg.get("ideogram_key", ""), PX
        )
        btns7 = tk.Frame(inner, bg=C["bg"])
        btns7.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns7, _("wizard_paid_ideogram_register_btn"), "https://ideogram.ai/")
        self._link_btn(btns7, _("wizard_paid_ideogram_key_btn"), "https://ideogram.ai/manage-api")
        self._divider(inner)

        # ══ 8. fal.ai FLUX.2 Pro（商业）══
        self._section(inner, "⚡", _("wizard_paid_fal_section_title"), _("wizard_paid_fal_section_sub"), PX)
        self._info_card(
            inner,
            [
                _("wizard_paid_fal_info_1"),
                _("wizard_paid_fal_info_2"),
                _("wizard_paid_fal_info_3"),
            ],
            PX,
        )
        self.fal_var = self._key_field(inner, _("wizard_paid_fal_key_label"), self.cfg.get("fal_key", ""), PX)
        btns8 = tk.Frame(inner, bg=C["bg"])
        btns8.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns8, _("wizard_paid_fal_register_btn"), "https://fal.ai/")
        self._link_btn(btns8, _("wizard_paid_fal_key_btn"), "https://fal.ai/dashboard/keys")
        self._divider(inner)

        # ══ 9. Recraft V4.1（商业）══
        self._section(inner, "🎭", _("wizard_paid_recraft_section_title"), _("wizard_paid_recraft_section_sub"), PX)
        self._info_card(
            inner,
            [
                _("wizard_paid_recraft_info_1"),
                _("wizard_paid_recraft_info_2"),
                _("wizard_paid_recraft_info_3"),
            ],
            PX,
        )
        self.recraft_var = self._key_field(
            inner, _("wizard_paid_recraft_key_label"), self.cfg.get("recraft_key", ""), PX
        )
        opt9 = tk.Frame(inner, bg=C["bg"])
        opt9.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(opt9, text=_("wizard_paid_model_label"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self._recraft_name_to_id = {v: k for k, v in RECRAFT_IMAGE_NAMES.items()}
        self.recraft_model_var = tk.StringVar(
            value=RECRAFT_IMAGE_NAMES.get(self.cfg.get("recraft_model", RECRAFT_DEFAULT), RECRAFT_DEFAULT)
        )
        ttk.Combobox(
            opt9,
            textvariable=self.recraft_model_var,
            width=22,
            state="readonly",
            values=[RECRAFT_IMAGE_NAMES.get(m, m) for m in RECRAFT_MODELS],
        ).pack(side="left", padx=(6, 18))
        tk.Label(opt9, text=_("wizard_paid_recraft_style_label"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(
            side="left"
        )
        self._recraft_style_labels = [
            ("realistic_image", _("wizard_paid_recraft_style_realistic")),
            ("digital_illustration", _("wizard_paid_recraft_style_digital")),
            ("vector_illustration", _("wizard_paid_recraft_style_vector")),
        ]
        current_style = self.cfg.get("recraft_style", "realistic_image")
        current_style_label = next(
            (label for code, label in self._recraft_style_labels if code == current_style),
            self._recraft_style_labels[0][1],
        )
        self.recraft_style_var = tk.StringVar(value=current_style_label)
        ttk.Combobox(
            opt9,
            textvariable=self.recraft_style_var,
            width=16,
            state="readonly",
            values=[label for _, label in self._recraft_style_labels],
        ).pack(side="left", padx=(6, 0))
        btns9 = tk.Frame(inner, bg=C["bg"])
        btns9.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns9, _("wizard_paid_recraft_register_btn"), "https://www.recraft.ai/")
        self._link_btn(btns9, _("wizard_paid_recraft_key_btn"), "https://www.recraft.ai/profile/api")
        self._divider(inner)

        # ══ 10. MiniMax H3 Image（商业）══
        self._section(inner, "🌀", _("wizard_paid_minimax_section_title"), _("wizard_paid_minimax_section_sub"), PX)
        self._info_card(
            inner,
            [
                _("wizard_paid_minimax_info_1"),
                _("wizard_paid_minimax_info_2"),
                _("wizard_paid_minimax_info_3"),
            ],
            PX,
        )
        self.mm_var = self._key_field(inner, _("wizard_paid_minimax_key_label"), self.cfg.get("minimax_key", ""), PX)
        opt10 = tk.Frame(inner, bg=C["bg"])
        opt10.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(opt10, text=_("wizard_paid_model_label"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self._mm_name_to_id = {v: k for k, v in MINIMAX_IMAGE_NAMES.items()}
        self.mm_model_var = tk.StringVar(
            value=MINIMAX_IMAGE_NAMES.get(self.cfg.get("minimax_model", MINIMAX_IMAGE_DEFAULT), MINIMAX_IMAGE_DEFAULT)
        )
        ttk.Combobox(
            opt10,
            textvariable=self.mm_model_var,
            width=28,
            state="readonly",
            values=[MINIMAX_IMAGE_NAMES.get(m, m) for m in MINIMAX_IMAGE_MODELS],
        ).pack(side="left", padx=(6, 0))
        btns10 = tk.Frame(inner, bg=C["bg"])
        btns10.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns10, _("wizard_paid_minimax_register_btn"), "https://platform.minimax.io/")
        self._link_btn(
            btns10,
            _("wizard_paid_minimax_key_btn"),
            "https://platform.minimax.io/user-center/basic-information/interface-key",
        )
        self._divider(inner)

        # ══ 11. 自动路由与付费预算 ══
        self._section(inner, "🧭", _("wizard_paid_routing_section_title"), _("wizard_paid_routing_section_sub"), PX)
        route_card = tk.Frame(inner, bg=C["panel"], highlightbackground=C["sep"], highlightthickness=1)
        route_card.pack(fill="x", padx=PX, pady=(4, 0))
        route_inner = tk.Frame(route_card, bg=C["panel"])
        route_inner.pack(fill="x", padx=16, pady=10)
        self.paid_opt_var = tk.BooleanVar(value=bool(self.cfg.get("paid_auto_opt_in", False)))
        tk.Checkbutton(
            route_inner,
            text=_("wizard_paid_routing_opt_in"),
            variable=self.paid_opt_var,
            font=F["btn"],
            bg=C["panel"],
            fg=C["text"],
            activebackground=C["panel"],
            activeforeground=C["text"],
            selectcolor=C["entry"],
            anchor="w",
        ).pack(fill="x", anchor="w")
        opt_hint = tk.Label(
            route_inner,
            text=_("wizard_paid_routing_opt_in_hint"),
            font=F["small"],
            bg=C["panel"],
            fg=C["text_muted"],
            anchor="w",
            justify="left",
        )
        opt_hint.pack(fill="x", anchor="w", pady=(2, 8))
        budget_row = tk.Frame(route_inner, bg=C["panel"])
        budget_row.pack(fill="x")
        tk.Label(budget_row, text=_("wizard_paid_budget_label"), font=F["body"], bg=C["panel"], fg=C["sub"]).pack(
            side="left"
        )
        budget_initial = parse_budget_input(self.cfg.get("paid_daily_budget_usd", 2.0), default=2.0)
        self.budget_var = tk.StringVar(value=f"{budget_initial:g}")
        tk.Entry(
            budget_row,
            textvariable=self.budget_var,
            width=8,
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        ).pack(side="left", padx=(6, 12), ipady=3)
        budget_hint = tk.Label(
            budget_row,
            text=_("wizard_paid_budget_hint"),
            font=F["small"],
            bg=C["panel"],
            fg=C["text_muted"],
            anchor="w",
            justify="left",
        )
        budget_hint.pack(side="left", fill="x", expand=True, anchor="w")
        bind_wraplength(route_card, [opt_hint, budget_hint], padx_total=32, floor=200)

    def _key_field(self, parent, label, initial, px=24):
        """密钥输入行（标签 + 输入框 + 显示切换），返回绑定变量。"""
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", padx=px, pady=(8, 0))
        tk.Label(row, text=label, font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef = tk.Frame(row, bg=C["entry"])
        ef.pack(fill="x", pady=(4, 0))
        var = tk.StringVar(value=initial)
        ent = tk.Entry(
            ef,
            textvariable=var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef, ent)
        return var

    def _section(self, parent, icon, title, sub, px=24):
        f = tk.Frame(parent, bg=C["bg"])
        f.pack(fill="x", padx=px, pady=(16, 4))
        tk.Label(f, text=f"{icon} {title}", font=F["h2"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        tk.Label(f, text=sub, font=F["body"], bg=C["bg"], fg=C["warn"]).pack(anchor="w")

    def _info_card(self, parent, lines, px=24):
        card = tk.Frame(parent, bg=C["panel"], highlightbackground=C["sep"], highlightthickness=1)
        card.pack(fill="x", padx=px, pady=(4, 0))
        labels = []
        for line in lines:
            lbl = tk.Label(
                card, text=line, font=F["body"], bg=C["panel"], fg=C["text_muted"], anchor="w", justify="left"
            )
            lbl.pack(fill="x", anchor="w", padx=16, pady=2)
            labels.append(lbl)
        bind_wraplength(card, labels)
        # 底部留白占位：必须显式用卡片底色，否则按系统默认色渲染成白色竖条
        tk.Label(card, text="", bg=card.cget("bg")).pack(pady=2)

    def _divider(self, parent):
        tk.Frame(parent, bg=C["sep"], height=1).pack(fill="x", padx=24, pady=12)

    def _link_btn(self, parent, text, url):
        tk.Button(
            parent,
            text=text,
            font=F["body"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=lambda: webbrowser.open(url),
        ).pack(side="left", padx=(0, 8), pady=4)

    @staticmethod
    def _gb(frame, entry):
        frame.config(highlightbackground=C["ok"], highlightthickness=2)
        entry.bind("<FocusIn>", lambda _: frame.config(highlightbackground=C["entry"]), add="+")
        entry.bind("<FocusOut>", lambda _: frame.config(highlightbackground=C["ok"]), add="+")

    def _eye_btn(self, parent, entry):
        showing = [False]

        def _toggle():
            showing[0] = not showing[0]
            entry.config(show="" if showing[0] else "*")

        eye = tk.Button(
            parent,
            text=glyph("eye"),
            font=icon_font(10),
            bg=C["entry"],
            fg=C["sub"],
            bd=0,
            padx=6,
            cursor="hand2",
            command=_toggle,
        )
        eye.pack(side="right", padx=4)
        attach_tooltip(eye, "tip_toggle_key")
        self._gb(parent, entry)

    def _save(self):
        budget = parse_budget_input(self.budget_var.get())
        if budget is None:
            messagebox.showwarning(_("dlg_tip"), _("wizard_paid_budget_invalid"), parent=self)
            return
        self._dirty = False
        gpt_name = self.gpt_image_model_var.get()
        gpt_id = self._gpt_image_name_to_id.get(gpt_name, GPT_IMAGE_DEFAULT)
        ark_name = self.ark_model_var.get()
        ark_id = self._ark_name_to_id.get(ark_name, ARK_IMAGE_DEFAULT)

        self.cfg["openai_key"] = self.oai_var.get().strip()
        self.cfg["gpt_image_model"] = gpt_id
        self.cfg["gpt_image_quality"] = self.gpt_image_quality_var.get()
        self.cfg["stability_key"] = self.stab_var.get().strip()
        self.cfg["stability_model"] = self.stab_model_var.get()
        self.cfg["replicate_key"] = self.repl_var.get().strip()
        self.cfg["replicate_model"] = self._replicate_name_to_id.get(self.repl_model_var.get(), "flux-2-pro")
        self.cfg["volcengine_key"] = self.ark_var.get().strip()
        self.cfg["ark_model"] = ark_id
        self.cfg["bfl_key"] = self.bfl_var.get().strip()
        bfl_name = self.bfl_model_var.get()
        self.cfg["bfl_model"] = self._bfl_name_to_id.get(bfl_name, BFL_TXT2IMG_DEFAULT)
        self.cfg["xai_key"] = self.xai_var.get().strip()
        self.cfg["xai_model"] = self._xai_name_to_id.get(self.xai_model_var.get(), XAI_IMAGE_DEFAULT)
        self.cfg["ideogram_key"] = self.ideo_var.get().strip()
        self.cfg["fal_key"] = self.fal_var.get().strip()
        self.cfg["recraft_key"] = self.recraft_var.get().strip()
        self.cfg["recraft_model"] = self._recraft_name_to_id.get(self.recraft_model_var.get(), RECRAFT_DEFAULT)
        style_label = self.recraft_style_var.get()
        self.cfg["recraft_style"] = next(
            (code for code, label in self._recraft_style_labels if label == style_label), "realistic_image"
        )
        self.cfg["minimax_key"] = self.mm_var.get().strip()
        self.cfg["minimax_model"] = self._mm_name_to_id.get(self.mm_model_var.get(), MINIMAX_IMAGE_DEFAULT)
        self.cfg["paid_auto_opt_in"] = bool(self.paid_opt_var.get())
        self.cfg["paid_daily_budget_usd"] = budget
        from config.settings import save_config

        save_config(self.cfg)  # 与免费配置向导一致：保存必须落盘
        self.on_save(self.cfg)
        self._on_close()
