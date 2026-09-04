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
from config.i18n import _



class ConfigWizard(tk.Toplevel):
    """免费接口配置向导（v5）。"""

    def __init__(self, parent: tk.Tk, cfg: dict, on_save: Callable[[dict], None]):
        super().__init__(parent)
        self.cfg     = cfg.copy()
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
        x = parent.winfo_x() + (parent.winfo_width()  - 820) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 960) // 2
        self.geometry(f"820x960+{max(0,x)}+{max(0,y)}")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()
        for _var in [self.sf_var, self.cf_id_var, self.cf_tok_var, self.ml_var,
                     self.sg_var, self.hf_var, self.sh_var, self.ta_var,
                     self.gm_var, self.qual_var,
                     self.pk_var, self.ds_var, self.br_var]:
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

        # 底部按钮
        bot = tk.Frame(self, bg=C["panel"])
        bot.pack(fill="x", side="bottom")
        tk.Button(bot, text=_("btn_save_and_start"),
                  font=F["h2"], bg=C["ok"], fg="#0a1a0a",
                  bd=0, padx=24, pady=10, cursor="hand2",
                  command=self._save).pack(side="right", padx=20, pady=12)
        tk.Button(bot, text=_("btn_skip"),
                  font=F["body"], bg=C["panel"], fg=C["sub"],
                  bd=0, padx=16, pady=10, cursor="hand2",
                  command=self._on_close).pack(side="right", pady=12)

        # 标题栏
        hdr = tk.Frame(self, bg=C["acc"]); hdr.pack(fill="x")
        tk.Label(hdr, text="⚙  配置接口密钥",
                 font=(F["_sans"], 16, "bold"), bg=C["acc"], fg="white"
                 ).pack(side="left", padx=20, pady=14)
        tk.Label(hdr, text="配置后将自动保存，下次启动无需重填",
                 font=F["body"], bg=C["acc"], fg="#c0cfe0"
                 ).pack(side="right", padx=20)

        # 可滚动内容区
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

        def _scroll_win(e):
            if self._closing: return
            try: cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
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
        #   1. 硅基流动（强烈推荐）
        # ══════════════════════════════════════════════════════
        self._section(inner, "1", "硅基流动 SiliconFlow",
                      "★ 强烈推荐 · 国内服务 · 速度快 · 注册送免费额度", C["ok"], PX)
        self._info_card(inner, [
            "• 中国国产云平台，注册即送免费额度，支持 FLUX.1-schnell / SDXL 等",
            "• 生图速度约 2~5 秒，推理质量高，支持最大 1024×1024",
            "• v3 HQ变体模式：优先使用 FLUX.1-dev（28步），画质显著高于 schnell",
        ], PX)
        sf_row = tk.Frame(inner, bg=C["bg"]); sf_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(sf_row, text="硅基流动 API Key:",
                 font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef0 = tk.Frame(sf_row, bg=C["entry"]); ef0.pack(fill="x", pady=(4, 0))
        self.sf_var = tk.StringVar(value=self.cfg.get("sf_key", ""))
        self.sf_entry = tk.Entry(ef0, textvariable=self.sf_var, show="*",
                                  bg=C["entry"], fg=C["text"], insertbackground="white",
                                  font=F["input"], bd=0, relief="flat")
        self.sf_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef0, self.sf_entry)
        sf_btns = tk.Frame(inner, bg=C["bg"]); sf_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(sf_btns, text="🌐 注册硅基流动（免费）",
                  font=F["body"], bg="#22c55e", fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://cloud.siliconflow.cn/account/ak")
                  ).pack(side="left")
        tk.Button(sf_btns, text="🔑 登录后获取 API Key",
                  font=F["body"], bg=C["acc"], fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://cloud.siliconflow.cn/account/ak")
                  ).pack(side="left", padx=(8, 0))
        self._hint(inner,
                   "📋 步骤：打开链接 → 注册/登录 → 账户 → API密钥 → 新建 → 复制（格式: sk-xxxxx）",
                   PX)

        # ══════════════════════════════════════════════════════
        #   2. Pollinations.AI（完全免费，无需 Key）
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "2", "Pollinations.AI",
                      "🆓 完全免费 · 无需注册 · 无需 Key · FLUX 高质量", "#34d399", PX)
        self._info_card(inner, [
            "• 完全开源的生成平台（柏林团队），基于 FLUX.1 模型，质量优秀",
            "• 无需注册、无需 API Key，直接启用即可使用",
            "• v2 HQ变体模式：开启 enhance=true（AI 自动丰富提示词），提升画面细节",
        ], PX)
        poll_f = tk.Frame(inner, bg=C["card"],
                          highlightbackground="#22c55e", highlightthickness=1)
        poll_f.pack(fill="x", padx=PX, pady=(8, 0))
        poll_inner = tk.Frame(poll_f, bg=C["card"])
        poll_inner.pack(fill="x", padx=12, pady=10)
        self.poll_enabled_var = tk.BooleanVar(
            value=self.cfg.get("pollinations_enabled", True))
        tk.Checkbutton(
            poll_inner,
            text="✅ 启用 Pollinations.AI（无需配置，直接使用）",
            variable=self.poll_enabled_var,
            font=F["btn"],
            bg=C["card"], fg="#34d399",
            activebackground=C["card"], activeforeground=C["text"],
            selectcolor=C["entry"]
        ).pack(anchor="w")
        tk.Label(poll_inner,
                 text="勾选后 Pollinations.AI 将在接口列表中出现，可直接选用",
                 font=F["small_i"], bg=C["card"], fg=C["sub"]
                 ).pack(anchor="w", pady=(2, 0))
        poll_btns = tk.Frame(inner, bg=C["bg"]); poll_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(poll_btns, text="🌐 官网：pollinations.ai",
                  font=F["body"], bg="#065f46", fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://pollinations.ai")
                  ).pack(side="left")

        # v7：Pollinations 新平台可能已要求鉴权，留一个可选 Key 输入框
        poll_key_row = tk.Frame(inner, bg=C["bg"]); poll_key_row.pack(fill="x", padx=PX, pady=(10, 0))
        tk.Label(poll_key_row, text="Pollinations Key（可选，遇 401 再填）:",
                 font=F["body"], bg=C["bg"], fg=C["sub"]).pack(anchor="w")
        ef_pk = tk.Frame(poll_key_row, bg=C["entry"]); ef_pk.pack(fill="x", pady=(4, 0))
        self.pk_var = tk.StringVar(value=self.cfg.get("pollinations_key", ""))
        self.pk_entry = tk.Entry(ef_pk, textvariable=self.pk_var, show="*",
                                  bg=C["entry"], fg=C["text"], insertbackground="white",
                                  font=F["input"], bd=0, relief="flat")
        self.pk_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_pk, self.pk_entry)

        # ══════════════════════════════════════════════════════
        #   3. Cloudflare Workers AI
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "3", "Cloudflare Workers AI",
                      "🆓 免费 10,000 neurons/天 · FLUX.1-schnell · SDXL · 全球 CDN 加速",
                      "#60a5fa", PX)
        self._info_card(inner, [
            "• Cloudflare 全球节点加速，FLUX.1-schnell + SDXL 高质量模型",
            "• 每天 10,000 free neurons ≈ 约 10~20 张全分辨率图片，完全免费",
            "• 需要：① Cloudflare Account ID  ② API Token（Workers AI Read 权限）",
            "• 注册免费，无需信用卡；API Token 仅需 Read 权限，安全性高",
        ], PX)

        cf_row = tk.Frame(inner, bg=C["bg"]); cf_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(cf_row, text="Cloudflare Account ID:",
                 font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_cfid = tk.Frame(cf_row, bg=C["entry"]); ef_cfid.pack(fill="x", pady=(4, 0))
        self.cf_id_var = tk.StringVar(value=self.cfg.get("cf_account_id", ""))
        cf_id_entry = tk.Entry(ef_cfid, textvariable=self.cf_id_var,
                                bg=C["entry"], fg=C["text"], insertbackground="white",
                                font=F["input"], bd=0, relief="flat")
        cf_id_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._gb(ef_cfid, cf_id_entry)

        cf_tok_row = tk.Frame(inner, bg=C["bg"]); cf_tok_row.pack(fill="x", padx=PX, pady=(10, 0))
        tk.Label(cf_tok_row, text="Cloudflare API Token:",
                 font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_cftok = tk.Frame(cf_tok_row, bg=C["entry"]); ef_cftok.pack(fill="x", pady=(4, 0))
        self.cf_tok_var = tk.StringVar(value=self.cfg.get("cf_api_token", ""))
        cf_tok_entry = tk.Entry(ef_cftok, textvariable=self.cf_tok_var, show="*",
                                 bg=C["entry"], fg=C["text"], insertbackground="white",
                                 font=F["input"], bd=0, relief="flat")
        cf_tok_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_cftok, cf_tok_entry)

        cf_btns = tk.Frame(inner, bg=C["bg"]); cf_btns.pack(fill="x", padx=PX, pady=(10, 0))
        tk.Button(cf_btns, text="🌐 注册 Cloudflare（免费）",
                  font=F["body"], bg="#1d4ed8", fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://dash.cloudflare.com")
                  ).pack(side="left")
        tk.Button(cf_btns, text="🔑 创建 API Token",
                  font=F["body"], bg=C["acc"], fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open(
                      "https://dash.cloudflare.com/profile/api-tokens")
                  ).pack(side="left", padx=(8, 0))
        tk.Button(cf_btns, text="📖 查看 Workers AI 文档",
                  font=F["body"], bg="#1e3a5a", fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open(
                      "https://developers.cloudflare.com/workers-ai/models/")
                  ).pack(side="left", padx=(8, 0))
        self._hint(inner,
                   "📋 步骤：① dash.cloudflare.com 注册 → ② 右侧找到 Account ID 并复制 "
                   "→ ③ Profile → API Tokens → Create Token → 选 Workers AI (Read) → 复制 Token",
                   PX)

        # ══════════════════════════════════════════════════════
        #   4. ModelsLab
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "4", "ModelsLab API",
                      "🆓 免费 100次/天 · FLUX/SDXL/10000+模型 · 无需信用卡",
                      "#a78bfa", PX)
        self._info_card(inner, [
            "• 印度 AI 平台，注册免费获得每日 100 次 API 配额，无需信用卡",
            "• 支持 FLUX.1-schnell / SDXL / Stable Diffusion 及 10,000+ 社区模型",
            "• 每日 100 次配额适合个人日常使用，次日自动重置",
            "• API 稳定（2~5秒响应），支持异步处理模式",
        ], PX)
        ml_row = tk.Frame(inner, bg=C["bg"]); ml_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(ml_row, text="ModelsLab API Key:",
                 font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_ml = tk.Frame(ml_row, bg=C["entry"]); ef_ml.pack(fill="x", pady=(4, 0))
        self.ml_var = tk.StringVar(value=self.cfg.get("modelslab_key", ""))
        self.ml_entry = tk.Entry(ef_ml, textvariable=self.ml_var, show="*",
                                  bg=C["entry"], fg=C["text"], insertbackground="white",
                                  font=F["input"], bd=0, relief="flat")
        self.ml_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_ml, self.ml_entry)
        ml_btns = tk.Frame(inner, bg=C["bg"]); ml_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(ml_btns, text="🌐 注册 ModelsLab（免费）",
                  font=F["body"], bg="#7c3aed", fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://modelslab.com")
                  ).pack(side="left")
        tk.Button(ml_btns, text="🔑 Dashboard → API Keys",
                  font=F["body"], bg=C["acc"], fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open(
                      "https://modelslab.com/dashboard/account/api-keys")
                  ).pack(side="left", padx=(8, 0))
        self._hint(inner,
                   "📋 步骤：注册 → Dashboard → Account → API Keys → Copy Key",
                   PX)

        # ══════════════════════════════════════════════════════
        #   5. Segmind（注册送 $5）
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "5", "Segmind API",
                      "注册送 $5 · SDXL/FLUX 高质量 · 印度云平台", "#f59e0b", PX)
        self._info_card(inner, [
            "• 印度 AI 云平台，支持 500+ 模型，注册即送 $5 免费额度",
            "• $5 额度约可生成 200~500 张图片（视模型而定）",
            "• 模型：SDXL 1.0（steps=30）/ FLUX Schnell / Stable Diffusion 3",
        ], PX)
        sg_row = tk.Frame(inner, bg=C["bg"]); sg_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(sg_row, text="Segmind API Key:",
                 font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_sg = tk.Frame(sg_row, bg=C["entry"]); ef_sg.pack(fill="x", pady=(4, 0))
        self.sg_var = tk.StringVar(value=self.cfg.get("segmind_key", ""))
        self.sg_entry = tk.Entry(ef_sg, textvariable=self.sg_var, show="*",
                                  bg=C["entry"], fg=C["text"], insertbackground="white",
                                  font=F["input"], bd=0, relief="flat")
        self.sg_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_sg, self.sg_entry)
        sg_btns = tk.Frame(inner, bg=C["bg"]); sg_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(sg_btns, text="🌐 注册 Segmind（免费送 $5）",
                  font=F["body"], bg="#d97706", fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://www.segmind.com")
                  ).pack(side="left")
        tk.Button(sg_btns, text="🔑 Dashboard → API Keys",
                  font=F["body"], bg=C["acc"], fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://www.segmind.com/dashboard")
                  ).pack(side="left", padx=(8, 0))

        # ══════════════════════════════════════════════════════
        #   6. HuggingFace
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "6", "HuggingFace Token", "备用接口", C["warn"], PX)
        self._info_card(inner, [
            "• 免费注册，作为上述接口的备用",
            "• 支持 FLUX.1-schnell / SDXL 等模型，有速率限制",
        ], PX)
        hf_row = tk.Frame(inner, bg=C["bg"]); hf_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(hf_row, text="HuggingFace Token:",
                 font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef1 = tk.Frame(hf_row, bg=C["entry"]); ef1.pack(fill="x", pady=(4, 0))
        self.hf_var = tk.StringVar(value=self.cfg.get("hf_token", ""))
        self.hf_entry = tk.Entry(ef1, textvariable=self.hf_var, show="*",
                                  bg=C["entry"], fg=C["text"], insertbackground="white",
                                  font=F["input"], bd=0, relief="flat")
        self.hf_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef1, self.hf_entry)
        hf_btns = tk.Frame(inner, bg=C["bg"]); hf_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(hf_btns, text="🌐 注册 HuggingFace",
                  font=F["body"], bg=C["acc"], fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://huggingface.co/join")
                  ).pack(side="left")
        tk.Button(hf_btns, text="🔑 创建 Token（类型选 Read）",
                  font=F["body"], bg=C["acc"], fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open(
                      "https://huggingface.co/settings/tokens/new?tokenType=read")
                  ).pack(side="left", padx=(8, 0))

        # ══════════════════════════════════════════════════════
        #   7. StableHorde（兜底）
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "7", "StableHorde Key",
                      "兜底接口，队列长时自动跳过", C["sub"], PX)
        self._info_card(inner, [
            "• 完全免费，无需填写（留空使用匿名 Key）",
            "• 高峰期队列可能较长，程序检测到队列过长会自动跳过",
        ], PX)
        sh_row = tk.Frame(inner, bg=C["bg"]); sh_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(sh_row, text="StableHorde Key（可选）:",
                 font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef2 = tk.Frame(sh_row, bg=C["entry"]); ef2.pack(fill="x", pady=(4, 0))
        self.sh_var = tk.StringVar(value=self.cfg.get("stablehorde_key", ""))
        self.sh_entry = tk.Entry(ef2, textvariable=self.sh_var, show="*",
                                  bg=C["entry"], fg=C["text"], insertbackground="white",
                                  font=F["input"], bd=0, relief="flat")
        self.sh_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef2, self.sh_entry)
        sh_btns = tk.Frame(inner, bg=C["bg"]); sh_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(sh_btns, text="🌐 注册 StableHorde（可选）",
                  font=F["body"], bg=C["acc"], fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://stablehorde.net/register")
                  ).pack(side="left")

        # ══════════════════════════════════════════════════════
        #   8. Together AI（v5 新增）
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "8", "Together AI",
                      "🆓 FLUX.1 Free · 免费额度 · 质量高", "#4ecca3", PX)
        self._info_card(inner, [
            "• 提供 FLUX.1-schnell-Free 免费图像生成端点，质量媲美付费模型",
            "• 注册即可使用，赠送初始 $5 额度，免费端点每月有一定配额",
            "• 速度快（通常 3~6 秒），支持最大 1024×1024",
        ], PX)
        ta_row = tk.Frame(inner, bg=C["bg"]); ta_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(ta_row, text="Together AI API Key:",
                 font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_ta = tk.Frame(ta_row, bg=C["entry"]); ef_ta.pack(fill="x", pady=(4, 0))
        self.ta_var = tk.StringVar(value=self.cfg.get("together_key", ""))
        self.ta_entry = tk.Entry(ef_ta, textvariable=self.ta_var, show="*",
                                  bg=C["entry"], fg=C["text"], insertbackground="white",
                                  font=F["input"], bd=0, relief="flat")
        self.ta_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_ta, self.ta_entry)
        ta_btns = tk.Frame(inner, bg=C["bg"]); ta_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(ta_btns, text="🌐 注册 Together AI（免费）",
                  font=F["body"], bg="#059669", fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://api.together.ai/")
                  ).pack(side="left")
        tk.Button(ta_btns, text="🔑 获取 API Key",
                  font=F["body"], bg=C["acc"], fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://api.together.ai/settings/api-keys")
                  ).pack(side="left", padx=(8, 0))
        self._hint(inner,
                   "📋 步骤：注册 → Settings → API Keys → New Key → 复制（格式: xxxx...）",
                   PX)

        # ══════════════════════════════════════════════════════
        #   9. Google Gemini Nano Banana（v5 新增，v7 更新）
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "9", "Google Gemini  Nano Banana",
                      "🆓 免费额度 · 无需绑卡 · 支持图生图", "#34d399", PX)
        self._info_card(inner, [
            "• Google 图像模型 \"Nano Banana\"（Gemini 2.5 Flash Image），免费额度",
            "• 通过 Google AI Studio 获取 API Key，登录 Google 账号即可，全程免费",
            "• 支持图生图（切到「图生图」模式后自动传入参考图）",
            "• 同一个 Key 也用于「💎 付费接口配置」里更高画质的 Nano Banana Pro",
        ], PX)
        gm_row = tk.Frame(inner, bg=C["bg"]); gm_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(gm_row, text="Gemini API Key:",
                 font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_gm = tk.Frame(gm_row, bg=C["entry"]); ef_gm.pack(fill="x", pady=(4, 0))
        self.gm_var = tk.StringVar(value=self.cfg.get("gemini_key", ""))
        self.gm_entry = tk.Entry(ef_gm, textvariable=self.gm_var, show="*",
                                  bg=C["entry"], fg=C["text"], insertbackground="white",
                                  font=F["input"], bd=0, relief="flat")
        self.gm_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_gm, self.gm_entry)
        gm_btns = tk.Frame(inner, bg=C["bg"]); gm_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(gm_btns, text="🌐 打开 Google AI Studio（免费）",
                  font=F["body"], bg="#1a6b3c", fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://aistudio.google.com/apikey")
                  ).pack(side="left")
        tk.Button(gm_btns, text="🔑 生成 API Key",
                  font=F["body"], bg=C["acc"], fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://aistudio.google.com/apikey")
                  ).pack(side="left", padx=(8, 0))
        self._hint(inner,
                   "📋 步骤：用 Google 账号登录 AI Studio → Get API Key → Create API Key → 复制",
                   PX)
        gm_mrow = tk.Frame(inner, bg=C["bg"]); gm_mrow.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(gm_mrow, text="图像模型:", font=F["body"],
                 bg=C["bg"], fg=C["sub"]).pack(side="left")
        self.gm_model_var = tk.StringVar(
            value=self.cfg.get("gemini_model", "gemini-2.5-flash-image"))
        ttk.Combobox(gm_mrow, textvariable=self.gm_model_var, width=26, state="readonly",
                     values=["gemini-2.5-flash-image", "gemini-3.1-flash-image"]
                     ).pack(side="left", padx=(6, 20))

        # ══════════════════════════════════════════════════════
        #   10. 阿里云 DashScope 通义万相 Qwen-Image（v7 新增）
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "10", "阿里云 通义万相 / Qwen-Image",
                      "🆓 新用户免费额度 · 国内直连速度快", "#ff6a00", PX)
        self._info_card(inner, [
            "• 阿里云 DashScope 平台，wanx2.1-t2i-turbo 模型，新用户有免费调用额度",
            "• 国内网络直连，无需代理，速度稳定",
            "• 提交任务后异步轮询，出图通常在 10~30 秒内完成",
        ], PX)
        ds_row = tk.Frame(inner, bg=C["bg"]); ds_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(ds_row, text="DashScope API Key:",
                 font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_ds = tk.Frame(ds_row, bg=C["entry"]); ef_ds.pack(fill="x", pady=(4, 0))
        self.ds_var = tk.StringVar(value=self.cfg.get("dashscope_key", ""))
        self.ds_entry = tk.Entry(ef_ds, textvariable=self.ds_var, show="*",
                                  bg=C["entry"], fg=C["text"], insertbackground="white",
                                  font=F["input"], bd=0, relief="flat")
        self.ds_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_ds, self.ds_entry)
        ds_btns = tk.Frame(inner, bg=C["bg"]); ds_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(ds_btns, text="🌐 注册阿里云 DashScope",
                  font=F["body"], bg="#ff6a00", fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://dashscope.console.aliyun.com/")
                  ).pack(side="left")
        tk.Button(ds_btns, text="🔑 获取 API Key",
                  font=F["body"], bg=C["acc"], fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open(
                      "https://dashscope.console.aliyun.com/apiKey")
                  ).pack(side="left", padx=(8, 0))

        # ══════════════════════════════════════════════════════
        #   11. Bria AI（v7 新增）
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "11", "Bria AI  Fibo",
                      "🆓 注册送 1000 次免费调用 · 商业合规定位", "#8b5cf6", PX)
        self._info_card(inner, [
            "• Fibo 模型，训练数据经授权，主打商业可用/版权合规场景",
            "• 新用户注册即送 1000 次免费 API 调用",
            "• 同步返回（sync=true），无需等待轮询",
        ], PX)
        br_row = tk.Frame(inner, bg=C["bg"]); br_row.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(br_row, text="Bria AI API Key:",
                 font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_br = tk.Frame(br_row, bg=C["entry"]); ef_br.pack(fill="x", pady=(4, 0))
        self.br_var = tk.StringVar(value=self.cfg.get("bria_key", ""))
        self.br_entry = tk.Entry(ef_br, textvariable=self.br_var, show="*",
                                  bg=C["entry"], fg=C["text"], insertbackground="white",
                                  font=F["input"], bd=0, relief="flat")
        self.br_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_br, self.br_entry)
        br_btns = tk.Frame(inner, bg=C["bg"]); br_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(br_btns, text="🌐 注册 Bria AI（送 1000 次）",
                  font=F["body"], bg="#7c3aed", fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: webbrowser.open("https://platform.bria.ai/")
                  ).pack(side="left")

        # ══════════════════════════════════════════════════════
        #   变体质量模式
        # ══════════════════════════════════════════════════════
        self._divider(inner)
        qual_hdr = tk.Frame(inner, bg=C["bg"]); qual_hdr.pack(fill="x", padx=PX, pady=(0, 4))
        tk.Label(qual_hdr, text=" Q ", font=F["btn"],
                 bg=C["hl"], fg="white").pack(side="left")
        tk.Label(qual_hdr, text="  变体生成质量模式",
                 font=F["h1"], bg=C["bg"], fg=C["text"]).pack(side="left")
        tk.Label(qual_hdr, text="  影响批量变体的画质与速度平衡",
                 font=F["body"], bg=C["bg"], fg=C["warn"]).pack(side="left")

        qual_card = tk.Frame(inner, bg=C["card"],
                             highlightbackground="#3a4a6a", highlightthickness=1)
        qual_card.pack(fill="x", padx=PX, pady=(4, 0))
        qual_inner = tk.Frame(qual_card, bg=C["card"])
        qual_inner.pack(fill="x", padx=16, pady=12)

        self.qual_var = tk.StringVar(
            value=self.cfg.get("variant_quality", "high"))

        for val, label, desc, tag_col in [
            ("high",     "🎨 高质量模式（推荐）",
             "硅基流动优先 FLUX.1-dev(28步)，Pollinations 开启 enhance，效果更佳，耗时稍长",
             C["ok"]),
            ("standard", "⚡ 标准模式",
             "各接口使用默认参数，速度更快，适合快速预览",
             C["warn"]),
        ]:
            row = tk.Frame(qual_inner, bg=C["card"]); row.pack(fill="x", pady=3)
            tk.Radiobutton(
                row, text=label,
                variable=self.qual_var, value=val,
                font=F["btn"],
                bg=C["card"], fg=tag_col,
                activebackground=C["card"], activeforeground=C["text"],
                selectcolor=C["entry"]
            ).pack(side="left")
            tk.Label(row, text=f"  {desc}",
                     font=F["small_i"], bg=C["card"], fg=C["sub"]
                     ).pack(side="left")

        # ── 启动选项 ────────────────────────────────────────────
        self._divider(inner)
        opts_f = tk.Frame(inner, bg=C["bg"]); opts_f.pack(fill="x", padx=PX, pady=(0, 24))
        self.show_wiz_var = tk.BooleanVar(value=self.cfg.get("show_wizard_on_start", True))
        tk.Checkbutton(opts_f,
                       text="下次启动时不再显示此向导（可在「⚙ 设置」中重新打开）",
                       variable=self.show_wiz_var,
                       font=F["body"], bg=C["bg"], fg=C["sub"],
                       activebackground=C["bg"], activeforeground=C["text"],
                       selectcolor=C["entry"]).pack(anchor="w")

    # ── 辅助控件 ───────────────────────────────────────────────
    def _section(self, parent, num, title, tag, tag_color, px=24):
        f = tk.Frame(parent, bg=C["bg"])
        f.pack(fill="x", padx=px, pady=(16, 4))
        tk.Label(f, text=f" {num} ", font=F["btn"],
                 bg=C["hl"], fg="white").pack(side="left")
        tk.Label(f, text=f"  {title}", font=F["h1"],
                 bg=C["bg"], fg=C["text"]).pack(side="left")
        tk.Label(f, text=f"  {tag}", font=F["body"],
                 bg=C["bg"], fg=tag_color).pack(side="left")

    def _info_card(self, parent, lines, px=24):
        
        card = tk.Frame(parent, bg=C["card"],
                        highlightbackground="#2a3a5a", highlightthickness=1)
        card.pack(fill="x", padx=px, pady=(4, 0))
        for line in lines:
            tk.Label(card, text=line, font=F["body"],
                     bg=C["card"], fg=C["sub"], anchor="w", justify="left"
                     ).pack(anchor="w", padx=12, pady=2)
        tk.Label(card, text="").pack(pady=2)

    def _hint(self, parent, text, px=24):
        
        tk.Label(parent, text=text, font=F["body_i"],
                 bg=C["bg"], fg=C["warn"], wraplength=740,
                 justify="left", anchor="w"
                 ).pack(fill="x", padx=px, pady=(6, 0))

    def _divider(self, parent):
        tk.Frame(parent, bg="#2a3a5a", height=1).pack(fill="x", padx=24, pady=12)

    @staticmethod
    def _gb(frame: tk.Frame, entry) -> None:
        """绿边 idle，获焦后变隐形。"""
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
        self._gb(parent, entry)  # 绿边：idle 显示，获焦后隐藏

    def _save(self):
        self._dirty = False
        self.cfg["sf_key"]               = self.sf_var.get().strip()
        self.cfg["hf_token"]             = self.hf_var.get().strip()
        self.cfg["stablehorde_key"]      = self.sh_var.get().strip()
        self.cfg["segmind_key"]          = self.sg_var.get().strip()
        self.cfg["pollinations_enabled"] = self.poll_enabled_var.get()
        self.cfg["cf_account_id"]        = self.cf_id_var.get().strip()
        self.cfg["cf_api_token"]         = self.cf_tok_var.get().strip()
        self.cfg["modelslab_key"]        = self.ml_var.get().strip()
        self.cfg["together_key"]         = self.ta_var.get().strip()   # v5 新增
        self.cfg["gemini_key"]           = self.gm_var.get().strip()   # v5 新增
        self.cfg["gemini_model"]         = self.gm_model_var.get()     # 添加 Gemini 3.1 图像模型
        self.cfg["pollinations_key"]     = self.pk_var.get().strip()   # v7 新增
        self.cfg["dashscope_key"]        = self.ds_var.get().strip()   # v7 新增
        self.cfg["bria_key"]             = self.br_var.get().strip()   # v7 新增
        self.cfg["variant_quality"]      = self.qual_var.get()
        self.cfg["show_wizard_on_start"] = not self.show_wiz_var.get()
        from config.settings import save_config
        save_config(self.cfg)
        self.on_save(self.cfg)
        self.destroy()
