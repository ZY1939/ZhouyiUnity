"""
对齐调试脚本 v9 — QGridLayout 方案（最终验证通过的方案）
用法: cd ~/Desktop/ZhouyiUnity && python3 src/qigua/_debug/test_alignment.py

方案说明：
  QGridLayout 列对齐：
    col0=QLabel("动爻设置" bold) / QCheckBox("上爻")
    col1=_FixedWidthSpacer(gap_lock)
    col2=QCheckBox("Lock") / QCheckBox("单动爻")
    col3=setColumnStretch(3, 1)

  Lock 和 单动爻 在同一列，天然水平对齐，不依赖 sizeHint 公式计算。

之前尝试过的失败方案记录：
  - _FixedWidthCheckBox + QHBoxLayout: 被 addStretch 压缩，QSizePolicy.Fixed 无效
  - _FixedWidthSpacer between checkboxes: macOS QCheckBox 有 -2px 布局偏移
  - setFixedWidth(sizeHint): sizeHint 在 show() 前后变化
"""
import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QGridLayout,
                                QLabel, QCheckBox, QSizePolicy)
from PySide6.QtCore import QTimer, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics


class _FixedWidthSpacer(QWidget):
    """固定宽度 Spacer"""
    def __init__(self, w: int, parent=None):
        super().__init__(parent)
        self._w = w
        self.setFixedWidth(w)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    def sizeHint(self):
        return QSize(self._w, 1)
    def minimumSizeHint(self):
        return QSize(self._w, 1)


class TestPanel(QWidget):
    """QGridLayout 对齐方案"""

    def __init__(self, font_size: int, gap_lock: int = 8):
        super().__init__()
        self._font_size = font_size
        self._gap_lock = gap_lock
        self._text_color = "#1d1d1f"
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        fm = QFont()
        fm.setPointSize(self._font_size)
        bfm = QFontMetrics(fm)
        name_h = max(16, bfm.height())
        line_h = bfm.height() + 12

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(0)
        grid.setVerticalSpacing(0)

        # Row 0: 标题行
        self._title_label = QLabel("动爻设置")
        tf = QFont()
        tf.setPointSize(self._font_size)
        tf.setBold(True)
        self._title_label.setFont(tf)
        self._title_label.setFixedHeight(name_h)
        self._title_label.setStyleSheet(f"QLabel {{ color: {self._text_color}; }}")
        grid.addWidget(self._title_label, 0, 0)

        grid.addWidget(_FixedWidthSpacer(self._gap_lock), 0, 1)

        self._lock_cb = QCheckBox("Lock")
        self._lock_cb.setStyleSheet(
            f"QCheckBox {{ spacing: 4px; color: {self._text_color}; font-size: {self._font_size - 2}px; }}")
        grid.addWidget(self._lock_cb, 0, 2, Qt.AlignmentFlag.AlignLeft)

        # Row 1: 上爻行
        cb_font = QFont()
        cb_font.setPointSize(self._font_size)

        self._shangyao_cb = QCheckBox("上爻")
        self._shangyao_cb.setFont(cb_font)
        self._shangyao_cb.setFixedHeight(line_h)
        self._shangyao_cb.setStyleSheet(f"QCheckBox {{ spacing: 8px; color: {self._text_color}; }}")
        grid.addWidget(self._shangyao_cb, 1, 0, Qt.AlignmentFlag.AlignLeft)

        self._single_line_cb = QCheckBox("单动爻")
        self._single_line_cb.setFont(cb_font)
        self._single_line_cb.setFixedHeight(line_h)
        self._single_line_cb.setStyleSheet(f"QCheckBox {{ spacing: 4px; color: {self._text_color}; }}")
        grid.addWidget(self._single_line_cb, 1, 2, Qt.AlignmentFlag.AlignLeft)

        grid.setColumnStretch(3, 1)

        root.addLayout(grid)
        root.addStretch()

    def measure(self):
        lock_x = self._lock_cb.pos().x()
        sl_x = self._single_line_cb.pos().x()
        return {"fs": self._font_size, "lock_x": lock_x, "sl_x": sl_x, "diff": sl_x - lock_x}


class TestRunner:
    def __init__(self, app):
        self._app = app
        self._fs_list = [15, 16, 17, 18]
        self._results = []
        self._idx = 0
        self._panel = None

    def start(self):
        self._idx = 0
        self._next()

    def _next(self):
        if self._idx >= len(self._fs_list):
            self._report()
            self._app.quit()
            return
        fs = self._fs_list[self._idx]
        self._panel = TestPanel(font_size=fs, gap_lock=8)
        self._panel.setWindowTitle(f"test fs={fs}")
        self._panel.resize(500, 200)
        self._panel.show()
        QTimer.singleShot(300, lambda f=fs: self._measure(f))

    def _measure(self, fs):
        self._app.processEvents()
        r = self._panel.measure()
        self._results.append(r)
        self._panel.hide()
        self._panel.deleteLater()
        self._panel = None
        self._idx += 1
        QTimer.singleShot(50, self._next)

    def _report(self):
        print("=" * 60)
        print("对齐测试 v9: QGridLayout 方案")
        print("=" * 60)
        for r in self._results:
            ok = "PASS" if abs(r['diff']) <= 2 else "FAIL"
            print(f"  fs={r['fs']:>2}:  Lock.x={r['lock_x']:>4}  单动爻.x={r['sl_x']:>4}  diff={r['diff']:>4}  {ok}")


def main():
    app = QApplication(sys.argv)
    runner = TestRunner(app)
    runner.start()
    app.exec()


if __name__ == "__main__":
    main()
