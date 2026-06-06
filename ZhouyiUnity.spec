# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — 跨平台构建配置（macOS → .app, Windows → .exe）

import sys
import os
import PySide6

APP_NAME = "ZhouyiUnity"
ICON_MAC = None
ICON_WIN = None

# 自动找图标
_site = os.path.dirname(PySide6.__file__)
_stock = os.path.join(_site, "scripts", "deploy_lib", "pyside_icon.icns")
if os.path.exists(_stock):
    ICON_MAC = _stock

# 源码路径
_src_data = [
    # 静态数据
    ("src/data/*/*", "src/data"),
    # 用户数据目录（空目录不会被自动打包，这里用占位）
    ("user_data/.gitkeep", "user_data"),
]

a = Analysis(
    [os.path.join("main.py")],
    pathex=[],
    binaries=[],
    datas=[
        ("user_data/.gitkeep", "user_data"),
    ],
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
