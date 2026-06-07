"""
外观设置面板 — 背景颜色、背景图片、字体、字号、行距 + 实时预览

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【这个文件做什么】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  提供完整的外观设置界面，用户在此面板中调整：
    1. 背景颜色 — 系统取色器选择任意颜色
    2. 背景图片 — 浏览本地图片（支持 png/jpg/jpeg/bmp/gif）
    3. 字体 — QFontComboBox 列出系统中所有可用字体
    4. 字号 — 10-48px 范围
    5. 行距 — 1.0-3.0 倍，步进 0.1

  所有配置变更自动保存到 usrCfg/UsrCfg.json，并通过 on_changed 回调
  通知 appearance_manager 即时生效。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【面板结构（三个 QGroupBox）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. 背景设置:
     - 颜色行: 色块预览(点击可选色) + 十六进制值标签 + "选择颜色..."按钮
     - 图片行: 路径输入框 + "浏览..."按钮 + "清除"按钮

  2. 字体设置:
     - QFontComboBox 字体选择 — 自动列出系统所有中文字体
     - QSpinBox 字号选择 — 10-48px
     - QDoubleSpinBox 行距选择 — 1.0-3.0，步进 0.1

  3. 预览区域:
     - QFrame 内嵌标题 + 正文段落（中英文混排 + 周易名句）
     - 即时反映当前的字体/字号/行距/背景色效果

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【配置变更通知机制】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  构造函数接受 on_changed 回调（签名: () -> None）。
  settings_tab.py 将 apply_appearance 函数作为回调传入：
    AppearancePanel(on_changed=lambda: apply_appearance(self._main))

  每当用户修改外观设置 → _notify_changed() 调用回调 → apply_appearance 执行
  → 全局字体、背景色、侧边栏图标等全部即时刷新。

  这样实现了"所见即所得"：用户在面板中调整，整个程序窗口立刻看到效果。
"""
import os
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QSpinBox, QDoubleSpinBox,
    QFontComboBox, QComboBox, QLineEdit, QGroupBox,
    QColorDialog, QFileDialog, QFrame, QCheckBox,
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt

from ..config_manager import config_manager

PANEL_STYLE = """
QWidget {{
    background: transparent;
}}
QGroupBox {{
    background: transparent;
    font-weight: bold;
    border: 1px solid #dcdcdc;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    color: {text_color};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {text_color};
}}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QFontComboBox {{
    padding: 6px 10px;
    border: 1px solid #c0c0c0;
    border-radius: 6px;
    background: white;
    color: #1d1d1f;
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QFontComboBox:focus {{
    border-color: #007aff;
}}
QComboBox QAbstractItemView {{
    background: white;
    color: #1d1d1f;
    selection-background-color: #007aff;
    selection-color: white;
}}
QPushButton {{
    padding: 6px 18px;
    border-radius: 6px;
    border: 1px solid #c0c0c0;
    background: #f5f5f5;
    color: #1d1d1f;
}}
QPushButton:hover {{
    background: #e8e8e8;
}}
#color_preview {{
    border: 1px solid #c0c0c0;
    border-radius: 6px;
    min-width: 32px;
    min-height: 32px;
    max-width: 32px;
    max-height: 32px;
}}
#preview_frame {{
    border: 1px solid #dcdcdc;
    border-radius: 8px;
    background: #ffffff;
    padding: 20px;
    color: #1d1d1f;
}}
QCheckBox {{
    background: transparent;
    color: {text_color};
    spacing: 8px;
}}
QLabel {{
    background: transparent;
    color: {text_color};
}}
"""


