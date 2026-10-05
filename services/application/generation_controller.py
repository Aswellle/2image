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
from services.generation.cancellation import CancellationToken
from services.generation.errors import DeadlineExceeded, GenerationCancelled
from services.image_service import generate_image, save_image_file
from services.generation.router import get_provider_order
from services.translation import has_chinese, translate_zh_to_en




class GenerationController:
    """Orchestrates single-image and variant generation workflows."""

    def __init__(self, app) -> None:
        self.app = app
        self.root = app.root
        self._cancel_token: CancellationToken | None = None

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

        # Check if provider needs API key + budget guard（单图/变体共用）
        if not self._precheck_provider(psel):
            return

        sz = content.szv.get()
        w, h = [int(x) for x in sz.replace("×", "x").split("x")]

        if psel == _("provider_auto"):
            if not self.app.cfg.get("sf_key", "").strip() and not self.app.cfg.get("hf_token", "").strip():
                if messagebox.askyesno("建议配置",
                    "尚未配置任何免费 API Key。\n建议配置「硅基流动」。\n是否现在配置？"):
                    self.app._open_wizard()
                    return
            porder = get_provider_order(prompt, self.app.cfg)
        else:
            porder = [psel]

        self.app._batch_total = 1
        self.app._batch_done = 0
        self.app._batch_params = {"prompt": prompt, "translated": "", "w": w, "h": h,
                                  "porder": porder, "cfg": self.app.cfg}

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

        # Create cancellation token for this generation job
        self._cancel_token = CancellationToken()

        # Start generation thread
        threading.Thread(
            target=self._run_generation,
            args=(prompt, w, h, porder, self._cancel_token),
            daemon=True,
        ).start()

    def cancel_generation(self) -> None:
        """Cancel the currently running generation, if any."""
        if self._cancel_token is not None:
            self._cancel_token.cancel()

    def _precheck_provider(self, psel: str) -> bool:
        """生成前置检查：Key 配置 + 付费日预算（单图与变体共用）。"""
        if not self._check_provider_key(psel):
            return False
        # PAY-001: 显式选择付费接口时，日预算用尽则阻断（免费接口不受限）
        from services.providers import resolve_provider_id
        from services.generation import budget
        cfg = self.app.cfg
        pid = resolve_provider_id(psel)
        if pid and budget.is_paid(pid) and budget.over_budget(cfg):
            limit = budget.daily_budget(cfg)
            messagebox.showwarning(
                "付费预算已用尽",
                f"今日付费估算消耗已达 ${budget.spent_today(cfg):.2f}"
                f"（上限 ${limit:.2f}）。\n"
                f"如需继续使用 {psel}，请调高「paid_daily_budget_usd」设置。")
            return False
        return True

    def _check_provider_key(self, psel: str) -> bool:
        """Check if selected provider has required API key configured.

        Registry-driven（ROUTE-001）: resolve display name → stable id →
        config key，新供应商自动纳入检查，无需在此维护硬编码名单。
        """
        from services.providers import (
            ALL_PROVIDERS, FREE_PROVIDERS, MULTI_KEY_PROVIDERS,
            OPTIONAL_KEY_PROVIDERS, PROVIDER_KEYS, resolve_provider_id,
        )

        pid = resolve_provider_id(psel)
        if pid is None or pid not in ALL_PROVIDERS:
            return True  # 自动模式 / 未知接口 — 交给运行时处理

        # 多键接口（如 Cloudflare 双凭证）：要求全部凭证就绪
        required_keys = MULTI_KEY_PROVIDERS.get(pid)
        if required_keys:
            if all(str(self.app.cfg.get(k, "") or "").strip() for k in required_keys):
                return True
            is_paid = pid not in FREE_PROVIDERS
            wizard_fn = self.app._open_paid_wizard if is_paid else self.app._open_wizard
            if messagebox.askyesno(
                    "需要配置",
                    f"使用 {psel} 需要填写全部凭证（{'、'.join(required_keys)}）。\n是否现在配置？"):
                wizard_fn()
            return False

        key_name = PROVIDER_KEYS.get(pid)
        if not key_name or pid in OPTIONAL_KEY_PROVIDERS:
            return True
        if str(self.app.cfg.get(key_name, "") or "").strip():
            return True

        # 缺 Key → 引导配置（付费接口走付费向导）
        is_paid = pid not in FREE_PROVIDERS
        wizard_fn = self.app._open_paid_wizard if is_paid else self.app._open_wizard
        msg = (f"使用 {psel} 需要填写 API Key。\n是否现在配置？")
        if messagebox.askyesno("需要配置", msg):
            wizard_fn()
        return False
    def _run_generation(
        self,
        prompt: str,
        w: int,
        h: int,
        porder: list,
        token: CancellationToken | None = None,
    ) -> None:
        """Background generation worker."""
        seed = random.randint(0, 2_147_483_647)
        translated = prompt

        try:
            # 翻译也纳入取消保护：限流等待期间取消会抛 GenerationCancelled，
            # 若在 try 之外会逃逸工作线程导致界面永久停留在“生成中”
            if has_chinese(prompt):
                self.root.after(0, lambda: self.app._st(_("status_translating"), "warn"))
                translated = translate_zh_to_en(prompt, log_cb=self.app._log, token=token)
                self.app._batch_params["translated"] = translated

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
                translated, w, h, seed, self.app.cfg,
                provider_order=porder,
                status_cb=self._make_status_cb(len(porder)),
                log_cb=self.app._log,
                ref_image=ref_image,
                strength=strength,
                token=token,
            )

            path = save_image_file(data, prompt,
                                   seed=seed, provider=used,
                                   translated=translated,
                                   size=f"{w}x{h}")
            add_entry(prompt, translated, path, used)
            self.root.after(0, lambda: self.app._ok(data, path, used))
        except GenerationCancelled:
            self.root.after(0, lambda: self.app._st(_("status_cancelled"), "warn"))
        except DeadlineExceeded as ex:
            err_msg = str(ex)
            self.root.after(0, lambda: self.app._err(f"⏰ 生成超时: {err_msg}"))
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

        # 变体与单图共用 Key + 预算前置检查，防止批量路径绕过付费阻断
        if not self._precheck_provider(psel):
            return

        n = max(1, min(6, content.variant_n_var.get()))
        sz = content.szv.get()
        w, h = [int(x) for x in sz.replace("×", "x").split("x")]

        if psel == _("provider_auto"):
            porder = get_provider_order(prompt, self.app.cfg)
        else:
            porder = [psel]

        self.app._batch_params = {"prompt": prompt, "translated": "", "w": w, "h": h,
                                  "porder": porder, "cfg": self.app.cfg}
        content._nb.select(1)

        content._batch_panel.start_batch(
            n=n, params=self.app._batch_params,
            translate_fn=lambda p, cfg, log_cb: translate_zh_to_en(p, log_cb=log_cb),
            generate_fn=generate_image, save_fn=save_image_file,
            log_fn=self.app._log, on_keep_fn=self.app._on_variant_kept)
        self.app._st(_("status_batch_start", n=n), "warn")
        self.app._log(f"🎲 变体生成 n={n} size={sz}")


