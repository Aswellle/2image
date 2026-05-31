"""
ui/queue_panel.py — 顺序生成队列面板  v1
────────────────────────────────────────
解决核心痛点：无法在等待当前图片生成时同时排队下一个任务。

功能：
  · 把主输入框里的提示词「加入队列」
  · 队列按顺序逐一生成（串行，接口稳定）
  · 每个条目实时显示状态 / 耗时 / 结果缩略图
  · 生成完成自动写入历史记录，触发主界面刷新
  · 支持暂停 / 继续 / 单条删除 / 批量清空已完成
"""
import io
import os
import random
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional

from PIL import Image, ImageTk
from config.fonts import F
from config.theme import DARK_THEME as C
from config.i18n import _


_STATUS = {
    "waiting":   (C["sub"],  _("queue_waiting")),
    "running":   (C["warn"], _("queue_running")),
    "done":      (C["ok"],   _("queue_done")),
    "failed":    (C["hl"],   _("queue_failed")),
    "cancelled": ("#64748b",  _("queue_cancelled")),
}


# ══════════════════════════════════════════════════════════════
#   数据模型
# ══════════════════════════════════════════════════════════════
class _QueueItem:
    _counter = 0

    def __init__(self, prompt: str, size: str, porder):
        _QueueItem._counter += 1
        self.item_id     = _QueueItem._counter
        self.prompt      = prompt
        self.size        = size
        self.porder      = porder
        self.status      = "waiting"
        self.result_path = ""
        self.result_data: Optional[bytes] = None
        self.provider    = ""
        self.error       = ""
        self.elapsed     = 0.0
        self.added_at    = time.strftime("%H:%M:%S")


