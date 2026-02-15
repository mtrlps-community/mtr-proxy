# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import PyInstaller.utils.win32.versioninfo as versioninfo

# 获取 Python 安装目录（在构建时动态获取）
python_dir = os.path.dirname(sys.executable)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        (os.path.join(python_dir, 'python312.dll'), '.'),  # 强制打包 python312.dll 到根目录
    ],
    datas=[],
    hiddenimports=['PySide6', 'requests'],
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
    name='MTR-accelerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                # 对应 --windowed
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
