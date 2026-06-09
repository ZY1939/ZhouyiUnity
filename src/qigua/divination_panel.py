"""
起卦主面板 — 整合卦图绘制 + 输入区域 + 结果显示 的核心面板

═══════════════════════════════════════════════════════════════
文件职责：提供 QiguaPanel 起卦主面板，组织卦图、输入、结果三大区域
         支持四种起卦方式（手工/报数/金钱/蓍草）的动态切换和跨方法同步
═══════════════════════════════════════════════════════════════

布局结构（ASCII art）：
  ┌─ QiguaPanel (root QVBoxLayout) ──────────────────────────┐
  │  ┌─ border_frame（无上/左边框，右边框线上戳到顶）──┐    │
  │  │  header: 起卦 ●手工 ●报数 ●金钱 ●蓍草 (方法选择器) │    │
  │  │  ── spacer ──                                     │    │
  │  │  卦象长方形（左）  │  QStackedWidget(右，4面板切换) │    │
  │  │  HexagramDrawer    │  [手工|报数|金钱/蓍草]          │    │
  │  │  ── spacer ──                                     │    │
  │  │  结果文字（本卦名称 → 变卦名称 / 六爻安静）           │    │
  │  └────────────────────────────────────────────────────┘    │
  │  ← addStretch() 所有额外空间沉底                           │
  └───────────────────────────────────────────────────────────┘

右侧面板索引：
  QStackedWidget index  0 = 手工指定面板（动爻多选复选框）
  QStackedWidget index  1 = 报数面板（三个SpinBox + 随机/秒表按钮）
  QStackedWidget index  2 = 金钱卦 / 蓍草卦 共用面板（下拉框选项不同）

导出类：
  QiguaPanel(QWidget) — 起卦主面板，组织所有起卦交互
  _DotButton(QPushButton) — 圆点选择按钮（选中实心/未选中空心），用于方法切换

被谁调用（字体/颜色刷新链）：
  yijing_viewer.py → refresh_font_size(font_size) / refresh_text_color(text_color)
                   → qigua_panel.refresh_font_size() / refresh_text_color()
                   → drawer.set_font_size() / drawer.set_text_color()
                   → 所有子面板 _update_panel_layout() / 样式更新

调用了哪些文件：
  - bagua.py:           GuaResult dataclass, COIN_TO_YAO, YARROW_TO_YAO 常量
  - hexagram_drawer.py: HexagramDrawer 卦图绘制控件
  - hexagram_calc.py:   calc_three_numbers(), calc_from_yang_lines(), calc_six_lines()
  - countdown_timer.py: CountdownDialog 10秒倒计时弹窗（报数模式"随机"按钮）
  - stopwatch_timer.py: StopwatchDialog 秒表弹窗（报数模式"秒表"按钮）
  - config_manager.py:  读写 usrCfg/UsrCfg.json，持久化上次起卦方式 + Lock状态
  - case_manager.py:    （间接）通过 GuaResult 保存案例

扩展方式：在 METHODS 列表添加条目，_build_right_panels 增加对应面板。

样式规范（与设置面板保持一致）：
  - 不硬编码 font-size，继承 QApplication 全局字体
  - 输入控件使用 CSS padding: 6px 10px
  - 行高由 HexagramDrawer.line_h 驱动，随字体动态缩放

───────────────────────────────────────────────────────────
所有【可手动调整】参数汇总表（在 _init_ui 中初始化，以 lh=line_h 为基准）
───────────────────────────────────────────────────────────
  参数名                 默认值(px)     说明
  ─────────────────────────────────────────────────────────
  _gap_xs                lh * 0.12     极小间距（header→内容区、结果→卦图）
  _gap_sm                lh * 0.25     小间距（面板内部元素）
  _gap_md                lh * 0.45     中等间距（标题→第一个dot）
  _gap_drawer            0             卦图到右侧面板的水平距离
  _gap_cb_text           1             勾选框到"动"字的距离
  _gap_cb_combo_extra    2             "动"复选框到下拉框的额外间距
  _gap_lock              8             Lock复选框到"动爻设置"文字右边的间距
  _gap_result_top        -4            结果文字到卦图的垂直距离（负值=上移）
  _gap_btn_pad           30            报数面板按钮水平留白
  _gap_btn_h             38            报数面板按钮高度
  _gap_mod_top_fs        3             mod标签字号偏移（相对全局字号减小量）
  _gap_mod_val_fs        3             余数值字号偏移（相对全局字号减小量）
  _gap_header_left       10            header"起卦"距窗口左侧的距离
  _gap_border_right      16            右边框线距combo下拉框右边缘的留白
"""
from PySide6.QtWidgets import (QGridLayout, QWidget, QVBoxLayout, QHBoxLayout,
                                QPushButton, QStackedWidget, QLabel, QButtonGroup,
                                QCheckBox, QSpinBox, QComboBox, QFrame, QSizePolicy,
                                QAbstractSpinBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QPixmap, QColor, QPen, QPainterPath
import os

from ..settings.config_manager import config_manager

from .bagua import GuaResult, COIN_TO_YAO, YARROW_TO_YAO
from .hexagram_drawer import HexagramDrawer
from .hexagram_calc import calc_three_numbers, calc_from_yang_lines, calc_six_lines, _yang_to_xiantian
from .hexagram_loader import load_all_gua, get_gua_by_xiantian
from ..algorithms.mutiDongyaoSel import get_judgment_line
from .countdown_timer import CountdownDialog
from .stopwatch_timer import StopwatchDialog
from .suangua import SuanguaPanel
from .CONST_DEFINE_UI import QiguaConfig
import os

# ── 调试断言：仅异常时输出到终端，方便排查问题 ──
def _check(condition, msg):
    if not condition:
        print(f"[QiguaPanel] ⚠️ {msg}", flush=True)

# ── 起卦方式注册表 ──
METHODS = [
    {"key": "manual", "label": "手工"},
    {"key": "three",  "label": "报数"},
    {"key": "coin",   "label": "金钱"},
    {"key": "yarrow", "label": "蓍草"},
]

LINE_NAMES = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]

# 与设置面板一致的输入控件样式（padding: 6px 10px / 6px 18px，不设 font-size）
_INPUT_STYLE = """
    padding: 6px 10px;
    border: 1.5px solid #dcdcdc;
    border-radius: 6px;
    background: #fff;
    color: #1d1d1f;
"""
_INPUT_FOCUS = "border-color: #007aff;"

_BTN_STYLE = """
    padding: 6px 18px;
    border: 1px solid #dcdcdc;
    border-radius: 6px;
    background: #f5f5f7;
    color: #1d1d1f;
"""
_BTN_HOVER = "border-color: #007aff;"

_PRIMARY_BTN = """
    border: none; border-radius: 6px; background: #007aff;
    font-weight: bold; color: #ffffff;
"""


