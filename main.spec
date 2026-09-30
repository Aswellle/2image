# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules

# Use SPECPATH so the spec works on any machine
_root = SPECPATH
_provider_modules = collect_submodules("services.providers")

# SUP-001: 随安装包分发字体（构建前由 tools/fetch_fonts.py 获取；
# 目录为空时跳过，运行时回退系统字体）
_datas = [(os.path.join(_root, 'ICON_256x256.ico'), '.')]
_fonts_dir = os.path.join(_root, 'assets', 'fonts')
if os.path.isdir(_fonts_dir):
    for _f in os.listdir(_fonts_dir):
        _fp = os.path.join(_fonts_dir, _f)
        if os.path.isfile(_fp):
            _datas.append((_fp, 'fonts'))

a = Analysis(
    [os.path.join(_root, 'main.py')],
    pathex=[_root],
    binaries=[],
    datas=_datas,
    hiddenimports=_provider_modules,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 防止用户数据文件被误打包进 exe
        'config.json',
        'history.db',
        'history.json',
        'debug.log',
        '.env',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='text2image_pro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(_root, 'ICON_256x256.ico')],
)
