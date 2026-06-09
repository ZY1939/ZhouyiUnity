#!/bin/bash
cd "$(dirname "$0")"
clear
clear
WIN_ID=""
if [ "$TERM_PROGRAM" = "Apple_Terminal" ]; then
    WIN_ID=$(osascript -e 'tell app "Terminal" to id of front window' 2>/dev/null)
fi

auto_exit() {
    if [ -n "$WIN_ID" ]; then
        (sleep 0.3 && osascript -e "tell app \"Terminal\" to close window id $WIN_ID" 2>/dev/null) &
    fi
    exit 0
}

# 关闭本项目所有的 Python 进程（通过 cwd 精确匹配，避免杀错）
PROJ="$(cd "$(dirname "$0")" && pwd)"
for pid in $(pgrep '^python' 2>/dev/null); do
    CWD=$(lsof -p "$pid" -a -d cwd -Fn 2>/dev/null | tail -1 | sed 's/^n//')
    if [ -n "$CWD" ] && ( [ "$CWD" = "$PROJ" ] || [[ "$CWD" == "$PROJ"/* ]] ); then
        kill "$pid" 2>/dev/null
    fi
done
sleep 0.3

# 前台运行，Terminal 窗口作为调试输出
python3 main.py

auto_exit
