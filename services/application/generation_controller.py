"""
services/application/generation_controller.py — Generation orchestrator
─────────────────────────────────────────────────────────────────────────
Extracts single-image and variant generation flow from App._gen()
to slim down the main window class.
"""
from __future__ import annotations

import random
import threading
from tkinter import messagebox

from config.i18n import _
from data.repository import add_entry
from services.image_service import generate_image, save_image_file
from services.smart_router import get_provider_order
from services.translation import has_chinese, translate_zh_to_en




class GenerationController:
    """Orchestrates single-image and variant generation workflows."""

    def __init__(self, app) -> None:
        self.app = app
        self.root = app.root
        self.cfg = app.cfg

    def generate(self, event=None) -> None:
        """Start single-image generation."""
        content = self.app.content
        prompt = content.pt.get("1.0", "end").strip()
        MAX_PROMPT_CHARS = 2000

        if len(prompt) > MAX_PROMPT_CHARS:
            self.app._st(_("status_prompt_too_long", cur=len(prompt), max=MAX_PROMPT_CHARS), "hl")
            return
        if not prompt:
            messagebox.showwarning("提示", "请先输入描述文字！")
            return

        psel = content.pv.get()
        if psel.startswith("───"):
            messagebox.showinfo("提示", "请选择一个具体接口，而非分隔线。")
            return

        # Check if provider needs API key
        if not self._check_provider_key(psel):
            return

        sz = content.szv.get()
        w, h = [int(x) for x in sz.replace("×", "x").split("x")]

        if psel == _("provider_auto"):
            if not self.cfg.get("sf_key", "").strip() and not self.cfg.get("hf_token", "").strip():
                if messagebox.askyesno("建议配置",
                    "尚未配置任何免费 API Key。\n建议配置「硅基流动」。\n是否现在配置？"):
                    self.app._open_wizard()
                    return
            porder = get_provider_order(prompt, self.cfg)
        else:
            porder = [psel]

        self.app._batch_total = 1
        self.app._batch_done = 0
        self.app._batch_params = {"prompt": prompt, "translated": "", "w": w, "h": h,
                                  "porder": porder, "cfg": self.cfg}

        # Update UI state
        content.gb.config(state="disabled", text=_("btn_generating"))
        content.pb.pack(fill="x", padx=14, pady=(0, 4))
        content.pb.start(10)
        self.app._st(_("status_translating"), "warn")
        content._prev_cv.delete("prev")
        content._prev_item = None
        content._prev_cv.update_idletasks()
        cw = content._prev_cv.winfo_width() or 600
        ch = content._prev_cv.winfo_height() or 400
        content._prev_cv.itemconfig(content._prev_ph, text=_("status_generating"))
        content._prev_cv.coords(content._prev_ph, cw // 2, ch // 2)
        self.app._log(f"── 开始: {prompt[:60]} ──")
        content._nb.select(0)

        # Start generation thread
        threading.Thread(target=self._run_generation, args=(prompt, w, h, porder), daemon=True).start()

    def _check_provider_key(self, psel: str) -> bool:
        """Check if selected provider has required API key configured."""
        checks = {
            "💎 OpenAI GPT-Image": ("openai_key", self.app._open_paid_wizard,
                                    "使用 OpenAI GPT-Image 需要填写 API Key。\n是否现在配置？"),
            "💎 Stability AI": ("stability_key", self.app._open_paid_wizard,
                                "使用 Stability AI 需要填写 API Key。\n是否现在配置？"),
            "💎 Replicate FLUX": ("replicate_key", self.app._open_paid_wizard,
                                "使用 Replicate 需要填写 API Token。\n是否现在配置？"),
            "💎 Nano Banana Pro (Gemini 3 Pro Image)": ("gemini_key", self.app._open_wizard,
                                "使用 Nano Banana Pro 需要填写 Google Gemini API Key。\n是否现在配置？"),
            "💎 MiniMax image-01": ("minimax_key", self.app._open_paid_wizard,
                                "使用 MiniMax image-01 需要填写 API Key。\n是否现在配置？"),
            "💎 Black Forest Labs FLUX": ("bfl_key", self.app._open_paid_wizard,
                                "使用 Black Forest Labs 官方 API 需要填写 API Key。\n是否现在配置？"),
            "硅基流动 SiliconFlow (★推荐)": ("sf_key", self.app._open_wizard,
                                "使用硅基流动需要填写 API Key。\n是否现在配置？"),
            "HuggingFace (备用)": ("hf_token", self.app._open_wizard,
                                "使用 HuggingFace 需要填写 Token。\n是否现在配置？"),
        }

        if psel not in checks:
            return True

        key_name, wizard_fn, msg = checks[psel]
        if not self.cfg.get(key_name, "").strip():
            if messagebox.askyesno("需要配置", msg):
                wizard_fn()
            return False
        return True

    def _run_generation(self, prompt: str, w: int, h: int, porder: list) -> None:
        """Background generation worker."""
        seed = random.randint(0, 2_147_483_647)
        translated = prompt

        if has_chinese(prompt):
            self.root.after(0, lambda: self.app._st(_("status_translating"), "warn"))
            translated = translate_zh_to_en(prompt, log_cb=self.app._log)
            self.app._batch_params["translated"] = translated

        try:
            # Handle img2img mode
            content = self.app.content
            _gen_mode = getattr(content, '_gen_mode', 't2i')
            if _gen_mode == 'i2i':
                ref_image = getattr(content, '_ref_image', None)
                strength = getattr(content, '_ref_strength', None)
                strength = strength.get() if strength is not None else 0.6
                if ref_image is None:
                    self.root.after(0, lambda: self.app._err("图生图模式需要先选取参考图"))
                    return
            else:
                ref_image = None
                strength = 0.6

            data, used = generate_image(
                translated, w, h, seed, self.cfg,
                provider_order=porder,
                status_cb=self._make_status_cb(len(porder)),
                log_cb=self.app._log,
                ref_image=ref_image,
                strength=strength)

            path = save_image_file(data, prompt,
                                   seed=seed, provider=used,
                                   translated=translated,
                                   size=f"{w}x{h}")
            add_entry(prompt, translated, path, used)
            self.root.after(0, lambda: self.app._ok(data, path, used))
        except Exception as ex:
            self.root.after(0, lambda e=str(ex): self.app._err(e))

    def _make_status_cb(self, total: int):
        """Create a status callback for progress updates."""
        cnt = [0]

        def cb(msg: str) -> None:
            cnt[0] += 1
            self.root.after(0, lambda: self.app._st(f"[{cnt[0]}/{total}] {msg}", "warn"))

        return cb

    def generate_variants(self) -> None:
        """Start variant batch generation."""
        content = self.app.content

        if getattr(content, "_gen_mode", "t2i") == "i2i":
            messagebox.showwarning(
                "提示", "批量生成暂不支持图生图模式\n请切换到「📝 文生图」后再批量生成")
            return

        prompt = content.pt.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning("提示", "请先输入描述文字！")
            return

        psel = content.pv.get()
        if psel.startswith("───"):
            messagebox.showinfo("提示", "请选择一个具体接口，而非分隔线。")
            return

        n = max(1, min(6, content.variant_n_var.get()))
        sz = content.szv.get()
        w, h = [int(x) for x in sz.replace("×", "x").split("x")]

        if psel == _("provider_auto"):
            porder = get_provider_order(prompt, self.cfg)
        else:
            porder = [psel]

        self.app._batch_params = {"prompt": prompt, "translated": "", "w": w, "h": h,
                                  "porder": porder, "cfg": self.cfg}
        content._nb.select(1)

        content._batch_panel.start_batch(
            n=n, params=self.app._batch_params,
            translate_fn=lambda p, cfg, log_cb: translate_zh_to_en(p, log_cb=log_cb),
            generate_fn=generate_image, save_fn=save_image_file,
            log_fn=self.app._log, on_keep_fn=self.app._on_variant_kept)
        self.app._st(_("status_batch_start", n=n), "warn")
        self.app._log(f"🎲 变体生成 n={n} size={sz}")


