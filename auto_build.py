#!/usr/bin/env python3
"""
自动化一键打包脚本：
1. 用 PyInstaller 打包 main.py 为 exe
2. 用 Inno Setup 打包 dist 目录为安装包
3. 自动记录版本号
"""
import os
import subprocess
import sys
import json
from pathlib import Path

# 配置区
PROJECT_DIR = r"D:\Chrome Downloads\Programs\text_to_iamge_app_refactored"
MAIN_PY = os.path.join(PROJECT_DIR, "main.py")
ICON = os.path.join(PROJECT_DIR, "ICON_256x256.ico")
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
BUILD_DIR = os.path.join(PROJECT_DIR, "build")
VERSION_FILE = os.path.join(PROJECT_DIR, "version.json")
INNO_TEMPLATE = os.path.join(PROJECT_DIR, "installer", "template.iss")
ISCC_PATH = "ISCC"  # 或 Inno Setup 的完整路径

# 读取版本号
def get_version():
    if not os.path.exists(VERSION_FILE):
        return "1.0.0"
    with open(VERSION_FILE, encoding="utf-8") as f:
        return json.load(f)["version"]

def update_version(version):
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        json.dump({"version": version}, f, ensure_ascii=False, indent=2)
    print(f"已记录新版本号: {version}")

# 1. PyInstaller 打包
def pyinstaller_build():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--onefile",
        f"--icon={ICON}",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        MAIN_PY
    ]
    print("运行 PyInstaller:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        print("PyInstaller 打包失败！", file=sys.stderr)
        sys.exit(result.returncode)

# 2. Inno Setup 打包
def inno_setup_build(app_name, version):
    # 生成临时 .iss 文件
    with open(INNO_TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    ctx = {
        "APP_NAME": app_name,
        "APP_VERSION": version,
        "OUTPUT_BASE": f"{app_name}_v{version}",
        "SRC_DIR": DIST_DIR.replace('\\', '\\\\'),
        "ICON_PATH": ICON.replace('\\', '\\\\'),
        "ICON_BASENAME": os.path.basename(ICON)
    }
    for k, v in ctx.items():
        tpl = tpl.replace(f'{{{k}}}', str(v))
    iss_path = os.path.join(PROJECT_DIR, "installer", f"auto_{version}.iss")
    with open(iss_path, "w", encoding="utf-8") as f:
        f.write(tpl)
    cmd = [ISCC_PATH, iss_path]
    print("运行 Inno Setup:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        print("Inno Setup 打包失败！", file=sys.stderr)
        sys.exit(result.returncode)

if __name__ == "__main__":
    version = get_version()
    app_name = "text2image_pro"
    pyinstaller_build()
    inno_setup_build(app_name, version)
    update_version(version)
    print("全部打包流程完成！")