def _is_light_color(hex_color: str) -> bool:
    """
    判断 hex 颜色是否为亮色（用于决定深色/浅色模式）

    将 hex 颜色转为 RGB，计算相对亮度。亮度 > 128 视为"亮色"→ 深色模式。

    Args:
        hex_color: CSS hex 颜色字符串，如 "#1d1d1f" 或 "#ffffff"

    Returns:
        True: 亮色文字 → 深色背景模式
        False: 暗色文字 → 浅色背景模式
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) < 6:
        return False
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return luminance > 128


class _DotButton(QPushButton):
    """
    圆点选择按钮 — 选中实心蓝色，未选中空心灰色

    用于起卦方法选择器（手工●报数●金钱●蓍草）。
    配合 QButtonGroup 实现互斥单选，一次只能选中一个方法。

    类属性：
      _COLOR: 选中时的蓝色值 (#007aff)，hover 时也使用此颜色
    """

    _COLOR = "#007aff"

    def __init__(self, parent=None):
        """
        初始化圆点按钮

        设置 14×14 固定大小、手型光标、可勾选、初始未选中。

        Args:
            parent: 父级 QWidget
        """
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(14, 14)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self._on_toggled)
        self._update_style(False)

    def _on_toggled(self, checked: bool):
        """
        勾选状态变化时更新外观样式

        Args:
            checked: True=选中（实心蓝）, False=未选中（空心灰）

        调用时机：按钮 toggled 信号触发
        """
        self._update_style(checked)

    def _update_style(self, checked: bool):
        """
        根据勾选状态更新按钮 CSS 样式

        选中（checked=True）：实心 #007aff 底 + #007aff 边框
        未选中（checked=False）：透明底 + #c7c7cc 灰色边框
        hover 时始终显示 #007aff 蓝色边框

        Args:
            checked: True=选中, False=未选中
        """
        bg = self._COLOR if checked else "transparent"
        border = self._COLOR if checked else "#c7c7cc"
        self.setStyleSheet(f"""
            QPushButton {{ background: {bg}; border: 2px solid {border}; border-radius: 7px; }}
            QPushButton:hover {{ border-color: {self._COLOR}; }}
        """)


class _GuaPickerPopup(QWidget):
    """
    卦选择弹窗 — Popup 窗口，点击外部自动关闭

    关闭时自动恢复标题按钮的 Lock 禁用状态 + 清理面板引用。

    Parameters:
        picker: QListWidget — 已构建好的卦列表控件
        was_enabled: bool — 弹出前标题按钮的启用状态（Lock OFF=True, Lock ON=False）
        title_btn: QPushButton — 标题按钮引用，用于关闭时恢复状态
        panel: QiguaPanel — 面板引用，用于关闭时清理 _gua_picker
    """

    def __init__(self, picker, was_enabled, title_btn, panel, parent=None):
        super().__init__(None)  # 必须无 parent，否则不是顶层 Popup 窗口
        self._was_enabled = was_enabled
        self._title_btn = title_btn
        self._panel = panel
        self.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(picker)

    def closeEvent(self, event):
        """关闭弹窗时恢复 Lock 状态 + 清理面板引用"""
        if not self._was_enabled and self._title_btn is not None:
            self._title_btn.setEnabled(False)
        if self._panel is not None:
            self._panel._gua_picker = None
        super().closeEvent(event)


class QiguaPanel(QWidget):
    """
    起卦主面板 — 组织卦图、输入、结果三大区域

    该类是整个起卦工具包的核心 UI 组件，负责：
      - 创建并管理 HexagramDrawer（左侧卦图）
      - 创建并管理 QStackedWidget（右侧四种输入面板）
      - 方法切换、动爻跨模式同步、Lock 锁定机制
      - 字体大小和文字颜色的全局联动刷新

    类属性说明（在 __init__ 中初始化）：
      _current_method: str          当前起卦方式 ("manual"/"three"/"coin"/"yarrow")
                                    所有交互逻辑以此判断分支
      _prev_method: str             上一次起卦方式，用于 _switch_method() 判断
                                    是否需要初始化控件值（金钱↔蓍草互切不重新初始化）
      _font_size: int               当前全局字体大小(pt)，由 refresh_font_size() 更新
                                    所有子控件字号以此加减偏移
      _text_color: str              当前文字颜色（CSS格式如 "#1d1d1f" 或 "#ffffff"）
                                    由 refresh_text_color() 根据背景色深浅动态更新
                                    所有 QLabel/QCheckBox/QComboBox 的 stylesheet 嵌入此值
      _changing_lines: set[int]     动爻集合 {1, 2, ..., 6}（1=初爻..6=上爻）
                                    跨方法切换保留，是四种起卦方式的动爻共享状态
                                    由各面板的交互事件更新，_sync_controls_to_changing_lines() 同步到所有面板控件
      _lock_cbs: list[QCheckBox]    所有 Lock 复选框的引用列表
                                    在 _make_title_row() 和 _make_lock_only_row() 中追加
                                    _on_lock_toggled() 遍历此列表同步所有复选框状态
      _lock_checked: bool           Lock 是否开启，用于 refresh 后恢复自定义 indicator 样式
                                    在 _on_lock_toggled() 中更新，_apply_lock_indicator() 中使用
    """

    def __init__(self, parent=None):
        """
        初始化起卦主面板

        流程：
          1. 初始化类属性（当前方法、字体、文字颜色、动爻集合、Lock相关）
          2. 调用 _init_ui() 构建全部界面
          3. 调用 _connect_all() 连接信号槽
          4. （_init_ui 末尾自动加载上次起卦方式并执行首次起卦）

        Args:
            parent: 父级 QWidget，通常为 yijing_viewer 中的容器
        """
        super().__init__(parent)
        self._current_method = "manual"            # 当前起卦方式（见类属性说明）
        self._prev_method = "manual"               # 追踪上一次方法，用于切换时判断是否需要初始化控件值
        self._font_size = 16                       # 当前全局字体大小，refresh_font_size() 会更新
        self._text_color = "#1d1d1f"               # 默认深色文字，refresh_text_color() 会更新
        self._changing_lines: set[int] = set()     # 动爻集合（1=初爻..6=上爻），跨方法切换保留
        self._lock_cbs: list[QCheckBox] = []       # 所有 Lock 复选框，toggled 时相互同步
        self._lock_checked = False                 # Lock 是否开启，用于 refresh 后恢复 indicator
        self._init_ui()
        self._connect_all()

    def _update_frame_max_width(self):
        """
        计算并设置圆角矩形右边框的最大宽度

        计算公式：
          max_w = drawer.width + _gap_drawer + cb_w + _gap_cb_combo + combo_w + _gap_border_right

        其中 cb_w（"动"复选框宽度）= "动"字宽 + _gap_cb_text + 14px(indicator)
             combo_w（下拉框宽度）= 最长选项文字宽 + 28px(padding+箭头)
             _gap_border_right = 右边框线距 combo 右边缘的留白

        调用时机：
          - _init_ui() 末尾首次计算
          - refresh_font_size() 中字号变更后重新计算（字体影响所有文字度量）
        """
        fm = QFont()
        fm.setPointSize(self._font_size)
        m = QFontMetrics(fm)
        # 1. 计算"动"复选框宽度：文字宽 + 文字到indicator间距 + indicator(14px)
        cb_text_w = m.horizontalAdvance("动")
        cb_w = cb_text_w + self._gap_cb_text + 14
        # 2. 计算下拉框宽度：取所有选项中最长的 + padding+箭头(28px)
        combo_text_w = max(m.horizontalAdvance(t) for t in self.COIN_OPTIONS)
        combo_w = combo_text_w + 28
        # 3. 从 drawer 左侧累加到 combo 右边缘 + 右边距
        max_w = self._drawer.width() + self._gap_drawer + cb_w + self._gap_cb_combo + combo_w + self._gap_border_right
        self._border_frame.setMaximumWidth(max_w)

    def _compute_cb_gaps(self):
        """
        根据当前字体动态计算"动"标签到下拉框的间距

        总间距 = "动"字的实际宽度 + _gap_cb_combo_extra
        字号变大时"动"字变宽，间距自动跟随变大

        调用时机：
          - _init_ui() 中首次计算
          - refresh_font_size() 中字号变更后重新计算
        """
        font = QFont()
        font.setPointSize(self._font_size - 2)
        fm = QFontMetrics(font)
        char_w = fm.horizontalAdvance("动")
        self._gap_cb_combo = char_w + self._gap_cb_combo_extra

    def _dropdown_style(self) -> str:
        """
        根据当前文字颜色返回下拉面板样式（深底白字/浅底黑字自适应）

        深色主题（text_color="#ffffff"）：深灰底白字，边框#555
        浅色主题（text_color="#1d1d1f"）：白底黑字，边框#dcdcdc

        Returns:
            str: QComboBox QAbstractItemView 的 CSS 样式字符串

        调用时机：
          - QComboBox 的 stylesheet 中嵌入此方法的返回值
          - refresh_font_size() 和 refresh_text_color() 中更新 combo 样式时调用
        """
        if self._text_color == "#ffffff":
            return ("background: #2c2c2e; color: #ffffff; border: 1px solid #555555; "
                    "selection-background-color: #007aff; selection-color: #ffffff;")
        else:
            return ("background: #ffffff; color: #1d1d1f; border: 1px solid #dcdcdc; "
                    "selection-background-color: #007aff; selection-color: #ffffff;")

    # ═══════════════════════════════════════════════════════════
    #  构建界面（_init_ui 及其子方法）
    # ═══════════════════════════════════════════════════════════

    def _init_ui(self):
        """
        构建完整起卦面板界面

        布局层次（自上而下）：
          1. 创建 HexagramDrawer ← 行高 lh 是所有间距的基准单位
          2. 计算所有间距（以 lh 为基准，随字体动态缩放）
          3. root QVBoxLayout → border_frame QFrame（右+下圆角边框）
          4. header：起卦标题 + 4个方法选择 dot + 标签
          5. 中部 content：drawer(左) + QStackedWidget(右，4个面板)
          6. 底部 footer：结果文字 QLabel
          7. root.addStretch() 沉底
          8. 加载上次起卦方式 → 执行首次起卦

        调用时机：__init__() 中仅调用一次
        """
        # ── 第1步：创建 drawer — 其 line_h 是所有间距的基准单位 ──
        self._drawer = HexagramDrawer()
        lh = self._drawer.line_h  # 基准行高，所有间距以此计算

        # ── 第2步：计算所有间距（以 line_h 为基准，随字体动态缩放）──
        self._gap_xs = max(2, int(lh * 0.12))   # 极小间距
        self._gap_sm = max(4, int(lh * 0.25))   # 小间距（面板内部）
        self._gap_md = max(6, int(lh * 0.45))   # 中等间距
        # 【可手动调整】卦图到右侧面板的水平距离（px）
        self._gap_drawer = 0
        # 【可手动调整】勾选框到"动"字的距离（px，QCheckBox spacing）
        self._gap_cb_text = 1
        # 【可手动调整】"动"复选框到下拉框的额外间距（px），总间距 = "动"字宽度 + 此值
        self._gap_cb_combo_extra = 2
        # 【可手动调整】起卦面板到算卦面板的水平间距（px）
        self._gap_suangua = QiguaConfig.gap_suangua
        # 【可手动调整】Lock复选框到"动爻设置"文字右边的间距（px）
        self._gap_lock = 8
        # 【可手动调整】报数面板 Lock 文字到刷新按钮的间距（px）
        self._gap_refresh = 20
        # 【可手动调整】刷新按钮图标尺寸比例（相对 name_h，默认 0.85 = name_h 的 85%）
        self._gap_refresh_icon_scale = 1
        # 【可手动调整】结果文字到卦图的垂直距离（px）
        self._gap_result_top = -4
        # 【可手动调整】动爻判断文字到结果文字的垂直间距（px）
        self._gap_judgment_top = 4
        # 【可手动调整】动爻判断文字字号偏移（相对全局字号的差值），负数=比正文小
        self._fs_judgment = -2
        # 【可手动调整】报数面板按钮水平留白（px），按钮宽 = 两个汉字宽 + 此值
        self._gap_btn_pad = 30
        # 【可手动调整】报数面板按钮高度（px）
        self._gap_btn_h = 38
        # 【可手动调整】mod 标签字号偏移（相对全局字号的减小量），上行"mod N"用
        self._gap_mod_top_fs = 3
        # 【可手动调整】余数值字号偏移（相对全局字号的减小量），下行余数用
        self._gap_mod_val_fs = 3
        self._compute_cb_gaps()

        # 【可手动调整】header"起卦"距窗口左侧的距离（px）
        self._gap_header_left = 10
        # 【可手动调整】右边框线距combo下拉框右边缘的留白距离（px）
        # 起点 = combo下拉框右边缘，_update_frame_max_width() 计算: ... + combo宽 + _gap_border_right
        self._gap_border_right = 16

        # ── 第3步：root 布局（QVBoxLayout → panels_row）──
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0,
                                self._gap_xs, self._gap_sm)
        root.setSpacing(0)

        # panels_row — 起卦面板 + 算卦面板 水平并排
        self._panels_row = QHBoxLayout()
        self._panels_row.setContentsMargins(0, 0, 0, 0)
        self._panels_row.setSpacing(self._gap_suangua)
        root.addLayout(self._panels_row)
        root.addStretch()  # 所有额外空间沉底，保证面板靠上对齐

        # ── 第4步：border_frame（右边+下边圆角矩形边框，无左/上边框）──
        # 右边框线向上戳到 header 行顶端，让方法选择器"嵌入"矩形框内
        # header 本身左边无边框，形成开放感
        self._border_frame = QFrame()
        self._border_frame.setObjectName("border_frame")
        self._border_frame.setStyleSheet(f"""
            QFrame#border_frame {{
                border: 1px solid {self._text_color};
                border-left: none;
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 10px;
                background: transparent;
            }}
        """)
        self._frame_layout = QVBoxLayout(self._border_frame)
        self._frame_layout.setContentsMargins(0, 0, 0, 0)
        self._frame_layout.setSpacing(0)

        # ── 第5步：header — 方法选择器行（在矩形框内顶部）──
        # 左边开放无边框，右边线向上戳到顶
        self._header_layout = QHBoxLayout()
        self._header_layout.setContentsMargins(self._gap_header_left, 0, 0, 0)
        self._header_layout.setSpacing(0)
        self._build_header(self._header_layout)
        self._frame_layout.addLayout(self._header_layout)
        # header 与内容区之间的小间距
        self._frame_layout.addSpacing(self._gap_xs)

        # ── 第6步：中部 content — 卦图(左) + QStackedWidget(右) ──
        self._content_layout = QHBoxLayout()
        self._content_layout.setSpacing(self._gap_drawer)

        self._content_layout.addWidget(self._drawer, 0, Qt.AlignmentFlag.AlignTop)

        self._right_stack = QStackedWidget()
        self._build_right_panels()
        self._content_layout.addWidget(self._right_stack, 1, Qt.AlignmentFlag.AlignTop)

        self._frame_layout.addLayout(self._content_layout)

        # ── 第7步：结果文字到卦图的垂直间距（可手动调整）──
        self._frame_layout.addSpacing(self._gap_result_top)

        # ── 第8步：底部 footer — 结果文字 ──
        self._footer_layout = QHBoxLayout()
        self._footer_layout.setContentsMargins(self._gap_header_left, 0, 0, 0)
        self._footer_layout.setSpacing(self._gap_sm)
        self._build_footer(self._footer_layout)
        self._frame_layout.addLayout(self._footer_layout)

        # ── 第8.1步：动爻判断方式标签 ──
        self._frame_layout.addSpacing(self._gap_judgment_top)
        self._judgment_layout = QHBoxLayout()
        self._judgment_layout.setContentsMargins(self._gap_header_left, 0, 0, 0)
        self._judgment_layout.setSpacing(self._gap_sm)
        self._label_judgment = QLabel("")
        self._label_judgment.setWordWrap(True)
        self._label_judgment.setStyleSheet(
            f"QLabel {{ color: {self._text_color}; font-size: {self._font_size + self._fs_judgment}px; }}")
        self._judgment_layout.addWidget(self._label_judgment, 1)
        self._frame_layout.addLayout(self._judgment_layout)

        self._panels_row.addWidget(self._border_frame)

        # ── 第8.5步：算卦面板（右侧并排）──
        self._suangua_panel = SuanguaPanel()
        self._panels_row.addWidget(self._suangua_panel, 1)

        # ── 第9步：计算边框右边界最大宽度 ──
        self._update_frame_max_width()

        # ── 第10步：从配置加载上次起卦方式，执行首次起卦 ──
        saved_method = config_manager.get("general", "qigua_method") or "manual"
        idx = next((i for i, m in enumerate(METHODS) if m["key"] == saved_method), 0)
        self._dots[idx].setChecked(True)
        self._switch_method(saved_method)
        self._on_calc()  # 执行首次起卦

        # ── 第11步：预生成 Lock 勾图到 usrCfg/_lock_chk.png ──
        self._ensure_lock_chk_image()

    def _build_header(self, header: QHBoxLayout):
        """
        构建方法选择器行（header）

        结构：起卦(标题按钮) + 间距 + ●手工 ●报数 ●金钱 ●蓍草(4组dot+标签) + stretch

        设计要点：
          - "起卦"标题同时也是起卦按钮（点击触发 _on_calc()）
          - 每个方法由 _DotButton + QPushButton 标签组成，两者均可点击
          - 标签间间距由 _update_header_alignment() 动态计算，使「蓍草」右边缘与下拉框右边缘对齐
          - 末尾 addStretch() 吸收额外空间

        Args:
            header: 父级 QHBoxLayout，由 _init_ui 创建并传入

        调用时机：_init_ui() → _build_header()
        """
        lh = self._drawer.line_h

        # "起卦"标题同时也是起卦按钮
        self._title_label = QPushButton("起卦")
        self._title_label.setFlat(True)
        self._title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._title_label.setFixedHeight(lh)
        # eventFilter 捕获鼠标按下 → 确保弹出菜单（比 clicked 信号更可靠）
        self._title_label.installEventFilter(self)
        # 按实际字号计算文本宽度，避免大字号下被裁剪
        title_font = QFont()
        title_font.setPointSize(self._font_size + 4)
        title_font.setBold(True)
        title_fm = QFontMetrics(title_font)
        self._title_label.setMinimumWidth(title_fm.horizontalAdvance("起卦") + 4)
        self._title_label.setStyleSheet(f"""
            QPushButton {{
                font-size: {self._font_size + 4}px;
                font-weight: bold;
                color: #007aff;
                border: none;
                background: transparent;
                text-align: left;
            }}
            QPushButton:hover {{ color: #0056cc; }}
        """)
        header.addWidget(self._title_label)
        header.addSpacing(self._gap_md)   # 标题→第一个 dot 间距，与原来一致

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        self._dots: list[_DotButton] = []
        self._header_labels: list[QPushButton] = []

        for i, m in enumerate(METHODS):
            dot = _DotButton()
            self._btn_group.addButton(dot, i)
            self._dots.append(dot)
            header.addWidget(dot)

            # 文字标签也是可点击的（flat QPushButton 仿 QLabel 外观）
            lbl = QPushButton(m["label"])
            lbl.setFlat(True)
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            lbl.setStyleSheet(f"""
                QPushButton {{
                    color: #86868b; border: none; background: transparent;
                    font-size: {self._font_size}px;
                }}
                QPushButton:hover {{ color: {self._text_color}; }}
            """)
            lbl.clicked.connect(lambda checked, idx=i: self._dots[idx].click())
            self._header_labels.append(lbl)
            header.addWidget(lbl)

            if i < len(METHODS) - 1:
                header.addSpacing(0)  # _update_header_alignment() 会动态更新

        header.addStretch()

        # 初始计算标签间间距（依赖 drawer 宽度，须在 drawer 构造后调用）
        self._update_header_alignment()

    def _update_header_alignment(self):
        """
        动态计算 header 方法标签间间距，使「蓍草」右边缘与下拉框右边缘对齐

        计算逻辑：
          1. 计算右侧面板 combo 右边缘的绝对 x 坐标
          2. 计算 header 元素链总宽度（不含标签间间距）
          3. 可用空间 = combo_right - chain_start - chain_content_w
          4. 3个方法间 gap = 可用空间 / 3（最小4px）

        调用时机：
          - _build_header() 末尾首次计算
          - refresh_font_size() 中字号变更后重新计算（字体影响所有文字度量）
        """
        # 字体度量
        fm = QFont()
        fm.setPointSize(self._font_size)
        metrics = QFontMetrics(fm)

        # --- 右侧面板 combo 右边缘（绝对 x） ---
        cb_text_w = metrics.horizontalAdvance("动")
        cb_w = cb_text_w + self._gap_cb_text + 14  # 14 = checkbox indicator
        combo_text_w = max(metrics.horizontalAdvance(t) for t in self.COIN_OPTIONS)
        combo_w = combo_text_w + 28  # padding + dropdown arrow
        combo_right = self._drawer.width() + self._gap_drawer + cb_w + self._gap_cb_combo + combo_w

        # --- Header 元素宽度 ---
        title_w = metrics.horizontalAdvance("起卦") + 12
        dot_w = 14
        label_ws = [metrics.horizontalAdvance(m["label"]) for m in METHODS]
        chain_content_w = 4 * dot_w + sum(label_ws)  # dots + labels 不含间距

        # --- 标签间间距：让「蓍草」右边缘 = combo 右边缘 ---
        # chain 起点 = 标题右边缘 + _gap_md（不碰这个间距，保持与原来一致）
        chain_start = title_w + self._gap_md
        available = combo_right - chain_start - chain_content_w
        gap_method = max(4, available // 3)

        # --- 更新 3 个方法间 spacer（索引 4, 7, 10） ---
        header = self._header_layout
        for gap_idx in (4, 7, 10):
            item = header.itemAt(gap_idx)
            if item and item.spacerItem():
                item.spacerItem().changeSize(gap_method, 0)

        header.invalidate()

    def _build_right_panels(self):
        """
        构建右侧面板 → 添加到 QStackedWidget

        QStackedWidget 索引映射：
          index 0 = _make_manual_panel()  → 手工指定面板
          index 1 = _make_three_panel()   → 报数面板
          index 2 = _make_lines_panel()   → 金钱卦/蓍草卦 共用面板

        调用时机：_init_ui() → _build_right_panels()，仅一次
        """
        self._right_stack.addWidget(self._make_manual_panel())   # 0
        self._right_stack.addWidget(self._make_three_panel())    # 1
        self._right_stack.addWidget(self._make_lines_panel())    # 2 — 金钱/蓍草共用

    def _build_footer(self, footer: QHBoxLayout):
        """
        构建底部结果文字区域

        包含一个 QLabel 用于显示起卦结果：
          格式: "䷀ 乾为天  →  ䷫ 天风姤" 或 "䷀ 乾为天 (六爻安静)"

        Args:
            footer: 父级 QHBoxLayout，由 _init_ui 创建并传入

        调用时机：_init_ui() → _build_footer()，仅一次
        """
        self._label_result = QLabel("")
        self._label_result.setWordWrap(True)
        self._label_result.setStyleSheet(f"QLabel {{ color: {self._text_color}; }}")
        footer.addWidget(self._label_result, 1)

    def _make_title_row(self, name_h: int) -> QWidget:
        """
        创建"动爻设置"标题行 + Lock 上锁复选框

        结构：QLabel("动爻设置") + 间距 + QCheckBox("Lock") + stretch

        Lock 复选框用于锁定所有交互控件，防止误操作。
        创建的 QCheckBox 会被追加到 self._lock_cbs 列表，确保多个面板间
        Lock 状态同步。

        Args:
            name_h: 标题行固定高度(px)，等于 drawer.name_area_h，保证与卦图对齐

        Returns:
            QWidget: 标题行容器（objectName="title_row"）

        调用时机：
          - _make_manual_panel() 中调用
          - _make_lines_panel() 中调用
        """
        row = QWidget()
        row.setObjectName("title_row")  # 标记，防止 _update_panel_layout 覆盖高度
        row.setFixedHeight(name_h)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        title = QLabel("动爻设置")
        tf = QFont()
        tf.setPointSize(self._font_size)
        tf.setBold(True)
        title.setFont(tf)
        title.setStyleSheet(f"QLabel {{ color: {self._text_color}; }}")
        title.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(title)

        lock_spacer = QWidget()
        lock_spacer.setFixedWidth(self._gap_lock)
        lock_spacer.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        lay.addWidget(lock_spacer)

        lock_cb = QCheckBox("Lock")
        lock_cb.setStyleSheet(f"QCheckBox {{ spacing: 4px; color: {self._text_color}; font-size: {self._font_size - 2}px; }}")
        lock_cb.toggled.connect(self._on_lock_toggled)
        lay.addWidget(lock_cb)
        self._lock_cbs.append(lock_cb)

        lay.addStretch()
        return row

    # ═══════════════════════════════════════════════════════════
    #  右侧面板：手工指定
    # ═══════════════════════════════════════════════════════════

    def _make_manual_panel(self) -> QWidget:
        """构建手工指定面板

        QVBoxLayout: title_row + 6 行 QWidget 容器（每行 setFixedHeight(line_h)），
        与金钱面板一致的行高控制方式，确保与卦图爻线严格对齐。

        Lock 在 title_row 中，单动爻在 上爻行 col2 位置。
        通过 _align_manual_columns() 对齐复选框宽度。
        """
        w = QWidget()
        w.setObjectName("manual_panel")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 4)
        lay.setSpacing(0)

        name_h = self._drawer.name_area_h
        self._manual_cbs: list[QCheckBox] = []
        line_h = self._drawer.line_h

        # Row 0: 标题行（与 lines/three 面板同款 _make_title_row，y=0）
        self._manual_title_row = self._make_title_row(name_h)
        lay.addWidget(self._manual_title_row)

        cb_font = QFont()
        cb_font.setPointSize(self._font_size)

        # Rows 1-6: QWidget 容器包裹每行，setFixedHeight(line_h) 确保与卦图对齐
        for i in range(5, -1, -1):
            line_num = i + 1
            row_wrapper = QWidget()
            row_wrapper.setFixedHeight(line_h)
            row_wrapper.setObjectName(f"manual_row_{line_num}")
            row = QHBoxLayout(row_wrapper)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)

            if i == 5:
                self._shangyao_cb = QCheckBox("上爻")
                self._shangyao_cb.setFont(cb_font)
                self._shangyao_cb.setStyleSheet(f"QCheckBox {{ spacing: 8px; color: {self._text_color}; }}")
                self._shangyao_cb.toggled.connect(lambda checked, ln=line_num: self._on_manual_changing_toggled(ln, checked))
                self._manual_cbs.append(self._shangyao_cb)
                row.addWidget(self._shangyao_cb)

                spacer = QWidget()
                spacer.setFixedWidth(self._gap_lock)
                spacer.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                row.addWidget(spacer)

                self._single_line_cb = QCheckBox("单动爻")
                self._single_line_cb.setFont(cb_font)
                self._single_line_cb.setStyleSheet(f"QCheckBox {{ spacing: 4px; color: {self._text_color}; }}")
                self._single_line_cb.toggled.connect(self._on_single_line_toggled)
                row.addWidget(self._single_line_cb)
            else:
                cb = QCheckBox(LINE_NAMES[i])
                cb.setFont(cb_font)
                cb.setStyleSheet(f"QCheckBox {{ spacing: 8px; color: {self._text_color}; }}")
                cb.toggled.connect(lambda checked, ln=line_num: self._on_manual_changing_toggled(ln, checked))
                self._manual_cbs.append(cb)
                row.addWidget(cb)

            row.addStretch()
            lay.addWidget(row_wrapper)

        lay.addStretch()
        return w

    def _align_manual_columns(self):
        """对齐 上爻 checkbox 宽度 → title_row 中 "动爻设置" 标签实际宽度

        用 QFontMetrics 计算标题文字宽度，设置 上爻 checkbox 最小宽度，
        确保 Lock（title_row 中）和 单动爻（上爻行中）的 x 坐标一致。
        """
        shangyao = getattr(self, "_shangyao_cb", None)
        if shangyao is None:
            return
        fm = QFont()
        fm.setPointSize(self._font_size)
        fm.setBold(True)
        m = QFontMetrics(fm)
        title_w = m.horizontalAdvance("动爻设置")
        shangyao.setMinimumWidth(title_w)

    # ═══════════════════════════════════════════════════════════
    #  右侧面板：报数（三位数）
    # ═══════════════════════════════════════════════════════════

    def _make_three_panel(self) -> QWidget:
        """
        构建报数面板

        布局：Lock 行 + 动(SpinBox+mod6) + 上(SpinBox+mod8) + 下(SpinBox+mod8)
              + 随机/秒表按钮(并排)

        三个 QSpinBox 分别对应：
          - 动爻数（取余 mod6，0-5 → 动爻位置）
          - 上卦数（取余 mod8，映射到先天八卦）
          - 下卦数（取余 mod8，映射到先天八卦）

        每次 spin 值变化自动触发起卦计算。
        随机按钮 → 10秒倒计时弹窗 → 自动填入三个随机数
        秒表按钮 → 手动计时弹窗 → 填入起止时间差

        Returns:
            QWidget: 报数面板（objectName="three_panel"）

        调用时机：_build_right_panels() 中调用，仅一次
        """
        w = QWidget()
        w.setObjectName("three_panel")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 4)
        lay.setSpacing(0)

        name_h = self._drawer.name_area_h
        line_h = self._drawer.line_h

        # Lock 复选框（与其他面板相同位置，不显示"动爻设置"文字）
        self._three_title_row = self._make_lock_only_row(name_h)
        lay.addWidget(self._three_title_row)

        lay.addSpacing(0)  # gap 1，_update_three_gaps() 会更新
        self._three_gap_indices = [1]

        # 动 + spin_n3 + 余数（自上而下：动/上/下，mod6/mod8/mod8）
        self._three_spin_labels: list[QLabel] = []
        self._three_mod_containers: list[QWidget] = []
        self._three_mod_values: list[QLabel] = []
        self._spin_n3 = self._make_spin()
        self._spin_n3.setValue(0)  # 默认动爻
        self._spin_n3.valueChanged.connect(self._run_three_auto)
        row, lbl, mod_ctn, val_lbl = self._make_spin_row("动", self._spin_n3, line_h, 6)
        self._three_spin_labels.append(lbl)
        self._three_mod_containers.append(mod_ctn)
        self._three_mod_values.append(val_lbl)
        lay.addWidget(row)

        lay.addSpacing(0)  # gap 2
        self._three_gap_indices.append(lay.count() - 1)

        self._spin_n2 = self._make_spin()
        self._spin_n2.setValue(1)  # 默认上卦
        self._spin_n2.valueChanged.connect(self._run_three_auto)
        row, lbl, mod_ctn, val_lbl = self._make_spin_row("上", self._spin_n2, line_h, 8)
        self._three_spin_labels.append(lbl)
        self._three_mod_containers.append(mod_ctn)
        self._three_mod_values.append(val_lbl)
        lay.addWidget(row)

        lay.addSpacing(0)  # gap 3
        self._three_gap_indices.append(lay.count() - 1)

        self._spin_n1 = self._make_spin()
        self._spin_n1.setValue(1)  # 默认下卦
        self._spin_n1.valueChanged.connect(self._run_three_auto)
        row, lbl, mod_ctn, val_lbl = self._make_spin_row("下", self._spin_n1, line_h, 8)
        self._three_spin_labels.append(lbl)
        self._three_mod_containers.append(mod_ctn)
        self._three_mod_values.append(val_lbl)
        lay.addWidget(row)

        lay.addSpacing(0)  # gap 4
        self._three_gap_indices.append(lay.count() - 1)

        # 底部并排按钮：随机 + 秒表（宽度=两个汉字+留白，随字号自动计算）
        fs_metrics = QFont()
        fs_metrics.setPointSize(self._font_size)
        m = QFontMetrics(fs_metrics)
        # 两个汉字的最大宽度（随机/秒表 都是2字）
        char2_w = max(m.horizontalAdvance("随机"), m.horizontalAdvance("秒表"))
        btn_h = self._gap_btn_h
        btn_gap = self._gap_sm
        each_btn_w = char2_w + self._gap_btn_pad
        total_btn_w = 2 * each_btn_w + btn_gap
        self._three_btn_h = btn_h
        self._three_btn_total_w = total_btn_w
        self._three_btn_each_w = each_btn_w

        btn_row = QWidget()
        btn_row.setObjectName("btn_row")
        btn_row.setFixedSize(total_btn_w, btn_h)
        self._three_btn_row = btn_row
        btn_lay = QHBoxLayout(btn_row)
        btn_lay.setContentsMargins(0, 0, 0, 0)
        btn_lay.setSpacing(btn_gap)

        self._btn_random = QPushButton("随机")
        self._btn_random.setFixedSize(each_btn_w, btn_h)
        self._btn_random.setStyleSheet("""
            QPushButton { padding: 4px 0px; border: 1px solid #dcdcdc; border-radius: 6px; background: #f5f5f7; color: #1d1d1f; }
            QPushButton:hover { border-color: #007aff; }
        """)
        self._btn_random.clicked.connect(self._on_time_random)
        btn_lay.addWidget(self._btn_random)

        self._btn_sw = QPushButton("秒表")
        self._btn_sw.setFixedSize(each_btn_w, btn_h)
        self._btn_sw.setStyleSheet("""
            QPushButton { padding: 4px 0px; border: 1px solid #dcdcdc; border-radius: 6px; background: #f5f5f7; color: #1d1d1f; }
            QPushButton:hover { border-color: #007aff; }
        """)
        self._btn_sw.clicked.connect(self._on_stopwatch)
        btn_lay.addWidget(self._btn_sw)

        lay.addWidget(btn_row)

        # 固定高度 = drawer 总高度
        w.setFixedHeight(name_h + 6 * line_h)

        # 初始均分间距
        self._update_three_gaps(name_h, line_h)
        return w

    def _update_three_gaps(self, name_h: int, line_h: int):
        """
        计算报数面板 5 项内容纵向间距，均分在卦图高度内

        报数面板固定高度 = name_h + 6 * line_h（与 drawer 总高一致）。
        剩余空间 = 总高 - 内容高，均分到 4 个间距位置。

        Args:
            name_h: drawer.name_area_h（卦名区域高度）
            line_h: drawer.line_h（单行爻线高度）

        调用时机：
          - _make_three_panel() 末尾首次计算
          - refresh_font_size() 中字号变更后重新计算
        """
        three = self._right_stack.widget(1)
        if three is None:
            return
        # 总高度
        total_h = name_h + 6 * line_h
        three.setFixedHeight(total_h)
        btn_h = getattr(self, "_three_btn_h", line_h)
        content_h = name_h + 3 * line_h + 1 * btn_h
        gap = max(0, (total_h - content_h) // 4)
        # 更新 4 个间距
        lay = three.layout()
        if lay is None:
            return
        for idx in self._three_gap_indices:
            item = lay.itemAt(idx)
            if item and item.spacerItem():
                item.spacerItem().changeSize(0, gap)
        lay.invalidate()

    def _make_lock_only_row(self, name_h: int) -> QWidget:
        """
        创建 Lock 复选框 + 刷新按钮的行（不显示"动爻设置"文字）

        供报数面板使用。报数面板不像手工/金钱/蓍草面板有"动爻设置"概念，
        但仍需 Lock 功能来控制 SpinBox 和按钮的启用/禁用，
        以及刷新按钮来手动触发起卦计算。

        布局：Lock 复选框 + gap_refresh + 刷新按钮(矢量图标) + stretch

        Args:
            name_h: 行固定高度(px)

        Returns:
            QWidget: 行容器（objectName="title_row"）

        调用时机：_make_three_panel() 中调用，仅一次
        """
        row = QWidget()
        row.setObjectName("title_row")
        row.setFixedHeight(name_h)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lock_cb = QCheckBox("Lock")
        lock_cb.setStyleSheet(f"QCheckBox {{ spacing: 4px; color: {self._text_color}; font-size: {self._font_size - 2}px; }}")
        lock_cb.toggled.connect(self._on_lock_toggled)
        lay.addWidget(lock_cb, 0, Qt.AlignmentFlag.AlignVCenter)
        self._lock_cbs.append(lock_cb)

        lay.addSpacing(self._gap_refresh)

        # 刷新按钮 — 矢量图标（QPainter 绘制），尺寸 = name_h * _gap_refresh_icon_scale
        icon_size = max(14, int(name_h * self._gap_refresh_icon_scale))
        self._btn_refresh = QPushButton()
        self._btn_refresh.setFlat(True)
        self._btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_refresh.setFixedSize(icon_size, icon_size)
        self._set_refresh_icon(self._text_color, icon_size)
        self._btn_refresh.clicked.connect(self._run_three_auto)
        lay.addWidget(self._btn_refresh, 0, Qt.AlignmentFlag.AlignVCenter)

        lay.addStretch()
        return row

    def _set_refresh_icon(self, color_hex: str, size: int):
        """
        用 QPainter 绘制矢量刷新图标并设为按钮图标

        绘制圆形箭头（refresh 图标）：圆弧 + 箭头尖，无锯齿无边框，
        纯矢量路径，颜色和尺寸随参数动态适配。

        Args:
            color_hex: CSS hex 颜色字符串（如 "#1d1d1f" 或 "#ffffff"）
            size:      图标尺寸(px)，正方形

        调用时机：
          - _make_lock_only_row() 中首次设置
          - refresh_font_size() 中字号变更后重设（尺寸跟随 name_h）
          - refresh_text_color() 中颜色变更后重设
        """
        if not hasattr(self, "_btn_refresh") or self._btn_refresh is None:
            return
        btn = self._btn_refresh
        btn.setFixedSize(size, size)

        px = QPixmap(size * 2, size * 2)  # @2x 保证 retina 清晰
        px.fill(Qt.GlobalColor.transparent)
        qp = QPainter(px)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor(color_hex)
        c = size  # 逻辑尺寸（@1x）
        r = c * 0.38      # 圆弧半径
        cx, cy = c, c     # @2x 画布中心
        pen_w = max(1.5, c * 0.14)  # 线宽随尺寸缩放

        pen = QPen(color, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        qp.setPen(pen)
        qp.setBrush(Qt.BrushStyle.NoBrush)

        # ── 圆弧：从 50° 画到 360°，留 50° 缺口 ──
        from PySide6.QtCore import QRectF
        qp.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), 50 * 16, 310 * 16)

        # ── 箭头（在圆弧 50° 方向，指向右上）──
        import math
        arrow_deg = 50
        arrow_rad = math.radians(arrow_deg)
        tip_x = cx + r * math.cos(arrow_rad)
        tip_y = cy - r * math.sin(arrow_rad)

        left_dir = arrow_rad + math.radians(28)
        right_dir = arrow_rad - math.radians(28)
        arrow_len = c * 0.16

        left_x = tip_x - arrow_len * math.cos(left_dir)
        left_y = tip_y + arrow_len * math.sin(left_dir)
        right_x = tip_x - arrow_len * math.cos(right_dir)
        right_y = tip_y + arrow_len * math.sin(right_dir)

        path = QPainterPath()
        path.moveTo(tip_x, tip_y)
        path.lineTo(left_x, left_y)
        path.lineTo(right_x, right_y)
        path.closeSubpath()
        qp.setPen(Qt.PenStyle.NoPen)
        qp.setBrush(color)
        qp.drawPath(path)

        qp.end()

        from PySide6.QtGui import QIcon
        btn.setIcon(QIcon(px))
        btn.setIconSize(px.size() / 2)  # @2x → @1x 显示

    def _make_mod_display(self, mod_val: int) -> tuple[QWidget, QLabel]:
        """
        创建两行余数显示区域

        上行：固定文字 "mod N"（N = mod_val）
        下行：实时显示的余数值（由 spin.value() % mod_val 动态更新）

        两行小字居中排列，间距随字号自动调节。

        Args:
            mod_val: 取余基数（6 或 8）

        Returns:
            tuple[QWidget, QLabel]:
              - QWidget: 容器（固定高度 = line_h）
              - QLabel: 下行余数值标签（用于后续动态更新 setText）

        调用时机：_make_spin_row() 中调用
        """
        fs = self._font_size
        container = QWidget()
        container.setFixedHeight(self._drawer.line_h)
        inner = QVBoxLayout(container)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(max(1, int(fs * 0.08)))

        top = QLabel(f"mod {mod_val}")
        top.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.setStyleSheet(f"QLabel {{ color: {self._text_color}; font-size: {fs - self._gap_mod_top_fs}px; }}")

        bottom = QLabel("")
        bottom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom.setStyleSheet(f"QLabel {{ color: {self._text_color}; font-size: {fs - self._gap_mod_val_fs}px; }}")

        inner.addStretch()
        inner.addWidget(top)
        inner.addWidget(bottom)
        inner.addStretch()
        return container, bottom

    def _make_spin_row(self, label: str, spin: QSpinBox, line_h: int, mod_val: int = 0) -> tuple[QWidget, QLabel, QWidget, QLabel]:
        """
        创建标签 + QSpinBox + 余数显示 行，固定高度

        例如："动 [ 0 ] mod6 \n 0" 其中 spin 为数字输入框，余数区显示 mod 和 取余值。

        Args:
            label:   标签文字（"动"/"上"/"下"）
            spin:    已创建的 QSpinBox 控件
            line_h:  行固定高度(px)
            mod_val: 取余基数（0=不显示余数区域，6=mod6动爻，8=mod8卦数）

        Returns:
            tuple[QWidget, QLabel, QWidget, QLabel]:
              - QWidget: 行容器
              - QLabel:  标签控件（用于后续样式更新）
              - QWidget: 余数容器（mod_val=0 时为空容器）
              - QLabel:  余数值标签（用于后续动态更新 setText）

        调用时机：_make_three_panel() 中调用 3 次（动/上/下）
        """
        row = QWidget()
        row.setFixedHeight(line_h)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        lbl = QLabel(label)
        lbl.setFixedHeight(line_h)
        lbl.setStyleSheet(f"QLabel {{ color: {self._text_color}; }}")
        lay.addWidget(lbl)
        lay.addWidget(spin, 0, Qt.AlignmentFlag.AlignVCenter)

        mod_container, val_lbl = self._make_mod_display(mod_val)
        if mod_val > 0:
            val_lbl.setText(str(spin.value() % mod_val))
        lay.addWidget(mod_container)
        lay.addStretch()
        return row, lbl, mod_container, val_lbl

    def _make_spin(self) -> QSpinBox:
        """
        创建统一样式的 QSpinBox

        配置：范围 0-999，无上下按钮（NoButtons），文字居中，宽度58px

        Returns:
            QSpinBox: 配置好的数字输入框

        调用时机：_make_three_panel() 中调用 3 次（为动/上/下各创建一个）
        """
        spin = QSpinBox()
        spin.setRange(0, 999)
        spin.setFixedWidth(58)
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin.setStyleSheet(f"""
            QSpinBox {{ padding: 3px 6px; border: 1px solid #dcdcdc; border-radius: 4px; background: transparent; color: {self._text_color}; }}
            QSpinBox:focus {{ border-color: #007aff; }}
        """)
        return spin

    # ═══════════════════════════════════════════════════════════
    #  右侧面板：金钱/蓍草（共用渲染器，仅下拉选项不同）
    # ═══════════════════════════════════════════════════════════

    # 金钱卦下拉选项：正面数-爻名(变爻标记)
    COIN_OPTIONS = ["3-老阳(o)", "2-少阴", "1-少阳", "0-老阴(x)"]
    # 蓍草卦下拉选项：蓍草数-爻名(变爻标记)
    YARROW_OPTIONS = ["9-老阳(o)", "8-少阴", "7-少阳", "6-老阴(x)"]

    def _combo_val(self, combo: QComboBox) -> int:
        """
        从下拉文本中提取数值（如 '3-老阳(o)' → 3）

        Args:
            combo: 下拉框控件

        Returns:
            int: 数值（金钱卦 0-3，蓍草卦 6-9）

        调用时机：所有需要从 combo 读取数值的地方
        """
        return int(combo.currentText().split("-")[0])

    def _is_yang_val(self, val: int, mode: str) -> bool:
        """
        判断数值是否为阳爻

        Args:
            val:  爻数值（金钱卦 0-3，蓍草卦 6-9）
            mode: 起卦方式 ("coin" 或 "yarrow")

        Returns:
            bool: True=阳爻（金钱卦1/3, 蓍草卦7/9）
        """
        return val in (1, 3) if mode == "coin" else val in (7, 9)

    def _is_changing_val(self, val: int, mode: str) -> bool:
        """
        判断数值是否为变爻（老阳/老阴）

        Args:
            val:  爻数值（金钱卦 0-3，蓍草卦 6-9）
            mode: 起卦方式 ("coin" 或 "yarrow")

        Returns:
            bool: True=变爻（金钱卦0老阴/3老阳, 蓍草卦6老阴/9老阳）
        """
        return val in (0, 3) if mode == "coin" else val in (6, 9)

    # 点击卦图翻转阴阳时的映射表（保留变爻状态）
    # 老阳↔老阴（变爻翻转），少阳↔少阴（静爻翻转）
    _COIN_TOGGLE = {0: 3, 3: 0, 1: 2, 2: 1}
    _YARROW_TOGGLE = {6: 9, 9: 6, 7: 8, 8: 7}
    # 点击"动"复选框翻转动静时的映射表（保留阴阳属性）
    # 老阳↔少阳（变静），老阴↔少阴（变静）
    _COIN_CHANGING = {0: 2, 2: 0, 1: 3, 3: 1}
    _YARROW_CHANGING = {6: 8, 8: 6, 7: 9, 9: 7}

    def _on_changing_toggled(self, ui_idx: int, _checked: bool):
        """
        金钱/蓍草面板"动"复选框点击 → 翻转动静状态

        使用 _COIN_CHANGING / _YARROW_CHANGING 映射表：
          老阳↔少阳（保留阳属性，切换变/静）
          老阴↔少阴（保留阴属性，切换变/静）

        Args:
            ui_idx: 复选框在 _lines_cbs 中的索引 (0=上爻..5=初爻)
            _checked: 未使用的勾选状态（通过 combo 值判断，不依赖 checked 状态）

        调用时机：金钱/蓍草面板"动"复选框 toggled 信号触发
        """
        if self._current_method not in ("coin", "yarrow"):
            return
        toggle_map = self._COIN_CHANGING if self._current_method == "coin" else self._YARROW_CHANGING
        combo = self._lines_inputs[ui_idx]
        old_val = self._combo_val(combo)
        new_val = toggle_map.get(old_val)
        if new_val is None:
            return
        for k in range(combo.count()):
            if int(combo.itemText(k).split("-")[0]) == new_val:
                combo.setCurrentIndex(k)
                break

    def _on_lock_toggled(self, checked: bool):
        """
        Lock 复选框切换 → 锁定/解锁所有交互控件

        Lock 机制设计目的：
          起卦完成后锁定所有交互，防止误操作破坏已有卦象。
          锁定时所有输入控件禁用（灰色不可操作），方法选择器禁用，
          卦图不可点击，动爻复选框显示自定义深灰底白勾 indicator。

        锁定范围：
          1. 卦图（HexagramDrawer）：setEnabled + set_clickable(False)
          2. 动爻复选框：应用自定义 indicator 样式
          3. 手工面板：6个动爻复选框
          4. 金钱/蓍草面板：6个"动"复选框 + 6个下拉框
          5. 报数面板：3个SpinBox + 随机/秒表按钮
          6. 方法选择器：4个dot + 4个标签按钮
          7. 起卦标题按钮

        Lock 复选框同步机制：
          遍历 self._lock_cbs 列表，用 blockSignals 静默设置所有
          Lock 复选框为相同状态，避免循环触发。

        Args:
            checked: True=锁定, False=解锁

        调用时机：任意 Lock 复选框 toggled 信号触发
        """
        self._lock_checked = checked
        # ── 第1步：同步所有 Lock 复选框（blockSignals 防止循环触发）──
        for cb in self._lock_cbs:
            if cb.isChecked() != checked:
                cb.blockSignals(True)
                cb.setChecked(checked)
                cb.blockSignals(False)

        enabled = not checked  # checked=True → enabled=False（锁定）

        # ── 第2步：卦图 ──
        self._drawer.setEnabled(enabled)
        if not enabled:
            self._drawer.set_clickable(False)           # 锁定时不可点击
        else:
            self._drawer.set_clickable(self._current_method in ("manual", "coin", "yarrow"))  # 解锁后恢复可点击（报数模式除外）

        # ── 第3步：动爻复选框 indicator 样式 ──
        self._apply_lock_indicator()

        # ── 第4步：手工面板复选框 ──
        for cb in self._manual_cbs:
            cb.setEnabled(enabled)
        if hasattr(self, "_single_line_cb") and self._single_line_cb is not None:
            self._single_line_cb.setEnabled(enabled)
        # ── 第5步：金钱/蓍草面板复选框 + 下拉框 ──
        for cb in getattr(self, "_lines_cbs", []):
            cb.setEnabled(enabled)
        for combo in getattr(self, "_lines_inputs", []):
            combo.setEnabled(enabled)

        # ── 第6步：报数面板 spin + 按钮 ──
        self._spin_n1.setEnabled(enabled)
        self._spin_n2.setEnabled(enabled)
        self._spin_n3.setEnabled(enabled)
        if hasattr(self, "_btn_random"):
            self._btn_random.setEnabled(enabled)
        if hasattr(self, "_btn_sw"):
            self._btn_sw.setEnabled(enabled)
        if hasattr(self, "_btn_refresh"):
            self._btn_refresh.setEnabled(enabled)

        # ── 第7步：方法选择器（dot + 标签）──
        for dot in self._dots:
            dot.setEnabled(enabled)

        # ── 第8步：起卦标题按钮 ──
        self._title_label.setEnabled(enabled)

    def _ensure_lock_chk_image(self):
        """
        确保 Lock 勾图已生成到 usrCfg/_lock_chk.png

        勾图：14x14 透明底 + 深灰圆角矩形 + 白色勾路径。
        仅在首次调用时绘制并保存为 PNG，后续调用返回缓存路径。

        Returns:
            str: 勾图文件绝对路径

        调用时机：
          - _init_ui() 末尾预生成
          - _apply_lock_indicator() 中获取路径（首次）
        """
        try:
            return self.__lock_chk_path
        except AttributeError:
            pass
        d = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "usrCfg")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "_lock_chk.png")
        if not os.path.exists(p):
            px = QPixmap(14, 14)
            px.fill(Qt.GlobalColor.transparent)
            qp = QPainter(px)
            qp.setRenderHint(QPainter.RenderHint.Antialiasing)
            qp.setBrush(QColor("#666"))
            qp.setPen(Qt.PenStyle.NoPen)
            qp.drawRoundedRect(0, 0, 14, 14, 3, 3)
            qp.setPen(QPen(QColor("#fff"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            g = QPainterPath()
            g.moveTo(3.5, 7)
            g.lineTo(6.5, 10)
            g.lineTo(11, 4.5)
            qp.drawPath(g)
            qp.end()
            px.save(p, "PNG")
        self.__lock_chk_path = p
        return p

    def _apply_lock_indicator(self):
        """
        Lock 开启/关闭时更新动爻 checkbox indicator 样式

        Lock 开启（_lock_checked=True）：
          所有动爻复选框使用自定义 indicator — 透明底 + 灰色边框 + 深灰底白勾图。
          视觉上表现为"灰化"的勾选状态，提示用户当前锁定中不可操作。

        Lock 关闭（_lock_checked=False）：
          移除自定义 indicator CSS，恢复 Qt 原生蓝色勾选样式。

        调用时机：
          - _on_lock_toggled() 中 Lock 状态切换时
          - refresh_font_size() 末尾重新挂载 indicator
          - refresh_text_color() 末尾重新挂载 indicator
        """
        fs = self._font_size
        if self._lock_checked:
            chk_path = self._ensure_lock_chk_image()
            indicator_css = f"""
    QCheckBox::indicator,
    QCheckBox::indicator:disabled {{
        width: 14px; height: 14px;
        border: 1px solid #999; border-radius: 3px;
        background: transparent;
    }}
    QCheckBox::indicator:checked,
    QCheckBox::indicator:checked:disabled {{
        image: url({chk_path});
    }}"""
        else:
            indicator_css = ""

        manual_base = f"QCheckBox {{ spacing: 8px; color: {self._text_color}; }}"
        lines_base = f"QCheckBox {{ spacing: {self._gap_cb_text}px; color: {self._text_color}; font-size: {fs - 2}px; }}"
        for cb in self._manual_cbs:
            cb.setStyleSheet(manual_base + indicator_css)
        for cb in getattr(self, "_lines_cbs", []):
            cb.setStyleSheet(lines_base + indicator_css)

    def _on_drawer_toggled(self, line_idx: int):
        """
        卦图点击 → 翻转该爻阴阳

        手工模式：翻转阴阳后重新计算
        金钱/蓍草模式：同步更新下拉框（保留变爻状态）

        Args:
            line_idx: drawer 爻索引 (0=初爻/bottom..5=上爻/top)

        调用时机：HexagramDrawer.line_toggled 信号触发
        """
        if self._current_method == "manual":
            # drawer 内部已翻转阴阳（mousePressEvent），直接重算
            # 不修改 _changing_lines — 点击卦图只改阴阳，不动复选框
            self._on_calc()
            return

        if self._current_method not in ("coin", "yarrow"):
            return
        toggle_map = self._COIN_TOGGLE if self._current_method == "coin" else self._YARROW_TOGGLE
        combo_idx = 5 - line_idx  # drawer[0]=初爻(bottom) → combo[5]
        combo = self._lines_inputs[combo_idx]
        old_val = self._combo_val(combo)
        new_val = toggle_map.get(old_val)
        if new_val is None:
            return
        # 找到 new_val 在 options 中的索引并静默设置（combo 信号会触发 _on_combo_changed 自动起卦）
        for k in range(combo.count()):
            if int(combo.itemText(k).split("-")[0]) == new_val:
                combo.setCurrentIndex(k)
                break

    def _on_combo_changed(self):
        """
        下拉框值变化 → 实时更新卦图 + 动爻复选框 + 自动起卦

        流程：
          1. _sync_coin_yarrow_display() → 更新卦图阴阳 + 动爻复选框
          2. _on_calc() → 执行起卦计算并显示结果

        调用时机：金钱/蓍草面板任意 QComboBox.currentIndexChanged 信号触发
        """
        self._sync_coin_yarrow_display()
        self._on_calc()

    def _sync_coin_yarrow_display(self):
        """
        同步金钱/蓍草下拉值 → 卦图阴阳 + 动爻复选框

        流程：
          1. 读取6个 combo 数值（从上而下 UI 顺序）
          2. reverse() 转换为从下而上（初爻→上爻）
          3. 判断每爻阴阳 → drawer.set_lines()
          4. 判断每爻是否变爻 → 设置"动"复选框勾选状态（blockSignals 防循环）

        调用时机：
          - _on_combo_changed() 中每次 combo 变化
          - _update_lines_combo_options() 中切换模式后
          - _switch_method() 中切换到金钱/蓍草模式
          - _sync_controls_to_changing_lines() 中跨模式同步
        """
        mode = self._current_method
        if mode not in ("coin", "yarrow"):
            return

        # 读取 6 爻数值（从下而上：[初爻..上爻]），与 UI 顺序（从上而下）相反
        vals = [self._combo_val(self._lines_inputs[j]) for j in range(6)]
        vals.reverse()

        yang = [self._is_yang_val(v, mode) for v in vals]
        self._drawer.set_lines(yang)

        # 复选框 disabled，用 blockSignals 避免 setChecked 触发无用信号
        for j in range(6):
            val = self._combo_val(self._lines_inputs[j])
            is_changing = self._is_changing_val(val, mode)
            self._lines_cbs[j].blockSignals(True)
            self._lines_cbs[j].setChecked(is_changing)
            self._lines_cbs[j].blockSignals(False)

    def _update_lines_combo_options(self, sync_final=True):
        """
        切换金钱/蓍草模式时更新所有下拉框选项

        跨模式映射规则（cross_map）：
          金钱卦 0,1,2,3 ↔ 蓍草卦 6,7,8,9
          老阴 0↔6, 少阳 1↔7, 少阴 2↔8, 老阳 3↔9

        处理流程：
          1. 读取当前 combo 值（切换前）
          2. 清空所有选项，填充新模式选项
          3. 通过 cross_map 将旧值映射到新模式对应值
          4. 如找不到匹配则默认选中 index 2（少阳/少阴）
          5. 如 sync_final=True，调用 _sync_coin_yarrow_display() 同步显示

        Args:
            sync_final: 是否在更新选项后同步卦图显示。
                       金钱↔蓍草互切时由 _switch_method 手动控制，
                       设为 False 避免重复同步。

        调用时机：
          - _switch_method() 中切换到 coin/yarrow 模式时
          - _sync_controls_to_changing_lines() 中更新选项后
        """
        mode = self._current_method
        options = self.COIN_OPTIONS if mode == "coin" else self.YARROW_OPTIONS
        for combo in self._lines_inputs:
            combo.blockSignals(True)
            old_val = self._combo_val(combo) if combo.count() > 0 else None
            combo.clear()
            combo.addItems(options)
            if old_val is not None:
                cross_map = {0: 6, 1: 7, 2: 8, 3: 9, 6: 0, 7: 1, 8: 2, 9: 3}
                mapped = cross_map.get(old_val, 2 if mode == "coin" else 7)
                found = False
                for k, opt in enumerate(options):
                    if int(opt.split("-")[0]) == mapped:
                        combo.setCurrentIndex(k)
                        found = True
                        break
                if not found:
                    combo.setCurrentIndex(2)
            else:
                combo.setCurrentIndex(2)
            combo.blockSignals(False)
        if sync_final:
            self._sync_coin_yarrow_display()

    def _make_lines_panel(self) -> QWidget:
        """
        构建金钱/蓍草共用面板

        布局：动爻设置标题行 + Lock复选框
              + 6行（"动"复选框 + 下拉框），每行用 QWidget 容器包裹，
                setFixedHeight(line_h) 精确控制行高

        金钱卦和蓍草卦共用一个面板：
          - 初始加载 COIN_OPTIONS（3-老阳/2-少阴/1-少阳/0-老阴）
          - 切换到蓍草模式时 _update_lines_combo_options() 替换为 YARROW_OPTIONS
          - combo padding 压缩（3px 6px + border 1px）确保行高不受 combo 影响
          - 每行默认选中"少阳"（index 2），combo 用 AdjustToContents 自适应宽度

        Returns:
            QWidget: 金钱/蓍草共用面板（objectName="lines_panel"）

        调用时机：_build_right_panels() 中调用，仅一次
        """
        w = QWidget()
        w.setObjectName("lines_panel")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 4)
        lay.setSpacing(0)

        # "动爻设置" 标题行 + Lock 复选框
        name_h = self._drawer.name_area_h
        self._lines_title_row = self._make_title_row(name_h)
        lay.addWidget(self._lines_title_row)

        line_h = self._drawer.line_h

        self._lines_cbs: list[QCheckBox] = []
        self._lines_inputs: list[QComboBox] = []
        self._lines_rows: list[QWidget] = []

        for idx, i in enumerate(range(5, -1, -1)):
            row_wrapper = QWidget()
            row_wrapper.setFixedHeight(line_h)
            row = QHBoxLayout(row_wrapper)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(self._gap_cb_combo)

            cb = QCheckBox("动")
            cb.toggled.connect(lambda checked, ui_idx=idx: self._on_changing_toggled(ui_idx, checked))
            cb.setStyleSheet(f"""
                QCheckBox {{
                    spacing: {self._gap_cb_text}px;
                    color: {self._text_color};
                    font-size: {self._font_size - 2}px;
                }}
            """)
            self._lines_cbs.append(cb)
            row.addWidget(cb)

            combo = QComboBox()
            combo.addItems(self.COIN_OPTIONS)
            combo.setCurrentIndex(2)  # 默认选中"少阳"
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
            combo.setStyleSheet(f"""
                QComboBox {{
                    padding: 3px 6px;
                    border: 1px solid #dcdcdc;
                    border-radius: 4px;
                    background: transparent;
                    color: {self._text_color};
                    font-size: {self._font_size - 1}px;
                }}
                QComboBox:focus {{ border-color: #007aff; }}
                QComboBox::drop-down {{ width: 16px; }}
                QComboBox QAbstractItemView {{ {self._dropdown_style()} }}
            """)
            combo.currentIndexChanged.connect(self._on_combo_changed)
            combo.view().setMinimumWidth(130)
            self._lines_inputs.append(combo)
            row.addWidget(combo, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addStretch()
            self._lines_rows.append(row_wrapper)
            lay.addWidget(row_wrapper)

        lay.addStretch()
        return w

    # ═══════════════════════════════════════════════════════════
    #  连接信号
    # ═══════════════════════════════════════════════════════════

    def _connect_all(self):
        """
        连接所有信号槽

        信号映射：
          - QButtonGroup.buttonClicked → _on_dot_clicked（方法dot点击）
          - 起卦标题按钮.clicked → _on_calc（手动触发起卦）
          - HexagramDrawer.line_toggled → _on_drawer_toggled（卦图点击翻转）

        调用时机：__init__() 中调用，仅一次
        """
        self._btn_group.buttonClicked.connect(self._on_dot_clicked)
        # title_label 已通过 installEventFilter 处理，见 eventFilter()
        self._drawer.line_toggled.connect(self._on_drawer_toggled)

    # ═══════════════════════════════════════════════════════════
    #  方法切换
    # ═══════════════════════════════════════════════════════════

    def _on_dot_clicked(self, btn):
        """
        方法选择 dot 按钮点击 → 切换到对应起卦方式

        Args:
            btn: 被点击的 _DotButton，通过 QButtonGroup.id() 获取 index

        调用时机：QButtonGroup.buttonClicked 信号触发
        """
        idx = self._btn_group.id(btn)
        key = METHODS[idx]["key"]
        self._switch_method(key)

    def _switch_method(self, key: str):
        """
        切换到指定起卦方式

        核心流程：
          1. 记录 prev → self._current_method 更新
          2. 切换 QStackedWidget 到对应面板
          3. 处理 Lock 状态下的卦图可点击性
          4. 将当前卦图和动爻状态同步到新面板控件：
             - 手工模式：从 _changing_lines 恢复复选框勾选
             - 报数模式：用当前 spin 值直接起卦
             - 金钱/蓍草模式：更新下拉选项 + 初始化值
               (金钱↔蓍草互切时通过 cross_map 保留已有值)
          5. 持久化当前方法到 usrCfg

        金钱↔蓍草互切特殊处理：
          当从 coin 切到 yarrow（或反之），_update_lines_combo_options 已通过
          cross_map 正确映射各爻值，不需要重新从 _changing_lines 初始化。

        Args:
            key: 起卦方式标识 ("manual"/"three"/"coin"/"yarrow")

        调用时机：
          - _on_dot_clicked() 中 dot 按钮点击
          - _init_ui() 末尾加载上次起卦方式
        """
        # ── 第1步：记录切换前的方法，更新当前方法 ──
        prev = self._current_method
        self._prev_method = prev
        self._current_method = key
        # ── 第2步：切换到对应 QStackedWidget 面板 ──
        # manual→0, three→1, coin/yarrow→2（共用面板）
        idx = {"manual": 0, "three": 1, "coin": 2, "yarrow": 2}[key]
        self._right_stack.setCurrentIndex(idx)

        # ── 第3步：处理 Lock 状态下的卦图可点击性 ──
        # Lock 时一律不可点击；解锁后报数模式不可点击，其余模式可点击
        locked = any(cb.isChecked() for cb in self._lock_cbs)
        self._drawer.set_clickable(key in ("manual", "coin", "yarrow") and not locked)

        # ── 第4步：同步控件到当前卦图状态（保留已有卦象和动爻）──
        yang = self._drawer.yang_lines()  # 获取当前卦图的阴阳状态（6个bool）
        if key == "manual":
            # 手工模式：checkbox = 动爻标记，从 _changing_lines 恢复
            # mapping: i=0→线0(初爻)对应cb[5], i=5→线5(上爻)对应cb[0]
            # _changing_lines 存的是爻位(1=初爻..6=上爻)
            for i in range(6):
                cb = self._manual_cbs[5 - i]
                cb.blockSignals(True)
                cb.setChecked((i + 1) in self._changing_lines)
                cb.blockSignals(False)
        elif key == "three":
            # 报数模式：用当前 spin 值直接起卦，动爻由 n3 mod6 决定
            self._run_three_auto()
        elif key in ("coin", "yarrow"):
            self._update_lines_combo_options(sync_final=False)
            # 仅当从非金钱/蓍草模式切过来时，用 _changing_lines + yang 初始化值
            # 金钱↔蓍草互切时 _update_lines_combo_options 已通过 cross_map 正确映射，不要覆盖
            if prev not in ("coin", "yarrow"):
                for i in range(6):
                    combo = self._lines_inputs[5 - i]
                    combo.blockSignals(True)
                    line_num = i + 1  # i=0→初爻(1), i=5→上爻(6)
                    is_yang = yang[i]
                    is_changing = line_num in self._changing_lines
                    if key == "coin":
                        val = 3 if (is_yang and is_changing) else (0 if (not is_yang and is_changing) else (1 if is_yang else 2))
                    else:
                        val = 9 if (is_yang and is_changing) else (6 if (not is_yang and is_changing) else (7 if is_yang else 8))
                    for k in range(combo.count()):
                        if int(combo.itemText(k).split("-")[0]) == val:
                            combo.setCurrentIndex(k)
                            break
                    combo.blockSignals(False)
            self._sync_coin_yarrow_display()

        # ── 第5步：持久化当前方法到 usrCfg ──
        config_manager.set("general", "qigua_method", value=key)

        # ── 第6步：按起卦方法自动切换算卦方法 + 状态栏 Info ──
        if hasattr(self, "_suangua_panel") and self._suangua_panel is not None:
            single_mode = hasattr(self, "_single_line_cb") and self._single_line_cb.isChecked()
            mgr = getattr(self.window(), "_statusbar_mgr", None)
            if key in ("coin", "yarrow") and not single_mode:
                self._suangua_panel.switch_method("liuyao")
                label = METHODS[next(i for i, m in enumerate(METHODS) if m["key"] == key)]["label"]
                if mgr:
                    mgr.show_status(f'<span style="color:#007aff;">[Info] {label}起卦，切换为六爻</span>')
                    QTimer.singleShot(5000, mgr.reset_status)
            elif key == "three":
                self._suangua_panel.switch_method("meihua")
                if mgr:
                    mgr.show_status('<span style="color:#007aff;">[Info] 报数起卦，切换为梅花</span>')
                    QTimer.singleShot(5000, mgr.reset_status)
            elif key == "manual":
                if mgr:
                    mgr.show_status('<span style="color:#007aff;">[Info] 手动指定起卦</span>')
                    QTimer.singleShot(5000, mgr.reset_status)

    # ═══════════════════════════════════════════════════════════
    #  字体大小响应（刷新链入口）
    # ═══════════════════════════════════════════════════════════

    def refresh_font_size(self, font_size: int):
        """
        全局字体大小变更时调用，重算行高并刷新所有布局

        这是外观刷新链的核心方法，调用链：
          appearance_manager.apply_appearance()
            → yijing_viewer.refresh_font_size()
              → qigua_panel.refresh_font_size()          ← 本方法
                → drawer.set_font_size()                  (更新卦图尺寸)
                → _update_panel_layout() × 4              (更新所有面板行高)
                → _update_three_gaps()                    (更新报数面板间距)
                → _update_header_alignment()              (更新header标签间距)
                → _update_frame_max_width()               (更新边框最大宽度)
                → _apply_lock_indicator()                 (重新挂载Lock indicator)

        刷新范围（按执行顺序）：
          1. 更新 drawer 尺寸（卦图重绘）
          2. 重算所有间距（以 line_h 为基准）
          3. 更新标题按钮（字号+4 + 最小宽度）
          4. 更新金钱/蓍草 combo+checkbox 字号 + 行内横向间距
          5. 更新所有面板标题行字体 + Lock checkbox 样式
          6. 更新 root layout margin + drawer横向间距 + header间距
          7. 更新圆角矩形边框最大宽度
          8. 更新 header 方法标签字号
          9. 更新 footer 按钮间距 + 结果文字间距
          10. 更新所有右侧面板行高 (_update_panel_layout × 4)
          11. 更新报数面板间距均分 + 按钮尺寸 + 余数标签字号
          12. 更新报数面板 spin 样式
          13. 重新挂载 Lock indicator

        Args:
            font_size: 全局字体大小(pt)，由 appearance_manager 从配置读取后传入

        调用时机：
          - 用户在设置面板修改字号后，appearance_manager 触发刷新链
          - _init_ui() 中不调用（初始化时已用默认字号构建）
        """
        self._font_size = font_size

        # ── 第1步：更新 drawer 尺寸（卦图重绘）──
        self._drawer.set_font_size(font_size)
        line_h = self._drawer.line_h
        name_h = self._drawer.name_area_h

        # ── 第2步：重算所有间距（以 line_h 为基准，保证比例一致）──
        self._gap_xs = max(2, int(line_h * 0.12))
        self._gap_sm = max(4, int(line_h * 0.25))
        self._gap_md = max(6, int(line_h * 0.45))
        self._compute_cb_gaps()  # 复选框间距跟随字号重算

        # ── 第3步：更新标题按钮（字号 +4，与设置面板侧边栏标题同级）──
        self._title_label.setFixedHeight(line_h)
        tf4 = QFont()
        tf4.setPointSize(font_size + 4)
        tf4.setBold(True)
        tfm = QFontMetrics(tf4)
        self._title_label.setMinimumWidth(tfm.horizontalAdvance("起卦") + 4)
        self._title_label.setStyleSheet(f"""
            QPushButton {{
                font-size: {font_size + 4}px;
                font-weight: bold;
                color: #007aff;
                border: none;
                background: transparent;
                text-align: left;
            }}
            QPushButton:hover {{ color: #0056cc; }}
        """)

        # ── 第4步：更新金钱/蓍草 combo + checkbox 字号 ──
        cb_style = f"""
            QCheckBox {{ spacing: {self._gap_cb_text}px; color: {self._text_color}; font-size: {font_size - 2}px; }}
        """
        combo_style = f"""
            QComboBox {{
                padding: 3px 6px;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                background: transparent;
                color: {self._text_color};
                font-size: {font_size - 1}px;
            }}
            QComboBox:focus {{ border-color: #007aff; }}
            QComboBox::drop-down {{ width: 16px; }}
            QComboBox QAbstractItemView {{ {self._dropdown_style()} }}
        """
        for cb in getattr(self, "_lines_cbs", []):
            cb.setStyleSheet(cb_style)
        for combo in getattr(self, "_lines_inputs", []):
            combo.setStyleSheet(combo_style)

        # ── 第5步：更新金钱/蓍草行内横向间距 ──
        for row_wrapper in getattr(self, "_lines_rows", []):
            inner = row_wrapper.layout()
            if inner is not None:
                inner.setSpacing(self._gap_cb_combo)

        # ── 第6步：更新手工/金钱/蓍草/报数面板的标题行（QFont 与 drawer 字体度量一致）──
        lock_style = f"QCheckBox {{ spacing: 4px; color: {self._text_color}; font-size: {font_size - 2}px; }}"
        for row_attr in ("_manual_title_row", "_lines_title_row", "_three_title_row"):
            row = getattr(self, row_attr, None)
            if row is None:
                continue
            row.setFixedHeight(name_h)
            lay = row.layout()
            if lay is None:
                continue
            for j in range(lay.count()):
                wgt = lay.itemAt(j).widget()
                if isinstance(wgt, QLabel):
                    tf2 = QFont()
                    tf2.setPointSize(font_size)
                    tf2.setBold(True)
                    wgt.setFont(tf2)
                    wgt.setStyleSheet(f"QLabel {{ color: {self._text_color}; }}")
                elif isinstance(wgt, QCheckBox):
                    wgt.setStyleSheet(lock_style)
        # 刷新按钮图标（矢量绘制，字号变更时尺寸跟随 name_h 等比缩放）
        if hasattr(self, "_btn_refresh") and self._btn_refresh is not None:
            icon_size = max(14, int(name_h * self._gap_refresh_icon_scale))
            self._set_refresh_icon(self._text_color, icon_size)
        # 更新手工面板 shangyao/single_line 复选框字号和样式
        cb_font2 = QFont()
        cb_font2.setPointSize(font_size)
        if hasattr(self, "_shangyao_cb") and self._shangyao_cb is not None:
            self._shangyao_cb.setFont(cb_font2)
            self._shangyao_cb.setFixedHeight(line_h)
            self._shangyao_cb.setStyleSheet(f"QCheckBox {{ spacing: 8px; color: {self._text_color}; }}")
        if hasattr(self, "_single_line_cb") and self._single_line_cb is not None:
            self._single_line_cb.setFont(cb_font2)
            self._single_line_cb.setFixedHeight(line_h)
            self._single_line_cb.setStyleSheet(f"QCheckBox {{ spacing: 4px; color: {self._text_color}; }}")
        root = self.layout()
        if root:
            root.setContentsMargins(0, 0,
                                    self._gap_xs, self._gap_sm)

        # ── 第7步：更新 drawer↔面板横向间距 ──
        self._content_layout.setSpacing(self._gap_drawer)

        # ── 第8步：更新 header→内容区间距 ──
        if hasattr(self, "_frame_layout"):
            hdr_spacer = self._frame_layout.itemAt(1)
            if hdr_spacer and hdr_spacer.spacerItem():
                hdr_spacer.spacerItem().changeSize(0, self._gap_xs)

        # ── 第9步：更新 header 标题→dot 间距 + 标签间对齐间距 + 标签字号 ──
        item1 = self._header_layout.itemAt(1)
        if item1 and item1.spacerItem():
            item1.spacerItem().changeSize(self._gap_md, 0)
        self._update_header_alignment()

        # ── 第10步：圆角矩形右边界跟随字号重算 ──
        if hasattr(self, "_border_frame"):
            self._update_frame_max_width()

        for lbl in self._header_labels:
            lbl.setStyleSheet(f"""
                QPushButton {{
                    color: #86868b; border: none; background: transparent;
                    font-size: {font_size}px;
                }}
                QPushButton:hover {{ color: {self._text_color}; }}
            """)

        # ── 第11步：更新 footer 按钮间距 ──
        self._footer_layout.setSpacing(self._gap_sm)

        # ── 第12步：更新结果文字和判断文字的垂直间距 ──
        if hasattr(self, "_frame_layout"):
            # 索引: 3=result_spacer, 5=judgment_spacer
            for idx, gap in ((3, self._gap_result_top), (5, self._gap_judgment_top)):
                item = self._frame_layout.itemAt(idx)
                if item and item.spacerItem():
                    item.spacerItem().changeSize(0, gap)

        # ── 第12.5步：更新动爻判断文字字号 ──
        if hasattr(self, "_label_judgment") and self._label_judgment is not None:
            self._label_judgment.setStyleSheet(
                f"QLabel {{ color: {self._text_color}; font-size: {font_size + self._fs_judgment}px; }}")

        # ── 第13步：更新所有右侧面板的行高和顶部边距 ──
        for panel_idx in range(self._right_stack.count()):
            w = self._right_stack.widget(panel_idx)
            self._update_panel_layout(w, line_h, name_h)

        # ── 第14步：报数面板间距均分 + 并排按钮尺寸 + 余数两行标签字号 ──
        if hasattr(self, "_three_gap_indices"):
            self._three_btn_h = self._gap_btn_h
            fm_btn = QFont()
            fm_btn.setPointSize(font_size)
            m_btn = QFontMetrics(fm_btn)
            char2_w_btn = max(m_btn.horizontalAdvance("随机"), m_btn.horizontalAdvance("秒表"))
            self._three_btn_each_w = char2_w_btn + self._gap_btn_pad
            self._three_btn_total_w = 2 * self._three_btn_each_w + self._gap_sm
            for btn_attr in ("_btn_random", "_btn_sw"):
                btn = getattr(self, btn_attr, None)
                if btn:
                    btn.setFixedSize(self._three_btn_each_w, self._three_btn_h)
            if hasattr(self, "_three_btn_row"):
                self._three_btn_row.setFixedSize(self._three_btn_total_w, self._three_btn_h)
            self._update_three_gaps(name_h, line_h)
        for ctn in getattr(self, "_three_mod_containers", []):
            ctn.setFixedHeight(line_h)
            inner = ctn.layout()
            if inner:
                inner.setSpacing(max(1, int(font_size * 0.08)))
                for j in range(inner.count()):
                    wgt = inner.itemAt(j).widget()
                    if isinstance(wgt, QLabel):
                        # 上下行都用默认文字颜色，上行 mod N 字号更小
                        is_top = "mod" in (wgt.text() or "")
                        fs_label = font_size - self._gap_mod_top_fs if is_top else font_size - self._gap_mod_val_fs
                        wgt.setStyleSheet(f"QLabel {{ color: {self._text_color}; font-size: {fs_label}px; }}")

        # ── 第15步：更新报数面板 spin 样式 ──
        spin_style = f"QSpinBox {{ padding: 3px 6px; border: 1px solid #dcdcdc; border-radius: 4px; background: transparent; color: {self._text_color}; }} QSpinBox:focus {{ border-color: #007aff; }}"
        for spin_attr in ("_spin_n1", "_spin_n2", "_spin_n3"):
            spin = getattr(self, spin_attr, None)
            if spin:
                spin.setStyleSheet(spin_style)

        # ── 第16步：Lock 状态下重新挂载自定义 indicator ──
        self._apply_lock_indicator()

        # ── 第17步：延迟对齐手工面板列宽（等布局完成后再测 col0 实际宽度）──
        QTimer.singleShot(0, self._align_manual_columns)

        # ── 第18步：转发到算卦面板 ──
        if hasattr(self, "_suangua_panel") and self._suangua_panel is not None:
            self._suangua_panel.refresh_font_size(font_size)

    def _update_panel_layout(self, w: QWidget, line_h: int, name_h: int):
        """
        更新单个面板内所有行的固定高度和顶部边距

        遍历面板 layout 中的所有子项：
          - QCheckBox / QLabel / QComboBox → setFixedHeight(line_h)
          - 跳过 title_row / manual_title / btn_row（其高度已在 refresh_font_size 中设为 name_h）
          - 对于 QWidget 包裹的行容器 → setFixedHeight(line_h) 并递归更新内部控件

        Args:
            w:      面板控件（QStackedWidget 中的某一页）
            line_h: 行高(px)，来自 drawer.line_h
            name_h: 卦名区域高度(px)，来自 drawer.name_area_h

        调用时机：
          - refresh_font_size() 中对所有面板调用（×4）
          - 不单独调用
        """
        layout = w.layout()
        if layout is None:
            return

        # 手工/金钱/蓍草面板自带标题行，不需要 name_h 顶部边距
        layout.setContentsMargins(0, 0 if w.objectName() in ("manual_panel", "lines_panel", "three_panel") else name_h, 0, 4)

        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue

            # 直接子布局（手工/报数面板）
            sub = item.layout()
            if sub is not None:
                for j in range(sub.count()):
                    child = sub.itemAt(j)
                    if child is None:
                        continue
                    wgt = child.widget()
                    if isinstance(wgt, (QCheckBox, QLabel, QComboBox)):
                        wgt.setFixedHeight(line_h)
                continue

            # QWidget 包裹的行容器（金钱/蓍草/报数面板）
            # 跳过 title_row / manual_title，其高度已在 refresh_font_size 中设为 name_h
            wrapper = item.widget()
            if wrapper is not None and wrapper.objectName() not in ("manual_title", "title_row", "btn_row"):
                wrapper.setFixedHeight(line_h)
                inner = wrapper.layout()
                if inner is not None:
                    for j in range(inner.count()):
                        child = inner.itemAt(j)
                        if child is None:
                            continue
                        wgt = child.widget()
                        if isinstance(wgt, (QCheckBox, QLabel)):
                            wgt.setFixedHeight(line_h)

    def refresh_text_color(self, text_color: str):
        """
        背景色变更时调用，更新所有面板文字颜色（深底白字/浅底黑字）

        这是文字颜色刷新链的核心方法，调用链：
          appearance_manager.apply_appearance() 计算 text_color
            → yijing_viewer.refresh_text_color()
              → qigua_panel.refresh_text_color()         ← 本方法
                → drawer.set_text_color()                 (更新卦名+边框颜色)
                → 所有 QLabel/QCheckBox/QComboBox 样式更新
                → _apply_lock_indicator()                 (重新挂载Lock indicator)

        刷新范围：
          1. 卦名文字颜色 + 圆角矩形边框颜色
          2. 所有面板标题行 QLabel + Lock QCheckBox
          3. 手工面板动爻复选框
          4. header 方法标签 hover 颜色
          5. 报数面板 Lock 复选框 + 标签行
          6. 金钱/蓍草面板复选框 + 下拉框
          7. 结果标签
          8. 报数面板 spin + 按钮
          9. mod 显示两行标签

        设计模式说明：
          设置面板 PANEL_STYLE 也是这样用 .format(text_color=) 联动背景色的。
          新增自定义组件应遵循同样模式：存 self._text_color，提供 refresh_text_color 方法。

        Args:
            text_color: CSS 颜色字符串（如 "#1d1d1f" 深色 / "#ffffff" 白色）
                       由 appearance_manager 根据背景色深浅计算后传入

        调用时机：
          - 用户在设置面板修改背景色/图片/模式后，appearance_manager 触发刷新链
          - _init_ui() 中不调用（初始化时已用默认文字颜色构建）
        """
        self._text_color = text_color

        # ── 第1步：卦名文字颜色 + 圆角矩形边框颜色 ──
        self._drawer.set_text_color(text_color)
        if hasattr(self, "_border_frame"):
            self._border_frame.setStyleSheet(f"""
                QFrame#border_frame {{
                    border: 1px solid {text_color};
                    border-left: none;
                    border-top: none;
                    border-top-left-radius: 0px;
                    border-top-right-radius: 0px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 10px;
                    background: transparent;
                }}
            """)

        # ── 第2步：手工/金钱/蓍草/报数面板标题行 + Lock 复选框 ──
        lock_style = f"QCheckBox {{ spacing: 4px; color: {text_color}; font-size: {self._font_size - 2}px; }}"
        for row_attr in ("_manual_title_row", "_lines_title_row", "_three_title_row"):
            row = getattr(self, row_attr, None)
            if row is None:
                continue
            lay = row.layout()
            if lay is None:
                continue
            for j in range(lay.count()):
                wgt = lay.itemAt(j).widget()
                if isinstance(wgt, QLabel):
                    tf3 = QFont()
                    tf3.setPointSize(self._font_size)
                    tf3.setBold(True)
                    wgt.setFont(tf3)
                    wgt.setStyleSheet(f"QLabel {{ color: {text_color}; }}")
                elif isinstance(wgt, QCheckBox):
                    wgt.setStyleSheet(lock_style)
        # 刷新按钮图标（矢量绘制，颜色变更时跟随 text_color）
        if hasattr(self, "_btn_refresh") and self._btn_refresh is not None:
            icon_size = max(14, int(self._drawer.name_area_h * self._gap_refresh_icon_scale))
            self._set_refresh_icon(text_color, icon_size)

        for cb in self._manual_cbs:
            cb.setStyleSheet(f"""
                QCheckBox {{ spacing: 8px; color: {text_color}; }}
            """)
        if hasattr(self, "_single_line_cb") and self._single_line_cb is not None:
            self._single_line_cb.setStyleSheet(f"""
                QCheckBox {{ spacing: 4px; color: {text_color}; }}
            """)

        # ── 第3步：更新 header 方法标签 hover 颜色 ──
        for lbl in self._header_labels:
            lbl.setStyleSheet(f"""
                QPushButton {{
                    color: #86868b; border: none; background: transparent;
                    font-size: {self._font_size}px;
                }}
                QPushButton:hover {{ color: {text_color}; }}
            """)

        # ── 第4步：报数面板 Lock 复选框 + 标签行 ──
        for row_attr in ("_three_title_row",):
            row = getattr(self, row_attr, None)
            if row is None:
                continue
            lay = row.layout()
            if lay is None:
                continue
            for j in range(lay.count()):
                wgt = lay.itemAt(j).widget()
                if isinstance(wgt, QCheckBox):
                    wgt.setStyleSheet(f"QCheckBox {{ spacing: 4px; color: {text_color}; font-size: {self._font_size - 2}px; }}")
        for lb in getattr(self, "_three_spin_labels", []):
            lb.setStyleSheet(f"QLabel {{ color: {text_color}; }}")

        # ── 第5步：金钱/蓍草面板复选框 + 下拉框 ──
        fs = self._font_size
        for cb in getattr(self, "_lines_cbs", []):
            cb.setStyleSheet(f"""
                QCheckBox {{ spacing: {self._gap_cb_text}px; color: {text_color}; font-size: {fs - 2}px; }}
            """)
        for combo in getattr(self, "_lines_inputs", []):
            combo.setStyleSheet(f"""
                QComboBox {{
                    padding: 3px 6px;
                    border: 1px solid #dcdcdc;
                    border-radius: 4px;
                    background: transparent;
                    color: {text_color};
                    font-size: {fs - 1}px;
                }}
                QComboBox:focus {{ border-color: #007aff; }}
                QComboBox::drop-down {{ width: 16px; }}
                QComboBox QAbstractItemView {{ {self._dropdown_style()} }}
            """)

        # ── 第6步：结果标签 ──
        self._label_result.setStyleSheet(f"QLabel {{ color: {text_color}; }}")
        # 动爻判断文字
        if hasattr(self, "_label_judgment") and self._label_judgment is not None:
            self._label_judgment.setStyleSheet(
                f"QLabel {{ color: {text_color}; font-size: {self._font_size + self._fs_judgment}px; }}")

        # ── 第7步：报数面板 spin + 按钮 文字颜色 ──
        spin_style = f"QSpinBox {{ padding: 3px 6px; border: 1px solid #dcdcdc; border-radius: 4px; background: transparent; color: {text_color}; }} QSpinBox:focus {{ border-color: #007aff; }}"
        for spin_attr in ("_spin_n1", "_spin_n2", "_spin_n3"):
            spin = getattr(self, spin_attr, None)
            if spin:
                spin.setStyleSheet(spin_style)
        # 按钮浅色背景 → 深色文字不随主题变化
        for btn_attr in ("_btn_random", "_btn_sw"):
            btn = getattr(self, btn_attr, None)
            if btn:
                btn.setStyleSheet("""
                    QPushButton { padding: 4px 0px; border: 1px solid #dcdcdc; border-radius: 6px; background: #f5f5f7; color: #1d1d1f; }
                    QPushButton:hover { border-color: #007aff; }
                """)

        # ── 第8步：mod 显示两行标签颜色 ──
        for ctn in getattr(self, "_three_mod_containers", []):
            inner = ctn.layout()
            if inner:
                for j in range(inner.count()):
                    wgt = inner.itemAt(j).widget()
                    if isinstance(wgt, QLabel):
                        is_top = "mod" in (wgt.text() or "")
                        fs_label = self._font_size - self._gap_mod_top_fs if is_top else self._font_size - self._gap_mod_val_fs
                        wgt.setStyleSheet(f"QLabel {{ color: {text_color}; font-size: {fs_label}px; }}")

        # Lock 状态下重新挂载自定义 indicator
        self._apply_lock_indicator()

        # 转发到算卦面板
        if hasattr(self, "_suangua_panel") and self._suangua_panel is not None:
            self._suangua_panel.refresh_text_color(text_color)

    # ═══════════════════════════════════════════════════════════
    #  三位数：随机倒计时 / 秒表
    # ═══════════════════════════════════════════════════════════

    def _on_time_random(self):
        """
        报数面板"随机"按钮点击 → 弹出10秒倒计时弹窗

        弹窗接受后，将生成的三个随机数填入 spin 控件并自动起卦。
        随机数由 CountdownDialog 基于当前时间戳生成。

        调用时机：_btn_random.clicked 信号触发
        """
        dlg = CountdownDialog(self.window())
        if dlg.exec() == CountdownDialog.DialogCode.Accepted:
            n1, n2, n3 = dlg.result_numbers
            self._spin_n1.setValue(n1)
            self._spin_n2.setValue(n2)
            self._spin_n3.setValue(n3)
            self._run_three_calc(n1, n2, n3)

    def _on_stopwatch(self):
        """
        报数面板"秒表"按钮点击 → 弹出秒表计时弹窗

        弹窗接受后，将起止时间差转换的三个数字填入 spin 控件并自动起卦。

        调用时机：_btn_sw.clicked 信号触发
        """
        dlg = StopwatchDialog(self.window())
        if dlg.exec() == StopwatchDialog.DialogCode.Accepted:
            n1, n2, n3 = dlg.result_numbers
            self._spin_n1.setValue(n1)
            self._spin_n2.setValue(n2)
            self._spin_n3.setValue(n3)
            self._run_three_calc(n1, n2, n3)

    # ═══════════════════════════════════════════════════════════
    #  动爻跨模式同步
    # ═══════════════════════════════════════════════════════════

    def _on_manual_changing_toggled(self, line_num: int, checked: bool):
        """
        手工模式动爻复选框勾选/取消

        手工模式下可多选动爻，更新 _changing_lines 集合后，
        立即同步到所有其他面板控件并重新起卦。

        单动爻模式：勾选时仅保留当前爻，其他爻自动取消（单选行为）。

        Args:
            line_num: 爻位（1=初爻..6=上爻）
            checked:  True=勾选（该爻为动爻），False=取消

        调用时机：手工面板动爻复选框 toggled 信号触发
        """
        single_mode = (self._single_line_cb is not None and self._single_line_cb.isChecked())
        if checked:
            if single_mode:
                self._changing_lines.clear()
            self._changing_lines.add(line_num)
        else:
            self._changing_lines.discard(line_num)
        self._sync_controls_to_changing_lines()
        self._on_calc()

    def _on_single_line_toggled(self, checked: bool):
        """"单动爻"复选框切换 — 限制最多只有一个动爻"""
        if self._lock_checked:
            return
        if checked:
            if self._changing_lines:
                top = max(self._changing_lines)
                self._changing_lines.clear()
                self._changing_lines.add(top)
            # 勾选单动爻 → 立即切到梅花
            if hasattr(self, "_suangua_panel") and self._suangua_panel is not None:
                self._suangua_panel.switch_method("meihua")
        else:
            self._changing_lines.clear()
        self._sync_controls_to_changing_lines()
        self._on_calc()

    def _sync_controls_to_changing_lines(self):
        """
        将 _changing_lines 动爻集合同步到所有面板控件

        同步目标（三个面板类型）：
          1. 手工面板：6个动爻复选框 → setChecked(line_num in changing)
          2. 金钱/蓍草面板：
             - 6个"动"复选框 → setChecked(line_num in changing)
             - 6个下拉框 → 翻转老/少状态（保留阴阳属性）
               使用 _COIN_CHANGING / _YARROW_CHANGING 映射表：
               是动爻 → 转为老阳/老阴，非动爻 → 转为少阳/少阴

        设计要点：
          - 使用 blockSignals 避免 setChecked/setCurrentIndex 触发循环信号
          - 自动检测当前 combo 选项集判断是金钱还是蓍草模式
          - 同步后调用 _sync_coin_yarrow_display() 更新卦图

        调用时机：
          - _on_manual_changing_toggled() 中手工复选框变化后
          - _run_three_calc() 中报数计算完成后
        """
        changing = self._changing_lines
        # 手工面板复选框
        for i in range(6):
            line_num = i + 1  # 初爻(1)..上爻(6)
            cb = self._manual_cbs[6 - line_num]  # cb[0]=上爻..cb[5]=初爻
            cb.blockSignals(True)
            cb.setChecked(line_num in changing)
            cb.blockSignals(False)
        # 同步 单动爻 checkbox：>1 动爻时自动取消，≤1 时保持原状态
        if hasattr(self, "_single_line_cb") and self._single_line_cb is not None:
            if self._single_line_cb.isChecked() and len(changing) > 1:
                self._single_line_cb.blockSignals(True)
                self._single_line_cb.setChecked(False)
                self._single_line_cb.blockSignals(False)
        # 金钱/蓍草面板：复选框 + 下拉框联动（始终同步，根据 combo 当前选项集判断金钱/蓍草）
        if self._lines_inputs:
            first_opt = self._lines_inputs[0].itemText(0) if self._lines_inputs[0].count() > 0 else ""
            cmode = "yarrow" if "9-老阳" in first_opt else "coin"
            for j in range(6):
                line_num = 6 - j  # j=0→上爻(line6), j=5→初爻(line1)
                is_changing = line_num in changing
                cb = self._lines_cbs[j]
                cb.blockSignals(True)
                cb.setChecked(is_changing)
                cb.blockSignals(False)
                # 下拉框：保持阴阳，只翻转动静
                combo = self._lines_inputs[j]
                old_val = self._combo_val(combo)
                toggle_map = self._COIN_CHANGING if cmode == "coin" else self._YARROW_CHANGING
                new_val = toggle_map.get(old_val, old_val)
                if is_changing:
                    changing_map = {1: 3, 3: 1, 2: 0, 0: 2} if cmode == "coin" else {7: 9, 9: 7, 8: 6, 6: 8}
                    new_val = changing_map.get(old_val, old_val)
                combo.blockSignals(True)
                for k in range(combo.count()):
                    if int(combo.itemText(k).split("-")[0]) == new_val:
                        combo.setCurrentIndex(k)
                        break
                combo.blockSignals(False)
        self._sync_coin_yarrow_display()

    # ═══════════════════════════════════════════════════════════
    #  事件过滤（确保弹出菜单在 macOS 下可靠触发）
    # ═══════════════════════════════════════════════════════════

    def eventFilter(self, obj, event):
        """拦截 _title_label 的鼠标按下事件 → 弹出卦选择列表"""
        from PySide6.QtCore import QEvent
        if obj is self._title_label and event.type() == QEvent.Type.MouseButtonPress:
            self._show_gua_picker()
            return True
        return super().eventFilter(obj, event)

    # ═══════════════════════════════════════════════════════════
    #  卦名弹出菜单
    # ═══════════════════════════════════════════════════════════

    def _show_gua_picker(self):
        """
        点击「起卦」标题 → 弹出可滚动的 64 卦选择列表

        列表格式：01 ☰ 乾为天  02 ☷ 坤为地  ...
        每次最多显示 10 行，超出滚动。
        选中后：跳转到对应卦象，动爻设置保持不变。
        点击列表外部自动关闭。
        """
        from PySide6.QtWidgets import QListWidget, QListWidgetItem

        all_gua = load_all_gua()
        if not all_gua:
            return

        # 强制启用标题按钮（Lock 状态下按钮被禁用）
        was_enabled = self._title_label.isEnabled()
        if not was_enabled:
            self._title_label.setEnabled(True)

        # 计算尺寸
        row_h = self._font_size * 2 + 10  # 每行高度（含上下 padding）
        visible_rows = min(10, len(all_gua))
        list_w = 320  # 列表宽度

        # ── 根据当前主题计算弹窗颜色 ──
        # 文字颜色亮 → 深色模式；文字颜色暗 → 浅色模式
        tc = self._text_color
        is_dark = _is_light_color(tc)
        if is_dark:
            bg = "#2c2c2e"
            border_c = "#555555"
            hover_bg = "#3a3a3c"
            scroll_handle = "#555555"
            item_text = "#f0f0f0"
        else:
            bg = "#ffffff"
            border_c = "#cccccc"
            hover_bg = "#f0f0f5"
            scroll_handle = "#cccccc"
            item_text = "#1d1d1f"

        # ── 列表控件 ──
        picker = QListWidget()
        picker.setFrameShape(QFrame.Shape.NoFrame)
        picker.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        picker.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        picker.setFixedSize(list_w, row_h * visible_rows + 4)
        picker.setStyleSheet(f"""
            QListWidget {{
                background: {bg};
                border: 1px solid {border_c};
                border-radius: 6px;
                font-size: {self._font_size}px;
                color: {item_text};
            }}
            QListWidget::item {{
                padding: 5px 12px;
                height: {row_h}px;
            }}
            QListWidget::item:selected {{
                background: #007aff;
                color: #ffffff;
            }}
            QListWidget::item:hover {{
                background: {hover_bg};
            }}
            QScrollBar:vertical {{
                width: 8px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_handle};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        sorted_ids = sorted(all_gua.keys())
        for gid in sorted_ids:
            data = all_gua[gid]
            item = QListWidgetItem(f"{gid:02d}  {data.get('symbol', '')} {data.get('full_name', '?')}")
            item.setData(Qt.ItemDataRole.UserRole, gid)
            picker.addItem(item)

        picker.itemClicked.connect(
            lambda item: self._on_picker_selected(item, picker, was_enabled)
        )

        # ── 包装到 Popup 弹窗中（处理关闭事件）──
        popup = _GuaPickerPopup(picker, was_enabled, self._title_label, self)
        # 保持引用防止 GC 回收（Popup 窗口必须被引用才能持续显示）
        self._gua_picker = popup
        # 弹出在标题按钮左下方
        pos = self._title_label.mapToGlobal(self._title_label.rect().bottomLeft())
        screen = self.screen()
        if screen:
            screen_bottom = screen.availableGeometry().bottom()
            if pos.y() + picker.height() > screen_bottom:
                pos.setY(screen_bottom - picker.height())
        popup.move(pos)
        popup.show()

    def _on_picker_selected(self, item, picker, was_enabled):
        """
        列表项被点击 → 提取卦 ID → 关闭弹窗 → 跳转卦象

        Parameters:
            item: QListWidgetItem — 被点击的列表项
            picker: QListWidget — 弹出列表控件
            was_enabled: bool — Lock 状态恢复
        """
        gua_id = item.data(Qt.ItemDataRole.UserRole)
        # 延迟销毁弹窗：picker 是 popup 的子控件，当前正处在 picker 的
        # itemClicked 信号处理器中，同步 close() 会销毁 picker 导致 SIGSEGV。
        # 改用 hide() + deleteLater() 清理，避免 use-after-free。
        popup = picker.window()
        if popup:
            self._gua_picker = None
            if not was_enabled:
                self._title_label.setEnabled(False)
            popup.hide()
            popup.deleteLater()
        if gua_id is not None:
            self._on_gua_picked(gua_id)

    def _on_gua_picked(self, gua_id: int):
        """
        用户从菜单选中某卦 → 跳转到该卦，保持当前动爻不变

        Parameters:
            gua_id: 卦 ID (1-64)
        """
        all_gua = load_all_gua()
        data = all_gua.get(gua_id)
        if not data:
            return

        binary = data.get("binary", "000000")
        yang = [c == "1" for c in binary]

        # 更新卦图
        self._drawer.set_lines(yang)

        # 保持 _changing_lines 不变，重新计算变卦
        lower_num = _yang_to_xiantian(yang[:3])
        upper_num = _yang_to_xiantian(yang[3:])

        # 构建变卦
        bian_gua = None
        changing_list = sorted(self._changing_lines)
        if changing_list:
            new_binary = list(binary)
            for cl in changing_list:
                idx = cl - 1
                new_binary[idx] = "0" if binary[idx] == "1" else "1"
            new_binary = "".join(new_binary)
            new_lower = _yang_to_xiantian([c == "1" for c in new_binary[:3]])
            new_upper = _yang_to_xiantian([c == "1" for c in new_binary[3:]])
            bian_gua = get_gua_by_xiantian(new_upper, new_lower)

        result = GuaResult(
            ben_gua=data,
            bian_gua=bian_gua,
            lower_num=lower_num,
            upper_num=upper_num,
            changing_line=changing_list[0] if changing_list else 0,
            changing_lines=changing_list,
        )

        # 同步动爻到所有面板控件
        self._sync_controls_to_changing_lines()

        # 显示结果
        self._show_result(result)

    # ═══════════════════════════════════════════════════════════
    #  统一计算入口
    # ═══════════════════════════════════════════════════════════

    def _on_calc(self):
        """
        统一计算入口 — 根据当前起卦方式执行对应计算并显示结果

        分发逻辑：
          - manual: 从 drawer.yang_lines() + 手工复选框读取 → calc_from_yang_lines()
          - three:  从 spin 读取三个数 → _run_three_calc()
          - coin/yarrow: 从6个 combo 读取数值 → calc_six_lines()

        每次计算后更新：
          1. _changing_lines 集合
          2. drawer 卦图
          3. 底部结果标签

        调用时机：
          - 任何输入控件变化后（手工勾选、报数 spin、金钱/蓍草 combo）
          - 起卦标题按钮点击
          - 方法切换时
          - _init_ui() 末尾首次起卦
        """
        key = self._current_method

        if key == "manual":
            yang = self._drawer.yang_lines()
            changing = []
            for j, cb in enumerate(self._manual_cbs):
                if cb.isChecked():
                    changing.append(6 - j)
            self._changing_lines = set(changing)
            result = calc_from_yang_lines(yang, changing)
            self._show_result(result)

        elif key == "three":
            n1 = self._spin_n1.value()
            n2 = self._spin_n2.value()
            n3 = self._spin_n3.value()
            self._run_three_calc(n1, n2, n3)

        elif key in ("coin", "yarrow"):
            mode = key
            vals = [self._combo_val(self._lines_inputs[j]) for j in range(6)]
            # 从 combo 值更新 _changing_lines
            self._changing_lines = set()
            for idx, v in enumerate(vals):
                if mode == "coin" and v in (0, 3):
                    self._changing_lines.add(6 - idx)
                elif mode == "yarrow" and v in (6, 9):
                    self._changing_lines.add(6 - idx)
            vals.reverse()
            result = calc_six_lines(vals, mode=mode)
            self._show_result(result)

    def _run_three_auto(self):
        """
        三位数 spin 值变化 → 自动起卦

        读取当前三个 spin 值并执行计算。
        与 _run_three_calc() 的区别：不接收参数，直接从控件读取。

        调用时机：
          - spin valueChanged 信号触发
          - _switch_method() 中切换到报数模式
        """
        self._run_three_calc(
            self._spin_n1.value(),
            self._spin_n2.value(),
            self._spin_n3.value(),
        )

    def _run_three_calc(self, n1: int, n2: int, n3: int):
        """
        三位数计算 + 更新卦图展示

        流程：
          1. 刷新余数标签（mod6 / mod8 / mod8）
          2. 调用 calc_three_numbers(n1, n2, n3) 执行计算
          3. 更新 _changing_lines 集合（动爻由 n3 mod6 决定）
          4. 同步动爻到所有面板控件
          5. 更新 drawer 卦图
          6. 显示结果

        Args:
            n1: 下卦数（取余 mod8 → 映射先天八卦）
            n2: 上卦数（取余 mod8 → 映射先天八卦）
            n3: 动爻数（取余 mod6 → 0=无动爻, 1-6=动爻位置）

        调用时机：
          - _run_three_auto() 中 spin 值变化
          - _on_time_random() / _on_stopwatch() 中弹窗返回后
        """
        # 刷新余数标签（仅更新下行数值，上行 modN 不变）
        if hasattr(self, "_three_mod_values"):
            self._three_mod_values[2].setText(str(n1 % 8))   # 下
            self._three_mod_values[1].setText(str(n2 % 8))   # 上
            self._three_mod_values[0].setText(str(n3 % 6))   # 动

        result = calc_three_numbers(n1, n2, n3)

        # 更新动爻状态 + 同步到所有面板控件
        if result.changing_line > 0:
            self._changing_lines = {result.changing_line}
        else:
            self._changing_lines = set()
        self._sync_controls_to_changing_lines()

        if result.ben_gua:
            binary = result.ben_gua.get("binary", "111111")
            yang = [c == "1" for c in binary]
            self._drawer.set_lines(yang)

        self._show_result(result)

    def _show_result(self, result: GuaResult):
        """
        显示起卦结果：卦图更新 + 底部详情文字

        显示格式：
          - 有变卦：  "䷀ 乾为天  →  ䷫ 天风姤"
          - 无变卦：  "䷀ 乾为天 (六爻安静)"
          - 异常时：  "? ?"
          - 无变卦且结果为None时显示 "(六爻安静)"

        GuaResult 数据流：
          hexagram_calc 创建 → _show_result() 显示 → case_manager 存储

        Args:
            result: 由 calc_three_numbers / calc_from_yang_lines / calc_six_lines 返回

        调用时机：
          - _on_calc() 中每次计算完成后
        """
        ben = result.ben_gua
        bian = result.bian_gua

        # 卦图更新
        if ben:
            binary = ben.get("binary", "111111")
            yang = [c == "1" for c in binary]
            self._drawer.set_lines(yang)

        # 底部详情
        symbol = ben.get("symbol", "?")
        name = ben.get("full_name", "?")
        text = f"{symbol} {name}"
        if bian:
            b_symbol = bian.get("symbol", "?")
            b_name = bian.get("full_name", "?")
            text += f"  →  {b_symbol} {b_name}"
        elif not result.changing_lines:
            text += " (六爻安静)"
        self._label_result.setText(text)

        # 动爻判断方式（显示应参照哪一爻的爻辞断卦）
        if ben and hasattr(self, "_label_judgment") and self._label_judgment is not None:
            binary = ben.get("binary", "111111")
            _, reason = get_judgment_line(binary, list(result.changing_lines))
            self._label_judgment.setText(f"断法: {reason}")
            _check(self._label_judgment.text(), "判断文字为空")

        # 转发起卦结果到算卦面板
        if hasattr(self, "_suangua_panel") and self._suangua_panel is not None and ben:
            self._suangua_panel.set_gua_result(ben, list(result.changing_lines), bian)

            _check(self._suangua_panel._gua_result is not None, "suangua 未收到卦数据")
            _check(self._suangua_panel._gua_result.get("full_name") == ben.get("full_name"),
                   f"suangua 卦名不匹配: {self._suangua_panel._gua_result.get('full_name')} != {ben.get('full_name')}")
