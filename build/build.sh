#!/bin/bash
# ============================================
#  ZhouyiUnity 跨平台构建脚本
#  用法:
#    macOS:   bash build/build.sh
#    Windows: bash build/build.sh  (Git Bash / WSL)
#    clean:   bash build/build.sh clean
# ============================================
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

PYINSTALLER="$HOME/Library/Python/3.12/bin/pyinstaller"
SPEC="ZhouyiUnity.spec"
DIST_DIR="$PROJECT_DIR/dist"
BUILD_DIR="$PROJECT_DIR/build"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'

# 安全清理：删 PyInstaller 工作目录，保留 build.sh
clean_build() {
    echo -e "${CYAN}清理构建...${NC}"
    find "$BUILD_DIR" -mindepth 1 -maxdepth 1 -not -name 'build.sh' -exec rm -rf {} + 2>/dev/null || true
    rm -rf "$DIST_DIR"/ZhouyiUnity* 2>/dev/null || true
    mkdir -p "$DIST_DIR"
    touch "$DIST_DIR/.gitkeep"
    echo -e "${GREEN}已清理${NC}"
}

case "${1:-build}" in
    clean)
        clean_build
        exit 0
        ;;
    build)
        ;;
    *)
        echo "用法: bash build/build.sh [build|clean]"
        exit 1
        ;;
esac

echo "========================================="
echo "  ZhouyiUnity 构建"
echo "========================================="
echo ""
echo "  平台: $(uname -s)"
echo "  输出: $DIST_DIR"

[ ! -f "$PYINSTALLER" ] && echo -e "${RED}❌ PyInstaller 未安装${NC}" && exit 1

# 先清理旧产物（保留 build.sh）
clean_build

echo ""
echo "正在打包..."

"$PYINSTALLER" \
    --distpath "$DIST_DIR" \
    --workpath "$BUILD_DIR" \
    --clean \
    --noconfirm \
    "$SPEC"

echo ""
echo "========================================="
echo -e "  ${GREEN}✓ 构建完成${NC}"
echo "========================================="
echo ""

if [ "$(uname -s)" = "Darwin" ]; then
    APP="$DIST_DIR/ZhouyiUnity.app"
    [ -d "$APP" ] && echo "  macOS: $APP ($(du -sh "$APP" 2>/dev/null | cut -f1))"
else
    EXE="$DIST_DIR/ZhouyiUnity/ZhouyiUnity.exe"
    [ -f "$EXE" ] && echo "  Windows: $EXE ($(du -sh "$DIST_DIR/ZhouyiUnity" 2>/dev/null | cut -f1))"
fi
echo ""
echo "  macOS 双击: dist/ZhouyiUnity.app"
echo "  Windows 双击: dist/ZhouyiUnity/ZhouyiUnity.exe"
