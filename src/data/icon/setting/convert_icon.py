"""
图标转换工具 — 将任意图片转换为统一多尺寸的 PNG 图标

用途：
  项目中设置面板的侧边栏图标需要通过此工具转换为统一规格的 PNG 文件。
  支持 SVG（矢量，推荐）和常规位图（PNG/JPG/BMP/GIF/WebP）。

用法：
  python3 convert_icon.py <输入图片>                          → 生成 24/48/64px 三种尺寸
  python3 convert_icon.py <输入图片> --size 32                → 指定单一尺寸
  python3 convert_icon.py <输入图片> --size 24 48 64          → 指定多个尺寸
  python3 convert_icon.py <输入图片> --name myicon --no-aspect → 自定义前缀 + 拉伸填充
  python3 convert_icon.py <输入图片> --output-dir /path/to/out → 指定输出目录

输出命名规则：{name}_{size}x{size}.png（如 ai_24x24.png, ai_48x48.png）

技术细节：
  - SVG: 用 QSvgRenderer 以最大尺寸的 2x 渲染（Retina 超采样），再缩放到各尺寸
  - 位图: 用 QPixmap 加载后 SmoothTransformation 缩放
  - 非正方形图片: 保持宽高比，居中放置在透明画布上
  - 所有输出: 32 位 ARGB PNG（含透明通道）

为什么需要这个工具：
  侧边栏图标通过 SVG + QSvgRenderer 渲染可以保证任意字号下都很清晰，
  但 Qt 的 setIcon() API 需要 QIcon 对象。此工具用于将外部获取的图标
  批量转为 PNG 备用，以及处理非矢量格式的图标资源。
"""
import argparse
import os
import sys
from pathlib import Path

# ── Qt 图标渲染 ──────────────────────────────────────
from PySide6.QtGui import QImage, QPainter, QPixmap, QIcon, Qt
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication
from PySide6.QtSvg import QSvgRenderer


DEFAULT_SIZES = [24, 48, 64]  # 默认输出三种尺寸（小/中/大）


def convert_to_png(source_path: str, output_dir: str, name: str,
                   sizes: list = None, keep_aspect: bool = True):
    """
    将源图片转换为多个指定尺寸的 PNG 图标

    Args:
        source_path: 输入图片路径（支持 SVG / PNG / JPG / BMP / GIF / WebP）
        output_dir:  输出目录
        name:        输出文件名前缀（不含扩展名）
        sizes:       目标尺寸列表（默认 [24, 48, 64]）
        keep_aspect: 是否保持原始宽高比（True=居中留边, False=拉伸填充）

    Returns:
        生成的输出文件路径列表
    """
    if sizes is None:
        sizes = DEFAULT_SIZES

    ext = Path(source_path).suffix.lower()
    pixmap = None

    if ext == ".svg":
        # SVG：用 QSvgRenderer 以 2x 超采样渲染，保证缩放清晰
        renderer = QSvgRenderer(source_path)
        if not renderer.isValid():
            print(f"错误：无法解析 SVG 文件 → {source_path}")
            return []
        max_size = max(sizes) * 2  # Retina 超采样
        pixmap = QPixmap(max_size, max_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
    else:
        # 位图：直接加载
        pixmap = QPixmap(source_path)
        if pixmap.isNull():
            print(f"错误：无法加载图片 → {source_path}")
            return []

    output_paths = []
    for size in sizes:
        # 缩放到目标尺寸（SmoothTransformation = 高质量缩放）
        scaled = pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio if keep_aspect else Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # 非正方形图片居中放置在透明画布上
        if keep_aspect and (scaled.width() != size or scaled.height() != size):
            canvas = QPixmap(size, size)
            canvas.fill(Qt.GlobalColor.transparent)
            painter = QPainter(canvas)
            x = (size - scaled.width()) // 2
            y = (size - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()
            final = canvas
        else:
            final = scaled

        # 输出 PNG
        out_path = os.path.join(output_dir, f"{name}_{size}x{size}.png")
        final.save(out_path, "PNG")
        output_paths.append(out_path)
        print(f"  ✓ {out_path}")

    return output_paths


def main():
    """命令行入口 — 解析参数并调用 convert_to_png"""
    # 确保 QApplication 实例存在（QPixmap / QSvgRenderer 依赖）
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    parser = argparse.ArgumentParser(
        description="图标转换工具 — 将任意图片转成统一尺寸的图标 PNG"
    )
    parser.add_argument("source", help="输入图片路径 (PNG / JPG / SVG / BMP / GIF / WebP)")
    parser.add_argument("--size", type=int, nargs="+",
                        help=f"输出尺寸列表 (默认: {' '.join(map(str, DEFAULT_SIZES))})")
    parser.add_argument("--name", type=str, default=None,
                        help="输出文件名前缀 (默认: 输入文件名)")
    parser.add_argument("--no-aspect", action="store_true",
                        help="拉伸填充（不保持宽高比）")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="输出目录 (默认: 输入文件所在目录)")

    args = parser.parse_args()

    # 校验输入文件
    source = args.source
    if not os.path.isfile(source):
        print(f"错误：文件不存在 → {source}")
        sys.exit(1)

    # 确定输出目录
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = os.path.dirname(os.path.abspath(source))

    os.makedirs(output_dir, exist_ok=True)

    # 输出文件名前缀
    name = args.name or Path(source).stem

    # 目标尺寸
    sizes = args.size if args.size else DEFAULT_SIZES

    print(f"\n图标转换: {source}")
    print(f"输出目录: {output_dir}")
    print(f"目标尺寸: {' '.join(f'{s}x{s}' for s in sizes)}")
    print(f"前缀: {name}\n")

    paths = convert_to_png(
        source, output_dir, name,
        sizes=sizes,
        keep_aspect=not args.no_aspect,
    )

    print(f"\n完成！共生成 {len(paths)} 个图标文件。\n")
    return paths


if __name__ == "__main__":
    main()