# ══════════════════════════════════════════════════════════════
#   单条任务 Widget
# ══════════════════════════════════════════════════════════════
class _ItemWidget(tk.Frame):
    THUMB = 76

    def __init__(self, parent, item: _QueueItem,
                 on_remove, on_view, **kw):
        super().__init__(parent, bg=C["panel"],
                         highlightbackground=C["sep"],
                         highlightthickness=1, **kw)
        self._item = item
        self._ph   = None    # 防 GC

        # ── 左侧缩略图 ────────────────────────────────────────
        host = tk.Frame(self, bg="#0a0f1a",
                        width=self.THUMB, height=self.THUMB)
        host.pack(side="left", padx=(8, 6), pady=8)
        host.pack_propagate(False)
        self._thumb_lbl = tk.Label(host, bg="#0a0f1a",
                                    text="⏳", font=F["disp_lg"],
                                    fg="#334155")
        self._thumb_lbl.pack(expand=True)

        # ── 右侧信息区 ────────────────────────────────────────
        info = tk.Frame(self, bg=C["panel"])
        info.pack(side="left", fill="both", expand=True)

        # 第一行：状态 + 编号 + 耗时 + 删除
        row1 = tk.Frame(info, bg=C["panel"])
        row1.pack(fill="x", padx=(0, 6), pady=(6, 0))

        self._st_lbl = tk.Label(row1, text="", font=F["small_b"],
                                 bg=C["panel"], fg=C["warn"], anchor="w")
        self._st_lbl.pack(side="left")

        tk.Label(row1,
                 text=f"  #{item.item_id}  {item.added_at}",
                 font=F["mono_tiny"], bg=C["panel"], fg=C["sub"]
                 ).pack(side="left")

        self._time_lbl = tk.Label(row1, text="", font=F["mono_tiny"],
                                   bg=C["panel"], fg="#64748b")
        self._time_lbl.pack(side="left")

        tk.Button(row1, text="✕", font=F["small"],
                  bg=C["panel"], fg="#e05555", bd=0,
                  padx=4, cursor="hand2",
                  command=lambda: on_remove(self)
                  ).pack(side="right")

        # 第二行：提示词
        self._prompt_lbl = tk.Label(
            info, text=item.prompt[:90],
            font=F["small"], bg=C["panel"], fg=C["text"],
            anchor="w", justify="left", wraplength=400)
        self._prompt_lbl.pack(anchor="w", padx=(0, 6))

        # 第三行：尺寸 + 接口 + 查看按钮
        row3 = tk.Frame(info, bg=C["panel"])
        row3.pack(fill="x", padx=(0, 6), pady=(2, 6))

        self._meta_lbl = tk.Label(row3,
                                   text=f"📐 {item.size}",
                                   font=F["mono_tiny"],
                                   bg=C["panel"], fg=C["sub"])
        self._meta_lbl.pack(side="left")

        self._view_btn = tk.Button(
            row3, text="🔍 查看结果",
            font=F["tiny_b"],
            bg=C["acc"], fg="white", bd=0,
            padx=8, pady=2, cursor="hand2",
            state="disabled",
            command=lambda: on_view(self._item))
        self._view_btn.pack(side="right")

        self._refresh()

    # ── 状态刷新 ──────────────────────────────────────────────
    def _refresh(self):
        color, text = _STATUS.get(self._item.status, ("#888", self._item.status))
        self._st_lbl.config(text=text, fg=color)
        border = color if self._item.status in ("done","failed","running") else C["sep"]
        self.config(highlightbackground=border)
        if self._item.status == "done":
            self._view_btn.config(state="normal")
        if self._item.elapsed > 0:
            self._time_lbl.config(text=f"  ⏱ {self._item.elapsed:.1f}s")
        if self._item.provider:
            self._meta_lbl.config(
                text=f"📐 {self._item.size}  ·  {self._item.provider[:28]}")
        if self._item.error:
            self._prompt_lbl.config(
                text=f"⚠ {self._item.error[:70]}", fg=C["hl"])

    def update_status(self, status: str, **kw):
        self._item.status = status
        for k, v in kw.items():
            setattr(self._item, k, v)
        self._refresh()

    def set_thumb(self, pil_img: Image.Image):
        """必须在主线程调用。在此方法里创建 PhotoImage。"""
        try:
            T = self.THUMB - 6
            pil_img.thumbnail((T, T), Image.LANCZOS)
            bg = Image.new("RGB", (T, T), (10, 15, 26))
            bg.paste(pil_img, ((T - pil_img.width) // 2,
                                (T - pil_img.height) // 2))
            ph = ImageTk.PhotoImage(bg)
            self._ph = ph          # 防 GC
            self._thumb_lbl.config(image=ph, text="",
                                   width=T, height=T)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════
#   队列主面板
# ══════════════════════════════════════════════════════════════
class QueuePanel(tk.Frame):
    """
    顺序生成队列面板。

    集成到 app.py 方式：
      self._queue_panel = QueuePanel(frame, self)
      self._queue_panel.pack(fill="both", expand=True)

    公开方法：
      add_task(prompt, size, porder)  — 外部添加任务
    """

    def __init__(self, parent, app, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self.app        = app
        self._widgets: List[_ItemWidget] = []
        self._running   = False
        self._paused    = False
        self._stop_flag = False

        self._build_ui()

    # ══════════════════════════════════════════════════════════
    #   UI 构建
    # ══════════════════════════════════════════════════════════
    def _build_ui(self):
        # ── 顶部标题 + 控制栏 ─────────────────────────────────
        hdr = tk.Frame(self, bg=C["acc"], height=48)
        hdr.pack(fill="x"); hdr.pack_propagate(False)

        tk.Label(hdr, text="📋  顺序生成队列",
                 font=F["h2"],
                 bg=C["acc"], fg="white"
                 ).pack(side="left", padx=14, pady=10)

        btn_f = tk.Frame(hdr, bg=C["acc"])
        btn_f.pack(side="right", padx=8, pady=6)

        def _btn(text, cmd, bg=C["acc"]):
            b = tk.Button(btn_f, text=text,
                          font=F["body_b"],
                          bg=bg, fg="white", bd=0,
                          padx=10, pady=4, cursor="hand2",
                          command=cmd,
                          activebackground="#1e3060")
            b.pack(side="left", padx=3)
            return b

        _btn(_("btn_add_queue"), self._add_from_app, "#065f46")
        self._start_btn = _btn(_("queue_btn_start"), self._start, "#1e40af")
        self._pause_btn = _btn(_("queue_btn_pause"), self._toggle_pause, "#7c3aed")
        _btn(_("queue_btn_clear_done"), self._clear_done, "#7c2d12")

        # ── 状态信息条 ────────────────────────────────────────
        bar = tk.Frame(self, bg="#0a0f1a", height=26)
        bar.pack(fill="x"); bar.pack_propagate(False)

        self._prog_lbl = tk.Label(
            bar,
            text="队列为空 · 在主输入框写好提示词后点「➕ 加入队列」",
            font=F["small"], bg="#0a0f1a", fg=C["sub"])
        self._prog_lbl.pack(side="left", padx=10, pady=4)

        self._cnt_lbl = tk.Label(bar, text="",
                                  font=F["mono_sm_b"],
                                  bg="#0a0f1a", fg=C["ok"])
        self._cnt_lbl.pack(side="right", padx=10)

        # ── 可滚动列表 ────────────────────────────────────────
        outer = tk.Frame(self, bg=C["bg"])
        outer.pack(fill="both", expand=True)

        self._cv = tk.Canvas(outer, bg=C["bg"],
                              bd=0, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical",
                             command=self._cv.yview)
        self._cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._cv.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(self._cv, bg=C["bg"])
        _win = self._cv.create_window((0, 0), window=self._inner,
                                       anchor="nw")
        self._inner.bind("<Configure>",
                          lambda e: self._cv.configure(
                              scrollregion=self._cv.bbox("all")))
        self._cv.bind("<Configure>",
                       lambda e: self._cv.itemconfig(_win, width=e.width))

        def _wheel(ev):
            self._cv.yview_scroll(int(-1*(ev.delta/120)), "units")
        self._cv.bind("<MouseWheel>", _wheel)
        self._cv.bind("<Button-4>",
                       lambda e: self._cv.yview_scroll(-1, "units"))
        self._cv.bind("<Button-5>",
                       lambda e: self._cv.yview_scroll(1, "units"))

        # 空状态提示
        self._empty_lbl = tk.Label(
            self._inner,
            text=("📋  队列为空\n\n"
                  "在主输入框填好提示词，点击「➕ 加入队列」\n"
                  "连续添加多个不同提示词后，点「▶ 开始」\n"
                  "程序会按顺序自动逐一生成，无需手动等待"),
            font=F["input"], bg=C["bg"], fg="#3a4a6a",
            justify="center")
        self._empty_lbl.pack(expand=True, pady=60)

    # ══════════════════════════════════════════════════════════
    #   公开 API
    # ══════════════════════════════════════════════════════════
    def add_task(self, prompt: str, size: str = "1024x1024",
                 porder=None) -> None:
        item   = _QueueItem(prompt, size, porder)
        widget = _ItemWidget(self._inner, item,
                             on_remove=self._remove,
                             on_view=self._view)
        widget.pack(fill="x", padx=8, pady=3)
        self._widgets.append(widget)

        if self._empty_lbl.winfo_ismapped():
            self._empty_lbl.pack_forget()

        self._update_counts()
        self._set_prog(f"已加入：{prompt[:40]}…")
        # 滚动到底部
        self.after(50, lambda: self._cv.yview_moveto(1.0))

    # ══════════════════════════════════════════════════════════
    #   控制按钮回调
    # ══════════════════════════════════════════════════════════
    def _add_from_app(self):
        prompt = self.app.pt.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning(
                "提示", "请先在主输入框填写提示词",
                parent=self.app.root)
            return
        sz    = self.app.szv.get()
        psel  = self.app.pv.get()
        pord  = None if psel in ("自动（按优先级）", "") else [psel]
        self.add_task(prompt, sz, pord)

    def _start(self):
        if self._running:
            return
        waiting = [w for w in self._widgets
                   if w._item.status == "waiting"]
        if not waiting:
            messagebox.showinfo(
                "提示", "队列中没有等待中的任务\n请先点「➕ 加入队列」添加提示词",
                parent=self.app.root)
            return
        self._running   = True
        self._paused    = False
        self._stop_flag = False
        self._start_btn.config(state="disabled", text="▶ 运行中…")
        threading.Thread(target=self._run_loop, daemon=True).start()

    def _toggle_pause(self):
        if not self._running:
            return
        self._paused = not self._paused
        self._pause_btn.config(
            text=_("queue_btn_resume") if self._paused else _("queue_btn_pause"))
        self._set_prog(
            "⏸ 已暂停 — 当前任务完成后停止" if self._paused
            else "▶ 已继续运行…")

    def _clear_done(self):
        done_s = {"done", "cancelled", "failed"}
        dead   = [w for w in self._widgets
                  if w._item.status in done_s]
        for w in dead:
            w.destroy()
            self._widgets.remove(w)
        if not self._widgets:
            self._empty_lbl.pack(expand=True, pady=60)
        self._update_counts()

    def _remove(self, widget: _ItemWidget):
        if widget._item.status == "running":
            return   # 正在跑的不让删
        widget.destroy()
        if widget in self._widgets:
            self._widgets.remove(widget)
        if not self._widgets:
            self._empty_lbl.pack(expand=True, pady=60)
        self._update_counts()

    def _view(self, item: _QueueItem):
        if item.result_data and item.result_path:
            self.app._cur_bytes = item.result_data
            self.app.cur_path   = item.result_path
            self.app._push_to_viewer(item.result_data, item.result_path)

    # ══════════════════════════════════════════════════════════
    #   队列执行（后台线程）
    # ══════════════════════════════════════════════════════════
    def _run_loop(self):
        from services.image_service import generate_image, save_image_file
        from services.translation  import has_chinese, translate_zh_to_en
        from data.repository       import add_entry

        waiting_total = len([w for w in self._widgets
                             if w._item.status == "waiting"])
        done_cnt      = 0

        for widget in list(self._widgets):
            if self._stop_flag:
                break
            if widget._item.status != "waiting":
                continue

            # 等待暂停解除
            while self._paused and not self._stop_flag:
                time.sleep(0.4)
            if self._stop_flag:
                break

            item    = widget._item
            t0      = time.time()
            idx     = done_cnt + 1

            # 标记运行中
            self.app.root.after(
                0, lambda w=widget: w.update_status("running"))
            self.app.root.after(
                0, lambda i=idx, t=waiting_total, p=item.prompt:
                self._set_prog(
                    f"🔄  [{i}/{t}]  {p[:40]}…"))

            try:
                prompt     = item.prompt
                w_n, h_n   = [int(x) for x in
                               item.size.replace("×","x").split("x")]
                translated = prompt

                if has_chinese(prompt):
                    translated = translate_zh_to_en(
                        prompt, log_cb=self.app._log)

                seed       = random.randint(0, 2_147_483_647)
                data, used = generate_image(
                    translated, w_n, h_n, seed, self.app.cfg,
                    provider_order=item.porder,
                    log_cb=self.app._log)

                path    = save_image_file(data, prompt)
                add_entry(prompt, translated, path, used)
                elapsed = time.time() - t0
                done_cnt += 1

                # 主线程回调：更新 UI + 刷新历史
                def _on_done(w=widget, d=data, p=path,
                             u=used, el=elapsed):
                    w.update_status("done",
                                    result_path=p, result_data=d,
                                    provider=u, elapsed=el)
                    # 主线程创建 PhotoImage，不在子线程中！
                    try:
                        img = Image.open(io.BytesIO(d))
                        w.set_thumb(img)
                    except Exception:
                        pass
                    self.app._refresh_hist()
                    self.app._refresh_tag_stats()
                    self.app._st(
                        f"✅ 队列完成一张  {u[:30]}", "ok")

                self.app.root.after(0, _on_done)

            except Exception as ex:
                elapsed = time.time() - t0
                emsg    = str(ex)[:120]
                self.app._log(f"❌ 队列任务失败: {emsg}")

                def _on_fail(w=widget, e=emsg, el=elapsed):
                    w.update_status("failed", error=e, elapsed=el)

                self.app.root.after(0, _on_fail)

        # 全部循环结束
        def _finish():
            self._running   = False
            self._stop_flag = False
            self._start_btn.config(state="normal", text=_("queue_btn_start"))
            self._pause_btn.config(text=_("queue_btn_pause"))
            self._paused = False
            remaining = len([w for w in self._widgets
                             if w._item.status == "waiting"])
            if remaining:
                self._set_prog(
                    f"⏹ 已完成  ·  本轮生成 {done_cnt} 张"
                    f"  ·  还有 {remaining} 个等待中（可再次点「▶ 开始」）")
            else:
                self._set_prog(
                    f"🎉 全部完成！  共生成 {done_cnt} 张图片")
            self._update_counts()

        self.app.root.after(0, _finish)

    # ══════════════════════════════════════════════════════════
    #   辅助
    # ══════════════════════════════════════════════════════════
    def _set_prog(self, msg: str):
        self._prog_lbl.config(text=msg)

    def _update_counts(self):
        total   = len(self._widgets)
        waiting = sum(1 for w in self._widgets
                      if w._item.status == "waiting")
        done    = sum(1 for w in self._widgets
                      if w._item.status == "done")
        failed  = sum(1 for w in self._widgets
                      if w._item.status == "failed")
        parts = [f"共 {total}"]
        if waiting: parts.append(f"⏳{waiting}")
        if done:    parts.append(f"✅{done}")
        if failed:  parts.append(f"❌{failed}")
        self._cnt_lbl.config(text="  ".join(parts))
