"""
秒表弹窗 — 自由计时 + 3 次记录取时间戳 → 三位数起卦

═══════════════════════════════════════════════════════════════
文件职责：模态弹窗，用户点击「开始」后自由计时，点击「记录」3 次，
         从每次记录的毫秒值中提取 x.aa 作为三位数输入。
═══════════════════════════════════════════════════════════════

计算流程：
    1. 用户点击「开始」→ QElapsedTimer 启动
    2. 60fps 定时器刷新大字计时器显示 (mm:ss.ms)
    3. 用户任意时刻点击「记录」→ 记录当前 elapsed 毫秒值
    4. 重复 3 次 → 自动结束
    5. 从 3 次毫秒值提取 x.aa：
       x  = 秒的个位 (0-9)
       aa = 毫秒前两位 (0-99)
       三位数 = x * 100 + aa  → 范围 000-999
    6. 1.5 秒后自动关闭，result_numbers = (三位数1, 三位数2, 三位数3)

设计意图：
    - 利用用户自然反应时间作为随机源，比伪随机数更"有机"
    - 用户无法精确控制毫秒值，保证起卦的客观性

被哪些文件调用：
    - number_input.py: ThreeNumberWidget._on_stopwatch() → StopwatchDialog

用法示例:
    dlg = StopwatchDialog(parent)
    if dlg.exec() == StopwatchDialog.DialogCode.Accepted:
        n1, n2, n3 = dlg.result_numbers  # (123, 456, 789) 三个 000-999 的数
        result = calc_three_numbers(n1, n2, n3)
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel,
                                QPushButton, QHBoxLayout)
from PySide6.QtCore import QTimer, Qt, QElapsedTimer


class StopwatchDialog(QDialog):
    """
    秒表弹窗 — 大字体计时器 + 3 次记录 → 三位数

    属性:
        result_numbers: tuple[int, int, int] — 弹窗关闭后，外部通过此属性获取
                        最终三位数 (下卦, 上卦, 动爻)，每数范围 000-999

    内部状态:
        _elapsed: QElapsedTimer — 高精度计时器（毫秒级）
        _running: bool — 计时器是否运行中
        _records: list[int] — 已记录的毫秒值（最多 3 个）

    UI 组件:
        _label_time: 大字计时器 (56px 等宽字体)
        _label_hint: 操作提示文字
        _label_records: 3 次记录的数字回显
        _btn_record/_btn_start/_btn_cancel: 操作按钮

    用法示例:
        dlg = StopwatchDialog(self.window())
        if dlg.exec() == StopwatchDialog.DialogCode.Accepted:
            n1, n2, n3 = dlg.result_numbers
    """

    def __init__(self, parent=None):
        """
        Parameters:
            parent: QWidget | None — 父窗口（用于模态弹窗居中）
        """
        super().__init__(parent)
        self.setWindowTitle("秒表起卦")
        self.setFixedSize(420, 360)
        self.setModal(True)

        self._elapsed = QElapsedTimer()
        self._running = False
        self._records: list[int] = []  # 存储毫秒值
        self.result_numbers: tuple[int, int, int] = (0, 0, 0)

        self._init_ui()

    def _init_ui(self):
        """
        构建弹窗界面：
        顶部大字体计时器 (56px SF Mono) → 提示文字 → 记录回显区 → 底部按钮行

        按钮区包含：
          - 记录 (0/3): 蓝色主按钮，记录当前毫秒值，3 次后自动完成
          - 开始: 绿色按钮，启动 QElapsedTimer
          - 取消: 灰色按钮，关闭弹窗

        同时启动 60fps 定时器刷新计时器显示。
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(16)

        # ── 大字体计时器（56px SF Mono，等宽字体保证数字不跳）──
        self._label_time = QLabel("00:00.000")
        self._label_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_time.setStyleSheet("""
            QLabel {
                font-size: 56px;
                font-weight: bold;
                color: #1d1d1f;
                font-family: "SF Mono", "Menlo", "Courier New", monospace;
            }
        """)
        root.addWidget(self._label_time)

        # 提示文字
        self._label_hint = QLabel("静心凝神，点击「记录」3 次\n取每次时间的 x.aa 作为三位数")
        self._label_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_hint.setWordWrap(True)
        self._label_hint.setStyleSheet("""
            QLabel {
                font-size: 15px;
                color: #86868b;
            }
        """)
        root.addWidget(self._label_hint)

        # 3 次记录显示
        self._label_records = QLabel("")
        self._label_records.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_records.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #aeaeb2;
                font-family: "SF Mono", "Menlo", "Courier New", monospace;
            }
        """)
        root.addWidget(self._label_records)

        root.addStretch()

        # 底部按钮行
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        # 记录按钮
        self._btn_record = QPushButton("记录 (0/3)")
        self._btn_record.setFixedWidth(120)
        self._btn_record.setEnabled(False)
        self._btn_record.setStyleSheet("""
            QPushButton {
                padding: 10px 24px;
                border: none;
                border-radius: 10px;
                background: #007aff;
                font-size: 15px;
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton:hover {
                background: #0062cc;
            }
            QPushButton:disabled {
                background: #dcdcdc;
                color: #aeaeb2;
            }
        """)
        self._btn_record.clicked.connect(self._on_record)
        btn_row.addWidget(self._btn_record)

        btn_row.addSpacing(12)

        # 开始/取消按钮
        self._btn_start = QPushButton("开始")
        self._btn_start.setFixedWidth(100)
        self._btn_start.setStyleSheet("""
            QPushButton {
                padding: 10px 24px;
                border: none;
                border-radius: 10px;
                background: #34c759;
                font-size: 15px;
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton:hover {
                background: #2db14e;
            }
        """)
        self._btn_start.clicked.connect(self._on_start)
        btn_row.addWidget(self._btn_start)

        btn_row.addSpacing(8)

        self._btn_cancel = QPushButton("取消")
        self._btn_cancel.setFixedWidth(80)
        self._btn_cancel.setStyleSheet("""
            QPushButton {
                padding: 10px 18px;
                border: 1px solid #dcdcdc;
                border-radius: 10px;
                background: #f5f5f7;
                font-size: 15px;
                color: #1d1d1f;
            }
            QPushButton:hover {
                background: #e8e8ed;
            }
        """)
        self._btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_cancel)

        root.addLayout(btn_row)

        # 定时刷新显示
        self._display_timer = QTimer(self)
        self._display_timer.timeout.connect(self._update_display)
        self._display_timer.start(16)  # ~60fps

    def _on_start(self):
        """
        开始计时：
          - 启动 QElapsedTimer（毫秒精度）
          - 清空之前记录
          - 启用「记录」按钮
          - 禁用「开始」按钮
        """
        self._elapsed.start()
        self._running = True
        self._records.clear()
        self._btn_record.setEnabled(True)
        self._btn_record.setText("记录 (0/3)")
        self._label_records.setText("")
        self._btn_start.setEnabled(False)

    def _on_record(self):
        """
        记录当前毫秒值：
          - 调用 QElapsedTimer.elapsed() 获取当前毫秒
          - 追加到 _records 列表
          - 更新记录数显示 (n/3)
          - 回显提取后的 x.aa 数字
          - 满 3 次 → 停止计时，调用 _finish()
        """
        if not self._running:
            return

        self._records.append(self._elapsed.elapsed())
        n = len(self._records)
        self._btn_record.setText(f"记录 ({n}/3)")

        # 显示记录
        lines = []
        for i, ms in enumerate(self._records):
            x, aa = self._extract_x_aa(ms)
            lines.append(f"第{i+1}次: {x}.{aa:02d}")
        self._label_records.setText("\n".join(lines))

        if n >= 3:
            self._running = False
            self._btn_record.setEnabled(False)
            self._finish()

    def _update_display(self):
        """
        60fps 刷新计时器大字显示

        格式: mm:ss.ms
          mm = 分钟，不足补零 (00-99)
          ss = 秒，不足补零 (00-59)
          ms = 毫秒，不足补零 (000-999)
        """
        if not self._running:
            return
        ms = self._elapsed.elapsed()
        total_sec = ms // 1000
        minutes = total_sec // 60
        seconds = total_sec % 60
        millis = ms % 1000
        self._label_time.setText(f"{minutes:02d}:{seconds:02d}.{millis:03d}")

    def _extract_x_aa(self, ms: int) -> tuple[int, int]:
        """
        从毫秒值提取 x 和 aa

        计算规则：
            x  = 秒的个位 = (ms // 1000) % 10   → 范围 0-9
            aa = 毫秒前两位 = (ms % 1000) // 10  → 范围 0-99

        Parameters:
            ms: int — 毫秒值（来自 QElapsedTimer.elapsed()）

        Returns:
            tuple[int, int]: (x, aa) — x=秒个位(0-9), aa=毫秒前两位(0-99)

        用法示例:
            x, aa = self._extract_x_aa(12345)  # → (2, 34)    12.345秒
            three_digit = x * 100 + aa          # → 234
        """
        total_sec = ms // 1000
        millis = ms % 1000
        x = total_sec % 10  # 秒的个位
        aa = millis // 10  # 毫秒前两位 (0-99)
        return x, aa

    def _finish(self):
        """
        3 次记录完成 → 计算最终三位数 → 1.5 秒后自动关闭

        计算规则：
            对每笔记录的毫秒值：x = 秒个位, aa = 毫秒前两位
            三位数 = x * 100 + aa
            result_numbers = (三位数1, 三位数2, 三位数3)

        显示"得卦" + 三个数字，1.5 秒后 accept()
        """
        nums = []
        for ms in self._records:
            x, aa = self._extract_x_aa(ms)
            nums.append(x * 100 + aa)

        self.result_numbers = (nums[0], nums[1], nums[2])

        self._label_time.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                color: #007aff;
                font-family: "SF Mono", "Menlo", "Courier New", monospace;
            }
        """)
        self._label_time.setText(f"得卦: {nums[0]} {nums[1]} {nums[2]}")
        self._label_hint.setText("")

        # 1.5 秒后自动关闭
        QTimer.singleShot(1500, self.accept)
