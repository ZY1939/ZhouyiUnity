"""
header 方法标签自动化测试

覆盖场景（对应 ARCHITECTURE.md "Header 方法标签设计" 章节）：
  1. METHODS 结构（3项，lines label="金钱/蓍草"）
  2. 手工/报数标签点击 → dot.click()
  3. lines 已激活 + 点金钱 → _lines_mode = "coin"
  4. lines 已激活 + 点蓍草 → _lines_mode = "yarrow"
  5. lines 未激活 + 点金钱 → 先设 coin 再切到 lines
  6. lines 未激活 + 点蓍草 → 先设 yarrow 再切到 lines
  7. 报数 → suangua.switch_method("meihua")
  8. lines → suangua.switch_method("liuyao")
  9. 已在六爻 → 不重复调用 switch_method
  10. 手工 → 不调用 switch_method
  11. 已选中 lines 点标签切换 → suangua 不跳转
  12. _dim_color() 白/黑输入输出验证
  13. _update_method_label_styles 各状态样式断言

用法：
    cd /Users/zhou/Desktop/ZhouyiUnity
    python3 src/yijingTab/qigua/_debug/test_method_labels.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from src.yijingTab.qigua.divination_panel import QiguaPanel, METHODS
from src.yijingTab.CONST_DEFINE_UI import QiguaConfig

passed = 0
failed = 0


def check(test_name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {test_name}")
    else:
        failed += 1
        print(f"  ✗ FAIL: {test_name}" + (f" — {detail}" if detail else ""))


# ── 创建面板 ──
panel = QiguaPanel()
mock_suangua = MagicMock()
mock_suangua._current_method = "meihua"
panel._suangua_panel = mock_suangua
mock_window = MagicMock()
mock_window._statusbar_mgr = MagicMock()
panel.window = MagicMock(return_value=mock_window)


# ═══════════════════════════════════════════════════════════
# 1. METHODS 结构
# ═══════════════════════════════════════════════════════════
print("=== 1. METHODS 结构 ===")
check("METHODS 长度 = 3", len(METHODS) == 3, f"got {len(METHODS)}")
check("METHODS[0] = manual/手工", METHODS[0]["key"] == "manual" and METHODS[0]["label"] == "手工")
check("METHODS[1] = three/报数", METHODS[1]["key"] == "three" and METHODS[1]["label"] == "报数")
check("METHODS[2] = lines/金钱蓍草", METHODS[2]["key"] == "lines" and METHODS[2]["label"] == "金钱/蓍草")
check("_header_labels 长度 = 3", len(panel._header_labels) == 3, f"got {len(panel._header_labels)}")
# lines 条目是元组
check("_header_labels[2] 是 lines 元组",
      isinstance(panel._header_labels[2], tuple) and panel._header_labels[2][0] == "lines")


# ═══════════════════════════════════════════════════════════
# 2. 手工/报数标签点击 → dot.click()
# ═══════════════════════════════════════════════════════════
print("\n=== 2. 手工/报数标签点击 → dot.click() ===")
for i, (key, name) in enumerate([("manual", "手工"), ("three", "报数")]):
    panel._dots[i].click = MagicMock()
    panel._on_method_label_clicked(key, i)
    check(f"{name}标签 → dot[{i}].click()", panel._dots[i].click.called)


# ═══════════════════════════════════════════════════════════
# 3. lines 已激活 + 点金钱 → _lines_mode = "coin"
# ═══════════════════════════════════════════════════════════
print("\n=== 3. lines 已激活 + 点金钱/蓍草 → 切换子模式 ===")
panel._current_method = "lines"
panel._lines_mode = "yarrow"
panel._on_method_label_clicked("lines", 2, "coin")
check("yarrow → coin", panel._lines_mode == "coin")

panel._on_method_label_clicked("lines", 2, "yarrow")
check("coin → yarrow", panel._lines_mode == "yarrow")


# ═══════════════════════════════════════════════════════════
# 5+6. lines 未激活 + 点金钱/蓍草 → 先设子模式再切到 lines
# ═══════════════════════════════════════════════════════════
print("\n=== 5+6. lines 未激活 + 点金钱/蓍草 → 先设子模式 ===")
panel._current_method = "three"
panel._lines_mode = "yarrow"  # 上次是 yarrow
panel._dots[2].click = MagicMock()
panel._on_method_label_clicked("lines", 2, "coin")
check("点金钱 → _lines_mode=coin", panel._lines_mode == "coin")
check("点金钱 → dot[2].click() 被调用", panel._dots[2].click.called)

panel._current_method = "three"
panel._lines_mode = "coin"  # 上次是 coin
panel._dots[2].click = MagicMock()
panel._on_method_label_clicked("lines", 2, "yarrow")
check("点蓍草 → _lines_mode=yarrow", panel._lines_mode == "yarrow")
check("点蓍草 → dot[2].click() 被调用", panel._dots[2].click.called)


# ═══════════════════════════════════════════════════════════
# 7-10. suangua 自动跳转
# ═══════════════════════════════════════════════════════════
print("\n=== 7-10. suangua 自动跳转 ===")

# 7. 报数 → 梅花
mock_suangua.reset_mock()
mock_suangua._current_method = "liuyao"
panel._switch_method("three")
check("报数 → switch_method('meihua')",
      mock_suangua.switch_method.called and mock_suangua.switch_method.call_args[0][0] == "meihua")

# 8. lines → 六爻
mock_suangua.reset_mock()
mock_suangua._current_method = "meihua"
panel._switch_method("lines")
check("lines → switch_method('liuyao')",
      mock_suangua.switch_method.called and mock_suangua.switch_method.call_args[0][0] == "liuyao")

# 9. 已在六爻 → 不重复
mock_suangua.reset_mock()
mock_suangua._current_method = "liuyao"
panel._switch_method("lines")
check("已在六爻 → 不重复切换", not mock_suangua.switch_method.called)

# 10. 手工 → 不跳转
mock_suangua.reset_mock()
panel._switch_method("manual")
check("手工 → 不调用 switch_method", not mock_suangua.switch_method.called)


# ═══════════════════════════════════════════════════════════
# 11. 已选中 lines 点标签切换 → suangua 不跳转
# ═══════════════════════════════════════════════════════════
print("\n=== 11. 已选中 lines 点标签 → suangua 不跳转 ===")
mock_suangua.reset_mock()
panel._current_method = "lines"
panel._lines_mode = "coin"
panel._on_method_label_clicked("lines", 2, "yarrow")
check("coin→yarrow suangua 不跳转", not mock_suangua.switch_method.called)


# ═══════════════════════════════════════════════════════════
# 12. _dim_color() 颜色自适应
# ═══════════════════════════════════════════════════════════
print("\n=== 12. _dim_color() 颜色自适应 ===")
panel._text_color = "#ffffff"
dim_white = panel._dim_color()
check("白底→暗灰", dim_white == "#bfbfbf", f"got {dim_white}")

panel._text_color = "#1d1d1f"
dim_black = panel._dim_color()
check("黑底→浅灰", dim_black == "#4e4e4f", f"got {dim_black}")


# ═══════════════════════════════════════════════════════════
# 13. _update_method_label_styles 样式断言
# ═══════════════════════════════════════════════════════════
print("\n=== 13. _update_method_label_styles 样式断言 ===")

# 手工选中 → 手工加粗+白字
panel._current_method = "manual"
panel._lines_mode = "coin"
panel._update_method_label_styles()

manual_style = panel._header_labels[0].styleSheet()
check("手工选中 → bold", "font-weight: bold" in manual_style)
check("手工选中 → text_color", panel._text_color in manual_style)

# 报数未选中 → 灰色+normal
three_style = panel._header_labels[1].styleSheet()
check("报数未选中 → normal", "font-weight: normal" in three_style)
check("报数未选中 → dim_color", panel._dim_color() in three_style)

# lines 选中 + coin 模式 → 金钱 bold+大字+下划线，蓍草 normal+小字
panel._current_method = "lines"
panel._lines_mode = "coin"
panel._update_method_label_styles()

_, coin_btn, yarrow_btn, slash_lbl = panel._header_labels[2]
coin_style = coin_btn.styleSheet()
yarrow_style = yarrow_btn.styleSheet()

check("coin选中 → bold", "font-weight: bold" in coin_style)
check("coin选中 → text_color", panel._text_color in coin_style)
check("coin选中 → 有underline" if QiguaConfig.lines_underline else "coin选中 → 无underline",
      ("border-bottom: 2px solid" in coin_style) if QiguaConfig.lines_underline else True)

check("yarrow未选中 → normal", "font-weight: normal" in yarrow_style)
if QiguaConfig.lines_underline:
    check("yarrow未选中 → 透明border占位", "transparent" in yarrow_style)

# lines 未激活（如报数选中）→ 金钱/蓍草都无 padding
panel._current_method = "three"
panel._update_method_label_styles()
_, coin_btn2, yarrow_btn2, _ = panel._header_labels[2]
coin_style2 = coin_btn2.styleSheet()
check("lines未激活+coin → 无padding-bottom",
      "padding-bottom" not in coin_style2 or "padding-bottom: 0px" in coin_style2)


# ═══════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"结果: {passed} 通过, {failed} 失败")
print(f"{'='*50}")

if failed > 0:
    sys.exit(1)
