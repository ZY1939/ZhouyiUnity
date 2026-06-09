"""手工面板交互功能回归测试 — 单动爻 / Lock / 卦图点击 / 动爻复选框 / suangua 转发 / 梅花切换"""
import sys
sys.path.insert(0, ".")
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt, QPoint
from src.qigua.divination_panel import QiguaPanel

app = QApplication(sys.argv)

p = QiguaPanel()
p.show()
app.processEvents()

_failures = 0

def header(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")

def check(cond, msg):
    global _failures
    if not cond:
        print(f"  ❌ FAIL: {msg}")
        _failures += 1
        return False
    return True

# ── 前置检查 ──
header("前置检查")
cb_ok = check(hasattr(p, '_single_line_cb') and p._single_line_cb is not None,
              "_single_line_cb 不存在")
if not cb_ok:
    print("  单动爻控件不存在，终止测试")
    sys.exit(1)
print(f"  _manual_cbs count: {len(p._manual_cbs)}")
print(f"  _lock_cbs count: {len(p._lock_cbs)}")
print(f"  _suangua_panel exists: {hasattr(p, '_suangua_panel') and p._suangua_panel is not None}")
print(f"  drawer _clickable: {p._drawer._clickable}")
print(f"  current_method: {p._current_method}")

# ═══════════════════════════════════════════════════════════
#  测试1: 多动爻 + 勾选单动爻 → 仅保留最大
# ═══════════════════════════════════════════════════════════
header("测试1: 多动爻 + 勾选单动爻 → 仅保留最大动爻")

# 先模拟多选：勾选二爻、四爻、上爻
p._manual_cbs[4].setChecked(True)   # 二爻 line_num=2
p._manual_cbs[2].setChecked(True)   # 四爻 line_num=4
p._manual_cbs[0].setChecked(True)   # 上爻 line_num=6
app.processEvents()
print(f"  多选后 _changing_lines: {p._changing_lines}")
check(p._changing_lines == {2, 4, 6}, f"多选失败，期望 {{2,4,6}} 实际 {p._changing_lines}")

# 勾选单动爻 → 应仅保留最大(6)
p._single_line_cb.setChecked(True)
app.processEvents()
print(f"  勾选单动爻后 _changing_lines: {p._changing_lines}")
if check(p._changing_lines == {6}, f"期望仅 {{6}}，实际 {p._changing_lines}"):
    print("  ✅ 多动爻→勾选单动爻→仅保留最大(6)")
if check(p._single_line_cb.isChecked(), "单动爻应保持勾选状态"):
    print("  ✅ 单动爻保持勾选")
# 验证其他复选框已被取消
others = [p._manual_cbs[i].isChecked() for i in range(1, 6)]
check(not any(others), f"其他爻应全部取消，实际 {others}")

# 取消单动爻 → 应清空
p._single_line_cb.setChecked(False)
app.processEvents()
if check(len(p._changing_lines) == 0, f"取消单动爻后应清空，实际 {p._changing_lines}"):
    print("  ✅ 取消单动爻 → 清空动爻")
all_unchecked = not any(p._manual_cbs[i].isChecked() for i in range(6))
check(all_unchecked, "取消单动爻后所有动爻复选框应取消")

# ═══════════════════════════════════════════════════════════
#  测试2: 单动爻模式下切换动爻（单选行为）
# ═══════════════════════════════════════════════════════════
header("测试2: 单动爻模式下切换动爻 → 单选行为")

# 2a: 无动爻时勾选单动爻 → 不自动选爻
p._single_line_cb.setChecked(True)
app.processEvents()
print(f"  勾选单动爻(无动爻): _changing_lines={p._changing_lines}")
check(len(p._changing_lines) == 0, f"无动爻时勾选单动爻应不自动选爻，实际 {p._changing_lines}")
all_unchecked = not any(p._manual_cbs[i].isChecked() for i in range(6))
check(all_unchecked, "无动爻时勾选单动爻→所有复选框应不勾选")
print("  ✅ 2a: 无动爻时勾选单动爻 → 不自动选爻，仅开启单选模式")

# 2b: 勾选五爻 → 应为唯一动爻
p._manual_cbs[1].setChecked(True)  # 五爻
app.processEvents()
print(f"  勾选五爻后: _changing_lines={p._changing_lines}")
if check(p._changing_lines == {5}, f"应仅有{{5}}，实际{p._changing_lines}"):
    print("  ✅ 2b: 单动爻模式下勾选五爻 → 唯一动爻")
check(p._single_line_cb.isChecked(), "单动爻应保持勾选")
# 验证只有五爻被勾选
only_wu = p._manual_cbs[1].isChecked() and not any(p._manual_cbs[i].isChecked() for i in [0,2,3,4,5])
check(only_wu, "仅五爻应被勾选")

# 2c: 勾选二爻 → 应替换五爻（仅二爻被选）
p._manual_cbs[4].setChecked(True)  # 二爻
app.processEvents()
print(f"  勾选二爻后: _changing_lines={p._changing_lines}")
if check(p._changing_lines == {2}, f"应替换为{{2}}，实际{p._changing_lines}"):
    print("  ✅ 2c: 单动爻模式下勾选二爻 → 自动替换五爻")
check(not p._manual_cbs[1].isChecked(), "原五爻应被取消")
check(p._manual_cbs[4].isChecked(), "二爻应被勾选")

# 2d: 取消二爻 → 清空，单动爻保持勾选
p._manual_cbs[4].setChecked(False)
app.processEvents()
print(f"  取消二爻后: _changing_lines={p._changing_lines}")
if check(len(p._changing_lines) == 0, "应清空"):
    print("  ✅ 2d: 取消唯一动爻 → 清空")
if check(p._single_line_cb.isChecked(), "单动爻应保持勾选（仍在单选模式）"):
    print("  ✅ 2d: 单动爻保持勾选，等待下次选择")

# 2e: 重新勾选上爻 → 再勾选初爻 → 应替换为上爻
p._manual_cbs[0].setChecked(True)   # 上爻=6
app.processEvents()
check(p._changing_lines == {6}, f"应仅有上爻，实际{p._changing_lines}")
p._manual_cbs[5].setChecked(True)   # 初爻=1
app.processEvents()
check(p._changing_lines == {1}, f"应替换为初爻，实际{p._changing_lines}")
check(not p._manual_cbs[0].isChecked(), "原上爻应被取消")
print("  ✅ 2e: 单动爻模式下替换动爻 → 新爻覆盖旧爻")

# ═══════════════════════════════════════════════════════════
#  测试3: 非单动爻模式下可多选
# ═══════════════════════════════════════════════════════════
header("测试3: 非单动爻模式下可多选")

p._single_line_cb.setChecked(False)
for cb in p._manual_cbs:
    cb.setChecked(False)
app.processEvents()

# 多选
p._manual_cbs[0].setChecked(True)   # 上爻=6
p._manual_cbs[2].setChecked(True)   # 四爻=4
p._manual_cbs[4].setChecked(True)   # 二爻=2
app.processEvents()
print(f"  多选后 _changing_lines: {p._changing_lines}")
if check(p._changing_lines == {2, 4, 6}, f"多选失败，期望 {{2,4,6}} 实际 {p._changing_lines}"):
    print("  ✅ 非单动爻模式 → 可多选")
if check(not p._single_line_cb.isChecked(), "多选(>1)时单动爻应自动取消"):
    print("  ✅ 多选(>1)时单动爻自动取消")

# 减少到1个 → 单动爻不自动勾选（只在手动勾选时激活）
p._manual_cbs[2].setChecked(False)  # 取消四爻
p._manual_cbs[4].setChecked(False)  # 取消二爻 → 仅剩上爻
app.processEvents()
check(p._changing_lines == {6}, f"应仅有上爻，实际{p._changing_lines}")
check(not p._single_line_cb.isChecked(), "仅1个动爻时单动爻不应自动勾选")
print("  ✅ 减少到1个动爻 → 单动爻不自动勾选（需手动激活）")

# ═══════════════════════════════════════════════════════════
#  测试4: Lock 影响单动爻 + 动爻复选框
# ═══════════════════════════════════════════════════════════
header("测试4: Lock 对单动爻和动爻复选框的影响")

p._single_line_cb.setChecked(False)
for cb in p._manual_cbs:
    cb.setChecked(False)
app.processEvents()

lock_cb = p._lock_cbs[0] if p._lock_cbs else None

if not lock_cb:
    print("  ⚠️ 找不到 Lock checkbox，跳过 Lock 测试")
else:
    # 4a: Lock → 单动爻 disabled + 动爻复选框 disabled
    lock_cb.setChecked(True)
    app.processEvents()
    check(not p._single_line_cb.isEnabled(), "Lock 后单动爻应 disabled")
    all_cbs_disabled = not any(p._manual_cbs[i].isEnabled() for i in range(6))
    check(all_cbs_disabled, "Lock 后所有动爻复选框应 disabled")
    print("  ✅ 4a: Lock 后单动爻+动爻复选框全部 disabled")

    # 4b: 解锁 → 恢复 enabled
    lock_cb.setChecked(False)
    app.processEvents()
    check(p._single_line_cb.isEnabled(), "解锁后单动爻应 enabled")
    all_cbs_enabled = all(p._manual_cbs[i].isEnabled() for i in range(6))
    check(all_cbs_enabled, "解锁后所有动爻复选框应 enabled")
    print("  ✅ 4b: 解锁后全部恢复 enabled")

    # 4c: Lock 状态下单动爻无法改变动爻
    lock_cb.setChecked(True)
    app.processEvents()
    old_lines = p._changing_lines.copy()
    p._on_single_line_toggled(True)
    app.processEvents()
    check(p._changing_lines == old_lines, "Lock 状态下单动爻不应改变动爻")
    print("  ✅ 4c: Lock 状态下单动爻不改变动爻")

    # 4d: Lock 状态下卦图不可点击
    check(not p._drawer._clickable, "Lock 后 drawer 应不可点击")
    print("  ✅ 4d: Lock 后卦图不可点击")

    lock_cb.setChecked(False)
    app.processEvents()

# ═══════════════════════════════════════════════════════════
#  测试5: 点击卦图翻转阴阳爻 (QTest 模拟真实点击)
# ═══════════════════════════════════════════════════════════
header("测试5: 手动模式下点击卦图 → 翻转阴阳爻")

p._single_line_cb.setChecked(False)
for cb in p._manual_cbs:
    cb.setChecked(False)
app.processEvents()

dw = p._drawer
line_h = dw._line_h
name_h = dw._name_area_h
offset_y = dw._offset_y

# 辅助函数：点击某一爻
def click_line(row_from_top):
    """row_from_top: 0=上爻(top)..5=初爻(bottom)"""
    y = offset_y + name_h + line_h * row_from_top + line_h // 2
    x = dw.width() // 2
    QTest.mouseClick(dw, Qt.MouseButton.LeftButton, pos=QPoint(x, y))

# 5a: 点击四爻(row=2 from top, line_idx=3 from bottom) → 翻转
yang_before = dw.yang_lines().copy()
print(f"  5a 点击前 yang_lines: {yang_before}")
click_line(2)  # 四爻
app.processEvents()
yang_after = dw.yang_lines()
print(f"  5a 点击后 yang_lines: {yang_after}")
check(yang_after[3] != yang_before[3], "四爻应翻转（True→False 或 False→True）")
print(f"  ✅ 5a: 点击四爻 → 阴阳翻转")

# 验证 suangua 同步更新
if hasattr(p, '_suangua_panel') and p._suangua_panel is not None:
    result = p._suangua_panel._gua_result
    check(result is not None, "点击卦图后 suangua 应有数据")
    if result:
        print(f"      suangua 本卦: {result.get('full_name', '?')}")
        print(f"  ✅ 5a: suangua 同步更新")

# 5b: 再次点击四爻 → 翻回
yang_before2 = dw.yang_lines().copy()
click_line(2)
app.processEvents()
yang_after2 = dw.yang_lines()
check(yang_after2[3] != yang_before2[3], "再次点击四爻应翻回")
print(f"  ✅ 5b: 再次点击同爻 → 翻回")

# 5c: 点击初爻(row=5 from top, line_idx=0 from bottom)
yang_before3 = dw.yang_lines().copy()
click_line(5)  # 初爻
app.processEvents()
yang_after3 = dw.yang_lines()
check(yang_after3[0] != yang_before3[0], "初爻应翻转")
print(f"  ✅ 5c: 点击初爻 → 阴阳翻转")

# 5d: 点击上爻(row=0 from top, line_idx=5 from bottom)
yang_before4 = dw.yang_lines().copy()
click_line(0)  # 上爻
app.processEvents()
yang_after4 = dw.yang_lines()
check(yang_after4[5] != yang_before4[5], "上爻应翻转")
print(f"  ✅ 5d: 点击上爻 → 阴阳翻转")

# 5e: 点击卦图翻转阴阳 → 动爻复选框不变（点击只改阴阳，不清动爻）
# 先设置一个动爻
p._single_line_cb.setChecked(False)
for cb in p._manual_cbs:
    cb.setChecked(False)
p._manual_cbs[0].setChecked(True)  # 上爻=6 为动爻
app.processEvents()
check(6 in p._changing_lines, f"应保留上爻动爻，实际 {p._changing_lines}")
click_line(2)  # 翻转四爻（非动爻）
app.processEvents()
check(6 in p._changing_lines, f"点击非动爻后动爻应保留，实际 {p._changing_lines}")
check(p._manual_cbs[0].isChecked(), "上爻 checkbox 应保持勾选")
# 点击动爻本身 → 动爻也不清
click_line(0)  # 翻转上爻（动爻）
app.processEvents()
check(6 in p._changing_lines, f"点击动爻后动爻也应保留，实际 {p._changing_lines}")
check(p._manual_cbs[0].isChecked(), "上爻 checkbox 应保持勾选（点击动爻也不清）")
print(f"  ✅ 5e: 点击卦图翻转阴阳 → 动爻复选框不变")

# ═══════════════════════════════════════════════════════════
#  测试6: suangua 转发
# ═══════════════════════════════════════════════════════════
header("测试6: suangua 转发")

p._single_line_cb.setChecked(False)
for cb in p._manual_cbs:
    cb.setChecked(False)
app.processEvents()

# 设一个动爻
p._manual_cbs[0].setChecked(True)  # 上爻=6 动爻
app.processEvents()

p._on_calc()
app.processEvents()

if hasattr(p, '_suangua_panel') and p._suangua_panel is not None:
    result = p._suangua_panel._gua_result
    if check(result is not None, "suangua 未收到卦数据"):
        print("  ✅ suangua 收到卦数据")
        print(f"    本卦: {result.get('full_name', '?')}")
        print(f"    动爻: {p._suangua_panel._changing_lines}")
else:
    print("  ⚠️ _suangua_panel 不存在")

# ═══════════════════════════════════════════════════════════
#  测试7: 卦图点击 + 单动爻 组合场景
# ═══════════════════════════════════════════════════════════
header("测试7: 卦图点击 + 单动爻 组合场景")

# 7a: 单动爻勾选 → 点击卦图 → 动爻被清除，单动爻保持
p._single_line_cb.setChecked(False)
for cb in p._manual_cbs:
    cb.setChecked(False)
app.processEvents()

p._manual_cbs[0].setChecked(True)  # 上爻=6
p._single_line_cb.setChecked(True)  # 单动爻模式
app.processEvents()
check(p._changing_lines == {6}, f"应有上爻为动爻，实际{p._changing_lines}")

# 点击卦图（翻转上爻 row=0, 不清除上爻动爻）
click_line(0)
app.processEvents()
check(6 in p._changing_lines, f"点击后上爻动爻应保留，实际{p._changing_lines}")
check(p._single_line_cb.isChecked(), "单动爻应保持勾选")
print("  ✅ 7a: 单动爻模式下点击卦图 → 动爻保留不变")

# 7b: 无动爻+单动爻 → 点击卦图不影响
p._single_line_cb.setChecked(True)
for cb in p._manual_cbs:
    cb.setChecked(False)
app.processEvents()

click_line(3)  # 翻转三爻(row=3)
app.processEvents()
check(len(p._changing_lines) == 0, f"应无动爻，实际{p._changing_lines}")
check(p._single_line_cb.isChecked(), "单动爻应保持勾选")
print("  ✅ 7b: 无动爻+单动爻 → 点击卦图翻转阴阳但不产生动爻")

# ═══════════════════════════════════════════════════════════
#  测试8: 单动爻勾选 → 立即切梅花；取消勾选不变
# ═══════════════════════════════════════════════════════════
header("测试8: 单动爻勾选 → 立即切梅花")

sp = p._suangua_panel

# 8a: 勾选单动爻 → 立即切梅花（无论有无动爻）
p._single_line_cb.setChecked(False)
for cb in p._manual_cbs:
    cb.setChecked(False)
# 先切到六爻
sp.switch_method("liuyao")
app.processEvents()
check(sp._current_method == "liuyao", "初始应为六爻")

# 勾选单动爻（无动爻）→ 立即切梅花
p._single_line_cb.setChecked(True)
app.processEvents()
check(sp._current_method == "meihua", f"勾选单动爻应切梅花，实际 {sp._current_method}")
check(sp._dots[0].isChecked(), "梅花 dot 应选中")
check(len(p._changing_lines) == 0, "应无动爻（不自动选爻）")
print("  ✅ 8a: 无动爻时勾选单动爻 → 立即切梅花")

# 8b: 取消单动爻 → 不变（保持梅花）
# 先确保从干净状态开始
p._single_line_cb.setChecked(False)
for cb in p._manual_cbs:
    cb.setChecked(False)
app.processEvents()
sp.switch_method("liuyao")  # 先切回六爻
app.processEvents()
check(sp._current_method == "liuyao", "初始应为六爻")

p._single_line_cb.setChecked(True)  # 勾选 → 切梅花
app.processEvents()
check(sp._current_method == "meihua", "勾选后应为梅花")

p._single_line_cb.setChecked(False)  # 取消 → 不变
app.processEvents()
check(sp._current_method == "meihua", f"取消单动爻应保持梅花，实际 {sp._current_method}")
print("  ✅ 8b: 取消单动爻 → 保持梅花不变")

# 8c: 多动爻+勾选单动爻 → 保留最大+切梅花
sp.switch_method("liuyao")
app.processEvents()
p._manual_cbs[0].setChecked(True)   # 上爻=6
p._manual_cbs[2].setChecked(True)   # 四爻=4
p._manual_cbs[4].setChecked(True)   # 二爻=2
app.processEvents()
check(len(p._changing_lines) == 3, f"应有3个动爻，实际{p._changing_lines}")

p._single_line_cb.setChecked(True)  # 勾选单动爻
app.processEvents()
check(sp._current_method == "meihua", f"应切梅花，实际 {sp._current_method}")
check(p._changing_lines == {6}, f"应保留最大{{6}}，实际{p._changing_lines}")
print("  ✅ 8c: 多动爻+勾选单动爻 → 保留最大+切梅花")

# 8d: >1动爻无单动爻 → 梅花仍可用但不自动切
p._single_line_cb.setChecked(False)
for cb in p._manual_cbs:
    cb.setChecked(False)
sp.switch_method("liuyao")
app.processEvents()
p._manual_cbs[0].setChecked(True)
p._manual_cbs[2].setChecked(True)
app.processEvents()
check(len(p._changing_lines) == 2, "应有2个动爻")
check(sp._dots[0].isEnabled() == False, "梅花 dot 应禁用（>1动爻）")
check(sp._current_method == "liuyao", ">1动爻应在六爻")
print("  ✅ 8d: >1动爻无单动爻 → 梅花禁用，保持六爻")

# ═══════════════════════════════════════════════════════════
#  测试9: 卦图点击 → 动爻复选框联动
# ═══════════════════════════════════════════════════════════
header("测试9: 卦图点击 → 动爻复选框联动")

dw = p._drawer

def click_line(row):
    y = dw._offset_y + dw._name_area_h + dw._line_h * row + dw._line_h // 2
    QTest.mouseClick(dw, Qt.MouseButton.LeftButton, pos=QPoint(dw.width() // 2, y))

# 9a: 点击非动爻 → 该爻动爻标记清除(no-op)，其他动爻不变
p._single_line_cb.setChecked(False)
for cb in p._manual_cbs:
    cb.setChecked(False)
app.processEvents()
p._manual_cbs[0].setChecked(True)  # 上爻=6 为动爻
app.processEvents()
check(p._changing_lines == {6}, f"应有上爻动爻，实际{p._changing_lines}")

click_line(2)  # 点击四爻(row=2, 非动爻)
app.processEvents()
check(6 in p._changing_lines, "上爻动爻应保留（点击的是非动爻）")
check(p._manual_cbs[0].isChecked(), "上爻 checkbox 应保持勾选")
print("  ✅ 9a: 点击非动爻 → 其他动爻不受影响")

# 9b: 点击动爻 → 不动爻标记（点击只翻转阴阳，不清复选框）
click_line(0)  # 点击上爻(row=0, 是动爻)
app.processEvents()
check(6 in p._changing_lines, f"上爻动爻应保留（点击卦图不清动爻），实际 {p._changing_lines}")
check(p._manual_cbs[0].isChecked(), "上爻 checkbox 应保持勾选")
print("  ✅ 9b: 点击动爻 → 动爻标记保留不变")

# 9c: 点击卦图后动爻复选框仍可正常操作（先清除旧动爻）
for cb in p._manual_cbs:
    cb.setChecked(False)
app.processEvents()
check(len(p._changing_lines) == 0, f"清除后应无动爻，实际{p._changing_lines}")

p._manual_cbs[1].setChecked(True)  # 勾选五爻
app.processEvents()
check(p._changing_lines == {5}, f"应可勾选新动爻，实际{p._changing_lines}")
check(p._manual_cbs[1].isChecked(), "五爻 checkbox 应勾选")
print("  ✅ 9c: 点击卦图后 → 动爻复选框仍可勾选")

p._manual_cbs[1].setChecked(False)  # 取消五爻
app.processEvents()
check(len(p._changing_lines) == 0, f"应可取消动爻，实际{p._changing_lines}")
print("  ✅ 9d: 点击卦图后 → 动爻复选框仍可取消")

# 9e: 连续点击多次 → 动爻复选框始终可用（先清除旧动爻）
for cb in p._manual_cbs:
    cb.setChecked(False)
app.processEvents()
for _ in range(3):
    click_line(3)  # 反复翻转三爻
    app.processEvents()
p._manual_cbs[3].setChecked(True)  # 勾选三爻
app.processEvents()
check(p._changing_lines == {3}, f"连续点击后应仍可勾选，实际{p._changing_lines}")
print("  ✅ 9e: 连续点击卦图 → 动爻复选框始终可用")

# 9f: 点击卦图 + 单动爻模式
p._single_line_cb.setChecked(False)
for cb in p._manual_cbs:
    cb.setChecked(False)
app.processEvents()
p._single_line_cb.setChecked(True)  # 开启单动爻模式
p._manual_cbs[0].setChecked(True)   # 上爻=6
app.processEvents()
check(p._changing_lines == {6}, "应有上爻动爻")

click_line(0)  # 点击上爻（动爻）→ 不清除
app.processEvents()
check(6 in p._changing_lines, f"上爻动爻应保留，实际 {p._changing_lines}")
check(p._single_line_cb.isChecked(), "单动爻应保持勾选")
print("  ✅ 9f: 单动爻模式+点击动爻 → 动爻保留，单动爻保持")

# 点击后可立即选新动爻
p._manual_cbs[2].setChecked(True)  # 四爻
app.processEvents()
check(p._changing_lines == {4}, "应可选新动爻")
print("  ✅ 9g: 单动爻模式+点击后 → 可立即选新动爻")

# ═══════════════════════════════════════════════════════════
#  测试10: 手动面板 ↔ 卦图爻线对齐验证
# ═══════════════════════════════════════════════════════════
header("测试10: 手动面板动爻复选框 ↔ 卦图爻线对齐")

dw = p._drawer
line_positions = dw.get_line_positions()
# get_line_positions returns [初爻..上爻] (index 0=初爻)
# manual panel rows: [0]=title_row, [1]=上爻..[6]=初爻

man_lay = p._right_stack.widget(0).layout()
drawer_global = dw.mapToGlobal(QPoint(0, 0))

for i in range(6):
    lp = line_positions[i]  # 初爻=0
    line_num = lp["line_num"]  # 1=初爻..6=上爻
    line_global_y = drawer_global.y() + lp["center_y"]

    # manual panel row: index 7-line_num (上爻=row[1], 初爻=row[6])
    row_idx = 7 - line_num  # 上爻(line_num=6) → row_idx=1, 初爻(line_num=1) → row_idx=6
    row_item = man_lay.itemAt(row_idx)
    if row_item and row_item.widget():
        row_w = row_item.widget()
        row_center_global = row_w.mapToGlobal(QPoint(0, row_w.height() // 2))
        delta = abs(row_center_global.y() - line_global_y)

        name_map = {1: "初爻", 2: "二爻", 3: "三爻", 4: "四爻", 5: "五爻", 6: "上爻"}
        name = name_map[line_num]

        if check(delta <= 2, f"{name}: checkbox center={row_center_global.y()}, line center={line_global_y}, delta={delta}px (允许≤2px)"):
            print(f"  ✅ {name}: 对齐 (delta={delta}px)")
        else:
            print(f"  ❌ {name}: 未对齐 (delta={delta}px)")

# ═══════════════════════════════════════════════════════════
#  结果汇总
# ═══════════════════════════════════════════════════════════
header("结果汇总")
if _failures == 0:
    print("  🎉 全部测试通过!")
else:
    print(f"  ⚠️ {_failures} 个测试失败")

app.quit()
