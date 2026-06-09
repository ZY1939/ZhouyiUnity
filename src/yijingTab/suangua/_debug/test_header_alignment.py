"""
调试脚本 — 测量 QiguaPanel 和 SuanguaPanel header 的垂直对齐

Usage:
  cd ~/Desktop/ZhouyiUnity && ZY_DEBUG=1 python3 src/qigua/suangua/_debug/test_header_alignment.py

检查要点：
  - 两个面板 header 的 title label 顶部 Y 坐标
  - 两个面板 frame 的顶部 Y 坐标
  - top_spacer 在各字号下的实际值
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
os.environ["ZY_DEBUG"] = "1"

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                                QLabel, QPushButton, QScrollArea, QFrame)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontMetrics

from src.yijingTab.qigua.divination_panel import QiguaPanel
from src.yijingTab.suangua.suangua_panel import SuanguaPanel
from src.yijingTab.CONST_DEFINE_UI import QiguaConfig, SuanguaConfig
from src.yijingTab.com.hexagram_drawer import HexagramDrawer, _app_font


def measure_positions(qigua_panel, suangua_panel, font_size, label=""):
    """测量两个面板 header 的关键坐标"""
    print(f"\n{'='*60}")
    print(f"测量: font_size={font_size} {label}")
    print(f"{'='*60}")

    # ── QiguaPanel ──
    qp = qigua_panel
    qf = qp._border_frame
    qt = qp._title_label

    # 全局坐标映射
    qt_global = qt.mapToGlobal(qt.pos())
    qf_global = qf.mapToGlobal(qf.pos())
    qp_global = qp.mapToGlobal(qp.pos())

    print(f"\n[QiguaPanel - 起卦]")
    print(f"  QiguaPanel 全局 Y:        {qp_global.y()}")
    print(f"  border_frame 全局 Y:      {qf_global.y()}")
    print(f"  title_label 全局 Y:       {qt_global.y()}")
    print(f"  title_label 高度:         {qt.height()}")
    print(f"  title_label 中心 Y:       {qt_global.y() + qt.height() // 2}")
    print(f"  drawer.line_h:            {qp._drawer.line_h}")
    print(f"  _gap_md:                  {qp._gap_md}")
    print(f"  border_frame→title 偏移:  {qt_global.y() - qf_global.y()}")

    # ── SuanguaPanel ──
    sp = suangua_panel
    sf = sp._suangua_frame
    st = sp._title_label

    st_global = st.mapToGlobal(st.pos())
    sf_global = sf.mapToGlobal(sf.pos())
    sp_global = sp.mapToGlobal(sp.pos())

    print(f"\n[SuanguaPanel - 算卦]")
    print(f"  SuanguaPanel 全局 Y:      {sp_global.y()}")
    print(f"  suangua_frame 全局 Y:     {sf_global.y()}")
    print(f"  title_label 全局 Y:       {st_global.y()}")
    print(f"  title_label 高度:         {st.height()}")
    print(f"  title_label 中心 Y:       {st_global.y() + st.height() // 2}")
    print(f"  _title_lh:                {sp._title_lh}")
    print(f"  _header_row_h:            {sp._header_row_h}")
    print(f"  _ydist_menu2top:          {sp._ydist_menu2top}")
    print(f"  suangua_frame→title 偏移: {st_global.y() - sf_global.y()}")

    # top_spacer 实际值
    top_item = sp._frame_layout.itemAt(0)
    top_spacer_h = 0
    if top_item and top_item.spacerItem():
        top_spacer_h = top_item.spacerItem().geometry().height()
    print(f"  top_spacer 实际高度:      {top_spacer_h}")
    print(f"  top_gap 公式值:           {max(0, sp._ydist_menu2top - sp._header_row_h // 2)}")

    # ── 关键对比 ──
    qigua_title_top = qf_global.y()
    suangua_title_top = sf_global.y()

    # 两个 title label 的相对偏移
    title_offset = st_global.y() - qt_global.y()
    frame_offset = sf_global.y() - qf_global.y()

    print(f"\n[对齐分析]")
    print(f"  suangua_frame - border_frame Y 偏移:  {frame_offset} px")
    print(f"  算卦title - 起卦title Y 偏移:          {title_offset} px")
    if title_offset > 1:
        print(f"  ⚠️ 算卦面板 header 低了 {title_offset} px")
    elif title_offset < -1:
        print(f"  ⚠️ 算卦面板 header 高了 {-title_offset} px")
    else:
        print(f"  ✓ 两个 header 基本对齐 (偏差 ≤1px)")

    # 两个 frame 是否在同一水平线
    if abs(frame_offset) > 0:
        print(f"  ⚠️ frame 不在同一水平线，偏移 {frame_offset} px")
    else:
        print(f"  ✓ frame 在同一水平线")


def build_test_window():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setFont(QFont("PingFang SC", 16))

    win = QWidget()
    win.setWindowTitle("Header对齐调试 — QiguaPanel vs SuanguaPanel")
    win.resize(1400, 800)
    win.setStyleSheet("background: #ffffff;")

    root = QVBoxLayout(win)
    root.setContentsMargins(10, 10, 10, 10)
    root.setSpacing(6)

    # 说明
    info = QLabel("Header 垂直对齐调试 — 查看终端输出 (ZY_DEBUG=1)")
    info.setStyleSheet("font-size: 16px; font-weight: bold; color: #1d1d1f;")
    root.addWidget(info)

    # 字号控制
    ctrl_row = QHBoxLayout()
    ctrl_row.setSpacing(8)

    font_label = QLabel("字号:")
    font_label.setStyleSheet("font-size: 14px; color: #666;")
    ctrl_row.addWidget(font_label)

    qp = QiguaPanel()
    sp = qp._suangua_panel

    # 记录初始测量
    initial_measures = []

    def measure_current(msg=""):
        measure_positions(qp, sp, app.font().pointSize(), msg)

    def set_fs(fs):
        print(f"\n>>> 切换字号到 {fs}pt <<<")
        app.setFont(QFont("PingFang SC", fs))
        qp.refresh_font_size(fs)

    for fs in [12, 14, 16, 20, 24]:
        btn = QPushButton(f"{fs}pt")
        btn.setStyleSheet("font-size: 13px; padding: 4px 10px;")
        btn.clicked.connect(lambda checked, f=fs: set_fs(f))
        ctrl_row.addWidget(btn)

    measure_btn = QPushButton("测量当前")
    measure_btn.setStyleSheet("font-size: 13px; padding: 4px 10px; background: #007aff; color: #fff; border-radius: 4px;")
    measure_btn.clicked.connect(lambda: measure_current())
    ctrl_row.addWidget(measure_btn)

    ctrl_row.addStretch()
    root.addLayout(ctrl_row)

    # 分隔线
    sep = QLabel()
    sep.setFixedHeight(1)
    sep.setStyleSheet("background: #ddd;")
    root.addWidget(sep)

    # 面板区
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(qp)
    container_layout.addStretch()

    scroll.setWidget(container)
    root.addWidget(scroll, 1)

    # 首次测量（延迟等布局完成）
    QTimer.singleShot(300, lambda: measure_current("初始(16pt)"))

    return app, win, qp, sp


def main():
    app, win, qp, sp = build_test_window()
    win.show()

    # 再测一次（show 后布局可能再变）
    QTimer.singleShot(600, lambda: measure_positions(qp, sp, app.font().pointSize(), "show后(16pt)"))

    app.exec()


if __name__ == "__main__":
    main()
