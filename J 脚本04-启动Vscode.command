#!/bin/bash
WIN_ID=""
if [ "$TERM_PROGRAM" = "Apple_Terminal" ]; then
    WIN_ID=$(osascript -e 'tell app "Terminal" to id of front window' 2>/dev/null)
fi

cd "$(dirname "$0")"
code . --new-window

if [ -n "$WIN_ID" ]; then
    (sleep 0.3 && osascript -e "tell app \"Terminal\" to close window id $WIN_ID" 2>/dev/null) &
fi
exit 0
