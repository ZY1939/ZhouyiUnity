# 起卦工具包架构文档

> 基于 2026-06-08 项目记忆 + 实际引用分析生成

---

## 文件状态一览

| 状态标记 | 含义 |
|----------|------|
| ✅ 活跃 | 当前运行时被实际引用和调用 |
| 🔮 预留 | 接口已写好但尚未接入 UI，后续开发使用 |
| 🗑️ 遗留 | 已被 `divination_panel.py` 内联取代，无任何文件引用，可安全删除 |

---

## 文件分层

```
src/qigua/
├── __init__.py              # ✅ 包导出：QiguaPanel, GuaResult, case CRUD
│
├── [核心层] 纯计算，零 UI 依赖
│   ├── bagua.py             # ✅ 先天八卦常量 + GuaResult 数据类
│   ├── hexagram_calc.py     # ✅ 三位数→卦 / 六爻→卦 / 阴阳→卦 核心计算
│   ├── hexagram_loader.py   # ✅ 读取 content/*.jsonc，64卦查询 + 缓存
│   └── hexagram_painter.py  # 🔮 画卦接口空壳（GuaPainter.draw_gua/clear）
│                              └─ 仅被 🗑️ result_view.py 引用，等待新 UI 接入
│
├── [UI 层] 主面板 — 当前唯一入口
│   └── divination_panel.py  # ✅ QiguaPanel 主面板（~2500行）
│       │                     整合卦图 + 4种输入 + 结果 + Lock + 弹窗
│       ├── 内部类 _DotButton         圆点方法选择按钮
│       ├── 内部类 _GuaPickerPopup    64卦弹出选择窗口
│       └── 引用的外部组件 ↓
│
├── [UI 组件] 被 divination_panel 引用
│   ├── hexagram_drawer.py   # ✅ HexagramDrawer — 左侧卦图绘制（QPainter）
│   ├── countdown_timer.py   # ✅ CountdownDialog — 10秒随机倒计时弹窗
│   └── stopwatch_timer.py   # ✅ StopwatchDialog — 秒表计时弹窗
│
├── [数据层] 持久化存储
│   └── case_manager.py      # 🔮 案例 CRUD 完整实现 → usrCfg/divination_cases.json
│                              └─ 被 __init__.py 导出，但尚未被任何 UI 调用
│
├── [遗留文件] 已被 divination_panel 内联取代，无其他文件引用
│   ├── lines_input.py       # 🗑️ 旧 CoinYarrowWidget（→ divination_panel._make_lines_panel）
│   ├── manual_input.py      # 🗑️ 旧 ManualInputWidget（→ divination_panel._make_manual_panel）
│   ├── number_input.py      # 🗑️ 旧 ThreeNumberWidget（→ divination_panel._make_three_panel）
│   └── result_view.py       # 🗑️ 旧 ResultDisplay（→ divination_panel._build_footer）
│
└── [测试]
    └── test_gua_picker.py   # 🧪 64卦弹窗崩溃修复验证（5项自动化测试）
```

---

## 各类文件详解

### ✅ 活跃文件（当前运行时被实际调用）

| 文件 | 被谁引用 | 职责摘要 |
|------|----------|----------|
| `bagua.py` | divination_panel, hexagram_calc | 先天八卦常量、GuaResult 数据类、COIN_TO_YAO/YARROW_TO_YAO 映射 |
| `hexagram_calc.py` | divination_panel | 三位数→卦、六爻值→卦、阴阳列表+动爻→GuaResult，纯计算无 UI |
| `hexagram_loader.py` | divination_panel | JSONC 解析 + 64卦缓存 + 先天数索引，4种查询接口 |
| `hexagram_drawer.py` | divination_panel | QPainter 绘制六爻卦象（阳爻/阴爻/变爻/卦名），支持字体缩放和颜色变更 |
| `divination_panel.py` | yijing_viewer (via __init__) | 主面板：方法选择 + 4输入面板 + 卦图 + 结果 + Lock + 64卦弹窗 |
| `countdown_timer.py` | divination_panel | 10秒倒计时模态弹窗，每秒采集随机数 → 三位数平均值 |
| `stopwatch_timer.py` | divination_panel | 秒表模态弹窗，自由计时 + 3次记录 → 提取时间戳三位数 |

### 🔮 预留接口（已实现但未接入 UI，后续开发用）

| 文件 | 现状 | 用途 |
|------|------|------|
| `case_manager.py` | `__init__.py` 已导出 5 个 CRUD 函数，但尚无 UI 调用 | 案例持久化 → `usrCfg/divination_cases.json`，UUID 标识，支持增删改查清空 |
| `hexagram_painter.py` | `GuaPainter.draw_gua()` / `clear()` 空壳，仅被 🗑️ result_view 引用 | 后续在 QWidget 上绘制爻象图（非文字符号，而是图形化卦象） |

> **case_manager 接入提示**：在 `divination_panel._show_result()` 末尾调用 `save_case(result, method=self._current_method, notes="")` 即可打通案例保存。`__init__.py` 已导出函数，外部只需 `from src.qigua import save_case, load_cases`。

### 🗑️ 遗留文件（可安全删除）

| 文件 | 原来的职责 | 现在由谁替代 |
|------|-----------|-------------|
| `lines_input.py` | 金钱卦/蓍草卦 6爻输入 Widget | `divination_panel._make_lines_panel()` 内联实现 |
| `manual_input.py` | 手工指定卦象选择 Widget | `divination_panel._make_manual_panel()` 内联实现 |
| `number_input.py` | 三位数输入 + 随机/秒表 Widget | `divination_panel._make_three_panel()` 内联实现 |
| `result_view.py` | 起卦结果卡片式展示 Widget | `divination_panel._build_footer()` + `_show_result()` 内联实现 |

