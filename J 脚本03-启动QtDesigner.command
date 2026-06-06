#!/bin/bash
cd "$(dirname "$0")"

WIN_ID=""
if [ "$TERM_PROGRAM" = "Apple_Terminal" ]; then
    WIN_ID=$(osascript -e 'tell app "Terminal" to id of front window' 2>/dev/null)
fi

DESIGNER="/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/PySide6/Designer.app/Contents/MacOS/Designer"

if [ -x "$DESIGNER" ]; then
    "$DESIGNER" "$(pwd)/ui/zhouyiUnity.ui" &
else
    open /Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/PySide6/Designer.app
fi

if [ -n "$WIN_ID" ]; then
    (sleep 0.3 && osascript -e "tell app \"Terminal\" to close window id $WIN_ID" 2>/dev/null) &
fi
exit 0
