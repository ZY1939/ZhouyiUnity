"""
主窗口：从 .ui 加载布局，注入 Tab 页逻辑
Qt Designer 画控件 → Python findChild 找到控件 → 连接信号
"""
import os
import platform
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (QMainWindow, QWidget, QTabWidget, QToolBar,
                                QTabBar, QSizePolicy)
from PySide6.QtCore import QFile, Qt, QTimer

from .tabs.yijing_viewer import YijingViewer
from .tabs.bazhai import BazhaiTab
from .tabs.case_manager import CaseManager
from .settings import SettingsTab
from .settings.appearance_manager import apply_appearance
from .settings.config_manager import config_manager
from .utils.statusbar_manager import StatusBarManager


_UI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ui", "zhouyiUnity.ui"))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._load_ui()
        self._wire_tabs()
        self._restore_window_size()

    def _restore_window_size(self):
        """从 UsrCfg 恢复窗口大小（首次运行则保存当前默认尺寸）"""
        wcfg = config_manager.get("window") or {}
        saved_w = wcfg.get("window_width", 0)
        saved_h = wcfg.get("window_height", 0)

        if saved_w > 0 and saved_h > 0:
            self.resize(saved_w, saved_h)
            print(f"[主窗口] ✓ 恢复窗口大小: {saved_w}×{saved_h}")
        else:
            # 首次运行：把当前尺寸写入配置
            config_manager.set("window", "window_width", value=self.width())
            config_manager.set("window", "window_height", value=self.height())
            print(f"[主窗口] ✓ 首次运行，保存默认窗口大小: {self.width()}×{self.height()}")

        # 应用 no_resize 设置
        if wcfg.get("no_resize", False):
            self._apply_fixed_size()

    def _save_window_size(self):
        """保存当前窗口大小到 UsrCfg（仅在非 fixed 模式下）"""
        wcfg = config_manager.get("window") or {}
        if not wcfg.get("no_resize", False):
            config_manager.set("window", "window_width", value=self.width())
            config_manager.set("window", "window_height", value=self.height())

    def _apply_fixed_size(self):
        """根据配置锁定或解锁窗口大小"""
        wcfg = config_manager.get("window") or {}
        if wcfg.get("no_resize", False):
            w = wcfg.get("window_width", self.width())
            h = wcfg.get("window_height", self.height())
            self.setFixedSize(w, h)
        else:
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)

    def resizeEvent(self, event):
        """窗口大小改变时：锁定宽高比 + 保存尺寸 + 防抖背景渲染"""
        # ── 锁定宽高比 ──
        window_cfg = config_manager.get("window") or {}
        if window_cfg.get("lock_aspect_ratio", False) and not getattr(self, "_locking_ratio", False):
            w = event.size().width()
            h = event.size().height()
            old = event.oldSize()
            if old.width() > 0 and old.height() > 0:
                ratio = old.width() / old.height()
                if abs(w - old.width()) >= abs(h - old.height()):
                    h = int(w / ratio)
                else:
                    w = int(h * ratio)
                self._locking_ratio = True
                self.resize(w, h)
                self._locking_ratio = False
                super().resizeEvent(event)
                return

        super().resizeEvent(event)
        if getattr(self, "_applying_appearance", False):
            return

        # ── 保存窗口大小（300ms 防抖）──
        if hasattr(self, "_size_save_timer"):
            self._size_save_timer.start()

        if hasattr(self, "_resize_timer"):
            if getattr(self, "_initial_appearance_applied", False):
                self._resize_timer.start()
            else:
                self._resize_timer.stop()
                apply_appearance(self)
                self._initial_appearance_applied = True

    def _load_ui(self):
        """加载 .ui 文件，提取布局和属性"""
        print(f"[主窗口] .ui 路径: {_UI_PATH}")
        if not os.path.exists(_UI_PATH):
            _ui_dir = os.path.dirname(_UI_PATH)
            _nearby = os.listdir(_ui_dir) if os.path.isdir(_ui_dir) else []
            print(f"[主窗口] ❌ .ui 文件不存在! ui/ 目录内容: {_nearby}")
            print(f"[主窗口]    当前工作目录: {os.getcwd()}")
            print(f"[主窗口]    __file__: {__file__}")
            return

        loader = QUiLoader()
        ui_file = QFile(_UI_PATH)
        if not ui_file.open(QFile.ReadOnly):
            print(f"[主窗口] ❌ 无法打开 {_UI_PATH}")
            return

        widget = loader.load(ui_file)
        ui_file.close()

        if widget is None:
            print("[主窗口] ❌ QUiLoader 加载 .ui 文件失败")
            return

        print("[主窗口] ✓ .ui 文件加载成功")

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
        self._bazhai = BazhaiTab(self)
        self._cases = CaseManager(self)
        self._settings = SettingsTab(self)

        # 窗口大小改变时重新渲染背景图片（300ms 防抖）
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(300)
        self._resize_timer.timeout.connect(lambda: apply_appearance(self))

        # 窗口大小改变时保存到配置（500ms 防抖，比背景渲染更慢）
        self._size_save_timer = QTimer(self)
        self._size_save_timer.setSingleShot(True)
        self._size_save_timer.setInterval(500)
        self._size_save_timer.timeout.connect(self._save_window_size)

        # 状态栏：实时时钟 + 农历 + 真太阳时 + 四柱
        self._statusbar_mgr = StatusBarManager(self.statusBar())

        tab_widget = self.findChild(QTabWidget, "mainTab")
        if tab_widget:
            tab_widget.setDocumentMode(True)  # 去掉 pane 默认内边距

            # macOS：把 tab bar 移到窗口标题栏区域，和红绿灯按钮同行
            if platform.system() == "Darwin":
                self._setup_unified_tabs(tab_widget)

            # 切换时保存当前选中索引
            tab_widget.currentChanged.connect(self._on_tab_changed)
            # 启动时恢复到上次选中的标签页
            last_idx = config_manager.get("general", "last_tab_index")
            if last_idx is None:
                last_idx = 0  # 默认显示「易经与起卦」
            if 0 <= last_idx < tab_widget.count():
                tab_widget.setCurrentIndex(last_idx)

    def _setup_unified_tabs(self, tab_widget: QTabWidget):
        """macOS 原生统一标题栏：把 tab bar 移入 toolbar，居中显示"""
        self.setUnifiedTitleAndToolBarOnMac(True)

        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        toolbar.setObjectName("unifiedToolbar")

        # 隐藏 QTabWidget 原生 tab bar
        tab_widget.tabBar().hide()

        # 在 toolbar 里用弹性空间实现居中
        left_spacer = QWidget()
        left_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        right_spacer = QWidget()
        right_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(left_spacer)

        self._toolbar_tabs = QTabBar()
        self._toolbar_tabs.setExpanding(False)
        self._toolbar_tabs.setDrawBase(False)
        self._toolbar_tabs.setObjectName("unifiedTabBar")
        for i in range(tab_widget.count()):
            self._toolbar_tabs.addTab(tab_widget.tabText(i))

        self._toolbar_tabs.currentChanged.connect(tab_widget.setCurrentIndex)
        tab_widget.currentChanged.connect(self._toolbar_tabs.setCurrentIndex)

        toolbar.addWidget(self._toolbar_tabs)
        toolbar.addWidget(right_spacer)

        self.addToolBar(toolbar)

    def _on_tab_changed(self, index):
        """标签页切换 → 保存索引到配置文件"""
        if hasattr(self, "_settings"):  # 初始化期间 _settings 可能还未赋值
            config_manager.set("general", "last_tab_index", value=index)
