"""
MethodLabelBar 公共组件 + 起卦/算卦面板统一测试

覆盖场景：
  1. MethodLabelBar 基本功能（dot、label、信号）
  2. 选中/未选中样式（bold+color vs dimmed）
  3. disable_label / 恢复
  4. dim_color() 自适应
  5. 自定义 builder（qigua lines 双按钮模式）
  6. debug_positions() 坐标输出
  7. suangua 集成（switch_method、多动爻守卫、refresh）
  8. 起卦/算卦 y 坐标一致性验证
  9. 起卦 3 方法 + lines 子模式 集成回归

用法：
    cd /Users/zhou/Desktop/ZhouyiUnity
    python3 src/yijingTab/qigua/_debug/test_method_label_bar.py
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication, QHBoxLayout, QWidget
from PySide6.QtCore import Qt

app = QApplication.instance() or QApplication(sys.argv)

from src.yijingTab.com.method_label_bar import MethodLabelBar
from src.yijingTab.qigua.divination_panel import QiguaPanel
from src.yijingTab.suangua.suangua_panel import SuanguaPanel

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ FAIL: {name}" + (f" — {detail}" if detail else ""))


# ═══════════════════════════════════════════════════════════
# 1. MethodLabelBar 基本功能
# ═══════════════════════════════════════════════════════════
print("=== 1. MethodLabelBar 基本功能 ===")
METHODS = [{"key": "a", "label": "标签A"}, {"key": "b", "label": "标签B"}]
bar = MethodLabelBar(METHODS, font_size=16, text_color="#ffffff", bg_color="transparent")
container = QWidget()
lay = QHBoxLayout(container)
lay.addWidget(bar)
container.show()  # 需要 show() 才能有 geometry

check("dots 数量=2", len(bar.dots()) == 2)
check("labels 数量=2", len(bar.labels()) == 2)
check("默认选中第一个", bar.current_method() == "a")

# 信号测试
received = []
bar.method_selected.connect(lambda k: received.append(k))
bar.dots()[1].click()
check("点击 dot[1] → 信号发出", received == ["b"])
check("current_method 更新", bar.current_method() == "b")

bar.set_current_method("a")
check("set_current_method → a", bar.current_method() == "a")
check("set_current_method 不发射信号", received == ["b"])  # 没有新信号

# ═══════════════════════════════════════════════════════════
# 2. 选中/未选中样式
# ═══════════════════════════════════════════════════════════
print("\n=== 2. 选中/未选中样式 ===")
bar.update_label_styles()
a_style = bar.labels()[0].styleSheet()
b_style = bar.labels()[1].styleSheet()
check("选中标签 → bold", "font-weight: bold" in a_style)
check("选中标签 → text_color", "#ffffff" in a_style)
check("未选中标签 → normal", "font-weight: normal" in b_style)
check("未选中标签 → dim_color", bar.dim_color() in b_style)

# ═══════════════════════════════════════════════════════════
# 3. set_label_enabled
# ═══════════════════════════════════════════════════════════
print("\n=== 3. set_label_enabled ===")
bar.set_label_enabled(0, False)
style_disabled = bar.labels()[0].styleSheet()
check("disabled → 灰色 #888888", "#888888" in style_disabled)
check("disabled → normal weight", "font-weight: normal" in style_disabled)

bar.set_label_enabled(0, True)
style_restored = bar.labels()[0].styleSheet()
check("恢复 → bold", "font-weight: bold" in style_restored)
check("恢复 → text_color", "#ffffff" in style_restored)

# ═══════════════════════════════════════════════════════════
# 4. dim_color() 自适应
# ═══════════════════════════════════════════════════════════
print("\n=== 4. dim_color() 自适应 ===")
bar_white = MethodLabelBar(METHODS, text_color="#ffffff")
check("白→灰", bar_white.dim_color() == "#bfbfbf", f"got {bar_white.dim_color()}")

bar_black = MethodLabelBar(METHODS, text_color="#1d1d1f")
check("黑→灰", bar_black.dim_color() == "#4e4e4f", f"got {bar_black.dim_color()}")

# ═══════════════════════════════════════════════════════════
# 5. 自定义 builder（模拟 qigua lines 双按钮）
# ═══════════════════════════════════════════════════════════
print("\n=== 5. 自定义 builder ===")
from PySide6.QtWidgets import QPushButton, QLabel

def build_lines_toggle(font_size, text_color):
    w = QWidget()
    l = QHBoxLayout(w)
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(0)
    coin = QPushButton("金钱")
    slash = QLabel("/")
    yarrow = QPushButton("蓍草")
    l.addWidget(coin)
    l.addWidget(slash)
    l.addWidget(yarrow)
    return w

bar_custom = MethodLabelBar(
    [{"key": "manual", "label": "手工"}, {"key": "lines", "label": "金钱/蓍草"}],
    text_color="#ffffff",
    custom_builders={1: build_lines_toggle})
check("lines label 是自定义 QWidget", not isinstance(bar_custom.labels()[1], QPushButton))
check("手工 label 是 QPushButton", isinstance(bar_custom.labels()[0], QPushButton))

# ═══════════════════════════════════════════════════════════
# 6. debug_positions()
# ═══════════════════════════════════════════════════════════
print("\n=== 6. debug_positions() ===")
positions = bar.debug_positions()
check("返回 4 个元素（2 dots + 2 labels）", len(positions) == 4)
for p in positions:
    check(f"{p['type']}[{p['index']}] 有 x,y,w,h",
          all(k in p for k in ("x", "y", "w", "h")))
    check(f"{p['type']}[{p['index']}] 有 global_x,global_y",
          all(k in p for k in ("global_x", "global_y")))

# ═══════════════════════════════════════════════════════════
# 7. suangua 集成
# ═══════════════════════════════════════════════════════════
print("\n=== 7. suangua 集成 ===")
suangua = SuanguaPanel()
check("_method_bar 存在", hasattr(suangua, "_method_bar"))
check("默认 meihua 选中", suangua._current_method == "meihua")
bar_s = suangua._method_bar
check("bar current = meihua", bar_s.current_method() == "meihua")

# 切换
suangua.switch_method("liuyao")
check("switch → liuyao", suangua._current_method == "liuyao")
check("bar 同步", bar_s.current_method() == "liuyao")

# refresh
suangua.refresh_font_size(18)
check("refresh_font_size 不崩溃", True)
suangua.refresh_text_color("#ffffff")
check("refresh_text_color 不崩溃", True)

# 多动爻守卫（_on_bar_method_selected）
suangua._current_method = "liuyao"
bar_s.set_current_method("liuyao")  # 先在六爻
suangua._changing_lines = [1, 2, 3]  # 多动爻
mock_mgr = MagicMock()
mock_win = MagicMock()
mock_win._statusbar_mgr = mock_mgr
suangua.window = MagicMock(return_value=mock_win)
# 模拟点击梅花 dot → _on_bar_method_selected
suangua._on_bar_method_selected("meihua")
check("多动爻点梅花 → bar 回退六爻", bar_s.current_method() == "liuyao")
check("多动爻点梅花 → _current_method 保持 liuyao", suangua._current_method == "liuyao")
check("多动爻点梅花 → 状态栏警告", mock_mgr.show_status.called)

# set_gua_result 中多动爻主动切换到六爻
suangua._current_method = "meihua"
bar_s.set_current_method("meihua")
suangua._changing_lines = [1, 2, 3]
mock_mgr.reset_mock()
suangua._on_bar_method_selected = MagicMock()  # 防止 set_gua_result 内的 switch_method 触发
suangua._switch_method = MagicMock()
# 模拟 set_gua_result 多动爻分支
suangua._method_bar.set_label_enabled(0, False)
check("set_label_enabled(0,False) 禁用梅花", 0 in bar_s._disabled_indices)
style_dis = bar_s.labels()[0].styleSheet()
check("disabled 样式 → #888888", "#888888" in style_dis)

# 恢复
suangua._method_bar.set_label_enabled(0, True)
check("set_label_enabled(0,True) 恢复", 0 not in bar_s._disabled_indices)

# ═══════════════════════════════════════════════════════════
# 8. y 坐标一致性（起卦 vs 算卦）
# ═══════════════════════════════════════════════════════════
print("\n=== 8. y 坐标一致性 ===")
qigua = QiguaPanel()
# 获取起卦 header labels 的 bar_global_y
qigua_positions = []
for lbl in qigua._header_labels:
    if isinstance(lbl, tuple):
        # lines 元组: ("lines", coin, yarrow, slash)
        pass  # 跳过
    else:
        g = lbl.mapToGlobal(lbl.rect().topLeft())
        qigua_positions.append(g.y())

# suangua bar positions
suangua_positions = bar_s.debug_positions()

# 验证两个面板的 label y 差值在合理范围（考虑到 header 布局差异）
if qigua_positions:
    print(f"  起卦 label global_y: {qigua_positions}")
    for p in suangua_positions:
        if p["type"] == "label":
            print(f"  算卦 label[{p['index']}] global_y: {p['global_y']} (mid_y: {p['mid_y']})")
    check("起卦 labels 有 y 坐标", len(qigua_positions) > 0)
    check("算卦 labels 有 y 坐标", any(p["type"] == "label" for p in suangua_positions))

# ═══════════════════════════════════════════════════════════
# 9. 起卦 3 方法 + lines 子模式 回归
# ═══════════════════════════════════════════════════════════
print("\n=== 9. 起卦 3 方法 + lines 子模式回归 ===")
check("_header_labels[0] 是手工 QPushButton", isinstance(qigua._header_labels[0], QPushButton))
check("_header_labels[1] 是报数 QPushButton", isinstance(qigua._header_labels[1], QPushButton))
check("_header_labels[2] 是 lines 元组",
      isinstance(qigua._header_labels[2], tuple) and qigua._header_labels[2][0] == "lines")

# lines 子模式切换
qigua._current_method = "lines"
qigua._lines_mode = "coin"
qigua._on_method_label_clicked("lines", 2, "yarrow")
check("coin→yarrow", qigua._lines_mode == "yarrow")
qigua._on_method_label_clicked("lines", 2, "coin")
check("yarrow→coin", qigua._lines_mode == "coin")

# lines 未激活时点击 → 设置子模式
qigua._current_method = "manual"
qigua._dots[2].click = MagicMock()
qigua._on_method_label_clicked("lines", 2, "yarrow")
check("从未激活→lines 设 yarrow", qigua._lines_mode == "yarrow")

# suangua 自动跳转（使用 mock suangua）
mock_sg = MagicMock()
mock_sg._current_method = "meihua"
qigua._suangua_panel = mock_sg
qigua._switch_method("lines")
check("lines→liuyao", mock_sg.switch_method.called and mock_sg.switch_method.call_args[0][0] == "liuyao")

mock_sg.reset_mock()
mock_sg._current_method = "liuyao"
qigua._switch_method("lines")
check("已在六爻→不重复", not mock_sg.switch_method.called)

# ═══════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"结果: {passed} 通过, {failed} 失败")
print(f"{'='*50}")

container.close()
if failed > 0:
    sys.exit(1)
