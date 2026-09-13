"""
ui/app.py — 主应用窗口  v5.2
──────────────────────────────
在 v5 基础上重构：
  · 侧栏控件提取至 HistorySidebar (ui/sidebar.py)
  · 右侧主区控件提取至 MainContent (ui/main_content.py)
  · App 保留协调/编排逻辑
"""
import io
import html
import os
import shutil
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk
import webbrowser
import random

from PIL import Image, ImageTk

from config.settings import load_config, save_config
from config.fonts import F
from data.repository import (add_entry, clear_all_entries, count_entries,
                             delete_entry, get_all_entries, get_all_tags,
                             get_entry, get_stats, get_year_heatmap,
                             get_available_years, get_year_stats,
                             rename_entry, toggle_favorite, update_tags)
from services.image_service import generate_image, save_image_file
from services.logger import log_to_file
from services.translation import has_chinese, translate_zh_to_en
from services.providers import FREE_PROVIDERS, PAID_PROVIDERS, PROVIDER_KEYS
from services.application import GenerationController, MenuController, SettingsController

from ui.viewer import ImageViewerWindow
from ui.wizard_free import ConfigWizard
from ui.wizard_paid import PaidWizard
from ui.prompt_wizard import PromptWizard
from ui.phrase_panel import PhrasePanel
from ui.sidebar import HistorySidebar
from ui.main_content import MainContent

from config.theme import DARK_THEME as C, TAG_PALETTE, tag_color, init_theme
from config.i18n import _, init_language


SIDEBAR_DEF  = 360
SIDEBAR_MIN  = 240
SIDEBAR_MAX  = 600
SASH_W       = 6


