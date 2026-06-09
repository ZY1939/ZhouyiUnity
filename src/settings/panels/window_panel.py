"""
窗口选项设置面板 — 锁定宽高比、字号联动缩放、窗口大小、禁用拖动调整

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【这个文件做什么】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  提供窗口行为设置界面，用户在此面板中调整：
    1. 锁定窗口宽高比 — 拖动改变大小时保持当前宽高比
    2. 字号联动缩放 — 增大字号时自动按比例放大窗口
    3. 窗口大小预设 — 小/中/大 或自定义宽高
    4. 禁止拖动调整 — 固定窗口大小，禁用 resize 手柄

  所有配置变更自动保存到 usrCfg/UsrCfg.json。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【面板结构（两个 QGroupBox）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. 缩放行为:
     - 锁定窗口宽高比复选框
     - 字号联动缩放复选框 + 缩放倍率微调
     - 禁止拖动调整复选框

  2. 窗口大小:
     - 预设按钮（小/中/大）
     - 自定义宽高 SpinBox

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【与哪些文件联动】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  → config_manager.py    DEFAULT_CONFIG 新增 window 段
  → settings_tab.py       CATEGORIES 注册 WindowPanel
  → main_window.py        resizeEvent 拦截宽高比锁定
  → appearance_manager.py apply_appearance 末尾字号联动缩放
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QSpinBox, QGroupBox, QCheckBox,
    QDoubleSpinBox,
)
from PySide6.QtCore import Qt

from ..config_manager import config_manager, get_project_root

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
QSpinBox, QDoubleSpinBox {{
    padding: 6px 10px;
    border: 1px solid #c0c0c0;
    border-radius: 6px;
    background: white;
    color: #1d1d1f;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: #007aff;
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
QPushButton:checked {{
    background: #007aff;
    color: white;
    border-color: #007aff;
}}
QLabel {{
    background: transparent;
    color: {text_color};
}}
QCheckBox {{
    background: transparent;
    color: {text_color};
    spacing: 8px;
}}
"""

# 窗口默认尺寸（来自 zhouyiUnity.ui 设计尺寸 1024×700，比例 ~1.463）
DEFAULT_SIZE = (1024, 700)
DEFAULT_RATIO = DEFAULT_SIZE[0] / DEFAULT_SIZE[1]  # ≈ 1.463

# 窗口大小预设 — 保持默认比例
_SIZE_BY_WIDTH = {
    "默认": 1024,
    "小": 800,
    "中": 1280,
    "大": 1600,
}
SIZE_PRESETS = {
    label: (w, round(w / DEFAULT_RATIO))
    for label, w in _SIZE_BY_WIDTH.items()
}


