"""
截图功能 — 截取易经 Tab 面板区域并保存为图片

═══════════════════════════════════════════════════════════════
文件职责：提供 capture_screenshot() 截图核心函数
         默认保存到 usrDat/ScreenShot-Yijing/，文件名含时间戳
═══════════════════════════════════════════════════════════════

调用方式：
    from .screenshot import capture_screenshot
    path = capture_screenshot(target_widget)

后续设置面板对接（预留参数）：
    用户可在设置面板中配置：
      - 默认保存路径（替换 usrDat/ScreenShot-Yijing）
      - 文件格式（PNG / JPEG）
      - JPEG 质量（1-100）
      - 是否包含背景图片
      - 文件名前缀
    所有配置项已作为函数参数预留，届时从 config_manager 读取传入即可。

文件名格式：
    截图-{YYMMDD}-{HHMMSS}.png
    例: 截图-250609-223015.png

输出目录：
    默认: {项目根}/usrDat/ScreenShot-Yijing/
    首次截图时自动创建目录，失败则降级到桌面。
"""

from __future__ import annotations

import os
import datetime
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtCore import QUrl


def _get_sound_path() -> str:
    """返回快门音效文件的绝对路径"""
    try:
        from ...settings.config_manager import get_project_root
        root = get_project_root()
        return os.path.join(root, "src", "data", "sound", "Screen Capture.aif")
    except Exception:
        return ""


# 模块级缓存：QSoundEffect 需要异步加载，预加载一次后复用
_cached_shutter: QSoundEffect | None = None
_cached_shutter_loaded = False


def _ensure_shutter_loaded():
    """预加载快门音效（首次调用时异步加载，后续复用）"""
    global _cached_shutter, _cached_shutter_loaded
    if _cached_shutter_loaded and _cached_shutter is not None:
        return
    path = _get_sound_path()
    if not path or not os.path.exists(path):
        _cached_shutter_loaded = True
        return
    try:
        _cached_shutter = QSoundEffect()
        _cached_shutter.setSource(QUrl.fromLocalFile(path))
        _cached_shutter.setVolume(0.6)
        _cached_shutter_loaded = True
    except Exception:
        _cached_shutter_loaded = True


def _play_shutter():
    """播放快门音效（非阻塞，模块级缓存确保不被 GC）"""
    global _cached_shutter
    _ensure_shutter_loaded()
    if _cached_shutter is not None:
        # 即使未完全加载也尝试播放（Qt 会排队等加载完成后播放）
        _cached_shutter.play()


def capture_screenshot(
    target_widget: QWidget,
    *,
    save_dir: str | None = None,
    file_format: str = "png",
    quality: int = 95,
    include_bg: bool = True,
    prefix: str = "截图",
) -> str | None:
    """
    截取 target_widget 的当前画面并保存为图片文件

    Args:
        target_widget:
            要截取的目标控件。
            调用方传入 self 或具体 panel 引用。

        save_dir (str | None):
            保存目录的绝对路径。
            传 None 时使用默认路径: {项目根}/usrDat/ScreenShot-Yijing/
            ── 后续设置面板会从此参数注入用户配置的路径 ──

        file_format (str):
            文件格式，可选 "png" 或 "jpg"。
            ── 后续设置面板从 config_manager.get("screenshot", "format") 读取 ──

        quality (int):
            JPEG 质量，取值范围 1-100（100=最高质量，文件最大）。
            仅当 file_format="jpg" 时生效，PNG 为无损格式忽略此参数。
            ── 后续设置面板从 config_manager.get("screenshot", "quality") 读取 ──

        include_bg (bool):
            是否包含背景图片/背景色。
            True:  直接截取控件当前可见画面（含背景）
            False: 预留 — 后续实现透明背景截图
            ── 后续设置面板从 config_manager.get("screenshot", "include_bg") 读取 ──

        prefix (str):
            文件名前缀，默认 "截图"。
            ── 后续设置面板可配置自定义前缀 ──

    Returns:
        str | None:
            成功时返回保存的完整文件路径。
            失败时返回 None（目录创建失败或保存异常）。

    Raises:
        不抛出异常 — 所有错误内部捕获并打印诊断信息。

    用法:
        >>> path = capture_screenshot(self)
        >>> if path:
        >>>     print(f"截图已保存: {path}")
    """
    # ── 1. 抓取控件画面 ──
    if include_bg:
        # 抓取顶层窗口 → 裁剪到控件区域，确保 CSS 背景色/图片都被捕获
        top_win = target_widget.window()
        win_pixmap = top_win.grab()
        dpr = win_pixmap.devicePixelRatio()
        # 控件在窗口坐标系中的矩形
        widget_pos = target_widget.mapTo(top_win, target_widget.rect().topLeft())
        x = int(widget_pos.x() * dpr)
        y = int(widget_pos.y() * dpr)
        w = int(target_widget.width() * dpr)
        h = int(target_widget.height() * dpr)
        pixmap = win_pixmap.copy(x, y, w, h)
    else:
        # 透明背景 — 仅控件自身画面
        pixmap = target_widget.grab()

    # ── 2. 确定保存目录 ──
    if save_dir is None:
        try:
            from ...settings.config_manager import get_project_root
            project_root = get_project_root()
            save_dir = os.path.join(project_root, "usrDat", "ScreenShot-Yijing")
        except Exception:
            # 极端情况：config_manager 不可用，降级到桌面
            save_dir = os.path.join(os.path.expanduser("~"), "Desktop", "ScreenShot-Yijing")

    try:
        os.makedirs(save_dir, exist_ok=True)
    except OSError as e:
        print(f"[截图] ❌ 无法创建目录: {save_dir} ({e})", flush=True)
        return None

    # ── 3. 生成文件名 ──
    now = datetime.datetime.now()
    timestamp = now.strftime("%y%m%d-%H%M%S")       # 例: 250609-223015
    ext = file_format.lower()
    filename = f"{prefix}-{timestamp}.{ext}"
    filepath = os.path.join(save_dir, filename)

    # ── 4. 保存图片 ──
    try:
        if ext == "jpg" or ext == "jpeg":
            # JPEG 有损压缩，quality 控制画质
            image: QImage = pixmap.toImage()
            success = image.save(filepath, "JPEG", quality)
        else:
            # PNG 无损，quality 参数忽略
            success = pixmap.save(filepath, "PNG")

        if success:
            print(f"[截图] ✓ 已保存: {filepath}", flush=True)
            _play_shutter()
            return filepath
        else:
            print(f"[截图] ❌ 保存失败: {filepath}", flush=True)
            return None
    except Exception as e:
        print(f"[截图] ❌ 保存异常: {filepath} ({e})", flush=True)
        return None
