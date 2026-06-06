"""
城市选择弹窗 — 搜索式列表对话框，供真太阳时定位使用

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【这个文件做什么】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  提供一个城市搜索选择对话框，用户在真太阳时面板中点击"选择城市"时弹出。
  数据源为全国 2851 个县级行政区划的经纬度坐标（WGS-84）。

  支持的交互方式：
    - 输入关键字实时过滤（匹配省名、市名、区/县名）
    - 点击"确定"或双击列表项确认选择
    - 未选择直接点"确定"等同取消

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【数据来源】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  国家统计局 2024 年行政区划 + 高德/腾讯地图坐标（GCJ-02 → WGS-84 转换）。
  数据文件: src/data/location/chinese_cities.py
  生成脚本: src/data/location/generate_cities.py
  原始数据: src/data/location/ok_geo.csv.7z

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【使用方式】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  dlg = CityPickerDialog(parent)
  if dlg.exec() == QDialog.Accepted:
      prov, city, district, lon, lat = dlg.result()

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【数据格式】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CITIES 列表中每项为 (省, 市, 区/县, 经度, 纬度) 五元组。
  显示时有智能去重：
    - 直辖市(prov==city):   "北京 东城"
    - 省直辖县(city==district): "海南 乐东黎族自治县"
    - 常规城市:              "广东 深圳 南山"
"""
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QLabel, QDialogButtonBox,
)
from PySide6.QtCore import Qt

# ── 城市数据文件路径 ──────────────────────────────────
# 使用相对路径（从本文件向上两级到 settings，再进入 src/data/location）
_CITIES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "location", "chinese_cities.py"
)


