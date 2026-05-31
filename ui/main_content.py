"""
ui/main_content.py — Main content / right-panel extracted from App.
────────────────────────────────────────────────────────────────
Mechanical extraction from ui/app.py v5.1.
All App-level methods and state accessed through self.app.
"""
import io
import os
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

from PIL import Image, ImageTk

from config.fonts import F
from config.theme import C, TAG_PALETTE, tag_color
from config.i18n import _
from data.repository import get_all_entries, get_stats
from services.providers import FREE_PROVIDERS, PAID_PROVIDERS
from services.image_service import generate_image, save_image_file
from ui.batch_panel import BatchPanel
from ui.queue_panel import QueuePanel
from ui.app_protocol import MainContentProtocol

class MainContent:
    """Right-panel main content: input, preview, variants, queue, log."""

    def __init__(self, parent: tk.Frame, app: MainContentProtocol):
        self.app = app
        self.parent = parent

        # ── State initialized before _build ───────────────────
        self.variant_n_var = tk.IntVar(value=5)
        self._batch_params = None

        # Preview state
        self._prev_orig = None
        self._prev_photo = None
        self._prev_item = None

        # Compare state
        self._cmp_orig = None
        self._cmp_photo = None
        self._cmp_mode = False

        # Resize timers
        self._prev_resize_timer = None
        self._cmp_resize_timer = None

        self._build(parent)

    # ══════════════════════════════════════════════════════════
    #   右侧主区
    # ══════════════════════════════════════════════════════════


    def _build(self, R):
        # ── ttk 暗色主题配置 ──────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")  # clam theme allows customization
        style.configure("TNotebook", background=C["bg"], borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=C["panel"], foreground=C["sub"],
                        padding=[12, 4], font=F["small_b"])
        style.map("TNotebook.Tab",
                  background=[("selected", C["acc"])],
                  foreground=[("selected", "white")])
        style.configure("TCombobox",
                        fieldbackground=C["entry"], background=C["acc"],
                        foreground=C["text"], arrowcolor=C["text"])
        style.map("TCombobox",
                  fieldbackground=[("readonly", C["entry"])],
                  foreground=[("readonly", C["text"])])
        tk.Label(R, text=_("app_input_label"),
                 font=F["btn"], bg=C["bg"], fg=C["text"]
                 ).pack(anchor="w", pady=(12, 4), padx=14)

        pf = tk.Frame(R, bg=C["entry"]); pf.pack(fill="x", padx=14, pady=(0, 0))
        self.pt = tk.Text(pf, height=4, font=F["label"], bg=C["entry"], fg=C["text"],
                          insertbackground="white", wrap="word", bd=0, padx=10, pady=8, relief="flat")
        self.pt.pack(fill="x")
        self.pt.bind("<Control-Return>", lambda e: (self.app._gen(), "break")[1])

        # ── 输入框底部辅助条：字数统计 + 快捷加入队列 ─────────
        _pt_foot = tk.Frame(R, bg="#0d1a30")
        _pt_foot.pack(fill="x", padx=14)

        self._char_lbl = tk.Label(
            _pt_foot, text="0 字符",
            font=F["mono_tiny"], bg="#0d1a30", fg="#4a5a7a")
        self._char_lbl.pack(side="left", padx=6, pady=2)

        tk.Button(
            _pt_foot, text=_("btn_add_queue"),
            font=F["tiny"], bg="#1e3060", fg="#93c5fd",
            bd=0, padx=8, pady=2, cursor="hand2",
            command=lambda: (self.app._switch_to_queue_tab(),
                             self._queue_panel._add_from_app())
        ).pack(side="right", padx=4, pady=2)

        # Bug3 修复：
        # · 旧代码用 self.after() —— App 不是 tk.Widget，静默失败
        # · 旧代码只绑 <KeyRelease> —— 对粘贴、程序写入等无效
        # · 正确方案：绑定 <<Modified>> 虚拟事件（Tkinter 标准文本变更接口），
        #   每次回调后必须 edit_modified(False) 重置标志，否则只触发一次
        def _on_text_modified(event=None):
            try:
                # 重置 Modified 标志（否则后续变更不再触发事件）
                self.pt.edit_modified(False)
            except Exception:
                pass
            self._update_char_count()

        self.pt.bind("<<Modified>>", _on_text_modified)


        # ── 生成行 ────────────────────────────────────────────
        opt = tk.Frame(R, bg=C["bg"]); opt.pack(fill="x", padx=14, pady=(0, 4))
        tk.Label(opt, text=_("lbl_size"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        sz_default = self.app.cfg.get("default_size", "1024x1024").replace("×", "x")
        self.szv = tk.StringVar(value=sz_default)
        ttk.Combobox(opt, textvariable=self.szv, width=12, state="readonly",
                     values=["512x512","768x768","1024x1024","1024x576","1280x720",
                             "1920x1080","576x1024","720x1280","768x1024"]
                     ).pack(side="left", padx=(2, 8))
        tk.Label(opt, text=_("lbl_provider"), font=F["body"], bg=C["bg"], fg=C["sub"]).pack(side="left")
        self.pv = tk.StringVar(value=_("provider_auto"))
        provider_list = ([_("provider_auto"),_("provider_free_section")]
                         + list(FREE_PROVIDERS.keys())
                         + [_("provider_paid_section")]
                         + list(PAID_PROVIDERS.keys()))
        ttk.Combobox(opt, textvariable=self.pv, width=26, state="readonly",
                     values=provider_list).pack(side="left", padx=(2, 8))
        self.gb = tk.Button(opt, text=_("btn_generate"),
                            font=F["btn"], bg=C["hl"], fg="white",
                            bd=0, padx=16, pady=6, cursor="hand2",
                            activebackground="#c73652", command=self.app._gen)
        self.gb.pack(side="left")

        # ── 工具行 ────────────────────────────────────────────
        opt2 = tk.Frame(R, bg=C["bg"]); opt2.pack(fill="x", padx=14, pady=(0, 6))
        tk.Button(opt2, text=_("btn_phrase_lib"),
                  font=F["body_b"], bg="#065f46", fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=self.app._open_phrase_panel).pack(side="left")
        tk.Button(opt2, text=_("btn_prompt_wizard"),
                  font=F["body_b"], bg="#7c3aed", fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=self.app._open_prompt_wizard).pack(side="left", padx=(6, 0))
        tk.Frame(opt2, bg=C["sep"], width=1).pack(side="left", fill="y", padx=8, pady=4)
        tk.Label(opt2, text=_("lbl_variant_count"), font=F["body"],
                 bg=C["bg"], fg=C["sub"]).pack(side="left")

        # ── 圆形 ➖ / 数字 / ➕ 控件（Issue-1 修复：大点击面积）────
        def _dec_n():
            v = max(1, self.variant_n_var.get() - 1)
            self.variant_n_var.set(v); _n_lbl.config(text=str(v))
        def _inc_n():
            v = min(6, self.variant_n_var.get() + 1)
            self.variant_n_var.set(v); _n_lbl.config(text=str(v))

        _n_grp = tk.Frame(opt2, bg=C["bg"]); _n_grp.pack(side="left", padx=(2, 4))
        tk.Button(_n_grp, text="⊖", font=F["btn"],
                  bg=C["acc"], fg="#a0c8ff", bd=0,
                  width=2, pady=2, cursor="hand2",
                  activebackground=C["hl"], activeforeground="white",
                  command=_dec_n).pack(side="left")
        _n_lbl = tk.Label(_n_grp,
                           text=str(self.variant_n_var.get()),
                           font=F["body_b"],
                           bg=C["entry"], fg=C["ok"],
                           width=2, pady=2, relief="flat")
        _n_lbl.pack(side="left", padx=2)
        tk.Button(_n_grp, text="⊕", font=F["btn"],
                  bg=C["acc"], fg="#a0c8ff", bd=0,
                  width=2, pady=2, cursor="hand2",
                  activebackground="#4ecca3", activeforeground="#0a1a0a",
                  command=_inc_n).pack(side="left")

        tk.Button(opt2, text=_("btn_variant_gen"),
                  font=F["body_b"], bg="#4a1d96", fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=self.app._gen_variants).pack(side="left")
        tk.Label(opt2, text=_("shortcut_hint"),
                 font=F["small"], bg=C["bg"], fg="#6a7a9a").pack(side="left", padx=6)

        # 接口状态栏
        tok_bar = tk.Frame(R, bg=C["panel"]); tok_bar.pack(fill="x", padx=14, pady=(0, 4))
        self.hf_status_lbl = tk.Label(tok_bar, text="", font=F["body"],
                                       bg=C["panel"], fg=C["sub"], padx=10)
        self.hf_status_lbl.pack(side="left")
        self.sh_status_lbl = tk.Label(tok_bar, text="", font=F["body"],
                                       bg=C["panel"], fg=C["sub"], padx=10)
        self.sh_status_lbl.pack(side="left")
        tk.Button(tok_bar, text=_("btn_paid_config"), font=F["body"],
                  bg="#7c3aed", fg="white", bd=0, padx=8, pady=3, cursor="hand2",
                  command=self.app._open_paid_wizard).pack(side="right", padx=4, pady=5)
        tk.Button(tok_bar, text=_("btn_free_config"), font=F["body"],
                  bg=C["hl"], fg="white", bd=0, padx=8, pady=3, cursor="hand2",
                  command=self.app._open_wizard).pack(side="right", padx=4, pady=5)

        # ── 标签统计区 ────────────────────────────────────────
        self._tag_stat_frame = tk.Frame(R, bg=C["panel"])
        self._tag_stat_frame.pack(fill="x", padx=14, pady=(0, 4))
        self._tag_stat_inner = tk.Frame(self._tag_stat_frame, bg=C["panel"])
        self._tag_stat_inner.pack(fill="x", padx=8, pady=4)
        self.app.root.after(200, self._refresh_tag_stats)

        # 状态栏
        self.stv = tk.StringVar(value=_("status_ready"))
        self.stl = tk.Label(R, textvariable=self.stv, font=F["body"],
                            bg=C["panel"], fg=C["ok"], anchor="w", padx=10, pady=5)
        self.stl.pack(fill="x", padx=14, pady=(0, 4))
        self.pb = ttk.Progressbar(R, mode="indeterminate")

        # ── Notebook ──────────────────────────────────────────
        self._nb = ttk.Notebook(R)
        self._nb.pack(fill="both", expand=True, padx=14, pady=(4, 8))

        self.imf = tk.Frame(self._nb, bg=C["panel"])
        self._nb.add(self.imf, text=_("tab_preview"))
        self._build_preview_tab()

        self._var_frame = tk.Frame(self._nb, bg="#0a0f1a")
        self._nb.add(self._var_frame, text=_("tab_variants"))
        self._batch_panel = BatchPanel(self._var_frame, self.app)
        self._batch_panel.pack(fill="both", expand=True)

        # ── 📋 顺序生成队列 Tab ───────────────────────────────
        self._queue_frame = tk.Frame(self._nb, bg="#1a1a2e")
        self._nb.add(self._queue_frame, text=_("tab_queue"))
        self._queue_panel = QueuePanel(self._queue_frame, self.app)
        self._queue_panel.pack(fill="both", expand=True)

        lf2 = tk.Frame(self._nb, bg=C["bg"])
        self._nb.add(lf2, text=_("tab_debug_log"))
        self.logt = scrolledtext.ScrolledText(
            lf2, font=F["mono"], bg="#080818", fg="#4ecca3",
            insertbackground="white", bd=0, state="disabled")
        self.logt.pack(fill="both", expand=True, padx=4, pady=4)
        tk.Button(lf2, text=_("btn_clear_log"), font=F["body"], bg=C["acc"],
                  fg="white", bd=0, padx=8, pady=2, cursor="hand2",
                  command=self.app._clr_log).pack(anchor="e", padx=4, pady=2)

    # ══════════════════════════════════════════════════════════
    #   标签统计区
    # ══════════════════════════════════════════════════════════
    def _refresh_tag_stats(self):
        for w in self._tag_stat_inner.winfo_children(): w.destroy()
        try:
            stats    = get_stats()
            top_tags = stats.get("top_tags", [])
        except Exception:
            top_tags = []
        if not top_tags:
            tk.Label(self._tag_stat_inner,
                     text="🏷 暂无标签  —  在历史记录卡片中点击 🏷 添加",
                     font=F["small_i"], bg=C["panel"], fg=C["sub"]
                     ).pack(anchor="w"); return
        tk.Label(self._tag_stat_inner, text="🏷 标签统计：",
                 font=F["small_b"], bg=C["panel"], fg=C["sub"]).pack(side="left")
        for tag, cnt in top_tags[:8]:
            tc     = tag_color(tag)
            active = (self.app._tag_filter == tag)
            chip   = tk.Frame(self._tag_stat_inner,
                               bg=tc if active else C["panel"],
                               highlightbackground=tc, highlightthickness=1)
            chip.pack(side="left", padx=(0, 4))
            tk.Label(chip, text=tag, font=F["small_b"],
                     bg=tc if active else C["panel"], fg="white",
                     padx=5, pady=2).pack(side="left")
            tk.Label(chip, text=str(cnt), font=F["mono_tiny"],
                     bg=tc if active else C["panel"],
                     fg="#c0ffee" if active else C["sub"],
                     padx=3, pady=2).pack(side="left")
            for w in chip.winfo_children():
                w.bind("<Button-1>", lambda ev, t=tag: self.app._on_tag_filter_changed(t))
            chip.bind("<Button-1>", lambda ev, t=tag: self.app._on_tag_filter_changed(t))

    # ══════════════════════════════════════════════════════════
    #   预览 Tab（含对比）— Fix-2: 补充 _cmp_label_b.pack()
    # ══════════════════════════════════════════════════════════
    def _build_preview_tab(self):
        tb = tk.Frame(self.imf, bg="#0d1b2a", height=36)
        tb.pack(fill="x"); tb.pack_propagate(False)

        tk.Button(tb, text=_("btn_open_viewer") + "  (Ctrl+O)",
                  font=F["small_b"], bg=C["hl"], fg="white",
                  bd=0, padx=10, pady=4, cursor="hand2",
                  command=self.app._open_viewer).pack(side="left", padx=6, pady=4)
        tk.Button(tb, text=_("btn_save"), font=F["small"],
                  bg=C["acc"], fg="white", bd=0, padx=8, pady=4,
                  cursor="hand2", command=self.app._save).pack(side="left", padx=2, pady=4)
        tk.Button(tb, text="📋 复制路径", font=F["small"],
                  bg=C["acc"], fg="white", bd=0, padx=8, pady=4,
                  cursor="hand2", command=self.app._copy_path).pack(side="left", padx=2, pady=5)
        tk.Button(tb, text="🔄 重新生成", font=F["small"],
                  bg=C["acc"], fg="white", bd=0, padx=8, pady=4,
                  cursor="hand2", command=self.app._gen).pack(side="left", padx=2, pady=5)
        tk.Frame(tb, bg=C["sep"], width=1).pack(side="left", fill="y", padx=6, pady=6)
        self._cmp_btn = tk.Button(tb, text="⚖ 选取对比图", font=F["small"],
                  bg=C["acc"], fg="white", bd=0, padx=8, pady=4, cursor="hand2",
                  command=self._pick_compare_image)
        self._cmp_btn.pack(side="left", padx=2, pady=5)
        self._cmp_clear_btn = tk.Button(tb, text="✕ 清空对比", font=F["small"],
                  bg=C["dis_bg"], fg="white", bd=0, padx=8, pady=4, cursor="hand2",
                  command=self._clear_compare, state="disabled")
        self._cmp_clear_btn.pack(side="left", padx=2, pady=5)
        tk.Label(tb, text="双击预览图 → 独立查看器",
                 font=F["small"], bg="#0d1b2a", fg=C["sub"]).pack(side="right", padx=10)

        # ── 预览主体 ──────────────────────────────────────────
        self._prev_host = tk.Frame(self.imf, bg="#111827")
        self._prev_host.pack(fill="both", expand=True)
        self._prev_host.columnconfigure(0, weight=1)
        self._prev_host.columnconfigure(2, weight=1)
        self._prev_host.rowconfigure(0, weight=1)

        # 左半（A — 当前图）
        left_wrap = tk.Frame(self._prev_host, bg="#111827")
        left_wrap.grid(row=0, column=0, sticky="nsew")

        # Fix-2: A 侧横幅（初始隐藏，activate 时 pack）
        self._cmp_label_a = tk.Label(left_wrap, text="A →  " + "当前图",
                                      font=F["small_b"],
                                      bg=C["cmp_a"], fg="white")
        # 注：初始不 pack，在 _set_compare_image 中动态 pack

        self._prev_cv = tk.Canvas(left_wrap, bg="#111827", bd=0, highlightthickness=0)
        self._prev_cv.pack(fill="both", expand=True)
        self._prev_photo = None
        self._prev_item  = None
        self._prev_orig  = None
        self._prev_ph = self._prev_cv.create_text(400, 200,
            text=("生成图片后在此处显示缩略预览\n\n"
                  "双击预览图 → 独立查看器\n"
                  "点击「⚖ 选取对比图」→ 并排对比"),
            font=F["body"], fill="#9ab4cc", anchor="center", justify="center")
        self._prev_cv.bind("<Configure>",       self._on_prev_resize)
        self._prev_cv.bind("<Double-Button-1>", lambda e: self.app._open_viewer())
        self._prev_cv.bind("<MouseWheel>",  lambda e: "break")
        self._prev_cv.bind("<Button-4>",    lambda e: "break")
        self._prev_cv.bind("<Button-5>",    lambda e: "break")

        # 分隔线（对比时才 grid）
        self._cmp_divider = tk.Frame(self._prev_host, bg="#4a1d96", width=3)

        # 右半（B — 对比图）
        self._cmp_right_wrap = tk.Frame(self._prev_host, bg="#111827")

        # Fix-2: B 侧横幅 —— 在此 pack，跟随 _cmp_right_wrap 一同显示/隐藏
        self._cmp_label_b = tk.Label(self._cmp_right_wrap, text="B →  " + "对比图",
                                      font=F["small_b"],
                                      bg=C["cmp_b"], fg="white")
        self._cmp_label_b.pack(fill="x")   # ← Fix-2 补充此行

        self._cmp_cv = tk.Canvas(self._cmp_right_wrap, bg="#0a0f1a",
                                  bd=0, highlightthickness=0)
        self._cmp_cv.pack(fill="both", expand=True)
        self._cmp_cv.create_text(80, 50, text="选取对比图后显示",
                                  font=F["input"], fill="#334155", anchor="center")
        self._cmp_cv.bind("<Configure>", self._on_cmp_resize)

    # ── 对比逻辑 ─────────────────────────────────────────────
    def _pick_compare_image(self):
        entries = get_all_entries()
        if not entries:
            messagebox.showinfo("提示", "暂无历史图片可用于对比"); return

        win = tk.Toplevel(self.app.root)
        win.title("⚖ 选取对比图"); win.configure(bg=C["bg"])
        win.resizable(True, True); win.minsize(700, 500)
        win.update_idletasks()
        ww, wh = 980, 720
        x = self.app.root.winfo_x() + (self.app.root.winfo_width()  - ww) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - wh) // 2
        win.geometry(f"{ww}x{wh}+{max(0,x)}+{max(0,y)}")
        win.grab_set()

        # ── 标题栏 ───────────────────────────────────────────
        hdr = tk.Frame(win, bg=C["acc"]); hdr.pack(fill="x")
        tk.Label(hdr, text="⚖  选取对比图（从历史记录）",
                 font=F["h2"], bg=C["acc"], fg="white"
                 ).pack(side="left", padx=14, pady=10)
        tk.Button(hdr, text="📁 " + _("btn_export").strip(),
                  font=F["body"], bg=C["hl"], fg="white",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=lambda: self._pick_cmp_file(win)
                  ).pack(side="right", padx=12, pady=8)
        tk.Label(hdr, text=f"共 {len(entries)} 张 · 滚轮滑动",
                 font=F["small"], bg=C["acc"], fg="#93c5fd"
                 ).pack(side="right", padx=4)

        # ── 可滚动网格区域 ────────────────────────────────────
        outer = tk.Frame(win, bg=C["bg"]); outer.pack(fill="both", expand=True)
        cv    = tk.Canvas(outer, bg=C["bg"], bd=0, highlightthickness=0)
        vsb   = ttk.Scrollbar(outer, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y"); cv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(cv, bg=C["bg"])
        _w2   = cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",    lambda e: cv.itemconfig(_w2, width=e.width))

        # 滚轮：绑到 win 级别，在窗口内任意位置均可滚动
        def _wheel(ev):
            try: cv.yview_scroll(int(-1 * (ev.delta / 120)), "units")
            except tk.TclError: pass
        def _wheel_linux(ev):
            try: cv.yview_scroll(-1 if ev.num == 4 else 1, "units")
            except tk.TclError: pass
        win.bind_all("<MouseWheel>", _wheel)
        win.bind_all("<Button-4>",   _wheel_linux)
        win.bind_all("<Button-5>",   _wheel_linux)
        win.protocol("WM_DELETE_WINDOW", lambda: (
            win.unbind_all("<MouseWheel>"),
            win.unbind_all("<Button-4>"),
            win.unbind_all("<Button-5>"),
            win.destroy()))

        # ── 网格参数 ──────────────────────────────────────────
        COLS  = 4
        THUMB = 160     # 缩略图尺寸

        # Bug2 修复：
        # 旧代码 _tc = {} 是方法内局部变量，所有线程回调执行完毕后
        # Python GC 发现无活跃引用即释放 _tc，连带释放其中所有
        # PhotoImage —— Tkinter 的 C 层不计入 Python 引用计数，
        # 因此 Label 图像变黑。
        # 修复：将缓存绑定到 win 对象，生命周期与窗口相同。
        win._photo_cache = {}   # {path: PhotoImage}，跟随窗口存活

        def _select(path, dialog):
            dialog.unbind_all("<MouseWheel>")
            dialog.unbind_all("<Button-4>")
            dialog.unbind_all("<Button-5>")
            if path and os.path.exists(path):
                with open(path, "rb") as _fh:
                    data = _fh.read()
                self._set_compare_image(data)
            dialog.destroy()

        for i, e in enumerate(entries):
            path  = e.get("image_path", "")
            ri, ci = divmod(i, COLS)
            inner.columnconfigure(ci, weight=1)

            # 格子容器
            cell = tk.Frame(inner, bg=C["panel"],
                            highlightbackground="#2a3a5a",
                            highlightthickness=1)
            cell.grid(row=ri, column=ci, padx=5, pady=5, sticky="nsew")
            cell.columnconfigure(0, weight=1)

            # 缩略图标签（居中，固定占位）
            img_host = tk.Frame(cell, bg="#0f172a", width=THUMB, height=THUMB)
            img_host.pack(padx=8, pady=(8, 0))
            img_host.pack_propagate(False)
            lbl = tk.Label(img_host, bg="#0f172a",
                           text="⏳", font=F["disp_lg"], fg="#334155")
            lbl.pack(expand=True)

            # 异步加载缩略图
            # PhotoImage 必须在主线程创建（Tcl 限制），
            # 并存入 win._photo_cache 防止被 GC 回收。
            def _load_t(p=path, l=lbl):
                def _worker():
                    try:
                        if p and os.path.exists(p):
                            img = Image.open(p)
                            img.thumbnail((THUMB - 8, THUMB - 8), Image.LANCZOS)
                            canvas_img = Image.new(
                                "RGB", (THUMB - 8, THUMB - 8), (15, 23, 42))
                            ox = (canvas_img.width  - img.width)  // 2
                            oy = (canvas_img.height - img.height) // 2
                            canvas_img.paste(img, (ox, oy))

                            # 回到主线程创建 PhotoImage（Tkinter 单线程规则）
                            # 同时写入 win._photo_cache，与窗口共存亡，不被 GC
                            def _apply(ci=canvas_img, l_=l, p_=p):
                                try:
                                    if not l_.winfo_exists(): return
                                    ph = ImageTk.PhotoImage(ci)   # 主线程创建
                                    win._photo_cache[p_] = ph     # 防 GC
                                    l_.config(image=ph, text="",
                                              width=THUMB - 8, height=THUMB - 8)
                                except Exception: pass
                            win.after(0, _apply)
                        else:
                            def _empty(l_=l):
                                try:
                                    if l_.winfo_exists():
                                        l_.config(text="🖼", font=F["display"])
                                except Exception: pass
                            win.after(0, _empty)
                    except Exception: pass
                threading.Thread(target=_worker, daemon=True).start()
            _load_t()

            # 标题（显示更多字符，换行显示）
            title = self.app._display_title(e)
            ts    = e.get("timestamp", "")[:16]
            prov  = (e.get("provider") or "")[-22:]

            tk.Label(cell,
                     text=title[:36],
                     font=F["body_b"],
                     bg=C["panel"], fg=C["text"],
                     wraplength=THUMB + 10,
                     justify="center"
                     ).pack(pady=(6, 0), padx=6)
            tk.Label(cell,
                     text=f"{ts}\n{prov}",
                     font=F["mono_tiny"],
                     bg=C["panel"], fg=C["sub"],
                     justify="center"
                     ).pack(pady=(2, 0))

            # 选取按钮
            tk.Button(cell,
                      text="✅ 选取此图",
                      font=F["body_b"],
                      bg="#7c3aed", fg="white",
                      bd=0, padx=14, pady=5,
                      cursor="hand2",
                      activebackground="#5b21b6",
                      command=lambda p=path: _select(p, win)
                      ).pack(pady=(6, 10))

    def _pick_cmp_file(self, dialog):
        path = filedialog.askopenfilename(
            title="选取对比图片",
            filetypes=[("图片", "*.png *.jpg *.jpeg *.webp"), ("所有文件", "*.*")])
        if path:
            with open(path, "rb") as _fh:
                data = _fh.read()
            self._set_compare_image(data)
        dialog.destroy()

    def _set_compare_image(self, data: bytes):
        self._cmp_orig = Image.open(io.BytesIO(data))
        self._cmp_mode = True
        self._prev_host.columnconfigure(0, weight=1)
        self._prev_host.columnconfigure(2, weight=1)
        # 显示 A 侧横幅（pack 在 canvas 上方）
        self._cmp_label_a.pack(fill="x", before=self._prev_cv)
        # 显示分隔线 & B 侧
        self._cmp_divider.grid(row=0, column=1, sticky="ns")
        self._cmp_right_wrap.grid(row=0, column=2, sticky="nsew")
        self._cmp_clear_btn.config(state="normal")
        self._render_cmp()

    def _clear_compare(self):
        self._cmp_orig = None; self._cmp_mode = False
        self._cmp_label_a.pack_forget()
        self._cmp_divider.grid_remove()
        self._cmp_right_wrap.grid_remove()
        self._cmp_clear_btn.config(state="disabled")

    def _render_cmp(self):
        if self._cmp_orig is None: return
        self._cmp_cv.update_idletasks()
        cw = self._cmp_cv.winfo_width()  or 300
        ch = self._cmp_cv.winfo_height() or 400
        img = self._cmp_orig.copy(); img.thumbnail((cw - 4, ch - 4), Image.LANCZOS)
        self._cmp_photo = ImageTk.PhotoImage(img)
        self._cmp_cv.delete("all")
        self._cmp_cv.create_image(cw // 2, ch // 2,
                                   image=self._cmp_photo, anchor="center")

    def _on_cmp_resize(self, event):
        if hasattr(self, '_cmp_resize_timer') and self._cmp_resize_timer:
            self.app.root.after_cancel(self._cmp_resize_timer)
        self._cmp_resize_timer = self.app.root.after(50, self._render_cmp)

    def _set_cmp_from_entry(self, e: dict):
        path = e.get("image_path", "")
        if path and os.path.exists(path):
            with open(path, "rb") as _fh:
                data = _fh.read()
            self._set_compare_image(data)
            self._nb.select(0)
            self.app._st(f"⚖ 已设置对比图：{self.app._display_title(e)}", "ok")

    def _on_prev_resize(self, event):
        if hasattr(self, '_prev_resize_timer') and self._prev_resize_timer:
            self.app.root.after_cancel(self._prev_resize_timer)
        self._prev_resize_timer = self.app.root.after(50, self._render_preview)

    def _render_preview(self):
        if self._prev_orig is None: return
        self._prev_cv.update_idletasks()
        cw = self._prev_cv.winfo_width()  or 600
        ch = self._prev_cv.winfo_height() or 400
        img = self._prev_orig.copy(); img.thumbnail((cw - 4, ch - 4), Image.LANCZOS)
        self._prev_photo = ImageTk.PhotoImage(img)
        self._prev_cv.delete("prev")
        self._prev_cv.itemconfig(self._prev_ph, text="")
        self._prev_item = self._prev_cv.create_image(
            cw // 2, ch // 2, image=self._prev_photo, anchor="center", tags="prev")

    def _set_preview(self, data: bytes):
        self._prev_orig = Image.open(io.BytesIO(data)); self._render_preview()

    def _show_file(self, path: str):
        if path and os.path.exists(path):
            with open(path, "rb") as _fh:
                data = _fh.read()
            self.app._cur_bytes = data; self._set_preview(data)

    def _update_char_count(self):
        """更新输入框字符计数标签（公开，供 PhrasePanel 等外部调用）。"""
        try:
            txt = self.pt.get("1.0", "end-1c")   # end-1c 排除末尾隐式换行
            n   = len(txt)
            color = (C["ok"]   if n < 200
                     else C["warn"] if n < 400
                     else C["hl"])
            self._char_lbl.config(text=_("lbl_chars", n=n), fg=color)
        except Exception:
            pass
