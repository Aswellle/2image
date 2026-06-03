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
from data.repository import (
    add_entry, get_all_entries, delete_entry,
    clear_all_entries, count_entries,
    rename_entry, toggle_favorite,
    update_tags, get_all_tags, get_stats,
    get_year_heatmap, get_available_years, get_year_stats,
)
from services.image_service import generate_image, save_image_file
from services.logger import log_to_file
from services.translation import has_chinese, translate_zh_to_en
from services.providers import FREE_PROVIDERS, PAID_PROVIDERS

from ui.viewer import ImageViewerWindow
from ui.wizard_free import ConfigWizard
from ui.wizard_paid import PaidWizard
from ui.prompt_wizard import PromptWizard
from ui.phrase_panel import PhrasePanel
from ui.sidebar import HistorySidebar
from ui.main_content import MainContent

from config.theme import DARK_THEME as C, TAG_PALETTE, tag_color, init_theme
from config.i18n import _, init_language
MAX_NICK_LEN = 20
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
        root.geometry("1380x920")
        root.configure(bg=C["bg"])
        root.minsize(1000, 720)

        self.cfg            = load_config()
        init_theme(self.cfg)
        init_language(self.cfg)
        self.cur_path       = None
        self.sel_id         = None
        self._viewer_win    = None
        self._prompt_wizard = None
        self._phrase_panel  = None
        self._cur_bytes     = None

        # 侧栏宽度
        self._sidebar_w   = SIDEBAR_DEF
        self.MAX_NICK_LEN = MAX_NICK_LEN
        self._sash_drag_x = None
        self._sash_drag_w = None

        # 批量（单张 / 旧兼容路径）
        self._batch_total  = 0
        self._batch_done   = 0
        self._batch_params = None

        # _load_entry 防抖 job
        self._load_entry_job = None
        self._resize_timer = None

        self._build_menu()
        self._build()
        self._bind_hotkeys()
        # Fix-6: 延迟首次刷新，等待 Canvas <Configure> 事件处理完毕后
        # self.hc 的 window item (_hw) 才会获得正确的 explicit width，
        # 否则 self.hi 无宽度约束，卡片布局在 "浮动" 状态下建立，
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
        r.bind("<Control-R>",        lambda e: self._gen())
        r.bind("<Control-p>",        lambda e: self._open_prompt_wizard())
        r.bind("<Control-P>",        lambda e: self._open_prompt_wizard())
        r.bind("<Control-l>",        lambda e: self._clr_log())
        r.bind("<Control-L>",        lambda e: self._clr_log())
        r.bind("<Control-b>",        lambda e: self._open_phrase_panel())
        r.bind("<Control-B>",        lambda e: self._open_phrase_panel())
        r.bind("<Control-q>",        lambda e: self._switch_to_queue_tab())
        r.bind("<Control-Q>",        lambda e: self._switch_to_queue_tab())

    # ══════════════════════════════════════════════════════════
    #   菜单
    # ══════════════════════════════════════════════════════════
    def _build_menu(self):
        from config.settings import APP_DIR, LOG_FILE

        def _menu(parent):
            return tk.Menu(parent, tearoff=0,
                           bg=C["panel"], fg=C["text"],
                           activebackground=C["acc"], activeforeground="white",
                           relief="flat", bd=0)

        def _open(url):
            return lambda: webbrowser.open(url)

        menubar = tk.Menu(self.root, bg=C["panel"], fg=C["text"],
                          activebackground=C["acc"], activeforeground="white",
                          relief="flat", bd=0)
        self.root.config(menu=menubar)

        # ── 🛠 工具 ───────────────────────────────────────────────
        m_tools = _menu(menubar)
        menubar.add_cascade(label=_("menu_tools"), menu=m_tools)
        m_tools.add_command(label=_("wizard_title") + "…        Ctrl+P",
                            command=self._open_prompt_wizard)
        m_tools.add_separator()
        m_tools.add_command(label=_("phrase_title") + "…         Ctrl+B",
                            command=self._open_phrase_panel)
        m_tools.add_command(label=_("btn_variant_gen"),
                            command=self._switch_to_variant_tab)
        m_tools.add_command(label="  📋  " + _("tab_queue").strip() + "…         Ctrl+Q",
                            command=self._switch_to_queue_tab)

        # ── 🔑 接口配置 ───────────────────────────────────────────
        m_api = _menu(menubar)
        menubar.add_cascade(label=" 🔑  接口配置 ", menu=m_api)
        m_api.add_command(label="  🆓  免费接口配置…",  command=self._open_wizard)
        m_api.add_command(label="  💎  付费接口配置…",  command=self._open_paid_wizard)
        m_api.add_separator()

        # 免费接口注册链接子菜单
        m_free_links = _menu(m_api)
        m_api.add_cascade(label="  🌐  免费接口注册链接", menu=m_free_links)
        m_free_links.add_command(label="  ★  硅基流动（推荐，免费赠额）",
            command=_open("https://cloud.siliconflow.cn/account/ak"))
        m_free_links.add_command(label="  ·  Google Gemini（500次/天）",
            command=_open("https://aistudio.google.com/app/apikey"))
        m_free_links.add_command(label="  ·  Cloudflare AI（1万次/天）",
            command=_open("https://dash.cloudflare.com/profile/api-tokens"))
        m_free_links.add_command(label="  ·  OpenRouter（部分模型免费）",
            command=_open("https://openrouter.ai/keys"))
        m_free_links.add_command(label="  ·  ModelsLab（100次/天）",
            command=_open("https://modelslab.com/dashboard/api"))
        m_free_links.add_command(label="  ·  Segmind（注册送 $5）",
            command=_open("https://www.segmind.com/"))
        m_free_links.add_command(label="  ·  HuggingFace Token",
            command=_open("https://huggingface.co/settings/tokens/new?tokenType=read"))

        # 付费接口注册链接子菜单
        m_paid_links = _menu(m_api)
        m_api.add_cascade(label="  🌐  付费接口注册链接", menu=m_paid_links)
        m_paid_links.add_command(label="  ·  OpenAI DALL-E 3",
            command=_open("https://platform.openai.com/api-keys"))
        m_paid_links.add_command(label="  ·  Stability AI",
            command=_open("https://platform.stability.ai/"))
        m_paid_links.add_command(label="  ·  Replicate FLUX",
            command=_open("https://replicate.com/account/api-tokens"))
        m_paid_links.add_command(label="  ·  xAI Grok（注册送 $25）",
            command=_open("https://console.x.ai/"))

        # ── 📊 数据 ───────────────────────────────────────────────
        m_data = _menu(menubar)
        menubar.add_cascade(label=_("menu_data"), menu=m_data)
        m_data.add_command(label="  📊  统计看板…",  command=self._show_stats)
        m_data.add_separator()
        def _open_path(p):
            if os.name == "nt":
                os.startfile(p)
            else:
                import subprocess as _sp
                _sp.Popen(["xdg-open", p])
        m_data.add_command(label="  📁  数据文件夹",
            command=lambda: _open_path(APP_DIR))
        m_data.add_command(label="  📄  调试日志",
            command=lambda: _open_path(LOG_FILE))

        # ── ⚙ 设置 ───────────────────────────────────────────────
        m_set = _menu(menubar)
        menubar.add_cascade(label=_("menu_settings"), menu=m_set)
        m_set.add_command(label="  🖼  应用偏好设置…",  command=self._open_app_settings)
        m_set.add_command(label="  ⌨  快捷键说明…",    command=self._show_shortcuts)

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
        self._top_free_lbl.pack(side="right", padx=(4, 14))

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

    def _gen_variants(self):
        prompt = self.content.pt.get("1.0", "end").strip()
        if not prompt: messagebox.showwarning("提示", "请先输入描述文字！"); return
        psel = self.content.pv.get()
        if psel.startswith("───"):
            messagebox.showinfo("提示", "请选择一个具体接口，而非分隔线。"); return
        n      = max(1, min(6, self.content.variant_n_var.get()))
        sz     = self.content.szv.get()
        w, h   = [int(x) for x in sz.replace("×", "x").split("x")]
        if psel == _("provider_auto"):
            from services.smart_router import get_provider_order
            porder = get_provider_order(prompt, self.cfg)
        else:
            porder = [psel]
        self._batch_params = {"prompt": prompt, "translated": "", "w": w, "h": h,
                               "porder": porder, "cfg": self.cfg}
        self.content._nb.select(1)
        from services.translation import translate_zh_to_en as _trans
        self.content._batch_panel.start_batch(
            n=n, params=self._batch_params,
            translate_fn=lambda p, cfg, log_cb: _trans(p, log_cb=log_cb),
            generate_fn=generate_image, save_fn=save_image_file,
            log_fn=self._log, on_keep_fn=self._on_variant_kept)
        self._st(_("status_batch_start", n=n), "warn")
        self._log(f"🎲 变体生成 n={n} size={sz}")

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
    def _show_shortcuts(self):
        win = tk.Toplevel(self.root); win.title("⌨ 快捷键说明")
        win.configure(bg=C["bg"]); win.resizable(False, False); win.grab_set()
        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width()  - 520) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 460) // 2
        win.geometry(f"520x460+{max(0,x)}+{max(0,y)}")
        hdr = tk.Frame(win, bg=C["acc"]); hdr.pack(fill="x")
        tk.Label(hdr, text="⌨  快捷键说明", font=F["h1"],
                 bg=C["acc"], fg="white").pack(side="left", padx=16, pady=10)
        body = tk.Frame(win, bg=C["bg"]); body.pack(fill="both", expand=True, padx=20, pady=16)
        rows = [
            ("生成 / 重新生成",    "Ctrl + Enter  /  Ctrl + R"),
            ("AI 提示词助手",      "Ctrl + P"),
            ("📚 提示词片段库",    "Ctrl + B"),
            ("另存为",             "Ctrl + S"),
            ("导出历史记录",       "Ctrl + E"),
            ("打开独立查看器",     "Ctrl + O"),
            ("清空调试日志",       "Ctrl + L"),
        ]
        for i, (action, keys) in enumerate(rows):
            rb = C["panel"] if i % 2 == 0 else C["bg"]
            row = tk.Frame(body, bg=rb); row.pack(fill="x", pady=1)
            tk.Label(row, text=action, font=F["input"], bg=rb, fg=C["text"],
                     width=20, anchor="w").pack(side="left", padx=(10, 0), pady=6)
            tk.Label(row, text=keys, font=F["mono_lg"],
                     bg=rb, fg=C["ok"], anchor="w").pack(side="left", padx=12, pady=6)
        tk.Button(win, text=_("btn_close"), font=F["input"], bg=C["acc"], fg="white",
                  bd=0, padx=24, pady=6, cursor="hand2", command=win.destroy
                  ).pack(pady=(8, 16))

    def _open_app_settings(self):
        win = tk.Toplevel(self.root); win.title("🖼 应用偏好设置")
        win.configure(bg=C["bg"]); win.resizable(False, False); win.grab_set()
        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width()  - 460) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 360) // 2
        win.geometry(f"460x360+{max(0,x)}+{max(0,y)}")
        hdr = tk.Frame(win, bg=C["acc"]); hdr.pack(fill="x")
        tk.Label(hdr, text="🖼  应用偏好设置", font=F["h1"],
                 bg=C["acc"], fg="white").pack(side="left", padx=16, pady=10)
        body = tk.Frame(win, bg=C["bg"]); body.pack(fill="both", expand=True, padx=24, pady=16)
        tk.Label(body, text="默认生成尺寸", font=F["btn"],
                 bg=C["bg"], fg=C["sub"]).pack(anchor="w", pady=(0, 4))
        sz_var = tk.StringVar(value=self.cfg.get("default_size", "1024x1024").replace("×", "x"))
        ttk.Combobox(body, textvariable=sz_var, state="readonly", width=20,
                     values=["512x512","768x768","1024x1024","1024x576","1280x720",
                             "1920x1080","576x1024","720x1280","768x1024"]
                     ).pack(anchor="w", pady=(0, 14))
        tk.Label(body, text="启动行为", font=F["btn"],
                 bg=C["bg"], fg=C["sub"]).pack(anchor="w", pady=(0, 4))
        wiz_var = tk.BooleanVar(value=self.cfg.get("show_wizard_on_start", True))
        tk.Checkbutton(body, text="启动时显示免费接口配置向导",
                       variable=wiz_var, font=F["body"], bg=C["bg"], fg=C["text"],
                       activebackground=C["bg"], selectcolor=C["entry"]).pack(anchor="w")
        st = tk.Label(body, text="", font=F["body"], bg=C["bg"], fg=C["ok"]); st.pack(anchor="w", pady=(12, 0))
        def _save():
            self.cfg["default_size"] = sz_var.get()
            self.cfg["show_wizard_on_start"] = wiz_var.get()
            save_config(self.cfg); self.content.szv.set(sz_var.get())
            st.config(text="✅ 已保存！"); win.after(1200, win.destroy)
        bot = tk.Frame(win, bg=C["panel"]); bot.pack(fill="x", side="bottom")
        tk.Button(bot, text=_("btn_save"), font=F["btn"], bg=C["ok"], fg="#0a1a0a",
                  bd=0, padx=24, pady=8, cursor="hand2", command=_save
                  ).pack(side="right", padx=16, pady=10)
        tk.Button(bot, text=_("btn_cancel"), font=F["body"], bg=C["panel"], fg=C["sub"],
                  bd=0, padx=16, pady=8, cursor="hand2", command=win.destroy
                  ).pack(side="right", pady=10)

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
        cfg = self.cfg
        sf  = cfg.get("sf_key",          "").strip()
        hf  = cfg.get("hf_token",        "").strip()
        sh  = cfg.get("stablehorde_key", "").strip()
        oai = cfg.get("openai_key",      "").strip()
        stb = cfg.get("stability_key",   "").strip()
        rep = cfg.get("replicate_key",   "").strip()
        xai = cfg.get("xai_key",         "").strip()
        gem = cfg.get("gemini_key",      "").strip()
        cfa = cfg.get("cf_account_id",   "").strip()
        cft = cfg.get("cf_api_token",    "").strip()
        mdl = cfg.get("modelslab_key",   "").strip()
        sgm = cfg.get("segmind_key",     "").strip()
        ort = cfg.get("openrouter_key",  "").strip()
        pol = cfg.get("pollinations_enabled", True)

        # 免费接口计数（共9个）：Pollinations 和 StableHorde 无需 Key 始终可用
        free_count = sum([
            bool(sf), bool(gem), bool(pol),
            bool(cfa and cft), bool(mdl), bool(sgm),
            bool(ort), bool(hf),
            True,  # StableHorde 匿名模式始终可用
        ])
        # 付费接口计数（共4个）
        paid_count = sum([bool(oai), bool(stb), bool(rep), bool(xai)])

        # ── 顶栏计数标签 ──────────────────────────────────────────
        free_has_key = bool(sf or hf or gem or ort or mdl or sgm or (cfa and cft))
        self._top_free_lbl.config(
            text=_("status_free_count", n=free_count, total=len(FREE_PROVIDERS)),
            fg=C["ok"] if free_has_key else C["warn"],
        )
        self._top_paid_lbl.config(
            text=_("status_paid_count", n=paid_count, total=len(PAID_PROVIDERS)),
            fg="#a78bfa" if paid_count else C["sub"],
        )

        # ── 侧边栏详细状态 ────────────────────────────────────
        if sf:
            self.content.hf_status_lbl.config(text="🆓 硅基流动: 已配置 ✓", fg=C["ok"])
        elif hf:
            self.content.hf_status_lbl.config(text="🆓 HF: 已配置 ✓（建议配置硅基流动）", fg=C["warn"])
        else:
            self.content.hf_status_lbl.config(text="⚠ " + _("status_no_records"), fg=C["hl"])
        paid_parts = []
        if oai: paid_parts.append("DALL-E ✅")
        if stb: paid_parts.append("Stability ✅")
        if rep: paid_parts.append("Replicate ✅")
        if xai: paid_parts.append("xAI ✅")
        if paid_parts:
            self.content.sh_status_lbl.config(text="💎 " + " | ".join(paid_parts), fg="#a78bfa")
        elif sh:
            self.content.sh_status_lbl.config(text="🆓 StableHorde: 已配置 ✓", fg=C["ok"])
        else:
            self.content.sh_status_lbl.config(text="ℹ StableHorde: 匿名兜底 | 无付费接口", fg=C["sub"])

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
    #   单张图片生成
    # ══════════════════════════════════════════════════════════
    def _gen(self, event=None):
        prompt = self.content.pt.get("1.0", "end").strip()
        MAX_PROMPT_CHARS = 2000
        if len(prompt) > MAX_PROMPT_CHARS:
            self._st(_("status_prompt_too_long", cur=len(prompt), max=MAX_PROMPT_CHARS), "hl")
            return
        if not prompt: messagebox.showwarning("提示", "请先输入描述文字！"); return
        psel = self.content.pv.get()
        if psel.startswith("───"):
            messagebox.showinfo("提示", "请选择一个具体接口，而非分隔线。"); return
        checks = {
            "💎 OpenAI DALL-E 3": ("openai_key",   self._open_paid_wizard,
                                    "使用 OpenAI DALL-E 3 需要填写 API Key。\n是否现在配置？"),
            "💎 Stability AI":    ("stability_key", self._open_paid_wizard,
                                    "使用 Stability AI 需要填写 API Key。\n是否现在配置？"),
            "💎 Replicate FLUX":  ("replicate_key", self._open_paid_wizard,
                                    "使用 Replicate 需要填写 API Token。\n是否现在配置？"),
            "硅基流动 SiliconFlow (★推荐)": ("sf_key",   self._open_wizard,
                                    "使用硅基流动需要填写 API Key。\n是否现在配置？"),
            "HuggingFace (备用)": ("hf_token",      self._open_wizard,
                                    "使用 HuggingFace 需要填写 Token。\n是否现在配置？"),
        }
        if psel in checks:
            key_name, wizard_fn, msg = checks[psel]
            if not self.cfg.get(key_name, "").strip():
                if messagebox.askyesno("需要配置", msg): wizard_fn()
                return
        if psel == _("provider_auto"):
            if not self.cfg.get("sf_key","").strip() and not self.cfg.get("hf_token","").strip():
                if messagebox.askyesno("建议配置",
                    "尚未配置任何免费 API Key。\n建议配置「硅基流动」。\n是否现在配置？"):
                    self._open_wizard(); return
        sz = self.content.szv.get(); w, h = [int(x) for x in sz.replace("×", "x").split("x")]
        if psel == _("provider_auto"):
            from services.smart_router import get_provider_order
            porder = get_provider_order(prompt, self.cfg)
        else:
            porder = [psel]
        self._batch_total = 1; self._batch_done = 0
        self._batch_params = {"prompt": prompt, "translated": "", "w": w, "h": h,
                               "porder": porder, "cfg": self.cfg}
        self.content.gb.config(state="disabled", text=_("btn_generating"))
        self.content.pb.pack(fill="x", padx=14, pady=(0, 4)); self.content.pb.start(10)
        self._st(_("status_translating"), "warn")
        self.content._prev_cv.delete("prev"); self.content._prev_item = None
        self.content._prev_cv.update_idletasks()
        cw = self.content._prev_cv.winfo_width() or 600; ch = self.content._prev_cv.winfo_height() or 400
        self.content._prev_cv.itemconfig(self.content._prev_ph, text=_("status_generating"))
        self.content._prev_cv.coords(self.content._prev_ph, cw // 2, ch // 2)
        self._log(f"── 开始: {prompt[:60]} ──")
        self.content._nb.select(0)  # 切换到预览 Tab

        def _make_status_cb(total):
            cnt = [0]
            def cb(msg):
                cnt[0] += 1
                self.root.after(0, lambda: self._st(f"[{cnt[0]}/{total}] {msg}", "warn"))
            return cb
        def _run():
            seed       = random.randint(0, 2_147_483_647)
            translated = prompt
            if has_chinese(prompt):
                self.root.after(0, lambda: self._st(_("status_translating"), "warn"))
                translated = translate_zh_to_en(prompt, log_cb=self._log)
                self._batch_params["translated"] = translated
            try:
                # 只在图生图模式且已选取参考图时传入，文生图模式始终为 None
                _gen_mode = getattr(self.content, '_gen_mode', 't2i')
                if _gen_mode == 'i2i':
                    ref_image = getattr(self.content, '_ref_image', None)
                    strength  = getattr(self.content, '_ref_strength', None)
                    strength  = strength.get() if strength is not None else 0.6
                    if ref_image is None:
                        self.root.after(0, lambda: self._err("图生图模式需要先选取参考图"))
                        return
                else:
                    ref_image = None
                    strength  = 0.6
                data, used = generate_image(
                    translated, w, h, seed, self.cfg,
                    provider_order=porder,
                    status_cb=_make_status_cb(len(porder)),
                    log_cb=self._log,
                    ref_image=ref_image,
                    strength=strength)
                path = save_image_file(data, prompt,
                                       seed=seed, provider=used,
                                       translated=translated,
                                       size=f"{w}x{h}")
                add_entry(prompt, translated, path, used)
                self.root.after(0, lambda: self._ok(data, path, used))
            except Exception as ex:
                self.root.after(0, lambda e=str(ex): self._err(e))

        threading.Thread(target=_run, daemon=True).start()

    def _ok(self, data: bytes, path: str, prov: str):
        self.content.pb.stop(); self.content.pb.pack_forget()
        self.content.gb.config(state="normal", text=_("btn_generate"))
        self.cur_path = path; self._cur_bytes = data
        self.content._set_preview(data)
        self._push_to_viewer(data, path)
        self._st(_("status_success", prov=prov), "ok")
        self._log(f"✓ 成功 provider={prov}")
        self._batch_params = None
        self.sidebar._refresh_hist(); self.content._refresh_tag_stats()

    def _err(self, err: str):
        self.content.gb.config(state="normal", text=_("btn_generate"))
        self.content.pb.stop(); self.content.pb.pack_forget()
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

        self._st(f"❌ {friendly}", "hl"); self._log(f"✗ {err}")
        cw = self.content._prev_cv.winfo_width() or 600; ch = self.content._prev_cv.winfo_height() or 400
        self.content._prev_cv.itemconfig(self.content._prev_ph, text=_("preview_error"))
        self.content._prev_cv.coords(self.content._prev_ph, cw // 2, ch // 2)
        if any(k in err for k in ["API Key","Key","Token","token","401","402","403","额度"]):
            self.root.after(100, lambda: messagebox.showwarning(
                "需要配置 API Key",
                f"{err[:200]}\n\n点击「🆓 免费配置」配置硅基流动 API Key。"))

    def _update_char_count(self):
        """更新输入框字符计数标签（公开，供 PhrasePanel 等外部调用）。"""
        try:
            txt = self.content.pt.get("1.0", "end-1c")   # end-1c 排除末尾隐式换行
            n   = len(txt)
            color = (C["ok"]   if n < 200
                     else C["warn"] if n < 400
                     else C["hl"])
            self.content._char_lbl.config(text=_("lbl_chars", n=n), fg=color)
        except Exception:
            pass

    def _st(self, msg: str, k: str = "ok"):
        m = {"ok": C["ok"], "warn": C["warn"], "hl": C["hl"]}
        self.content.stv.set(msg); self.content.stl.config(fg=m.get(k, C["ok"]))

    # ══════════════════════════════════════════════════════════
    #   重置 / 导出 / 保存
    # ══════════════════════════════════════════════════════════
    def _reset_view(self):
        # ── Bug4 修复：重置全部过滤状态，确保"清空当前显示"能恢复完整列表 ──
        self.sidebar._tag_filter = ""
        self.sidebar._fav_only   = False
        try:
            self.sidebar._btn_all.config(bg=C["acc"], fg="white")
            self.sidebar._btn_fav.config(bg=C["panel"], fg=C["star_off"])
            self.sidebar._refresh_tag_chips()
        except Exception:
            pass
        # ── 清空主界面状态 ──
        self.sel_id = self.cur_path = None
        self._cur_bytes = self.content._prev_orig = None
        self.content.pt.delete("1.0", "end")
        self.content._prev_cv.delete("prev"); self.content._prev_item = None
        self.content._clear_compare()
        self.content._prev_cv.update_idletasks()
        cw = self.content._prev_cv.winfo_width() or 600; ch = self.content._prev_cv.winfo_height() or 400
        self.content._prev_cv.itemconfig(self.content._prev_ph,
            text=_("preview_placeholder"))
        self.content._prev_cv.coords(self.content._prev_ph, cw // 2, ch // 2)
        self.sidebar._refresh_hist()
        self._st(_("status_ready"), "ok")

    def _export(self):
        items = get_all_entries()
        if not items: messagebox.showinfo(_("status_no_records"), _("status_no_records")); return
        d = filedialog.askdirectory(title=_("dlg_select_export_dir"))
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
