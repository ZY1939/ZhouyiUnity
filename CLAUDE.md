
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
│   ├── data/            Static lookup tables (64 hexagrams, stems/branches, ziwei stars)
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
