# -*- mode: python ; coding: utf-8 -*-
# tools/updater/updater.spec — 2image_updater.exe (standalone update runner)
#
# Bundles the services.updater package (stdlib-only logic) so the
# updater shares the pending/success marker + log helpers with the app.
import os

_root = os.path.abspath(os.path.join(SPECPATH, "..", ".."))

a = Analysis(
    ["updater.py"],
    pathex=[_root],
    binaries=[],
    datas=[],
    hiddenimports=[
        "services",
        "services.updater",
        "services.updater.errors",
        "services.updater.version",
        "services.updater.manifest",
        "services.updater.downloader",
        "services.updater.installer",
        "services.updater.state",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="2image_updater",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # windowed: fatal states surface via MessageBoxW
    icon=os.path.join(_root, "ICON_256x256.ico"),
)
