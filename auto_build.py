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

# 配置区（动态路径，适用于任意机器）
PROJECT_DIR = Path(__file__).resolve().parent
MAIN_PY      = str(PROJECT_DIR / "main.py")
ICON         = str(PROJECT_DIR / "ICON_256x256.ico")
DIST_DIR     = str(PROJECT_DIR / "dist")
BUILD_DIR    = str(PROJECT_DIR / "build")
VERSION_FILE = str(PROJECT_DIR / "version.json")
INNO_TEMPLATE = str(PROJECT_DIR / "installer" / "template.iss")
ISCC_PATH = "ISCC"  # 或 Inno Setup 的完整路径
APP_EXE_NAME = "text2image_pro"

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


def _clean_build_dirs():
    """Clean dist/ and build/ directories to prevent stale data from leaking into releases."""
    import shutil
    for d in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
            print(f"已清除: {d}")

# 1. PyInstaller 打包（使用 main.spec，输出名称固定为 text2image_pro.exe）
def pyinstaller_build():
    _clean_build_dirs()
    spec_file = str(PROJECT_DIR / "main.spec")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",            # 清除 PyInstaller 缓存，防止旧数据残留
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        spec_file          # spec 文件已定义 name/icon/console 等，不再重复传参
    ]
    print("运行 PyInstaller:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.stdout:
        sys.stdout.buffer.write(result.stdout.encode("utf-8", errors="replace"))
        sys.stdout.flush()
    if result.stderr:
        sys.stderr.buffer.write(result.stderr.encode("utf-8", errors="replace"))
        sys.stderr.flush()
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
        "APP_EXE_NAME": APP_EXE_NAME,
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
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.stdout:
        sys.stdout.buffer.write(result.stdout.encode("utf-8", errors="replace"))
        sys.stdout.flush()
    if result.stderr:
        sys.stderr.buffer.write(result.stderr.encode("utf-8", errors="replace"))
        sys.stderr.flush()
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
