#!/bin/bash
cd "$(dirname "$0")"

# ============================================
#  ZhouyiUnity 一键启动
#  1. VS Code（后台）
#  2. Qt Designer（后台）
#  3. Claude Code（前台，终端保留）
# ============================================

# 1. 启动 VS Code
code . --new-window &

# 2. 启动 Qt Designer
DESIGNER="/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/PySide6/Designer.app/Contents/MacOS/Designer"
if [ -x "$DESIGNER" ]; then
    "$DESIGNER" "$(pwd)/ui/zhouyiUnity.ui" &
fi

# 3. 清屏
clear

# 4. 启动 Claude Code（前台运行，终端保留）
echo "VS Code 和 Qt Designer 已启动。"
exec claude --dangerously-skip-permissions
