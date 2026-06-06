"""
ZhouyiUnity - 周易算命软件
基于 PySide6 的多窗口桌面应用
"""
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from src.main_window import MainWindow


def _setup_fonts():
    """全局字体：苹方 16px，确保 macOS/Windows 都清晰"""
    font = QFont("PingFang SC", 16)
    if not font.exactMatch():
        font = QFont("Microsoft YaHei", 16)
    if not font.exactMatch():
        font = QFont("Noto Sans CJK SC", 16)
    QApplication.setFont(font)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ZhouyiUnity")

    _setup_fonts()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
