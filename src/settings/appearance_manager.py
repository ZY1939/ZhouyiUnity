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
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPixmapCache
from PySide6.QtWidgets import QApplication, QTabWidget
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


def _scale_and_cache_image(image_path: str, opacity: int = 100,
                           mode: str = "fill", canvas_w: int = 0, canvas_h: int = 0,
                           overlay_alpha: int = 0, overlay_dark: bool = True) -> str:
    """
    预渲染背景图片到画布尺寸并缓存，返回缓存路径

    参数:
        image_path (str):   原始图片路径
        opacity (int):      不透明度 10-100，100=完全不透明
        mode (str):         拉伸模式 "fill"/"fit"/"center"/"tile"
        canvas_w (int):     画布宽度（像素），0=使用屏幕宽度
        canvas_h (int):     画布高度（像素），0=使用屏幕高度
        overlay_alpha (int):可读性遮罩透明度 0-255，0=不叠加
        overlay_dark (bool):True=暗化遮罩(白字用), False=亮化遮罩(黑字用)

    返回:
        str: 缓存图片路径

    为什么需要预渲染:
        1. CSS background-image 加载原始分辨率，Retina 截图 10000+ 像素卡死
        2. Qt QSS 不支持 background-size，拉伸/适应/居中/平铺必须在 QPainter 层面实现
        3. 渲染到与 Widget 相同的尺寸，确保 1:1 像素映射
        4. 可读性遮罩在缓存时叠加，零运行时开销
    """
    pix = QPixmap(image_path)
    if pix.isNull():
        return image_path

    # 画布尺寸：优先用传入的精确值，否则回退到屏幕分辨率
    if canvas_w <= 0 or canvas_h <= 0:
        app = QApplication.instance()
        screen = app.primaryScreen() if app else None
        if screen:
            canvas_w = screen.size().width()
            canvas_h = screen.size().height()
        else:
            canvas_w, canvas_h = 2560, 1600

    canvas = QPixmap(canvas_w, canvas_h)
    canvas.fill(Qt.GlobalColor.transparent)

    painter = QPainter(canvas)
    painter.setOpacity(opacity / 100.0)

    if mode == "fill":
        # 拉伸填满 — 忽略宽高比，可能变形
        scaled = pix.scaled(canvas_w, canvas_h,
                            Qt.AspectRatioMode.IgnoreAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap(0, 0, scaled)

    elif mode == "fit":
        # 适应窗口 — 保持宽高比，居中放置
        scaled = pix.scaled(canvas_w, canvas_h,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)
        x = (canvas_w - scaled.width()) // 2
        y = (canvas_h - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

    elif mode == "center":
        # 居中 — 原始大小，不缩放，居中放置
        x = (canvas_w - pix.width()) // 2
        y = (canvas_h - pix.height()) // 2
        painter.drawPixmap(x, y, pix)

    elif mode == "tile":
        # 平铺 — 从左上角重复绘制填满整个画布
        for ty in range(0, canvas_h, pix.height()):
            for tx in range(0, canvas_w, pix.width()):
                painter.drawPixmap(tx, ty, pix)

    # 可读性增强遮罩 — 在图片上叠加半透明层，降低对比度让文字更清晰
    if overlay_alpha > 0:
        painter.setOpacity(overlay_alpha / 255.0)
        overlay = QColor(0, 0, 0) if overlay_dark else QColor(255, 255, 255)
        painter.fillRect(canvas.rect(), overlay)

    painter.end()
    canvas.save(_BG_CACHE, "PNG")
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

    # 清除 Qt 全局 pixmap 缓存 — 必须在任何 QPixmap 加载之前，
    # 否则 _bg_original.png 被覆盖后 QPixmap 仍返回旧图
    QPixmapCache.clear()

    bg_color = cfg.get("background_color", "#f5f5f5")
    bg_image = cfg.get("background_image", "")
    # 支持相对路径（相对于项目根目录）
    if bg_image and not os.path.isabs(bg_image):
        _proj_root = os.path.join(os.path.dirname(__file__), "..", "..")
        bg_image = os.path.join(_proj_root, bg_image)
    bg_image_mode = cfg.get("background_image_mode", "fill")
    bg_image_opacity = cfg.get("background_image_opacity", 100)
    font_family = cfg.get("font_family", "PingFang SC")
    font_size = cfg.get("font_size", 16)

    # ── 文字颜色：auto=自动计算, manual=使用配置中的值 ──
    has_bg_image = bool(bg_image and os.path.isfile(bg_image))
    text_color_mode = cfg.get("text_color_mode", "auto")
    if has_bg_image and text_color_mode == "manual":
        text_color = cfg.get("text_color", "#1d1d1f")
    else:
        text_color = _text_color_for_bg(bg_color)

    # ── 可读性增强遮罩：仅在有背景图 + 启用时生效 ──
    overlay_alpha = 0
    overlay_dark = True
    if has_bg_image and cfg.get("overlay_enabled", False):
        strength = cfg.get("overlay_strength", "medium")
        alpha_map = {"light": 20, "medium": 38, "strong": 64}
        overlay_alpha = alpha_map.get(strength, 38)
        # 白字用暗化遮罩，黑字用亮化遮罩
        overlay_dark = (text_color == "#ffffff")

    # 控制台输出当前外观参数，方便调试
    ov_str = cfg.get("overlay_strength", "medium") if overlay_alpha else "off"
    print(f"[外观应用] 字体={font_family} {font_size}px, 背景={bg_color}, "
          f"亮度={_luminance(bg_color)}, 文字={text_color}, "
          f"模式={'手动' if text_color_mode == 'manual' else '自动'}, "
          f"遮罩={overlay_alpha}/{ov_str}, "
          f"图片={'有' if has_bg_image else '无'}")

    # ── 1. 全局字体（QApplication 级别，所有 Widget 的默认字体）──
    app = QApplication.instance()
    if app:
        font = QFont(font_family, font_size)
        app.setFont(font)

    # ── 2. 背景图预渲染（必须在 refresh_sidebar 之前，毛玻璃需要 _bg_cache.png）──
    central = main_window.centralWidget()
    style_parts = [
        f"background-color: {bg_color};",
    ]

    if central is not None and bg_image and os.path.isfile(bg_image):
        csize = central.size()
        cached = _scale_and_cache_image(bg_image, bg_image_opacity, bg_image_mode,
                                        csize.width(), csize.height(),
                                        overlay_alpha, overlay_dark)
        escaped = cached.replace("\\", "/")
        style_parts.append(
            f"background-image: url({escaped});"
            f"background-repeat: no-repeat;"
        )

    # 应用到 centralWidget
    if central is not None:
        central.setStyleSheet("")
        central.setStyleSheet(" ".join(style_parts))

    # ── 3. 侧边栏图标/行高联动字号（在背景图缓存之后，确保毛玻璃用到新图）──
    settings_tab = getattr(main_window, "_settings", None)
    if settings_tab and hasattr(settings_tab, "refresh_sidebar"):
        settings_tab.refresh_sidebar(font_size, text_color, has_bg_image)

    # ── 3.5. 面板文字颜色跟随背景切换 ──
    if settings_tab and hasattr(settings_tab, "refresh_text_color"):
        settings_tab.refresh_text_color(text_color)

    # ── 3.6. 起卦面板行高/间距跟随字号缩放 ──
    yijing_viewer = getattr(main_window, "_yijing", None)
    if yijing_viewer:
        if hasattr(yijing_viewer, "refresh_font_size"):
            yijing_viewer.refresh_font_size(font_size)
        if hasattr(yijing_viewer, "refresh_text_color"):
            yijing_viewer.refresh_text_color(text_color)

    # ── 3.5. QTabWidget 标签栏样式 — 跟随系统主题、无接缝、字号自适应 ──
    tab = main_window.findChild(QTabWidget, "mainTab")
    if tab:
        # 检测系统深色/浅色模式，标签栏与 macOS 标题栏融合
        try:
            app_ref = QApplication.instance()
            if app_ref and hasattr(app_ref, "styleHints"):
                is_dark = app_ref.styleHints().colorScheme() == Qt.ColorScheme.Dark
            else:
                is_dark = False
        except Exception:
            is_dark = False

        if is_dark:
            tab_text = "#f0f0f0"        # 浅色文字（深色标题栏上）
        else:
            tab_text = "#1d1d1f"        # 深色文字（浅色标题栏上）

        tab_pad_v = max(4, int(font_size * 0.35))   # 上下内边距 ~6px@16pt
        tab_pad_h = max(12, int(font_size * 0.95))  # 左右内边距 ~15px@16pt
        tab_bar_selected = "#007aff"  # 选中标签底部指示线

        # toolbar/tab bar 背景设为 transparent，让 macOS 原生统一标题栏材质透过来
        tab.setStyleSheet(f"""
            QTabWidget {{
                border: none;
                padding: 0px;
            }}
            QTabWidget::pane {{
                background: transparent;
                border: none;
                top: 0px;
            }}
            QToolBar#unifiedToolbar {{
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
                spacing: 0px;
            }}
            QTabBar {{
                background: transparent;
            }}
            QTabBar::tab {{
                background: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                padding: {tab_pad_v}px {tab_pad_h}px;
                margin: 0px;
                color: {tab_text};
            }}
            QTabBar::tab:selected {{
                border-bottom: 2px solid {tab_bar_selected};
            }}
            QTabBar::tab:hover:!selected {{
                border-bottom: 2px solid rgba(0,122,255,0.3);
            }}
            QTabBar::tab:first {{
                margin-left: 4px;
            }}
        """)
        for i in range(tab.count()):
            page = tab.widget(i)
            # tab_settings 通过 WA_TranslucentBackground 实现透明，
            # 不能用 QSS background: transparent（会传播到右侧 ScrollArea viewport）
            if page and page.objectName() != "tab_settings":
                page.setStyleSheet("background: transparent;")

    # 状态栏使用固定深灰色背景+白字，无需随外观联动刷新
