#!/bin/bash
cd "$(dirname "$0")/.."

# 以当前工程目录启动 Claude Code
# --dangerously-skip-permissions: 跳过权限确认（YOLO 模式）
exec claude --dangerously-skip-permissions
