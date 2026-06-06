#!/bin/bash
cd "$(dirname "$0")"

REPO_NAME="ZhouyiUnity"
GITHUB_USER="ZY1939"
REMOTE_URL="git@github.com:$GITHUB_USER/$REPO_NAME.git"

# ---- 初始化 git 仓库 ----
if [ ! -d .git ]; then
    git init
    git branch -m main
    echo "✅ Git 仓库已初始化 (main 分支)"
fi

# ---- 提交信息 ----
DEFAULT_MSG="$(date '+%Y年%m月%d日%H时') 更新"

if [ -n "$1" ]; then
    COMMIT_MSG="$1"
else
    read -p "📝 提交信息 (回车使用默认): " INPUT_MSG
    COMMIT_MSG="${INPUT_MSG:-$DEFAULT_MSG}"
fi
echo "📝 提交信息: $COMMIT_MSG"

# ---- 提交所有变更 ----
git add .
git commit -m "$COMMIT_MSG" 2>/dev/null && echo "✅ 已提交" || echo "ℹ️  无新变更"

# ---- 设置推送远端 ----
if git remote get-url origin 2>/dev/null; then
    git remote set-url origin "$REMOTE_URL"
else
    git remote add origin "$REMOTE_URL"
fi

# ---- 推送 ----
git push -u origin main 2>&1 && echo "🚀 已推送至 $REMOTE_URL" || {
    echo "❌ 推送失败，请检查 SSH 配置"
    exit 1
}
