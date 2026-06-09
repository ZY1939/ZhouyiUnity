"""
六爻面板调试脚本 — 测试 LiuyaoPanel 的布局、对齐和数据显示（含变卦功能）

Usage:
  cd ~/Desktop/ZhouyiUnity && python3 src/qigua/suangua/_debug/test_liuyao.py

环境变量:
  ZY_DEBUG=1   输出调试信息（对齐坐标等）
  ZY_DEBUG_BADGE=1  输出 badge 绘制信息
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,
                                QHBoxLayout, QLabel, QScrollArea)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from src.yijingTab.suangua.liuyao_panel import LiuyaoPanel
from src.yijingTab.suangua.common import compute_current_ganzhi
from src.yijingTab.com.hexagram_loader import load_all_gua


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
    win.resize(1200, 800)
    win.setStyleSheet("background: #ffffff;")

    root = QVBoxLayout(win)
    root.setContentsMargins(20, 20, 20, 20)
    root.setSpacing(8)

    # 标题
    title = QLabel("六爻面板 (LiuyaoPanel) 变卦测试")
    title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1d1d1f;")
    root.addWidget(title)

    # 当前干支显示
    gz = compute_current_ganzhi()
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
                # 打印变卦信息
                if panel._bian_info:
                    bi = panel._bian_info
                    print(f"  变卦: {bi['bian_name']}  箭头: {len(bi['arrows'])}个")
                    for idx, d, c, label in bi['arrows']:
                        print(f"    爻{idx+1}: dir={d} color={c} label={label}")
                else:
                    print(f"  无变卦（静卦）")
            else:
                print(f"[TEST] ❌ 未找到卦: {gua_name}")
        return _test

    # ── 基础测试 ──
    tests = [
        ("乾为天", [], "乾为天 (静卦—安静)"),
        ("乾为天", [1], "乾为天 (动1—变天风姤)"),
        ("乾为天", [1, 4], "乾为天 (动1,4—克+生)"),
        ("乾为天", [1, 2, 3, 4, 5, 6], "乾为天 (全动→坤)"),
        ("天风姤", [2], "天风姤 (动2)"),
        ("天地否", [1], "天地否 (动1—伏神)"),
        ("离为火", [3, 6], "离为火 (动3,6)"),
        ("坎为水", [1, 2, 5], "坎为水 (动1,2,5—多克)"),
        ("坤为地", [2], "坤为地 (动2)"),
        ("泽火革", [1, 4, 6], "泽火革 (动1,4,6)"),
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

    # ── 变卦专项测试行 ──
    bian_label = QLabel("变卦专项测试（验证箭头方向/颜色/标签）:")
    bian_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #8e44ad; margin-top: 4px;")
    root.addWidget(bian_label)

    bian_row = QHBoxLayout()
    bian_row.setSpacing(8)

    bian_tests = [
        ("火风鼎", [1], "鼎动1(子孙→官鬼:本克变→右克)"),
        ("火风鼎", [4], "鼎动4(妻财→兄弟:变克本→左克)"),
        ("水火既济", [2], "既济动2(官鬼→子孙:本克变→右克)"),
        ("水火既济", [5], "既济动5(妻财→官鬼:变生本→左生)"),
    ]

    for gua_name, cls, label_text in bian_tests:
        btn = QPushButton(label_text)
        btn.setStyleSheet("""
            QPushButton {
                font-size: 12px; padding: 4px 10px;
                background: #f5e6ff; border: 1px solid #c9a8e8;
                border-radius: 4px; color: #1d1d1f;
            }
            QPushButton:hover { background: #e8d5f5; }
        """)
        btn.clicked.connect(make_test(gua_name, cls))
        bian_row.addWidget(btn)

    bian_row.addStretch()
    root.addLayout(bian_row)

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

    # 自动测试：加载乾为天(动1,4) 验证变卦显示
    QTimer.singleShot(300, make_test("乾为天", [1, 4]))

    # DEBUG 输出
    if os.environ.get("ZY_DEBUG"):
        print(f"[DEBUG TEST] app font = {app.font().pointSize()}pt", flush=True)
        QTimer.singleShot(600, lambda: _debug_print(panel))

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

    # ── 变卦 debug ──
    if panel._bian_info:
        bi = panel._bian_info
        print(f"[DEBUG] 变卦: {bi['bian_name']} 箭头={len(bi['arrows'])}个", flush=True)
        for idx, d, c, label in bi['arrows']:
            print(f"       爻{idx+1}: dir={d} color={c} label={label}", flush=True)

    ac = panel._arrow_column
    if ac:
        print(f"[DEBUG] arrow_column: w={ac.width()} h={ac.height()} "
              f"offset_y={ac._offset_y} line_h={ac._line_h}", flush=True)

    bd = panel._bian_drawer
    if bd:
        print(f"[DEBUG] bian_drawer: line_h={bd.line_h} "
              f"name_area_h={bd.name_area_h} w={bd.width()}", flush=True)

    print(f"[DEBUG] min_w={panel.compute_min_width()}", flush=True)


def main():
    app, win, panel = build_test_window()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