class WindowPanel(QWidget):
    """
    窗口选项设置面板

    参数:
        parent (QWidget, 可选): 父 Widget

    用法:
        from .panels.window_panel import WindowPanel
        panel = WindowPanel()
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load_config()
        self._connect_signals()

    # ── UI 构建 ───────────────────────────────────────

    def _init_ui(self):
        """
        构建面板的完整 UI 布局

        UI 结构（从上到下）:
            1. "缩放行为" GroupBox:
               - 锁定窗口宽高比 QCheckBox
               - 字号联动缩放 QCheckBox + 缩放倍率 QDoubleSpinBox
               - 禁止拖动调整 QCheckBox

            2. "窗口大小" GroupBox:
               - 预设按钮行（小/中/大）
               - 自定义宽高 SpinBox
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(20)

        # ── 缩放行为 ──
        behavior_group = QGroupBox("缩放行为")
        behavior_layout = QVBoxLayout(behavior_group)
        behavior_layout.setContentsMargins(12, 20, 12, 12)
        behavior_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        behavior_layout.setSpacing(12)

        # 复选框左对齐样式
        cb_align = "QCheckBox { margin-left: 0px; padding-left: 0px; }"

        # 锁定窗口宽高比
        self._lock_ratio_cb = QCheckBox("拖动窗口时自动保持当前宽高比")
        self._lock_ratio_cb.setStyleSheet(cb_align)
        behavior_layout.addWidget(self._lock_ratio_cb)

        # 字号联动缩放：复选框
        self._auto_resize_cb = QCheckBox("增大字号后自动按比例缩放窗口")
        self._auto_resize_cb.setStyleSheet(cb_align)
        behavior_layout.addWidget(self._auto_resize_cb)

        # 缩放倍率（缩进一行，右边留 stretch）
        scale_row = QHBoxLayout()
        scale_row.setContentsMargins(20, 0, 0, 0)
        scale_row.setSpacing(8)
        scale_row.addWidget(QLabel("缩放倍率："))
        self._scale_factor_spin = QDoubleSpinBox()
        self._scale_factor_spin.setRange(0.5, 2.0)
        self._scale_factor_spin.setSingleStep(0.1)
        self._scale_factor_spin.setValue(1.0)
        self._scale_factor_spin.setDecimals(1)
        self._scale_factor_spin.setFixedWidth(70)
        self._scale_factor_spin.setToolTip("1.0=字号变化比例即窗口缩放比例\n"
                                           ">1.0=更激进地缩放，<1.0=更保守地缩放")
        scale_row.addWidget(self._scale_factor_spin)
        scale_row.addStretch()
        behavior_layout.addLayout(scale_row)

        # 禁止拖动调整
        self._no_resize_cb = QCheckBox("禁止拖动窗口边缘调整大小")
        self._no_resize_cb.setStyleSheet(cb_align)
        behavior_layout.addWidget(self._no_resize_cb)

        root.addWidget(behavior_group)

        # ── 窗口大小 ──
        size_group = QGroupBox("窗口大小")
        size_layout = QVBoxLayout(size_group)
        size_layout.setSpacing(12)

        # 预设按钮行
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        preset_row.addWidget(QLabel("预设尺寸："))
        self._preset_buttons = {}
        for label, (pw, ph) in SIZE_PRESETS.items():
            btn = QPushButton(f"{label}\n{pw}×{ph}")
            btn.setCheckable(False)
            btn.setStyleSheet("QPushButton { padding: 4px 2px; min-width: 80px; }")
            btn.clicked.connect(lambda checked, w=pw, h=ph: self._apply_preset(w, h))
            self._preset_buttons[label] = btn
            preset_row.addWidget(btn)
        preset_row.addStretch()
        size_layout.addLayout(preset_row)

        # 自定义宽高
        custom_row = QHBoxLayout()
        custom_row.setSpacing(8)
        custom_row.addWidget(QLabel("自定义："))
        custom_row.addWidget(QLabel("宽"))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(640, 5120)
        self._width_spin.setSingleStep(10)
        self._width_spin.setFixedWidth(90)
        custom_row.addWidget(self._width_spin)
        custom_row.addWidget(QLabel("×"))
        custom_row.addWidget(QLabel("高"))
        self._height_spin = QSpinBox()
        self._height_spin.setRange(480, 3200)
        self._height_spin.setSingleStep(10)
        self._height_spin.setFixedWidth(90)
        custom_row.addWidget(self._height_spin)

        self._keep_ratio_cb = QCheckBox("保持宽高比")
        self._keep_ratio_cb.setChecked(True)
        self._keep_ratio_cb.setStyleSheet("QCheckBox { spacing: 6px; } QCheckBox::indicator { width: 18px; height: 18px; }")
        custom_row.addWidget(self._keep_ratio_cb)
        custom_row.addSpacing(16)

        self._btn_apply = QPushButton("应用")
        self._btn_apply.clicked.connect(self._on_apply_custom_size)
        custom_row.addWidget(self._btn_apply)
        custom_row.addStretch()
        size_layout.addLayout(custom_row)

        root.addWidget(size_group)
        root.addStretch()
        self.setStyleSheet(PANEL_STYLE.format(text_color="#1d1d1f"))

    def refresh_text_color(self, text_color: str):
        """
        根据背景亮度更新面板文字颜色（由 settings_tab 调用）

        参数:
            text_color (str): 计算后的文字颜色，如 "#ffffff" 或 "#1d1d1f"
        """
        self.setStyleSheet(PANEL_STYLE.format(text_color=text_color))

    # ── 配置加载/保存 ─────────────────────────────────

    def _load_config(self):
        """从 usrCfg 加载窗口配置并填充控件"""
        cfg = config_manager.get("window") or {}
        self._lock_ratio_cb.setChecked(cfg.get("lock_aspect_ratio", True))
        self._auto_resize_cb.setChecked(cfg.get("auto_resize_with_font", False))
        self._scale_factor_spin.setValue(cfg.get("auto_scale_factor", 1.0))
        self._no_resize_cb.setChecked(cfg.get("no_resize", False))

        # 加载上次保存的窗口大小
        saved_w = cfg.get("window_width", 0)
        saved_h = cfg.get("window_height", 0)
        # 如果没有保存值，使用当前主窗口大小
        if saved_w <= 0 or saved_h <= 0:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app and app.activeWindow():
                saved_w = app.activeWindow().width()
                saved_h = app.activeWindow().height()
            else:
                saved_w, saved_h = DEFAULT_SIZE
        self._width_spin.setValue(saved_w)
        self._height_spin.setValue(saved_h)
        self._wh_ratio = saved_w / max(saved_h, 1)

    def _save(self):
        """保存所有窗口配置到 usrCfg"""
        config_manager.set("window", "lock_aspect_ratio", value=self._lock_ratio_cb.isChecked())
        config_manager.set("window", "auto_resize_with_font", value=self._auto_resize_cb.isChecked())
        config_manager.set("window", "auto_scale_factor", value=self._scale_factor_spin.value())
        config_manager.set("window", "no_resize", value=self._no_resize_cb.isChecked())

    def _connect_signals(self):
        """连接各控件变更信号"""
        self._lock_ratio_cb.toggled.connect(self._save)
        self._auto_resize_cb.toggled.connect(self._save)
        self._scale_factor_spin.valueChanged.connect(self._save)
        self._no_resize_cb.toggled.connect(self._on_no_resize_toggled)
        self._width_spin.valueChanged.connect(self._on_width_changed)
        self._height_spin.valueChanged.connect(self._on_height_changed)

    # ── 槽函数 ────────────────────────────────────────

    def _apply_preset(self, width: int, height: int):
        """应用预设窗口大小"""
        self._width_spin.setValue(width)
        self._height_spin.setValue(height)
        self._resize_main_window(width, height)

    def _on_apply_custom_size(self):
        """应用自定义窗口大小"""
        w = self._width_spin.value()
        h = self._height_spin.value()
        self._resize_main_window(w, h)
        # 保存自定义大小
        config_manager.set("window", "window_width", value=w)
        config_manager.set("window", "window_height", value=h)

    def _on_no_resize_toggled(self, checked: bool):
        """禁止拖动调整 → 固定窗口大小"""
        self._save()
        self._resize_main_window(self._width_spin.value(), self._height_spin.value())

    def _on_width_changed(self, w: int):
        """宽度变更 → 若保持宽高比，联动更新高度"""
        if self._keep_ratio_cb.isChecked() and not getattr(self, "_syncing_wh", False):
            ratio = getattr(self, "_wh_ratio", DEFAULT_RATIO)
            self._syncing_wh = True
            self._height_spin.setValue(round(w / ratio))
            self._syncing_wh = False
            self._wh_ratio = w / max(self._height_spin.value(), 1)

    def _on_height_changed(self, h: int):
        """高度变更 → 若保持宽高比，联动更新宽度"""
        if self._keep_ratio_cb.isChecked() and not getattr(self, "_syncing_wh", False):
            ratio = getattr(self, "_wh_ratio", DEFAULT_RATIO)
            self._syncing_wh = True
            self._width_spin.setValue(round(h * ratio))
            self._syncing_wh = False
            self._wh_ratio = max(self._width_spin.value(), 1) / h

    def _resize_main_window(self, width: int, height: int):
        """调整主窗口大小并保存到配置"""
        from PySide6.QtWidgets import QApplication
        config_manager.set("window", "window_width", value=width)
        config_manager.set("window", "window_height", value=height)
        app = QApplication.instance()
        if app:
            win = app.activeWindow()
            if win:
                if self._no_resize_cb.isChecked():
                    win.setFixedSize(width, height)
                else:
                    win.setMinimumSize(0, 0)
                    win.setMaximumSize(16777215, 16777215)
                    win.resize(width, height)

    # ── 公开方法（供 appearance_manager 联动）──────────

    def on_font_size_changed(self, old_size: int, new_size: int):
        """
        字号变更后，如果启用联动缩放，按比例缩放窗口

        参数:
            old_size (int): 旧字号（px）
            new_size (int): 新字号（px）

        缩放公式:
            ratio = new_size / old_size
            scale = 1 + (ratio - 1) * auto_scale_factor
            new_window_w = current_w * scale
            new_window_h = current_h * scale
        """
        if not self._auto_resize_cb.isChecked():
            return
        if old_size <= 0 or new_size <= 0 or old_size == new_size:
            return

        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if not app:
            return
        win = app.activeWindow()
        if not win:
            return

        ratio = new_size / old_size
        scale = 1.0 + (ratio - 1.0) * self._scale_factor_spin.value()
        new_w = int(win.width() * scale)
        new_h = int(win.height() * scale)
        print(f"[窗口缩放] 字号 {old_size}→{new_size}, 比例×{ratio:.2f}, "
              f"倍率×{self._scale_factor_spin.value():.1f}, "
              f"最终缩放×{scale:.2f}, 窗口 {win.width()}×{win.height()}→{new_w}×{new_h}")
        win.resize(new_w, new_h)
        config_manager.set("window", "window_width", value=new_w)
        config_manager.set("window", "window_height", value=new_h)
