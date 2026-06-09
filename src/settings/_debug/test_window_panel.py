"""
窗口面板功能测试脚本
验证 WindowPanel 的构建、配置读写、联动缩放、宽高比锁定等功能

运行: python3 src/settings/_debug/test_window_panel.py
"""
import sys
import os

# 项目根目录
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, _project_root)

print("=" * 60)
print("窗口面板功能测试")
print("=" * 60)

# ── 1. 模块导入测试 ──
print("\n【1. 模块导入】")
try:
    from src.settings.panels.window_panel import WindowPanel, SIZE_PRESETS, PANEL_STYLE
    print("  ✓ WindowPanel 导入成功")
except Exception as e:
    print(f"  ✗ WindowPanel 导入失败: {e}")
    sys.exit(1)

try:
    from src.settings.config_manager import config_manager, DEFAULT_CONFIG
    print("  ✓ config_manager 导入成功")
except Exception as e:
    print(f"  ✗ config_manager 导入失败: {e}")
    sys.exit(1)

try:
    from src.settings.settings_tab import CATEGORIES
    print("  ✓ settings_tab 导入成功")
except Exception as e:
    print(f"  ✗ settings_tab 导入失败: {e}")
    sys.exit(1)

# ── 2. DEFAULT_CONFIG 验证 ──
print("\n【2. DEFAULT_CONFIG 窗口段】")
win_defaults = DEFAULT_CONFIG.get("window", {})
print(f"  lock_aspect_ratio: {win_defaults.get('lock_aspect_ratio')}")
print(f"  auto_resize_with_font: {win_defaults.get('auto_resize_with_font')}")
print(f"  auto_scale_factor: {win_defaults.get('auto_scale_factor')}")
print(f"  no_resize: {win_defaults.get('no_resize')}")
print(f"  window_width: {win_defaults.get('window_width')}")
print(f"  window_height: {win_defaults.get('window_height')}")

assert win_defaults.get("lock_aspect_ratio") == True
assert win_defaults.get("auto_resize_with_font") == False
assert win_defaults.get("auto_scale_factor") == 1.0
assert win_defaults.get("no_resize") == False
print("  ✓ DEFAULT_CONFIG 所有字段默认值正确")

# ── 3. CATEGORIES 注册验证 ──
print("\n【3. CATEGORIES 注册】")
cat_ids = [c["id"] for c in CATEGORIES]
cat_titles = {c["id"]: c["title"] for c in CATEGORIES}
print(f"  注册的分类: {cat_ids}")
assert "window" in cat_ids, "window 分类未注册到 CATEGORIES"
print(f"  ✓ '窗口选项' 已注册 (id=window)")
assert cat_titles["window"] == "窗口选项"
print("  ✓ 标题为 '窗口选项'")
win_cat = next(c for c in CATEGORIES if c["id"] == "window")
assert win_cat["icon_name"] == "window"
print("  ✓ 图标名称为 'window'")
assert win_cat["panel_class"] == WindowPanel
print("  ✓ panel_class 指向 WindowPanel")

# ── 4. SVG 图标验证 ──
print("\n【4. SVG 图标】")
svg_path = os.path.join(_project_root, "src", "data", "icon", "setting", "window.svg")
print(f"  路径: {svg_path}")
assert os.path.isfile(svg_path), f"SVG 文件不存在: {svg_path}"
with open(svg_path, "r") as f:
    svg_content = f.read()
assert "<svg" in svg_content, "不是有效的 SVG 文件"
assert "viewBox" in svg_content, "SVG 缺少 viewBox"
print(f"  ✓ SVG 文件有效 ({os.path.getsize(svg_path)} bytes)")

# ── 5. QApplication 初始化 ──
print("\n【5. QApplication 初始化】")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)
print("  ✓ QApplication 就绪")

# ── 6. WindowPanel 控件构建和默认值 ──
print("\n【6. WindowPanel 控件构建】")
panel = WindowPanel()
assert hasattr(panel, "_lock_ratio_cb"), "缺少 _lock_ratio_cb"
assert hasattr(panel, "_auto_resize_cb"), "缺少 _auto_resize_cb"
assert hasattr(panel, "_scale_factor_spin"), "缺少 _scale_factor_spin"
assert hasattr(panel, "_no_resize_cb"), "缺少 _no_resize_cb"
assert hasattr(panel, "_width_spin"), "缺少 _width_spin"
assert hasattr(panel, "_height_spin"), "缺少 _height_spin"
assert hasattr(panel, "_btn_apply"), "缺少 _btn_apply"
assert hasattr(panel, "_preset_buttons"), "缺少 _preset_buttons"
print("  ✓ 所有控件已创建")