def _load_cities():
    """
    动态加载城市数据

    参数:
        （无参数）

    返回:
        list: CITIES 列表，每项为 (省, 市, 区/县, 经度, 纬度) 五元组

    为什么用 importlib 动态加载而非静态 import：
      - 避免在 settings 模块导入时就加载 194KB 的城市数据
      - 仅在用户打开城市选择弹窗时才读取文件（延迟加载）
      - 工程移动后路径自动跟随（基于本文件的相对路径）

    用法:
        >>> cities = _load_cities()
        >>> len(cities)
        2851
        >>> cities[0]
        ('北京市', '北京市', '东城区', 116.4167, 39.9289)
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("chinese_cities", _CITIES_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CITIES


class CityPickerDialog(QDialog):
    """
    城市选择对话框

    参数:
        parent (QWidget, 可选): 父 Widget

    用法:
        >>> dlg = CityPickerDialog(self)
        >>> if dlg.exec() == CityPickerDialog.DialogCode.Accepted:
        >>>     prov, city, district, lon, lat = dlg.result()
        >>>     print(f"选中: {prov} {city} {district} ({lon}, {lat})")

    交互:
        - 输入关键字实时过滤（匹配省名、市名、区/县名，大小写不敏感）
        - 点击"确定"或双击列表项确认选择
        - 未选择直接点"确定"等同取消（调用 reject() 关闭弹窗）
    """

    def __init__(self, parent=None):
        """
        构造 CityPickerDialog 实例

        参数:
            parent (QWidget, 可选): 父 Widget

        做的事:
            1. 设置窗口标题和最小尺寸（480×520）
            2. 调用 _load_cities() 动态加载 2851 条城市数据
            3. 初始化 _result = None（未选择状态）
            4. 调用 _init_ui() 构建弹窗界面
        """
        super().__init__(parent)
        self.setWindowTitle("选择城市")
        self.setMinimumSize(480, 520)
        self._cities = _load_cities()  # 打开弹窗时加载数据（延迟加载）
        self._result = None            # 选中结果: (省, 市, 区/县, 经度, 纬度) or None
        self._init_ui()

    def _init_ui(self):
        """
        （内部方法）构建弹窗 UI

        参数:
            （无参数）

        返回:
            None

        UI 结构（从上到下）:
            1. 搜索框 QLineEdit — placeholder "输入省市名称搜索..."
            2. 城市列表 QListWidget — 选中项蓝色高亮，双击可确认
            3. 底部按钮行 — "取消"（灰色）+ "确定"（蓝色）

        信号连接:
            - 搜索框 textChanged → _on_search（实时过滤列表）
            - 列表 itemDoubleClicked → _on_ok（双击确认）
            - 取消按钮 clicked → reject（关闭弹窗）
            - 确定按钮 clicked → _on_ok（确认选择）

        初始加载全部 2851 条城市记录。
        """
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── 搜索框 ──
        self._search = QLineEdit()
        self._search.setPlaceholderText("输入省市名称搜索...")
        self._search.setStyleSheet(
            "padding: 8px 12px; border: 1px solid #c0c0c0; border-radius: 8px; "
            "font-size: 15px;"
        )
        layout.addWidget(self._search)

        # ── 城市列表 ──
        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { border: 1px solid #dcdcdc; border-radius: 8px; font-size: 14px; }"
            "QListWidget::item { padding: 8px 12px; }"
            "QListWidget::item:selected { background: #007aff; color: white; }"
        )
        layout.addWidget(self._list)

        # ── 底部按钮行 ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(
            "padding: 6px 20px; border-radius: 6px; border: 1px solid #c0c0c0; "
            "background: #f5f5f5;"
        )
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        ok_btn.setStyleSheet(
            "padding: 6px 20px; border-radius: 6px; border: none; "
            "background: #007aff; color: white; font-weight: bold;"
        )
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

        # 初始加载全部列表
        self._populate_list("")

        # 信号连接
        self._search.textChanged.connect(self._on_search)
        self._list.itemDoubleClicked.connect(self._on_ok)

    def _populate_list(self, keyword: str):
        """
        （内部方法）根据关键字过滤并填充城市列表

        参数:
            keyword (str): 搜索关键字（用户输入的文本）。
                          空字符串 = 显示全部 2851 条记录。
                          非空时只显示省/市/区县名称中包含该关键字的记录（大小写不敏感）。

        返回:
            None

        每项显示格式:
            - 直辖市 (prov==city):       "北京 东城"
            - 省直辖县 (city==district): "海南 乐东黎族自治县"
            - 常规城市:                  "广东 深圳 南山"

        每项的 data (UserRole):
            (省, 市, 区/县, 经度, 纬度) 五元组
            通过 item.data(Qt.ItemDataRole.UserRole) 获取，用于 result() 返回

        过滤规则:
            - 关键字转为小写后匹配 display 字符串（小写）
            - 匹配的是显示名称，不是原始数据 → 支持搜索"北京"也能找到"北京市"的条目

        用法:
            >>> self._populate_list("南山")  # 搜索包含"南山"的城市
            >>> self._populate_list("")      # 显示全部城市
        """
        self._list.clear()
        kw = keyword.strip().lower()
        for prov, city, district, lon, lat in self._cities:
            # 智能显示：避免重复显示
            # 直辖市 (prov==city): "北京 东城"
            # 省直辖县 (city==district): "海南 乐东黎族自治县"
            # 常规城市: "广东 深圳 南山"
            if prov == city or city == district:
                display = f"{prov} {district}"
            else:
                display = f"{prov} {city} {district}"
            if kw and kw not in display.lower():
                continue
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, (prov, city, district, lon, lat))
            self._list.addItem(item)

    def _on_search(self, text):
        """
        （槽函数）搜索框文字变化 → 实时过滤列表

        参数:
            text (str): 搜索框中的当前文本，由 QLineEdit.textChanged 信号自动传入

        返回:
            None

        原理:
            每次用户输入/删除字符时，立即调用 _populate_list(text) 过滤。
            这种"即时搜索"的方式比"输入完后点搜索按钮"更符合现代 UI 习惯。

        用法:
            # 通过信号自动触发，不需要手动调用
            self._search.textChanged.connect(self._on_search)
        """
        self._populate_list(text)

    def _on_ok(self):
        """
        （槽函数）确认选择

        参数:
            （无参数）

        返回:
            None

        行为:
            - 有选中项 → 保存当前项的 UserRole data 到 self._result，调用 accept()
            - 无选中项 → 调用 reject()（等同取消，关闭弹窗）

        触发方式:
            - 点击"确定"按钮
            - 双击列表中的某个城市

        用法:
            # 通过信号自动触发
            ok_btn.clicked.connect(self._on_ok)
            self._list.itemDoubleClicked.connect(self._on_ok)
        """
        item = self._list.currentItem()
        if item:
            self._result = item.data(Qt.ItemDataRole.UserRole)
            self.accept()
        else:
            self.reject()

    def result(self):
        """
        返回用户选择的城市数据

        参数:
            （无参数）

        返回:
            tuple or None: 如果用户选择了城市，返回 (省, 市, 区/县, 经度, 纬度) 五元组；
                          如果用户取消了（点关闭/取消/未选择点确定），返回 None

        用法:
            >>> dlg = CityPickerDialog(self)
            >>> if dlg.exec() == QDialog.Accepted:
            >>>     prov, city, district, lon, lat = dlg.result()
            >>>     print(f"选中: {prov} {city} {district}, 经度={lon}, 纬度={lat}")
            >>> else:
            >>>     print("用户取消了选择")
        """
        return self._result
