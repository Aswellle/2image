"""
ui/wizard_llm.py
AI 提示词助手 · 推理模型密钥配置向导

独立于生图密钥向导（wizard_free/paid），专门引导用户配置
用于生成生图提示词的 LLM 推理模型 API Key。

支持的通道（按推荐顺序）：
  1. 硅基流动 SiliconFlow  →  sf_key（自动候选：DeepSeek V3 / Qwen2.5-72B）
  2. DeepSeek 官方 API      →  deepseek_key（显式 Pro / Flash 预设）
  3. HuggingFace            →  hf_token（免费兜底：Mixtral / Zephyr）

硅基流动与 HuggingFace 的 Key 与生图配置共用；DeepSeek 官方 Key 专供
AI 提示词助手的 Pro / Flash 预设。
"""
import tkinter as tk
from tkinter import ttk
import webbrowser
from typing import Callable

from config.fonts import F
from config.theme import DARK_THEME as C
from config.settings import save_config


# ── 每个模型通道的展示信息 ────────────────────────────────────────
_SF_MODELS_INFO = [
    ("🥇 DeepSeek V3-0324",  "硅基流动自动预设的首选候选"),
    ("   DeepSeek V3",        "硅基流动自动预设的稳定备用"),
    ("   Qwen2.5-72B-Instruct", "千问旗舰，英文创作能力强"),
    ("   Qwen2.5-32B-Instruct", "速度与质量均衡"),
    ("   GLM-4-9B-chat",       "轻量兜底，保证最低可用性"),
]

_DEEPSEEK_PRESETS_INFO = [
    ("deepseek_pro", "DeepSeek Pro", "质量优先 · 更强推理/指令遵循 · 官方 API 按量计费"),
    ("deepseek_flash", "DeepSeek Flash", "速度优先 · 低延迟/低成本 · 官方 API 按量计费"),
]

_HF_MODELS_INFO = [
    ("Mixtral-8x7B-Instruct", "效果较好，但速度受免费队列影响"),
    ("Zephyr-7b-beta",        "轻量快速，效果一般"),
]


