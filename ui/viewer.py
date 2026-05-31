"""
ui/viewer.py  v4 — 单图渲染架构图片查看器
─────────────────────────────────────
性能优化：
  · 永远只有一张 PhotoImage 通过 create_image 渲染在 Canvas 上
  · 缩放时 itemconfig 替换 PhotoImage，拖拽时 coords 更新位置
  · 后台线程异步准备缩放图，主线程轮询提交到 Canvas
  · OrderedDict zoom 缓存（最多3个级别），16ms 防抖
"""
import io
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from collections import OrderedDict
from threading import Thread, Event
from queue import Queue, Empty

from PIL import Image, ImageTk
from config.fonts import F
from config.theme import DARK_THEME as C
from config.i18n import _
from config.settings import IMAGES_DIR



class ImageViewerWindow(tk.Toplevel):
    """弹出式图片查看器（单图渲染架构、自由拖拽、缩放、裁剪）。"""

    def __init__(self, parent_app):
        super().__init__(parent_app.root)
        self.app = parent_app

        # 图片状态
        self._img_orig   = None
        self._img_bytes  = None
        self._cur_path   = ""
        self._zoom       = 1.0
        self._photo      = None
        self._img_cx     = 0
        self._img_cy     = 0
        self._img_item   = None
        self._pan_last   = None

        # 裁剪状态
        self._crop_mode    = False
        self._crop_drawing = False
        self._crop_x0 = self._crop_y0 = 0
        self._crop_rect    = None
        self._crop_coords  = None

        # 待渲染数据
        self._pending_load = None

        # ── 性能优化：单图渲染状态 ────────────────────────────────
        self._zoom_cache = OrderedDict()        # {round(zoom,2): PhotoImage}
        self._render_queue = Queue(maxsize=50)  # round_zoom float
        self._done_queue   = Queue(maxsize=50)  # (round_zoom, PIL_Image)
        self._pending_job  = None               # round(zoom,2) currently in flight
        self._render_timer = None               # after() id for debounce
        self._stop_event   = Event()
        self._bg_thread    = None
        self._polling      = False

        self.title(_("viewer_title"))
        self.geometry("1020x740")
        self.configure(bg=C["bg"])
        self.minsize(640, 480)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # 居中
        self.update_idletasks()
        px = parent_app.root.winfo_x() + (parent_app.root.winfo_width()  - 1020) // 2
        py = parent_app.root.winfo_y() + (parent_app.root.winfo_height() -  740) // 2
        self.geometry(f"1020x740+{max(0, px)}+{max(0, py)}")

        self.bind("<Map>", self._on_mapped)

    # ── UI 构建 ───────────────────────────────────────────────
    def _build_ui(self):
        

        # 顶部工具栏
        tb = tk.Frame(self, bg=C["tb"], height=46)
        tb.pack(fill="x"); tb.pack_propagate(False)

        def tbtn(txt, cmd, color=None, side="left"):
            b = tk.Button(tb, text=txt, font=F["body"],
                          command=cmd, bg=color or C["acc"], fg="white",
                          bd=0, padx=10, pady=5, cursor="hand2",
                          activebackground="#1a4a7a")
            b.pack(side=side, padx=2, pady=6)
            return b

        def sep():
            tk.Frame(tb, bg="#2a3a5a", width=1).pack(
                side="left", fill="y", padx=5, pady=8)

        tbtn(_("viewer_zoom_in"),   self._zoom_in)
        tbtn(_("viewer_zoom_out"),   self._zoom_out)
        tbtn(_("viewer_fit"), self._zoom_fit)
        tbtn(_("viewer_100"),   self._zoom_100)
        sep()
        self._crop_btn = tbtn(_("viewer_crop"), self._crop_toggle, color="#7c3aed")
        sep()
        tbtn(_("viewer_save"), self._save_overwrite)
        tbtn("📁 另存为",   self._save_as)
        tbtn("📋 复制路径", self._copy_path)
        sep()

        self._zoom_badge = tk.Label(tb, text="--",
                                     font=F["badge"],
                                     bg=C["tb"], fg=C["ok"], width=6)
        self._zoom_badge.pack(side="left", padx=(4, 0))
        tk.Label(tb, text="滚轮缩放  拖拽平移  +/- 键  Esc 退出裁剪",
                 font=F["body"], bg=C["tb"], fg=C["sub"]
                 ).pack(side="right", padx=14)

        # 画布
        self.cv = tk.Canvas(self, bg="#111827", cursor="hand2",
                             bd=0, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self._ph_text = self.cv.create_text(
            500, 340, text="", font=(F["_sans"], 16),
            fill="#9ab4cc", anchor="center", tags="placeholder")

        # 底部信息栏
        info_bar = tk.Frame(self, bg=C["panel"], height=30)
        info_bar.pack(fill="x", side="bottom")
        info_bar.pack_propagate(False)

        def infolbl(text, fg=None):
            return tk.Label(info_bar, text=text, font=F["mono"],
                            bg=C["panel"], fg=fg or C["ok"])

        def vsep():
            tk.Frame(info_bar, bg="#2a3a5a", width=1).pack(
                side="left", fill="y", pady=5, padx=6)

        self._info_res  = infolbl(_("lbl_size") + " --");  self._info_res.pack(side="left", padx=(14, 0))
        vsep()
        self._info_kb   = infolbl("大小: --", fg=C["sub"]); self._info_kb.pack(side="left")
        vsep()
        self._info_zoom = infolbl("缩放: --", fg=C["sub"]); self._info_zoom.pack(side="left")
        vsep()
        self._info_file = infolbl("文件: --", fg=C["sub"]); self._info_file.pack(side="left")
        self._info_tip  = tk.Label(info_bar, text="",
                                    font=F["body"], bg=C["panel"], fg=C["warn"])
        self._info_tip.pack(side="right", padx=14)

        # Metadata label (PNG tEXt chunks)
        self._meta_lbl = tk.Label(self, text="", font=F["mono_tiny"],
                                   bg=C["bg"], fg=C["sub"], anchor="w", justify="left")
        self._meta_lbl.pack(fill="x", padx=8, pady=(0, 4))

        # 事件绑定
        self.cv.bind("<MouseWheel>",      self._on_wheel)
        self.cv.bind("<Button-4>",        self._on_wheel)
        self.cv.bind("<Button-5>",        self._on_wheel)
        self.cv.bind("<ButtonPress-1>",   self._on_down)
        self.cv.bind("<B1-Motion>",        self._on_drag)
        self.cv.bind("<ButtonRelease-1>",  self._on_up)
        self.cv.bind("<Configure>",        self._on_canvas_resize)
        self.bind("<plus>",  lambda e: self._zoom_in())
        self.bind("<equal>", lambda e: self._zoom_in())
        self.bind("<minus>", lambda e: self._zoom_out())
        self.bind("<f>",     lambda e: self._zoom_fit())
        self.bind("<F>",     lambda e: self._zoom_fit())
        self.bind("<Home>",  lambda e: self._zoom_fit())
        self.bind("<Escape>", lambda e: self._crop_cancel() if self._crop_mode else None)

    # ── 后台线程 ───────────────────────────────────────────────
    def _ensure_worker(self):
        if self._bg_thread is None or not self._bg_thread.is_alive():
            self._stop_event.clear()
            self._bg_thread = Thread(target=self._resize_worker, daemon=True)
            self._bg_thread.start()

    def _resize_worker(self):
        """后台线程：只负责 PIL 图像缩放，PIL Image 发回主线程创建 PhotoImage。"""
        while not self._stop_event.is_set():
            try:
                round_zoom = self._render_queue.get(timeout=0.05)
            except Empty:
                continue
            # 任务过时（已被新任务替代），跳过
            if round_zoom != self._pending_job:
                continue
            img = self._img_orig
            if img is None:
                continue
            try:
                ow, oh = img.size
                new_w = max(1, int(ow * round_zoom))
                new_h = max(1, int(oh * round_zoom))
                filt = Image.NEAREST if round_zoom >= 3.0 else Image.LANCZOS
                resized = img.resize((new_w, new_h), filt)
                # 注意：ImageTk.PhotoImage 必须在主线程创建，这里只发 PIL Image
                self._done_queue.put((round_zoom, resized))
            except Exception:
                pass

    def _poll_queue(self):
        if not self._polling or self._img_orig is None:
            return
        processed = 0
        while processed < 4:
            try:
                round_zoom, pil_img = self._done_queue.get_nowait()
            except Empty:
                break
            # 在主线程创建 PhotoImage（Tkinter 要求）
            if round_zoom not in self._zoom_cache:
                photo = ImageTk.PhotoImage(pil_img)
                self._zoom_cache[round_zoom] = photo
                while len(self._zoom_cache) > 3:
                    self._zoom_cache.popitem(last=False)
            if round_zoom == self._pending_job:
                self._commit_frame(self._zoom_cache[round_zoom])
                self._pending_job = None
            processed += 1
        if self._polling:
            self.after(2, self._poll_queue)

    def _start_polling(self):
        if not self._polling:
            self._polling = True
            self._poll_queue()

    def _stop_polling(self):
        self._polling = False

    # ── 渲染核心 ───────────────────────────────────────────────
    def _commit_frame(self, photo):
        self._photo = photo  # 保持强引用，防止被 GC 导致画布空白
        if self._img_item is None:
            self._img_item = self.cv.create_image(
                self._img_cx, self._img_cy, image=photo, anchor="center", tags="main_img")
        else:
            self.cv.itemconfig(self._img_item, image=photo)
            self.cv.coords(self._img_item, self._img_cx, self._img_cy)
        z = self._zoom
        self._info_zoom.config(text=f"缩放: {z*100:.0f}%")
        self._zoom_badge.config(text=f"{z*100:.0f}%")

    def _do_zoom(self):
        self._render_timer = None
        if self._img_orig is None:
            return
        cw = self.cv.winfo_width()
        ch = self.cv.winfo_height()
        if cw < 10 or ch < 10:
            return
        round_zoom = round(self._zoom, 2)
        if round_zoom in self._zoom_cache:
            self._commit_frame(self._zoom_cache[round_zoom])
            return
        if self._pending_job != round_zoom:
            self._pending_job = round_zoom
            self._ensure_worker()
            try:
                self._render_queue.put_nowait(round_zoom)
            except Exception:
                pass
            self._start_polling()

    # ── 窗口就绪 ───────────────────────────────────────────────
    def _on_mapped(self, event=None):
        self.unbind("<Map>")
        if self._pending_load:
            data, path = self._pending_load
            self._pending_load = None
            self._img_orig = Image.open(io.BytesIO(data)).convert("RGBA")
            self._img_bytes = data
            self._cur_path  = path
            self._update_info()
            self._show_metadata()
            self._zoom_fit()

    # ── 图片加载 ───────────────────────────────────────────────
    def load_bytes(self, data: bytes, path: str = "") -> None:
        self._img_bytes = data
        self._cur_path  = path
        self._img_orig  = Image.open(io.BytesIO(data)).convert("RGBA")
        self._zoom_cache.clear()
        self._pending_job = None
        self._update_info()
        self._show_metadata()
        cw = self.cv.winfo_width()
        if cw > 1:
            self._zoom_fit()
        else:
            self._pending_load = (data, path)

    def load_file(self, path: str) -> None:
        if path and os.path.exists(path):
            real = os.path.realpath(path)
            images_real = os.path.realpath(IMAGES_DIR)
            if not real.startswith(images_real + os.sep):
                return
            with open(path, "rb") as _fh:
                self.load_bytes(_fh.read(), path)

    # ── 信息更新 ───────────────────────────────────────────────
    def _update_info(self):
        if self._img_orig is None: return
        ow, oh = self._img_orig.size
        self._info_res.config(text=f'{_("lbl_size")} {ow} × {oh} px')
        if self._img_bytes:
            kb = len(self._img_bytes) / 1024
            self._info_kb.config(text=f"大小: {kb:.1f} KB")
        if self._cur_path:
            self._info_file.config(text=f"文件: {os.path.basename(self._cur_path)}")

    def _show_metadata(self):
        """Extract and display PNG text metadata."""
        if hasattr(self, '_meta_lbl'):
            if self._img_orig is None:
                self._meta_lbl.config(text="")
                return
            meta = self._img_orig.info or {}
            lines = []
            for key in ("Prompt", "Translated", "Provider", "Seed", "Size"):
                val = meta.get(key, "")
                if val:
                    lines.append(f"{key}: {val}")
            self._meta_lbl.config(text="\n".join(lines) if lines else "无元数据")

    # ── 缩放 ───────────────────────────────────────────────────
    def _zoom_fit(self):
        if self._img_orig is None:
            return
        self.cv.update_idletasks()
        cw = self.cv.winfo_width()
        ch = self.cv.winfo_height()
        # Canvas 未就绪（尺寸无效），延迟到 _on_mapped 处理
        if cw < 10 or ch < 10:
            self._pending_load = (self._img_bytes, self._cur_path)
            return
        ow, oh = self._img_orig.size
        self._zoom  = min((cw - 4) / ow, (ch - 4) / oh)
        # 确保缩放值有效
        if self._zoom <= 0:
            self._zoom = 1.0
        self._img_cx = cw // 2
        self._img_cy = ch // 2
        self._pending_job = None
        if self._render_timer is not None:
            self.after_cancel(self._render_timer)
        self._render_timer = self.after(16, self._do_zoom)

    def _zoom_100(self):
        if self._img_orig is None:
            return
        self.cv.update_idletasks()
        cw = self.cv.winfo_width()
        ch = self.cv.winfo_height()
        if cw < 10 or ch < 10:
            return
        self._zoom   = 1.0
        self._img_cx = cw // 2
        self._img_cy = ch // 2
        self._pending_job = None
        if self._render_timer is not None:
            self.after_cancel(self._render_timer)
        self._render_timer = self.after(16, self._do_zoom)

    def _zoom_in(self):
        self._zoom_by(1.25)

    def _zoom_out(self):
        self._zoom_by(0.8)

    def _zoom_by(self, factor, cx=None, cy=None):
        if self._img_orig is None:
            return
        old_zoom = self._zoom
        new_zoom = max(0.02, min(30.0, self._zoom * factor))
        if abs(new_zoom - old_zoom) < 0.001:
            return
        if cx is not None and cy is not None:
            dx = cx - self._img_cx
            dy = cy - self._img_cy
            ratio = new_zoom / old_zoom
            self._img_cx = int(cx - dx * ratio)
            self._img_cy = int(cy - dy * ratio)
        self._zoom = new_zoom
        if self._render_timer is not None:
            self.after_cancel(self._render_timer)
        self._render_timer = self.after(16, self._do_zoom)

    def _on_wheel(self, event):
        if self._img_orig is None: return
        if event.num == 4 or (hasattr(event, "delta") and event.delta > 0):
            factor = 1.15
        else:
            factor = 1 / 1.15
        self._zoom_by(factor, event.x, event.y)

    def _on_canvas_resize(self, event):
        if self._img_orig is None:
            self.cv.coords(self._ph_text, event.width // 2, event.height // 2)
        else:
            self._img_cx = event.width // 2
            self._img_cy = event.height // 2
            if self._img_item:
                self.cv.coords(self._img_item, self._img_cx, self._img_cy)
            # 缓存基于 zoom 级别，与 canvas 尺寸无关，无需清除

    # ── 拖拽平移 ───────────────────────────────────────────────
    def _on_down(self, event):
        if self._crop_mode:
            self._crop_drawing = True
            self._crop_x0, self._crop_y0 = event.x, event.y
            if self._crop_rect:
                self.cv.delete(self._crop_rect); self._crop_rect = None
        else:
            self._pan_last = (event.x, event.y)
            self.cv.config(cursor="fleur")

    def _on_drag(self, event):
        if self._crop_mode and self._crop_drawing:
            if self._crop_rect:
                self.cv.delete(self._crop_rect)
            self._crop_rect = self.cv.create_rectangle(
                self._crop_x0, self._crop_y0, event.x, event.y,
                outline="#e94560", width=2, dash=(6, 3), tags="crop")
        elif self._pan_last and self._img_item:
            dx = event.x - self._pan_last[0]
            dy = event.y - self._pan_last[1]
            self._img_cx += dx
            self._img_cy += dy
            self._pan_last = (event.x, event.y)
            self.cv.coords(self._img_item, self._img_cx, self._img_cy)
            if self._crop_rect:
                self.cv.tag_raise(self._crop_rect)

    def _on_up(self, event):
        if self._crop_mode and self._crop_drawing:
            self._crop_drawing = False
            x0, y0 = min(self._crop_x0, event.x), min(self._crop_y0, event.y)
            x1, y1 = max(self._crop_x0, event.x), max(self._crop_y0, event.y)
            if (x1 - x0) > 10 and (y1 - y0) > 10:
                self._crop_coords = (x0, y0, x1, y1)
                self._crop_confirm()
        else:
            self.cv.config(cursor="hand2")
            self._pan_last = None

    # ── 裁剪 ───────────────────────────────────────────────────
    def _crop_toggle(self):
        if self._img_orig is None:
            messagebox.showinfo("提示", "请先加载图片", parent=self); return
        self._crop_mode = not self._crop_mode
        if self._crop_mode:
            self._crop_btn.config(bg="#dc2626", text="✂ 取消裁剪")
            self.cv.config(cursor="crosshair")
            self._info_tip.config(text="裁剪模式：拖拽鼠标选区，Esc 取消")
        else:
            self._crop_cancel()

    def _crop_cancel(self):
        self._crop_mode = self._crop_drawing = False
        self._crop_coords = None
        if self._crop_rect:
            self.cv.delete(self._crop_rect); self._crop_rect = None
        if hasattr(self, "_crop_btn"):
            self._crop_btn.config(bg="#7c3aed", text=_("viewer_crop"))
        self.cv.config(cursor="hand2")
        self._info_tip.config(text="")

    def _crop_confirm(self):
        if self._img_orig is None or self._crop_coords is None: return
        cx0, cy0, cx1, cy1 = self._crop_coords
        ow, oh = self._img_orig.size
        nw, nh = int(ow * self._zoom), int(oh * self._zoom)
        img_left = self._img_cx - nw // 2
        img_top  = self._img_cy - nh // 2
        sx = int((cx0 - img_left) / self._zoom)
        sy = int((cy0 - img_top)  / self._zoom)
        ex = int((cx1 - img_left) / self._zoom)
        ey = int((cy1 - img_top)  / self._zoom)
        sx, sy = max(0, sx), max(0, sy)
        ex, ey = min(ow, ex), min(oh, ey)
        if ex - sx < 8 or ey - sy < 8:
            messagebox.showwarning("裁剪", "选区太小，请重新选择", parent=self); return
        self._crop_preview(sx, sy, ex, ey)

    def _crop_preview(self, sx, sy, ex, ey):
        
        win = tk.Toplevel(self)
        win.title("裁剪预览"); win.configure(bg=C["bg"])
        win.grab_set(); win.resizable(True, True); win.minsize(520, 480)

        cropped = self._img_orig.crop((sx, sy, ex, ey))

        bot_f = tk.Frame(win, bg=C["panel"]); bot_f.pack(fill="x", side="bottom")
        ow_var = tk.BooleanVar(value=False)

        def do_apply():
            buf = io.BytesIO(); cropped.save(buf, "PNG"); new_bytes = buf.getvalue()
            if ow_var.get() and self._cur_path:
                cropped.save(self._cur_path, "PNG")
                self._info_tip.config(text="✂ 裁剪完成，原图已覆盖保存")
            else:
                self._info_tip.config(text="✂ 裁剪完成（原图未修改）")
            self._crop_cancel(); win.destroy()
            self.load_bytes(new_bytes, self._cur_path)
            if self._cur_path:
                self.app.cur_path = self._cur_path
            self.app._log(f"✂ 裁剪: {ex-sx}×{ey-sy}px")

        tk.Button(bot_f, text="✅ 应用裁剪",
                  font=F["h2"], bg=C["ok"], fg="#0a1a0a",
                  bd=0, padx=28, pady=10, cursor="hand2",
                  command=do_apply).pack(side="right", padx=16, pady=10)
        tk.Button(bot_f, text=_("btn_cancel"),
                  font=F["input"], bg=C["panel"], fg=C["sub"],
                  bd=0, padx=16, pady=10, cursor="hand2",
                  command=win.destroy).pack(side="right", pady=10)

        opt_f = tk.Frame(win, bg=C["bg"])
        opt_f.pack(fill="x", side="bottom", padx=16)
        tk.Button(opt_f, text="📁 另存为新文件…",
                  font=F["body"], bg=C["acc"], fg="white", bd=0,
                  padx=10, pady=4, cursor="hand2",
                  command=lambda: self._crop_saveas(cropped, win)
                  ).pack(side="left", pady=(0, 6))
        tk.Radiobutton(opt_f,
                       text="同时覆盖保存原图文件（此操作不可撤销）",
                       variable=ow_var, value=True, font=F["body"],
                       bg=C["bg"], fg=C["warn"],
                       activebackground=C["bg"], selectcolor=C["entry"]
                       ).pack(anchor="w", pady=(4, 2))
        tk.Radiobutton(opt_f,
                       text="仅在查看器中显示裁剪结果（不修改原图文件）",
                       variable=ow_var, value=False, font=F["body"],
                       bg=C["bg"], fg=C["text"],
                       activebackground=C["bg"], selectcolor=C["entry"]
                       ).pack(anchor="w", pady=(0, 6))

        info_f = tk.Frame(win, bg=C["panel"]); info_f.pack(fill="x", side="bottom")
        tk.Label(info_f, text=f"裁剪后尺寸：{ex-sx} × {ey-sy} px",
                 font=F["body"], bg=C["panel"], fg=C["ok"]
                 ).pack(side="left", padx=14, pady=6)

        screen_h   = win.winfo_screenheight()
        max_prev_h = min(420, int(screen_h * 0.45))
        preview    = cropped.copy(); preview.thumbnail((660, max_prev_h), Image.LANCZOS)
        ph = ImageTk.PhotoImage(preview)
        img_frame = tk.Frame(win, bg="#111827"); img_frame.pack(fill="both", expand=True)
        img_lbl   = tk.Label(img_frame, image=ph, bg="#111827")
        img_lbl.image = ph; img_lbl.pack(expand=True)

        win.update_idletasks()
        w_req = max(660, win.winfo_reqwidth())
        h_req = min(int(screen_h * 0.9), win.winfo_reqheight() + 20)
        wx = max(0, self.winfo_x() + (self.winfo_width()  - w_req) // 2)
        wy = max(0, self.winfo_y() + (self.winfo_height() - h_req) // 2)
        win.geometry(f"{w_req}x{h_req}+{wx}+{wy}")

    def _crop_saveas(self, cropped_img, parent_win):
        dest = filedialog.asksaveasfilename(
            parent=parent_win, defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("所有文件", "*.*")],
            title="裁剪另存为")
        if dest:
            cropped_img.save(dest)
            self.app._log(f"✂ 裁剪另存为: {dest}")
            self._info_tip.config(text=f"另存: {os.path.basename(dest)}")
            messagebox.showinfo("保存成功", f"已保存至：\n{dest}", parent=parent_win)

    # ── 保存操作 ───────────────────────────────────────────────
    def _save_overwrite(self):
        if self._img_orig is None:
            messagebox.showwarning("提示", "暂无图片", parent=self); return
        if self._cur_path:
            self._img_orig.save(self._cur_path, "PNG")
            self._info_tip.config(text=f"💾 已保存: {os.path.basename(self._cur_path)}")
            self.app._log(f"💾 覆盖保存: {self._cur_path}")
        else:
            self._save_as()

    def _save_as(self):
        if self._img_orig is None:
            messagebox.showwarning("提示", "暂无图片", parent=self); return
        d = filedialog.asksaveasfilename(
            parent=self, defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("所有文件", "*.*")],
            initialfile=os.path.basename(self._cur_path) if self._cur_path else "image.png")
        if d:
            self._img_orig.save(d)
            self._info_tip.config(text=f"💾 另存: {os.path.basename(d)}")
            self.app._log(f"💾 另存为: {d}")
            messagebox.showinfo("完成", f"已保存：{d}", parent=self)

    def _copy_path(self):
        if self._cur_path:
            self.clipboard_clear(); self.clipboard_append(self._cur_path)
            self._info_tip.config(text="📋 路径已复制")
            self.app._log("📋 路径已复制")

    def _on_close(self):
        self._stop_event.set()
        self._polling = False
        if self._render_timer is not None:
            self.after_cancel(self._render_timer)
        self.app._viewer_win = None
        self.destroy()