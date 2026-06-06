"""起卦功能 - 手动/随机起卦"""
from PySide6.QtWidgets import QPushButton, QLabel


class QiguaTab:
    """找到 .ui 里 tab_qigua 页的控件，连接信号"""

    def __init__(self, main_window):
        self._btn = main_window.findChild(QPushButton, "btn_random_gua")
        self._label = main_window.findChild(QLabel, "label_gua_result")

        if self._btn:
            self._btn.clicked.connect(self._on_click)

    def _on_click(self):
        print("[起卦] 按钮被点击了")
        if self._label:
            self._label.setText("乾为天 ☰☰ (示例)")