class AppearancePanel(QWidget):
    """
    外观设置面板 — 背景、字体、预览一体化

    参数:
        parent (QWidget, 可选): 父 Widget
        on_changed (callable, 可选): 配置变更回调，签名 () -> None
            每次用户修改外观设置后自动调用此回调。
            settings_tab.py 传入 lambda: apply_appearance(self._main)，实现即时生效。

    用法:
        # 在 settings_tab.py 中创建：
        from .panels.appearance_panel import AppearancePanel

        # 带回调（修改外观后整个窗口即时刷新）:
        panel = AppearancePanel(on_changed=lambda: apply_appearance(main_window))

        # 不带回调（仅独立使用）:
        panel = AppearancePanel()
    """

    def __init__(self, parent=None, on_changed=None):
        """
        构造 AppearancePanel 实例

        参数:
            parent (QWidget, 可选): 父 Widget
            on_changed (callable, 可选): 配置变更回调，每次修改后调用

        做的事:
            1. 初始化 _bg_color 和 _bg_image 内存变量
            2. 保存 on_changed 回调引用
            3. 调用 _init_ui() 构建界面
            4. 调用 _load_config() 从 usrCfg 加载已有配置
            5. 调用 _connect_signals() 绑定控件事件
        """
        super().__init__(parent)
        self._bg_color = "#f5f5f5"    # 当前背景颜色（十六进制字符串）
        self._bg_image = ""            # 当前背景图片路径（空字符串 = 不使用）
        self._on_changed = on_changed  # 配置变更回调（由 settings_tab 传入）
        self._init_ui()
        self._load_config()
        self._connect_signals()

    # ── UI 构建 ───────────────────────────────────────

    def _init_ui(self):
        """
        （内部方法）构建面板的完整 UI 布局

        参数:
            （无参数）

        返回:
            None（直接设置 self 的布局和子控件）

        UI 结构（从上到下的三个 QGroupBox）:
            1. "背景" GroupBox:
               - 颜色行: 色块预览 QFrame + 颜色值 QLabel + "选择颜色..." QPushButton
               - 图片行: 路径输入 QLineEdit + "浏览..." QPushButton + "清除" QPushButton

            2. "字体" GroupBox:
               - QFontComboBox 字体下拉（带预览，自动列出系统字体）
               - QSpinBox 字号 10-48px
               - QDoubleSpinBox 行距 1.0-3.0（步进 0.1）

            3. "预览" GroupBox:
               - QFrame 容器，内部包含标题 QLabel 和正文 QLabel
               - 标题显示"预览标题 Sample Title"
               - 正文包含中英文混排 + "天行健，君子以自强不息"
               - 即时反映当前设置的视觉效果

        交互细节:
            - 色块预览可点击（mousePressEvent → _on_color_pick），和"选择颜色"按钮等效
            - 色块鼠标光标变为手形（PointingHandCursor），暗示可点击
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(20)

        # ── 背景设置 ──
        bg_group = QGroupBox("背景")
        bg_layout = QFormLayout(bg_group)
        bg_layout.setSpacing(12)

        # 背景颜色行：色块预览 + 十六进制值 + 选择按钮
        color_row = QHBoxLayout()
        self._color_preview = QFrame()
        self._color_preview.setObjectName("color_preview")
        self._color_preview.setCursor(Qt.CursorShape.PointingHandCursor)  # 手形光标暗示可点击
        self._color_preview.mousePressEvent = self._on_color_pick  # 点击色块也能弹出取色器
        color_row.addWidget(self._color_preview)

        self._color_label = QLabel("#f5f5f5")  # 显示当前颜色的十六进制值
        color_row.addWidget(self._color_label)

        self._btn_color = QPushButton("选择颜色...")
        self._btn_color.clicked.connect(self._on_color_pick)
        color_row.addWidget(self._btn_color)
        color_row.addStretch()
        bg_layout.addRow("背景颜色：", color_row)

        # 背景图片行：路径输入 + 浏览 + 清除
        img_row = QHBoxLayout()
        self._bg_image_input = QLineEdit()
        self._bg_image_input.setPlaceholderText("留空则不使用背景图片...")
        img_row.addWidget(self._bg_image_input)

        self._btn_browse_img = QPushButton("浏览...")
        self._btn_browse_img.clicked.connect(self._on_browse_image)
        img_row.addWidget(self._btn_browse_img)

        self._btn_clear_img = QPushButton("清除")
        self._btn_clear_img.clicked.connect(self._on_clear_image)
        img_row.addWidget(self._btn_clear_img)
        bg_layout.addRow("背景图片：", img_row)

        # 图片模式 + 透明度（同一行）
        mode_opacity_row = QHBoxLayout()
        mode_opacity_row.setSpacing(8)
        self._bg_mode_combo = QComboBox()
        self._bg_mode_combo.addItems(["拉伸填满", "适应窗口", "居中", "平铺"])
        mode_opacity_row.addWidget(self._bg_mode_combo)
        mode_opacity_row.addWidget(QLabel("透明度："))
        self._bg_opacity_spin = QSpinBox()
        self._bg_opacity_spin.setRange(10, 100)
        self._bg_opacity_spin.setSingleStep(10)
        self._bg_opacity_spin.setValue(100)
        self._bg_opacity_spin.setSuffix(" %")
        self._bg_opacity_spin.setFixedWidth(80)
        mode_opacity_row.addWidget(self._bg_opacity_spin)
        mode_opacity_row.addStretch()
        bg_layout.addRow("图片模式：", mode_opacity_row)

        root.addWidget(bg_group)

        # ── 字体设置 ──
        font_group = QGroupBox("字体")
        font_layout = QFormLayout(font_group)
        font_layout.setSpacing(12)

        # 字体 + 字号 + 行距（同一行，自适应宽度）
        font_row = QHBoxLayout()
        font_row.setSpacing(8)
        # 字体选择
        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(QFont("PingFang SC"))
        font_box = QHBoxLayout()
        font_box.setSpacing(1)
        font_box.addWidget(QLabel("字体："))
        font_box.addWidget(self._font_combo)
        font_row.addLayout(font_box)
        # 字号
        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(10, 48)
        self._font_size_spin.setValue(16)
        self._font_size_spin.setSuffix(" px")
        size_box = QHBoxLayout()
        size_box.setSpacing(1)
        size_box.addWidget(QLabel("字号："))
        size_box.addWidget(self._font_size_spin)
        font_row.addLayout(size_box)
        # 行距
        self._line_spacing_spin = QDoubleSpinBox()
        self._line_spacing_spin.setRange(1.0, 3.0)
        self._line_spacing_spin.setSingleStep(0.1)
        self._line_spacing_spin.setValue(1.5)
        self._line_spacing_spin.setDecimals(2)
        line_box = QHBoxLayout()
        line_box.setSpacing(1)
        line_box.addWidget(QLabel("行距："))
        line_box.addWidget(self._line_spacing_spin)
        font_row.addLayout(line_box)
        # 剩余空间推至右侧
        font_row.addStretch()
        font_layout.addRow(font_row)

        # 文字颜色：自动适配 / 手动选择
        text_color_row = QHBoxLayout()
        text_color_row.setSpacing(8)
        self._auto_text_cb = QCheckBox("自动适配")
        self._auto_text_cb.setChecked(True)
        text_color_row.addWidget(self._auto_text_cb)
        self._text_color_combo = QComboBox()
        self._text_color_combo.addItems(["深色文字", "浅色文字"])
        self._text_color_combo.hide()
        text_color_row.addWidget(self._text_color_combo)
        text_color_row.addStretch()
        font_layout.addRow("文字颜色：", text_color_row)

        # 可读性增强：遮盖层降低背景图对比度，让文字更清晰
        overlay_row = QHBoxLayout()
        overlay_row.setSpacing(8)
        self._overlay_cb = QCheckBox("启用")
        self._overlay_cb.setToolTip("在背景图上叠加半透明遮罩，增强文字可读性")
        overlay_row.addWidget(self._overlay_cb)
        self._overlay_combo = QComboBox()
        self._overlay_combo.addItems(["轻度", "中度", "重度"])
        self._overlay_combo.hide()
        overlay_row.addWidget(self._overlay_combo)
        overlay_row.addStretch()
        font_layout.addRow("可读性增强：", overlay_row)
        root.addWidget(font_group)

        # ── 预览区域 ──
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)

        self._preview_frame = QFrame()
        self._preview_frame.setObjectName("preview_frame")
        self._preview_frame.setMinimumHeight(120)
        preview_inner = QVBoxLayout(self._preview_frame)

        # 预览中的标题文字（比正文大 4px 并加粗）
        self._preview_title = QLabel("预览标题 Sample Title")
        self._preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_inner.addWidget(self._preview_title)

        # 预览中的正文段落（中英文混排 + 周易名句）
        self._preview_body = QLabel(
            "这是一段预览文字，用于展示当前字体、字号和行距的视觉效果。\n"
            "The quick brown fox jumps over the lazy dog.\n"
            "周易 — 天行健，君子以自强不息。"
        )
        self._preview_body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_body.setWordWrap(True)
        preview_inner.addWidget(self._preview_body)
        preview_layout.addWidget(self._preview_frame)
        root.addWidget(preview_group)

        root.addStretch()
        self.setStyleSheet(PANEL_STYLE.format(text_color="#1d1d1f"))

    def refresh_text_color(self, text_color: str):
        """
        根据背景亮度更新面板文字颜色（由 appearance_manager 调用）

        参数:
            text_color (str): 计算后的文字颜色，如 "#ffffff" 或 "#1d1d1f"
        """
        self.setStyleSheet(PANEL_STYLE.format(text_color=text_color))

    # ── 配置加载/保存 ─────────────────────────────────

    def _load_config(self):
        """
        （内部方法）从 usrCfg 加载外观配置并填充到各控件

        参数:
            （无参数，从 config_manager 读取配置）

        返回:
            None

        加载内容:
            - background_color → 设置 _bg_color + 更新色块预览
            - background_image → 设置 _bg_image + 填入路径输入框
            - font_family      → 设置 QFontComboBox 当前字体
            - font_size        → 设置 QSpinBox 当前值
            - line_spacing     → 设置 QDoubleSpinBox 当前值

        加载完成后调用 _update_preview() 刷新预览区域。
        """
        cfg = config_manager.get("appearance") or {}

        self._bg_color = cfg.get("background_color", "#f5f5f5")
        self._update_color_preview()

        self._bg_image = cfg.get("background_image", "")
        self._bg_image_input.setText(self._bg_image)

        # 图片模式
        mode = cfg.get("background_image_mode", "fill")
        mode_map = {"fill": 0, "fit": 1, "center": 2, "tile": 3}
        self._bg_mode_combo.setCurrentIndex(mode_map.get(mode, 0))

        # 图片透明度
        self._bg_opacity_spin.setValue(cfg.get("background_image_opacity", 100))

        # 自动补全缺失字段（兼容旧配置）
        if "background_image_mode" not in cfg:
            config_manager.set("appearance", "background_image_mode", value="fill")
        if "background_image_opacity" not in cfg:
            config_manager.set("appearance", "background_image_opacity", value=100)

        font_family = cfg.get("font_family", "PingFang SC")
        self._font_combo.setCurrentFont(QFont(font_family))

        font_size = cfg.get("font_size", 16)
        self._font_size_spin.setValue(font_size)

        line_spacing = cfg.get("line_spacing", 1.5)
        self._line_spacing_spin.setValue(line_spacing)

        # 文字颜色模式
        text_color_mode = cfg.get("text_color_mode", "auto")
        self._auto_text_cb.setChecked(text_color_mode == "auto")
        manual_color = cfg.get("text_color", "#1d1d1f")
        self._text_color_combo.setCurrentIndex(0 if manual_color == "#1d1d1f" else 1)
        self._text_color_combo.setVisible(text_color_mode == "manual")

        # 可读性增强遮罩
        self._overlay_cb.setChecked(cfg.get("overlay_enabled", False))
        strength = cfg.get("overlay_strength", "medium")
        strength_map = {"light": 0, "medium": 1, "strong": 2}
        self._overlay_combo.setCurrentIndex(strength_map.get(strength, 1))
        self._overlay_combo.setVisible(cfg.get("overlay_enabled", False))

        # 自动补全缺失字段（兼容旧配置）
        for key, val in [("text_color_mode", "auto"), ("text_color", "#1d1d1f"),
                         ("overlay_enabled", False), ("overlay_strength", "medium")]:
            if key not in cfg:
                config_manager.set("appearance", key, value=val)

        self._update_controls_enabled()
        self._update_preview()

    def _connect_signals(self):
        """
        （内部方法）连接各控件的变更信号到保存 + 预览 + 通知逻辑

        参数:
            （无参数）

        返回:
            None

        连接关系:
            - 背景图片输入框文本变更 → _save_appearance()（保存图片路径）
            - 字体下拉变更(currentFontChanged) → _on_font_changed()（保存 + 预览 + 通知）
            - 字号微调框变更(valueChanged) → _on_font_size_changed()（保存 + 预览 + 通知）
            - 行距微调框变更(valueChanged) → _on_line_spacing_changed()（保存 + 预览 + 通知）

        为什么行距也触发 _notify_changed:
            虽然行距目前没有全局生效（只有预览区用到），但未来可能会用到，
            先保持通知机制一致。
        """
        self._bg_image_input.textChanged.connect(self._save_appearance)
        self._bg_mode_combo.currentIndexChanged.connect(self._save_appearance)
        self._bg_opacity_spin.valueChanged.connect(self._save_appearance)
        self._font_combo.currentFontChanged.connect(self._on_font_changed)
        self._font_size_spin.valueChanged.connect(self._on_font_size_changed)
        self._line_spacing_spin.valueChanged.connect(self._on_line_spacing_changed)
        # 文字颜色
        self._auto_text_cb.toggled.connect(self._on_text_color_mode_changed)
        self._text_color_combo.currentIndexChanged.connect(self._save_text_color_config)
        # 可读性增强
        self._overlay_cb.toggled.connect(self._on_overlay_toggled)
        self._overlay_combo.currentIndexChanged.connect(self._save_overlay_config)

    def _notify_changed(self):
        """
        （内部方法）触发外观立即生效回调

        参数:
            （无参数）

        返回:
            None

        原理:
            调用构造时传入的 on_changed 回调（实际是 apply_appearance）。
            如果构造时没传 on_changed（为 None），什么都不做。

        用法:
            # 每次用户修改外观设置后自动调用
            self._notify_changed()
        """
        if self._on_changed:
            self._on_changed()

    def _save_appearance(self):
        """
        （内部方法）保存背景图片路径到 usrCfg，并触发外观刷新

        参数:
            （无参数，从 _bg_image_input 控件读取当前文本）

        返回:
            None

        保存内容:
            - appearance.background_image → 图片文件路径（去掉首尾空格）

        为什么背景颜色和字体不在这里保存:
            颜色、字体、字号、行距有各自的槽函数处理（_on_color_pick,
            _on_font_changed, _on_font_size_changed, _on_line_spacing_changed），
            它们各自负责保存对应的配置项。这里只保存背景图片。
        """
        config_manager.set("appearance", "background_image",
                           value=self._bg_image_input.text().strip())
        mode_map = {0: "fill", 1: "fit", 2: "center", 3: "tile"}
        config_manager.set("appearance", "background_image_mode",
                           value=mode_map.get(self._bg_mode_combo.currentIndex(), "fill"))
        config_manager.set("appearance", "background_image_opacity",
                           value=self._bg_opacity_spin.value())
        self._update_controls_enabled()
        self._notify_changed()

    def _update_controls_enabled(self):
        """背景图片有/无 → 控制文字颜色和遮罩选项的可用状态"""
        has_bg = bool(self._bg_image_input.text().strip())
        # 文字颜色：无图片时强制自动，有图片时可手动
        self._auto_text_cb.setEnabled(has_bg)
        if not has_bg:
            self._auto_text_cb.setChecked(True)
            self._text_color_combo.setVisible(False)
        # 可读性增强：仅在有图片时可用
        self._overlay_cb.setEnabled(has_bg)
        if not has_bg:
            self._overlay_cb.setChecked(False)
            self._overlay_combo.setVisible(False)

    def _on_text_color_mode_changed(self, checked):
        """自动适配 checkbox 切换"""
        mode = "auto" if checked else "manual"
        config_manager.set("appearance", "text_color_mode", value=mode)
        self._text_color_combo.setVisible(not checked)
        if not checked:
            self._save_text_color_config()
        self._notify_changed()

    def _save_text_color_config(self):
        """保存手动选择的文字颜色"""
        idx = self._text_color_combo.currentIndex()
        color = "#1d1d1f" if idx == 0 else "#ffffff"
        config_manager.set("appearance", "text_color", value=color)
        self._notify_changed()

    def _on_overlay_toggled(self, checked):
        """可读性增强 checkbox 切换"""
        config_manager.set("appearance", "overlay_enabled", value=checked)
        self._overlay_combo.setVisible(checked)
        if checked:
            self._save_overlay_config()
        else:
            self._notify_changed()

    def _save_overlay_config(self):
        """保存遮罩强度选择"""
        idx = self._overlay_combo.currentIndex()
        strength_map = {0: "light", 1: "medium", 2: "strong"}
        config_manager.set("appearance", "overlay_strength",
                           value=strength_map.get(idx, "medium"))
        self._notify_changed()

    def _on_font_changed(self, font):
        """
        （槽函数）字体变更 → 保存配置 + 更新预览 + 通知全局生效

        参数:
            font (QFont): QFontComboBox 当前选中的字体对象
                         由 currentFontChanged 信号自动传入

        返回:
            None

        做的事:
            1. 保存 font.family() 到 usrCfg（appearance.font_family）
            2. 刷新预览区域（立即看到新字体效果）
            3. 通知全局外观刷新（整个窗口字体立刻变化）
        """
        config_manager.set("appearance", "font_family", value=font.family())
        self._update_preview()
        self._notify_changed()

    def _on_font_size_changed(self, value):
        """
        （槽函数）字号变更 → 保存配置 + 更新预览 + 通知全局生效

        参数:
            value (int): QSpinBox 当前值（10-48），由 valueChanged 信号自动传入

        返回:
            None

        做的事:
            1. 保存 value 到 usrCfg（appearance.font_size）
            2. 刷新预览区域（预览文字立刻变大/变小）
            3. 通知全局外观刷新（整个窗口字号立刻变化）
        """
        config_manager.set("appearance", "font_size", value=value)
        self._update_preview()
        self._notify_changed()

    def _on_line_spacing_changed(self, value):
        """
        （槽函数）行距变更 → 保存配置 + 更新预览 + 通知全局刷新

        参数:
            value (float): QDoubleSpinBox 当前值（1.0-3.0），由 valueChanged 信号自动传入

        返回:
            None

        做的事:
            1. 保存 value 到 usrCfg（appearance.line_spacing）
            2. 刷新预览区域（预览文字行间距立刻变化）
            3. 通知全局刷新

        注意:
            目前行距只影响预览区的显示效果，不影响 QApplication 全局。
            QApplication.setFont() 不直接支持行距设置。
            这是为未来扩展预留的（如富文本编辑器中的行距）。
        """
        config_manager.set("appearance", "line_spacing", value=value)
        self._update_preview()
        self._notify_changed()

    # ── 颜色 ──────────────────────────────────────────

    def _on_color_pick(self, event=None):
        """
        （槽函数）弹出系统颜色选择器，选中后保存并更新预览

        参数:
            event: QMouseEvent 或 None
                   - 从"选择颜色..."按钮触发时 → event 为 None
                   - 从色块预览点击触发时 → event 为 QMouseEvent（被 mousePressEvent 重定向）

        返回:
            None

        流程:
            1. 弹出 QColorDialog（系统原生取色器，macOS 上支持吸管取色）
            2. 如果用户点击"确定"（color.isValid()=True）:
               - 保存十六进制颜色值到 self._bg_color
               - 写入 usrCfg（appearance.background_color）
               - 更新色块预览 + 更新预览区背景色 + 通知全局刷新
            3. 如果用户点击"取消" → 什么都不做（保持原颜色）

        用法:
            # 通过按钮 click 或色块 mousePressEvent 触发
            self._btn_color.clicked.connect(self._on_color_pick)
            self._color_preview.mousePressEvent = self._on_color_pick
        """
        color = QColorDialog.getColor(QColor(self._bg_color), self, "选择背景颜色")
        if color.isValid():
            self._bg_color = color.name()
            config_manager.set("appearance", "background_color", value=self._bg_color)
            self._update_color_preview()
            self._update_preview()
            self._notify_changed()

    def _update_color_preview(self):
        """
        （内部方法）更新色块预览和十六进制颜色值标签

        参数:
            （无参数，从 self._bg_color 读取当前颜色值）

        返回:
            None

        做的事:
            1. 设置色块 QFrame 的 CSS 背景色为当前颜色
            2. 更新颜色值 QLabel 的文字为当前十六进制值

        用法:
            # 选择新颜色后调用
            self._update_color_preview()
        """
        self._color_preview.setStyleSheet(
            f"#color_preview {{ background-color: {self._bg_color}; "
            f"border: 1px solid #c0c0c0; border-radius: 6px; }}"
        )
        self._color_label.setText(self._bg_color)

    # ── 图片 ──────────────────────────────────────────

    def _copy_bg_to_usrCfg(self, src_path: str) -> str:
        """
        将背景图片复制到 usrCfg/ 目录下，返回相对路径

        图片统一保存为 usrCfg/_bg_original.<ext>，配置中存储相对路径，
        这样项目工程移动后背景不会失效。
        """
        if not src_path:
            return src_path
        usrCfg_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "usrCfg")
        _proj_root = os.path.join(os.path.dirname(__file__), "..", "..", "..")

        # 相对路径 → 解析为绝对路径
        if not os.path.isabs(src_path):
            src_path = os.path.join(_proj_root, src_path)

        if not os.path.isfile(src_path):
            return src_path

        ext = os.path.splitext(src_path)[1] or ".png"
        dst = os.path.join(usrCfg_dir, f"_bg_original{ext}")
        if os.path.normpath(src_path) == os.path.normpath(dst):
            return f"usrCfg/_bg_original{ext}"

        # 清理旧格式的背景图文件
        for old_ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
            old = os.path.join(usrCfg_dir, f"_bg_original{old_ext}")
            if old != dst and os.path.isfile(old):
                os.remove(old)

        shutil.copy2(src_path, dst)
        return f"usrCfg/_bg_original{ext}"

    def _on_browse_image(self):
        """
        （槽函数）打开系统文件选择器选择背景图片，自动复制到 usrCfg/
        """
        path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", os.path.expanduser("~"),
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if path:
            # 复制到 usrCfg/ 目录，避免原图被移动后失效
            local_path = self._copy_bg_to_usrCfg(path)
            self._bg_image = local_path
            self._bg_image_input.setText(local_path)
            self._save_appearance()
            self._update_preview()

    def _on_clear_image(self):
        """
        （槽函数）清除背景图片路径

        参数:
            （无参数）

        返回:
            None

        做的事:
            1. 清空 self._bg_image
            2. 清空路径输入框
            3. 保存（空字符串 = 不使用背景图片）+ 更新预览 + 通知全局刷新

        用法:
            # 用户点击"清除"按钮
            self._btn_clear_img.clicked.connect(self._on_clear_image)
        """
        self._bg_image = ""
        self._bg_image_input.clear()
        self._save_appearance()
        self._update_preview()

    # ── 预览刷新 ──────────────────────────────────────

    def _update_preview(self):
        """
        （内部方法）根据当前字体/字号/行距/背景色更新预览区域样式

        参数:
            （无参数，从各控件读取当前值）

        返回:
            None

        做的事:
            1. 读取 font_family / font_size / line_spacing / _bg_color 当前值
            2. 设置预览 QFrame 的 CSS 样式（背景色 + 边框 + 内边距）
            3. 设置预览标题 QLabel 的样式（字体 + 字号+4 + 加粗）
            4. 设置预览正文 QLabel 的样式（字体 + 字号 + 行距）

        设计思路:
            预览区标题比正文大 4px 并加粗，模拟真实文档的标题/正文对比效果。
            这样用户调整字号时，能直观看到正文和标题的变化关系。

        用法:
            # 每次外观设置变更后调用
            self._update_preview()
        """
        font_family = self._font_combo.currentFont().family()
        font_size = self._font_size_spin.value()
        line_spacing = self._line_spacing_spin.value()

        # 预览区域的背景色 + 基本样式
        style = (
            f"font-family: '{font_family}'; "
            f"font-size: {font_size}px; "
            f"line-height: {line_spacing}; "
            f"background-color: {self._bg_color}; "
            f"border-radius: 8px; "
            f"padding: 16px;"
        )
        self._preview_frame.setStyleSheet(f"#preview_frame {{ {style} }}")

        # 预览标题: 比正文大 4px + 加粗
        self._preview_title.setStyleSheet(
            f"font-family: '{font_family}'; font-size: {font_size + 4}px; font-weight: bold;"
        )

        # 预览正文: 和正文同字号 + 指定行距
        self._preview_body.setStyleSheet(
            f"font-family: '{font_family}'; font-size: {font_size}px; line-height: {line_spacing};"
        )
