
# ZhouyiUnity Development Guide

## Project Overview
周易算命桌面应用 — PySide6 (Qt 6) 多窗口 GUI，跨平台 (macOS/Windows)。

## Tech Stack
- Python 3.12 (`/usr/local/bin/python3`)
- PySide6 6.11.1 (官方 Qt for Python, LGPL)
- Qt Designer → `.ui` files in `ui/`
- PyInstaller → `dist/ZhouyiUnity.app` or `.exe`

## Directory Map
```
ZhouyiUnity/
├── main.py              Entry point, global font 16px
├── ui/                  Qt Designer .ui files
├── src/
│   ├── main_window.py   Main window (QTabWidget, 4 tabs)
│   ├── tabs/            Tab pages: yijing_viewer, qigua, bazhai, case_manager
│   ├── windows/         Independent popup windows (e.g. bazhai_window)
│   ├── data/
│   │   ├── yijing/             易经数据库
│   │   │   ├── content/        64卦 JSONC 文件 (01_乾.jsonc ~ 64_未济.jsonc)
│   │   │   │                  nishi.diagram.description 为字符串数组
│   │   │   ├── diagram/        倪师卦图 (01.jpeg ~ 64.jpeg) + 倪师卦像图解.md
│   │   │   ├── MgrScript/      数据库管理脚本（统一入口目录）
│   │   │   │   ├── yijing_manager.py        数据库管理（编辑/备份/恢复/批量字段）
│   │   │   │   ├── sync_structure.py        格式刷（模板同步+字段清理+格式化）
│   │   │   │   ├── import_nishi_diagram.py  解析 MD → 写入 description（数组格式，含自修改）
│   │   │   ├── import_home_fields.py     上卦→member, 下卦→direction（含自修改）
│   │   │   │   └── 易经数据库管理.command   macOS 双击入口（菜单选择工具）
│   │   │   └── content.bkp.zip      数据库压缩备份
│   │   ├── stems_branches.py   干支/五行/生肖 lookup
│   │   └── ziwei_stars.py      紫微斗数星曜数据
│   ├── algorithms/      Pure computation (calendar convert, bazi pan, qigua calc)
│   ├── models/          Data structures (User, Gua, Case)
│   └── utils/           Helpers (SQLite wrapper, etc.)
├── user_data/           User runtime data (JSON / SQLite)
├── build.sh     Cross-platform build → dist/
├── build/               PyInstaller temp (gitignored)
└── dist/                Final .app / .exe (gitignored)
```

## Key Conventions
- Font: system-default CJK (PingFang SC on Mac, Microsoft YaHei on Win), fallback Noto Sans CJK SC
- Chinese comments OK, English identifiers
- UI logic in `src/`, UI layout in `ui/` — separate them
- Static reference data (卦辞, 干支表) → `src/data/`, computational algorithms → `src/algorithms/`
- 项目工程会移动，所有脚本中的路径显示/引用使用相对路径（避免硬编码绝对路径）

## Build
```bash
bash build/build.sh          # Full build → dist/ZhouyiUnity.app
bash build/build.sh clean    # Clean build artifacts
```

## Run for Development
```bash
cd ~/Desktop/ZhouyiUnity
python3 main.py
```
