#!/usr/bin/env python3
"""
构建 Inno Setup 安装包的工具，集成ICON和版本号管理。
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import json

DEFAULT_TEMPLATE = os.path.join(os.path.dirname(__file__), '..', 'installer', 'template.iss')
DEFAULT_ICON = r"D:\Chrome Downloads\1.Vibe Coding文生图一站式程序项目更新仓库\text_to_iamge_app_refactored\ICON_256x256.ico"
VERSION_FILE = os.path.join(os.path.dirname(__file__), '..', 'version.json')


def render_template(template_text: str, ctx: dict) -> str:
    for k, v in ctx.items():
        template_text = template_text.replace(f'{{{k}}}', str(v))
    return template_text


def update_version(version: str):
    data = {"version": version}
    with open(VERSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已记录新版本号: {version}")


def build(app_name: str, version: str, src_dir: str, out_dir: str, iscc_path: str, output_base: str = None, icon_path: str = None):
    if not icon_path:
        icon_path = DEFAULT_ICON
    icon_abspath = os.path.abspath(icon_path)
    icon_basename = os.path.basename(icon_abspath)
    template_path = DEFAULT_TEMPLATE
    with open(template_path, 'r', encoding='utf-8') as f:
        template_text = f.read()
    ctx = {
        'APP_NAME': app_name,
        'APP_VERSION': version,
        'OUTPUT_BASE': output_base or app_name,
        'SRC_DIR': os.path.abspath(src_dir).replace('\\', '\\\\'),
        'ICON_PATH': icon_abspath.replace('\\', '\\\\'),
        'ICON_BASENAME': icon_basename,
    }
    rendered = render_template(template_text, ctx)
    with tempfile.NamedTemporaryFile('w', suffix='.iss', delete=False, encoding='utf-8') as f:
        iss_path = f.name
        f.write(rendered)
    print(f"生成临时 .iss：{iss_path}")
    cmd = [iscc_path, iss_path]
    print('调用 Inno Setup 编译器:', ' '.join(cmd))
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    if proc.returncode != 0:
        print(f"Inno Setup 编译失败，返回码: {proc.returncode}", file=sys.stderr)
        sys.exit(proc.returncode)
    print('编译完成。输出文件位于 Inno Setup 默认输出目录（通常是 .\\Output）或 .iss 中定义的位置。')
    update_version(version)


def main():
    p = argparse.ArgumentParser(description='Build Inno Setup installer for this project')
    p.add_argument('--app-name', required=True)
    p.add_argument('--version', required=True)
    default_src = str(Path(__file__).resolve().parents[1])
    p.add_argument('--src-dir', default=default_src)
    p.add_argument('--out-dir', default='dist')
    p.add_argument('--iscc-path', default='ISCC', help='Path to Inno Setup Compiler (ISCC). If in PATH, just use ISCC')
    p.add_argument('--icon-path', default=None, help='Path to application icon to include (optional). Defaults to <src-dir>/ICON_256x256.ico')
    p.add_argument('--output-base', default=None, help='Output base filename for the installer')
    args = p.parse_args()
    build(args.app_name, args.version, args.src_dir, args.out_dir, args.iscc_path, args.output_base, args.icon_path)

if __name__ == '__main__':
    main()
