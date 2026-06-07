"""
易经与起卦 Tab — 集成易经查看器和起卦功能

在 tab_yijing 中注入 QiguaPanel（起卦面板），
后续可扩展易经查看器部分。
"""
from PySide6.QtWidgets import QVBoxLayout, QWidget


class YijingViewer:
    """易经与起卦 Tab — 找到 tab_yijing 布局并注入 QiguaPanel"""

    def __init__(self, main_window):
        self._main = main_window

        tab = main_window.findChild(QWidget, "tab_yijing")
        if tab is None:
            return

        layout = tab.layout()
        if layout is None:
            return

        from ..qigua import QiguaPanel

        self._qigua_panel = QiguaPanel()
        layout.addWidget(self._qigua_panel)

    def refresh_font_size(self, font_size: int):
        """全局字体变更时，转发给起卦面板刷新行高/间距"""
        if hasattr(self, "_qigua_panel"):
            self._qigua_panel.refresh_font_size(font_size)

    def refresh_text_color(self, text_color: str):
        """背景色变更时，转发给起卦面板刷新文字颜色（深底白字/浅底黑字）"""
        if hasattr(self, "_qigua_panel"):
            self._qigua_panel.refresh_text_color(text_color)
