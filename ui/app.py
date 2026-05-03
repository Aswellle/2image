"""
ui/app.py — Tkinter 主窗口
多面板：生成(txt2img) / 图生图(img2img) / 历史 / 设置
"""
import io, os, sys, tempfile, threading, webbrowser
from datetime import datetime
from functools import partial
from tkinter import (
    ANCHOR, BooleanVar, Button, Canvas, Checkbutton, END, Entry, filedialog,
    Frame, HORIZONTAL, IntVar, Label, Listbox, Menu, Message, OptionMenu,
    PhotoImage, Scrollbar, StringVar, Text, Tk, Toplevel, VERTICAL, messagebox,
    ttk,
)
from tkinter.font import Font
from PIL import Image as PILImage, ImageTk

# 本地模块
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.settings import load_config, save_config
from data.repository import HistoryRepository
from services.image_service import generate_image, generate_image_img2img, save_image_file
from services.logger import get_log_content, clear_log


# ─── 配色 ────────────────────────────────────────────────────────────
BG       = "#1e1e2e"
FG       = "#cdd6f4"
ACCENT   = "#cba6f7"
BTN_BG   = "#313244"
BTN_HV   = "#45475a"
SEL_BG   = "#585b70"
RED      = "#f38ba8"
GREEN    = "#a6e3a1"
YELLOW   = "#f9e2af"
INFO_BG  = "#11111b"
CANVAS_W = 512
CANVAS_H = 512


