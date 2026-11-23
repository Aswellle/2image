"""
tests/e2e/conftest.py — 端到端驾驶舱
────────────────────────────────────
真实 App（全控件、全业务层）+ 隔离磁盘（继承 tests/conftest.py 的
isolate_real_config）+ 内存库 + 可编程假 provider（网络边界桩）。

假 provider 打在 services.providers.ALL_PROVIDERS 注册表条目上——
image_service 以同一 dict 对象解析 provider 调用方，patch 即生效；
编排器/重试/回退/落盘/历史/UI 刷新全部走真实代码路径。
"""

from __future__ import annotations

import io
import tkinter as tk
import traceback

import pytest
from PIL import Image


def make_png_bytes(width: int = 64, height: int = 64, color=(70, 204, 163)) -> bytes:
    """生成最小真实 PNG（走真实 save_image_file 解码链路）。"""
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


class FakeProvider:
    """可编程假 provider：成功返回 PNG / 指定失败 / 延迟。"""

    def __init__(self):
        self.calls: list[dict] = []
        self.fail = False
        self.png = make_png_bytes()
        self.display = "FakeProvider/fake-model"

    def __call__(self, prompt: str, w: int, h: int, seed, cfg: dict, log) -> tuple[bytes, str]:
        self.calls.append({"prompt": prompt, "w": w, "h": h, "seed": seed})
        if self.fail:
            raise RuntimeError("fake provider forced failure")
        return self.png, self.display


@pytest.fixture
def e2e(tk_root, monkeypatch, tmp_path):
    """端到端驾驶舱：yield (app, root, monkeypatch)，并挂假 provider 工厂。

    用文件库而非 :memory:——内存 SQLite 每线程独立连接，队列等真实
    worker 线程写入的记录主线程不可见；文件库跨线程共享，也更贴近实机。
    """
    import data.repository as repo
    from config.fonts import init_fonts
    from config.settings import DEFAULT_CONFIG
    import ui.app as app_mod

    repo._set_test_db(str(tmp_path / "e2e_history.db"))
    repo.init_db()
    init_fonts()
    cfg = dict(DEFAULT_CONFIG)
    cfg["show_wizard_on_start"] = False
    cfg["pollinations_enabled"] = True
    saved = {}
    monkeypatch.setattr(app_mod, "load_config", lambda: dict(cfg))
    monkeypatch.setattr(app_mod, "save_config", lambda c: saved.update(dict(c)))
    top = tk.Toplevel(tk_root)
    top.withdraw()
    a = app_mod.App(top)
    tk_root.update()

    harness = E2EHarness(a, tk_root, monkeypatch, saved)
    # 全局打桩所有模态对话框：CI/无人值守环境下 messagebox 会永久阻塞
    # 等待点击（CI 曾因此挂起数小时被取消）。所有模块都 `from tkinter
    # import messagebox` 引用同一模块对象，改属性即全局生效；对话框调用
    # 被记录到 harness.dialogs 供断言。
    harness.patch_modals()
    # 单图生成默认内联化：Tcl 单线程约束下，后台线程的 after 派发只在
    # 解释器处于事件循环时合法——测试里生成点击与等待之间存在竞争窗口。
    # 内联后业务链路（翻译→编排→provider→落盘→UI 回调）全部真实，
    # 仅线程调度同步化；after(0,...) 回调仍需泵事件才执行。
    harness.inline_generation()
    # Tk 回调异常默认只打印到 stderr，用例照常通过——多候选进度
    # TypeError 曾因此漏检。挂记录器，teardown 时把回调异常判为失败。
    previous_hook = tk_root.report_callback_exception
    tk_root.report_callback_exception = harness._record_callback_exception
    yield harness
    tk_root.report_callback_exception = previous_hook
    try:
        top.destroy()
    except tk.TclError:
        pass
    assert not harness.callback_errors, "Tk 回调期间抛出异常（界面状态可能已部分失效）：\n" + "\n".join(
        harness.callback_errors[:3]
    )


