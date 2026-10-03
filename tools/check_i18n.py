"""
tools/check_i18n.py — i18n 质量门（I18N-001）
─────────────────────────────────────────────
两个检查：

1. --missing-keys   各 locale（zh-CN/en/ja/zh-TW）的 key 集合必须一致。
                    缺失即失败（硬门槛）。

2. --hardcoded      AST 扫描 ui/ 与 services/application/ 中包含中文的
                    字符串字面量（排除注释、日志调用 —— 文档 §35 允许
                    注释和开发日志不翻译）。配合 --baseline 使用棘轮模式：
                    基线之外的**新增**硬编码即失败，存量靠后续清扫消化。

用法：
    python tools/check_i18n.py --missing-keys
    python tools/check_i18n.py --hardcoded                       # 仅报告
    python tools/check_i18n.py --hardcoded --baseline FILE       # 棘轮模式
    python tools/check_i18n.py --hardcoded --update-baseline FILE
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ["ui", "services/application"]
I18N_MODULE = "config/i18n.py"

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
# 这些调用里的中文视为开发日志/调试信息，允许不翻译（§35）
_LOGGISH = {"log", "log_cb", "_log", "log_to_file", "make_log_callback",
            "debug", "info", "warning", "error", "print"}
# 关键词参数中的字符串视为用户可见
_VISIBLE_KWARGS = {"text", "label", "title", "message", "msg", "values",
                   "initialfile", "confirm", "tooltip", "placeholder"}


# ── 缺失 key 检查 ──────────────────────────────────────────────

def load_strings() -> dict:
    src = (PROJECT_ROOT / I18N_MODULE).read_text(encoding="utf-8")
    module = ast.parse(src)
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, "id", "") == "STRINGS":
                    return ast.literal_eval(node.value)
    raise SystemExit(f"未在 {I18N_MODULE} 中找到 STRINGS 字典")


def check_missing_keys() -> int:
    strings = load_strings()
    if not strings:
        print("STRINGS 为空", file=sys.stderr)
        return 1
    # 参照 locale = 各 locale key 集合的并集
    locales: dict[str, set] = {}
    for key, translations in strings.items():
        if isinstance(translations, dict):
            for loc in translations:
                locales.setdefault(loc, set()).add(key)
    if not locales:
        print("STRINGS 结构异常：期望 {key: {locale: text}}", file=sys.stderr)
        return 1
    all_keys = set(strings.keys())
    failed = 0
    for loc, keys in sorted(locales.items()):
        missing = all_keys - keys
        if missing:
            failed = 1
            print(f"[missing-keys] locale '{loc}' 缺少 {len(missing)} 个 key:")
            for k in sorted(missing)[:10]:
                print(f"    {k}")
            if len(missing) > 10:
                print(f"    … 共 {len(missing)} 个")
    if not failed:
        print(f"[missing-keys] OK — {len(strings)} keys × {len(locales)} locales 一致")
    return failed


# ── 硬编码扫描 ─────────────────────────────────────────────────

def _is_loggish(node: ast.AST, parents: dict) -> bool:
    """字符串位于日志类调用（直接参数或关键字值）中。"""
    cur = node
    while True:
        parent = parents.get(id(cur))
        if parent is None:
            return False
        if isinstance(parent, ast.Call):
            fn = parent.func
            name = getattr(fn, "id", "") or getattr(fn, "attr", "")
            if name in _LOGGISH or "log" in name.lower():
                return True
            return False
        cur = parent


def _visible_string(node: ast.Constant, parents: dict) -> bool:
    """可见性启发式：位置参数中的中文，或可见关键字参数中的中文 → True；
    日志调用中的中文 → False。"""
    if _is_loggish(node, parents):
        return False
    parent = parents.get(id(node))
    if isinstance(parent, ast.keyword):
        if parent.arg in _VISIBLE_KWARGS:
            return True
        return _is_loggish(parent, parents) is False and parent.arg is None
    return True  # 位置参数 / f-string 片段：保守视为可见


def scan_hardcoded() -> list[dict]:
    findings: list[dict] = []
    for scan_dir in SCAN_DIRS:
        base = PROJECT_ROOT / scan_dir
        if not base.is_dir():
            continue
        for py in sorted(base.rglob("*.py")):
            rel = str(py.relative_to(PROJECT_ROOT)).replace("\\", "/")
            if ".history" in rel:
                continue
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                print(f"[hardcoded] 无法解析 {rel}: {exc}", file=sys.stderr)
                continue
            parents = {}
            for parent in ast.walk(tree):
                for child in ast.iter_child_nodes(parent):
                    parents[id(child)] = parent
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if _CJK_RE.search(node.value) and _visible_string(node, parents):
                        findings.append({
                            "file": rel,
                            "line": node.lineno,
                            "text": node.value.strip()[:60],
                        })
    return findings


def report_hardcoded(baseline_path: str | None, update: bool) -> int:
    findings = scan_hardcoded()
    if update:
        Path(baseline_path).write_text(
            json.dumps(findings, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[hardcoded] 基线已更新：{len(findings)} 条 → {baseline_path}")
        return 0
    if not baseline_path:
        by_file: dict[str, int] = {}
        for f in findings:
            by_file[f["file"]] = by_file.get(f["file"], 0) + 1
        print(f"[hardcoded] 共 {len(findings)} 处待清扫（--baseline 启用棘轮模式）：")
        for file, cnt in sorted(by_file.items(), key=lambda x: -x[1]):
            print(f"    {cnt:4d}  {file}")
        return 0
    base = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    # 棘轮键只用 (file, text)：行号会随任何编辑漂移，纳入键会让存量
    # 字符串被误报为新增（v2.4.1 曾因此阻断发布）
    base_set = {(f["file"], f["text"]) for f in base}
    new = [f for f in findings if (f["file"], f["text"]) not in base_set]
    if new:
        print(f"[hardcoded] 发现 {len(new)} 处**新增**硬编码中文：", file=sys.stderr)
        for f in new[:20]:
            print(f"    {f['file']}:{f['line']}  {f['text']}", file=sys.stderr)
        return 1
    print(f"[hardcoded] OK — 无新增（基线 {len(base)} 条，存量待清扫）")
    return 0


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="i18n 质量门（I18N-001）")
    parser.add_argument("--missing-keys", action="store_true",
                        help="校验各 locale key 集合一致（硬门槛）")
    parser.add_argument("--hardcoded", action="store_true",
                        help="扫描硬编码中文字符串")
    parser.add_argument("--baseline", metavar="FILE",
                        help="棘轮模式：仅报告基线之外的新增项并返回非零")
    parser.add_argument("--update-baseline", metavar="FILE", dest="update_baseline",
                        help="将当前扫描结果写入基线文件并退出")
    args = parser.parse_args()

    if not args.missing_keys and not args.hardcoded:
        parser.print_help()
        return 2

    rc = check_missing_keys() if args.missing_keys else 0
    if args.hardcoded:
        if args.update_baseline:
            rc |= report_hardcoded(args.update_baseline, update=True)
        else:
            rc |= report_hardcoded(args.baseline, update=False)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