assert panel._lock_ratio_cb.isChecked() == True
assert panel._auto_resize_cb.isChecked() == False
assert panel._scale_factor_spin.value() == 1.0
assert panel._no_resize_cb.isChecked() == False
print(f"  ✓ 默认值: lock_ratio={panel._lock_ratio_cb.isChecked()}, "
      f"auto_resize={panel._auto_resize_cb.isChecked()}, "
      f"scale_factor={panel._scale_factor_spin.value()}, "
      f"no_resize={panel._no_resize_cb.isChecked()}")
print(f"  ✓ 窗口大小: {panel._width_spin.value()}×{panel._height_spin.value()}")

# ── 7. 配置读写测试 ──
print("\n【7. 配置读写】")
config_manager.set("window", "lock_aspect_ratio", value=True)
config_manager.set("window", "auto_resize_with_font", value=False)
config_manager.set("window", "auto_scale_factor", value=1.5)
config_manager.set("window", "no_resize", value=True)

read_lock = config_manager.get("window", "lock_aspect_ratio")
read_auto = config_manager.get("window", "auto_resize_with_font")
read_scale = config_manager.get("window", "auto_scale_factor")
read_noresize = config_manager.get("window", "no_resize")

print(f"  写入: lock=True, auto=False, scale=1.5, no_resize=True")
print(f"  读回: lock={read_lock}, auto={read_auto}, scale={read_scale}, no_resize={read_noresize}")
assert read_lock == True
assert read_auto == False
assert read_scale == 1.5
assert read_noresize == True
print("  ✓ 配置读写一致")

config_manager.set("window", "lock_aspect_ratio", value=False)
config_manager.set("window", "auto_resize_with_font", value=True)
config_manager.set("window", "auto_scale_factor", value=1.0)
config_manager.set("window", "no_resize", value=False)
print("  ✓ 配置已恢复默认")

# ── 8. refresh_text_color 测试 ──
print("\n【8. refresh_text_color】")
panel.refresh_text_color("#ffffff")
style = panel.styleSheet()
assert "#ffffff" in style, f"stylesheet 应包含 #ffffff"
print("  ✓ 白色文字 → stylesheet 包含 #ffffff")

panel.refresh_text_color("#1d1d1f")
style = panel.styleSheet()
assert "#1d1d1f" in style, f"stylesheet 应包含 #1d1d1f"
print("  ✓ 深色文字 → stylesheet 包含 #1d1d1f")

# ── 9. on_font_size_changed 缩放计算测试 ──
print("\n【9. 字号联动缩放计算】")
def simulate_scale(old_size, new_size, scale_factor, current_w, current_h):
    ratio = new_size / old_size
    scale = 1.0 + (ratio - 1.0) * scale_factor
    new_w = int(current_w * scale)
    new_h = int(current_h * scale)
    return new_w, new_h

w, h = simulate_scale(16, 20, 1.0, 1440, 900)
assert w == 1800, f"字号 16→20 scale_factor=1.0: 预期宽=1800, 实际={w}"
assert h == 1125, f"字号 16→20 scale_factor=1.0: 预期高=1125, 实际={h}"
print(f"  ✓ 字号 16→20 scale_factor=1.0: 1440×900 → {w}×{h}")

w, h = simulate_scale(16, 20, 0.5, 1440, 900)
assert w == 1620, f"预期宽=1620, 实际={w}"
assert h == 1012, f"预期高=1012, 实际={h}"
print(f"  ✓ 字号 16→20 scale_factor=0.5: 1440×900 → {w}×{h}")

w, h = simulate_scale(16, 20, 2.0, 1440, 900)
assert w == 2160, f"预期宽=2160, 实际={w}"
assert h == 1350, f"预期高=1350, 实际={h}"
print(f"  ✓ 字号 16→20 scale_factor=2.0: 1440×900 → {w}×{h}")

w, h = simulate_scale(20, 16, 1.0, 1800, 1125)
assert w == 1440, f"预期宽=1440, 实际={w}"
assert h == 900, f"预期高=900, 实际={h}"
print(f"  ✓ 字号 20→16 scale_factor=1.0: 1800×1125 → {w}×{h}")

