"""
外观管理器 — 将 usrCfg 中的外观配置应用到整个主窗口

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【这个文件做什么】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  当用户在"背景与字体"面板修改设置后，这个模块负责让修改在整个窗口上立刻生效。
  它读取 usrCfg/UsrCfg.json 中的 appearance 配置，然后：
    1. 设置 Qt 全局字体（所有文字立刻变化）
    2. 更新侧边栏图标大小（随字号缩放）
    3. 更新窗口背景颜色 + 背景图片
    4. 通知状态栏刷新（背景色联动）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【核心函数】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  apply_appearance(main_window) — 读取配置并应用外观（最重要的入口）
  _luminance(hex_color)         — 计算颜色亮度
  _text_color_for_bg(hex_color) — 根据背景亮度自动选择文字颜色

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【文字颜色自动适配原理】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  使用 ITU-R BT.709 感知亮度公式：
    L = 0.2126×R + 0.7152×G + 0.0722×B

  人眼对绿色最敏感（权重 0.7152），对蓝色最不敏感（0.0722）。
  亮度值 < 140 → 深色背景 → 白色文字
  亮度值 ≥ 140 → 浅色背景 → 深色文字(#1d1d1f)

  举例：
    黑色 #000000 → 亮度 0   → 白字
    深蓝 #1a1a3e → 亮度 30  → 白字
    灰色 #888888 → 亮度 136 → 白字
    浅灰 #f0f0f0 → 亮度 240 → 黑字
    白色 #ffffff → 亮度 255 → 黑字

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【调用时机】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  - 应用启动时：main_window.py 调用 apply_appearance(self) 初始化外观
  - 外观变更时：AppearancePanel 通过 on_changed 回调触发
"""
import os
from PySide6.QtGui import QFont, QPixmap, QPainter
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from .config_manager import config_manager


def _luminance(hex_color: str) -> int:
    """
    计算颜色的"感知亮度"（人眼觉得有多亮）

    参数:
        hex_color (str): 十六进制颜色值，如 "#f5f5f5" 或 "#1d1d1f"
                         支持带 # 或不带 #，长度必须是 6 位

    返回:
        int: 亮度值，范围 0-255
             - 0   = 纯黑（最暗）
             - 128 = 中性灰附近
             - 255 = 纯白（最亮）

    用法:
        >>> _luminance("#ffffff")   # 白色
        255
        >>> _luminance("#000000")   # 黑色
        0
        >>> _luminance("#888888")   # 灰色（刚好在白色/黑色文字的分界线附近）
        136

    公式: L = 0.2126×R + 0.7152×G + 0.0722×B (ITU-R BT.709)
         这是国际标准，考虑了人眼对不同颜色的敏感度差异
    """
    c = hex_color.lstrip("#")
    if len(c) != 6:
        return 128  # 格式不对时返回中性值
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return int(0.2126 * r + 0.7152 * g + 0.0722 * b)


def _text_color_for_bg(bg_hex: str) -> str:
    """
    根据背景颜色，自动选择最合适的文字颜色（深底白字 / 浅底黑字）

    参数:
        bg_hex (str): 背景色的十六进制值，如 "#f5f5f5"

    返回:
        str: 文字颜色值
             - "#ffffff" — 白色文字（深色背景用）
             - "#1d1d1f" — 深灰色文字（浅色背景用，比纯黑柔和）

    阈值说明:
        亮度 < 140 → 深色背景 → 白色文字
        亮度 ≥ 140 → 浅色背景 → 深色文字
        这个阈值经过实测编定，确保在大多数背景上文字清晰可读

    用法:
        >>> _text_color_for_bg("#1a1a2e")  # 深蓝背景
        '#ffffff'                          # 返回白色文字
        >>> _text_color_for_bg("#f5f5f5")  # 浅灰背景
        '#1d1d1f'                          # 返回深色文字
    """
    return "#ffffff" if _luminance(bg_hex) < 140 else "#1d1d1f"


# ── 背景图片缓存路径 ──────────────────────────────
_BG_CACHE = os.path.join(os.path.dirname(__file__), "..", "..", "usrCfg", "_bg_cache.png")


