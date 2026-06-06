"""
主窗口：从 .ui 加载布局，注入 Tab 页逻辑
Qt Designer 画控件 → Python findChild 找到控件 → 连接信号
"""
import os
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QWidget, QTabWidget
from PySide6.QtCore import QFile

from .tabs.yijing_viewer import YijingViewer
from .tabs.qigua import QiguaTab
from .tabs.bazhai import BazhaiTab
from .tabs.case_manager import CaseManager
from .settings import SettingsTab
from .settings.appearance_manager import apply_appearance
from .settings.config_manager import config_manager
from .utils.statusbar_manager import StatusBarManager


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
        self._settings = SettingsTab(self)

        # 首次启动无配置 → 默认值自动生成；有配置 → 读取并应用
        apply_appearance(self)

        # 状态栏：实时时钟 + 农历 + 真太阳时 + 四柱
        self._statusbar_mgr = StatusBarManager(self.statusBar())

        # ── 记住上次选中的标签页 ──
        tab_widget = self.findChild(QTabWidget, "mainTab")
        if tab_widget:
            # 切换时保存当前选中索引
            tab_widget.currentChanged.connect(self._on_tab_changed)
            # 启动时恢复到上次选中的标签页
            last_idx = config_manager.get("general", "last_tab_index") or 4
            if 0 <= last_idx < tab_widget.count():
                tab_widget.setCurrentIndex(last_idx)

    def _on_tab_changed(self, index):
        """标签页切换 → 保存索引到配置文件"""
        if hasattr(self, "_settings"):  # 初始化期间 _settings 可能还未赋值
            config_manager.set("general", "last_tab_index", value=index)
