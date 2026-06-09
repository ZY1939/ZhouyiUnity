"""
圆点选择按钮 — 选中实心蓝色，未选中空心灰色

用于起卦/算卦方法选择器（手工●报数●金钱●蓍草 / 梅花●六爻）。
配合 QButtonGroup 实现互斥单选，一次只能选中一个方法。
"""
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt


class DotButton(QPushButton):
    """
    圆点选择按钮 — 选中实心蓝色，未选中空心灰色

    类属性：
      _COLOR: 选中时的蓝色值 (#007aff)，hover 时也使用此颜色
    """

    _COLOR = "#007aff"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(14, 14)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self._on_toggled)
        self._update_style(False)

    def _on_toggled(self, checked: bool):
        self._update_style(checked)

    def _update_style(self, checked: bool):
        bg = self._COLOR if checked else "transparent"
        border = self._COLOR if checked else "#c7c7cc"
        self.setStyleSheet(f"""
            QPushButton {{ background: {bg}; border: 2px solid {border}; border-radius: 7px; }}
            QPushButton:hover {{ border-color: {self._COLOR}; }}
        """)