class E2EHarness:
    """App + 驱动工具 + provider 桩的聚合入口。"""

    def __init__(self, app, root, monkeypatch, saved):
        self.app = app
        self.root = root
        self.mp = monkeypatch
        self.saved = saved
        self.dialogs: list[tuple] = []  # (kind, title, message, kwargs)
        self.callback_errors: list[str] = []  # Tk 回调异常（teardown 判失败）

    def _record_callback_exception(self, exc, val, tb) -> None:
        text = "".join(traceback.format_exception(exc, val, tb))
        # 参数绑定类 TypeError 不会为 lambda 建帧，补记回调函数出处便于定位
        try:
            frame = tb.tb_frame
            func = frame.f_locals.get("self").func
            text += (
                f"\n[callback] {func.__qualname__} @ {func.__code__.co_filename}:{func.__code__.co_firstlineno}"
                f" args={frame.f_locals.get('args')!r}"
            )
        except Exception:
            pass
        self.callback_errors.append(text)

    # ── 模态对话框打桩 ───────────────────────────────────────
    def patch_modals(self):
        """把 messagebox 的模态函数替换为记录器（永不阻塞、永不弹窗）。"""
        import tkinter.messagebox as mb

        def _recorder(kind: str, ret):
            def _fn(*args, **kwargs):
                title = args[0] if args else kwargs.get("title", "")
                message = args[1] if len(args) > 1 else kwargs.get("message", "")
                self.dialogs.append((kind, title, message, dict(kwargs)))
                return ret

            return _fn

        for kind in ("showwarning", "showinfo", "showerror"):
            self.mp.setattr(mb, kind, _recorder(kind, None))
        for kind in ("askyesno", "askokcancel", "askretrycancel"):
            self.mp.setattr(mb, kind, _recorder(kind, True))

        # 文件对话框同样会阻塞：默认一律「取消」（返回空串），
        # 需要真实选择的测试在用例内再次打桩覆盖（monkeypatch 后设者生效）
        import tkinter.filedialog as fd

        for kind in ("askopenfilename", "asksaveasfilename", "askdirectory"):
            self.mp.setattr(fd, kind, lambda *a, **k: "")

    def dialog_kinds(self) -> list:
        return [k for k, *_rest in self.dialogs]

    # ── provider 桩 ──────────────────────────────────────────
    def install_fake_provider(self, name: str = "pollinations") -> FakeProvider:
        """把注册表里的指定 provider 换成可编程假实现。"""
        from services.providers import ALL_PROVIDERS

        fake = FakeProvider()
        self.mp.setitem(ALL_PROVIDERS, name, fake)
        return fake

    def inline_generation(self):
        """单图生成线程内联化（仅线程调度，业务链路保持真实）。"""
        import services.application.generation_controller as gc

        class _InlineThread:
            def __init__(self, target=None, daemon=False, args=(), kwargs=None, **kw):
                self._target = target
                self._args = args or ()

            def start(self):
                self._target(*self._args)

        self.mp.setattr(gc, "threading", type("_M", (), {"Thread": _InlineThread}))

    def provider_display(self, name: str = "pollinations") -> str:
        """stable id → UI 下拉框里的展示名。"""
        from services.providers import display_name_for

        return display_name_for(name)

    # ── 常用断言前泵 ─────────────────────────────────────────
    def pump(self, times: int = 5):
        from tests.e2e.driver import pump

        pump(self.root, times)

    def wait_until(self, predicate, timeout_ms: int = 8000) -> bool:
        from tests.e2e.driver import wait_until

        return wait_until(self.root, predicate, timeout_ms)

    def history_count(self) -> int:
        from data.repository import count_entries

        return count_entries()

    # ── 常用操作 ─────────────────────────────────────────────
    def set_prompt(self, text: str):
        from tests.e2e.driver import clear_text, type_into_text

        clear_text(self.app.content.pt)
        type_into_text(self.app.content.pt, text)

    def select_provider(self, name: str = "pollinations"):
        from tests.e2e.driver import set_combobox

        set_combobox(self.app.content._provider_cb, self.provider_display(name))

    def click_generate(self):
        from tests.e2e.driver import invoke_btn

        invoke_btn(self.app.content.gb)

    def patch_filedialog(self, chooser: str, return_value: str):
        """把指定文件对话框选择器打桩到固定返回值（全局模块级）。"""
        import tkinter.filedialog as fd

        self.mp.setattr(fd, chooser, lambda *a, **k: return_value)
