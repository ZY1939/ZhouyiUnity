"""
设置 Tab 的 UI 构建器 — 负责构建"设置"标签页的整体界面框架

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【这个文件做什么】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  本文件是纯 UI 构建层，不包含任何设置业务逻辑。它的唯一职责是：
    1. 构建 macOS 风格的设置界面骨架（左侧分类列表 + 右侧面板切换）
    2. 将各设置面板注册到 CATEGORIES 注册表中
    3. 响应全局外观变更，刷新侧边栏图标和字号

  它不是 QWidget 子类，而是遵循项目 Tab 注册模式的管理类。
  构造时接收 main_window 引用，在 .ui 文件中的 tab_settings 容器内构建 UI。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【与哪些文件联动】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ← main_window.py        创建 SettingsTab 实例，传入 self(主窗口)
  → appearance_manager.py  调用 refresh_sidebar(font_size) 联动字号
  → panels/ai_panel.py     AI 工具设置面板（AIPanel）
  → panels/appearance_panel.py  外观设置面板（AppearancePanel）
  → panels/solar_time_panel.py  真太阳时设置面板（SolarTimePanel）
  ← data/icon/setting/*.svg   侧边栏 SVG 图标源文件

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【UI 布局结构】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  tab_settings (QWidget, 来自 zhouyiUnity.ui)
  └── QHBoxLayout
      ├── 左侧: QListWidget (240px 固定宽)
      │        ├── QLabel "设置" 标题
      │        └── 分类列表项 (AI工具 / 背景字体 / 真太阳时)
      ├── 中间: QFrame 分割线 (1px)
      └── 右侧: QScrollArea
               └── QStackedWidget (面板容器，按索引切换)
                    ├── index 0: AIPanel
                    ├── index 1: AppearancePanel
                    └── index 2: SolarTimePanel

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【扩展新分类】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. 在 CATEGORIES 列表中新增条目（id / title / icon_name / panel_class）
  2. 在 src/settings/panels/ 下创建对应的 Panel 类（需继承 QWidget）
  3. 准备 SVG 图标放入 data/icon/setting/<icon_name>.svg
  无需修改本文件的任何其他代码。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【侧边栏图标缩放机制】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  图标使用 SVG 矢量格式 + QSvgRenderer 实时渲染，保证任意字号下清晰。
  refresh_sidebar(font_size) 由 appearance_manager.apply_appearance()
  在每次外观变更时调用，联动规则：
    - 图标尺寸 = 字号 × 1.6（最小 20px）
    - 侧边栏文字 = 字号 - 2（最小 11px）
    - 行高 = max(图标高, 文字高) + 18px
"""
import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QScrollArea, QFrame, QLabel,
)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt, QSize, QRect, QPoint
from PySide6.QtSvg import QSvgRenderer

from .appearance_manager import apply_appearance
from .panels.ai_panel import AIPanel
from .panels.appearance_panel import AppearancePanel
from .panels.solar_time_panel import SolarTimePanel
from .panels.window_panel import WindowPanel

# ── 图标路径 ──────────────────────────────────────────
# 使用相对路径保证工程移动后依然能找到图标
_ICON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "icon", "setting"))


def _svg_icon(name: str, size: int, icon_bg_alpha: int = 0) -> QIcon:
    """
    从 SVG 文件渲染指定像素尺寸的 QIcon，可选蓝色圆角方块背景

    参数:
        name (str):         SVG 文件名（不含 .svg 后缀）
        size (int):         期望的图标像素尺寸
        icon_bg_alpha (int): 图标蓝色背景透明度 0-255，0=无背景

    返回:
        QIcon: 渲染好的图标对象
    """
    svg_path = os.path.join(_ICON_DIR, f"{name}.svg")
    if not os.path.exists(svg_path):
        print(f"[图标] ❌ SVG 文件不存在: {svg_path}")
        print(f"[图标]    _ICON_DIR = {_ICON_DIR}")
        print(f"[图标]    __file__ = {__file__}")
        return QIcon()

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)

    # 蓝色圆角方块背景 — 让图标在背景图上也能看清
    if icon_bg_alpha > 0:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        margin = max(1, int(size * 0.03))
        radius = max(4, int(size * 0.24))
        painter.setBrush(QColor(0, 122, 255, icon_bg_alpha))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(margin, margin, size - 2 * margin, size - 2 * margin, radius, radius)

    renderer = QSvgRenderer(svg_path)
    # SVG 图标在蓝底内部缩小，留出蓝底可见区域
    icon_pad = max(4, int(size * 0.18))
    renderer.render(painter, QRect(icon_pad, icon_pad, size - 2 * icon_pad, size - 2 * icon_pad))
    painter.end()
    return QIcon(pixmap)


