"""
ui/wizard_paid.py  v2
──────────────────────
付费接口配置向导。
修复：bind_all 实现全窗口滚轮滚动（窗口为 modal grab_set，bind_all 安全）
改动：窗口初始尺寸增大

v2 新增：
  · OpenRouter — 统一 AI 路由，部分模型免费（Section 4）
  · xAI Grok   — Grok Imagine 图像生成，付费按量计费（Section 5）
"""
import tkinter as tk
from tkinter import ttk
import webbrowser
from typing import Callable
from config.fonts import F
from config.theme import DARK_THEME as C
from config.i18n import _



class PaidWizard(tk.Toplevel):
    """付费接口（OpenAI / Stability AI / Replicate / OpenRouter / xAI）配置窗口。"""

    def __init__(self, parent: tk.Tk, cfg: dict, on_save: Callable[[dict], None]):
        super().__init__(parent)
        self.cfg     = cfg.copy()
        self.on_save = on_save
        self._closing = False
        self._dirty = False

        self.title(_("wizard_paid_title"))
        self.geometry("860x900")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.minsize(700, 580)
        self.grab_set(); self.focus_set()
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width()  - 860) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 900) // 2
        self.geometry(f"860x900+{max(0,x)}+{max(0,y)}")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()
        for _var in [self.oai_var, self.dalle_model_var, self.dalle_q_var,
                     self.stab_var, self.stab_model_var,
                     self.rep_var, self.rep_model_var,
                     self.or_var, self.or_model_var,
                     self.xai_var]:
            _var.trace("w", lambda *_: setattr(self, '_dirty', True))

    # ── 滚轮清理：销毁前必须解绑，否则 bind_all 残留在根 Tk 上 ──────
    def _on_close(self):
        """关闭窗口前先解绑 bind_all，防止 Canvas 销毁后仍触发 TclError。"""
        if self._dirty:
            from tkinter import messagebox
            if not messagebox.askyesno("未保存的更改", "有未保存的更改，确定关闭？"):
                return
        self._closing = True
        try:
            self.unbind_all("<MouseWheel>")
            self.unbind_all("<Button-4>")
            self.unbind_all("<Button-5>")
        except Exception:
            pass
        self.destroy()

    def _build(self):
        PX = 24

        # 标题栏
        hdr = tk.Frame(self, bg=C["paid"]); hdr.pack(fill="x")
        tk.Label(hdr, text=_("wizard_paid_title"),
                 font=F["title"], bg=C["paid"], fg="white"
                 ).pack(side="left", padx=20, pady=14)
        tk.Label(hdr, text=_("wizard_paid_subtitle"),
                 font=F["body_b"], bg=C["paid"], fg="#e9d5ff"
                 ).pack(side="right", padx=20)

        # 底部按钮
        bot = tk.Frame(self, bg=C["panel"]); bot.pack(fill="x", side="bottom")
        tk.Button(bot, text=_("btn_save_config"),
                  font=F["h2"], bg=C["ok"], fg="#0a1a0a",
                  bd=0, padx=24, pady=10, cursor="hand2",
                  command=self._save).pack(side="right", padx=20, pady=12)
        tk.Button(bot, text=_("btn_close"),
                  font=F["body"], bg=C["panel"], fg="#c0cfe0",
                  bd=0, padx=16, pady=10, cursor="hand2",
                  command=self._on_close).pack(side="right", pady=12)

        # ── 可滚动内容区 ────────────────────────────────────────
        fo  = tk.Frame(self, bg=C["bg"]); fo.pack(fill="both", expand=True)
        cv  = tk.Canvas(fo, bg=C["bg"], bd=0, highlightthickness=0)
        vsb = ttk.Scrollbar(fo, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(cv, bg=C["bg"])
        cwin  = cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",    lambda e: cv.itemconfig(cwin, width=e.width))

        # ── 全窗口滚轮绑定（modal 窗口 bind_all 安全）──────────
        def _scroll_win(e):
            if self._closing: return
            try: cv.yview_scroll(int(-1*(e.delta/120)), "units")
            except tk.TclError: pass
        def _scroll_up(e):
            if self._closing: return
            try: cv.yview_scroll(-1, "units")
            except tk.TclError: pass
        def _scroll_dn(e):
            if self._closing: return
            try: cv.yview_scroll( 1, "units")
            except tk.TclError: pass
        self.bind_all("<MouseWheel>", _scroll_win)
        self.bind_all("<Button-4>",   _scroll_up)
        self.bind_all("<Button-5>",   _scroll_dn)

        # ══════════════════════════════════════════════════════
        #   1. OpenAI DALL-E 3
        # ══════════════════════════════════════════════════════
        self._section(inner, "💡", "OpenAI DALL-E 3",
                      "最强文字理解力  |  Standard ~¥0.28/张  |  HD ~¥0.57/张", PX)
        self._info_card(inner, [
            "• 全球最强的文生图接口之一，对提示词理解最精准",
            "• 支持 1024×1024 / 1792×1024 / 1024×1792 三种尺寸",
            "• 需要信用卡绑定，按月账单结算（最低充值 $5）",
        ], PX)
        row1 = tk.Frame(inner, bg=C["bg"]); row1.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(row1, text="OpenAI API Key:", font=F["btn"],
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef1 = tk.Frame(row1, bg=C["entry"]); ef1.pack(fill="x", pady=(4, 0))
        self.oai_var = tk.StringVar(value=self.cfg.get("openai_key", ""))
        self.oai_ent = tk.Entry(ef1, textvariable=self.oai_var, show="*",
                                bg=C["entry"], fg=C["text"], insertbackground="white",
                                font=F["input"], bd=0, relief="flat")
        self.oai_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef1, self.oai_ent)

        opt1 = tk.Frame(inner, bg=C["bg"]); opt1.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(opt1, text="模型版本:", font=F["body"],
                 bg=C["bg"], fg=C["sub"]).pack(side="left")
        self.dalle_model_var = tk.StringVar(value=self.cfg.get("dalle_model", "dall-e-3"))
        ttk.Combobox(opt1, textvariable=self.dalle_model_var, width=12, state="readonly",
                     values=["dall-e-3", "dall-e-2"]).pack(side="left", padx=(6, 20))
        tk.Label(opt1, text="画质:", font=F["body"],
                 bg=C["bg"], fg=C["sub"]).pack(side="left")
        self.dalle_q_var = tk.StringVar(value=self.cfg.get("dalle_quality", "standard"))
        ttk.Combobox(opt1, textvariable=self.dalle_q_var, width=12, state="readonly",
                     values=["standard", "hd"]).pack(side="left", padx=(6, 20))

        btns1 = tk.Frame(inner, bg=C["bg"]); btns1.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns1, "🌐 OpenAI 注册 / 充值",
                       "https://platform.openai.com/account/billing")
        self._link_btn(btns1, "🔑 生成 API Key",
                       "https://platform.openai.com/api-keys")
        self._divider(inner)

        # ══════════════════════════════════════════════════════
        #   2. Stability AI
        # ══════════════════════════════════════════════════════
        self._section(inner, "🎨", "Stability AI  (Stable Image)",
                      "Core ~¥0.02/张  |  Ultra ~¥0.06/张  |  SD3.5 ~¥0.47/张", PX)
        self._info_card(inner, [
            "• 支持 Core / Ultra / SD3.5-Large 三档，新用户赠送 25 Credits 试用",
            "• Core：速度最快；Ultra：最高画质；SD3.5：文字渲染能力强",
        ], PX)
        row2 = tk.Frame(inner, bg=C["bg"]); row2.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(row2, text="Stability AI API Key:", font=F["btn"],
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef2 = tk.Frame(row2, bg=C["entry"]); ef2.pack(fill="x", pady=(4, 0))
        self.stab_var = tk.StringVar(value=self.cfg.get("stability_key", ""))
        self.stab_ent = tk.Entry(ef2, textvariable=self.stab_var, show="*",
                                  bg=C["entry"], fg=C["text"], insertbackground="white",
                                  font=F["input"], bd=0, relief="flat")
        self.stab_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef2, self.stab_ent)

        opt2 = tk.Frame(inner, bg=C["bg"]); opt2.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(opt2, text="模型档位:", font=F["body"],
                 bg=C["bg"], fg=C["sub"]).pack(side="left")
        self.stab_model_var = tk.StringVar(value=self.cfg.get("stability_model", "core"))
        ttk.Combobox(opt2, textvariable=self.stab_model_var, width=18, state="readonly",
                     values=["core", "ultra", "sd3.5-large"]
                     ).pack(side="left", padx=(6, 0))
        tk.Label(opt2, text="  core=最快  ultra=最佳  sd3.5=文字强",
                 font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left", padx=8)

        btns2 = tk.Frame(inner, bg=C["bg"]); btns2.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns2, "🌐 注册 Stability AI", "https://platform.stability.ai/")
        self._link_btn(btns2, "🔑 获取 API Key",
                       "https://platform.stability.ai/account/keys")
        self._divider(inner)

        # ══════════════════════════════════════════════════════
        #   3. Replicate FLUX
        # ══════════════════════════════════════════════════════
        self._section(inner, "⚡", "Replicate  (FLUX 系列)",
                      "FLUX.1 Pro ~¥0.39/张  |  1.1 Pro ~¥0.28/张  |  Dev ~¥0.18/张", PX)
        self._info_card(inner, [
            "• 顶级开源模型 FLUX.1，业界最高画质之一",
            "• flux-1.1-pro：最新旗舰；flux-pro：经典旗舰；flux-dev：性价比高",
            "• 按次计费，首次注册赠送 $10 试用额度",
        ], PX)
        row3 = tk.Frame(inner, bg=C["bg"]); row3.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(row3, text="Replicate API Token:", font=F["btn"],
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef3 = tk.Frame(row3, bg=C["entry"]); ef3.pack(fill="x", pady=(4, 0))
        self.rep_var = tk.StringVar(value=self.cfg.get("replicate_key", ""))
        self.rep_ent = tk.Entry(ef3, textvariable=self.rep_var, show="*",
                                 bg=C["entry"], fg=C["text"], insertbackground="white",
                                 font=F["input"], bd=0, relief="flat")
        self.rep_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef3, self.rep_ent)

        opt3 = tk.Frame(inner, bg=C["bg"]); opt3.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(opt3, text="模型:", font=F["body"],
                 bg=C["bg"], fg=C["sub"]).pack(side="left")
        self.rep_model_var = tk.StringVar(value=self.cfg.get("replicate_model", "flux-1.1-pro"))
        ttk.Combobox(opt3, textvariable=self.rep_model_var, width=18, state="readonly",
                     values=["flux-1.1-pro", "flux-pro", "flux-dev"]
                     ).pack(side="left", padx=(6, 0))

        btns3 = tk.Frame(inner, bg=C["bg"]); btns3.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns3, "🌐 注册 Replicate",
                       "https://replicate.com/account/api-tokens")
        self._link_btn(btns3, "🔑 获取 API Token",
                       "https://replicate.com/account/api-tokens")
        self._divider(inner)

        # ══════════════════════════════════════════════════════
        #   4. OpenRouter（v2 新增）
        # ══════════════════════════════════════════════════════
        self._section(inner, "🔀", "OpenRouter  (AI 路由聚合)",
                      "部分模型免费 · 统一接入数十家供应商 · 单 Key 搞定", PX)
        self._info_card(inner, [
            "• 统一接入 OpenAI / Anthropic / Meta / 开源模型等数十家供应商",
            "• 部分图像模型完全免费（如 FLUX.1-schnell:free / FLUX.1-dev:free）",
            "• 付费模型通常比直连便宜，计费清晰，适合探索不同风格",
            "• 默认使用 FLUX.1-schnell:free（免费），可在下方修改为其他模型",
        ], PX)
        row4 = tk.Frame(inner, bg=C["bg"]); row4.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(row4, text="OpenRouter API Key:", font=F["btn"],
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef4 = tk.Frame(row4, bg=C["entry"]); ef4.pack(fill="x", pady=(4, 0))
        self.or_var = tk.StringVar(value=self.cfg.get("openrouter_key", ""))
        self.or_ent = tk.Entry(ef4, textvariable=self.or_var, show="*",
                               bg=C["entry"], fg=C["text"], insertbackground="white",
                               font=F["input"], bd=0, relief="flat")
        self.or_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef4, self.or_ent)

        row4m = tk.Frame(inner, bg=C["bg"]); row4m.pack(fill="x", padx=PX, pady=(10, 0))
        tk.Label(row4m, text="图像模型:", font=F["btn"],
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef4m = tk.Frame(row4m, bg=C["entry"]); ef4m.pack(fill="x", pady=(4, 0))
        self.or_model_var = tk.StringVar(
            value=self.cfg.get("openrouter_model",
                               "black-forest-labs/FLUX.1-schnell:free"))
        or_model_ent = tk.Entry(ef4m, textvariable=self.or_model_var,
                                 bg=C["entry"], fg=C["text"], insertbackground="white",
                                 font=F["input"], bd=0, relief="flat")
        or_model_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._gb(ef4m, or_model_ent)

        btns4 = tk.Frame(inner, bg=C["bg"]); btns4.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns4, "🌐 注册 OpenRouter（免费）",
                       "https://openrouter.ai/keys")
        self._link_btn(btns4, "📋 查看免费图像模型列表",
                       "https://openrouter.ai/models?modality=image")

        # 推荐模型提示
        or_hint_f = tk.Frame(inner, bg=C["card"],
                             highlightbackground="#2a3a5a", highlightthickness=1)
        or_hint_f.pack(fill="x", padx=PX, pady=(8, 0))
        for tip in [
            "💡 免费模型推荐（直接粘贴到「图像模型」栏）：",
            "  • black-forest-labs/FLUX.1-schnell:free  （速度最快，质量好）",
            "  • black-forest-labs/FLUX.1-dev:free      （质量更高，稍慢）",
        ]:
            tk.Label(or_hint_f, text=tip, font=F["small"],
                     bg=C["card"], fg=C["ok"] if tip.startswith("💡") else C["sub"],
                     anchor="w", justify="left"
                     ).pack(anchor="w", padx=12, pady=2)
        tk.Label(or_hint_f, text="").pack(pady=2)
        self._divider(inner)

        # ══════════════════════════════════════════════════════
        #   5. xAI Grok Imagine（v2 新增）
        # ══════════════════════════════════════════════════════
        self._section(inner, "🌌", "xAI Grok  (Aurora 图像模型)",
                      "付费按量计费 · 真实感极强 · 细节与光影出色", PX)
        self._info_card(inner, [
            "• 基于 Aurora 自回归模型，真实感强，光影/材质/人像细节处理出色",
            "• ⚠️ 当前为纯付费服务：2024 年底公测送 $25 活动已结束",
            "• 现行免费政策：消费满 $5 后，可申请「数据共享计划」换取每月 $150 额度",
            "  （需同意 xAI 使用 API 请求训练模型，不适合数据敏感场景）",
            "• 图像生成约 $0.07/张，响应速度稳定（5~15 秒），使用 aspect_ratio 参数控制比例",
        ], PX)
        row5 = tk.Frame(inner, bg=C["bg"]); row5.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(row5, text="xAI API Key:", font=F["btn"],
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef5 = tk.Frame(row5, bg=C["entry"]); ef5.pack(fill="x", pady=(4, 0))
        self.xai_var = tk.StringVar(value=self.cfg.get("xai_key", ""))
        self.xai_ent = tk.Entry(ef5, textvariable=self.xai_var, show="*",
                                 bg=C["entry"], fg=C["text"], insertbackground="white",
                                 font=F["input"], bd=0, relief="flat")
        self.xai_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef5, self.xai_ent)

        btns5 = tk.Frame(inner, bg=C["bg"]); btns5.pack(fill="x", padx=PX, pady=(8, 24))
        self._link_btn(btns5, "🌐 注册 xAI 账号",
                       "https://console.x.ai")
        self._link_btn(btns5, "🔑 获取 API Key",
                       "https://console.x.ai/")
        self._link_btn(btns5, "📖 查看定价",
                       "https://docs.x.ai/developers/models")

    # ── 辅助控件 ───────────────────────────────────────────────
    def _section(self, parent, icon, title, sub, px=24):
        f = tk.Frame(parent, bg=C["bg"])
        f.pack(fill="x", padx=px, pady=(16, 4))
        tk.Label(f, text=f" {icon} ", font=F["label"],
                 bg=C["paid"], fg="white").pack(side="left")
        tk.Label(f, text=f"  {title}", font=F["h1"],
                 bg=C["bg"], fg=C["text"]).pack(side="left")
        tk.Label(f, text=f"  {sub}", font=F["body"],
                 bg=C["bg"], fg=C["warn"]).pack(side="left")

    def _info_card(self, parent, lines, px=24):
        
        card = tk.Frame(parent, bg=C["card"],
                        highlightbackground="#2a3a5a", highlightthickness=1)
        card.pack(fill="x", padx=px, pady=(4, 0))
        for line in lines:
            tk.Label(card, text=line, font=F["body"],
                     bg=C["card"], fg=C["sub"], anchor="w", justify="left"
                     ).pack(anchor="w", padx=12, pady=2)
        tk.Label(card, text="").pack(pady=2)

    def _divider(self, parent):
        tk.Frame(parent, bg="#2a3a5a", height=1).pack(fill="x", padx=24, pady=12)

    def _link_btn(self, parent, text, url):
        
        tk.Button(parent, text=text, font=F["body"],
                  bg=C["acc"], fg="white", bd=0, padx=12, pady=5,
                  cursor="hand2", command=lambda: webbrowser.open(url)
                  ).pack(side="left", padx=(0, 8))

    @staticmethod
    def _gb(frame: tk.Frame, entry) -> None:
        """绿边 idle，获焦后隐藏。"""
        frame.config(highlightbackground=C["ok"], highlightthickness=1)
        entry.bind("<FocusIn>",  lambda _: frame.config(highlightbackground=C["entry"]), add="+")
        entry.bind("<FocusOut>", lambda _: frame.config(highlightbackground=C["ok"]),    add="+")

    def _eye_btn(self, parent, entry):
        showing = [False]
        def toggle():
            showing[0] = not showing[0]
            entry.config(show="" if showing[0] else "*")
            btn.config(text="🙈" if showing[0] else "👁")
        btn = tk.Button(parent, text="👁", font=F["input"],
                        bg=C["entry"], fg=C["sub"], bd=0, padx=8,
                        cursor="hand2", command=toggle)
        btn.pack(side="right", padx=4)
        self._gb(parent, entry)

    def _save(self):
        self._dirty = False
        self.cfg["openai_key"]        = self.oai_var.get().strip()
        self.cfg["dalle_model"]       = self.dalle_model_var.get()
        self.cfg["dalle_quality"]     = self.dalle_q_var.get()
        self.cfg["stability_key"]     = self.stab_var.get().strip()
        self.cfg["stability_model"]   = self.stab_model_var.get()
        self.cfg["replicate_key"]     = self.rep_var.get().strip()
        self.cfg["replicate_model"]   = self.rep_model_var.get()
        self.cfg["openrouter_key"]    = self.or_var.get().strip()     # v2 新增
        self.cfg["openrouter_model"]  = self.or_model_var.get().strip() or \
                                        "black-forest-labs/FLUX.1-schnell:free"
        self.cfg["xai_key"]           = self.xai_var.get().strip()    # v2 新增
        from config.settings import save_config
        save_config(self.cfg)
        self.on_save(self.cfg)
        self._on_close()