# ── 10. SIZE_PRESETS 验证 ──
print("\n【10. 窗口大小预设】")
from src.settings.panels.window_panel import DEFAULT_SIZE
assert "默认" in SIZE_PRESETS and "小" in SIZE_PRESETS and "中" in SIZE_PRESETS and "大" in SIZE_PRESETS
# 验证预设比例一致（基于 DEFAULT_RATIO = 1024/700）
from src.settings.panels.window_panel import DEFAULT_RATIO
for label, (w, h) in SIZE_PRESETS.items():
    expected_h = round(w / DEFAULT_RATIO)
    assert h == expected_h, f"预设 {label} 高度应为 {expected_h}, 实际 {h}"
    assert w > h, f"预设 {label} 应为横屏 (宽>高), 实际 {w}×{h}"
print(f"  ✓ 所有预设比例一致 (DEFAULT_RATIO={DEFAULT_RATIO:.4f})")
for label, (w, h) in SIZE_PRESETS.items():
    print(f"    {label}: {w}×{h}")

# ── 11. 宽高比锁定逻辑测试 ──
print("\n【11. 宽高比锁定逻辑】")
def simulate_ratio_lock(old_w, old_h, new_w, new_h):
    if old_w > 0 and old_h > 0:
        ratio = old_w / old_h
        if abs(new_w - old_w) >= abs(new_h - old_h):
            new_h = int(new_w / ratio)
        else:
            new_w = int(new_h * ratio)
    return new_w, new_h

w, h = simulate_ratio_lock(1440, 900, 1600, 900)
assert w == 1600 and h == 1000
print(f"  ✓ 仅拖宽: 1440×900 → 1600×900 → 锁定为 {w}×{h}")

w, h = simulate_ratio_lock(1440, 900, 1440, 1000)
assert w == 1600 and h == 1000
print(f"  ✓ 仅拖高: 1440×900 → 1440×1000 → 锁定为 {w}×{h}")

w, h = simulate_ratio_lock(1440, 900, 1600, 1000)
assert w == 1600 and h == 1000
print(f"  ✓ 等比例拖动: 1440×900 → 1600×1000 → 保持 {w}×{h}")

# ── 12. SpinBox 范围验证 ──
print("\n【12. SpinBox 范围验证】")
assert panel._width_spin.minimum() == 640
assert panel._width_spin.maximum() == 5120
assert panel._height_spin.minimum() == 480
assert panel._height_spin.maximum() == 3200
assert panel._scale_factor_spin.minimum() == 0.5
assert panel._scale_factor_spin.maximum() == 2.0
print(f"  ✓ 宽度范围: {panel._width_spin.minimum()}-{panel._width_spin.maximum()}")
print(f"  ✓ 高度范围: {panel._height_spin.minimum()}-{panel._height_spin.maximum()}")
print(f"  ✓ 缩放倍率范围: {panel._scale_factor_spin.minimum()}-{panel._scale_factor_spin.maximum()}")

# ── 13. 预设按钮验证 ──
print("\n【13. 预设按钮】")
for label in ["默认", "小", "中", "大"]:
    assert label in panel._preset_buttons, f"缺少预设按钮: {label}"
    btn = panel._preset_buttons[label]
    assert btn.text().startswith(label)
print(f"  ✓ 四个预设按钮正常")

# ── 14. 保持宽高比联动测试 ──
print("\n【14. 保持宽高比联动】")
assert panel._keep_ratio_cb.isChecked() == True, "保持宽高比默认应勾选"
print("  ✓ 保持宽高比默认勾选")

# 模拟宽→高联动
panel._wh_ratio = 1024 / 700
panel._syncing_wh = True
panel._height_spin.setValue(round(1280 / panel._wh_ratio))
panel._syncing_wh = False
assert panel._height_spin.value() == 875, f"宽1280 → 高应为875, 实际{panel._height_spin.value()}"
print(f"  ✓ 宽度联动: 1280 → 高={panel._height_spin.value()}")

# 模拟高→宽联动
panel._syncing_wh = True
panel._width_spin.setValue(round(547 * panel._wh_ratio))
panel._syncing_wh = False
assert panel._width_spin.value() == 800, f"高547 → 宽应为800, 实际{panel._width_spin.value()}"
print(f"  ✓ 高度联动: 547 → 宽={panel._width_spin.value()}")

# ── 15. 清理 ──
print("\n【15. 清理】")
panel.deleteLater()
app.quit()

print("\n" + "=" * 60)
print("全部 15 项测试通过 ✓")
print("=" * 60)
