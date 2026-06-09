"""
按钮对齐测试 — 验证 保存↔随机 同x, 读取↔秒表 同x

测试项：
  1. 保存.x == 随机.x   (保存按钮在随机按钮正下方)
  2. 读取.x == 秒表.x   (读取按钮在秒表按钮正下方)
  3. 所有按钮在同一行 (y 坐标一致)
  4. toolbar 按钮顺序: 截图 < AI < 保存 < 读取 (x 递增)

⚠️ 重要踩坑：此测试中 app.processEvents() 让 Qt 布局完成，所以 width() 返回正确值。
但在真实 app 中 apply_appearance 在首次 resizeEvent 同步调用，布局未完成，
width() 返回旧值。因此 refresh_font_size 链中所有地方必须用 minimumWidth()。
此测试验证的是「布局完成后的对齐结果」，不验证「resize 事件中的 width() 可靠性」。

用法：
  cd ~/Desktop/ZhouyiUnity
  python3 src/yijingTab/_debug/test_button_alignment.py
"""
import sys
sys.path.insert(0, '.')

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout


def run_test():
    app = QApplication.instance() or QApplication(sys.argv)

    from src.yijingTab.qigua.divination_panel import QiguaPanel

    w = QWidget()
    w.resize(1400, 800)
    w.setStyleSheet('background: #ffffff;')
    ly = QVBoxLayout(w)
    ly.setContentsMargins(0, 0, 0, 0)
    panel = QiguaPanel()
    ly.addWidget(panel)
    w.show()
    app.processEvents()

    # 切换到报数模式
    panel._dots[1].setChecked(True)
    panel._switch_method("three")
    app.processEvents()

    bar = panel._button_bar
    rand_btn = getattr(panel, '_btn_random', None)
    sw_btn = getattr(panel, '_btn_sw', None)

    # ── 坐标采集 ──
    rand_p = rand_btn.mapTo(panel, rand_btn.rect().topLeft())
    sw_p = sw_btn.mapTo(panel, sw_btn.rect().topLeft())

    positions = []
    for btn in bar._btns:
        p = btn.mapTo(panel, btn.rect().topLeft())
        positions.append(p)

    # ── 输出 ──
    print("=" * 60)
    print("按钮对齐测试")
    print("=" * 60)

    print(f"\n报数面板 (y={rand_p.y()}):")
    print(f"  随机  x={rand_p.x()}  x_right={rand_p.x() + rand_btn.width()}")
    print(f"  秒表  x={sw_p.x()}  x_right={sw_p.x() + sw_btn.width()}")

    print(f"\nToolbar (y={positions[0].y()}):")
    names = ["截图", "AI", "保存", "读取"]
    for i, p in enumerate(positions):
        r = p.x() + bar._btns[i].width()
        print(f"  {names[i]:4s}  x={p.x():>4}  x_right={r:>4}")

    # ── ASCII 对比图 ──
    print(f"\n{'─' * 40}")
    print(f"x 坐标对比 (同一个 x → 垂直对齐):")
    print(f"")
    print(f"  报数:   [{(' '*rand_p.x())}随机{' ' * (sw_p.x() - rand_p.x() - rand_btn.width())}秒表]")
    print(f"  工具栏: [{(' '*positions[0].x())}截图  AI{(' ' * max(0, positions[2].x() - positions[1].x() - bar._btns[1].width()))}保存{' ' * (positions[3].x() - positions[2].x() - bar._btns[2].width())}读取]")
    print(f"")
    x_labels = f"          "
    for xv in [0, 69, 111, 180]:
        x_labels += f"{xv:<8}"
    print(f"          {x_labels}")
    print(f"{'─' * 40}")

    # ── 验证 ──
    all_ok = True
    print(f"\n验证:")

    ok1 = abs(positions[2].x() - rand_p.x()) <= 1
    print(f"  {'✅' if ok1 else '❌'} 保存.x={positions[2].x()} == 随机.x={rand_p.x()}  diff={abs(positions[2].x() - rand_p.x())}")
    if not ok1: all_ok = False

    ok2 = abs(positions[3].x() - sw_p.x()) <= 1
    print(f"  {'✅' if ok2 else '❌'} 读取.x={positions[3].x()} == 秒表.x={sw_p.x()}  diff={abs(positions[3].x() - sw_p.x())}")
    if not ok2: all_ok = False

    ys = {p.y() for p in positions}
    ok3 = len(ys) == 1
    print(f"  {'✅' if ok3 else '❌'} 单行: y={ys}")
    if not ok3: all_ok = False

    xs = [p.x() for p in positions]
    ok4 = xs == sorted(xs)
    print(f"  {'✅' if ok4 else '❌'} 从左到右: {xs}")
    if not ok4: all_ok = False

    for i, btn in enumerate(bar._btns):
        if btn.height() != rand_btn.height():
            print(f"  ❌ btn[{i}] h={btn.height()} != {rand_btn.height()}")
            all_ok = False
            break
    else:
        print(f"  ✅ 高度一致: {rand_btn.height()}px")

    # ── ButtonBar 在 border_frame 内的位置 ──
    bar_pos_in_frame = bar.mapTo(panel._border_frame, bar.rect().topLeft())
    print(f"\n  ButtonBar 在 border_frame 内位置: x={bar_pos_in_frame.x()} y={bar_pos_in_frame.y()}")
    print(f"  border_frame 在 panel 内位置: x={panel._border_frame.mapTo(panel, panel._border_frame.rect().topLeft()).x()}")

    # ── border_frame 内逐一映射诊断（与 divination_panel._check_btn_alignment 等效）──
    print(f"\n  border_frame 内逐一映射 (QPoint(0,0)):")
    bf = panel._border_frame
    rand_x_bf = rand_btn.mapTo(bf, QPoint(0, 0)).x()
    sw_x_bf = sw_btn.mapTo(bf, QPoint(0, 0)).x()
    save_x_bf = bar._btns[bar._I_SAVE].mapTo(bf, QPoint(0, 0)).x()
    load_x_bf = bar._btns[bar._I_LOAD].mapTo(bf, QPoint(0, 0)).x()
    print(f"    随机.x={rand_x_bf}  保存.x={save_x_bf}  diff={abs(rand_x_bf - save_x_bf)}")
    print(f"    秒表.x={sw_x_bf}  读取.x={load_x_bf}  diff={abs(sw_x_bf - load_x_bf)}")

    print(f"\n{'✅ 全部通过' if all_ok else '❌ 存在问题'}")
    app.quit()
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(run_test())
