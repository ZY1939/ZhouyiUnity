"""
方法标签栏 — dot + 标签行公共组件

供起卦面板（divination_panel）和算卦面板（suangua_panel）共用。

特性：
  - dot（DotButton）+ 标签（QPushButton）水平排列
  - 选中标签：bold + text_color；未选中：normal + 自适应暗淡色
  - 支持自定义标签构建器（如 qigua 的"金钱/蓍草"双按钮）
  - 支持背景色设置（默认 transparent）
  - 提供 debug_positions() 返回各元素渲染坐标

用法：
    bar = MethodLabelBar(methods=[{"key": "meihua", "label": "梅花"}, ...])
    bar.method_selected.connect(on_method_selected)
    bar.set_current_method("meihua")

    # 刷新
    bar.refresh_font_size(17)
    bar.refresh_text_color("#ffffff")

    # 调试
    for info in bar.debug_positions():
        print(info)
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup, QLabel
from PySide6.QtCore import Signal, Qt, QPoint, QRect
from PySide6.QtGui import QFont, QFontMetrics

from .dot_button import DotButton


class MethodLabelBar(QWidget):
    """
    方法选择标签栏

    Signals:
        method_selected(key: str) — 方法被选中时发射

    调试：
        debug_positions() → list[dict]  返回每个元素的渲染位置和尺寸
    """

    method_selected = Signal(str)

    def __init__(self, methods: list[dict], font_size: int = 16,
                 text_color: str = "#1d1d1f", bg_color: str = "transparent",
                 custom_builders: dict | None = None, spacing: int = 0, parent=None):
        """
        Args:
            methods:         [{"key": "meihua", "label": "梅花"}, ...]
            font_size:       初始字号(pt)
            text_color:      文字颜色（选中/active 时使用）
            bg_color:        背景色（默认 "transparent" = 跟随父级背景）
            custom_builders: {index: callable} 自定义标签构建器。
                             callable(font_size, text_color) → QWidget
                             返回的 widget 替代默认 QPushButton 标签。
            spacing:         方法标签之间的间距(px)，默认 0
        """
        super().__init__(parent)
        self._methods = methods
        self._font_size = font_size
        self._text_color = text_color
        self._bg_color = bg_color
        self._custom_builders = custom_builders or {}
        self._spacing = spacing
        self._current_key: str = methods[0]["key"] if methods else ""

        self._dots: list[DotButton] = []
        self._labels: list[QPushButton | QWidget] = []
        self._disabled_indices: set[int] = set()  # 被禁用的标签索引
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        self._build()
        self._update_bg()

    # ═══════════════════════════════════════════════════════════
    #  构建
    # ═══════════════════════════════════════════════════════════

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        for i, m in enumerate(self._methods):
            dot = DotButton()
            self._btn_group.addButton(dot, i)
            self._dots.append(dot)
            layout.addWidget(dot)

            builder = self._custom_builders.get(i)
            if builder:
                lbl = builder(self._font_size, self._text_color)
            else:
                lbl = QPushButton(m["label"])
                lbl.setFlat(True)
                lbl.setCursor(Qt.CursorShape.PointingHandCursor)
                lbl.clicked.connect(lambda checked, idx=i: self._dots[idx].click())
            self._labels.append(lbl)
            layout.addWidget(lbl)

            if i < len(self._methods) - 1:
                layout.addSpacing(self._spacing)

        layout.addStretch()

        self._btn_group.buttonClicked.connect(self._on_dot_clicked)

    def _on_dot_clicked(self, btn):
        idx = self._btn_group.id(btn)
        key = self._methods[idx]["key"]
        self._current_key = key
        self.update_label_styles()
        self.method_selected.emit(key)

    # ═══════════════════════════════════════════════════════════
    #  方法访问
    # ═══════════════════════════════════════════════════════════

    def current_method(self) -> str:
        return self._current_key

    def set_current_method(self, key: str):
        """程序化设置选中方法（更新 dot + 标签样式，不发射信号）"""
        for i, m in enumerate(self._methods):
            if m["key"] == key:
                self._dots[i].setChecked(True)
                self._current_key = key
                self.update_label_styles()
                return

    def method_keys(self) -> list[str]:
        return [m["key"] for m in self._methods]

    # ═══════════════════════════════════════════════════════════
    #  样式
    # ═══════════════════════════════════════════════════════════

    def dim_color(self) -> str:
        """text_color 与 50% 灰色混合，适配深浅背景"""
        tc = self._text_color.lstrip("#")
        r, g, b = int(tc[0:2], 16), int(tc[2:4], 16), int(tc[4:6], 16)
        dim = lambda c: (c + 128) // 2
        return f"#{dim(r):02x}{dim(g):02x}{dim(b):02x}"

    def set_label_enabled(self, index: int, enabled: bool):
        """
        启用/禁用单个标签（如多动爻时梅花灰色显示）

        Args:
            index:   标签索引
            enabled: True=正常, False=灰色禁用
        """
        if enabled:
            self._disabled_indices.discard(index)
        else:
            self._disabled_indices.add(index)
        self.update_label_styles()

    def update_label_styles(self):
        """更新标签样式：选中 → bold+text_color，未选中 → normal+dim_color，禁用 → 灰色"""
        for i, lbl in enumerate(self._labels):
            if not isinstance(lbl, QPushButton):
                continue
            disabled = i in self._disabled_indices
            is_active = self._methods[i]["key"] == self._current_key and not disabled
            if disabled:
                lbl.setStyleSheet(f"""
                    QPushButton {{
                        color: #888888; border: none; background: transparent;
                        font-size: {self._font_size}px; font-weight: normal;
                    }}
                """)
            else:
                lbl.setStyleSheet(f"""
                    QPushButton {{
                        color: {self._text_color if is_active else self.dim_color()};
                        border: none; background: transparent;
                        font-size: {self._font_size}px;
                        font-weight: {'bold' if is_active else 'normal'};
                    }}
                    QPushButton:hover {{ color: {self._text_color}; }}
                """)

    def _update_bg(self):
        self.setStyleSheet(f"MethodLabelBar {{ background: {self._bg_color}; }}")

    def set_bg_color(self, bg_color: str):
        self._bg_color = bg_color
        self._update_bg()

    # ═══════════════════════════════════════════════════════════
    #  刷新
    # ═══════════════════════════════════════════════════════════

    def refresh_font_size(self, font_size: int):
        self._font_size = font_size
        self.update_label_styles()
        # 刷新自定义构建器的字体（如果有的话，子类重载）
        for i, builder in self._custom_builders.items():
            if i < len(self._labels):
                self._on_refresh_custom_label(i, font_size, self._text_color)

    def refresh_text_color(self, text_color: str):
        self._text_color = text_color
        self.update_label_styles()
        for i, builder in self._custom_builders.items():
            if i < len(self._labels):
                self._on_refresh_custom_label(i, self._font_size, text_color)

    def _on_refresh_custom_label(self, index: int, font_size: int, text_color: str):
        """子类可重载以处理自定义标签的刷新"""

    # ═══════════════════════════════════════════════════════════
    #  访问器（供父级布局计算使用）
    # ═══════════════════════════════════════════════════════════

    def dots(self) -> list[DotButton]:
        return self._dots

    def labels(self) -> list:
        return self._labels

    def button_group(self) -> QButtonGroup:
        return self._btn_group

    # ═══════════════════════════════════════════════════════════
    #  调试
    # ═══════════════════════════════════════════════════════════

    def debug_positions(self) -> list[dict]:
        """
        返回每个元素的渲染位置信息，供调试对齐问题。

        Returns:
            [{ "type": "dot"|"label", "index": 0, "label": "梅花",
               "x": 100, "y": 20, "w": 14, "h": 28,
               "global_x": 250, "global_y": 120 }, ...]
        """
        result = []
        bar_global = self.mapToGlobal(QPoint(0, 0))
        for i, dot in enumerate(self._dots):
            r = dot.geometry()
            g = dot.mapToGlobal(QPoint(0, 0))
            result.append({
                "type": "dot", "index": i,
                "label": self._methods[i]["label"],
                "x": r.x(), "y": r.y(), "w": r.width(), "h": r.height(),
                "global_x": g.x(), "global_y": g.y(),
                "bar_global_x": bar_global.x(), "bar_global_y": bar_global.y(),
            })
        for i, lbl in enumerate(self._labels):
            r = lbl.geometry()
            g = lbl.mapToGlobal(QPoint(0, 0))
            mid_y = r.y() + r.height() // 2
            result.append({
                "type": "label", "index": i,
                "label": self._methods[i]["label"],
                "x": r.x(), "y": r.y(), "w": r.width(), "h": r.height(),
                "mid_y": mid_y,
                "global_x": g.x(), "global_y": g.y(),
                "bar_global_x": bar_global.x(), "bar_global_y": bar_global.y(),
                "font_size": self._font_size,
            })
        return result
