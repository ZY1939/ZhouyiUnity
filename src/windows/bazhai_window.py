"""八字排盘独立窗口"""
from PySide6.QtWidgets import QDialog, QLabel

class BazhaiWindow(QDialog):
    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"八字排盘 - {user.get('name', '') if user else ''}")
        self.resize(800, 600)
        QLabel("八字排盘详情 (待实现)", self)