# ══════════════════════════════════════════════════════════════
class App:
    """主窗口控制器 v5.2。侧栏/主区控件已提取至独立模块。"""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(_("app_title"))
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        window_w = min(1380, int(screen_w * 0.98))
        window_h = min(920, int(screen_h * 0.95))
        root.geometry(f"{window_w}x{window_h}")
        root.configure(bg=C["bg"])
        root.minsize(min(1000, window_w), min(720, window_h))
        if screen_w < 1400 or screen_h < 800:
            root.state("zoomed")

        self.cfg = load_config()
        init_theme(self.cfg)
        init_language(self.cfg)

        # Initialize controllers
        self.menu_controller = MenuController(self)
        self.settings_controller = SettingsController(self)
        self.gen_controller = GenerationController(self)

        self.cur_path = None
        self.sel_id = None
        self._viewer_win = None
        self._prompt_wizard = None
        self._phrase_panel = None
        self._cur_bytes = None

        # Sidebar width
        self._sidebar_w = SIDEBAR_DEF
        self.MAX_NICK_LEN = MAX_NICK_LEN
        self._sash_drag_x = None
        self._sash_drag_w = None

        # Batch state
        self._batch_total = 0
        self._batch_done = 0
        self._batch_params = None

        # Debounce jobs
        self._load_entry_job = None
        self._resize_timer = None

        self.menu_controller.build()
        self._build()
        self._bind_hotkeys()
        self.root.after(50, lambda: self.sidebar._refresh_hist())
        self._update_status_bar_tokens()

        if self.cfg.get("show_wizard_on_start", True):
            root.after(300, self._open_wizard)


        # 导致 thumb_lbl 字符单位宽度把 right 挤成 0px → 标题/信息不可见。
        self.root.after(50, lambda: self.sidebar._refresh_hist())
        self._update_status_bar_tokens()

        if self.cfg.get("show_wizard_on_start", True):
            root.after(300, self._open_wizard)

    # ── 转发属性（供 HistorySidebar / MainContent 通过 self.app.xxx 访问）──

    @property
    def pt(self):
        return self.content.pt

    @property
    def pv(self):
        return self.content.pv

    @property
    def szv(self):
        return self.content.szv

    @property
    def gb(self):
        return self.content.gb

    @property
    def stv(self):
        return self.content.stv

    @property
    def stl(self):
        return self.content.stl

    @property
    def _nb(self):
        return self.content._nb

    @property
    def _queue_panel(self):
        return self.content._queue_panel

    @property
    def _tag_filter(self):
        return self.sidebar._tag_filter

    @_tag_filter.setter
    def _tag_filter(self, value):
        self.sidebar._tag_filter = value

    @property
    def _fav_only(self):
        return self.sidebar._fav_only

    @_fav_only.setter
    def _fav_only(self, value):
        self.sidebar._fav_only = value

    # ── 薄委托方法（供侧栏/主区回调使用）─────────────────────────

    def _refresh_hist(self, load_all: bool = False):
        self.sidebar._refresh_hist(load_all)

    def _refresh_tag_stats(self):
        self.content._refresh_tag_stats()

    def _refresh_tag_chips(self):
        self.sidebar._refresh_tag_chips()

    def _on_tag_filter_changed(self, tag: str):
        self.sidebar._set_tag_filter(tag)

    def _set_cmp_from_entry(self, e: dict):
        self.content._set_cmp_from_entry(e)
    # ── 意图方法（增量改进：提供语义化入口，保留 @property 兼容）──

    def _get_prompt_text(self) -> str:
        """Intent: read current prompt from input."""
        return self.content.pt.get("1.0", "end").strip()

    def _set_prompt_text(self, text: str) -> None:
        """Intent: write prompt to input."""
        self.content.pt.delete("1.0", "end")
        self.content.pt.insert("1.0", text)

    def _queue_current_prompt(self) -> None:
        """Intent: add current prompt to queue."""
        self._switch_to_queue_tab()
        self.content._queue_panel._add_from_app()

    @staticmethod
    def _display_title(e):
        nick = e.get("nickname") or ""
        if nick:
            return nick
        raw = e.get("prompt", "")
        return raw[:MAX_NICK_LEN] + ("…" if len(raw) > MAX_NICK_LEN else "")

    # ══════════════════════════════════════════════════════════
    #   快捷键
    # ══════════════════════════════════════════════════════════
    def _bind_hotkeys(self):
        r = self.root
        r.bind("<Control-Return>",   lambda e: (self._gen(), "break")[1])
        r.bind("<Control-KP_Enter>", lambda e: (self._gen(), "break")[1])
        r.bind("<Control-s>",        lambda e: self._save())
        r.bind("<Control-S>",        lambda e: self._save())
        r.bind("<Control-e>",        lambda e: self._export())
        r.bind("<Control-E>",        lambda e: self._export())
        r.bind("<Control-o>",        lambda e: self._open_viewer())
        r.bind("<Control-O>",        lambda e: self._open_viewer())
        r.bind("<Control-r>",        lambda e: self._gen())

    # ── Controllers delegate menu/settings/build ─────────────────────
    def _build_menu(self) -> None:
        """Delegated to MenuController."""
        self.menu_controller.build()


    # ══════════════════════════════════════════════════════════
    #   主框架
    # ══════════════════════════════════════════════════════════
    def _build(self):
        bar = tk.Frame(self.root, bg=C["acc"], height=50)
        bar.pack(fill="x"); bar.pack_propagate(False)
        tk.Label(bar, text=_("app_title"),
                 font=F["title"], bg=C["acc"], fg="white"
                 ).pack(side="left", padx=16)
        # 付费接口数量
        self._top_paid_lbl = tk.Label(bar, text=_("status_paid_count", n=0, total=len(PAID_PROVIDERS)),
                                       font=F["body"], bg=C["acc"], fg=C["sub"])
        self._top_paid_lbl.pack(side="right", padx=(0, 16))
        # 分隔线
        tk.Frame(bar, bg="#2a4a8a", width=1).pack(side="right", fill="y", pady=10)
        # 免费接口数量
        self._top_free_lbl = tk.Label(bar, text=_("status_free_count", n=0, total=len(FREE_PROVIDERS)),
                                       font=F["body"], bg=C["acc"], fg=C["warn"])
        self._top_free_lbl.pack(side="right", padx=(4, 8))
        # 接口配置按钮（原位于主内容区接口状态栏，移至顶栏节省垂直空间）
        tk.Frame(bar, bg="#2a4a8a", width=1).pack(side="right", fill="y", pady=10)
        tk.Button(bar, text=_("btn_paid_config"), font=F["small_b"],
                  bg="#7c3aed", fg="white", bd=0, padx=10, pady=4, cursor="hand2",
                  command=self._open_paid_wizard).pack(side="right", padx=(0, 4), pady=8)
        tk.Button(bar, text=_("btn_free_config"), font=F["small_b"],
                  bg=C["hl"], fg="white", bd=0, padx=10, pady=4, cursor="hand2",
                  command=self._open_wizard).pack(side="right", padx=(0, 4), pady=8)

        self._body = tk.Frame(self.root, bg=C["bg"])
        self._body.pack(fill="both", expand=True)

        self._L = tk.Frame(self._body, bg=C["panel"])
        self.sidebar = HistorySidebar(self._L, self)

        self._sash = tk.Frame(self._body, bg=C["sash"],
                              cursor="sb_h_double_arrow", width=SASH_W)
        self._sash.bind("<Enter>",           self._sash_enter)
        self._sash.bind("<Leave>",           self._sash_leave)
        self._sash.bind("<ButtonPress-1>",   self._sash_start)
        self._sash.bind("<B1-Motion>",       self._sash_move)
        self._sash.bind("<ButtonRelease-1>", self._sash_end)

        self._R = tk.Frame(self._body, bg=C["bg"])
        self.content = MainContent(self._R, self)

        self._body.bind("<Configure>", self._on_body_resize)
        self._place_panels()

    def _place_panels(self):
        bw = self._body.winfo_width();  bh = self._body.winfo_height()
        if bw < 10: bw = 1380
        if bh < 10: bh = 870
        sw = self._sidebar_w
        self._L.place(x=0,          y=0, width=sw,            height=bh)
        self._sash.place(x=sw,      y=0, width=SASH_W,        height=bh)
        self._R.place(x=sw+SASH_W,  y=0, width=bw-sw-SASH_W, height=bh)
        pass  # deferred to _finish_resize

    def _on_body_resize(self, event):
        self._place_panels()  # immediate layout only
        if self._resize_timer:
            self.root.after_cancel(self._resize_timer)
        self._resize_timer = self.root.after(100, self._finish_resize)

    def _finish_resize(self):
        self._resize_timer = None
        self.sidebar._update_card_wraplength(self._sidebar_w)
    def _sash_enter(self, e): self._sash.config(bg=C["sash_hl"])
    def _sash_leave(self, e):
        if self._sash_drag_x is None: self._sash.config(bg=C["sash"])
    def _sash_start(self, e):
        self._sash_drag_x = e.x_root
        self._sash_drag_w = self._sidebar_w
    def _sash_move(self, e):
        if self._sash_drag_x is None: return
        self._sidebar_w = max(SIDEBAR_MIN, min(SIDEBAR_MAX,
            self._sash_drag_w + e.x_root - self._sash_drag_x))
        # 拖动期间只做轻量布局（跳过卡片 wraplength 遍历），保证丝滑
        bw = self._body.winfo_width()
        bh = self._body.winfo_height()
        if bw < 10: bw = 1380
        if bh < 10: bh = 870
        sw = self._sidebar_w
        self._L.place(x=0,         y=0, width=sw,            height=bh)
        self._sash.place(x=sw,     y=0, width=SASH_W,        height=bh)
        self._R.place(x=sw+SASH_W, y=0, width=bw-sw-SASH_W, height=bh)
    def _sash_end(self, e):
        self._sash_drag_x = None; self._sash_drag_w = None
        self._sash.config(bg=C["sash"])
        # 松手后补全 wraplength 更新
        self.sidebar._update_card_wraplength(self._sidebar_w)

    # ══════════════════════════════════════════════════════════
    #   加载历史条目 ── 根治版 v2
    #   彻底移除 _refresh_hist 调用，改用轻量 _update_sidebar_selection。
    #   原理：点击卡片只是"选中"，不涉及数据变化，无需重建整个列表。
    #   消灭了 viewer 的 update_idletasks() 与列表重建的竞态，
    #   从根本上杜绝"标题/信息消失"问题。
    # ══════════════════════════════════════════════════════════
    def _load_entry(self, e: dict):
        # ── 1. 立即更新界面状态（全部非破坏性操作）──────────────
        self.sel_id   = e["id"]
        self.cur_path = e.get("image_path", "")
        self.content.pt.delete("1.0", "end")
        self.content.pt.insert("1.0", e["prompt"])
        self.content._show_file(self.cur_path)
        self._st(_("status_history_entry", ts=e['timestamp'], prov=e.get('provider','')), "ok")

        # ── 2. 更新侧栏选中高亮（仅改两张卡片颜色，不重建任何 widget）
        self.sidebar._update_sidebar_selection(e["id"])

        # ── 3. 若查看器已打开，异步加载新图片（与选中高亮完全解耦）
        if self._viewer_win is not None and self.cur_path:
            snap = self.cur_path
            def _update_viewer():
                if self._viewer_win is not None:
                    try: self._viewer_win.load_file(snap)
                    except tk.TclError: self._viewer_win = None
            # after(50)：给 Tkinter 足够时间完成本次点击事件的所有内部处理
            self.root.after(50, _update_viewer)

    # ══════════════════════════════════════════════════════════
    #   查看器
    # ══════════════════════════════════════════════════════════
    def _open_viewer(self):
        if self._cur_bytes is None and self.cur_path is None:
            messagebox.showinfo("提示", "请先生成或选择一张图片"); return
        if self._viewer_win is not None:
            try: self._viewer_win.lift(); self._viewer_win.focus_force(); return
            except tk.TclError: self._viewer_win = None
        self._viewer_win = ImageViewerWindow(self)
        if self._cur_bytes:
            self._viewer_win.load_bytes(self._cur_bytes, self.cur_path or "")
        elif self.cur_path and os.path.exists(self.cur_path):
            self._viewer_win.load_file(self.cur_path)

    def _push_to_viewer(self, data: bytes, path: str):
        if self._viewer_win is not None:
            try: self._viewer_win.load_bytes(data, path); self._viewer_win.lift(); return
            except tk.TclError: self._viewer_win = None
        self._viewer_win = ImageViewerWindow(self)
        self._viewer_win.load_bytes(data, path)

    # ══════════════════════════════════════════════════════════
    #   词库 / 变体 / 助手
    # ══════════════════════════════════════════════════════════
    def _open_phrase_panel(self):
        if self._phrase_panel is not None:
            try: self._phrase_panel.lift(); self._phrase_panel.focus_force(); return
            except tk.TclError: self._phrase_panel = None
        self._phrase_panel = PhrasePanel(self)

    def _switch_to_variant_tab(self):
        self.content._nb.select(1)

    def _switch_to_queue_tab(self):
        self.content._nb.select(2)

    def _gen_variants(self) -> None:
        """Delegated to GenerationController."""
        self.gen_controller.generate_variants()



    def _on_variant_kept(self, entry: dict):
        """
        保留变体后刷新历史列表并自动预览。

        修复：
          · 接收 batch_panel 传来的完整 entry dict（含 id / image_path）。
          · 刷新历史列表后，自动选中并展示刚保留的图片，
            用户无需再次点击历史条目即可看到预览。
        """
        if self._load_entry_job is not None:
            try: self.root.after_cancel(self._load_entry_job)
            except Exception: pass
            self._load_entry_job = None

        def _do():
            self.sidebar._refresh_hist()
            self.sidebar._refresh_tag_chips()
            self.content._refresh_tag_stats()
            self._st("✅ 已保留变体到历史记录", "ok")

            # ── 自动预览刚保留的图片 ──────────────────────────────
            if not entry:
                return
            img_path = entry.get("image_path", "")
            if not img_path:
                return
            import os as _os
            if not _os.path.exists(img_path):
                self._log(f"⚠ 保留后找不到图片文件: {img_path}")
                return
            try:
                with open(img_path, "rb") as _fh:
                    data = _fh.read()
            except Exception as e:
                self._log(f"⚠ 读取保留图片失败: {e}")
                return
            # 更新主界面当前图片状态
            self.cur_path    = img_path
            self._cur_bytes  = data
            self.sel_id      = entry.get("id")
            self.content._set_preview(data)
            # 高亮侧栏选中项（refresh 已建好 card，直接更新颜色即可）
            if self.sel_id:
                self.sidebar._update_sidebar_selection(self.sel_id)

        self.root.after(120, _do)

    def _open_prompt_wizard(self):
        if self._prompt_wizard is not None:
            try: self._prompt_wizard.lift(); self._prompt_wizard.focus_force(); return
            except tk.TclError: self._prompt_wizard = None
        self._prompt_wizard = PromptWizard(self)

    # ══════════════════════════════════════════════════════════
    #   配置向导
    # ══════════════════════════════════════════════════════════
    def _open_wizard(self):
        def on_save(new_cfg):
            self.cfg = new_cfg; self._update_status_bar_tokens()
        ConfigWizard(self.root, self.cfg, on_save)

    def _open_paid_wizard(self):
        def on_save(new_cfg):
            self.cfg = new_cfg; self._update_status_bar_tokens()
        PaidWizard(self.root, self.cfg, on_save)

    # ══════════════════════════════════════════════════════════
    #   ⚙ 设置
    # ══════════════════════════════════════════════════════════
    #   Settings & shortcuts (delegated to SettingsController) ───
    # ══════════════════════════════════════════════════════════
    def _show_shortcuts(self) -> None:
        self.settings_controller.show_shortcuts()

    def _open_app_settings(self) -> None:
        self.settings_controller.show_app_settings()



    # ══════════════════════════════════════════════════════════
    #   📊 统计看板  v2  —  GitHub 风格全年热力图 + 完整重设计
    # ══════════════════════════════════════════════════════════
    def _show_stats(self):
        from ui.stats_dashboard import StatsDashboard
        StatsDashboard(self.root, self)
    # ══════════════════════════════════════════════════════════
    #   接口状态栏
    # ══════════════════════════════════════════════════════════
    def _update_status_bar_tokens(self):
        """根据当前自动发现的 Provider 注册表实时统计顶栏可用接口数。

        不再维护易过期的手写 key 列表：新增/移除 provider 或变更 category 后，
        PROVIDER_KEYS 与 FREE_PROVIDERS/PAID_PROVIDERS 会自动让数量同步更新。
        config_key 为 None 的接口（如 StableHorde 匿名模式）被视为始终可用；
        Pollinations 则额外遵从 pollinations_enabled 开关。
        """
        cfg = self.cfg

        def _is_available(name: str) -> bool:
            if name == "Pollinations.AI (免费·无需Key)":
                return bool(cfg.get("pollinations_enabled", True))
            if name == "StableHorde (兜底)":
                return True  # 空 Key 走匿名低优先级模式，仍可正常生成
            if name == "Cloudflare AI (免费1万次/天)":
                return bool(cfg.get("cf_account_id", "").strip()
                            and cfg.get("cf_api_token", "").strip())
            key_name = PROVIDER_KEYS.get(name)
            return key_name is None or bool(cfg.get(key_name, "").strip())

        free_count = sum(_is_available(name) for name in FREE_PROVIDERS)
        paid_count = sum(_is_available(name) for name in PAID_PROVIDERS)

        # ── 顶栏计数标签 ──────────────────────────────────────────
        self._top_free_lbl.config(
            text=_("status_free_count", n=free_count, total=len(FREE_PROVIDERS)),
            fg=C["ok"] if free_count else C["warn"],
        )
        self._top_paid_lbl.config(
            text=_("status_paid_count", n=paid_count, total=len(PAID_PROVIDERS)),
            fg="#a78bfa" if paid_count else C["sub"],
        )


    # ══════════════════════════════════════════════════════════
    #   日志
    # ══════════════════════════════════════════════════════════
    def _log(self, msg: str):
        log_to_file(msg)
        def _a():
            safe_msg = msg.replace('\n', '\\n').replace('\r', '\\r')
            self.content.logt.configure(state="normal")
            self.content.logt.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {safe_msg}\n")
            self.content.logt.see("end"); self.content.logt.configure(state="disabled")
        self.root.after(0, _a)

    def _clr_log(self):
        self.content.logt.configure(state="normal")
        self.content.logt.delete("1.0", "end")
        self.content.logt.configure(state="disabled")

    # ══════════════════════════════════════════════════════════
    #   单张图片生成 (delegated to GenerationController) ─────────
    # ══════════════════════════════════════════════════════════
    def _gen(self, event=None) -> None:
        self.gen_controller.generate(event)


    def _err(self, err: str) -> None:
        """Handle generation error (kept in App for UI state access)."""
        self.content.gb.config(state="normal", text=_("btn_generate"))
        self.content.pb.stop()
        self.content.pb.pack_forget()
        self._batch_params = None

        friendly = err
        if "429" in err or "rate limit" in err.lower():
            friendly = _("err_rate_limit")
        elif "401" in err or "403" in err:
            friendly = _("err_api_key")
        elif "402" in err or "额度" in err or "balance" in err.lower():
            friendly = _("err_balance")
        elif "timeout" in err.lower() or "timed out" in err.lower():
            friendly = _("err_timeout")
        elif "ConnectionError" in err or "connection" in err.lower():
            friendly = _("err_connection")

        self._st(f"❌ {friendly}", "hl")
        self._log(f"✗ {err}")
        cw = self.content._prev_cv.winfo_width() or 600
        ch = self.content._prev_cv.winfo_height() or 400
        self.content._prev_cv.itemconfig(self.content._prev_ph, text=_("preview_error"))
        self.content._prev_cv.coords(self.content._prev_ph, cw // 2, ch // 2)
        if any(k in err for k in ["API Key", "Key", "Token", "token", "401", "402", "403", "额度"]):
            self.root.after(100, lambda: messagebox.showwarning(
                "需要配置 API Key",
                f"{err[:200]}\n\n点击「🆓 免费配置」配置硅基流动 API Key。"))


        if not d: return
        out = os.path.join(d, f"AI生图_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(out, exist_ok=True)

        def _copy_worker():
            for i, e in enumerate(items, 1):
                p = e.get("image_path", "")
                if p and os.path.exists(p):
                    shutil.copy2(p, os.path.join(out, f"{i:03d}_{os.path.basename(p)}"))
            self.root.after(0, lambda: self._finish_export(out, items))

        threading.Thread(target=_copy_worker, daemon=True).start()
        self._st(_("status_exporting"), "warn")

    def _finish_export(self, out: str, items: list):
        rows = ""
        for i, e in enumerate(items, 1):
            ib   = os.path.basename(e.get("image_path", ""))
            it   = (f'<img src="{i:03d}_{ib}" style="max-width:260px;border-radius:6px">'
                    if ib else "无图")
            title = html.escape(App._display_title(e), quote=True)
            tags  = e.get("tags", "") or ""
            tag_html = "".join(
                f'<span style="background:{tag_color(t)};color:white;'
                f'padding:2px 6px;border-radius:3px;font-size:11px;margin-right:4px">'
                f'{html.escape(t, quote=True)}</span>'
                for t in tags.split(",") if t.strip())
            rows += (f"<tr><td style='color:#888;font-size:11px'>{e['timestamp']}</td>"
                     f"<td><b>{title}</b>{('<br>' + tag_html) if tag_html else ''}"
                     f"<br><span style='color:#aaa;font-size:10px'>{html.escape(e['prompt'], quote=True)}</span><br>"
                     f"<span style='color:#f0a500;font-size:11px'>{html.escape(e.get('translated',''), quote=True)}</span></td>"
                     f"<td style='color:#4ecca3;font-size:11px'>{html.escape(e.get('provider',''), quote=True)}</td>"
                     f"<td>{'⭐' if e.get('favorited') else ''}</td>"
                     f"<td>{it}</td></tr>")
        html_str = (f"<!DOCTYPE html><html lang='zh'><head><meta charset='UTF-8'>"
                f"<title>AI生图记录</title>"
                f"<style>body{{font-family:Arial;background:#1a1a2e;color:#eaeaea;padding:24px}}"
                f"h1{{color:#e94560}}table{{width:100%;border-collapse:collapse}}"
                f"th{{background:#0f3460;padding:10px;text-align:left}}"
                f"td{{border-bottom:1px solid #2a3a5a;padding:10px;vertical-align:top}}"
                f"tr:hover{{background:#16213e}}</style>"
                f"</head><body><h1>✨ AI 文字生图记录本</h1>"
                f"<p>{len(items)} 条 · {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>"
                f"<table><tr><th>时间</th><th>提示词</th><th>接口</th>"
                f"<th>收藏</th><th>图片</th></tr>{rows}</table></body></html>")
        open(os.path.join(out, "记录本.html"), "w", encoding="utf-8").write(html_str)
        messagebox.showinfo("完成", f"已导出 {len(items)} 条\n至：{out}")

    def _save(self):
        if not self.cur_path or not os.path.exists(self.cur_path):
            messagebox.showwarning("提示", "暂无图片"); return
        d = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("所有文件", "*.*")],
            initialfile=os.path.basename(self.cur_path))
        if d:
            Image.open(self.cur_path).save(d)
            messagebox.showinfo("完成", f"已保存：{d}")

    def _copy_path(self):
        if self.cur_path:
            self.root.clipboard_clear(); self.root.clipboard_append(self.cur_path)
            self._st("📋 路径已复制", "ok")
