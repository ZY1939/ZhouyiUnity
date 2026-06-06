#!/bin/bash
cd "$(dirname "$0")"

WIN_ID=""
if [ "$TERM_PROGRAM" = "Apple_Terminal" ]; then
    WIN_ID=$(osascript -e 'tell app "Terminal" to id of front window' 2>/dev/null)
fi

pause_and_exit() {
    echo ""
    echo "按回车键退出..."
    read -r
    if [ -n "$WIN_ID" ]; then
        (sleep 0.3 && osascript -e "tell app \"Terminal\" to close window id $WIN_ID" 2>/dev/null) &
    fi
    exit 0
}

# 杀掉已有的 main.py 进程，避免重复开窗
pkill -f "python3 main.py" 2>/dev/null

# 前台运行，Terminal 窗口作为调试输出
python3 main.py

pause_and_exit
