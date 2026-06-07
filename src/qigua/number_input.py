"""
三位数起卦 Widget — 手动输入 / 时间随机 / 秒表 三种方式获取数字

═══════════════════════════════════════════════════════════════
文件职责：提供 ThreeNumberWidget，支持三种方式产生 3 个三位数
═══════════════════════════════════════════════════════════════

三种输入方式：
    1. 手动输入 — 3 个 QSpinBox (0-999)，用户自行输入后点「起卦」
    2. 时间随机 — 弹出 CountdownDialog，10 秒倒计时每秒采集随机数，
                   10 组取平均 → 3 个三位数
    3. 秒表    — 弹出 StopwatchDialog，自由计时 + 3 次记录，
                   从毫秒值提取 x.aa → 3 个三位数

计算流程：
    三位数 → calc_three_numbers(n1, n2, n3) → GuaResult
    n1 % 8 → 下卦, n2 % 8 → 上卦, n3 % 6 → 动爻

被哪些文件调用：
    - divination_panel.py: QiguaPanel 已将三位数输入整合到 _make_number_panel()
    - 本文件保留作为独立组件参考和备选

依赖：
    - hexagram_calc.py: calc_three_numbers()
    - countdown_timer.py: CountdownDialog
    - stopwatch_timer.py: StopwatchDialog

用法示例:
    widget = ThreeNumberWidget()
    widget.set_on_result(lambda result: print(f"本卦: {result.ben_gua}"))
    # 用户操作 → 自动回调传入 GuaResult
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QSpinBox, QPushButton, QFrame, QAbstractSpinBox)
from PySide6.QtCore import Qt

from .hexagram_calc import calc_three_numbers
from .countdown_timer import CountdownDialog
from .stopwatch_timer import StopwatchDialog


class ThreeNumberWidget(QWidget):
    """
    三位数起卦输入区

    属性:
        _on_result: Callable[[GuaResult], None] | None — 结果回调，由外部 set_on_result() 设置
        _spin_n1/_spin_n2/_spin_n3: QSpinBox — 分别对应下卦数/上卦数/动爻数
        _btn_manual_calc: QPushButton — 「起卦」按钮
        _btn_time_random: QPushButton — 「时间随机」按钮
        _btn_stopwatch: QPushButton — 「秒表」按钮
        _label_info: QLabel — 底部计算过程提示

    UI 结构:
        ┌─────────────────────────────┐
        │ 先下卦 · 再上卦 · 后动爻      │
        │ [下 000] [上 000] [动 000]  │
        │ [起卦]                      │
        │                             │
        │ [时间随机]  [秒表]            │
        │                             │
        │ 下卦:123%8=3(→3) ...        │
        └─────────────────────────────┘

    用法示例:
        widget = ThreeNumberWidget()
        widget.set_on_result(lambda result: print(result))
    """

    def __init__(self, parent=None):
        """
        Parameters:
            parent: QWidget | None — 父组件
        """
        super().__init__(parent)
        self._on_result = None
        self._init_ui()

    def _init_ui(self):
        """
        构建界面：
        说明标签 → 手动输入行（3 个 QSpinBox + 起卦按钮）→ 时间随机/秒表按钮行 → 信息提示
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # 说明
        hint = QLabel("先下卦 · 再上卦 · 后动爻")
        hint.setStyleSheet("""
            QLabel { font-size: 11px; color: #86868b; }
        """)
        root.addWidget(hint)

        # ── 手动输入行 ──
        manual_row = QHBoxLayout()
        manual_row.setSpacing(6)

        self._spin_n1 = self._make_spin()
        self._spin_n2 = self._make_spin()
        self._spin_n3 = self._make_spin()

        manual_row.addWidget(QLabel("下"))
        manual_row.addWidget(self._spin_n1)
        manual_row.addWidget(QLabel("上"))
        manual_row.addWidget(self._spin_n2)
        manual_row.addWidget(QLabel("动"))
        manual_row.addWidget(self._spin_n3)

        self._btn_manual_calc = QPushButton("起卦")
        self._btn_manual_calc.setFixedSize(56, 30)
        self._btn_manual_calc.setStyleSheet("""
            QPushButton {
                border: none; border-radius: 6px; background: #007aff;
                font-size: 12px; font-weight: bold; color: #ffffff;
            }
            QPushButton:hover { background: #0062cc; }
        """)
        self._btn_manual_calc.clicked.connect(self._on_manual)
        manual_row.addWidget(self._btn_manual_calc)

        root.addLayout(manual_row)

        # ── 时间随机 / 秒表（同一行紧凑排列）──
        auto_row = QHBoxLayout()
        auto_row.setSpacing(6)

        self._btn_time_random = QPushButton("时间随机")
        self._btn_time_random.setFixedHeight(28)
        self._btn_time_random.setStyleSheet("""
            QPushButton {
                padding: 4px 10px; border: 1px solid #dcdcdc; border-radius: 5px;
                background: #f5f5f7; font-size: 11px; color: #1d1d1f;
            }
            QPushButton:hover { background: #e8e8ed; border-color: #007aff; }
        """)
        self._btn_time_random.clicked.connect(self._on_time_random)
        auto_row.addWidget(self._btn_time_random)

        self._btn_stopwatch = QPushButton("秒表")
        self._btn_stopwatch.setFixedHeight(28)
        self._btn_stopwatch.setStyleSheet("""
            QPushButton {
                padding: 4px 10px; border: 1px solid #dcdcdc; border-radius: 5px;
                background: #f5f5f7; font-size: 11px; color: #1d1d1f;
            }
            QPushButton:hover { background: #e8e8ed; border-color: #007aff; }
        """)
        self._btn_stopwatch.clicked.connect(self._on_stopwatch)
        auto_row.addWidget(self._btn_stopwatch)

        auto_row.addStretch()
        root.addLayout(auto_row)

        # 信息提示
        self._label_info = QLabel("")
        self._label_info.setWordWrap(True)
        self._label_info.setStyleSheet("""
            QLabel { font-size: 11px; color: #aeaeb2; }
        """)
        root.addWidget(self._label_info)

        root.addStretch()

    def _make_spin(self) -> QSpinBox:
        """
        创建紧凑 QSpinBox (0-999)

        特性：
          - 无上下箭头按钮（NoButtons）
          - 文本居中对齐
          - 聚焦蓝边

        Returns:
            QSpinBox: 配置好的旋转框
        """
        spin = QSpinBox()
        spin.setRange(0, 999)
        spin.setFixedWidth(62)
        spin.setFixedHeight(28)
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin.setStyleSheet("""
            QSpinBox {
                padding: 2px 4px; border: 1.5px solid #dcdcdc; border-radius: 5px;
                font-size: 14px; background: #ffffff; color: #1d1d1f;
            }
            QSpinBox:focus { border-color: #007aff; }
        """)
        return spin

    def _on_manual(self):
        """
        手动输入起卦：
          读取 3 个 QSpinBox 的值 → _do_calc(n1, n2, n3)
        """
        n1, n2, n3 = self._spin_n1.value(), self._spin_n2.value(), self._spin_n3.value()
        self._do_calc(n1, n2, n3)

    def _on_time_random(self):
        """
        弹出 CountdownDialog 时间随机弹窗

        流程：
          1. 弹出模态弹窗 → 10 秒倒计时
          2. 每秒生成 1 组 3 个随机数 (000-999)，共 10 组
          3. 每组取平均 → 3 个三位数
          4. 弹窗 accept → 读取 dlg.result_numbers
          5. 回填到 QSpinBox + 调用 _do_calc
        """
        dlg = CountdownDialog(self.window())
        if dlg.exec() == CountdownDialog.DialogCode.Accepted:
            n1, n2, n3 = dlg.result_numbers
            self._spin_n1.setValue(n1)
            self._spin_n2.setValue(n2)
            self._spin_n3.setValue(n3)
            self._do_calc(n1, n2, n3)

    def _on_stopwatch(self):
        """
        弹出 StopwatchDialog 秒表弹窗

        流程：
          1. 弹出模态弹窗 → 用户点击「开始」
          2. 自由计时，任意时刻点击「记录」3 次
          3. 从每次记录的毫秒值提取 x.aa → 三位数 = x * 100 + aa
          4. 弹窗 accept → 读取 dlg.result_numbers
          5. 回填到 QSpinBox + 调用 _do_calc
        """
        dlg = StopwatchDialog(self.window())
        if dlg.exec() == StopwatchDialog.DialogCode.Accepted:
            n1, n2, n3 = dlg.result_numbers
            self._spin_n1.setValue(n1)
            self._spin_n2.setValue(n2)
            self._spin_n3.setValue(n3)
            self._do_calc(n1, n2, n3)

    def _do_calc(self, n1: int, n2: int, n3: int):
        """
        执行三位数起卦计算 + 显示过程信息 + 触发 _on_result 回调

        计算规则：
            n1 % 8 → 下卦先天数（余 0 → 8 坤）
            n2 % 8 → 上卦先天数（余 0 → 8 坤）
            n3 % 6 → 动爻位置（余 0 → 第 6 爻）

        Parameters:
            n1: int — 下卦原始数 (0-999)
            n2: int — 上卦原始数 (0-999)
            n3: int — 动爻原始数 (0-999)
        """
        result = calc_three_numbers(n1, n2, n3)
        lower_num = result.lower_num
        upper_num = result.upper_num
        info = (
            f"下卦: {n1}%8={n1%8}(→{lower_num})  "
            f"上卦: {n2}%8={n2%8}(→{upper_num})  "
            f"动爻: {n3}%6={n3%6}(→{result.changing_line})"
        )
        self._label_info.setText(info)
        if self._on_result:
            self._on_result(result)

    def set_on_result(self, callback):
        """
        设置起卦结果回调

        Parameters:
            callback: Callable[[GuaResult], None] — 接收 GuaResult 的回调函数
        """
        self._on_result = callback
