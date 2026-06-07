"""
真太阳时设置面板 — 定位（启动自动定位 / 城市选择 / 手动经纬度）+ 启用开关

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【这个文件做什么】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  提供"真太阳时"的完整设置界面。真太阳时是根据当地经度校正后的"日晷时间"，
  与我们日常使用的北京时间（东八区标准时）不同。例如：
    - 北京（经度 116.4°）的真太阳时约比北京时间慢 14 分钟
    - 乌鲁木齐（经度 87.6°）的真太阳时约比北京时间慢约 2 小时

  用户在此面板中可以：
    1. 设置当前所在地的经纬度（启动自动定位 / 城市选择 / 手动输入）
    2. 开关真太阳时功能
    3. 选择在哪些功能中使用真太阳时（排八字、状态栏显示）

  所有配置变更即时保存到 usrCfg 并在控制台打印日志。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【启动自动定位】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  勾选"启动时自动定位"后，每次打开设置面板时自动通过 ip-api.com 获取
  当前 IP 的地理位置。如果无网络连接（3 秒超时），自动降级为默认位置
  "浙江省 杭州市"（经纬度 120.2, 30.25，取自内置城市数据库）。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【面板结构（两个 QGroupBox）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. "定位" GroupBox:
     - "启动时自动定位" 复选框（默认勾选）
     - 当前位置蓝色标签显示（城市名）
     - "刷新定位" + "选择城市" 按钮
     - 经度/纬度 QDoubleSpinBox（同一行对齐）+ "手动编辑经纬度" 复选框

  2. "真太阳时" GroupBox:
     - 主开关：是否启用真太阳时
     - "排八字中使用" 子开关（仅主开关打开时可操作）
     - "状态栏中显示" 子开关（仅主开关打开时可操作）
"""
import requests
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QCheckBox, QPushButton,
    QGroupBox, QDoubleSpinBox, QApplication,
)

from ..config_manager import config_manager
from .city_picker_dialog import CityPickerDialog

# ── 无网络时的默认位置：浙江省 杭州市 ──────────────
FALLBACK_CITY = "浙江省 杭州市"
FALLBACK_LON = 120.2
FALLBACK_LAT = 30.25

PANEL_STYLE = """
QWidget {{ background: transparent; }}
QGroupBox {{ background: transparent; font-weight: bold; border: 1px solid #dcdcdc; border-radius: 8px; margin-top: 12px; padding-top: 16px; color: {text_color}; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {text_color}; }}
QLineEdit, QDoubleSpinBox {{ padding: 6px 10px; border: 1px solid #c0c0c0; border-radius: 6px; background: white; color: #1d1d1f; }}
QCheckBox {{ background: transparent; color: {text_color}; spacing: 8px; }}
QPushButton {{ padding: 6px 18px; border-radius: 6px; border: 1px solid #c0c0c0; background: #f5f5f5; color: #1d1d1f; }}
QPushButton:hover {{ background: #e8e8e8; }}
QLabel {{ background: transparent; color: {text_color}; }}
QLabel#city_display {{ font-size: 15px; font-weight: bold; color: #007aff; padding: 4px 0; }}
"""


