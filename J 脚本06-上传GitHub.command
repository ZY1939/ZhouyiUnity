#!/bin/bash
cd "$(dirname "$0")"

REPO_NAME="ZhouyiUnity"
GITHUB_USER="ZY1939"
TOKEN_FILE="$HOME/.github_token_zy"

# ---- 初始化 git 仓库 ----
if [ ! -d .git ]; then
    git init
    git branch -m main
    echo "✅ Git 仓库已初始化 (main 分支)"
fi

# ---- 提交信息 ----
if [ -n "$1" ]; then
    COMMIT_MSG="$1"
else
    COMMIT_MSG="$(date '+%Y年%m月%d日%H时') 更新"
fi
echo "📝 提交信息: $COMMIT_MSG"

# ---- 提交所有变更 ----
git add .
git commit -m "$COMMIT_MSG" 2>/dev/null && echo "✅ 已提交" || echo "ℹ️  无新变更"

# ---- 获取/验证 GitHub Token ----
get_token() {
    if [ -f "$TOKEN_FILE" ]; then
        GITHUB_TOKEN=$(cat "$TOKEN_FILE")
    else
        GITHUB_TOKEN=$(osascript -e 'display dialog "请输入 GitHub Personal Access Token (需 repo 权限):" default answer "" with hidden answer' -e 'text returned of result' 2>/dev/null)
        if [ -n "$GITHUB_TOKEN" ]; then
            echo "$GITHUB_TOKEN" > "$TOKEN_FILE"
            chmod 600 "$TOKEN_FILE"
            echo "🔑 Token 已保存至 $TOKEN_FILE"
        fi
    fi
}

# ---- 在 GitHub 上创建仓库 (如不存在) ----
create_repo() {
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: token $GITHUB_TOKEN" \
        "https://api.github.com/repos/$GITHUB_USER/$REPO_NAME")

    if [ "$http_code" = "200" ]; then
        echo "ℹ️  远端仓库 $GITHUB_USER/$REPO_NAME 已存在"
        return 0
    fi

    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/user/repos" \
        -d "{\"name\":\"$REPO_NAME\",\"private\":false,\"default_branch\":\"main\"}")

    if [ "$http_code" = "201" ]; then
        echo "✅ 远端仓库 $GITHUB_USER/$REPO_NAME 已创建"
    else
        echo "❌ 创建仓库失败 (HTTP $http_code)，请检查 Token 权限"
        rm -f "$TOKEN_FILE"
        exit 1
    fi
}

# ---- 设置/推送远端 ----
push_to_github() {
    REMOTE_URL="git@github.com:$GITHUB_USER/$REPO_NAME.git"

    if git remote get-url origin 2>/dev/null; then
        git remote set-url origin "$REMOTE_URL"
    else
        git remote add origin "$REMOTE_URL"
    fi

    git push -u origin main 2>&1 && echo "🚀 已推送至 $REMOTE_URL" || {
        echo "❌ 推送失败，请检查 SSH 配置"
        exit 1
    }
}

# ---- 主流程 ----
get_token
create_repo
push_to_github