def _scale_and_cache_image(image_path: str, opacity: int = 100) -> str:
    """
    预缩放背景图片并缓存到 usrCfg/_bg_cache.png，返回缓存路径

    参数:
        image_path (str): 原始图片路径

    返回:
        str: 缩放后缓存图片的路径

    为什么需要预缩放:
        CSS background-image: url() 会加载原始分辨率的图片。
        用户的截图可能是 Retina 分辨率（10000+ 像素），
        Qt 在主线程同步渲染会卡死。
        预缩放到屏幕分辨率后缓存，避免 UI 冻结。
    """
    pix = QPixmap(image_path)
    if pix.isNull():
        return image_path

    # 获取主屏幕分辨率作为缩放上限
    app = QApplication.instance()
    screen = app.primaryScreen() if app else None
    if screen:
        screen_size = screen.size()
        max_w = screen_size.width()
        max_h = screen_size.height()
    else:
        max_w, max_h = 2560, 1600

    # 仅在图片比屏幕大时才缩放
    if pix.width() > max_w or pix.height() > max_h:
        pix = pix.scaled(
            max_w, max_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    # 透明度合成（opacity < 100 时降低图片不透明度）
    if opacity < 100:
        transparent = QPixmap(pix.size())
        transparent.fill(Qt.GlobalColor.transparent)
        p = QPainter(transparent)
        p.setOpacity(opacity / 100.0)
        p.drawPixmap(0, 0, pix)
        p.end()
        pix = transparent

    pix.save(_BG_CACHE, "PNG")
    return _BG_CACHE


def apply_appearance(main_window) -> None:
    """
    读取 usrCfg 中的外观配置，并应用到整个程序窗口（最重要的入口函数）

    参数:
        main_window: 主窗口对象（QMainWindow 实例）。
                     调用方式: apply_appearance(self)  # 在 main_window 内部

    返回:
        None（无返回值，直接修改窗口样式）

    做了哪些事:
        1. 设置 QApplication 全局字体 → 所有界面文字立刻变化
        2. 通知 SettingsTab 刷新侧边栏 → 图标大小跟随字号
        3. 为 centralWidget 设置 CSS 样式 → 背景色 + 可选背景图
        4. 通知状态栏即时刷新 → 文字颜色跟随背景

    用法示例:
        # 在 main_window.py 中：
        from src.settings.appearance_manager import apply_appearance
        class MainWindow(QMainWindow):
            def __init__(self):
                ...
                apply_appearance(self)  # 应用启动时初始化外观

        # 在 appearance_panel.py 中（用户修改设置时）：
        self._on_changed = lambda: apply_appearance(self._main)
        每当用户改了字体/颜色/背景，立刻调用这个函数刷新界面

    关于背景图片:
        背景图片通过 CSS background-image 叠加在背景色之上。
        如果图片是透明 PNG，背景色会透过透明区域显示出来。
        这样就实现了"半透明图片 + 背景色"的效果。
    """
    cfg = config_manager.get("appearance") or {}

    bg_color = cfg.get("background_color", "#f5f5f5")
    bg_image = cfg.get("background_image", "")
    bg_image_mode = cfg.get("background_image_mode", "fill")
    bg_image_opacity = cfg.get("background_image_opacity", 100)
    font_family = cfg.get("font_family", "PingFang SC")
    font_size = cfg.get("font_size", 16)

    text_color = _text_color_for_bg(bg_color)

    # 控制台输出当前外观参数，方便调试
    print(f"[外观应用] 字体={font_family} {font_size}px, 背景={bg_color}, "
          f"亮度={_luminance(bg_color)}, 文字={text_color}, "
          f"图片={'有' if bg_image else '无'}")

    # ── 1. 全局字体（QApplication 级别，所有 Widget 的默认字体）──
    app = QApplication.instance()
    if app:
        font = QFont(font_family, font_size)
        app.setFont(font)

    # ── 2. 侧边栏图标/行高联动字号 ──
    settings_tab = getattr(main_window, "_settings", None)
    if settings_tab and hasattr(settings_tab, "refresh_sidebar"):
        settings_tab.refresh_sidebar(font_size)

    # ── 2.5. 面板文字颜色跟随背景切换 ──
    if settings_tab and hasattr(settings_tab, "refresh_text_color"):
        settings_tab.refresh_text_color(text_color)

    # ── 3. 背景 + 文字颜色（应用到 centralWidget）──
    central = main_window.centralWidget()
    if central is None:
        return

    style_parts = [
        f"background-color: {bg_color};",
        f"color: {text_color};",
    ]

    # 如果有背景图片，预缩放后通过 CSS 叠加（支持透明 PNG）
    if bg_image and os.path.isfile(bg_image):
        cached = _scale_and_cache_image(bg_image, bg_image_opacity)
        escaped = cached.replace("\\", "/")  # Windows 反斜杠→正斜杠

        # 拉伸模式 → CSS background-size
        mode_css = {
            "fill":   "100% 100%",         # 拉伸填满
            "fit":    "contain",            # 适应窗口（保持比例）
            "center": "auto",               # 居中（原始大小）
            "tile":   "auto",               # 平铺（原始大小 + repeat）
        }
        bg_size = mode_css.get(bg_image_mode, "100% 100%")
        bg_repeat = "repeat" if bg_image_mode == "tile" else "no-repeat"

        style_parts.append(
            f"background-image: url({escaped});"
            f"background-repeat: {bg_repeat};"
            f"background-position: center center;"
            f"background-size: {bg_size};"
        )

    central.setStyleSheet(" ".join(style_parts))

    # 状态栏使用固定深灰色背景+白字，无需随外观联动刷新
