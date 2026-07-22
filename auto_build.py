#!/usr/bin/env python3
"""Build the portable executable and Windows installer."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
ICON = PROJECT_DIR / "ICON_256x256.ico"
DIST_DIR = PROJECT_DIR / "dist"
BUILD_DIR = PROJECT_DIR / "build"
INSTALLER_DIR = PROJECT_DIR / "installer"
INSTALLER_OUTPUT_DIR = INSTALLER_DIR / "Output"
VERSION_FILE = PROJECT_DIR / "version.json"
INNO_TEMPLATE = INSTALLER_DIR / "template.iss"
ISCC_PATH = "ISCC"
APP_EXE_NAME = "text2image_pro"
APP_NAME = "text2image_pro"


def get_version() -> str:
    try:
        version = json.loads(VERSION_FILE.read_text(encoding="utf-8"))["version"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise RuntimeError(f"无法读取版本文件: {VERSION_FILE}") from exc
    if not isinstance(version, str) or not version:
        raise RuntimeError(f"版本号无效: {version!r}")
    return version


def _run(command: list[str], label: str) -> None:
    print(f"{label}: {' '.join(command)}")
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode:
        raise RuntimeError(f"{label}失败，退出码: {result.returncode}")


def _require_file(path: Path, label: str) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"未生成{label}: {path}")
    return path


def _clean_output_dirs() -> None:
    for directory in (DIST_DIR, BUILD_DIR, INSTALLER_OUTPUT_DIR):
        if directory.exists():
            shutil.rmtree(directory)
            print(f"已清除: {directory}")


def pyinstaller_build() -> Path:
    _clean_output_dirs()
    _run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            f"--distpath={DIST_DIR}",
            f"--workpath={BUILD_DIR}",
            str(PROJECT_DIR / "main.spec"),
        ],
        "运行 PyInstaller",
    )
    return _require_file(DIST_DIR / f"{APP_EXE_NAME}.exe", "便携版可执行文件")


def render_installer_script(version: str) -> str:
    template = INNO_TEMPLATE.read_text(encoding="utf-8")
    values = {
        "APP_NAME": APP_NAME,
        "APP_VERSION": version,
        "APP_EXE_NAME": APP_EXE_NAME,
        "OUTPUT_BASE": f"{APP_NAME}_v{version}",
        "OUTPUT_DIR": str(INSTALLER_OUTPUT_DIR),
        "SRC_DIR": str(DIST_DIR),
        "ICON_PATH": str(ICON),
        "ICON_BASENAME": ICON.name,
    }
    for key, value in values.items():
        template = template.replace(f"{{{key}}}", value)
    return template


def write_installer_script(version: str) -> Path:
    script = INSTALLER_DIR / f"auto_{version}.iss"
    script.write_text(render_installer_script(version), encoding="utf-8")
    return script


def inno_setup_build(version: str) -> Path:
    script = write_installer_script(version)
    _run([ISCC_PATH, str(script)], "运行 Inno Setup")
    return _require_file(
        INSTALLER_OUTPUT_DIR / f"{APP_NAME}_v{version}.exe",
        "Windows 安装程序",
    )


def main() -> None:
    version = get_version()
    portable_exe = pyinstaller_build()
    installer_exe = inno_setup_build(version)
    print("全部打包流程完成！")
    print(f"便携版: {portable_exe}")
    print(f"安装版: {installer_exe}")


if __name__ == "__main__":
    main()
