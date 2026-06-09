"""
测试 QGridLayout Row 0 高度：title_label+lock_cb 的 setFixedHeight(name_h) 是否被遵守
用法: cd ~/Desktop/ZhouyiUnity && python3 src/qigua/_debug/test_grid_row_height.py
"""
import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QGridLayout,
                                QLabel, QCheckBox, QSizePolicy)
from PySide6.QtCore import QTimer, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics


class _FixedWidthSpacer(QWidget):
    def __init__(self, w, parent=None):
        super().__init__(parent)
        self._w = w
        self.setFixedWidth(w)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    def sizeHint(self):
        return QSize(self._w, 1)
    def minimumSizeHint(self):
        return QSize(self._w, 1)


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
        self._panel = QWidget()
        self._panel.setWindowTitle(f"test fs={fs}")
        self._panel.resize(500, 200)
        lay = QVBoxLayout(self._panel)
        lay.setContentsMargins(0, 0, 0, 0)

        fm = QFont()
        fm.setPointSize(fs)
        bfm = QFontMetrics(fm)
        name_h = max(16, bfm.height())
        line_h = bfm.height() + 12

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(0)
        grid.setVerticalSpacing(0)

        # Row 0: title label + spacer + lock cb
        self._title_label = QLabel("动爻设置")
        tf = QFont(); tf.setPointSize(fs); tf.setBold(True)
        self._title_label.setFont(tf)
        self._title_label.setFixedHeight(name_h)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(self._title_label, 0, 0)

        grid.addWidget(_FixedWidthSpacer(8), 0, 1)

        self._lock_cb = QCheckBox("Lock")
        self._lock_cb.setFixedHeight(name_h)
        self._lock_cb.setStyleSheet(f"QCheckBox {{ spacing: 4px; font-size: {fs - 2}px; }}")
        grid.addWidget(self._lock_cb, 0, 2, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        # Row 1: 上爻 cb + 单动爻 cb
        cb_font = QFont(); cb_font.setPointSize(fs)
        self._shangyao = QCheckBox("上爻")
        self._shangyao.setFont(cb_font)
        self._shangyao.setFixedHeight(line_h)
        grid.addWidget(self._shangyao, 1, 0, Qt.AlignmentFlag.AlignLeft)

        self._single = QCheckBox("单动爻")
        self._single.setFont(cb_font)
        self._single.setFixedHeight(line_h)
        grid.addWidget(self._single, 1, 2, Qt.AlignmentFlag.AlignLeft)

        grid.setColumnStretch(3, 1)
        lay.addLayout(grid)
        lay.addStretch()

        self._panel.show()
        QTimer.singleShot(300, self._measure)

    def _measure(self):
        self._app.processEvents()
        fs = self._fs_list[self._idx]
        r = {
            "fs": fs,
            "title_sizeHint_h": self._title_label.sizeHint().height(),
            "title_minHint_h": self._title_label.minimumSizeHint().height(),
            "title_actual_h": self._title_label.height(),
            "title_y": self._title_label.pos().y(),
            "lock_sizeHint_h": self._lock_cb.sizeHint().height(),
            "lock_minHint_h": self._lock_cb.minimumSizeHint().height(),
            "lock_actual_h": self._lock_cb.height(),
            "lock_y": self._lock_cb.pos().y(),
            "lock_x": self._lock_cb.pos().x(),
            "single_x": self._single.pos().x(),
        }
        self._results.append(r)
        self._panel.hide()
        self._panel.deleteLater()
        self._panel = None
        self._idx += 1
        QTimer.singleShot(50, self._next)

    def _report(self):
        print("=" * 75)
        print("QGridLayout Row 0 高度诊断")
        print("=" * 75)
        for r in self._results:
            h_diff = r["lock_actual_h"] - r["title_actual_h"]
            y_diff = r["lock_y"] - r["title_y"]
            x_diff = r["single_x"] - r["lock_x"]
            print(f"fs={r['fs']:>2}: title sizeHint={r['title_sizeHint_h']} minHint={r['title_minHint_h']} actual={r['title_actual_h']} y={r['title_y']}")
            print(f"       lock  sizeHint={r['lock_sizeHint_h']} minHint={r['lock_minHint_h']} actual={r['lock_actual_h']} y={r['lock_y']}")
            print(f"       高度diff={h_diff} y_diff={y_diff} 水平diff={x_diff}")
            print()


def main():
    app = QApplication(sys.argv)
    runner = TestRunner(app)
    runner.start()
    app.exec()


if __name__ == "__main__":
    main()
