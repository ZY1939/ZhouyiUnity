"""
倒计时弹窗 — 10秒倒计时 + 每秒随机数采集 → 三位数起卦

═══════════════════════════════════════════════════════════════
文件职责：模态弹窗，10秒倒计时期间每秒生成1组3个随机三位数(000-999)，
         倒计时结束后取10组数据的平均值作为起卦输入参数。
═══════════════════════════════════════════════════════════════

计算流程：
    1. 用户点击「随机」→ 弹出弹窗，显示「开始」按钮
    2. 点击「开始」→ 10秒倒计时开始，每秒生成 (rand(0,999), rand(0,999), rand(0,999))
    3. 屏幕实时显示：倒计时数字 + 已生成的随机数预览
    4. 倒计时结束 → avg(n1) = sum(所有n1) // 10, 同理得 avg(n2), avg(n3)
    5. 1.5秒后自动关闭，result_numbers = (avg1, avg2, avg3)

被哪些文件调用：
    - divination_panel.py: _on_time_random() → CountdownDialog

用法示例:
    dlg = CountdownDialog(parent_window)
    if dlg.exec() == CountdownDialog.DialogCode.Accepted:
        n1, n2, n3 = dlg.result_numbers  # (123, 456, 789) 三个三位数
        result = calc_three_numbers(n1, n2, n3)
"""
import random
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel,
                                QPushButton, QHBoxLayout)
from PySide6.QtCore import QTimer, Qt


class CountdownDialog(QDialog):
    """
    10秒倒计时弹窗 — 大字体显示倒计时，每秒采集随机数

    属性:
        result_numbers: tuple[int, int, int] — 弹窗关闭后，外部通过此属性获取
                        最终的三位数 (n1=下卦, n2=上卦, n3=动爻)

    用法示例:
        dlg = CountdownDialog(self.window())
        if dlg.exec() == CountdownDialog.DialogCode.Accepted:
            n1, n2, n3 = dlg.result_numbers
    """

    def __init__(self, parent=None):
        """
        Parameters:
            parent: QWidget | None — 父窗口（用于模态弹窗居中）
        """
        super().__init__(parent)
        self.setWindowTitle("时间随机起卦")
        self.setFixedSize(420, 320)
        self.setModal(True)

        self._countdown = 10  # 倒计时秒数（从10倒数到0）
        self._samples: list[tuple[int, int, int]] = []  # 每秒1组 (n1, n2, n3)
        self.result_numbers: tuple[int, int, int] = (0, 0, 0)  # 最终输出（3个三位数）

        self._init_ui()

    def _init_ui(self):
        """
        构建弹窗界面：
        顶部大字体倒计时 → 中间提示文字 → 开始按钮 → 随机数预览 → 底部取消按钮
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        # ── 大字体倒计时（72px，视觉焦点）──
        self._label_countdown = QLabel(str(self._countdown))
        self._label_countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_countdown.setStyleSheet("""
            QLabel {
                font-size: 72px;
                font-weight: bold;
                color: #1d1d1f;
            }
        """)
        root.addWidget(self._label_countdown)

        # ── 提示文字 ──
        self._label_hint = QLabel("心中想一件事情，静心凝神…\n点击「开始」后启动倒计时")
        self._label_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_hint.setWordWrap(True)
        self._label_hint.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #86868b;
            }
        """)
        root.addWidget(self._label_hint)

        # ── 开始按钮（居中，蓝色醒目）──
        start_row = QHBoxLayout()
        start_row.addStretch()
        self._btn_start = QPushButton("开始")
        self._btn_start.setFixedSize(120, 44)
        self._btn_start.setStyleSheet("""
            QPushButton {
                border: none; border-radius: 10px;
                background: #007aff;
                font-size: 18px; font-weight: bold;
                color: #ffffff;
            }
            QPushButton:hover { background: #0062cc; }
            QPushButton:pressed { background: #0055aa; }
        """)
        self._btn_start.clicked.connect(self._on_start)
        start_row.addWidget(self._btn_start)
        start_row.addStretch()
        root.addLayout(start_row)

        # ── 每秒生成的随机数预览（小字，等宽）──
        self._label_samples = QLabel("")
        self._label_samples.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_samples.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #aeaeb2;
            }
        """)
        root.addWidget(self._label_samples)

        root.addStretch()

        # ── 底部取消按钮 ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_cancel = QPushButton("取消")
        self._btn_cancel.setFixedWidth(100)
        self._btn_cancel.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #dcdcdc;
                border-radius: 8px;
                background: #f5f5f7;
                font-size: 14px;
                color: #1d1d1f;
            }
            QPushButton:hover {
                background: #e8e8ed;
            }
        """)
        self._btn_cancel.clicked.connect(self.reject)  # reject → DialogCode.Rejected → 外部 discard
        btn_row.addWidget(self._btn_cancel)

        root.addLayout(btn_row)

    def _on_start(self):
        """
        点击「开始」按钮 → 隐藏按钮 → 更新提示 → 启动倒计时
        """
        self._btn_start.hide()
        self._label_hint.setText("心中想一件事情，静心凝神…\n倒计时结束后自动得卦")
        self._start_timer()

    def _start_timer(self):
        """
        启动 1 秒定时器 + 立即生成第 1 组随机数
        定时器每秒触发 _tick()，10 次后自动结束
        """
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)  # 1000ms = 1秒

        self._generate_sample()  # 立即生成第一组

    def _tick(self):
        """
        每秒回调：
        - 倒计时减 1，更新大字体显示
        - 到 0 → 停止定时器，计算结果，显示"得卦"
        - 否则 → 生成新一组随机数
        """
        self._countdown -= 1
        self._label_countdown.setText(str(self._countdown))

        if self._countdown <= 0:
            self._timer.stop()
            self._finish()
        else:
            self._generate_sample()

    def _generate_sample(self):
        """
        生成一组 3 个随机三位数 (000-999) 并加入 _samples
        同时更新预览区域显示
        """
        s = (random.randint(0, 999), random.randint(0, 999), random.randint(0, 999))
        self._samples.append(s)

        # 更新预览：每行显示 3 个三位数
        preview = "  ".join(f"{a:03d} {b:03d} {c:03d}" for a, b, c in self._samples)
        self._label_samples.setText(preview)

    def _finish(self):
        """
        倒计时结束 → 计算最终三位数 → 1.5秒后自动关闭弹窗

        计算规则：
            n1 = sum(所有第1列) // 组数
            n2 = sum(所有第2列) // 组数
            n3 = sum(所有第3列) // 组数
        （取整数平均，整数除法保证是整数）
        """
        if not self._samples:
            self.reject()
            return

        n = len(self._samples)
        avg1 = sum(s[0] for s in self._samples) // n  # 下卦
        avg2 = sum(s[1] for s in self._samples) // n  # 上卦
        avg3 = sum(s[2] for s in self._samples) // n  # 动爻
        self.result_numbers = (avg1, avg2, avg3)

        # 显示"得卦" + 蓝色文字
        self._label_countdown.setText("得卦")
        self._label_countdown.setStyleSheet("""
            QLabel {
                font-size: 48px;
                font-weight: bold;
                color: #007aff;
            }
        """)
        self._label_hint.setText(f"下卦: {avg1}  上卦: {avg2}  动爻: {avg3}")

        # 1.5 秒后自动 accept → DialogCode.Accepted → 外部读取 result_numbers
        QTimer.singleShot(1500, self.accept)
