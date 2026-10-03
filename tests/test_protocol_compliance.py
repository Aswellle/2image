"""协议与实现漂移回归测试。

背景（v2.4.0 启动崩溃）：app.py 重构删除了 ``_reset_view`` / ``_st``，
但 SidebarProtocol 仍声明、sidebar.py 仍调用 ``self.app._reset_view``，
导致便携版启动即 ``AttributeError``。本测试静态校验：

1. 两个 Protocol 声明的每个方法都在 ``App`` 上有实现或属性赋值；
2. 面板代码里每个 ``self.app.X`` 引用都落在 ``App`` 表面上。

纯 AST 检查，无需 Tk 实例，可在无显示环境运行。
"""

import ast
from pathlib import Path

import pytest

UI_DIR = Path(__file__).resolve().parent.parent / "ui"
PANEL_FILES = [
    "sidebar.py",
    "main_content.py",
    "batch_panel.py",
    "queue_panel.py",
    "viewer.py",
    "prompt_wizard.py",
    "phrase_panel.py",
    "wizard_free.py",
    "wizard_paid.py",
    "stats_dashboard.py",
]


def _class_def(tree: ast.AST, name: str) -> ast.ClassDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise pytest.fail(f"class {name} not found")


def _protocol_methods(path: Path, protocol_name: str) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = _class_def(tree, protocol_name)
    methods = set()
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.add(node.name)
    return methods


def _app_surface() -> set:
    """App 类上定义的方法名 + self 属性赋值名（含 __init__ 动态属性）。"""
    tree = ast.parse((UI_DIR / "app.py").read_text(encoding="utf-8"))
    app_cls = _class_def(tree, "App")
    surface = set()
    for node in ast.walk(app_cls):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            surface.add(node.name)
        elif (isinstance(node, ast.Attribute)
              and isinstance(node.value, ast.Name) and node.value.id == "self"
              and isinstance(node.ctx, ast.Store)):
            surface.add(node.attr)
    return surface


def _app_refs(path: Path) -> dict:
    """收集 self.app.X 引用（含 self.app.root 之类，跳过 app 本身）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    refs = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        inner = node.value
        if (isinstance(inner, ast.Attribute) and inner.attr == "app"
                and isinstance(inner.value, ast.Name) and inner.value.id == "self"):
            refs.setdefault(node.attr, []).append(node.lineno)
    return refs


def test_app_implements_sidebar_protocol():
    surface = _app_surface()
    missing = _protocol_methods(UI_DIR / "app_protocol.py", "SidebarProtocol") - surface
    assert not missing, f"SidebarProtocol declared but App missing: {sorted(missing)}"


def test_app_implements_main_content_protocol():
    surface = _app_surface()
    missing = _protocol_methods(UI_DIR / "app_protocol.py", "MainContentProtocol") - surface
    assert not missing, f"MainContentProtocol declared but App missing: {sorted(missing)}"


@pytest.mark.parametrize("fname", PANEL_FILES)
def test_panel_app_refs_exist_on_app(fname):
    path = UI_DIR / fname
    if not path.exists():
        pytest.skip(f"{fname} not present")
    surface = _app_surface()
    missing = {k: v for k, v in _app_refs(path).items() if k not in surface}
    assert not missing, (
        f"{fname} references self.app.<X> not defined on App: {missing}"
    )


def test_app_self_references_defined():
    """app.py 内部 self._X 调用都应有定义（v2.4.0 曾缺失 _st）。"""
    path = UI_DIR / "app.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    surface = _app_surface()
    missing = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name) and node.value.id == "self"
                and not isinstance(node.ctx, ast.Store)
                and node.attr not in surface):
            missing.setdefault(node.attr, []).append(node.lineno)
    # 内建/继承自 tk.Tk 的方法不算缺失
    builtin_like = {n for n in missing if not n.startswith("_") or n.startswith("__")}
    unknown = {k: v for k, v in missing.items()
               if k not in builtin_like and k != "root"}
    assert not unknown, f"app.py references undefined self attributes: {unknown}"
