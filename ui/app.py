"""
ui/app.py — Tkinter 主窗口
多面板：生成(txt2img) / 图生图(img2img) / 历史 / 设置
"""
import io, os, sys, tempfile, threading, webbrowser
from datetime import datetime
from functools import partial
from tkinter import (
    ANCHOR, BooleanVar, Button, Canvas, Checkbutton, DoubleVar, END, Entry, filedialog,
    Frame, HORIZONTAL, IntVar, Label, Listbox, Menu, Message, OptionMenu,
    PhotoImage, Scale, Scrollbar, StringVar, Text, Tk, Toplevel, VERTICAL, messagebox,
    ttk,
)
from tkinter.font import Font
from PIL import Image as PILImage, ImageTk

# 本地模块
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.settings import load_config, save_config
from data.repository import HistoryRepository, add_entry, delete_entry
from services.image_service import generate_image, generate_image_img2img, save_image_file
from services.i18n import get_text, format
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
        titles = [(get_text("tabs.txt2img"),  "tab_txt2img"),
                  (get_text("tabs.img2img"),  "tab_img2img"),
                  (get_text("tabs.history"),  "tab_history"),
                  (get_text("tabs.settings"), "tab_settings")]
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
        Label(left, text=get_text("txt2img.prompt"), bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.prompt_var = StringVar()
        prompt_entry = Entry(left, textvariable=self.prompt_var, bg=BTN_BG,
                             fg=FG, insertbackground=FG, relief="flat",
                             font=("Segoe UI", 11))
        prompt_entry.pack(fill="x", pady=(2, 8), ipady=4)

        # 底色提示词
        Label(left, text=get_text("txt2img.negative_prompt"), bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.neg_var = StringVar()
        Entry(left, textvariable=self.neg_var, bg=BTN_BG,
              fg=FG, insertbackground=FG, relief="flat",
              font=("Segoe UI", 10)).pack(fill="x", pady=(2, 8), ipady=4)

        # 尺寸
        size_frame = Frame(left, bg=BG)
        size_frame.pack(fill="x", pady=4)
        Label(size_frame, text=get_text("txt2img.width"), bg=BG, fg=FG).pack(side="left")
        self.w_var = IntVar(value=512)
        Entry(size_frame, textvariable=self.w_var, bg=BTN_BG, fg=FG,
              width=8, relief="flat").pack(side="left", padx=4)
        Label(size_frame, text=get_text("txt2img.height"), bg=BG, fg=FG).pack(side="left", padx=(12, 4))
        self.h_var = IntVar(value=512)
        Entry(size_frame, textvariable=self.h_var, bg=BTN_BG, fg=FG,
              width=8, relief="flat").pack(side="left")

        # Seed
        seed_frame = Frame(left, bg=BG)
        seed_frame.pack(fill="x", pady=4)
        Label(seed_frame, text=get_text("txt2img.seed"), bg=BG, fg=FG).pack(side="left")
        self.seed_var = IntVar(value=0)
        Entry(seed_frame, textvariable=self.seed_var, bg=BTN_BG, fg=FG,
              width=12, relief="flat").pack(side="right")

        # 生成按钮
        self.gen_btn = Button(left, text=get_text("txt2img.generate_btn"),
                              bg=ACCENT, fg="#1e1e2e",
                              font=("Segoe UI", 12, "bold"),
                              relief="flat", padx=20, pady=8,
                              command=self._on_generate)
        self.gen_btn.pack(fill="x", pady=10, ipady=6)

        # 状态标签
        self.status_var = StringVar(value=get_text("app.ready"))
        Label(left, textvariable=self.status_var, bg=BG, fg=GREEN,
              font=("Segoe UI", 10)).pack(anchor="w")

        # 图片预览
        Label(right, text=get_text("txt2img.preview"), bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.canvas = Canvas(right, width=CANVAS_W, height=CANVAS_H,
                            bg=INFO_BG, highlightthickness=0)
        self.canvas.pack(pady=6)
        self.canvas_image = None

        # 保存按钮
        save_frame = Frame(right, bg=BG)
        save_frame.pack(fill="x", pady=4)
        Button(save_frame, text=get_text("txt2img.save_local"),
               bg=BTN_BG, fg=FG, relief="flat",
               command=self._save).pack(side="left", padx=2)
        Button(save_frame, text=get_text("txt2img.open_folder"),
               bg=BTN_BG, fg=FG, relief="flat",
               command=lambda: os.startfile(os.path.dirname(
                   self.app.last_saved_path or "."))).pack(side="left", padx=2)

    def _on_generate(self):
        prompt = self.prompt_var.get().strip()
        if not prompt:
            messagebox.showwarning(get_text("app.title"), get_text("txt2img.prompt_required"))
            return
        w = max(256, min(2048, self.w_var.get()))
        h = max(256, min(2048, self.h_var.get()))
        seed = self.seed_var.get() or None
        self.gen_btn.config(state="disabled", text=get_text("app.generate_disabled"))
        self.status_var.set(get_text("app.generating"))

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
                # 写入 SQLite 历史记录
                add_entry(
                    prompt=prompt,
                    translated="",
                    image_path=path,
                    provider=used,
                    is_img2img=False,
                )
                self.app.after(0, lambda: self._show(data, used, path))
            except Exception as e:
                self.app.after(0, lambda: self.status_var.set(f"✗ {e}"))
            finally:
                self.app.after(0, lambda: self.gen_btn.config(
                    state="normal", text=get_text("txt2img.generate_btn")))

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
            self.status_var.set(format("app.success", provider=used, filename=os.path.basename(path)))
        except Exception as e:
            self.status_var.set(format("app.error", message=f"图片显示失败：{e}"))

    def _save(self):
        if not self.current_image_bytes:
            messagebox.showinfo(get_text("app.title"), get_text("txt2img.save_first"))
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if path:
            PILImage.open(io.BytesIO(self.current_image_bytes)).save(path)
            messagebox.showinfo(get_text("app.saved_ok"), format("app.saved_to", path=path))


class Img2ImgPanel(Frame):
    """图生图面板（v1.1 增强版）"""
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self.source_bytes = None
        self.current_result_bytes = None
        self._build()

    def _build(self):
        left  = Frame(self, bg=BG)
        right = Frame(self, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # ── 参考图上传 ───────────────────────────────────────────
        Label(left, text=get_text("img2img.source_image"), bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.src_canvas = Canvas(left, width=256, height=256,
                                  bg=INFO_BG, highlightthickness=0)
        self.src_canvas.pack(pady=6)
        Button(left, text=get_text("img2img.select_source"),
               bg=BTN_BG, fg=FG, relief="flat",
               command=self._select_source).pack(pady=4)
        self.src_label = Label(left, text=get_text("img2img.no_source"), bg=BG, fg=FG,
                               font=("Segoe UI", 9))
        self.src_label.pack()

        # ── 提示词 ──────────────────────────────────────────────
        Label(left, text=get_text("img2img.prompt"), bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 2))
        self.prompt_var = StringVar()
        Entry(left, textvariable=self.prompt_var, bg=BTN_BG,
              fg=FG, insertbackground=FG, relief="flat",
              font=("Segoe UI", 11)).pack(fill="x", pady=(2, 8), ipady=4)

        # ── 尺寸 ────────────────────────────────────────────────
        Label(left, text=get_text("img2img.width_height"), bg=BG, fg=FG).pack(anchor="w")
        wh_frame = Frame(left, bg=BG)
        wh_frame.pack(pady=4)
        self.w_var = IntVar(value=512)
        self.h_var = IntVar(value=512)
        Entry(wh_frame, textvariable=self.w_var, bg=BTN_BG, fg=FG,
              width=8, relief="flat").pack(side="left")
        Label(wh_frame, text="×", bg=BG, fg=FG).pack(side="left", padx=8)
        Entry(wh_frame, textvariable=self.h_var, bg=BTN_BG, fg=FG,
              width=8, relief="flat").pack(side="left")

        # ── ControlNet 模式选择（v2.0 P3）────────────────────────────
        Label(left, text=get_text("img2img.control_mode"), bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 2))
        Label(left, text=get_text("img2img.control_mode_hint"), bg=BG, fg=YELLOW,
              font=("Segoe UI", 8)).pack(anchor="w")

        control_frame = Frame(left, bg=BG)
        control_frame.pack(fill="x", pady=2)
        self.control_var = StringVar(value="none")

        control_options = [
            (get_text("img2img.control_none"),     "none"),
            (get_text("img2img.control_canny"),    "canny"),
            (get_text("img2img.control_openpose"), "openpose"),
            (get_text("img2img.control_depth"),    "depth"),
        ]
        self.control_menu = OptionMenu(control_frame, self.control_var,
                                        *[opt[0] for opt in control_options])
        self.control_menu.config(bg=BTN_BG, fg=FG, font=("Segoe UI", 10),
                                 relief="flat", width=22)
        self.control_menu["menu"].config(bg=BTN_BG, fg=FG)
        self.control_menu.pack(side="left")

        # ── 变化强度滑块 ─────────────────────────────────────────
        Label(left, text=get_text("img2img.strength"), bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 2))

        strength_frame = Frame(left, bg=BG)
        strength_frame.pack(fill="x", pady=2)
        self.strength_var = DoubleVar(value=0.7)

        def _update_strength_label(v):
            s = float(v)
            label_key = "img2img.strength_light" if s < 0.35 else "img2img.strength_medium" if s < 0.65 else "img2img.strength_heavy"
            self.strength_label.config(text=format("img2img.strength_display",
                                                   value=f"{s:.1f}",
                                                   label=get_text(label_key)))

        self.strength_scale = Scale(strength_frame, from_=0.1, to=0.9,
                                     orient=HORIZONTAL, variable=self.strength_var,
                                     command=_update_strength_label,
                                     bg=BG, fg=FG, troughcolor=BTN_BG,
                                     highlightthickness=0,
                                     sliderrelief="flat", length=200,
                                     digits=2, resolution=0.1)
        self.strength_scale.pack(side="left")

        self.strength_label = Label(strength_frame, text=format("img2img.strength_display",
                                                                  value="0.7",
                                                                  label=get_text("img2img.strength_medium")),
                                     bg=BG, fg=YELLOW, font=("Segoe UI", 9))
        self.strength_label.pack(side="left", padx=6)

        # 强度预设快捷按钮
        presets = [(get_text("img2img.preset_light"), 0.3),
                   (get_text("img2img.preset_medium"), 0.7),
                   (get_text("img2img.preset_heavy"), 0.9)]
        preset_frame = Frame(left, bg=BG)
        preset_frame.pack(fill="x", pady=(2, 6))
        for label_text, val in presets:
            btn = Button(preset_frame, text=label_text,
                         bg=BTN_BG, fg=FG, relief="flat",
                         font=("Segoe UI", 9),
                         command=lambda v=val: (self.strength_var.set(v),
                                                self.strength_scale.set(v),
                                                _update_strength_label(v)))
            btn.pack(side="left", padx=2)

        # ── Provider 选择 ────────────────────────────────────────
        Label(left, text=get_text("img2img.provider"), bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(6, 2))

        self.provider_var = StringVar(value=get_text("img2img.provider_auto"))
        provider_frame = Frame(left, bg=BG)
        provider_frame.pack(fill="x", pady=2)

        # 动态加载 img2img provider 列表
        from services.image_service import _load_img2img_providers, IMG2IMG_PROVIDERS
        _load_img2img_providers()
        provider_options = [get_text("img2img.provider_auto")] + list(IMG2IMG_PROVIDERS.keys())

        self.provider_menu = OptionMenu(provider_frame, self.provider_var,
                                        *provider_options)
        self.provider_menu.config(bg=BTN_BG, fg=FG, font=("Segoe UI", 10),
                                  relief="flat", width=22)
        self.provider_menu["menu"].config(bg=BTN_BG, fg=FG)
        self.provider_menu.pack(side="left")

        # ── 生成按钮 + 状态 ───────────────────────────────────────
        self.gen_btn = Button(left, text=get_text("img2img.generate_btn"),
                               bg=ACCENT, fg="#1e1e2e",
                               font=("Segoe UI", 12, "bold"),
                               relief="flat", padx=20, pady=8,
                               command=self._on_generate)
        self.gen_btn.pack(fill="x", pady=10, ipady=6)
        self.status_var = StringVar(value=get_text("app.ready"))
        Label(left, textvariable=self.status_var, bg=BG, fg=GREEN,
              font=("Segoe UI", 10)).pack(anchor="w")

        # ── 右侧：结果预览 ────────────────────────────────────────
        Label(right, text=get_text("img2img.preview"), bg=BG, fg=ACCENT,
              font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.canvas = Canvas(right, width=CANVAS_W, height=CANVAS_W,
                            bg=INFO_BG, highlightthickness=0)
        self.canvas.pack(pady=6)
        self.canvas_image = None

        save_frame = Frame(right, bg=BG)
        save_frame.pack(fill="x", pady=4)
        Button(save_frame, text=get_text("img2img.save_result"),
               bg=BTN_BG, fg=FG, relief="flat",
               command=self._save).pack(side="left", padx=2)
        Button(save_frame, text=get_text("img2img.open_folder"),
               bg=BTN_BG, fg=FG, relief="flat",
               command=lambda: os.startfile(os.path.dirname(
                   self.app.last_saved_path or "."))).pack(side="left", padx=2)

    def _select_source(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp")])
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
            self.src_label.config(text=format("img2img.source_selected", filename=os.path.basename(path)))
        except Exception as e:
            messagebox.showerror(get_text("app.error"), format("img2img.source_load_error", error=str(e)))

    def _on_generate(self):
        if not self.source_bytes:
            messagebox.showwarning(get_text("app.title"), get_text("img2img.source_required"))
            return
        prompt = self.prompt_var.get().strip()
        if not prompt:
            messagebox.showwarning(get_text("app.title"), get_text("img2img.prompt_required"))
            return
        w = max(256, min(2048, self.w_var.get()))
        h = max(256, min(2048, self.h_var.get()))
        strength = round(self.strength_var.get(), 2)

        # ControlNet 模式：把显示文字映射回内部值
        control_options = [
            ("none",     get_text("img2img.control_none")),
            ("canny",    get_text("img2img.control_canny")),
            ("openpose", get_text("img2img.control_openpose")),
            ("depth",    get_text("img2img.control_depth")),
        ]
        control_map = {label: key for key, label in control_options}
        control_mode = control_map.get(self.control_var.get(), "none")

        # Provider 选择："自动" = None（走默认顺序），否则只尝试指定 provider
        selected = self.provider_var.get()
        provider_order = None if selected == get_text("img2img.provider_auto") else [selected]

        self.gen_btn.config(state="disabled", text=get_text("app.img2img_disabled"))
        self.status_var.set(get_text("app.generating"))

        def work():
            try:
                cfg = load_config()
                data, used = generate_image_img2img(
                    prompt, w, h, None, self.source_bytes, cfg,
                    strength=strength,
                    control_mode=control_mode,
                    provider_order=provider_order,
                    status_cb=lambda s: self.app.after(0,
                        lambda msg=s: self.status_var.set(msg)),
                )
                path = save_image_file(data, prompt)
                self.app.last_saved_path = path
                # 写入 SQLite 历史记录（含 img2img 标记和参考图路径）
                add_entry(
                    prompt=prompt,
                    translated="",
                    image_path=path,
                    provider=used,
                    is_img2img=True,
                    source_img="[in-memory-bytes]",  # 源图为内存字节，不存路径
                )
                self.app.after(0, lambda: self._show(data, used, path))
            except Exception as e:
                self.app.after(0, lambda: self.status_var.set(f"✗ {e}"))
            finally:
                self.app.after(0, lambda: self.gen_btn.config(
                    state="normal", text=get_text("img2img.generate_btn")))

        threading.Thread(target=work, daemon=True).start()

    def _show(self, data, used, path):
        try:
            self.current_result_bytes = data   # 保存原始字节，供 _save() 使用
            img = PILImage.open(io.BytesIO(data))
            img.thumbnail((CANVAS_W, CANVAS_H), PILImage.LANCZOS)
            self.tk_img = ImageTk.PhotoImage(img)
            if self.canvas_image:
                self.canvas.delete(self.canvas_image)
            self.canvas_image = self.canvas.create_image(
                CANVAS_W//2, CANVAS_H//2, image=self.tk_img)
            self.status_var.set(format("app.success", provider=used, filename=os.path.basename(path)))
        except Exception as e:
            self.status_var.set(format("img2img.display_failed", error=str(e)))

    def _save(self):
        if not self.current_result_bytes:
            messagebox.showinfo(get_text("app.title"), get_text("img2img.generate_first"))
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if path:
            PILImage.open(io.BytesIO(self.current_result_bytes)).save(path)


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
        Button(toolbar, text=get_text("history.refresh"), bg=BTN_BG, fg=FG,
               relief="flat", command=self._refresh).pack(side="left", padx=2)
        Button(toolbar, text=get_text("history.delete"), bg=BTN_BG, fg=RED,
               relief="flat", command=self._delete).pack(side="left", padx=2)
        self.search_var = StringVar()
        Entry(toolbar, textvariable=self.search_var, bg=BTN_BG, fg=FG,
              relief="flat", font=("Segoe UI", 10),
              insertbackground=FG).pack(side="left", padx=8, fill="x", expand=True)
        Button(toolbar, text=get_text("history.search"), bg=BTN_BG, fg=FG,
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
        if not sel:
            return
        idx = sel[0]
        # 根据 Listbox 当前显示顺序找到对应的数据库记录
        rows = self.repo.get_all(50)
        if idx < len(rows):
            entry_id = rows[idx].get("id")
            if entry_id:
                # 同时从 SQLite 删除记录（文件可选保留）
                delete_entry(entry_id, remove_file=False)
        self.listbox.delete(idx)

    def _open(self):
        """双击打开图片：用系统默认图片查看器"""
        idx = self.listbox.index("anchor")
        rows = self.repo.get_all(50)
        if idx < len(rows):
            p = rows[idx].get("image_path", "")
            if p and os.path.exists(p):
                webbrowser.open(p) if sys.platform != "win32" else os.startfile(p)
            else:
                messagebox.showwarning(get_text("app.title"), get_text("history.file_not_exist"))


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
        Label(inner, text=get_text("settings.api_keys"), bg=BG, fg=ACCENT,
              font=("Segoe UI", 13, "bold")).grid(
                  row=0, column=0, columnspan=2, sticky="w", pady=(8, 4))

        keys = [
            ("gemini_key",    "Google Gemini API Key"),
            ("openai_key",   "OpenAI API Key (DALL-E)"),
            ("openrouter_key","OpenRouter API Key"),
            ("together_key", "Together AI API Key"),
            ("siliconflow_key","siliconflow_key"),
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
            display = get_text(f"settings.{key_id}") if not key_id.startswith(("cf_", "hf_", "replicate", "xai", "ideogram", "recraft", "leonardo", "gemini", "openai", "openrouter", "together", "modelslab", "segmind", "stability")) else label
            if key_id == "siliconflow_key":
                display = get_text("settings.siliconflow_key")
            Label(inner, text=display, bg=BG, fg=FG,
                 font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", padx=8, pady=3)
            e = Entry(inner, bg=BTN_BG, fg=FG, relief="flat",
                      font=("Segoe UI", 10), show="*" if "key" in key_id else "",
                      insertbackground=FG, width=40)
            e.grid(row=row, column=1, padx=8, pady=3)
            self.entries[key_id] = e
            row += 1

        # 默认 Provider 顺序
        Label(inner, text=get_text("settings.provider_priority"), bg=BG, fg=ACCENT,
              font=("Segoe UI", 13, "bold")).grid(
                  row=row, column=0, columnspan=2, sticky="w", pady=(16, 4))
        row += 1
        Label(inner, text=get_text("settings.provider_hint"),
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

        # 语言选择
        Label(inner, text=get_text("settings.language"), bg=BG, fg=ACCENT,
              font=("Segoe UI", 13, "bold")).grid(
                  row=row, column=0, columnspan=2, sticky="w", pady=(16, 4))
        row += 1

        from services.i18n import available_locales, current_locale
        self.lang_var = StringVar(value=current_locale())
        lang_frame = Frame(inner, bg=BG)
        lang_frame.grid(row=row, column=0, columnspan=2, sticky="w", padx=8)
        for code, name in available_locales():
            Radiobutton(lang_frame, text=name, variable=self.lang_var,
                        value=code, bg=BG, fg=FG, selectcolor=BTN_BG,
                        activebackground=BG, activeforeground=FG,
                        font=("Segoe UI", 10),
                        command=lambda c=code: self._on_lang_change(c)).pack(side="left", padx=8)
        row += 1

        # 按钮
        btn_frame = Frame(inner, bg=BG)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=16)
        Button(btn_frame, text=get_text("settings.save"),
               bg=ACCENT, fg="#1e1e2e",
               font=("Segoe UI", 11, "bold"),
               relief="flat", padx=20, pady=6,
               command=self._save).pack(side="left", padx=6)
        Button(btn_frame, text=get_text("settings.debug_log"),
               bg=BTN_BG, fg=FG, relief="flat",
               command=self._show_log).pack(side="left", padx=6)

        self._load()

    def _load(self):
        cfg = load_config()
        for key_id, e in self.entries.items():
            val = cfg.get(key_id, "")
            e.delete(0, END)
            e.insert(0, val)

    def _on_lang_change(self, code):
        """切换语言（实时预览，保存后生效）"""
        from services.i18n import set_locale
        set_locale(code)

    def _save(self):
        cfg = {key_id: e.get().strip() for key_id, e in self.entries.items()}
        enabled = [n for n, v in self.provider_vars.items() if v.get()]
        cfg["provider_order"] = enabled
        cfg["language"] = self.lang_var.get()
        save_config(cfg)
        messagebox.showinfo(get_text("app.saved_ok"), get_text("settings.saved_reboot"))

    def _show_log(self):
        log = get_log_content()
        win = Toplevel(self)
        win.title(get_text("settings.debug_title"))
        win.geometry("700x400")
        txt = Text(win, bg=INFO_BG, fg=GREEN, font=("Consolas", 9),
                   relief="flat", wrap="none")
        txt.insert("1.0", log or get_text("settings.no_log"))
        txt.config(state="disabled")
        Scrollbar(win, orient=HORIZONTAL, command=txt.xview).pack(side="bottom", fill="x")
        Scrollbar(win, orient=VERTICAL, command=txt.yview).pack(side="right", fill="y")
        txt.config(xscrollcommand=Scrollbar(win, orient=HORIZONTAL).set)
        txt.pack(fill="both", expand=True)


class App(Tk):
    def __init__(self):
        super().__init__()
        self.title(get_text("app.title"))
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