> 这 4 个文件**当前无任何文件 import 它们**（已通过 `grep -rl` 验证）。保留它们仅作为重构前的代码参考，新功能开发不需要也不应该修改它们。

---

## 调用关系图

```
yijing_viewer.py (Tab页)
  │ import QiguaPanel
  │ refresh_font_size(fs) ──────────────┐
  │ refresh_text_color(tc) ────────────┐│
  ▼                                    ││
QiguaPanel (divination_panel.py)       ││
  │ import ↓                           ││
  ├── bagua.py         常量 + 数据结构  ││
  ├── hexagram_calc.py 核心计算         ││
  ├── hexagram_loader  64卦数据加载     ││
  ├── hexagram_drawer  卦图绘制 ←──────┘│
  ├── countdown_timer  倒计时弹窗        │
  ├── stopwatch_timer  秒表弹窗          │
  └── config_manager   配置读写          │
     │                                   │
     └── hexagram_drawer.set_font_size()─┘
         hexagram_drawer.set_text_color()┘

[预留] case_manager.py (被 __init__.py 导出，等待 UI 接入)
  └── usrCfg/divination_cases.json

[预留] hexagram_painter.py (空壳，等待后续实现)
  └── 仅被 🗑️ result_view.py 引用
```

---

## 关键设计模式

### 1. 字体/颜色刷新链

```
外观面板改字号
  → apply_appearance()
    → yijing_viewer.refresh_font_size(font_size)
      → qigua_panel.refresh_font_size(font_size)
        → drawer.set_font_size(font_size)        # 重算 line_h/bar_h/name_area_h
        → _update_panel_layout() × 4              # 所有面板行高同步
        → _update_three_gaps()                    # 报数面板间距均分
        → _update_header_alignment()              # header标签间距
        → _update_frame_max_width()               # 右边框边界
        → _set_refresh_icon()                     # 刷新按钮图标
        → _apply_lock_indicator()                 # Lock indicator
```

颜色刷新同理，`refresh_text_color(text_color)` 走同样的链。

### 2. 间距体系（以 line_h 为动态基准）

```python
_gap_xs  = max(2,  int(line_h * 0.12))  # 极小间距
_gap_sm  = max(4,  int(line_h * 0.25))  # 小间距
_gap_md  = max(6,  int(line_h * 0.45))  # 中等间距
```

所有可调参数在 `_init_ui` 集中声明，标注 `【可手动调整】`。

### 3. 动爻跨模式同步

- `_changing_lines: set[int]` (1-6) 是权威来源
- `_sync_controls_to_changing_lines()` 同步到所有面板
- 金钱↔蓍草互切用 `cross_map` 保留老阳/老阴/少阳/少阴

### 4. Lock 锁定机制

- 遍历 `_lock_cbs` 列表同步所有 Lock 复选框状态
- 锁定范围：卦图 + 动爻复选框 + 下拉框 + SpinBox + 按钮 + 方法选择器
- 锁定时 checkbox indicator 用自定义深灰底白勾 PNG 替代原生 Aqua

### 5. 起卦标题弹窗（64卦选择器）

- 点击「起卦」→ `_show_gua_picker()` → `_GuaPickerPopup` 弹出列表
- **重要**：选中项后必须用 `hide() + deleteLater()` 延迟销毁，不能用同步 `close()`
  - 原因：`itemClicked` 信号处理器中同步销毁 picker → SIGSEGV
  - 见 test_gua_picker.py 回归测试

---

## 反复踩坑记录

### SIGSEGV — 弹窗同步关闭
- **现象**：点击起卦→弹出64卦列表→点击某项→Segmentation fault: 11
- **根因**：`_on_picker_selected` 中 `popup.close()` 在 picker 的信号处理器内同步销毁子控件
- **修复**：改用 `hide() + deleteLater()`，手动处理 Lock 恢复和引用清理

### 索引映射方向不一致
- `drawer._yang_lines[0]=初爻, [5]=上爻`（从下而上）
- `manual_cbs[0]=上爻, [5]=初爻`（UI从上而下）
- `_changing_lines = {1..6}`（1=初爻, 6=上爻）
- **教训**：改索引映射前先画表验证初爻和上爻两端

### _update_panel_layout 覆盖 widget 高度
- **现象**：新增 QLabel 设了 FixedHeight，但渲染后高度不对，导致错位
- **根因**：该方法遍历所有顶层 widget 强制设为 `line_h`
- **修复**：设 objectName 并在遍历时跳过

### CSS font-size: px ≠ QFont.setPointSize
- QPainter 用 QFont.setPointSize，CSS 用 font-size: Npx，两者度量不一致
- **规则**：需与 drawer 对齐的文字用 QFont + setFont()，不用 CSS

### 金钱↔蓍草互切被初始化覆盖
- **现象**：`cross_map` 正确映射后被简单阴阳循环覆盖
- **修复**：仅当 `prev not in ("coin", "yarrow")` 时才执行初始化循环

### header 标签对齐只动标签间间距
- 标题→第一个 dot 间距固定 `_gap_md`，不随对齐变动
- 只方法标签之间的 3 个 gap 计算均分
- gap 设下限 `max(4, ...)` 防止负数

### 浅色背景控件文字颜色
- 有自身背景的控件（按钮、输入框）→ 硬编码深色
- 透明背景控件 → 用 `self._text_color` 跟随主题
