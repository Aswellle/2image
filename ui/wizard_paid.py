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
from tkinter import ttk
import webbrowser
from typing import Callable
from config.fonts import F
from config.theme import DARK_THEME as C
from config.model_catalog import (
    ARK_IMAGE_DEFAULT, ARK_IMAGE_MODELS, ARK_IMAGE_NAMES,
    BFL_TXT2IMG_DEFAULT, BFL_TXT2IMG_MODELS,
    GPT_IMAGE_DEFAULT, GPT_IMAGE_NAMES,
)


class PaidWizard(tk.Toplevel):
    """付费接口（OpenAI / Stability AI / Replicate / xAI / 豆包）配置窗口。"""

    def __init__(self, parent: tk.Tk, cfg: dict, on_save: Callable[[dict], None]):
        super().__init__(parent)
        self.cfg = cfg
        self.on_save = on_save
        self._closing = False
        self._dirty = False
        self.title("💎 付费接口配置")
        self.geometry("820x720")
        self.configure(bg=C["bg"])
        self._build()
        self.grab_set()

    def _on_close(self):
        """关闭窗口前先解绑 bind_all，防止 Canvas 销毁后仍触发 TclError。"""
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

        hdr = tk.Frame(self, bg=C["paid"]); hdr.pack(fill="x")
        tk.Label(hdr, text="💎 付费接口配置",
                 font=F["title"], bg=C["paid"], fg="white"
                 ).pack(side="left", padx=20, pady=14)
        tk.Label(hdr, text="GPT-Image / 豆包 / Stability / Replicate",
                 font=F["body_b"], bg=C["paid"], fg="#e9d5ff"
                 ).pack(side="right", padx=20)

        bot = tk.Frame(self, bg=C["panel"]); bot.pack(fill="x", side="bottom")
        tk.Button(bot, text="💾 保存配置",
                  font=F["h2"], bg=C["ok"], fg="#0a1a0a",
                  bd=0, padx=24, pady=10, cursor="hand2",
                  command=self._save).pack(side="right", padx=20, pady=12)
        tk.Button(bot, text="关闭",
                  font=F["body"], bg=C["panel"], fg="#c0cfe0",
                  bd=0, padx=16, pady=10, cursor="hand2",
                  command=self._on_close).pack(side="right", pady=12)

        fo = tk.Frame(self, bg=C["bg"]); fo.pack(fill="both", expand=True)
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
            if self._closing: return
            try: cv.yview_scroll(int(-1*(e.delta/120)), "units")
            except tk.TclError: pass
        def _scroll_up(e):
            if self._closing: return
            try: cv.yview_scroll(-1, "units")
            except tk.TclError: pass
        def _scroll_dn(e):
            if self._closing: return
            try: cv.yview_scroll(1, "units")
            except tk.TclError: pass
        self.bind_all("<MouseWheel>", _scroll_win)
        self.bind_all("<Button-4>", _scroll_up)
        self.bind_all("<Button-5>", _scroll_dn)

        # ══ 1. OpenAI GPT-Image ══
        self._section(inner, "💡", "OpenAI GPT-Image",
                      "支持文生图+图生图  |  6 种模型可选  |  按量计费", PX)
        self._info_card(inner, [
            "• 模型族：GPT-Image 1 (旧版) / 1.5 / 2 / 2.5 Flare (快速) / 2.5 Sunburst (最强)",
            "• GPT-Image 2+ 支持任意分辨率（16 的倍数，长边 ≤3840）",
            "• quality=auto/low/medium/high  |  支持图生图",
            "• 首次使用可能需要在 OpenAI 后台完成 Organization Verification",
            "• 需要信用卡绑定，按用量计费（最低充值 $5）",
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
        tk.Label(opt1, text="模型:", font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self._gpt_image_name_to_id = {v: k for k, v in GPT_IMAGE_NAMES.items()}
        self.gpt_image_model_var = tk.StringVar(
            value=GPT_IMAGE_NAMES.get(self.cfg.get("gpt_image_model", GPT_IMAGE_DEFAULT), GPT_IMAGE_DEFAULT))
        ttk.Combobox(opt1, textvariable=self.gpt_image_model_var, width=30, state="readonly",
                     values=list(GPT_IMAGE_NAMES.values())).pack(side="left", padx=(6, 20))
        tk.Label(opt1, text="画质:", font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self.gpt_image_quality_var = tk.StringVar(value=self.cfg.get("gpt_image_quality", "auto"))
        ttk.Combobox(opt1, textvariable=self.gpt_image_quality_var, width=12, state="readonly",
                     values=["auto", "low", "medium", "high"]).pack(side="left", padx=(6, 20))

        btns1 = tk.Frame(inner, bg=C["bg"]); btns1.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns1, "🌐 OpenAI 注册 / 充值", "https://platform.openai.com/account/billing")
        self._link_btn(btns1, "🔑 生成 API Key", "https://platform.openai.com/api-keys")
        self._divider(inner)

        # ══ 2. Stability AI ══
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
        tk.Label(opt2, text="模型档位:", font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self.stab_model_var = tk.StringVar(value=self.cfg.get("stability_model", "core"))
        ttk.Combobox(opt2, textvariable=self.stab_model_var, width=18, state="readonly",
                     values=["core", "ultra", "sd3.5-large"]).pack(side="left", padx=(6, 0))
        tk.Label(opt2, text="  core=最快  ultra=最佳  sd3.5=文字强",
                 font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left", padx=8)
        btns2 = tk.Frame(inner, bg=C["bg"]); btns2.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns2, "🌐 注册 Stability AI", "https://platform.stability.ai/")
        self._link_btn(btns2, "🔑 获取 API Key", "https://platform.stability.ai/account/keys")
        self._divider(inner)

        # ══ 3. Replicate ══
        self._section(inner, "🔮", "Replicate  (FLUX / SD3)",
                      "多种 FLUX 模型可选  |  社区模型丰富  |  按量计费", PX)
        self._info_card(inner, [
            "• FLUX.1 系列：Pro / Dev / Schnell / Realism 多种风格",
            "• 支持图生图（FLUX.1 Kontext 系列）和 ControlNet",
            "• $0.04~0.08/张，新用户赠送 $5 Credits",
        ], PX)
        row3 = tk.Frame(inner, bg=C["bg"]); row3.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(row3, text="Replicate API Token:", font=F["btn"],
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef3 = tk.Frame(row3, bg=C["entry"]); ef3.pack(fill="x", pady=(4, 0))
        self.repl_var = tk.StringVar(value=self.cfg.get("replicate_key", ""))
        self.repl_ent = tk.Entry(ef3, textvariable=self.repl_var, show="*",
                                  bg=C["entry"], fg=C["text"], insertbackground="white",
                                  font=F["input"], bd=0, relief="flat")
        self.repl_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef3, self.repl_ent)
        opt3 = tk.Frame(inner, bg=C["bg"]); opt3.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(opt3, text="模型:", font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self.repl_model_var = tk.StringVar(value=self.cfg.get("replicate_model", "flux-1.1-pro"))
        ttk.Combobox(opt3, textvariable=self.repl_model_var, width=24, state="readonly",
                     values=["flux-1.1-pro", "flux-schnell", "flux-2-pro", "flux-kontext-pro"]
                     ).pack(side="left", padx=(6, 0))
        btns3 = tk.Frame(inner, bg=C["bg"]); btns3.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns3, "🌐 注册 Replicate", "https://replicate.com/")
        self._link_btn(btns3, "🔑 获取 API Token", "https://replicate.com/account/api-tokens")
        self._divider(inner)

        # ══ 4. 火山引擎豆包 (v3 新增) ══
        self._section(inner, "🫘", "火山引擎 豆包 Seedream",
                      "Seedream 4.0 文生图 (最新最强)  |  SeedEdit 3.0 图生图  |  按量计费", PX)
        self._info_card(inner, [
            "• Seedream 4.0：最新最强模型，支持 1024x1024 ~ 2048x2048 多种尺寸",
            "• Seedream 3.0：上一代模型，速度更快，成本更低",
            "• SeedEdit 3.0：图生图专用，自动在「图生图」模式下启用",
            "• guidance_scale 建议 2.0~3.0，支持 watermark 开关",
            "• 新用户赠送试用额度，按生成张数计费",
        ], PX)
        row4 = tk.Frame(inner, bg=C["bg"]); row4.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(row4, text="火山引擎 API Key:", font=F["btn"],
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef4 = tk.Frame(row4, bg=C["entry"]); ef4.pack(fill="x", pady=(4, 0))
        self.ark_var = tk.StringVar(value=self.cfg.get("volcengine_key", ""))
        self.ark_ent = tk.Entry(ef4, textvariable=self.ark_var, show="*",
                                 bg=C["entry"], fg=C["text"], insertbackground="white",
                                 font=F["input"], bd=0, relief="flat")
        self.ark_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef4, self.ark_ent)
        opt4 = tk.Frame(inner, bg=C["bg"]); opt4.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(opt4, text="模型:", font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self._ark_name_to_id = {v: k for k, v in ARK_IMAGE_NAMES.items()}
        self.ark_model_var = tk.StringVar(
            value=ARK_IMAGE_NAMES.get(self.cfg.get("ark_model", ARK_IMAGE_DEFAULT), ARK_IMAGE_DEFAULT))
        ttk.Combobox(opt4, textvariable=self.ark_model_var, width=28, state="readonly",
                     values=[ARK_IMAGE_NAMES.get(m, m) for m in ARK_IMAGE_MODELS]
                     ).pack(side="left", padx=(6, 0))
        tk.Label(opt4, text="  图生图自动用 SeedEdit",
                 font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left", padx=8)
        btns4 = tk.Frame(inner, bg=C["bg"]); btns4.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns4, "🌐 注册火山引擎", "https://www.volcengine.com/")
        self._link_btn(btns4, "🔑 获取 API Key",
                       "https://console.volcengine.com/ark/region:ark+cn-beijing/overview")
        self._divider(inner)

        # ══ 5. Black Forest Labs ══
        self._section(inner, "🌲", "Black Forest Labs (FLUX 官方)",
                      "FLUX.2 Pro / Flex  |  最高写实质量  |  按量计费", PX)
        self._info_card(inner, [
            "• FLUX.2 Pro：官方最强模型，支持 2K 分辨率",
            "• FLUX.2 Flex：灵活风格，适合创意设计",
            "• FLUX Kontext Pro：图生图专用（自动在图生图模式启用）",
        ], PX)
        row5 = tk.Frame(inner, bg=C["bg"]); row5.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(row5, text="BFL API Key:", font=F["btn"],
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        ef5 = tk.Frame(row5, bg=C["entry"]); ef5.pack(fill="x", pady=(4, 0))
        self.bfl_var = tk.StringVar(value=self.cfg.get("bfl_key", ""))
        self.bfl_ent = tk.Entry(ef5, textvariable=self.bfl_var, show="*",
                                 bg=C["entry"], fg=C["text"], insertbackground="white",
                                 font=F["input"], bd=0, relief="flat")
        self.bfl_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=10)
        self._eye_btn(ef5, self.bfl_ent)
        opt5 = tk.Frame(inner, bg=C["bg"]); opt5.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(opt5, text="模型:", font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self.bfl_model_var = tk.StringVar(value=self.cfg.get("bfl_model", BFL_TXT2IMG_DEFAULT))
        ttk.Combobox(opt5, textvariable=self.bfl_model_var, width=20, state="readonly",
                     values=BFL_TXT2IMG_MODELS).pack(side="left", padx=(6, 0))
        btns5 = tk.Frame(inner, bg=C["bg"]); btns5.pack(fill="x", padx=PX, pady=(8, 0))
        self._link_btn(btns5, "🌐 注册 BFL", "https://api.bfl.ai/")
        self._link_btn(btns5, "🔑 获取 API Key", "https://api.bfl.ai/keys")
        self._divider(inner)

    def _section(self, parent, icon, title, sub, px=24):
        f = tk.Frame(parent, bg=C["bg"])
        f.pack(fill="x", padx=px, pady=(16, 4))
        tk.Label(f, text=f"{icon} {title}", font=F["h2"],
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        tk.Label(f, text=sub, font=F["body"], bg=C["bg"], fg=C["warn"]).pack(anchor="w")

    def _info_card(self, parent, lines, px=24):
        card = tk.Frame(parent, bg="#1a2a4a",
                        highlightbackground="#2a3a5a", highlightthickness=1)
        card.pack(fill="x", padx=px, pady=(8, 0))
        for line in lines:
            tk.Label(card, text=line, font=F["body"],
                     bg="#1a2a4a", fg="#a0b8d0").pack(anchor="w", padx=16, pady=2)
        tk.Label(card, text="").pack(pady=2)

    def _divider(self, parent):
        tk.Frame(parent, bg="#2a3a5a", height=1).pack(fill="x", padx=24, pady=12)

    def _link_btn(self, parent, text, url):
        tk.Button(parent, text=text, font=F["body"],
                  bg=C["acc"], fg="white", bd=0, padx=12, pady=6, cursor="hand2",
                  command=lambda: webbrowser.open(url)).pack(side="left", padx=(0, 8), pady=4)

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
        eye = tk.Button(parent, text="👁", font=F["body"],
                        bg=C["entry"], fg=C["sub"], bd=0, padx=6, cursor="hand2",
                        command=_toggle)
        eye.pack(side="right", padx=4)
        self._gb(parent, entry)

    def _save(self):
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
        self.cfg["replicate_model"] = self.repl_model_var.get()
        self.cfg["volcengine_key"] = self.ark_var.get().strip()
        self.cfg["ark_model"] = ark_id
        self.cfg["bfl_key"] = self.bfl_var.get().strip()
        self.cfg["bfl_model"] = self.bfl_model_var.get()
        self.on_save(self.cfg)
        self._on_close()
