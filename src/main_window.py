"""
主窗口：从 .ui 加载布局，注入 Tab 页逻辑
Qt Designer 画控件 → Python findChild 找到控件 → 连接信号
"""
import os
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QWidget
from PySide6.QtCore import QFile

from .tabs.yijing_viewer import YijingViewer
from .tabs.qigua import QiguaTab
from .tabs.bazhai import BazhaiTab
from .tabs.case_manager import CaseManager


_UI_PATH = os.path.join(os.path.dirname(__file__), "..", "ui", "zhouyiUnity.ui")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._load_ui()
        self._wire_tabs()

    def _load_ui(self):
        """加载 .ui 文件，提取布局和属性"""
        loader = QUiLoader()
        ui_file = QFile(_UI_PATH)
        if not ui_file.open(QFile.ReadOnly):
            print(f"WARNING: 无法打开 {_UI_PATH}")
            return

        widget = loader.load(ui_file)
        ui_file.close()

        if widget is None:
            return

        self.resize(widget.size())
        self.setWindowTitle(widget.windowTitle())

        if isinstance(widget, QMainWindow):
            cw = widget.centralWidget()
            if cw:
                cw.setParent(self)
                self.setCentralWidget(cw)
        else:
            self.setCentralWidget(widget)

    def _wire_tabs(self):
        """找到 .ui 里的各个 tab 页，注入 Python 逻辑"""
        self._yijing = YijingViewer(self)
        self._qigua = QiguaTab(self)
        self._bazhai = BazhaiTab(self)
        self._cases = CaseManager(self)
        self.statusBar().showMessage("就绪")
