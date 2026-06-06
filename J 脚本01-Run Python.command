#!/bin/bash
cd "$(dirname "$0")"

# 杀掉已有的 main.py 进程，避免重复开窗
pkill -f "python3 main.py" 2>/dev/null

# 脱离终端启动 GUI，终端窗口自动关闭
nohup python3 main.py > /dev/null 2>&1 &
exit 0
