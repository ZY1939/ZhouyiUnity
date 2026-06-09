"""
诊断 LiuyaoPanel 布局问题 — 打印所有列的宽度、间距、总宽度
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontMetrics

app = QApplication(sys.argv)

from src.qigua.suangua.liuyao_panel import LiuyaoPanel
from src.qigua.hexagram_drawer import _app_font

panel = LiuyaoPanel()
panel.set_font_size(16)

fake_gz = {"year_ganzhi": "丙午", "month_ganzhi": "甲午",
           "day_ganzhi": "甲子", "day_gan": "甲", "hour_ganzhi": "甲子"}
panel.set_time_ganzhi(fake_gz)

# 用地天泰测试长标题
fake_ben = {
    "full_name": "地天泰",
    "binary": "111000",
    "judgment": "测试",
    "lines_data": [{"line_statement": f"爻{i+1}"} for i in range(6)],
}
panel.set_gua_result(fake_ben, [3])
panel.show()
app.processEvents()

print("=" * 70)
print("LiuyaoPanel 布局诊断")
print("=" * 70)

# ── 基本参数 ──
lh = panel._drawer.line_h
name_h = panel._drawer.name_area_h
print(f"\nfont_size={panel._font_size}, line_h={lh}, name_h={name_h}")

# ── Drawer ──
dr = panel._drawer
dr_geo = dr.geometry()
dr_title = dr._custom_title
print(f"\n[Drawer] title='{dr_title}'")
print(f"[Drawer] geometry: x={dr_geo.x()} y={dr_geo.y()} w={dr_geo.width()} h={dr_geo.height()}")
print(f"[Drawer] minimumWidth={dr.minimumWidth()}")
print(f"[Drawer] _bar_w={dr._bar_w}, _font_size={dr._font_size}, _name_fs={dr._name_fs}")

# 计算标题实际像素宽度
fm = QFontMetrics(_app_font())
fm_font = _app_font()
fm_font.setPointSize(dr._font_size + dr._name_fs)
fm_font.setBold(True)
fm_title = QFontMetrics(fm_font)
title_w = fm_title.horizontalAdvance(dr_title) if dr_title else 0
print(f"[Drawer] 标题像素宽度: {title_w}px (bar_w={dr._bar_w})")

# ── 左列 ──
ls = panel._liushen_marker
sy = panel._shiying_marker
btn = panel._compact_btn

print(f"\n[左列 VBox]:")
print(f"  六神: x={ls.geometry().x()} y={ls.geometry().y()} w={ls.geometry().width()} h={ls.geometry().height()}")
print(f"  世应: x={sy.geometry().x()} y={sy.geometry().y()} w={sy.geometry().width()} h={sy.geometry().height()}")
print(f"  按钮: x={btn.geometry().x()} y={btn.geometry().y()} w={btn.geometry().width()} h={btn.geometry().height()}")

ls_w = panel._liushen_marker_w
sy_w = panel._shiying_marker_w
gap_ls = panel._gap_liushen_to_shiying
left_total = ls_w + gap_ls + sy_w
print(f"  六神_w={ls_w}, 世应_w={sy_w}, gap={gap_ls}, 左列总宽={left_total}")

# ── 右列 ──
dy = panel._dongyao_marker
nl = panel._nayin_label

print(f"\n[右列]:")
print(f"  动爻: x={dy.geometry().x()} y={dy.geometry().y()} w={dy.geometry().width()} h={dy.geometry().height()}")
print(f"  纳音: x={nl.geometry().x()} y={nl.geometry().y()} w={nl.geometry().width()} h={nl.geometry().height()}")

dy_w = panel._dongyao_marker_w
nl_w = nl._fixed_w if nl else 80
gap_dn = panel._gap_dongyao_to_nayin
right_total = dy_w + gap_dn + nl_w
print(f"  动爻_w={dy_w}, 纳音_w={nl_w}, gap={gap_dn}, 右列总宽={right_total}")

# ── 间距 ──
gl = panel._gap_liuyao_left
gr = panel._gap_liuyao_right
g = panel._gap_marker_to_drawer
print(f"\n[间距]: gap_left={gl}, gap_drawer_L={g}, gap_drawer_R={g}, gap_right={gr}")

# ── 总宽度 ──
total = gl + left_total + g + dr_geo.width() + g + right_total + gr
min_w = panel.compute_min_width()
print(f"\n[总宽度计算]: {gl} + {left_total} + {g} + {dr_geo.width()} + {g} + {right_total} + {gr} = {total}")
print(f"[compute_min_width] = {min_w}")
print(f"[Panel geometry]: w={panel.geometry().width()} h={panel.geometry().height()}")
print(f"[Panel minimumWidth]: {panel.minimumWidth()}")

# ── 问题分析 ──
print(f"\n{'='*70}")
print("问题分析")
print(f"{'='*70}")

# 标题宽度 vs drawer bar_w
if title_w > dr._bar_w:
    print(f"✗ 标题太宽: {title_w}px > bar_w {dr._bar_w}px — 标题撑大了 drawer")
else:
    print(f"✓ 标题宽度 OK: {title_w}px <= bar_w {dr._bar_w}px")

# 间距检查
print(f"\n水平间距: left={gl}, L-gap={g}, R-gap={g}, right={gr}")
print(f"总padding={gl+g+g+gr}")

panel.close()
app.quit()
