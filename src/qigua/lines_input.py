"""
金钱卦 / 蓍草卦 Widget — 6 爻输入，从下而上排列

═══════════════════════════════════════════════════════════════
文件职责：提供 CoinYarrowWidget，金钱卦和蓍草卦两种模式的 6 爻输入
═══════════════════════════════════════════════════════════════

两种模式共享相同的核心逻辑：
    金钱模式: 0-3 个正面（QSpinBox 0-3）
    蓍草模式: 6/7/8/9（QComboBox 6,7,8,9）

    映射关系（cross-map）：
        金钱 → 蓍草: 0→6, 1→7, 2→8, 3→9
        蓍草 → 金钱: 6→0, 7→1, 8→2, 9→3

    阴阳判定（两种模式共用）：
        3/9 = 老阳(⚊○) = 阳 + 变爻
        0/6 = 老阴(⚋×) = 阴 + 变爻
        1/7 = 少阳(⚊)  = 阳 + 静爻
        2/8 = 少阴(⚋)  = 阴 + 静爻

爻序排列：
    - 输入界面从上到下：上爻→五爻→四爻→三爻→二爻→初爻
    - 传递给 calc_six_lines 的顺序：[初爻..上爻]（从下而上，index 0=初爻）

被哪些文件调用：
    - divination_panel.py: QiguaPanel 已将六爻输入整合到 _make_lines_panel()
    - 本文件保留作为独立组件参考和备选

依赖：
    - hexagram_calc.py: calc_six_lines()
    - bagua.py: COIN_TO_YAO, YARROW_TO_YAO

用法示例:
    widget = CoinYarrowWidget()
    widget.set_on_result(lambda result: print(f"本卦: {result.ben_gua}"))
    # 用户切换模式 → 输入 6 爻 → 点击「起卦」→ 回调传入 GuaResult
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QSpinBox, QComboBox, QPushButton, QFrame)
from PySide6.QtCore import Qt

from .hexagram_calc import calc_six_lines
from .bagua import COIN_TO_YAO, YARROW_TO_YAO


class CoinYarrowWidget(QWidget):
    """
    金钱卦/蓍草卦 6 爻输入区

    属性:
        _mode: str — "coin" 或 "yarrow"，当前模式
        _on_result: Callable[[GuaResult], None] | None — 结果回调
        _coin_inputs: list[QSpinBox] — 6 个金钱模式输入控件（0-3）
        _yarrow_inputs: list[QComboBox] — 6 个蓍草模式输入控件（6/7/8/9）
        _line_labels: list[QLabel] — 6 个爻象提示标签（如"少阳 ⚊"）
        _btn_coin/_btn_yarrow: QPushButton — 模式切换按钮
        _btn_calc: QPushButton — 「起卦」按钮
        _label_info: QLabel — 底部计算结果提示

    UI 结构:
        ┌─────────────────────────────┐
        │ 从下而上  初爻→上爻 [金钱][蓍草]│
        │                             │
        │         上爻 [0▼] 少阳 ⚊     │
        │         五爻 [0▼] 少阳 ⚊     │
        │         四爻 [0▼] 少阳 ⚊     │
        │         三爻 [0▼] 少阳 ⚊     │
        │         二爻 [0▼] 少阳 ⚊     │
        │         初爻 [0▼] 少阳 ⚊     │
        │                             │
        │                   [起卦]    │
        │ 第1爻: 少阳 (1) ...          │
        └─────────────────────────────┘

    用法示例:
        widget = CoinYarrowWidget()
        widget.set_on_result(lambda result: print(result))
    """

    def __init__(self, parent=None):
        """
        Parameters:
            parent: QWidget | None — 父组件
        """
        super().__init__(parent)
        self._mode = "coin"  # 默认金钱卦模式
        self._on_result = None
        self._line_inputs: list = []  # 当前激活的输入控件引用
        self._line_labels: list = []  # 6 个爻名标签
        self._init_ui()

    def _init_ui(self):
        """
        构建界面：
        顶行（说明 + 模式切换按钮）→ 6 爻输入行 → 起卦按钮 → 提示信息
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # ── 说明 + 模式切换（同一行）──
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        hint = QLabel("从下而上  初爻→上爻")
        hint.setStyleSheet("""
            QLabel { font-size: 11px; color: #86868b; }
        """)
        top_row.addWidget(hint)

        top_row.addStretch()

        # 紧凑模式切换
        self._btn_coin = QPushButton("金钱")
        self._btn_coin.setFixedHeight(24)
        self._btn_coin.setStyleSheet("""
            QPushButton {
                padding: 2px 8px; border: 1.5px solid #007aff; border-radius: 4px;
                background: #007aff; font-size: 11px; font-weight: bold; color: #fff;
            }
            QPushButton:hover { background: #0062cc; }
        """)
        self._btn_coin.clicked.connect(lambda: self._switch_mode("coin"))
        top_row.addWidget(self._btn_coin)

        self._btn_yarrow = QPushButton("蓍草")
        self._btn_yarrow.setFixedHeight(24)
        self._btn_yarrow.setStyleSheet("""
            QPushButton {
                padding: 2px 8px; border: 1px solid #dcdcdc; border-radius: 4px;
                background: #f5f5f7; font-size: 11px; color: #1d1d1f;
            }
            QPushButton:hover { background: #e8e8ed; }
        """)
        self._btn_yarrow.clicked.connect(lambda: self._switch_mode("yarrow"))
        top_row.addWidget(self._btn_yarrow)

        root.addLayout(top_row)

        # ── 6 爻输入行（从下而上：初爻在下，上爻在上）──
        # 显示顺序：上爻 → … → 初爻（从上到下排列，符合视觉习惯）
        self._lines_widget = QWidget()
        lines_layout = QVBoxLayout(self._lines_widget)
        lines_layout.setContentsMargins(0, 0, 0, 0)
        lines_layout.setSpacing(6)

        line_names = ["上爻", "五爻", "四爻", "三爻", "二爻", "初爻"]

        for i, name in enumerate(line_names):
            row = QHBoxLayout()
            row.setSpacing(10)

            # 爻名标签
            lbl = QLabel(name)
            lbl.setFixedWidth(36)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: #86868b;
                }
            """)
            row.addWidget(lbl)

            # 输入：金钱模式用 QSpinBox (0-3)，蓍草模式用 QComboBox (6,7,8,9)
            self._make_coin_input(row)
            self._make_yarrow_input(row)

            # 爻象提示标签
            hint_lbl = QLabel("")
            hint_lbl.setFixedWidth(120)
            hint_lbl.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: #aeaeb2;
                }
            """)
            row.addWidget(hint_lbl)
            self._line_labels.append(hint_lbl)

            row.addStretch()
            lines_layout.addLayout(row)

        # 初始显示金钱模式
        for w in self._yarrow_inputs:
            w.hide()

        root.addWidget(self._lines_widget)

        # ── 起卦按钮 ──
        calc_row = QHBoxLayout()
        calc_row.addStretch()
        self._btn_calc = QPushButton("起卦")
        self._btn_calc.setFixedSize(72, 30)
        self._btn_calc.setStyleSheet("""
            QPushButton {
                border: none; border-radius: 6px; background: #007aff;
                font-size: 12px; font-weight: bold; color: #ffffff;
            }
            QPushButton:hover { background: #0062cc; }
        """)
        self._btn_calc.clicked.connect(self._on_calc)
        calc_row.addWidget(self._btn_calc)
        root.addLayout(calc_row)

        # 提示信息
        self._label_info = QLabel("")
        self._label_info.setWordWrap(True)
        self._label_info.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #aeaeb2;
            }
        """)
        root.addWidget(self._label_info)

        root.addStretch()

        # 连接输入变化 → 更新爻象提示
        self._connect_hints()

    def _make_coin_input(self, row: QHBoxLayout):
        """
        创建金钱模式输入 (QSpinBox 0-3)

        值含义：
            0 = 0 个正面 → 老阴(⚋×) 变爻
            1 = 1 个正面 → 少阳(⚊)  静爻
            2 = 2 个正面 → 少阴(⚋)  静爻
            3 = 3 个正面 → 老阳(⚊○) 变爻

        Parameters:
            row: QHBoxLayout — 要添加控件到的行布局
        """
        spin = QSpinBox()
        spin.setRange(0, 3)
        spin.setFixedWidth(80)
        spin.setMinimumHeight(32)
        spin.setStyleSheet("""
            QSpinBox {
                padding: 4px 8px;
                border: 1.5px solid #dcdcdc;
                border-radius: 6px;
                font-size: 14px;
                background: #ffffff;
                color: #1d1d1f;
            }
            QSpinBox:focus {
                border-color: #007aff;
            }
        """)
        row.addWidget(spin)
        if not hasattr(self, '_coin_inputs'):
            self._coin_inputs = []
        self._coin_inputs.append(spin)

    def _make_yarrow_input(self, row: QHBoxLayout):
        """
        创建蓍草模式输入 (QComboBox 6/7/8/9)

        值含义：
            6 = 老阴(⚋×) 变爻
            7 = 少阳(⚊)  静爻
            8 = 少阴(⚋)  静爻
            9 = 老阳(⚊○) 变爻

        Parameters:
            row: QHBoxLayout — 要添加控件到的行布局
        """
        combo = QComboBox()
        combo.addItems(["6", "7", "8", "9"])
        combo.setFixedWidth(80)
        combo.setMinimumHeight(32)
        combo.setStyleSheet("""
            QComboBox {
                padding: 4px 8px;
                border: 1.5px solid #dcdcdc;
                border-radius: 6px;
                font-size: 14px;
                background: #ffffff;
                color: #1d1d1f;
            }
            QComboBox:focus {
                border-color: #007aff;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid #dcdcdc;
            }
        """)
        row.addWidget(combo)
        if not hasattr(self, '_yarrow_inputs'):
            self._yarrow_inputs = []
        self._yarrow_inputs.append(combo)

    def _connect_hints(self):
        """
        连接所有输入控件的值变化信号 → 实时更新右侧爻象提示

        信号链：
            QSpinBox.valueChanged / QComboBox.currentIndexChanged
              → _update_hints()
                → COIN_TO_YAO / YARROW_TO_YAO 查表
                  → _line_labels[i].setText(爻名 + 变爻标记)
        """
        def _update_hints():
            for i in range(6):
                if self._mode == "coin":
                    val = self._coin_inputs[i].value()
                    yao_info = COIN_TO_YAO.get(val, ("", False))
                else:
                    val = int(self._yarrow_inputs[i].currentText())
                    yao_info = YARROW_TO_YAO.get(val, ("", False))
                name, is_changing = yao_info
                suffix = " 变" if is_changing else ""
                self._line_labels[i].setText(name + suffix)

        for spin in self._coin_inputs:
            spin.valueChanged.connect(_update_hints)
        for combo in self._yarrow_inputs:
            combo.currentIndexChanged.connect(_update_hints)

    def _switch_mode(self, mode: str):
        """
        切换金钱卦 / 蓍草卦模式

        行为：
          - 显示/隐藏对应输入控件（coin 显示 QSpinBox，yarrow 显示 QComboBox）
          - 更新模式按钮样式（激活 → 蓝底白字，未激活 → 灰底黑字）
          - 触发 _update_hints 刷新爻象提示

        Parameters:
            mode: str — "coin" 或 "yarrow"
        """
        self._mode = mode

        coin_active = "background: #007aff; color: #fff; border-color: #007aff;"
        coin_inactive = "background: #f5f5f7; color: #1d1d1f; border-color: #dcdcdc;"
        base = "padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;"

        if mode == "coin":
            for w in self._coin_inputs:
                w.show()
            for w in self._yarrow_inputs:
                w.hide()
            self._btn_coin.setStyleSheet(f"QPushButton {{ {base} border: 1.5px solid #007aff; {coin_active} }}")
            self._btn_yarrow.setStyleSheet(f"QPushButton {{ {base} border: 1px solid #dcdcdc; {coin_inactive} }}")
        else:
            for w in self._coin_inputs:
                w.hide()
            for w in self._yarrow_inputs:
                w.show()
            self._btn_coin.setStyleSheet(f"QPushButton {{ {base} border: 1px solid #dcdcdc; {coin_inactive} }}")
            self._btn_yarrow.setStyleSheet(f"QPushButton {{ {base} border: 1.5px solid #007aff; {coin_active} }}")

    def _on_calc(self):
        """
        执行起卦计算

        流程：
          1. 根据 _mode 读取 6 行输入值
          2. 调用 calc_six_lines(lines, mode) → GuaResult
          3. 在 _label_info 显示每爻详情（含变爻标记）
          4. 调用 _on_result 回调通知外部

        注意：
          lines 列表顺序为 [初爻..上爻]（从下而上，index 0=初爻）
          传递给 calc_six_lines 时已按此顺序排列
        """
        if self._mode == "coin":
            lines = [self._coin_inputs[i].value() for i in range(6)]
        else:
            lines = [int(self._yarrow_inputs[i].currentText()) for i in range(6)]

        result = calc_six_lines(lines, mode=self._mode)

        # 显示每爻详情
        lines_desc = []
        for i, (name, val, is_changing) in enumerate(result.lines_data):
            marker = " ← 变爻" if is_changing else ""
            lines_desc.append(f"第{i+1}爻: {name} ({val}){marker}")
        self._label_info.setText("\n".join(lines_desc))

        if self._on_result:
            self._on_result(result)

    def set_on_result(self, callback):
        """
        设置起卦结果回调

        Parameters:
            callback: Callable[[GuaResult], None] — 接收 GuaResult 的回调函数
        """
        self._on_result = callback