def rgb(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"


class ToolBar(Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG, height=48)
        self.app = app
        self.pack(side="top", fill="x")
        self.create_widgets()

    def create_widgets(self):
        style = {"bg": BG, "fg": FG, "font": ("Segoe UI", 11), "bd": 0,
                 "activebackground": BTN_HV, "activeforeground": FG,
                 "relief": "flat", "padx": 16, "pady": 8}
        titles = [("📝 文生图",  "tab_txt2img"),
                   ("🔄 图生图",  "tab_img2img"),
                   ("📚 历史",    "tab_history"),
                   ("⚙️  设置",   "tab_settings")]
        for emoji, tab_id in titles:
            btn = Button(self, text=emoji, cnf=style,
                         command=lambda t=tab_id: self.app.switch_tab(t))
            btn.pack(side="left", padx=2)


class Txt2ImgPanel(Frame):
    """文生图主面板"""
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self._build()
        self.current_image_bytes = None

    def _build(self):
        left  = Frame(self, bg=BG)
        right = Frame(self, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # 提示词
        Label(left, text="🎨 提示词", bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.prompt_var = StringVar()
        prompt_entry = Entry(left, textvariable=self.prompt_var, bg=BTN_BG,
                             fg=FG, insertbackground=FG, relief="flat",
                             font=("Segoe UI", 11))
        prompt_entry.pack(fill="x", pady=(2, 8), ipady=4)

        # 底色提示词
        Label(left, text="🚫 负面提示词（可选）", bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.neg_var = StringVar()
        Entry(left, textvariable=self.neg_var, bg=BTN_BG,
              fg=FG, insertbackground=FG, relief="flat",
              font=("Segoe UI", 10)).pack(fill="x", pady=(2, 8), ipady=4)

        # 尺寸
        size_frame = Frame(left, bg=BG)
        size_frame.pack(fill="x", pady=4)
        Label(size_frame, text="宽", bg=BG, fg=FG).pack(side="left")
        self.w_var = IntVar(value=512)
        Entry(size_frame, textvariable=self.w_var, bg=BTN_BG, fg=FG,
              width=8, relief="flat").pack(side="left", padx=4)
        Label(size_frame, text="高", bg=BG, fg=FG).pack(side="left", padx=(12, 4))
        self.h_var = IntVar(value=512)
        Entry(size_frame, textvariable=self.h_var, bg=BTN_BG, fg=FG,
              width=8, relief="flat").pack(side="left")

        # Seed
        seed_frame = Frame(left, bg=BG)
        seed_frame.pack(fill="x", pady=4)
        Label(seed_frame, text="Seed（留空随机）", bg=BG, fg=FG).pack(side="left")
        self.seed_var = IntVar(value=0)
        Entry(seed_frame, textvariable=self.seed_var, bg=BTN_BG, fg=FG,
              width=12, relief="flat").pack(side="right")

        # 生成按钮
        self.gen_btn = Button(left, text="🚀 生成图片",
                              bg=ACCENT, fg="#1e1e2e",
                              font=("Segoe UI", 12, "bold"),
                              relief="flat", padx=20, pady=8,
                              command=self._on_generate)
        self.gen_btn.pack(fill="x", pady=10, ipady=6)

        # 状态标签
        self.status_var = StringVar(value="就绪")
        Label(left, textvariable=self.status_var, bg=BG, fg=GREEN,
              font=("Segoe UI", 10)).pack(anchor="w")

        # 图片预览
        Label(right, text="🖼️  预览", bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.canvas = Canvas(right, width=CANVAS_W, height=CANVAS_H,
                            bg=INFO_BG, highlightthickness=0)
        self.canvas.pack(pady=6)
        self.canvas_image = None

        # 保存按钮
        save_frame = Frame(right, bg=BG)
        save_frame.pack(fill="x", pady=4)
        Button(save_frame, text="💾 保存本地",
               bg=BTN_BG, fg=FG, relief="flat",
               command=self._save).pack(side="left", padx=2)
        Button(save_frame, text="🖼️ 打开文件夹",
               bg=BTN_BG, fg=FG, relief="flat",
               command=lambda: os.startfile(os.path.dirname(
                   self.app.last_saved_path or "."))).pack(side="left", padx=2)

    def _on_generate(self):
        prompt = self.prompt_var.get().strip()
        if not prompt:
            messagebox.showwarning("提示", "请输入提示词！")
            return
        w = max(256, min(2048, self.w_var.get()))
        h = max(256, min(2048, self.h_var.get()))
        seed = self.seed_var.get() or None
        self.gen_btn.config(state="disabled", text="生成中…")
        self.status_var.set("⏳ 正在生成…")

        def work():
            try:
                cfg = load_config()
                data, used = generate_image(
                    prompt, w, h, seed, cfg,
                    status_cb=lambda s: self.app.after(0,
                        lambda: self.status_var.set(s)),
                )
                self.current_image_bytes = data
                path = save_image_file(data, prompt)
                self.app.last_saved_path = path
                self.app.after(0, lambda: self._show(data, used, path))
            except Exception as e:
                self.app.after(0, lambda: self.status_var.set(f"✗ {e}"))
            finally:
                self.app.after(0, lambda: self.gen_btn.config(
                    state="normal", text="🚀 生成图片"))

        threading.Thread(target=work, daemon=True).start()

    def _show(self, data, used, path):
        try:
            img = PILImage.open(io.BytesIO(data))
            img.thumbnail((CANVAS_W, CANVAS_H), PILImage.LANCZOS)
            self.tk_img = ImageTk.PhotoImage(img)
            if self.canvas_image:
                self.canvas.delete(self.canvas_image)
            self.canvas_image = self.canvas.create_image(
                CANVAS_W//2, CANVAS_H//2, image=self.tk_img)
            self.status_var.set(f"✓ {used} | 已保存：{os.path.basename(path)}")
        except Exception as e:
            self.status_var.set(f"✗ 图片显示失败：{e}")

    def _save(self):
        if not self.current_image_bytes:
            messagebox.showinfo("提示", "先生成图片再保存！")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if path:
            PILImage.open(io.BytesIO(self.current_image_bytes)).save(path)
            messagebox.showinfo("保存成功", f"已保存至：{path}")


class Img2ImgPanel(Frame):
    """图生图面板"""
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self.source_bytes = None
        self._build()

    def _build(self):
        left  = Frame(self, bg=BG)
        right = Frame(self, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # 上传源图
        Label(left, text="📤 参考图", bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.src_canvas = Canvas(left, width=256, height=256,
                                  bg=INFO_BG, highlightthickness=0)
        self.src_canvas.pack(pady=6)
        Button(left, text="📂 选择参考图",
               bg=BTN_BG, fg=FG, relief="flat",
               command=self._select_source).pack(pady=4)
        self.src_label = Label(left, text="未选择", bg=BG, fg=FG,
                               font=("Segoe UI", 9))
        self.src_label.pack()

        # 提示词
        Label(left, text="🎨 提示词（描述期望结果）", bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10,2))
        self.prompt_var = StringVar()
        Entry(left, textvariable=self.prompt_var, bg=BTN_BG,
              fg=FG, insertbackground=FG, relief="flat",
              font=("Segoe UI", 11)).pack(fill="x", pady=(2,8), ipady=4)

        Label(left, text="宽 高", bg=BG, fg=FG).pack(anchor="w")
        wh_frame = Frame(left, bg=BG)
        wh_frame.pack(pady=4)
        self.w_var = IntVar(value=512)
        self.h_var = IntVar(value=512)
        Entry(wh_frame, textvariable=self.w_var, bg=BTN_BG, fg=FG,
              width=8, relief="flat").pack(side="left")
        Label(wh_frame, text="×", bg=BG, fg=FG).pack(side="left", padx=8)
        Entry(wh_frame, textvariable=self.h_var, bg=BTN_BG, fg=FG,
              width=8, relief="flat").pack(side="left")

        self.gen_btn = Button(left, text="🔄 图生图生成",
                               bg=ACCENT, fg="#1e1e2e",
                               font=("Segoe UI", 12, "bold"),
                               relief="flat", padx=20, pady=8,
                               command=self._on_generate)
        self.gen_btn.pack(fill="x", pady=10, ipady=6)
        self.status_var = StringVar(value="就绪")
        Label(left, textvariable=self.status_var, bg=BG, fg=GREEN,
              font=("Segoe UI", 10)).pack(anchor="w")

        # 预览
        Label(right, text="🖼️  结果预览", bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.canvas = Canvas(right, width=CANVAS_W, height=CANVAS_H,
                            bg=INFO_BG, highlightthickness=0)
        self.canvas.pack(pady=6)
        self.canvas_image = None
        Button(right, text="💾 保存结果",
               bg=BTN_BG, fg=FG, relief="flat",
               command=self._save).pack(pady=4)

    def _select_source(self):
        path = filedialog.askopenfilename(
            filetypes=[("图片", "*.png *.jpg *.jpeg *.webp *.bmp")])
        if not path:
            return
        with open(path, "rb") as f:
            self.source_bytes = f.read()
        try:
            img = PILImage.open(io.BytesIO(self.source_bytes))
            img.thumbnail((256, 256), PILImage.LANCZOS)
            self.src_tk = ImageTk.PhotoImage(img)
            if hasattr(self, "src_img"):
                self.src_canvas.delete(self.src_img)
            self.src_img = self.src_canvas.create_image(128, 128, image=self.src_tk)
            self.src_label.config(text=f"已选：{os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("错误", f"图片加载失败：{e}")

    def _on_generate(self):
        if not self.source_bytes:
            messagebox.showwarning("提示", "请先选择参考图！")
            return
        prompt = self.prompt_var.get().strip()
        if not prompt:
            messagebox.showwarning("提示", "请输入提示词！")
            return
        w = max(256, min(2048, self.w_var.get()))
        h = max(256, min(2048, self.h_var.get()))
        self.gen_btn.config(state="disabled", text="生成中…")
        self.status_var.set("⏳ 正在生成…")

        def work():
            try:
                cfg = load_config()
                data, used = generate_image_img2img(
                    prompt, w, h, None, self.source_bytes, cfg)
                path = save_image_file(data, prompt)
                self.app.after(0, lambda: self._show(data, used, path))
            except Exception as e:
                self.app.after(0, lambda: self.status_var.set(f"✗ {e}"))
            finally:
                self.app.after(0, lambda: self.gen_btn.config(
                    state="normal", text="🔄 图生图生成"))

        threading.Thread(target=work, daemon=True).start()

    def _show(self, data, used, path):
        try:
            img = PILImage.open(io.BytesIO(data))
            img.thumbnail((CANVAS_W, CANVAS_H), PILImage.LANCZOS)
            self.tk_img = ImageTk.PhotoImage(img)
            if self.canvas_image:
                self.canvas.delete(self.canvas_image)
            self.canvas_image = self.canvas.create_image(
                CANVAS_W//2, CANVAS_H//2, image=self.tk_img)
            self.status_var.set(f"✓ {used} | 已保存：{os.path.basename(path)}")
        except Exception as e:
            self.status_var.set(f"✗ 显示失败：{e}")

    def _save(self):
        if not hasattr(self, "tk_img"):
            messagebox.showinfo("提示", "先生成图片再保存！")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if path:
            PILImage.open(io.BytesIO(self.source_bytes)).save(path)


class HistoryPanel(Frame):
    """历史记录面板"""
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self.repo = HistoryRepository()
        self._build()

    def _build(self):
        toolbar = Frame(self, bg=BG)
        toolbar.pack(fill="x", padx=10, pady=6)
        Button(toolbar, text="🔄 刷新", bg=BTN_BG, fg=FG,
               relief="flat", command=self._refresh).pack(side="left", padx=2)
        Button(toolbar, text="🗑️ 删除选中", bg=BTN_BG, fg=RED,
               relief="flat", command=self._delete).pack(side="left", padx=2)
        self.search_var = StringVar()
        Entry(toolbar, textvariable=self.search_var, bg=BTN_BG, fg=FG,
              relief="flat", font=("Segoe UI", 10),
              insertbackground=FG).pack(side="left", padx=8, fill="x", expand=True)
        Button(toolbar, text="🔍 搜索", bg=BTN_BG, fg=FG,
               relief="flat", command=self._search).pack(side="left", padx=2)

        body = Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=4)
        self.listbox = Listbox(body, bg=INFO_BG, fg=FG, font=("Segoe UI", 10),
                               selectbackground=SEL_BG, selectforeground=FG,
                               relief="flat", highlightthickness=0)
        scroll = Scrollbar(body, orient=VERTICAL, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.listbox.bind("<Double-Button-1>", lambda _: self._open())

        self._refresh()

    def _refresh(self):
        self.listbox.delete(0, END)
        for row in self.repo.get_all(50):
            ts = row.get("created_at", "")[:16]
            p  = row.get("prompt", "")[:40]
            self.listbox.insert(END, f"{ts}  {p}…")

    def _search(self):
        q = self.search_var.get().strip()
        self.listbox.delete(0, END)
        rows = self.repo.search(q) if q else self.repo.get_all(50)
        for row in rows:
            ts = row.get("created_at", "")[:16]
            p  = row.get("prompt", "")[:40]
            self.listbox.insert(END, f"{ts}  {p}…")

    def _delete(self):
        sel = self.listbox.curselection()
        if sel:
            self.listbox.delete(sel[0])

    def _open(self):
        idx = self.listbox.index("anchor")
        rows = self.repo.get_all(50)
        if idx < len(rows):
            p = rows[idx].get("file_path", "")
            if p and os.path.exists(p):
                webbrowser.open(p)


class SettingsPanel(Frame):
    """设置面板 — API Key 配置 + Provider 优先级"""
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self.entries = {}
        self._build()

    def _build(self):
        canvas = Canvas(self, bg=BG, highlightthickness=0)
        scroll = Scrollbar(self, orient=VERTICAL, command=canvas.yview)
        inner  = Frame(canvas, bg=BG)

        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        canvas.config(yscrollcommand=scroll.set)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # API Keys 区域
        Label(inner, text="🔑 API Keys", bg=BG, fg=ACCENT,
              font=("Segoe UI", 13, "bold")).grid(
                  row=0, column=0, columnspan=2, sticky="w", pady=(8, 4))

        keys = [
            ("gemini_key",    "Google Gemini API Key"),
            ("openai_key",   "OpenAI API Key（DALL-E）"),
            ("openrouter_key","OpenRouter API Key"),
            ("together_key", "Together AI API Key"),
            ("siliconflow_key","硅基流动 API Key"),
            ("cf_account_id","Cloudflare Account ID"),
            ("cf_api_token", "Cloudflare API Token"),
            ("modelslab_key","ModelsLab API Key"),
            ("segmind_key",  "Segmind API Key"),
            ("hf_token",     "HuggingFace Token"),
            ("stability_key","Stability AI API Key"),
            ("replicate_key","Replicate Token"),
            ("xai_key",      "xAI API Key"),
            ("ideogram_key", "Ideogram API Key"),
            ("recraft_key",  "Recraft API Key"),
            ("leonardo_key", "Leonardo.ai Token"),
        ]

        row = 1
        for key_id, label in keys:
            Label(inner, text=label, bg=BG, fg=FG,
                 font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", padx=8, pady=3)
            e = Entry(inner, bg=BTN_BG, fg=FG, relief="flat",
                      font=("Segoe UI", 10), show="*" if "key" in key_id else "",
                      insertbackground=FG, width=40)
            e.grid(row=row, column=1, padx=8, pady=3)
            self.entries[key_id] = e
            row += 1

        # 默认 Provider 顺序
        Label(inner, text="⬆️ 默认 Provider 优先级", bg=BG, fg=ACCENT,
              font=("Segoe UI", 13, "bold")).grid(
                  row=row, column=0, columnspan=2, sticky="w", pady=(16, 4))
        row += 1
        Label(inner, text="（失败时按从上到下顺序自动切换）",
              bg=BG, fg=YELLOW, font=("Segoe UI", 9)).grid(
                  row=row, column=0, columnspan=2, sticky="w", padx=8)
        row += 1

        from services.providers import DEFAULT_ORDER
        self.provider_vars = {}
        for name in DEFAULT_ORDER:
            var = BooleanVar(value=True)
            self.provider_vars[name] = var
            Checkbutton(inner, text=name, variable=var,
                        bg=BG, fg=FG, selectcolor=BTN_BG,
                        activebackground=BG, activeforeground=FG,
                        font=("Segoe UI", 10)).grid(
                            row=row, column=0, columnspan=2, sticky="w", padx=16, pady=1)
            row += 1

        # 按钮
        btn_frame = Frame(inner, bg=BG)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=16)
        Button(btn_frame, text="💾 保存设置",
               bg=ACCENT, fg="#1e1e2e",
               font=("Segoe UI", 11, "bold"),
               relief="flat", padx=20, pady=6,
               command=self._save).pack(side="left", padx=6)
        Button(btn_frame, text="📋 调试日志",
               bg=BTN_BG, fg=FG, relief="flat",
               command=self._show_log).pack(side="left", padx=6)

        self._load()

    def _load(self):
        cfg = load_config()
        for key_id, e in self.entries.items():
            val = cfg.get(key_id, "")
            e.delete(0, END)
            e.insert(0, val)

    def _save(self):
        cfg = {key_id: e.get().strip() for key_id, e in self.entries.items()}
        enabled = [n for n, v in self.provider_vars.items() if v.get()]
        cfg["provider_order"] = enabled
        save_config(cfg)
        messagebox.showinfo("保存成功", "配置已保存，重启后生效！")

    def _show_log(self):
        log = get_log_content()
        win = Toplevel(self)
        win.title("调试日志")
        win.geometry("700x400")
        txt = Text(win, bg=INFO_BG, fg=GREEN, font=("Consolas", 9),
                   relief="flat", wrap="none")
        txt.insert("1.0", log or "（无日志）")
        txt.config(state="disabled")
        Scrollbar(win, orient=HORIZONTAL, command=txt.xview).pack(side="bottom", fill="x")
        Scrollbar(win, orient=VERTICAL, command=txt.yview).pack(side="right", fill="y")
        txt.config(xscrollcommand=Scrollbar(win, orient=HORIZONTAL).set)
        txt.pack(fill="both", expand=True)


class App(Tk):
    def __init__(self):
        super().__init__()
        self.title("2image — 文生图 / 图生图")
        self.configure(bg=BG)
        self.last_saved_path = None
        self._set_dpi()
        self._build()

    def _set_dpi(self):
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    def _build(self):
        # 顶部工具栏
        self.toolbar = ToolBar(self, self)

        # 标签页容器
        self.tabs = {}
        self.tab_container = Frame(self, bg=BG)
        self.tab_container.pack(fill="both", expand=True)

        for tab_id, panel_cls in [
            ("tab_txt2img",  Txt2ImgPanel),
            ("tab_img2img",  Img2ImgPanel),
            ("tab_history",  HistoryPanel),
            ("tab_settings", SettingsPanel),
        ]:
            panel = panel_cls(self.tab_container, self)
            panel.pack(fill="both", expand=True)
            self.tabs[tab_id] = panel

        self.switch_tab("tab_txt2img")

    def switch_tab(self, tab_id):
        for tid, panel in self.tabs.items():
            panel.pack_forget()
        self.tabs[tab_id].pack(fill="both", expand=True)
