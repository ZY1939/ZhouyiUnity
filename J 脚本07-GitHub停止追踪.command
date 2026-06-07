#!/bin/bash
cd "$(dirname "$0")"

WIN_ID=""
if [ "$TERM_PROGRAM" = "Apple_Terminal" ]; then
    WIN_ID=$(osascript -e 'tell app "Terminal" to id of front window' 2>/dev/null)
fi

trap 'echo ""; echo "👋 已退出"; echo ""; echo "按回车键关闭窗口..."; read -r; [ -n "$WIN_ID" ] && (sleep 0.3 && osascript -e "tell app \"Terminal\" to close window id $WIN_ID" 2>/dev/null) &; exit 0' INT

PROJECT_DIR="$(pwd)"

# ---- 处理单个目标 ----
process_target() {
    local TARGET="$1"

    # 去掉首尾空格和引号
    TARGET=$(echo "$TARGET" | sed 's/^[[:space:]"'"'"']*//;s/[[:space:]"'"'"']*$//')

    [ -z "$TARGET" ] && return

    # 验证在项目内
    if [[ ! "$TARGET" == "$PROJECT_DIR"* ]]; then
        echo "   ❌ 不在项目内"
        return
    fi

    local REL_PATH="${TARGET#$PROJECT_DIR/}"

    if [ -z "$REL_PATH" ]; then
        echo "   ❌ 不能停止追踪项目根目录"
        return
    fi

    echo "   📁 $REL_PATH"

    # 添加到 .gitignore
    if grep -qxF "$REL_PATH" .gitignore 2>/dev/null; then
        echo "      ℹ️  .gitignore 已存在"
    else
        echo "$REL_PATH" >> .gitignore
        echo "      ✅ 已添加到 .gitignore"
    fi

    # 从 git 追踪中移除
    local TRACKED=$(git ls-files "$REL_PATH" 2>/dev/null)
    if [ -n "$TRACKED" ]; then
        local COUNT=$(echo "$TRACKED" | wc -l | tr -d ' ')
        git rm --cached -r "$REL_PATH" 2>/dev/null
        echo "      ✅ 已从 git 移除 ($COUNT 个文件)"
    else
        echo "      ℹ️  无已追踪文件"
    fi

    echo ""
}

# ---- 处理初始拖入 ----
if [ $# -gt 0 ]; then
    echo "━━━━ 处理拖入的 $# 个目标 ━━━━"
    for TARGET in "$@"; do
        process_target "$TARGET"
    done
fi

# ---- 循环接受更多输入 ----
echo "拖入文件/文件夹到终端，或按 q 退出"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"
while true; do
    printf "📁> "
    read -r INPUT

    if [ -z "$INPUT" ] || [ "$INPUT" = "q" ] || [ "$INPUT" = "Q" ]; then
        echo "👋 已退出"
        break
    fi

    process_target "$INPUT"
done

echo ""
echo "📌 请运行脚本06提交变更"
echo ""
echo "按回车键关闭窗口..."
read -r
if [ -n "$WIN_ID" ]; then
    (sleep 0.3 && osascript -e "tell app \"Terminal\" to close window id $WIN_ID" 2>/dev/null) &
fi