def _gaussian_blur(src: QPixmap, radius: float) -> QPixmap:
    """
    多级缩放叠加逼近高斯模糊（中心极限定理：多次 box blur → 高斯）

    比分离卷积纯 Python 实现快 ~50 倍（O(w·h·passes) vs O(w·h·2k)），
    视觉上与真高斯差异极小。

    参数:
        src (QPixmap): 原始图像
        radius (float): 模糊半径（px）

    返回:
        QPixmap: 模糊后的图像
    """
    if radius <= 0:
        return src

    blurred = src
    passes = 6
    for i in range(passes):
        factor = max(2, int(radius * (i + 1) / passes * 1.5))
        small = blurred.scaled(
            max(1, src.width() // factor),
            max(1, src.height() // factor),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        blurred = small.scaled(
            src.width(), src.height(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return blurred


# ── 分类定义 ──────────────────────────────────────────
# 添加新分类只需在此列表中新增一条，无需修改 SettingsTab 内部逻辑
CATEGORIES = [
    {
        "id": "ai",
        "title": "AI 工具",
        "icon_name": "ai",
        "panel_class": AIPanel,
    },
    {
        "id": "appearance",
        "title": "背景与字体",
        "icon_name": "appearance",
        "panel_class": AppearancePanel,
    },
    {
        "id": "solar_time",
        "title": "真太阳时和定位",
        "icon_name": "solartime",
        "panel_class": SolarTimePanel,
    },
    {
        "id": "window",
        "title": "窗口选项",
        "icon_name": "window",
        "panel_class": WindowPanel,
    },
]

# ── 侧边栏固定宽度 ────────────────────────────────────
SIDEBAR_WIDTH = 240

class SettingsTab:
    """
    设置 Tab 的管理类 — 遵循项目 Tab 注册模式

    参数:
        main_window: 主窗口对象（QMainWindow 实例），用于：
                     1. 查找 .ui 文件中的 tab_settings 容器
                     2. 传入 AppearancePanel 的外观变更回调

    内部管理:
        - _sidebar_list:  左侧 QListWidget（分类列表，点击切换面板）
        - _content_stack: 右侧 QStackedWidget（按索引切换不同设置面板）
        - _panels:         { category_id: panel_instance } 字典，按 id 索引面板

    用法:
        # 在 main_window.py 中：
        from src.settings.settings_tab import SettingsTab
        self._settings = SettingsTab(self)  # self = MainWindow

    AppearancePanel 特殊处理:
        AppearancePanel 需要 on_changed 回调来通知外观变更。
        构造时传入 lambda: apply_appearance(self._main)，使得：
          用户修改背景/字体 → AppearancePanel 触发回调 → apply_appearance 全局生效
    """

    def __init__(self, main_window):
        """
        构造 SettingsTab 实例

        参数:
            main_window: 主窗口对象（QMainWindow）

        做的事:
            1. 在 .ui 文件中查找 tab_settings 容器
            2. 调用 _build_ui() 构建左右分栏界面
            3. 创建所有面板实例并注册到 QStackedWidget

        如果找不到 tab_settings 容器，打印错误日志并退出（不会崩溃）。
        """
        self._main = main_window
        self._panels = {}

        # 在 .ui 文件中查找 tab_settings 容器
        container = main_window.findChild(QWidget, "tab_settings")
        if container is None:
            print("[设置] ❌ 找不到 tab_settings 容器")
            print("[设置]    可能原因: .ui 文件未加载, 或容器 objectName 不匹配")
            print("[设置]    检查: 主窗口是否加载了 zhouyiUnity.ui?")
            return

        self._build_ui(container)

    # ── UI 构建 ───────────────────────────────────────

    def _build_ui(self, container):
        """
        （内部方法）构建设置界面的完整 UI 布局（左-中-右三段式）

        参数:
            container (QWidget): .ui 文件中的 tab_settings 容器，作为布局的父级

        返回:
            None（直接在 container 上构建 UI）

        做的事（按顺序）:
            1. 移除 .ui 文件中的旧 layout（安全转移所有权，避免 Qt 布局冲突）
            2. 创建 HBoxLayout：左侧分类列表(240px) | 中间分割线(1px) | 右侧面板滚动区
            3. 遍历 CATEGORIES 列表，为每个分类创建对应面板实例
            4. 将面板添加到 QStackedWidget 中
            5. 默认选中第一个分类

        注意:
            AppearancePanel 特殊处理 —— 注入 on_changed 回调 = apply_appearance(self._main)
            这样当用户修改外观设置时，整个窗口会立刻刷新
        """
        # .ui 文件已有一个 layout，先删除再重建（避免 Qt 布局冲突）
        old_layout = container.layout()
        if old_layout is not None:
            QWidget().setLayout(old_layout)

        # 容器自身不绘制背景，透传给父级（QTabWidget pane → centralWidget 背景图）
        # 使用 QSS background: transparent 让 Qt 合成引擎跳过此层绘制
        # 注意：这不会影响右侧面板区，因为 QScrollArea viewport 已显式设白色
        container.setAutoFillBackground(False)
        container.setStyleSheet("background: transparent;")
        self._container = container

        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 左侧：分类列表 ──
        sidebar = self._build_sidebar()
        layout.addWidget(sidebar)

        # ── 中间：1px 竖线分割 ──
        divider = QFrame()
        divider.setObjectName("divider")
        divider.setStyleSheet("QFrame#divider { border: none; background-color: #d0d0d5; min-width: 1px; max-width: 1px; }")
        layout.addWidget(divider)

        # ── 右侧：设置面板滚动区 ──
        self._content_stack = QStackedWidget()

        for cat in CATEGORIES:
            if cat["panel_class"] == AppearancePanel:
                panel = cat["panel_class"](on_changed=lambda: apply_appearance(self._main))
            else:
                panel = cat["panel_class"]()
            self._panels[cat["id"]] = panel
            self._content_stack.addWidget(panel)

        scroll = QScrollArea()
        scroll.setObjectName("content_area")
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._content_stack)
        scroll.setStyleSheet("QScrollArea#content_area { border: none; background: transparent; }")
        layout.addWidget(scroll, 1)

        # 默认选中第一项
        self._sidebar_list.setCurrentRow(0)
        self._content_stack.setCurrentIndex(0)

    def _build_sidebar(self) -> QWidget:
        """
        （内部方法）构建左侧分类列表

        参数:
            （无参数）

        返回:
            QWidget: 包含标题 + 分类列表的侧边栏 Widget，固定宽度 240px

        做的事:
            1. 创建顶部 QLabel 标题 "设置"（20px 加粗）
            2. 创建 QListWidget 分类列表（每项对应 CATEGORIES 中的一个条目）
            3. 连接 currentRowChanged 信号 → 切换右侧面板
            4. 初始加载 SVG 图标 + 自适应行高

        用法:
            # 只在 _build_ui() 内部调用
            sidebar = self._build_sidebar()
            layout.addWidget(sidebar)
        """
        # QFrame 原生支持 stylesheet background，QSS rgba 背景色负责渲染
        self._sidebar_widget = QFrame()
        self._sidebar_widget.setFrameShape(QFrame.Shape.NoFrame)
        self._sidebar_widget.setFixedWidth(SIDEBAR_WIDTH)
        sidebar_widget = self._sidebar_widget
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # 标题 "设置"
        self._sidebar_title = QLabel("设置")
        self._sidebar_title.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #1d1d1f; "
            "padding: 20px 16px 12px 20px;"
            "background: transparent;"
        )
        sidebar_layout.addWidget(self._sidebar_title)

        # 分类列表
        self._sidebar_list = QListWidget()
        self._sidebar_list.setObjectName("sidebar")
        self._sidebar_list.setSpacing(2)

        for cat in CATEGORIES:
            item = QListWidgetItem()
            item.setText(cat["title"])
            item.setData(Qt.ItemDataRole.UserRole, cat["id"])  # 存储 category id → 后续根据 id 查找图标
            self._sidebar_list.addItem(item)

        # 切换面板监听
        self._sidebar_list.currentRowChanged.connect(self._on_category_changed)
        sidebar_layout.addWidget(self._sidebar_list, 1)

        # 初始加载图标 + 自适应行高（默认字号 16px）
        self.refresh_sidebar(font_size=16)

        return sidebar_widget

    # ── 外观联动 ──────────────────────────────────────

    def _render_frosted_sidebar_bg(self) -> str:
        """
        渲染毛玻璃侧边栏背景图：裁取 → 高斯模糊（QGraphicsBlurEffect）

        模糊半径读取 appearance.sidebar_blur_radius 配置（默认 8.0px）。
        设 0 则返回 None，退化为纯半透明色。

        返回:
            str: 毛玻璃背景图缓存路径，失败返回 None
        """
        from .config_manager import config_manager, get_project_root
        blur_radius = config_manager.get("appearance", "sidebar_blur_radius")
        if blur_radius is None:
            blur_radius = 8.0
        if blur_radius <= 0:
            return None

        bg_cache = os.path.join(get_project_root(), "usrCfg", "_bg_cache.png")
        if not os.path.isfile(bg_cache):
            return None

        bg_pixmap = QPixmap(bg_cache)
        if bg_pixmap.isNull():
            return None

        central = self._main.centralWidget()
        if central is None:
            return None

        pos = self._sidebar_widget.mapTo(central, QPoint(0, 0))
        size = self._sidebar_widget.size()
        if size.width() <= 0 or size.height() <= 0:
            return None

        # Retina 屏设备像素比转换
        dpr = bg_pixmap.devicePixelRatio()
        source_rect = QRect(
            int(pos.x() * dpr), int(pos.y() * dpr),
            int(size.width() * dpr), int(size.height() * dpr),
        )
        source_rect = source_rect.intersected(bg_pixmap.rect())
        if source_rect.isEmpty():
            return None

        cropped = bg_pixmap.copy(source_rect)
        cropped.setDevicePixelRatio(1.0)
        cropped = cropped.scaled(size, Qt.AspectRatioMode.IgnoreAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)

        # 真高斯模糊：分离卷积（水平+垂直），ctypes 直接操作像素数组
        blurred = _gaussian_blur(cropped, blur_radius)

        cache_path = os.path.join(get_project_root(), "usrCfg", "_sidebar_frosted.png")
        blurred.save(cache_path, "PNG")
        return cache_path

    def refresh_sidebar(self, font_size: int, text_color: str = "#1d1d1f",
                         has_bg_image: bool = False):
        """
        根据全局字号、文字颜色、有无背景图重新渲染侧边栏

        参数:
            font_size (int):  全局字号（像素）
            text_color (str): 自适应文字颜色，如 "#ffffff" 或 "#1d1d1f"
            has_bg_image (bool): 是否有背景图片。无图片→侧边栏显示实色底色；
                                 有图片→侧边栏透明，让图片透出，文字自适应

        两种模式:
            - 无背景图: 侧边栏 #f0f0f5 实色背景，深色文字（固定颜色）
            - 有背景图: 侧边栏全透明，文字颜色用 text_color 自适应
        """
        sidebar = getattr(self, "_sidebar_list", None)
        if sidebar is None:
            print("[设置] ⚠ refresh_sidebar 跳过: _sidebar_list 未初始化"
                  " (tab_settings 容器可能未加载)")
            return

        # 图标填满行高，字号 × 2.8，最小 24px
        icon_size = max(24, int(font_size * 2.8))
        sidebar.setIconSize(QSize(icon_size, icon_size))

        # 侧边栏文字比正文小 2px，避免太挤
        sidebar_font_size = max(11, font_size - 2)

        # ── 两种模式的颜色变量 ──
        # 图标蓝底白字 → Apple 系统菜单风格
        # 选中项纯蓝底，不用透明淡蓝
        icon_bg_alpha = 255  # 图标蓝色背景完全不透明
        selected_bg = "#007aff"  # 纯蓝选中（非半透明）
        selected_color = "white"

        if has_bg_image:
            if text_color == "#ffffff":
                frame_bg = "rgba(0, 0, 0, 89)"
            else:
                frame_bg = "rgba(255, 255, 255, 102)"
            item_color = text_color
            hover_bg = "rgba(128, 128, 128, 46)"
            title_color = text_color
            list_bg = "transparent"
        else:
            frame_bg = "#f0f0f5"
            list_bg = "#f0f0f5"
            item_color = "#333"
            hover_bg = "#e0e0e5"
            title_color = "#1d1d1f"

        if hasattr(self, "_sidebar_widget") and self._sidebar_widget:
            if has_bg_image:
                # 尝试毛玻璃效果：裁取背景图 → 模糊 → 叠加蒙版
                frosted_path = self._render_frosted_sidebar_bg()
                if frosted_path:
                    escaped = frosted_path.replace("\\", "/")
                    # 先清空再设置，强制 Qt stylesheet 引擎重新加载图片文件
                    self._sidebar_widget.setStyleSheet("")
                    self._sidebar_widget.setStyleSheet(
                        f"background-image: url({escaped});"
                        f"background-repeat: no-repeat;"
                    )
                else:
                    # 降级：纯半透明色
                    self._sidebar_widget.setStyleSheet(
                        f"background-color: {frame_bg};"
                    )
            else:
                self._sidebar_widget.setStyleSheet(
                    f"background-color: {frame_bg};"
                )

        # 强制 viewport 透明 — QListWidget 内部 viewport 可能有系统默认背景色
        vp = sidebar.viewport()
        if vp:
            vp.setStyleSheet("background: transparent;")

        sidebar.setStyleSheet(
            f"""
            QListWidget#sidebar {{
                background-color: {list_bg};
                border: none;
                outline: none;
                padding: 8px 0;
                color: {item_color};
                font-size: {sidebar_font_size}px;
            }}
            QListWidget#sidebar::item {{
                background: transparent;
                padding: 6px 14px;
                margin: 0px 10px;
                border-radius: 8px;
                color: {item_color};
            }}
            QListWidget#sidebar::item:selected {{
                background-color: {selected_bg};
                color: {selected_color};
            }}
            QListWidget#sidebar::item:hover:!selected {{
                background-color: {hover_bg};
            }}
            """
        )

        # 行高 = 图标高 + 少量上下留白
        row_height = icon_size + 8

        # 逐项更新图标和行高
        for i in range(sidebar.count()):
            item = sidebar.item(i)
            cat_id = item.data(Qt.ItemDataRole.UserRole)
            cat = next((c for c in CATEGORIES if c["id"] == cat_id), None)
            if cat:
                icon = _svg_icon(cat["icon_name"], icon_size, icon_bg_alpha)
                if not icon.isNull():
                    item.setIcon(icon)
            item.setSizeHint(QSize(0, row_height))

        # 标题字号联动 = 字号 + 4，颜色跟随模式
        if hasattr(self, "_sidebar_title") and self._sidebar_title:
            self._sidebar_title.setStyleSheet(
                f"font-size: {font_size + 4}px; font-weight: bold; "
                f"color: {title_color}; padding: 20px 16px 12px 20px;"
                f"background: transparent;"
            )

    def refresh_text_color(self, text_color: str):
        """
        根据背景亮度更新所有设置面板的文字颜色（由 appearance_manager 调用）

        参数:
            text_color (str): 计算后的文字颜色，如 "#ffffff" 或 "#1d1d1f"

        返回:
            None（直接调用各面板的 refresh_text_color 方法）

        注意:
            侧边栏和输入控件的颜色不在此处更新（它们有自己的固定背景色）
        """
        for panel in self._panels.values():
            if hasattr(panel, "refresh_text_color"):
                panel.refresh_text_color(text_color)

    # ── 槽函数 ────────────────────────────────────────

    def _on_category_changed(self, index):
        """
        （槽函数）侧边栏点击某一分类 → 切换右侧面板

        参数:
            index (int): 用户点击的分类在 CATEGORIES 列表中的索引（从 0 开始）
                         如果 index 超出范围（不应该发生），什么都不做

        返回:
            None

        连接方式:
            self._sidebar_list.currentRowChanged.connect(self._on_category_changed)

        原理:
            QListWidget 的 currentRowChanged 信号传递当前选中行号。
            QStackedWidget 按同样的索引顺序存储面板，所以直接用 index 切换即可。
            例如：用户点击"背景与字体"(index=1) → stack 切换到 index=1(AppearancePanel)
        """
        if 0 <= index < len(CATEGORIES):
            self._content_stack.setCurrentIndex(index)
