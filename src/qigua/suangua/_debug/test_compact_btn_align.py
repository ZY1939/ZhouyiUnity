"""
测试 LiuyaoPanel 精简按钮水平对齐 — 左↔六兽badge左边缘, 右↔世应badge右边缘

用法: python3 src/qigua/suangua/_debug/test_compact_btn_align.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontMetrics

app = QApplication(sys.argv)

from src.qigua.suangua.liuyao_panel import LiuyaoPanel
from src.qigua.hexagram_drawer import _app_font

# 测试多个字号
for font_size in [14, 16, 20]:
    panel = LiuyaoPanel()
    panel.set_font_size(font_size)

    fake_gz = {"year_ganzhi": "丙午", "month_ganzhi": "甲午",
               "day_ganzhi": "甲子", "day_gan": "甲", "hour_ganzhi": "甲子"}
    panel.set_time_ganzhi(fake_gz)
    fake_ben = {
        "full_name": "天风姤",
        "binary": "111110",
        "judgment": "测试",
        "lines_data": [{"line_statement": f"爻{i+1}"} for i in range(6)],
    }
    panel.set_gua_result(fake_ben, [1])
    panel.show()
    app.processEvents()

    print(f"\n{'='*70}")
    print(f"  font_size={font_size}")
    print(f"{'='*70}")

    # ── 公共参数 ──
    lh = panel._drawer.line_h
    name_h = panel._drawer.name_area_h
    liushen_w = panel._liushen_marker_w
    shiying_w = panel._shiying_marker_w
    gap = panel._gap_liushen_to_shiying

    # 六兽 badge 尺寸
    badge_fs = font_size + panel._fs_offset_liushen
    liushen_badge_side = panel._calc_badge_side(badge_fs)
    badge_left_offset = max(0, liushen_w - liushen_badge_side)

    print(f"  line_h={lh}, name_h={name_h}")
    print(f"  liushen_marker_w={liushen_w}, shiying_marker_w={shiying_w}, gap={gap}")
    print(f"  badge_fs={badge_fs}, badge_side={liushen_badge_side}, badge_left_offset={badge_left_offset}")

    # ── 按钮 ──
    btn = panel._compact_btn
    btn_geo = btn.geometry()
    print(f"\n  [精简按钮] rect: x={btn_geo.x()}, y={btn_geo.y()}, w={btn_geo.width()}, h={btn_geo.height()}")

    # ── 六神 marker ──
    lm = panel._liushen_marker
    lm_geo = lm.geometry()

    # 六兽 badge 在 marker 内的左边缘 x 坐标（right-aligned）
    # badge_x = marker_w - badge_side, badge_left_edge = badge_x
    badge_left_in_marker = liushen_w - liushen_badge_side
    print(f"  六兽 badge left edge (in marker): x={badge_left_in_marker}")

    # ── 世应 marker ──
    sm = panel._shiying_marker
    sm_geo = sm.geometry()

    # 世应 badge 在 marker 内的右边缘 x 坐标（right-aligned, badge right = marker right）
    badge_right_in_vbox = liushen_w + gap + shiying_w  # 世应 right edge in vbox coords
    print(f"  世应 badge right edge (in vbox): x={badge_right_in_vbox}")

    # ── 对齐检查 ──
    btn_left = btn_geo.x()
    btn_right = btn_geo.x() + btn_geo.width()
    print(f"\n  ═══ 对齐分析 ═══")
    print(f"  按钮 left edge: x={btn_left}  (目标: {badge_left_in_marker})")
    print(f"  按钮 right edge: x={btn_right}  (目标: {badge_right_in_vbox})")

    left_delta = btn_left - badge_left_in_marker
    right_delta = btn_right - badge_right_in_vbox

    left_ok = abs(left_delta) < 4
    right_ok = abs(right_delta) < 4

    print(f"  左对齐 Δ={left_delta}px {'✓' if left_ok else '✗'}")
    print(f"  右对齐 Δ={right_delta}px {'✓' if right_ok else '✗'}")

    # ── 坏块宽度检查 ──
    print(f"\n  按钮宽度: {btn_geo.width()}")
    print(f"  期望宽度: badge_side({liushen_badge_side}) + gap({gap}) + shiying_w({shiying_w}) = {liushen_badge_side + gap + shiying_w}")

    panel.close()

app.quit()
print(f"\n{'='*70}")
print("全部测试完成")
print(f"{'='*70}")
