"""
六爻面板调试脚本 — 测试 LiuyaoPanel 的布局、对齐和数据显示

Usage:
  cd ~/Desktop/ZhouyiUnity && python3 src/qigua/suangua/_debug/test_liuyao.py

环境变量:
  ZY_DEBUG=1   输出调试信息（对齐坐标等）
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,
                                QHBoxLayout, QLabel, QScrollArea)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from src.qigua.suangua.liuyao_panel import LiuyaoPanel, _compute_current_ganzhi
from src.qigua.hexagram_loader import load_all_gua


def find_gua_data(gua_name: str) -> dict | None:
    """在数据库中查找指定卦名的数据"""
    all_gua = load_all_gua()
    for gid, data in all_gua.items():
        if data.get("full_name") == gua_name:
            return data
    return None


def build_test_window():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setFont(QFont("PingFang SC", 16))

    win = QWidget()
    win.setWindowTitle("六爻面板测试 — LiuyaoPanel Debug")
    win.resize(1100, 750)
    win.setStyleSheet("background: #ffffff;")

    root = QVBoxLayout(win)
    root.setContentsMargins(20, 20, 20, 20)
    root.setSpacing(8)

    # 标题
    title = QLabel("六爻面板 (LiuyaoPanel) 测试")
    title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1d1d1f;")
    root.addWidget(title)

    # 当前干支显示
    gz = _compute_current_ganzhi()
    gz_label = QLabel(
        f"当前时间: {gz['year_ganzhi']}年 {gz['month_ganzhi']}月 "
        f"{gz['day_ganzhi']}日 {gz['hour_ganzhi']}时  "
        f"日干={gz['day_gan']}"
    )
    gz_label.setStyleSheet("font-size: 14px; color: #666;")
    root.addWidget(gz_label)

    # 测试按钮行
    btn_row = QHBoxLayout()
    btn_row.setSpacing(8)

    panel = LiuyaoPanel()

    def make_test(gua_name, changing_lines):
        def _test():
            data = find_gua_data(gua_name)
            if data:
                print(f"[TEST] 加载 {gua_name} 动爻={changing_lines}")
                panel.set_gua_result(data, changing_lines)
            else:
                print(f"[TEST] ❌ 未找到卦: {gua_name}")
        return _test

    tests = [
        ("乾为天", [1, 4], "乾为天 (动爻1,4)"),
        ("乾为天", [], "乾为天 (静卦)"),
        ("天风姤", [2], "天风姤 (动爻2)"),
        ("离为火", [3, 6], "离为火 (动爻3,6)"),
        ("坎为水", [1, 2, 5], "坎为水 (动爻1,2,5)"),
        ("坤为地", [2], "坤为地 (动爻2)"),
        ("泽火革", [1, 4, 6], "泽火革 (动爻1,4,6)"),
    ]

    for gua_name, cls, label_text in tests:
        btn = QPushButton(label_text)
        btn.setStyleSheet("""
            QPushButton {
                font-size: 13px; padding: 5px 12px;
                background: #f0f0f0; border: 1px solid #ccc;
                border-radius: 4px; color: #1d1d1f;
            }
            QPushButton:hover { background: #e0e0e0; }
        """)
        btn.clicked.connect(make_test(gua_name, cls))
        btn_row.addWidget(btn)

    btn_row.addStretch()
    root.addLayout(btn_row)

    # 分隔线
    sep = QLabel()
    sep.setFixedHeight(1)
    sep.setStyleSheet("background: #ddd;")
    root.addWidget(sep)

    # 面板容器（ScrollArea 确保内容溢出可滚动）
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(panel)
    container_layout.addStretch()

    scroll.setWidget(container)
    root.addWidget(scroll, 1)

    # 自动测试：加载第一个测试
    QTimer.singleShot(200, make_test("乾为天", [1, 4]))

    # DEBUG 输出
    if os.environ.get("ZY_DEBUG"):
        print(f"[DEBUG TEST] app font = {app.font().pointSize()}pt", flush=True)
        QTimer.singleShot(500, lambda: _debug_print(panel))

    return app, win, panel


def _debug_print(panel: LiuyaoPanel):
    """打印调试信息"""
    d = panel._drawer
    if d:
        print(f"[DEBUG] drawer: line_h={d.line_h} name_area_h={d.name_area_h} "
              f"bar_h={d._bar_h} bar_w={d._bar_w} offset_y={d._offset_y} "
              f"min_w={d.minimumWidth()}", flush=True)

    for name, marker in [("六神", panel._liushen_marker),
                          ("世应", panel._shiying_marker),
                          ("动爻", panel._dongyao_marker)]:
        if marker:
            print(f"[DEBUG] {name} marker: w={marker.width()} "
                  f"markers={[(ln, txt) for ln, txt, _, _ in marker._markers]}", flush=True)

    nl = panel._nayin_label
    if nl:
        print(f"[DEBUG] 纳音: w={nl._fixed_w} items={[(ln, txt) for ln, txt, _ in nl._items]}",
              flush=True)

    print(f"[DEBUG] min_w={panel.compute_min_width()}", flush=True)


def main():
    app, win, panel = build_test_window()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