def _check_network() -> bool:
    """
    检测网络是否可用（尝试连接 ip-api.com）

    参数:
        （无参数）

    返回:
        bool: True = 网络可用, False = 无网络

    原理:
        向 ip-api.com 发起 GET 请求（3 秒超时），绕过系统代理。
        如果成功返回 200，说明网络畅通。

    用法:
        >>> if _check_network():
        >>>     do_auto_locate()
        >>> else:
        >>>     use_fallback()
    """
    try:
        session = requests.Session()
        session.trust_env = False
        resp = session.get("http://ip-api.com/json/", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


class SolarTimePanel(QWidget):
    """
    真太阳时设置面板 — 定位 + 开关一体化

    参数:
        parent (QWidget, 可选): 父 Widget

    用法:
        # 在 settings_tab.py 中创建：
        from .panels.solar_time_panel import SolarTimePanel
        solar_panel = SolarTimePanel()
    """

    def __init__(self, parent=None):
        """
        构造 SolarTimePanel 实例

        参数:
            parent (QWidget, 可选): 父 Widget

        做的事:
            1. 调用 _init_ui() 构建界面
            2. 调用 _load_config() 从 usrCfg 加载已有配置
            3. 调用 _connect_signals() 绑定控件变更信号
            4. 如果"启动时自动定位"已勾选 → 延迟 100ms 后触发自动定位
               （延迟是为了让 UI 先渲染出来，用户能看到"定位中..."状态）
        """
        super().__init__(parent)
        self._init_ui()
        self._load_config()
        self._connect_signals()
        # 启动时自动定位（延迟 100ms 让 UI 先渲染）
        if self._cb_auto_startup.isChecked():
            QTimer.singleShot(100, self._on_auto_locate)

    # ── UI 构建 ───────────────────────────────────────

    def _init_ui(self):
        """
        （内部方法）构建面板的完整 UI 布局

        参数:
            （无参数）

        返回:
            None（直接设置 self 的布局和子控件）

        UI 结构（从上到下的两个 QGroupBox）:
            1. "定位" GroupBox:
               - "启动时自动定位" QCheckBox
               - 当前位置显示行: "当前位置：" QLabel + 城市名 QLabel（蓝色加粗）
               - 操作按钮行: "刷新定位" + "选择城市"
               - 经纬度行: 经度 QDoubleSpinBox + 纬度 QDoubleSpinBox + "手动编辑经纬度" QCheckBox

            2. "真太阳时" GroupBox:
               - 主开关 QCheckBox: "启用真太阳时"
               - 子开关 QCheckBox: "排八字中使用"
               - 子开关 QCheckBox: "状态栏中显示"
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(20)

        # ── 定位 ──
        loc_group = QGroupBox("定位")
        loc_layout = QFormLayout(loc_group)
        loc_layout.setSpacing(12)

        # 启动时自动定位复选框（默认勾选）
        self._cb_auto_startup = QCheckBox("启动时自动定位（通过IP获取）")
        loc_layout.addRow("", self._cb_auto_startup)

        # 当前位置显示行
        city_header = QHBoxLayout()
        self._city_label = QLabel("当前位置：")
        city_header.addWidget(self._city_label)
        self._city_display = QLabel("")
        self._city_display.setObjectName("city_display")  # CSS 蓝色加粗样式
        city_header.addWidget(self._city_display, 1)
        loc_layout.addRow("", city_header)

        # 操作按钮行
        btn_row = QHBoxLayout()
        self._btn_locate = QPushButton("刷新定位")
        self._btn_locate.clicked.connect(self._on_auto_locate)
        btn_row.addWidget(self._btn_locate)

        self._btn_pick_city = QPushButton("选择城市")
        self._btn_pick_city.clicked.connect(self._on_pick_city)
        btn_row.addWidget(self._btn_pick_city)
        btn_row.addStretch()
        loc_layout.addRow("", btn_row)

        # 经纬度行（经度 + 纬度 + 手动编辑复选框，同一行对齐）
        lonlat_row = QHBoxLayout()
        lonlat_row.setSpacing(8)

        self._lon_input = QDoubleSpinBox()
        self._lon_input.setRange(-180, 180)
        self._lon_input.setDecimals(4)
        self._lon_input.setSuffix(" °")
        self._lon_input.setFixedWidth(140)
        lonlat_row.addWidget(QLabel("经度："))
        lonlat_row.addWidget(self._lon_input)

        self._lat_input = QDoubleSpinBox()
        self._lat_input.setRange(-90, 90)
        self._lat_input.setDecimals(4)
        self._lat_input.setSuffix(" °")
        self._lat_input.setFixedWidth(140)
        lonlat_row.addWidget(QLabel("纬度："))
        lonlat_row.addWidget(self._lat_input)

        self._cb_manual = QCheckBox("手动编辑经纬度")
        lonlat_row.addWidget(self._cb_manual)
        lonlat_row.addStretch()
        loc_layout.addRow("", lonlat_row)

        root.addWidget(loc_group)

        # ── 启用开关 ──
        enable_group = QGroupBox("真太阳时")
        enable_layout = QVBoxLayout(enable_group)
        enable_layout.setSpacing(10)

        self._cb_master = QCheckBox("启用真太阳时")
        enable_layout.addWidget(self._cb_master)

        self._cb_bazi = QCheckBox("排八字中使用")
        self._cb_bazi.setEnabled(False)  # 初始禁用，打开主开关后才可操作
        enable_layout.addWidget(self._cb_bazi)

        self._cb_statusbar = QCheckBox("状态栏中显示")
        self._cb_statusbar.setEnabled(False)
        enable_layout.addWidget(self._cb_statusbar)

        root.addWidget(enable_group)
        root.addStretch()
        self.setStyleSheet(PANEL_STYLE.format(text_color="#1d1d1f"))

    def refresh_text_color(self, text_color: str):
        """
        根据背景亮度更新面板文字颜色（由 appearance_manager 调用）

        参数:
            text_color (str): 计算后的文字颜色，如 "#ffffff" 或 "#1d1d1f"
        """
        self.setStyleSheet(PANEL_STYLE.format(text_color=text_color))

    # ── 配置加载 ──────────────────────────────────────

    def _load_config(self):
        """
        （内部方法）从 usrCfg 加载真太阳时配置并填充到各控件

        参数:
            （无参数，从 config_manager 读取配置）

        返回:
            None

        加载内容:
            - auto_locate_on_startup → "启动时自动定位"复选框
            - longitude              → 经度 QDoubleSpinBox
            - latitude               → 纬度 QDoubleSpinBox
            - city_name              → 城市名称标签
            - enabled                → 主开关复选框
            - use_in_bazi            → "排八字中使用"子开关
            - show_in_statusbar      → "状态栏中显示"子开关

        加载完成后调用 _update_states() 设置控件的启用/禁用状态。
        """
        cfg = config_manager.get("solar_time") or {}

        # 启动自动定位
        auto = cfg.get("auto_locate_on_startup", True)
        self._cb_auto_startup.setChecked(auto)

        # 经纬度
        self._lon_input.setValue(cfg.get("longitude", 120.0))
        self._lat_input.setValue(cfg.get("latitude", 30.0))

        # 手动编辑模式（从经纬度只读状态反推，兼容旧配置）
        manual = cfg.get("manual_edit", False)
        self._cb_manual.setChecked(manual)

        # 城市名称
        city = cfg.get("city_name", "")
        self._city_display.setText(city if city else "未设置")

        # 启用开关
        self._cb_master.setChecked(cfg.get("enabled", False))
        self._cb_bazi.setChecked(cfg.get("use_in_bazi", True))
        self._cb_statusbar.setChecked(cfg.get("show_in_statusbar", True))
        self._update_states()

    def _connect_signals(self):
        """
        （内部方法）连接 UI 控件变更信号到处理逻辑

        参数:
            （无参数）

        返回:
            None

        连接关系:
            - _cb_auto_startup 的 toggled → 保存 auto_locate_on_startup
            - _cb_manual 的 toggled → _on_manual_toggled (切换只读/可编辑)
            - _lon_input / _lat_input 的 valueChanged → _save_config
            - _cb_master 的 toggled → _on_master_toggled
            - _cb_bazi / _cb_statusbar 的 toggled → _save_config
        """
        self._cb_auto_startup.toggled.connect(self._on_auto_startup_toggled)
        self._cb_manual.toggled.connect(self._on_manual_toggled)
        self._lon_input.valueChanged.connect(self._save_config)
        self._lat_input.valueChanged.connect(self._save_config)
        self._cb_master.toggled.connect(self._on_master_toggled)
        self._cb_bazi.toggled.connect(self._save_config)
        self._cb_statusbar.toggled.connect(self._save_config)

    # ── 状态切换 ──────────────────────────────────────

    def _on_auto_startup_toggled(self, checked):
        """
        （槽函数）"启动时自动定位"复选框切换

        参数:
            checked (bool): 勾选状态，由 QCheckBox.toggled 信号自动传入

        返回:
            None
        """
        config_manager.set("solar_time", "auto_locate_on_startup", value=checked)

    def _on_manual_toggled(self, checked):
        """
        （槽函数）"手动编辑经纬度"复选框切换

        参数:
            checked (bool): True=手动编辑模式（经纬度框可编辑）, False=自动模式（只读）

        返回:
            None

        做的事:
            1. 保存 manual_edit 配置到 usrCfg
            2. 更新经纬度框的只读/启用状态
        """
        config_manager.set("solar_time", "manual_edit", value=checked)
        self._update_states()

    def _on_master_toggled(self, checked):
        """
        （槽函数）真太阳时主开关切换

        参数:
            checked (bool): True=启用真太阳时, False=关闭

        返回:
            None

        做的事:
            1. 保存 enabled 配置到 usrCfg
            2. 调用 _update_states() 更新子开关状态
            3. 调用 _save_config() 确保子开关数据一致
        """
        config_manager.set("solar_time", "enabled", value=checked)
        self._update_states()
        self._save_config()

    def _update_states(self):
        """
        （内部方法）根据"手动编辑"复选框和主开关状态更新控件启用/禁用

        参数:
            （无参数）

        返回:
            None

        状态规则:
            - 手动编辑模式: 经纬度框可编辑，"刷新定位"和"选择城市"禁用
            - 自动模式: 经纬度框只读，"刷新定位"和"选择城市"可用
            - 主开关打开: 两个子开关可操作
            - 主开关关闭: 两个子开关禁用（灰色）
        """
        manual = self._cb_manual.isChecked()
        solar_on = self._cb_master.isChecked()

        # 手动编辑模式 → 可编辑；自动模式 → 只读
        self._lon_input.setReadOnly(not manual)
        self._lat_input.setReadOnly(not manual)

        # 操作按钮仅在自动模式下可用
        self._btn_locate.setEnabled(not manual)
        self._btn_pick_city.setEnabled(not manual)

        # 子开关仅在主开关打开时可操作
        self._cb_bazi.setEnabled(solar_on)
        self._cb_statusbar.setEnabled(solar_on)

    # ── 保存 ──────────────────────────────────────────

    def _save_config(self):
        """
        （内部方法）将当前面板上的经纬度和子开关值写入 usrCfg，并刷新状态栏

        参数:
            （无参数，直接从各控件读取当前值）

        返回:
            None

        保存内容:
            - solar_time.longitude         ← 经度 QDoubleSpinBox
            - solar_time.latitude          ← 纬度 QDoubleSpinBox
            - solar_time.use_in_bazi       ← "排八字中使用" 复选框
            - solar_time.show_in_statusbar ← "状态栏中显示" 复选框

        保存后强制刷新状态栏（确保真太阳时显示/隐藏即时生效，
        不受 30 秒定时器延迟影响）。
        """
        config_manager.set("solar_time", "longitude",
                           value=self._lon_input.value())
        config_manager.set("solar_time", "latitude",
                           value=self._lat_input.value())
        config_manager.set("solar_time", "use_in_bazi",
                           value=self._cb_bazi.isChecked())
        config_manager.set("solar_time", "show_in_statusbar",
                           value=self._cb_statusbar.isChecked())

        # 即时刷新状态栏（避免等到下一个 timer tick）
        mgr = getattr(self.window(), "_statusbar_mgr", None)
        if mgr:
            mgr._refresh()

    # ── 定位 ──────────────────────────────────────────

    def _on_auto_locate(self):
        """
        （槽函数）通过网络自动获取当前位置（IP 定位）

        参数:
            （无参数）

        返回:
            None

        流程:
            1. **网络检查**（3 秒超时）:
               - 无网络 → 降级为默认位置"浙江省 杭州市"（120.2, 30.25）
               - 有网络 → 继续下一步
            2. 按钮变为"定位中..."并禁用（防止重复点击）
            3. GET http://ip-api.com/json/（8 秒超时，绕过系统代理）
            4. 解析响应中的 lon / lat / city / regionName / country
            5. 更新经纬度输入框和城市名称显示
            6. 保存到 usrCfg

        无网络降级:
            显示"浙江省 杭州市（默认，无网络连接）"，经纬度设为 120.2, 30.25。
            杭州坐标取自内置城市数据库 chinese_cities.py。

        调用时机:
            - 启动时（如果 auto_locate_on_startup 已勾选）
            - 用户点击"刷新定位"按钮

        用法:
            # 用户点击"刷新定位"按钮
            self._btn_locate.clicked.connect(self._on_auto_locate)
        """
        # ── 网络检查 ──
        mgr = getattr(self.window(), "_statusbar_mgr", None)
        if mgr:
            mgr.show_status("检查网络...")

        if not _check_network():
            self._city_display.setText(f"{FALLBACK_CITY}（默认，无网络连接）")
            self._lon_input.setValue(FALLBACK_LON)
            self._lat_input.setValue(FALLBACK_LAT)
            config_manager.set("solar_time", "city_name", value=FALLBACK_CITY)
            self._save_config()
            print(f"[定位] 无网络 → 默认: {FALLBACK_CITY} ({FALLBACK_LON}, {FALLBACK_LAT})")
            if mgr:
                mgr.reset_status()
            return

        self._btn_locate.setEnabled(False)
        self._btn_locate.setText("定位中...")
        if mgr:
            mgr.show_status("定位中...")
        QApplication.processEvents()  # 刷新 UI，让用户看到"定位中..."状态

        try:
            # 使用 trust_env=False 绕过系统代理（VPN），获取真实 IP 定位
            session = requests.Session()
            session.trust_env = False
            resp = session.get("http://ip-api.com/json/", timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    lon = data["lon"]
                    lat = data["lat"]
                    city = data.get("city", "")
                    region = data.get("regionName", "")
                    country = data.get("country", "")
                    city_name = f"{country} {region} {city}".strip()

                    self._lon_input.setValue(lon)
                    self._lat_input.setValue(lat)
                    self._city_display.setText(city_name)
                    config_manager.set("solar_time", "city_name", value=city_name)
                    self._save_config()

                    print(f"[定位] IP自动定位: {city_name} ({lon}, {lat})")
                    self._btn_locate.setText("刷新定位")
                    self._btn_locate.setEnabled(True)
                    mgr = getattr(self.window(), "_statusbar_mgr", None)
                    if mgr:
                        mgr.reset_status()
                    return

            print("[定位] IP定位失败")
            self._city_display.setText("定位失败，请手动选择城市")
        except Exception as e:
            print(f"[定位] 网络请求失败: {e}")
            self._city_display.setText("网络不可用，请手动选择城市")
        finally:
            self._btn_locate.setText("刷新定位")
            self._btn_locate.setEnabled(True)
            mgr = getattr(self.window(), "_statusbar_mgr", None)
            if mgr:
                mgr.reset_status()

    def _on_pick_city(self):
        """
        （槽函数）弹出城市选择对话框，让用户手动搜索并选择城市

        参数:
            （无参数）

        返回:
            None

        流程:
            1. 创建 CityPickerDialog 实例（模态弹窗）
            2. 用户在弹窗中搜索/选择城市
            3. 如果用户点击"确定":
               - 从对话框获取 (prov, city, district, lon, lat) 五元组
               - 智能格式化城市名（避免直辖市和省直辖县的重复显示）
               - 更新经纬度输入框 + 城市名称标签
               - 保存到 usrCfg
            4. 如果用户点击"取消" → 什么都不做

        城市名显示规则:
            - 直辖市 (prov==city):       "北京 东城"
            - 省直辖县 (city==district): "海南 乐东黎族自治县"
            - 常规城市:                  "广东 深圳 南山"

        用法:
            # 用户点击"选择城市"按钮
            self._btn_pick_city.clicked.connect(self._on_pick_city)
        """
        dlg = CityPickerDialog(self)
        if dlg.exec() == CityPickerDialog.DialogCode.Accepted:
            r = dlg.result()
            if r:
                prov, city, district, lon, lat = r
                if prov == city or city == district:
                    city_name = f"{prov} {district}"
                else:
                    city_name = f"{prov} {city} {district}"
                self._lon_input.setValue(lon)
                self._lat_input.setValue(lat)
                self._city_display.setText(city_name)
                config_manager.set("solar_time", "city_name", value=city_name)
                self._save_config()
                print(f"[定位] 手动选择: {city_name} ({lon}, {lat})")
