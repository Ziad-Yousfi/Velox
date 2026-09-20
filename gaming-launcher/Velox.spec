# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

# SPECPATH is provided by PyInstaller and points to gaming-launcher
base_dir = SPECPATH

added_files = [
    (os.path.join(base_dir, 'icon'), 'icon'),
    (os.path.join(base_dir, 'assets'), 'assets'),
]

hidden_imports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'pyqtgraph',
    'numpy',
    'PIL',
    'PIL.Image',
    'PIL.ImageQt',
    'win32gui',
    'win32process',
    'win32api',
    'win32con',
    'sqlite3',
]

a = Analysis(
    [os.path.join(base_dir, 'main.py')],
    pathex=[base_dir],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Velox',
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
    icon=os.path.join(base_dir, 'icon', 'velox.ico'),
)
