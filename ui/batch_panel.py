"""
ui/batch_panel.py  v2
─────────────────────
Fix-3: ≥4张时底部按钮栏消失
  · _Cell 内部改用 grid 布局（canvas row=0 weight=1，bot row=1 weight=0）
  · 无论父框架高度多小，bot 始终固定在行1，不会被挤压消失

Fix-4: 查看对比后点「返回」清空面板 / 无法再次生成变体
  · ctrl 和 grid_host 存为 self._ctrl / self._grid_host
  · _show_compare : pack_forget ctrl+grid_host，pack cmp_frame
  · _hide_compare : pack_forget cmp_frame，重新 pack ctrl+grid_host
  · reset() 先调用 _hide_compare() 确保面板恢复正常布局
"""
import io
import threading
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from config.fonts import F
from config.theme import DARK_THEME as C
from config.i18n import _


CELL_W    = 260
CELL_H    = 200
BOT_H     = 38        # 底部按钮栏固定高度
MAX_CELLS = 6
COLS      = 3
ROWS      = 2


class _Cell:
    """网格中的单个图片格（v2：内部用 grid 布局保证按钮栏始终可见）。"""

    def __init__(self, master: tk.Frame, idx: int, batch_panel):
        self.idx     = idx
        self.bp      = batch_panel
        self.data    = None
        self.path    = None
        self.used    = ""
        self.img_obj = None
        self._photo  = None
        self.state   = "empty"   # empty | loading | done | kept | discarded
        self.cmp_role = None     # None | "A" | "B"

        # 外框（放入 grid_host 的 grid 布局）
        self.frame = tk.Frame(master, bg=C["empty"],
                              highlightbackground=C["sep"], highlightthickness=1)
        row, col = divmod(idx, COLS)
        self.frame.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")

        # ── 内部用 grid：row0 = canvas（弹性），row1 = bot（固定 BOT_H）──
        self.frame.rowconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=0, minsize=BOT_H)
        self.frame.columnconfigure(0, weight=1)

        # 图片 Canvas
        self.canvas = tk.Canvas(self.frame, bg=C["empty"],
                                width=CELL_W, height=CELL_H,
                                bd=0, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # 占位文字
        self._ph_id = self.canvas.create_text(
            CELL_W // 2, CELL_H // 2 - 10,
            text=f"— {idx + 1} —",
            font=F["body"], fill="#334155", anchor="center")

        # 底部操作栏（固定高度，永远在 row=1）
        self.bot = tk.Frame(self.frame, bg="#0a1220", height=BOT_H)
        self.bot.grid(row=1, column=0, sticky="ew")
        self.bot.grid_propagate(False)   # 防止子控件撑开

        self.keep_btn = tk.Button(
            self.bot, text=_("btn_keep"), font=F["small_b"],
            bg=C["keep_bg"], fg="white", bd=0, padx=8, pady=3,
            cursor="hand2", state="disabled", command=self._keep)
        self.keep_btn.pack(side="left", padx=(4, 2), pady=4)

        self.dis_btn = tk.Button(
            self.bot, text=_("btn_discard"), font=F["small"],
            bg=C["dis_bg"], fg="white", bd=0, padx=8, pady=3,
            cursor="hand2", state="disabled", command=self._discard)
        self.dis_btn.pack(side="left", padx=(0, 2), pady=4)

        self.cmp_btn = tk.Button(
            self.bot, text=_("btn_compare"), font=F["small"],
            bg=C["acc"], fg="white", bd=0, padx=8, pady=3,
            cursor="hand2", state="disabled", command=self._toggle_compare)
        self.cmp_btn.pack(side="left", pady=4)

        self.status_lbl = tk.Label(
            self.bot, text="等待…", font=F["mono_tiny"],
            bg="#0a1220", fg=C["sub"])
        self.status_lbl.pack(side="right", padx=6)

    # ── 状态更新 ────────────────────────────────────────────────
    def set_loading(self):
        self.state = "loading"
        self.canvas.itemconfig(self._ph_id, text=_("batch_loading"), fill=C["warn"])
        self.frame.config(highlightbackground=C["warn"])
        self.status_lbl.config(text="生成中")

    def set_done(self, data: bytes, path: str, used: str):
        self.state   = "done"
        self.data    = data
        self.path    = path
        self.used    = used
        self.img_obj = Image.open(io.BytesIO(data))
        self._render_thumb()
        self.keep_btn.config(state="normal")
        self.dis_btn.config(state="normal")
        self.cmp_btn.config(state="normal")
        self.frame.config(highlightbackground=C["ok"])
        self.status_lbl.config(text=used[:20])

    def set_error(self, msg: str):
        self.state = "error"
        self.canvas.itemconfig(self._ph_id, text=_("batch_error"), fill=C["hl"])
        self.frame.config(highlightbackground=C["hl"])
        self.status_lbl.config(text=msg[:22])
        self.dis_btn.config(state="normal")   # 允许手动丢弃

    def _render_thumb(self):
        self.canvas.update_idletasks()
        cw = self.canvas.winfo_width()  or CELL_W
        ch = self.canvas.winfo_height() or CELL_H
        img = self.img_obj.copy()
        img.thumbnail((cw - 4, ch - 4), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2,
                                  image=self._photo, anchor="center",
                                  tags="img")
        self.canvas.bind("<Double-Button-1>",
                          lambda e: self.bp._open_cell_viewer(self))

    # ── 操作 ────────────────────────────────────────────────────
    def _keep(self):
        if self.state != "done": return
        self.bp._keep_cell(self)
        self.state = "kept"
        self.keep_btn.config(state="disabled", text="✅ 已保留", bg="#34d399")
        self.dis_btn.config(state="disabled")
        self.frame.config(highlightbackground="#34d399")

    def _discard(self):
        if self.state not in ("done", "error"): return
        self.bp._discard_cell(self)
        self.state = "discarded"
        self.canvas.delete("all")
        self.canvas.create_text(
            CELL_W // 2, CELL_H // 2,
            text="— 已丢弃 —", font=F["input"], fill="#334155")
        self.keep_btn.config(state="disabled")
        self.dis_btn.config(state="disabled")
        self.cmp_btn.config(state="disabled")
        self.frame.config(highlightbackground=C["sep"])

    def _toggle_compare(self):
        self.bp._toggle_cmp_cell(self)

    def mark_cmp(self, role):
        self.cmp_role = role
        if role == "A":
            self.frame.config(highlightbackground=C["cmp_a"], highlightthickness=2)
            self.cmp_btn.config(text="A ×", bg=C["cmp_a"])
        elif role == "B":
            self.frame.config(highlightbackground=C["cmp_b"], highlightthickness=2)
            self.cmp_btn.config(text="B ×", bg=C["cmp_b"])
        else:
            self.frame.config(highlightbackground=C["ok"], highlightthickness=1)
            self.cmp_btn.config(text=_("btn_compare"), bg=C["acc"])

    def reset(self):
        self.data = self.path = self.img_obj = self._photo = None
        self.used = ""; self.state = "empty"; self.cmp_role = None
        self.canvas.delete("all")
        self._ph_id = self.canvas.create_text(
            CELL_W // 2, CELL_H // 2 - 10,
            text=f"— {self.idx + 1} —",
            font=F["label_lg"], fill="#334155", anchor="center")
        self.keep_btn.config(state="disabled", text=_("btn_keep"), bg=C["keep_bg"])
        self.dis_btn.config(state="disabled")
        self.cmp_btn.config(state="disabled", text=_("btn_compare"), bg=C["acc"])
        self.status_lbl.config(text="等待…")
        self.frame.config(highlightbackground=C["sep"], highlightthickness=1)
        try: self.canvas.unbind("<Double-Button-1>")
        except Exception: pass


# ══════════════════════════════════════════════════════════════
class BatchPanel(tk.Frame):
    """批量变体面板主控件 v2。"""

    def __init__(self, master, parent_app):
        super().__init__(master, bg=C["bg"])
        self.app       = parent_app
        self._cells    = []
        self._n        = 0
        self._done_cnt = 0
        self._running   = False     # 防止并发 start_batch
        self._batch_gen = 0         # 版本号：旧批次 stale after() 回调通过对比自动失效
        self._cmp_a    = None
        self._cmp_b    = None
        self._cmp_mode = False
        self._on_keep  = None

        # 这两个引用在 _build 中赋值，用于 show/hide compare 切换
        self._ctrl      = None
        self._grid_host = None

        self._build()

    # ── UI 构建 ──────────────────────────────────────────────
    def _build(self):
        # ── 顶部控制栏（存引用 self._ctrl）────────────────────
        self._ctrl = tk.Frame(self, bg="#0a1220", height=44)
        self._ctrl.pack(fill="x")
        self._ctrl.pack_propagate(False)

        tk.Label(self._ctrl, text="🎲  批量变体面板",
                 font=F["small_b"], bg="#0a1220", fg=C["text"]
                 ).pack(side="left", padx=10, pady=6)

        self._progress_lbl = tk.Label(
            self._ctrl, text="", font=F["body"], bg="#0a1220", fg=C["warn"])
        self._progress_lbl.pack(side="left", padx=8)

        tk.Button(self._ctrl, text="⚖ 查看对比",
                  font=F["small_b"], bg=C["cmp_a"], fg="white",
                  bd=0, padx=8, pady=3, cursor="hand2",
                  command=self._show_compare
                  ).pack(side="right", padx=3, pady=6)
        tk.Button(self._ctrl, text=_("batch_discard_all"),
                  font=F["small_b"], bg=C["dis_bg"], fg="white",
                  bd=0, padx=8, pady=3, cursor="hand2",
                  command=self._discard_all
                  ).pack(side="right", padx=(0, 3), pady=6)
        tk.Button(self._ctrl, text=_("batch_keep_all"),
                  font=F["small_b"], bg=C["keep_bg"], fg="white",
                  bd=0, padx=8, pady=3, cursor="hand2",
                  command=self._keep_all
                  ).pack(side="right", padx=(0, 3), pady=6)

        # ── 网格容器（存引用 self._grid_host）────────────────
        self._grid_host = tk.Frame(self, bg=C["bg"])
        self._grid_host.pack(fill="both", expand=True, padx=4, pady=4)
        for c in range(COLS):
            self._grid_host.columnconfigure(c, weight=1)
        for r in range(ROWS):
            self._grid_host.rowconfigure(r, weight=1)

        for i in range(MAX_CELLS):
            cell = _Cell(self._grid_host, i, self)
            self._cells.append(cell)

        # ── 对比面板（初始不 pack，通过 show/hide 切换）──────
        self._cmp_frame = tk.Frame(self, bg="#0a0f1a")
        self._build_compare_pane()

        # ── 键盘快捷键 ────────────────────────────────────────
        self.bind("<Key-k>", lambda e: self._shortcut_keep())
        self.bind("<Key-d>", lambda e: self._shortcut_discard())
        self.bind("<Key-c>", lambda e: self._shortcut_compare())
        self.configure(takefocus=True)

    def _build_compare_pane(self):
        f = self._cmp_frame

        # 标题栏
        hdr = tk.Frame(f, bg="#0a1220", height=40)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="⚖  图片对比模式",
                 font=F["btn"], bg="#0a1220", fg="white"
                 ).pack(side="left", padx=12, pady=6)
        # ── 返回网格按钮（Fix-4: 点击后恢复 ctrl+grid_host）──
        tk.Button(hdr, text="← 返回网格", font=F["body"],
                  bg=C["acc"], fg="white", bd=0, padx=10, pady=4,
                  cursor="hand2", command=self._hide_compare
                  ).pack(side="right", padx=8, pady=5)
        tk.Button(hdr, text="🔄 交换 A/B", font=F["body"],
                  bg="#4a3a8a", fg="white", bd=0, padx=10, pady=4,
                  cursor="hand2", command=self._swap_compare
                  ).pack(side="right", padx=(0, 4), pady=5)

        # 左右分屏
        split = tk.Frame(f, bg=C["bg"]); split.pack(fill="both", expand=True)
        split.columnconfigure(0, weight=1)
        split.columnconfigure(2, weight=1)
        split.rowconfigure(0, weight=1)

        # 左（A）
        lw = tk.Frame(split, bg=C["bg"]); lw.grid(row=0, column=0, sticky="nsew")
        tk.Label(lw, text="← A  原图", font=F["btn"],
                 bg=C["cmp_a"], fg="white").pack(fill="x")
        self._cmp_cv_a = tk.Canvas(lw, bg="#0a0f1a", bd=0, highlightthickness=0)
        self._cmp_cv_a.pack(fill="both", expand=True)
        self._cmp_ph_a = None

        # 分隔线
        tk.Frame(split, bg="#2a3a5a", width=3).grid(row=0, column=1, sticky="ns")

        # 右（B）
        rw = tk.Frame(split, bg=C["bg"]); rw.grid(row=0, column=2, sticky="nsew")
        tk.Label(rw, text="B →  对比图", font=F["btn"],
                 bg=C["cmp_b"], fg="white").pack(fill="x")
        self._cmp_cv_b = tk.Canvas(rw, bg="#0a0f1a", bd=0, highlightthickness=0)
        self._cmp_cv_b.pack(fill="both", expand=True)
        self._cmp_ph_b = None

        for cv in [self._cmp_cv_a, self._cmp_cv_b]:
            cv.bind("<Configure>", lambda e, c=cv: self._render_cmp_side(c))

    # ── 批量控制 ─────────────────────────────────────────────
    def start_batch(self, n: int, params: dict,
                    translate_fn, generate_fn, save_fn,
                    log_fn, on_keep_fn):
        if self._running:
            log_fn("⚠ 批量生成正在进行中，请等待完成后再次触发")
            return
        self._running   = True
        self._batch_gen += 1   # 让所有旧批次挂起的 after() 回调失效
        self._n        = min(max(1, n), MAX_CELLS)
        self._done_cnt = 0
        self._on_keep  = on_keep_fn
        self._cmp_a    = self._cmp_b = None

        # Fix-4: 确保先回到网格视图（避免对比面板遮盖网格）
        self._hide_compare()

        # 重置所有格
        for cell in self._cells:
            cell.reset()
            if cell.idx < self._n:
                cell.frame.grid()
            else:
                cell.frame.grid_remove()

        self._progress_lbl.config(text=f"0 / {self._n}  生成中…")

        from services.translation import has_chinese

        # ── 翻译：单次执行，加锁防并发重复翻译 ──────────────────
        # 所有线程共享同一个 params dict，使用 threading.Lock 保证
        # translate 只调用一次，后续线程复用结果。
        import threading as _th
        _trans_lock = _th.Lock()
        _trans_done = _th.Event()

        def _ensure_translated():
            """线程安全地确保 params['translated'] 已完成翻译。"""
            prompt = params["prompt"]
            # 快速检查（无锁）
            if params.get("translated"):
                return params["translated"]
            with _trans_lock:
                # 双重检查（持锁后再判断）
                if params.get("translated"):
                    return params["translated"]
                if has_chinese(prompt):
                    result = translate_fn(prompt, params["cfg"], log_fn)
                    params["translated"] = result
                else:
                    params["translated"] = prompt
            return params["translated"]

        def _gen_one(cell_idx: int):
            import time as _t, random as _r

            # ── 根据质量模式确定请求间距 ──────────────────────────
            # standard：1.2s 间距（比原 0.8s 更大，减少并发限速）
            # high：    2.0s 间距（HQ 模式请求本身耗时更长，无需过密）
            # 目的：避免瞬间并发触发 API 速率限制 → 自动 fallback 到劣质模型
            base_cfg     = params.get("cfg", {})
            variant_qual = base_cfg.get("variant_quality", "high")
            stagger_sec  = 2.0 if variant_qual == "high" else 1.2
            _t.sleep(cell_idx * stagger_sec)

            # ── 每张图使用独立随机 seed，确保变体多样性 ──────────
            seed = _r.randint(0, 2_147_483_647)

            # ── 注入高质量模式标志（deep copy cfg，不修改原始对象）──
            # variant_hq=True 告知各 provider 使用更高步数/更好模型
            import copy as _copy
            hq_cfg = _copy.copy(base_cfg)
            if variant_qual == "high":
                hq_cfg["variant_hq"] = True

            # ── 翻译（线程安全，只翻译一次）──────────────────────
            try:
                translated = _ensure_translated()
            except Exception as te:
                log_fn(f"  ⚠ 翻译失败，使用原文: {te}")
                translated = params["prompt"]

            gen  = self._batch_gen   # 捕获版本号，stale-callback 检测用
            cell = self._cells[cell_idx]
            self.after(0, lambda c=cell, g=gen:
                       c.set_loading() if g == self._batch_gen else None)

            try:
                data, used = generate_fn(
                    translated,
                    params["w"], params["h"],
                    seed,
                    hq_cfg,              # 传入注入了 variant_hq 的 cfg
                    provider_order=params["porder"],
                    status_cb=lambda s: None,
                    log_cb=log_fn,
                )
                path = save_fn(data, params["prompt"])
                self.after(0, lambda c=cell, d=data, p=path, u=used, g=gen:
                           self._on_cell_done(c, d, p, u, g))
            except Exception as ex:
                self.after(0, lambda c=cell, e=str(ex), g=gen:
                           self._on_cell_error(c, e, g))

        for i in range(self._n):
            threading.Thread(target=_gen_one, args=(i,), daemon=True).start()

    def _on_cell_done(self, cell, data, path, used, gen=None):
        if gen is not None and gen != self._batch_gen:
            return   # 旧批次的 stale 回调，直接忽略
        cell.set_done(data, path, used)
        self._done_cnt += 1
        self._check_batch_progress()

    def _on_cell_error(self, cell, msg, gen=None):
        """出错也计入完成数，确保 _running 能正确重置。"""
        if gen is not None and gen != self._batch_gen:
            return
        cell.set_error(msg)
        self._done_cnt += 1
        self._check_batch_progress()

    def _check_batch_progress(self):
        if self._done_cnt < self._n:
            self._progress_lbl.config(
                text=f"{self._done_cnt} / {self._n}  生成中…")
        else:
            self._running = False
            err_cnt  = sum(1 for c in self._cells[:self._n] if c.state == "error")
            if err_cnt:
                self._progress_lbl.config(
                    text=f"⚠ {self._n - err_cnt} 张成功 / {err_cnt} 张失败  · 请检查状态")
            else:
                self._progress_lbl.config(
                    text=f"✅ 全部 {self._n} 张生成完成  · 请选择保留或丢弃")

    def reset(self):
        """完全重置面板（Fix-4: 先 hide_compare 恢复布局）。"""
        self._hide_compare()   # 确保 ctrl+grid_host 可见
        self._running = False  # 允许新批次启动
        self._cmp_a = self._cmp_b = None
        self._progress_lbl.config(text="")
        for cell in self._cells:
            cell.reset()
            cell.frame.grid()  # 恢复所有格显示

    # ── 保留 / 丢弃 ──────────────────────────────────────────
    def _keep_cell(self, cell):
        """
        保留变体 — 修复版。

        问题根因：
          1. 原代码未验证 cell.path 对应的文件是否真实存在；若文件缺失
             （多线程时序 / 并发 discard 竞争），DB 中会存入一个死路径，
             导致历史缩略图和预览都无法显示。
          2. 原代码将空字典 {} 传给 on_keep 回调，导致 _on_variant_kept
             无法知道刚保留了哪条记录，无法自动预览。
        修复策略：
          - 写 DB 前先确认文件存在；若 cell.path 无效则用 cell.data 重新
            保存（data 始终是刚从 API 拿到的原始字节，不受路径问题影响）。
          - 将 add_entry() 返回值（完整 entry dict）传给 on_keep，
            主界面可直接自动预览并高亮选中该条目。
        """
        import os
        from data.repository import add_entry

        params     = self.app._batch_params or {}
        prompt     = params.get("prompt", "")
        translated = params.get("translated", "")

        # ── 1. 确保图片文件真实存在 ──────────────────────────────
        path = cell.path

        if not path or not os.path.exists(path):
            # 原始文件不存在：用内存中的 bytes 重新保存一份
            if cell.data:
                try:
                    from services.image_service import save_image_file
                    path = save_image_file(cell.data, prompt or "variant",
                                           provider=cell.used,
                                           translated=translated)
                    cell.path = path          # 同步更新 cell 内记录
                    self.app._log(f"  ⚠ 原始文件缺失，重新保存至: {path}")
                except Exception as e:
                    self.app._log(f"⚠ 保留失败（重存图片异常）: {e}")
                    return
            else:
                self.app._log(
                    f"⚠ 保留失败：cell #{cell.idx+1} 既无有效路径也无图片数据")
                return

        # ── 2. 写入数据库，获得完整 entry（含 id / image_path）─────
        try:
            entry = add_entry(prompt, translated, path, cell.used)
        except Exception as e:
            self.app._log(f"⚠ 保留失败（数据库写入异常）: {e}")
            return

        self.app._log(f"✅ 保留变体 #{cell.idx + 1}: {path}")

        # ── 3. 将完整 entry 传给回调，主界面可直接预览 ─────────────
        if self._on_keep:
            self._on_keep(entry)

    def _discard_cell(self, cell):
        # 修复 #5：从对比槽移除，防止对比模式展示已丢弃的图片
        if self._cmp_a is cell: self._cmp_a = None
        if self._cmp_b is cell: self._cmp_b = None
        # 修复 #8：后台线程删除文件，避免主线程同步 I/O 阻塞
        if cell.path:
            import os, threading as _th
            _th.Thread(
                target=lambda p=cell.path:
                    os.remove(p) if os.path.exists(p) else None,
                daemon=True).start()
        self.app._log(f"✕ 丢弃变体 #{cell.idx + 1}")

    def _keep_all(self):
        for cell in self._cells[:self._n]:
            if cell.state == "done":
                cell._keep()

    def _discard_all(self):
        for cell in self._cells[:self._n]:
            if cell.state == "done":
                cell._discard()

    # ── 键盘快捷键 ────────────────────────────────────────────
    def _shortcut_keep(self):
        """K 键：保留第一个「完成」状态的格。"""
        for cell in self._cells[:self._n]:
            if cell.state == "done":
                cell._keep()
                return

    def _shortcut_discard(self):
        """D 键：丢弃第一个「完成」或「出错」状态的格。"""
        for cell in self._cells[:self._n]:
            if cell.state in ("done", "error"):
                cell._discard()
                return

    def _shortcut_compare(self):
        """C 键：对第一个「完成」状态的格触发对比。"""
        for cell in self._cells[:self._n]:
            if cell.state == "done":
                self._toggle_cmp_cell(cell)
                return

    # ── 对比 ─────────────────────────────────────────────────
    def _toggle_cmp_cell(self, cell):
        if cell.cmp_role == "A":
            cell.mark_cmp(None); self._cmp_a = None
        elif cell.cmp_role == "B":
            cell.mark_cmp(None); self._cmp_b = None
        elif self._cmp_a is None:
            self._cmp_a = cell; cell.mark_cmp("A")
        elif self._cmp_b is None:
            self._cmp_b = cell; cell.mark_cmp("B")
        else:
            self._cmp_b.mark_cmp(None)
            self._cmp_b = cell; cell.mark_cmp("B")

    def _show_compare(self):
        if self._cmp_a is None or self._cmp_b is None:
            from tkinter import messagebox
            messagebox.showinfo("提示",
                "请先在两张图上点击「⚖ 对比」按钮分别标记 A 和 B",
                parent=self.app.root)
            return
        if self._cmp_mode: return
        self._cmp_mode = True

        # Fix-4: 隐藏 ctrl + grid_host，显示 cmp_frame
        self._ctrl.pack_forget()
        self._grid_host.pack_forget()
        self._cmp_frame.pack(fill="both", expand=True)

        # 渲染图片（延迟一帧等 canvas 完成布局）
        self.after(50, lambda: self._draw_cmp_image(self._cmp_cv_a, self._cmp_a))
        self.after(50, lambda: self._draw_cmp_image(self._cmp_cv_b, self._cmp_b))

    def _hide_compare(self):
        """Fix-4: 正确恢复 ctrl + grid_host 布局。"""
        if not self._cmp_mode and self._cmp_frame not in self.pack_slaves():
            return  # 已经在网格视图，无需操作
        self._cmp_mode = False
        self._cmp_frame.pack_forget()
        # 按原始顺序重新 pack
        self._ctrl.pack(fill="x")
        self._ctrl.pack_propagate(False)
        self._grid_host.pack(fill="both", expand=True, padx=4, pady=4)

    def _swap_compare(self):
        self._cmp_a, self._cmp_b = self._cmp_b, self._cmp_a
        if self._cmp_a: self._cmp_a.mark_cmp("A")
        if self._cmp_b: self._cmp_b.mark_cmp("B")
        self._draw_cmp_image(self._cmp_cv_a, self._cmp_a)
        self._draw_cmp_image(self._cmp_cv_b, self._cmp_b)

    def _draw_cmp_image(self, cv, cell):
        if cell is None or cell.img_obj is None: return
        cv.update_idletasks()
        cw = cv.winfo_width()  or 400
        ch = cv.winfo_height() or 500
        img = cell.img_obj.copy()
        img.thumbnail((cw - 4, ch - 4), Image.LANCZOS)
        ph = ImageTk.PhotoImage(img)
        if cv is self._cmp_cv_a:
            self._cmp_ph_a = ph
        else:
            self._cmp_ph_b = ph
        cv.delete("all")
        cv.create_image(cw // 2, ch // 2, image=ph, anchor="center")

    def _render_cmp_side(self, cv):
        cell = self._cmp_a if cv is self._cmp_cv_a else self._cmp_b
        if cell and cell.img_obj:
            self._draw_cmp_image(cv, cell)

    def _open_cell_viewer(self, cell):
        if cell.data and cell.path:
            self.app._cur_bytes = cell.data
            self.app.cur_path   = cell.path
            self.app._open_viewer()
