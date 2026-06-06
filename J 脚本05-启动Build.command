#!/bin/bash
cd "$(dirname "$0")/.."

WIN_ID=""
if [ "$TERM_PROGRAM" = "Apple_Terminal" ]; then
    WIN_ID=$(osascript -e 'tell app "Terminal" to id of front window' 2>/dev/null)
fi

echo "========================================="
echo "  ZhouyiUnity 构建 & 启动"
echo "========================================="
echo ""

# 构建
bash build/build.sh

# 启动 app
APP="$(pwd)/dist/ZhouyiUnity.app"
if [ -d "$APP" ]; then
    echo ""
    echo "启动 ZhouyiUnity.app ..."
    open "$APP"
else
    echo "❌ 构建失败，未找到 $APP"
    exit 1
fi

if [ -n "$WIN_ID" ]; then
    (sleep 0.3 && osascript -e "tell app \"Terminal\" to close window id $WIN_ID" 2>/dev/null) &
fi
exit 0
