# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — 跨平台构建配置（macOS → .app, Windows → .exe）

import sys
import os
import glob
import PySide6

APP_NAME = "ZhouyiUnity"
ICON_MAC = None
ICON_WIN = None

# 自动找图标
_site = os.path.dirname(PySide6.__file__)
_stock = os.path.join(_site, "scripts", "deploy_lib", "pyside_icon.icns")
if os.path.exists(_stock):
    ICON_MAC = _stock

# ── 收集数据文件（recursive glob，保持目录结构）───────────
# PyInstaller spec 不支持 datas 中的通配符，用 Python glob 展开
_datas = []
_skip_patterns = [".DS_Store", "__pycache__", ".pyc", ".7z"]
for _pattern, _dest_base in [
    ("src/data/**", "src/data"),   # 所有数据库、图标、位置数据等
    ("ui/**", "ui"),               # Qt Designer .ui 文件
]:
    for _src in glob.glob(_pattern, recursive=True):
        if not os.path.isfile(_src):
            continue
        if any(p in _src for p in _skip_patterns):
            continue
        # 保持源文件目录结构：dest = 文件所在目录
        _dest = os.path.dirname(_src)
        _datas.append((_src, _dest))

print(f"[spec] 收集数据文件: {len(_datas)} 个")
for _s, _d in _datas:
    print(f"  {_s} → {_d}")

a = Analysis(
    [os.path.join("main.py")],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
        "src", "src.main_window", "src.tabs", "src.windows",
        "src.tabs.yijing_viewer", "src.tabs.qigua",
        "src.tabs.bazhai", "src.tabs.case_manager",
        "src.windows.bazhai_window",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                        # 不显示终端窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_MAC,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)

# macOS .app bundle
app = BUNDLE(
    coll,
    name=APP_NAME + ".app",
    icon=ICON_MAC,
    bundle_identifier="com.zhouyi.unity",
    info_plist={
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
    },
)