class LLMWizard(tk.Toplevel):
    """AI 提示词助手模型密钥配置向导（模态对话框）。"""

    def __init__(self, parent: tk.Tk, cfg: dict, on_save: Callable[[dict], None]):
        super().__init__(parent)
        self.cfg      = cfg.copy()
        self.on_save  = on_save
        self._closing = False
        self._dirty   = False

        self.title("🤖 AI 提示词助手 · 模型密钥配置")
        self.geometry("780x700")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.minsize(640, 520)
        self.grab_set()
        self.focus_set()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width()  - 780) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 700) // 2
        self.geometry(f"780x700+{max(0,x)}+{max(0,y)}")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build()
        for v in (self.sf_var, self.deepseek_var, self.hf_var, self.preset_var):
            v.trace("w", lambda *_: setattr(self, "_dirty", True))

    # ──────────────────────────────────────────────────────────────
    #   关闭
    # ──────────────────────────────────────────────────────────────
    def _on_close(self):
        self._closing = True
        try:
            self.unbind_all("<MouseWheel>")
            self.unbind_all("<Button-4>")
            self.unbind_all("<Button-5>")
        except Exception:
            pass
        self.destroy()

    # ──────────────────────────────────────────────────────────────
    #   构建界面
    # ──────────────────────────────────────────────────────────────
    def _build(self):
        PX = 24

        # ── 底部按钮（先 pack，确保不被内容挤掉）────────────────────
        bot = tk.Frame(self, bg=C["panel"])
        bot.pack(fill="x", side="bottom")
        tk.Button(
            bot, text="💾  保存并关闭",
            font=F["h2"], bg=C["ok"], fg="#0a1a0a",
            bd=0, padx=24, pady=10, cursor="hand2",
            command=self._save,
        ).pack(side="right", padx=20, pady=12)
        tk.Button(
            bot, text="稍后配置",
            font=F["body"], bg=C["panel"], fg=C["sub"],
            bd=0, padx=16, pady=10, cursor="hand2",
            command=self._on_close,
        ).pack(side="right", pady=12)
        self._status_lbl = tk.Label(
            bot, text="", font=F["body"], bg=C["panel"], fg=C["ok"])
        self._status_lbl.pack(side="left", padx=16, pady=12)

        # ── 标题栏 ──────────────────────────────────────────────────
        hdr = tk.Frame(self, bg="#4c1d95")   # 紫色，区别于生图向导的蓝色
        hdr.pack(fill="x")
        tk.Label(
            hdr, text="🤖  AI 提示词助手 · 模型密钥配置",
            font=(F["_sans"], 15, "bold"), bg="#4c1d95", fg="white",
        ).pack(side="left", padx=20, pady=14)
        tk.Label(
            hdr, text="配置后即可使用 AI 自动生成高质量生图提示词",
            font=F["body"], bg="#4c1d95", fg="#d8b4fe",
        ).pack(side="right", padx=20)

        # ── 可滚动内容区 ────────────────────────────────────────────
        fo  = tk.Frame(self, bg=C["bg"])
        fo.pack(fill="both", expand=True)
        cv  = tk.Canvas(fo, bg=C["bg"], bd=0, highlightthickness=0)
        vsb = ttk.Scrollbar(fo, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(cv, bg=C["bg"])
        cwin  = cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",    lambda e: cv.itemconfig(cwin, width=e.width))

        def _scroll(e):
            if self._closing: return
            try: cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except tk.TclError: pass
        def _scroll_up(e):
            if self._closing: return
            try: cv.yview_scroll(-1, "units")
            except tk.TclError: pass
        def _scroll_dn(e):
            if self._closing: return
            try: cv.yview_scroll(1, "units")
            except tk.TclError: pass
        self.bind_all("<MouseWheel>", _scroll)
        self.bind_all("<Button-4>",   _scroll_up)
        self.bind_all("<Button-5>",   _scroll_dn)

        # ══════════════════════════════════════════════════════════
        #   顶部：已配置状态提示
        # ══════════════════════════════════════════════════════════
        self._build_status_banner(inner, PX)

        # ══════════════════════════════════════════════════════════
        #   模型预设：自动 / DeepSeek Pro / DeepSeek Flash
        # ══════════════════════════════════════════════════════════
        self._section(inner, "0", "提示词模型预设",
                      "选择质量优先或速度优先的调用路径", "#c084fc", PX)
        preset_card = tk.Frame(inner, bg="#17233d",
                               highlightbackground=C["purple"], highlightthickness=1)
        preset_card.pack(fill="x", padx=PX, pady=(4, 0))
        self.preset_var = tk.StringVar(
            value=self.cfg.get("prompt_llm_preset", "siliconflow_auto"))
        self._preset_cards = {}

        preset_header = tk.Frame(preset_card, bg="#17233d")
        preset_header.pack(fill="x", padx=14, pady=(10, 5))
        tk.Label(preset_header, text="单选模型预设",
                 font=F["body_b"], bg="#17233d", fg="#e9d5ff"
                 ).pack(side="left")
        tk.Label(preset_header,
                 text="请选择 1 个模型作为 AI 提示词助手的调用路径",
                 font=F["small"], bg="#17233d", fg="#94a3b8"
                 ).pack(side="left", padx=(10, 0))
        tk.Label(preset_header, text="◉ 当前使用", font=F["small_b"],
                 bg="#17233d", fg="#c084fc"
                 ).pack(side="right")

        presets = [
            ("siliconflow_auto", "硅基流动自动（推荐）",
             "按 DeepSeek V3 → Qwen → GLM 自动降级；复用 sf_key，适合免费/稳妥使用", C["ok"]),
            *[(key, name, desc, "#c084fc")
              for key, name, desc in _DEEPSEEK_PRESETS_INFO],
        ]

        def _select_preset(key):
            self.preset_var.set(key)

        for key, title, desc, accent in presets:
            card = tk.Frame(preset_card, bg="#1a2238",
                            highlightbackground="#2a3a5a", highlightthickness=1,
                            cursor="hand2")
            card.pack(fill="x", padx=12, pady=4)
            indicator = tk.Label(card, text="○", font=F["h2"],
                                 bg="#1a2238", fg="#64748b", cursor="hand2")
            indicator.pack(side="left", padx=(12, 8), pady=9)
            text_f = tk.Frame(card, bg="#1a2238", cursor="hand2")
            text_f.pack(side="left", fill="x", expand=True, pady=7)
            title_lbl = tk.Label(text_f, text=title, font=F["body_b"],
                                 bg="#1a2238", fg=accent, anchor="w", cursor="hand2")
            title_lbl.pack(fill="x")
            desc_lbl = tk.Label(text_f, text=desc, font=F["small"],
                                bg="#1a2238", fg=C["sub"], anchor="w", cursor="hand2")
            desc_lbl.pack(fill="x", pady=(2, 0))
            badge = tk.Label(card, text="点击选择", font=F["small_b"],
                             bg="#1a2238", fg="#64748b", cursor="hand2")
            badge.pack(side="right", padx=12)
            self._preset_cards[key] = (card, indicator, text_f, title_lbl, desc_lbl, badge, accent)
            for widget in (card, indicator, text_f, title_lbl, desc_lbl, badge):
                widget.bind("<Button-1>", lambda _e, k=key: _select_preset(k))

        self.preset_var.trace_add("write", lambda *_: self._refresh_preset_cards())
        self._refresh_preset_cards()
        tk.Label(preset_card, text="", bg="#17233d").pack(pady=4)

        deepseek_row = tk.Frame(inner, bg=C["bg"])
        deepseek_row.pack(fill="x", padx=PX, pady=(10, 0))
        tk.Label(deepseek_row, text="DeepSeek 官方 API Key（Pro / Flash 预设专用）:",
                 font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef_ds = tk.Frame(deepseek_row, bg=C["entry"])
        ef_ds.pack(fill="x", pady=(4, 0))
        self.deepseek_var = tk.StringVar(value=self.cfg.get("deepseek_key", ""))
        self.deepseek_entry = tk.Entry(
            ef_ds, textvariable=self.deepseek_var, show="*",
            bg=C["entry"], fg=C["text"], insertbackground="white",
            font=F["input"], bd=0, relief="flat")
        self.deepseek_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef_ds, self.deepseek_entry)

        ds_btns = tk.Frame(inner, bg=C["bg"])
        ds_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(
            ds_btns, text="🌐 DeepSeek 官方平台",
            font=F["body"], bg="#2563eb", fg="white",
            bd=0, padx=12, pady=5, cursor="hand2",
            command=lambda: webbrowser.open("https://platform.deepseek.com"),
        ).pack(side="left")
        self._hint(inner,
                   "提示：Pro / Flash 使用 DeepSeek 官方 API（api.deepseek.com），"
                   "不能复用硅基流动 sf_key；未填 Key 时请选回「硅基流动自动」。",
                   PX)

        # ══════════════════════════════════════════════════════════
        #   Section 1：硅基流动（强烈推荐）
        # ══════════════════════════════════════════════════════════
        self._section(inner, "1", "硅基流动 SiliconFlow",
                      "⭐ 强烈推荐 · DeepSeek V3 · 免费额度 · 国内访问快", C["ok"], PX)

        self._info_card(inner, [
            "• 注册即送免费 Token，DeepSeek V3-0324 / Qwen2.5-72B 等顶级模型均可调用",
            "• 同一个 sf_key 同时用于生图和提示词生成，已在「免费配置」中填写则此处自动预填",
            "• 提示词生成约消耗 200~400 token/次，免费额度通常够用数百次",
        ], PX)

        # 模型优先级展示
        model_f = tk.Frame(inner, bg=C["card"],
                           highlightbackground=C["purple"], highlightthickness=1)
        model_f.pack(fill="x", padx=PX, pady=(6, 0))
        tk.Label(model_f, text="  模型调用优先级（自动降级，无需手动选择）",
                 font=F["body_b"], bg=C["card"], fg=C["purple"]
                 ).pack(anchor="w", padx=12, pady=(8, 4))
        for name, desc in _SF_MODELS_INFO:
            row = tk.Frame(model_f, bg=C["card"])
            row.pack(fill="x", padx=12, pady=1)
            tk.Label(row, text=name, font=F["mono_sm_b"],
                     bg=C["card"], fg=C["text"], width=26, anchor="w"
                     ).pack(side="left")
            tk.Label(row, text=desc, font=F["small"],
                     bg=C["card"], fg=C["sub"], anchor="w"
                     ).pack(side="left", padx=(4, 0))
        tk.Label(model_f, text="").pack(pady=2)

        # Key 输入
        key_row = tk.Frame(inner, bg=C["bg"])
        key_row.pack(fill="x", padx=PX, pady=(10, 0))
        tk.Label(key_row, text="硅基流动 API Key（sf_key）:",
                 font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef0 = tk.Frame(key_row, bg=C["entry"])
        ef0.pack(fill="x", pady=(4, 0))
        self.sf_var = tk.StringVar(value=self.cfg.get("sf_key", ""))
        self.sf_entry = tk.Entry(
            ef0, textvariable=self.sf_var, show="*",
            bg=C["entry"], fg=C["text"], insertbackground="white",
            font=F["input"], bd=0, relief="flat")
        self.sf_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef0, self.sf_entry)

        # 按钮
        sf_btns = tk.Frame(inner, bg=C["bg"])
        sf_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(
            sf_btns, text="🌐 注册硅基流动（免费）",
            font=F["body"], bg="#22c55e", fg="white",
            bd=0, padx=12, pady=5, cursor="hand2",
            command=lambda: webbrowser.open("https://cloud.siliconflow.cn/i/free"),
        ).pack(side="left")
        tk.Button(
            sf_btns, text="🔑 获取 API Key",
            font=F["body"], bg=C["acc"], fg="white",
            bd=0, padx=12, pady=5, cursor="hand2",
            command=lambda: webbrowser.open("https://cloud.siliconflow.cn/account/ak"),
        ).pack(side="left", padx=(8, 0))

        self._hint(inner,
                   "📋 步骤：注册/登录 → 控制台 → API 密钥 → 新建密钥 → 复制（格式：sk-xxxxx）",
                   PX)

        # ══════════════════════════════════════════════════════════
        #   Section 2：HuggingFace（免费兜底）
        # ══════════════════════════════════════════════════════════
        self._divider(inner)
        self._section(inner, "2", "HuggingFace",
                      "🆓 完全免费 · 速度较慢 · 硅基流动不可用时自动切换", "#60a5fa", PX)

        self._info_card(inner, [
            "• 免费推理 API，Mixtral-8x7B / Zephyr-7b 两个模型按顺序自动尝试",
            "• 生成质量低于硅基流动，且有并发限制（免费队列可能需等待 20~60 秒）",
            "• 建议：已配置 sf_key 的情况下，hf_token 作为备用即可；也可只填 sf_key",
        ], PX)

        hf_row = tk.Frame(inner, bg=C["bg"])
        hf_row.pack(fill="x", padx=PX, pady=(10, 0))
        tk.Label(hf_row, text="HuggingFace Token（hf_token）:",
                 font=F["btn"], bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef1 = tk.Frame(hf_row, bg=C["entry"])
        ef1.pack(fill="x", pady=(4, 0))
        self.hf_var = tk.StringVar(value=self.cfg.get("hf_token", ""))
        self.hf_entry = tk.Entry(
            ef1, textvariable=self.hf_var, show="*",
            bg=C["entry"], fg=C["text"], insertbackground="white",
            font=F["input"], bd=0, relief="flat")
        self.hf_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef1, self.hf_entry)

        hf_btns = tk.Frame(inner, bg=C["bg"])
        hf_btns.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Button(
            hf_btns, text="🌐 注册 HuggingFace（免费）",
            font=F["body"], bg="#f97316", fg="white",
            bd=0, padx=12, pady=5, cursor="hand2",
            command=lambda: webbrowser.open("https://huggingface.co/join"),
        ).pack(side="left")
        tk.Button(
            hf_btns, text="🔑 获取 Access Token",
            font=F["body"], bg=C["acc"], fg="white",
            bd=0, padx=12, pady=5, cursor="hand2",
            command=lambda: webbrowser.open("https://huggingface.co/settings/tokens"),
        ).pack(side="left", padx=(8, 0))

        self._hint(inner,
                   "📋 步骤：注册/登录 → Settings → Access Tokens → New token → 复制（格式：hf_xxxxx）",
                   PX)

        # ══════════════════════════════════════════════════════════
        #   底部说明：数据安全
        # ══════════════════════════════════════════════════════════
        self._divider(inner)
        privacy_f = tk.Frame(inner, bg="#0d1f0d",
                             highlightbackground="#1a4a1a", highlightthickness=1)
        privacy_f.pack(fill="x", padx=PX, pady=(0, 16))
        for line in [
            "🔒  密钥安全说明",
            "• 密钥仅保存在本机 ~/.text_to_image_app/config.json，不上传至任何服务器",
            "• 开发版本的 .gitignore 已排除 config.json，密钥不会随代码提交到仓库",
            "• 提示词生成请求直接从你的电脑发往 SiliconFlow / HuggingFace，不经过中间服务器",
        ]:
            tk.Label(
                privacy_f, text=line,
                font=F["body_b"] if line.startswith("🔒") else F["body"],
                bg="#0d1f0d",
                fg="#4ade80" if line.startswith("🔒") else "#86efac",
                anchor="w", justify="left",
            ).pack(anchor="w", padx=14, pady=(8 if line.startswith("🔒") else 2, 2))
        tk.Label(privacy_f, text="").pack(pady=2)

    # ──────────────────────────────────────────────────────────────
    #   顶部状态横幅
    # ──────────────────────────────────────────────────────────────
    def _build_status_banner(self, parent, px):
        sf_ok = bool(self.cfg.get("sf_key", "").strip())
        hf_ok = bool(self.cfg.get("hf_token", "").strip())
        deepseek_ok = bool(self.cfg.get("deepseek_key", "").strip())
        preset = self.cfg.get("prompt_llm_preset", "siliconflow_auto")

        if preset in {"deepseek_pro", "deepseek_flash"} and deepseek_ok:
            label = "DeepSeek Pro" if preset == "deepseek_pro" else "DeepSeek Flash"
            bg, fg = "#312e81", "#c4b5fd"
            msg = f"✅  检测到 DeepSeek 官方 Key，{label} 预设可立即使用"
        elif sf_ok:
            bg, fg = "#064e3b", "#6ee7b7"
            msg = "✅  检测到已配置硅基流动 Key，AI 提示词助手可立即使用"
        elif deepseek_ok:
            bg, fg = "#312e81", "#c4b5fd"
            msg = "✅  检测到 DeepSeek 官方 Key；请选择 DeepSeek Pro 或 Flash 预设后使用"
        elif hf_ok:
            bg, fg = "#1e3a5f", "#93c5fd"
            msg = "⚠️  仅配置了 HuggingFace Token（兜底通道），建议同时配置硅基流动或 DeepSeek"
        else:
            bg, fg = "#3b1515", "#fca5a5"
            msg = "❌  尚未配置任何推理模型密钥，AI 提示词助手暂时无法使用，请至少配置一项"

        banner = tk.Frame(parent, bg=bg)
        banner.pack(fill="x", padx=px, pady=(14, 4))
        tk.Label(banner, text=msg, font=F["body_b"],
                 bg=bg, fg=fg, anchor="w", padx=12, pady=8
                 ).pack(fill="x")

    # ──────────────────────────────────────────────────────────────
    #   辅助组件（与 wizard_free 同款样式）
    # ──────────────────────────────────────────────────────────────
    def _section(self, parent, num, title, tag, tag_color, px=24):
        f = tk.Frame(parent, bg=C["bg"])
        f.pack(fill="x", padx=px, pady=(16, 4))
        tk.Label(f, text=f" {num} ", font=F["btn"],
                 bg=C["hl"], fg="white").pack(side="left")
        tk.Label(f, text=f"  {title}", font=F["h1"],
                 bg=C["bg"], fg=C["text"]).pack(side="left")
        tk.Label(f, text=f"  {tag}", font=F["body"],
                 bg=C["bg"], fg=tag_color).pack(side="left")

    def _refresh_preset_cards(self):
        """把当前 preset_var 的值投射为整行卡片的明确选中态。"""
        selected = self.preset_var.get()
        for key, (card, indicator, text_f, title_lbl, desc_lbl, badge, accent) in self._preset_cards.items():
            is_selected = key == selected
            bg = "#2e1f5c" if is_selected else "#1a2238"
            border = accent if is_selected else "#2a3a5a"
            card.config(bg=bg, highlightbackground=border)
            indicator.config(text="●" if is_selected else "○",
                             bg=bg, fg=accent if is_selected else "#64748b")
            text_f.config(bg=bg)
            title_lbl.config(bg=bg)
            desc_lbl.config(bg=bg, fg="#ddd6fe" if is_selected else C["sub"])
            badge.config(text="✓ 已选择" if is_selected else "点击选择",
                         bg=bg, fg=accent if is_selected else "#64748b")

    def _info_card(self, parent, lines, px=24):
        card = tk.Frame(parent, bg=C["card"],
                        highlightbackground=C["sep"], highlightthickness=1)
        card.pack(fill="x", padx=px, pady=(4, 0))
        for line in lines:
            tk.Label(card, text=line, font=F["body"],
                     bg=C["card"], fg=C["sub"],
                     anchor="w", justify="left"
                     ).pack(anchor="w", padx=12, pady=2)
        tk.Label(card, text="").pack(pady=2)

    def _hint(self, parent, text, px=24):
        tk.Label(parent, text=text, font=F["body_i"],
                 bg=C["bg"], fg=C["warn"],
                 wraplength=700, justify="left", anchor="w"
                 ).pack(fill="x", padx=px, pady=(6, 0))

    def _divider(self, parent):
        tk.Frame(parent, bg=C["sep"], height=1).pack(fill="x", padx=24, pady=12)

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
        # 绿边：idle 显示，获焦后隐藏
        parent.config(highlightbackground=C["ok"], highlightthickness=1)
        entry.bind("<FocusIn>",  lambda _: parent.config(highlightbackground=C["entry"]), add="+")
        entry.bind("<FocusOut>", lambda _: parent.config(highlightbackground=C["ok"]),    add="+")

    # ──────────────────────────────────────────────────────────────
    #   保存
    # ──────────────────────────────────────────────────────────────
    def _save(self):
        self._dirty = False
        sf       = self.sf_var.get().strip()
        hf       = self.hf_var.get().strip()
        deepseek = self.deepseek_var.get().strip()
        preset   = self.preset_var.get()

        if preset in {"deepseek_pro", "deepseek_flash"} and not deepseek:
            self._status_lbl.config(
                text="⚠️  Pro / Flash 预设需要填写 DeepSeek 官方 API Key", fg=C["warn"])
            return
        if preset == "siliconflow_auto" and not sf and not hf:
            self._status_lbl.config(
                text="⚠️  自动预设请至少填写硅基流动或 HuggingFace Key", fg=C["warn"])
            return

        self.cfg["sf_key"]            = sf
        self.cfg["hf_token"]          = hf
        self.cfg["deepseek_key"]      = deepseek
        self.cfg["prompt_llm_preset"] = preset
        save_config(self.cfg)
        self.on_save(self.cfg)
        self._on_close()
