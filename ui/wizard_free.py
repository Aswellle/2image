"""
ui/wizard_free.py  v5
─────────────────────
免费接口配置向导  v5 新增：
  · Together AI  — FLUX.1 Free 免费端点（Section 8）
  · Gemini API   — Google Gemini 2.5 Flash Image，免费 500次/天（Section 9）
"""

import tkinter as tk
from tkinter import ttk
import webbrowser
from typing import Callable
from config.fonts import F
from config.theme import DARK_THEME as C
from ui.icons import glyph, icon_font
from config.i18n import _
from config.model_catalog import GEMINI_IMAGE_DEFAULT, GEMINI_IMAGE_MODELS


class ConfigWizard(tk.Toplevel):
    """免费接口配置向导（v5）。"""

    def __init__(self, parent: tk.Tk, cfg: dict, on_save: Callable[[dict], None]):
        super().__init__(parent)
        self.cfg = cfg.copy()
        self.on_save = on_save
        self._closing = False
        self._dirty = False

        self.title(_("wizard_free_title"))
        self.geometry("820x960")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.minsize(680, 600)
        self.grab_set()
        self.focus_set()
        self.update_idletasks()
        sh = self.winfo_screenheight()
        h = min(960, sh - 80)
        x = parent.winfo_x() + (parent.winfo_width() - 820) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"820x{h}+{max(0, x)}+{max(0, y)}")
        self.bind("<Escape>", lambda _e: self._on_close())
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()
        for _var in [
            self.sf_var,
            self.cf_id_var,
            self.cf_tok_var,
            self.ml_var,
            self.sg_var,
            self.hf_var,
            self.sh_var,
            self.ta_var,
            self.gm_var,
            self.gm_model_var,
            self.qual_var,
            self.pk_var,
            self.ds_var,
            self.br_var,
        ]:
            _var.trace("w", lambda *_: setattr(self, "_dirty", True))

    # ── 滚轮清理：销毁前必须解绑，否则 bind_all 残留在根 Tk 上 ──────
    def _on_close(self):
        """关闭窗口前先解绑 bind_all，防止 Canvas 销毁后仍触发 TclError。"""
        if self._dirty:
            from tkinter import messagebox

            if not messagebox.askyesno(_("wz_close_title"), _("wz_close_msg")):
                return
        self._closing = True
        try:
            self.unbind_all("<MouseWheel>")
            self.unbind_all("<Button-4>")
            self.unbind_all("<Button-5>")
        except Exception:
            pass
        # 用户主动关闭（跳过/保存/取消）→ 不再自动弹出
        self.cfg["show_wizard_on_start"] = False
        from config.settings import save_config

        save_config(self.cfg)
        self.destroy()

    def _build(self):
        PX = 24

        # 底部按钮
        bot = tk.Frame(self, bg=C["panel"])
        bot.pack(fill="x", side="bottom")
        tk.Button(
            bot,
            text=_("btn_save_and_start"),
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
            text=_("btn_skip"),
            font=F["body"],
            bg=C["panel"],
            fg=C["sub"],
            bd=0,
            padx=16,
            pady=10,
            cursor="hand2",
            command=self._on_close,
        ).pack(side="right", pady=12)

        # 标题栏
        hdr = tk.Frame(self, bg=C["acc"])
        hdr.pack(fill="x")
        tk.Label(hdr, text=_("wz_hdr_title"), font=(F["_sans"], 16, "bold"), bg=C["acc"], fg="white").pack(
            side="left", padx=20, pady=14
        )
        tk.Label(hdr, text=_("wz_hdr_subtitle"), font=F["body"], bg=C["acc"], fg=C["sub"]).pack(side="right", padx=20)

        # 可滚动内容区
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

        # ══════════════════════════════════════════════════════
        #   1. 硅基流动（强烈推荐）
        # ══════════════════════════════════════════════════════
        self._section(inner, "1", _("wz_sf_title"), _("wz_sf_tag"), C["ok"], PX)
        self._info_card(
            inner,
            [
                _("wz_sf_info1"),
                _("wz_sf_info2"),
                _("wz_sf_info3"),
            ],
            PX,
        )
        sf_row = tk.Frame(inner, bg=C["bg"])
        sf_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(sf_row, text=_("wz_sf_key_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef0 = tk.Frame(sf_row, bg=C["entry"])
        ef0.pack(fill="x", pady=(4, 0))
        self.sf_var = tk.StringVar(value=self.cfg.get("sf_key", ""))
        self.sf_entry = tk.Entry(
            ef0,
            textvariable=self.sf_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.sf_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef0, self.sf_entry)
        sf_btns = tk.Frame(inner, bg=C["bg"])
        sf_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(
            sf_btns,
            text=_("wz_sf_register"),
            font=F["body"],
            bg=C["ok"],
            fg=C["ok_fg"],
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://cloud.siliconflow.cn/account/ak"),
        ).pack(side="left")
        tk.Button(
            sf_btns,
            text=_("wz_sf_get_key"),
            font=F["body"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://cloud.siliconflow.cn/account/ak"),
        ).pack(side="left", padx=(8, 0))
        self._hint(inner, _("wz_sf_hint"), PX)

        # ══════════════════════════════════════════════════════
        #   2. Pollinations.AI（完全免费，无需 Key）
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "2", _("wz_poll_title"), _("wz_poll_tag"), C["ok"], PX)
        self._info_card(
            inner,
            [
                _("wz_poll_info1"),
                _("wz_poll_info2"),
                _("wz_poll_info3"),
            ],
            PX,
        )
        poll_f = tk.Frame(inner, bg=C["card"], highlightbackground=C["ok"], highlightthickness=1)
        poll_f.pack(fill="x", padx=PX, pady=(8, 0))
        poll_inner = tk.Frame(poll_f, bg=C["card"])
        poll_inner.pack(fill="x", padx=12, pady=10)
        self.poll_enabled_var = tk.BooleanVar(value=self.cfg.get("pollinations_enabled", True))
        tk.Checkbutton(
            poll_inner,
            text=_("wz_poll_enable"),
            variable=self.poll_enabled_var,
            font=F["btn"],
            bg=C["card"],
            fg=C["ok"],
            activebackground=C["card"],
            activeforeground=C["text"],
            selectcolor=C["entry"],
        ).pack(anchor="w")
        tk.Label(poll_inner, text=_("wz_poll_enable_desc"), font=F["small_i"], bg=C["card"], fg=C["sub"]).pack(
            anchor="w", pady=(2, 0)
        )
        poll_btns = tk.Frame(inner, bg=C["bg"])
        poll_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(
            poll_btns,
            text=_("wz_poll_website"),
            font=F["body"],
            bg=C["keep_bg"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://pollinations.ai"),
        ).pack(side="left")

        # v7：Pollinations 新平台可能已要求鉴权，留一个可选 Key 输入框
        poll_key_row = tk.Frame(inner, bg=C["bg"])
        poll_key_row.pack(fill="x", padx=PX, pady=(10, 0))
        tk.Label(poll_key_row, text=_("wz_poll_key_label"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(anchor="w")
        ef_pk = tk.Frame(poll_key_row, bg=C["entry"])
        ef_pk.pack(fill="x", pady=(4, 0))
        self.pk_var = tk.StringVar(value=self.cfg.get("pollinations_key", ""))
        self.pk_entry = tk.Entry(
            ef_pk,
            textvariable=self.pk_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.pk_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_pk, self.pk_entry)

        # ══════════════════════════════════════════════════════
        #   3. Cloudflare Workers AI
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "3", _("wz_cf_title"), _("wz_cf_tag"), "#60a5fa", PX)
        self._info_card(
            inner,
            [
                _("wz_cf_info1"),
                _("wz_cf_info2"),
                _("wz_cf_info3"),
                _("wz_cf_info4"),
            ],
            PX,
        )

        cf_row = tk.Frame(inner, bg=C["bg"])
        cf_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(cf_row, text=_("wz_cf_account_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_cfid = tk.Frame(cf_row, bg=C["entry"])
        ef_cfid.pack(fill="x", pady=(4, 0))
        self.cf_id_var = tk.StringVar(value=self.cfg.get("cf_account_id", ""))
        cf_id_entry = tk.Entry(
            ef_cfid,
            textvariable=self.cf_id_var,
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        cf_id_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._gb(ef_cfid, cf_id_entry)

        cf_tok_row = tk.Frame(inner, bg=C["bg"])
        cf_tok_row.pack(fill="x", padx=PX, pady=(10, 0))
        tk.Label(cf_tok_row, text=_("wz_cf_token_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_cftok = tk.Frame(cf_tok_row, bg=C["entry"])
        ef_cftok.pack(fill="x", pady=(4, 0))
        self.cf_tok_var = tk.StringVar(value=self.cfg.get("cf_api_token", ""))
        cf_tok_entry = tk.Entry(
            ef_cftok,
            textvariable=self.cf_tok_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        cf_tok_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_cftok, cf_tok_entry)

        cf_btns = tk.Frame(inner, bg=C["bg"])
        cf_btns.pack(fill="x", padx=PX, pady=(10, 0))
        tk.Button(
            cf_btns,
            text=_("wz_cf_register"),
            font=F["body"],
            bg=C["cmp_a"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://dash.cloudflare.com"),
        ).pack(side="left")
        tk.Button(
            cf_btns,
            text=_("wz_cf_create_token"),
            font=F["body"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://dash.cloudflare.com/profile/api-tokens"),
        ).pack(side="left", padx=(8, 0))
        tk.Button(
            cf_btns,
            text=_("wz_cf_docs"),
            font=F["body"],
            bg=C["chip_info_bg"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://developers.cloudflare.com/workers-ai/models/"),
        ).pack(side="left", padx=(8, 0))
        self._hint(inner, _("wz_cf_hint"), PX)

        # ══════════════════════════════════════════════════════
        #   4. ModelsLab
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "4", _("wz_ml_title"), _("wz_ml_tag"), "#a78bfa", PX)
        self._info_card(
            inner,
            [
                _("wz_ml_info1"),
                _("wz_ml_info2"),
                _("wz_ml_info3"),
                _("wz_ml_info4"),
            ],
            PX,
        )
        ml_row = tk.Frame(inner, bg=C["bg"])
        ml_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(ml_row, text=_("wz_ml_key_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_ml = tk.Frame(ml_row, bg=C["entry"])
        ef_ml.pack(fill="x", pady=(4, 0))
        self.ml_var = tk.StringVar(value=self.cfg.get("modelslab_key", ""))
        self.ml_entry = tk.Entry(
            ef_ml,
            textvariable=self.ml_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.ml_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_ml, self.ml_entry)
        ml_btns = tk.Frame(inner, bg=C["bg"])
        ml_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(
            ml_btns,
            text=_("wz_ml_register"),
            font=F["body"],
            bg=C["purple"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://modelslab.com"),
        ).pack(side="left")
        tk.Button(
            ml_btns,
            text=_("wz_ml_get_key"),
            font=F["body"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://modelslab.com/dashboard/account/api-keys"),
        ).pack(side="left", padx=(8, 0))
        self._hint(inner, _("wz_ml_hint"), PX)

        # ══════════════════════════════════════════════════════
        #   5. Segmind（注册送 $5）
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "5", _("wz_sg_title"), _("wz_sg_tag"), C["gold"], PX)
        self._info_card(
            inner,
            [
                _("wz_sg_info1"),
                _("wz_sg_info2"),
                _("wz_sg_info3"),
            ],
            PX,
        )
        sg_row = tk.Frame(inner, bg=C["bg"])
        sg_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(sg_row, text=_("wz_sg_key_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_sg = tk.Frame(sg_row, bg=C["entry"])
        ef_sg.pack(fill="x", pady=(4, 0))
        self.sg_var = tk.StringVar(value=self.cfg.get("segmind_key", ""))
        self.sg_entry = tk.Entry(
            ef_sg,
            textvariable=self.sg_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.sg_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_sg, self.sg_entry)
        sg_btns = tk.Frame(inner, bg=C["bg"])
        sg_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(
            sg_btns,
            text=_("wz_sg_register"),
            font=F["body"],
            bg="#d97706",
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://www.segmind.com"),
        ).pack(side="left")
        tk.Button(
            sg_btns,
            text=_("wz_sg_get_key"),
            font=F["body"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://www.segmind.com/dashboard"),
        ).pack(side="left", padx=(8, 0))

        # ══════════════════════════════════════════════════════
        #   6. HuggingFace
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "6", _("wz_hf_title"), _("wz_hf_tag"), C["warn"], PX)
        self._info_card(
            inner,
            [
                _("wz_hf_info1"),
                _("wz_hf_info2"),
            ],
            PX,
        )
        hf_row = tk.Frame(inner, bg=C["bg"])
        hf_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(hf_row, text=_("wz_hf_key_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef1 = tk.Frame(hf_row, bg=C["entry"])
        ef1.pack(fill="x", pady=(4, 0))
        self.hf_var = tk.StringVar(value=self.cfg.get("hf_token", ""))
        self.hf_entry = tk.Entry(
            ef1,
            textvariable=self.hf_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.hf_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef1, self.hf_entry)
        hf_btns = tk.Frame(inner, bg=C["bg"])
        hf_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(
            hf_btns,
            text=_("wz_hf_register"),
            font=F["body"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://huggingface.co/join"),
        ).pack(side="left")
        tk.Button(
            hf_btns,
            text=_("wz_hf_create_token"),
            font=F["body"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://huggingface.co/settings/tokens/new?tokenType=read"),
        ).pack(side="left", padx=(8, 0))

        # ══════════════════════════════════════════════════════
        #   7. StableHorde（兜底）
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "7", _("wz_sh_title"), _("wz_sh_tag"), C["sub"], PX)
        self._info_card(
            inner,
            [
                _("wz_sh_info1"),
                _("wz_sh_info2"),
            ],
            PX,
        )
        sh_row = tk.Frame(inner, bg=C["bg"])
        sh_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(sh_row, text=_("wz_sh_key_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef2 = tk.Frame(sh_row, bg=C["entry"])
        ef2.pack(fill="x", pady=(4, 0))
        self.sh_var = tk.StringVar(value=self.cfg.get("stablehorde_key", ""))
        self.sh_entry = tk.Entry(
            ef2,
            textvariable=self.sh_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.sh_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef2, self.sh_entry)
        sh_btns = tk.Frame(inner, bg=C["bg"])
        sh_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(
            sh_btns,
            text=_("wz_sh_register"),
            font=F["body"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://stablehorde.net/register"),
        ).pack(side="left")

        # ══════════════════════════════════════════════════════
        #   8. Together AI（v5 新增）
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "8", _("wz_ta_title"), _("wz_ta_tag"), "#4ecca3", PX)
        self._info_card(
            inner,
            [
                _("wz_ta_info1"),
                _("wz_ta_info2"),
                _("wz_ta_info3"),
            ],
            PX,
        )
        ta_row = tk.Frame(inner, bg=C["bg"])
        ta_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(ta_row, text=_("wz_ta_key_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_ta = tk.Frame(ta_row, bg=C["entry"])
        ef_ta.pack(fill="x", pady=(4, 0))
        self.ta_var = tk.StringVar(value=self.cfg.get("together_key", ""))
        self.ta_entry = tk.Entry(
            ef_ta,
            textvariable=self.ta_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.ta_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_ta, self.ta_entry)
        ta_btns = tk.Frame(inner, bg=C["bg"])
        ta_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(
            ta_btns,
            text=_("wz_ta_register"),
            font=F["body"],
            bg=C["ok"],
            fg=C["ok_fg"],
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://api.together.ai/"),
        ).pack(side="left")
        tk.Button(
            ta_btns,
            text=_("wz_ta_get_key"),
            font=F["body"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://api.together.ai/settings/api-keys"),
        ).pack(side="left", padx=(8, 0))
        self._hint(inner, _("wz_ta_hint"), PX)

        # ══════════════════════════════════════════════════════
        #   9. Google Gemini Nano Banana（v5 新增，v7 更新）
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "9", _("wz_gm_title"), _("wz_gm_tag"), C["ok"], PX)
        self._info_card(
            inner,
            [
                _("wz_gm_info1"),
                _("wz_gm_info2"),
                _("wz_gm_info3"),
                _("wz_gm_info4"),
            ],
            PX,
        )
        gm_row = tk.Frame(inner, bg=C["bg"])
        gm_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(gm_row, text=_("wz_gm_key_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_gm = tk.Frame(gm_row, bg=C["entry"])
        ef_gm.pack(fill="x", pady=(4, 0))
        self.gm_var = tk.StringVar(value=self.cfg.get("gemini_key", ""))
        self.gm_entry = tk.Entry(
            ef_gm,
            textvariable=self.gm_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.gm_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_gm, self.gm_entry)
        gm_btns = tk.Frame(inner, bg=C["bg"])
        gm_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(
            gm_btns,
            text=_("wz_gm_register"),
            font=F["body"],
            bg=C["ok"],
            fg=C["ok_fg"],
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://aistudio.google.com/apikey"),
        ).pack(side="left")
        tk.Button(
            gm_btns,
            text=_("wz_gm_get_key"),
            font=F["body"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://aistudio.google.com/apikey"),
        ).pack(side="left", padx=(8, 0))
        self._hint(inner, _("wz_gm_hint"), PX)
        gm_mrow = tk.Frame(inner, bg=C["bg"])
        gm_mrow.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(gm_mrow, text=_("wz_gm_model_label"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self.gm_model_var = tk.StringVar(value=self.cfg.get("gemini_model", GEMINI_IMAGE_DEFAULT))
        ttk.Combobox(
            gm_mrow, textvariable=self.gm_model_var, width=26, state="readonly", values=GEMINI_IMAGE_MODELS
        ).pack(side="left", padx=(6, 20))

        # ══════════════════════════════════════════════════════
        #   10. 阿里云 DashScope 通义万相 Qwen-Image（v7 新增）
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "10", _("wz_ds_title"), _("wz_ds_tag"), "#ff6a00", PX)
        self._info_card(
            inner,
            [
                _("wz_ds_info1"),
                _("wz_ds_info2"),
                _("wz_ds_info3"),
            ],
            PX,
        )
        ds_row = tk.Frame(inner, bg=C["bg"])
        ds_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(ds_row, text=_("wz_ds_key_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_ds = tk.Frame(ds_row, bg=C["entry"])
        ef_ds.pack(fill="x", pady=(4, 0))
        self.ds_var = tk.StringVar(value=self.cfg.get("dashscope_key", ""))
        self.ds_entry = tk.Entry(
            ef_ds,
            textvariable=self.ds_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.ds_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_ds, self.ds_entry)
        ds_btns = tk.Frame(inner, bg=C["bg"])
        ds_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(
            ds_btns,
            text=_("wz_ds_register"),
            font=F["body"],
            bg="#ff6a00",
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://dashscope.console.aliyun.com/"),
        ).pack(side="left")
        tk.Button(
            ds_btns,
            text=_("wz_ds_get_key"),
            font=F["body"],
            bg=C["acc"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://dashscope.console.aliyun.com/apiKey"),
        ).pack(side="left", padx=(8, 0))

        # ══════════════════════════════════════════════════════
        #   11. Bria AI（v7 新增）
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "11", _("wz_br_title"), _("wz_br_tag"), "#8b5cf6", PX)
        self._info_card(
            inner,
            [
                _("wz_br_info1"),
                _("wz_br_info2"),
                _("wz_br_info3"),
            ],
            PX,
        )
        br_row = tk.Frame(inner, bg=C["bg"])
        br_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(br_row, text=_("wz_br_key_label"), font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_br = tk.Frame(br_row, bg=C["entry"])
        ef_br.pack(fill="x", pady=(4, 0))
        self.br_var = tk.StringVar(value=self.cfg.get("bria_key", ""))
        self.br_entry = tk.Entry(
            ef_br,
            textvariable=self.br_var,
            show="*",
            bg=C["entry"],
            fg=C["text"],
            insertbackground="white",
            font=F["input"],
            bd=0,
            relief="flat",
        )
        self.br_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_br, self.br_entry)
        br_btns = tk.Frame(inner, bg=C["bg"])
        br_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(
            br_btns,
            text=_("wz_br_register"),
            font=F["body"],
            bg=C["purple"],
            fg="white",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open("https://platform.bria.ai/"),
        ).pack(side="left")

        # ══════════════════════════════════════════════════════
        #   变体质量模式
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        qual_hdr = tk.Frame(inner, bg=C["bg"])
        qual_hdr.pack(fill="x", padx=PX, pady=(0, 4))
        tk.Label(qual_hdr, text=" Q ", font=F["btn"], bg=C["hl"], fg="white").pack(side="left")
        tk.Label(qual_hdr, text=_("wz_qual_title"), font=F["h1"], bg=C["bg"], fg=C["text"]).pack(side="left")
        tk.Label(qual_hdr, text=_("wz_qual_subtitle"), font=F["body"], bg=C["bg"], fg=C["warn"]).pack(side="left")

        qual_card = tk.Frame(inner, bg=C["card"], highlightbackground=C["sep"], highlightthickness=1)
        qual_card.pack(fill="x", padx=PX, pady=(4, 0))
        qual_inner = tk.Frame(qual_card, bg=C["card"])
        qual_inner.pack(fill="x", padx=16, pady=12)

        self.qual_var = tk.StringVar(value=self.cfg.get("variant_quality", "high"))

        for val, label, desc, tag_col in [
            ("high", _("wz_qual_high"), _("wz_qual_high_desc"), C["ok"]),
            ("standard", _("wz_qual_std"), _("wz_qual_std_desc"), C["warn"]),
        ]:
            row = tk.Frame(qual_inner, bg=C["card"])
            row.pack(fill="x", pady=3)
            tk.Radiobutton(
                row,
                text=label,
                variable=self.qual_var,
                value=val,
                font=F["btn"],
                bg=C["card"],
                fg=tag_col,
                activebackground=C["card"],
                activeforeground=C["text"],
                selectcolor=C["entry"],
            ).pack(side="left")
            tk.Label(row, text=f"  {desc}", font=F["small_i"], bg=C["card"], fg=C["sub"]).pack(side="left")

        # ── 启动选项 ────────────────────────────────────────────
        self._divider(inner)
        opts_f = tk.Frame(inner, bg=C["bg"])
        opts_f.pack(fill="x", padx=PX, pady=(0, 24))
        self.show_wiz_var = tk.BooleanVar(value=self.cfg.get("show_wizard_on_start", True))
        tk.Checkbutton(
            opts_f,
            text=_("wz_hide_on_startup"),
            variable=self.show_wiz_var,
            font=F["body"],
            bg=C["bg"],
            fg=C["sub"],
            activebackground=C["bg"],
            activeforeground=C["text"],
            selectcolor=C["entry"],
        ).pack(anchor="w")

    # ── 辅助控件 ───────────────────────────────────────────────
    def _section(self, parent, num, title, tag, tag_color, px=24):
        f = tk.Frame(parent, bg=C["bg"])
        f.pack(fill="x", padx=px, pady=(16, 4))
        tk.Label(f, text=f" {num} ", font=F["btn"], bg=C["hl"], fg="white").pack(side="left")
        tk.Label(f, text=f"  {title}", font=F["h1"], bg=C["bg"], fg=C["text"]).pack(side="left")
        tk.Label(f, text=f"  {tag}", font=F["body"], bg=C["bg"], fg=tag_color).pack(side="left")

    def _info_card(self, parent, lines, px=24):

        card = tk.Frame(parent, bg=C["card"], highlightbackground=C["sep"], highlightthickness=1)
        card.pack(fill="x", padx=px, pady=(4, 0))
        for line in lines:
            tk.Label(card, text=line, font=F["body"], bg=C["card"], fg=C["sub"], anchor="w", justify="left").pack(
                anchor="w", padx=12, pady=2
            )
        tk.Label(card, text="").pack(pady=2)

    def _hint(self, parent, text, px=24):

        tk.Label(
            parent, text=text, font=F["body_i"], bg=C["bg"], fg=C["warn"], wraplength=740, justify="left", anchor="w"
        ).pack(fill="x", padx=px, pady=(6, 0))

    def _divider(self, parent):
        tk.Frame(parent, bg=C["sep"], height=1).pack(fill="x", padx=24, pady=12)

    @staticmethod
    def _gb(frame: tk.Frame, entry) -> None:
        """绿边 idle，获焦后变隐形。"""
        frame.config(highlightbackground=C["ok"], highlightthickness=1)
        entry.bind("<FocusIn>", lambda _: frame.config(highlightbackground=C["entry"]), add="+")
        entry.bind("<FocusOut>", lambda _: frame.config(highlightbackground=C["ok"]), add="+")

    def _eye_btn(self, parent, entry):
        showing = [False]

        def toggle():
            showing[0] = not showing[0]
            entry.config(show="" if showing[0] else "*")
            btn.config(text=glyph("eye_off") if showing[0] else glyph("eye"))

        btn = tk.Button(
            parent,
            text=glyph("eye"),
            font=icon_font(11),
            bg=C["entry"],
            fg=C["sub"],
            bd=0,
            padx=8,
            cursor="hand2",
            command=toggle,
        )
        btn.pack(side="right", padx=4)
        self._gb(parent, entry)  # 绿边：idle 显示，获焦后隐藏

    def _save(self):
        self._dirty = False
        self.cfg["sf_key"] = self.sf_var.get().strip()
        self.cfg["hf_token"] = self.hf_var.get().strip()
        self.cfg["stablehorde_key"] = self.sh_var.get().strip()
        self.cfg["segmind_key"] = self.sg_var.get().strip()
        self.cfg["pollinations_enabled"] = self.poll_enabled_var.get()
        self.cfg["cf_account_id"] = self.cf_id_var.get().strip()
        self.cfg["cf_api_token"] = self.cf_tok_var.get().strip()
        self.cfg["modelslab_key"] = self.ml_var.get().strip()
        self.cfg["together_key"] = self.ta_var.get().strip()  # v5 新增
        self.cfg["gemini_key"] = self.gm_var.get().strip()  # v5 新增
        self.cfg["gemini_model"] = self.gm_model_var.get()  # 添加 Gemini 3.1 图像模型
        self.cfg["pollinations_key"] = self.pk_var.get().strip()  # v7 新增
        self.cfg["dashscope_key"] = self.ds_var.get().strip()  # v7 新增
        self.cfg["bria_key"] = self.br_var.get().strip()  # v7 新增
        self.cfg["variant_quality"] = self.qual_var.get()
        self.cfg["show_wizard_on_start"] = not self.show_wiz_var.get()
        from config.settings import save_config

        save_config(self.cfg)
        self.on_save(self.cfg)
        self.destroy()
