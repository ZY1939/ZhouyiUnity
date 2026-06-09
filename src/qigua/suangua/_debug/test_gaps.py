"""
诊断 LiuyaoPanel 列间水平间距 — 像素级分析
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

from src.qigua.suangua.liuyao_panel import LiuyaoPanel

panel = LiuyaoPanel()
panel.set_font_size(16)
fake_gz = {"year_ganzhi": "丙午", "month_ganzhi": "甲午",
           "day_ganzhi": "甲子", "day_gan": "甲", "hour_ganzhi": "甲子"}
panel.set_time_ganzhi(fake_gz)
fake_ben = {
    "full_name": "地天泰", "binary": "111000", "judgment": "测试",
    "lines_data": [{"line_statement": f"爻{i+1}"} for i in range(6)],
}
panel.set_gua_result(fake_ben, [3])
panel.show()
app.processEvents()

print(f"font_size={panel._font_size}, bar_w={panel._drawer._bar_w}")
print()

# 每个 widget 的全局 x 坐标
def gx(w): return w.mapToGlobal(w.rect().topLeft()).x()
def gr(w): return gx(w) + w.width()  # right edge global x

ls = panel._liushen_marker   # 六神
sy = panel._shiying_marker   # 世应
dr = panel._drawer           # 卦图
dy = panel._dongyao_marker   # 动爻
nl = panel._nayin_label      # 纳音(六亲)
btn = panel._compact_btn     # 精简按钮

# 把坐标统一到 panel 坐标系
px0 = gx(panel)  # panel global x origin

def rx(w): return gx(w) - px0   # relative x (left)
def rr(w): return rx(w) + w.width()  # relative x (right)

print("列左右边缘 x 坐标 (相对 panel 左上角):")
print(f"  {'Column':<12s} {'left':>5s} {'right':>5s} {'width':>5s}")
print(f"  {'─'*12} {'─'*5} {'─'*5} {'─'*5}")
print(f"  {'精简按钮':<12s} {rx(btn):>5d} {rr(btn):>5d} {btn.width():>5d}")
print(f"  {'六神badge':<12s} {rx(ls):>5d} {rr(ls):>5d} {ls.width():>5d}")
print(f"  {'世应badge':<12s} {rx(sy):>5d} {rr(sy):>5d} {sy.width():>5d}")
print(f"  {'卦图drawer':<12s} {rx(dr):>5d} {rr(dr):>5d} {dr.width():>5d}")
print(f"  {'动爻badge':<12s} {rx(dy):>5d} {rr(dy):>5d} {dy.width():>5d}")
print(f"  {'纳音(六亲)':<12s} {rx(nl):>5d} {rr(nl):>5d} {nl.width():>5d}")

print(f"\n列间间隙 (像素):")
gaps = [
    ("六神right → 世应left", rr(ls), rx(sy)),
    ("世应right → 卦图left", rr(sy), rx(dr)),
    ("卦图right → 动爻left", rr(dr), rx(dy)),
    ("动爻right → 纳音left", rr(dy), rx(nl)),
]
for name, a, b in gaps:
    gap = b - a
    print(f"  {name:<28s}: {gap:>3d} px  {'⚠️ 宽' if gap > 6 else '✓'}")

print(f"\nPanel 总宽度: {panel.width()} px")
print(f"compute_min_width: {panel.compute_min_width()} px")

panel.close()
app.quit()
