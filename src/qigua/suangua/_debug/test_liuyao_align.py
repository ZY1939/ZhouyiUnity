"""
测试 LiuyaoPanel 布局对齐 — 精简按钮/六神/世应/纳音/伏神 坐标分析

用法: python3 src/qigua/suangua/_debug/test_liuyao_align.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from src.qigua.suangua.liuyao_panel import LiuyaoPanel
from src.algorithms.liuyao import get_fushen

TEST_CASES = [
    {"name": "天风姤", "binary": "111110", "changing": [1],
     "desc": "4个伏神（初至四爻），乾宫一世卦"},
    {"name": "乾为天", "binary": "111111", "changing": [6],
     "desc": "0个伏神（八纯卦）"},
    {"name": "风地观", "binary": "110000", "changing": [6],
     "desc": "6个伏神（乾宫四世卦）"},
    {"name": "火山旅", "binary": "001101", "changing": [4],
     "desc": "3个伏神（离宫一世卦）"},
]

fake_gz = {"year_ganzhi": "丙午", "month_ganzhi": "甲午",
           "day_ganzhi": "甲子", "day_gan": "甲", "hour_ganzhi": "甲子"}

errors = []

for tc in TEST_CASES:
    panel = LiuyaoPanel()
    panel.set_font_size(16)
    panel.set_time_ganzhi(fake_gz)

    fake_ben = {
        "full_name": tc["name"],
        "binary": tc["binary"],
        "judgment": "测试",
        "lines_data": [{"line_statement": f"爻{i+1}"} for i in range(6)],
    }
    panel.set_gua_result(fake_ben, tc["changing"])
    panel.show()
    app.processEvents()

    print("=" * 70)
    print(f"  卦: {tc['name']} — {tc['desc']}")
    print("=" * 70)

    lh = panel._drawer.line_h
    name_h = panel._drawer.name_area_h
    print(f"  line_h={lh}, name_h={name_h}")

    # ── 全局坐标 ──
    dr_gy = panel._drawer.mapToGlobal(panel._drawer.rect().topLeft()).y()
    btn = panel._compact_btn
    btn_gy = btn.mapToGlobal(btn.rect().topLeft()).y()
    lm_gy = panel._liushen_marker.mapToGlobal(panel._liushen_marker.rect().topLeft()).y()
    sm_gy = panel._shiying_marker.mapToGlobal(panel._shiying_marker.rect().topLeft()).y()
    nl_gy = panel._nayin_label.mapToGlobal(panel._nayin_label.rect().topLeft()).y()
    # ── 按钮 ↔ drawer title ──
    btn_center = btn_gy + btn.height() // 2
    dr_title_center = dr_gy + name_h // 2
    d1 = btn_center - dr_title_center
    ok1 = abs(d1) < 6
    print(f"  {'✓' if ok1 else '✗'} 按钮↔drawer title: Δ={d1:.0f}px")
    if not ok1: errors.append(f"{tc['name']}: btn↔title Δ={d1:.0f}")

    # ── 伏神数据 ──
    fs_count = sum(1 for f in (panel._fushen_data or []) if f)
    print(f"  伏神: {fs_count} 个")
    for i, fs in enumerate(panel._fushen_data or []):
        if fs:
            print(f"    第{i+1}爻: {fs['liuqin']}-{fs['najia']}{fs['zhi']} ({fs['dizhi_wuxing']})")

    # ── 每爻对齐检查 ──
    # Drawer 爻 center_y (全局): dr_gy + name_h + pos*lh + lh//2
    #   pos=0 → 上爻(top), pos=5 → 初爻(bottom)
    # 六神 marker 爻 center_y (全局): lm_gy + pos*lh + lh//2 (offset_y=-name_h 已抵消 name_area_h)
    #   但 line_idx=5→绘制在pos=0(上爻), line_idx=0→pos=5(初爻)
    # 纳音/伏神 label 爻 center_y: nl_gy/fl_gy + name_h + pos*lh + lh//2
    #   同样 line_idx=5→pos=0, line_idx=0→pos=5

    print(f"\n  {'爻':4s} {'Drawer':>8s} {'六神':>8s} {'世应':>8s} {'纳音':>8s}")
    row_errors = 0
    for pos in range(6):  # pos=0 上爻(top), pos=5 初爻(bottom)
        line_name = ["上", "五", "四", "三", "二", "初"][pos]

        dr_y = dr_gy + name_h + pos * lh + lh // 2
        lm_y = lm_gy + pos * lh + lh // 2  # offset_y=-name_h 抵消了 name_area_h
        sm_y = sm_gy + pos * lh + lh // 2
        nl_y = nl_gy + name_h + pos * lh + lh // 2

        d_lm = lm_y - dr_y
        d_sm = sm_y - dr_y
        d_nl = nl_y - dr_y

        lm_ok = "✓" if abs(d_lm) < 6 else "✗"
        sm_ok = "✓" if abs(d_sm) < 6 else "✗"
        nl_ok = "✓" if abs(d_nl) < 6 else "✗"

        print(f"  {line_name:4s} {dr_y:8.0f} {lm_ok}{d_lm:+5.0f}  {sm_ok}{d_sm:+5.0f}  {nl_ok}{d_nl:+5.0f}")

        for tag, delta, ok in [("六神", d_lm, lm_ok), ("世应", d_sm, sm_ok),
                                ("纳音", d_nl, nl_ok)]:
            if ok == "✗":
                row_errors += 1
                errors.append(f"{tc['name']} {line_name}爻 {tag} Δ={delta:.0f}")

    print(f"  行对齐错误: {row_errors} 处")

    # ── 伏神 drawer 检查 ──
    dr_fs = panel._drawer._fushen_texts
    dr_fs_count = sum(1 for t in dr_fs if t)
    if fs_count != dr_fs_count:
        err = f"{tc['name']}: 伏神数据{fs_count}个 ≠ drawer {dr_fs_count}个"
        print(f"  ✗ {err}")
        errors.append(err)
    if dr_fs_count > 0:
        print(f"  [伏神 drawer]: {[t for t in dr_fs if t]}")

    panel.close()
    print()

print()
print("=" * 70)
if errors:
    print(f"❌ {len(errors)} 个错误:")
    for e in errors:
        print(f"   {e}")
else:
    print("✓ 全部测试通过")
print("=" * 70)

app.quit()
