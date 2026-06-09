# 起卦工具包架构文档

> 基于 2026-06-09 项目记忆 + 实际引用分析生成（最后更新：2026-06-09）

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
├── [UI 层] 主面板
│   ├── divination_panel.py  # ✅ QiguaPanel 起卦主面板（~2600行）
│   │   │                     整合卦图 + 4种输入 + 结果 + Lock + 弹窗 + 算卦面板集成
│   │   ├── _FixedWidthCheckBox   QCheckBox 子类 — sizeHint 中加入额外宽度（对齐方案）
│   │   ├── _GuaPickerPopup       64卦弹出选择窗口
│   │   └── 引用的外部组件 ↓
│   │
│   └── suangua/             # ✅ 算卦面板（梅花易数/六爻断卦）
│       ├── __init__.py        导出 SuanguaPanel
│       ├── suangua_panel.py   算卦主面板（header: 算卦标题+梅花/六爻dot+时间显示）
│       │                       时间管理：共享干支时间 → 梅花/六爻子面板
│       ├── meihua_panel.py    梅花面板（本/互/变三卦 + 体用标注 + 爻辞解读）
│       │                       _LineMarker — 共享标注组件（badge/outlined/normal 模式）
│       ├── liuyao_panel.py    六爻面板（主卦 + 六神/世应/卦图/动爻/纳音 5列标注）
│       │                       _NayinLabel — 纳音标注（五行彩色边框）
│       │                       _TimePickerDialog — 双模式时间选择器（天干地支/阳历）
│       └── _debug/            调试脚本（test_liuyao.py, test_header_alignment.py）
│
├── [UI 组件] 被 divination_panel / suangua 引用
│   ├── hexagram_drawer.py   # ✅ HexagramDrawer — 卦图绘制（QPainter）
│   ├── dot_button.py        # ✅ DotButton — 圆点选择按钮（共享组件）
│   ├── countdown_timer.py   # ✅ CountdownDialog — 10秒随机倒计时弹窗
│   ├── stopwatch_timer.py   # ✅ StopwatchDialog — 秒表计时弹窗
│   └── CONST_DEFINE_UI.py   # ✅ QiguaConfig / SuanguaConfig / MeihuaConfig 参数集中管理
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
    ├── test_gua_picker.py      # 🧪 64卦弹窗崩溃修复验证（5项自动化测试）
    └── _debug/
        └── test_manual_panel.py  # 🧪 手工面板交互回归测试（10类30+子场景）
                                   #    单动爻/Lock/卦图翻转/动爻联动/suangua转发/梅花切换/对齐验证
```

---

## 各类文件详解

### ✅ 活跃文件（当前运行时被实际调用）

| 文件 | 被谁引用 | 职责摘要 |
|------|----------|----------|
| `bagua.py` | divination_panel, hexagram_calc | 先天八卦常量、GuaResult 数据类、COIN_TO_YAO/YARROW_TO_YAO 映射 |
| `hexagram_calc.py` | divination_panel | 三位数→卦、六爻值→卦、阴阳列表+动爻→GuaResult，纯计算无 UI |
| `hexagram_loader.py` | divination_panel | JSONC 解析 + 64卦缓存 + 先天数索引，4种查询接口 |
| `hexagram_drawer.py` | divination_panel, suangua/meihua_panel | QPainter 绘制六爻卦象（阳爻/阴爻），支持字体缩放、颜色变更、五行模式(get_line_positions/set_disabled_look/set_wuxing_mode) |
| `divination_panel.py` | yijing_viewer (via __init__) | 主面板：方法选择 + 4输入面板 + 卦图 + 结果 + Lock + 单动爻 + 64卦弹窗 |
| `dot_button.py` | divination_panel, suangua/suangua_panel | DotButton 圆点选择按钮（共享组件，避免循环导入） |
| `countdown_timer.py` | divination_panel | 10秒倒计时模态弹窗，每秒采集随机数 → 三位数平均值 |
| `stopwatch_timer.py` | divination_panel | 秒表模态弹窗，自由计时 + 3次记录 → 提取时间戳三位数 |
| `suangua/__init__.py` | divination_panel | 导出 SuanguaPanel |
| `suangua/suangua_panel.py` | divination_panel | 算卦主面板：算卦标题 + 梅花/六爻 dot + 时间管理 + QStackedWidget |
| `suangua/meihua_panel.py` | suangua_panel | 梅花面板：本/互/变三卦 + 体用标注 + ○/× 动爻标注 + 爻辞解读 |
| `suangua/liuyao_panel.py` | suangua_panel | 六爻面板：主卦 + 六神/世应/动爻/纳音 5列标注 + 主事爻选择 + 时间选择器 |

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

## 算卦面板 (suangua/) 架构

### SuanguaPanel — 共享时间管理

SuanguaPanel 管理共享的干支时间，通过 header 中的时间显示 + "修改"/"现在"按钮控制：

```
header: [算卦] [●梅花] [六爻] [stretch] [时间：2026-06-09 丙午年 甲午月 甲寅日 庚午时] [修改] [现在]
```

**时间传播链**：
```
SuanguaPanel._current_ganzhi (权威来源)
  ├── 计算：_compute_current_ganzhi()（首次 set_gua_result 时）
  ├── 修改：_TimePickerDialog（天干地支/阳历双模式）
  ├── 重置：_on_now_clicked() → 系统当前时间
  └── 传播：_propagate_time()
        ├── MeihuaPanel.set_time_ganzhi()  # 预留接口
        └── LiuyaoPanel.set_time_ganzhi()  # 触发 _refresh_analysis() 重算纳甲
```

**时间显示格式**：`时间：YYYY-MM-DD  年干支 月干支 日干支 时干支`
- 时间标签：白色 (#ffffff)，与 梅花/六爻 标签同字号 (font_size)
- 修改/现在按钮：蓝色 (#007aff)，字号 font_size - 1

### Header 垂直对齐规则（2026-06-09 修复）

两个面板 header 的 title 高度必须一致，否则视觉上不对齐：
- **QiguaPanel**："起卦" title 使用 `drawer.line_h` 作为高度
- **SuanguaPanel**："算卦" title 之前独立计算 `QFontMetrics.height() + 12`，与 `line_h` 不一致
- **修复**：SuanguaPanel 的 `_init_ui` 先创建 MeihuaPanel（获取 drawer.line_h），再用 `line_h` 作为 title 高度
- `refresh_font_size` 中 **必须先**调用 `meihua_panel.set_font_size()` 更新 drawer，**再**获取 `line_h`
- `ydist_menu2top`（两面板 Config 中均=20）QiguaPanel 实际未使用，SuanguaPanel 的 top_spacer 在多数字号下为 0

### 六爻面板 (LiuyaoPanel) — 5 列标注布局

```
[六神] [世应] [HexagramDrawer] [动爻o/x] [纳音]
  青     世       ████            ○      妻财甲寅木
  朱              ████            ×      官鬼丙午火
  勾     应       ████                   父母壬戌土
  ...
```

**六神标注**：单字 badge + 五行填充色
| 六神 | 显示 | 五行 | 颜色 |
|------|------|------|------|
| 青龙 | 龙 | 木 | #27ae60 绿底白字 |
| 朱雀 | 雀 | 火 | #e74c3c 红底白字 |
| 勾陈 | 陈 | 土 | #d4a017 黄底白字 |
| 螣蛇 | 蛇 | 土 | #d4a017 黄底白字 |
| 白虎 | 虎 | 金 | 跟随系统深色/浅色模式 |
| 玄武 | 玄 | 水 | #3498db 蓝底白字 |

- 白虎特殊处理：亮底→暗填充(#2c2c2e)+白字，暗底→亮填充(#cccccc)+暗字
- 世应：世=红色(TI_COLOR)，应=蓝色(YONG_COLOR)
- 静卦时动爻列显示"安静"（普通文字模式）

**标注对齐**：所有标注使用统一公式 `center_y = offset_y + name_area_h + (5 - line_idx) * line_h + line_h // 2`

**纳甲计算**：`analyze_gua(gua_name, day_gan)` → 每爻的六亲/纳甲/地支五行/世应/六神

### _TimePickerDialog — 双模式时间选择器

- **天干地支模式**：天干(10选1) + 地支(根据天干阴阳自动过滤，6选1) 分开选择
- **阳历模式**：年/月/日/时/分 QSpinBox
- **双向转换**：切换模式时自动转换（干支→公历近似值，公历→干支精确值）
- **启用时辰**：勾选框在阳历标签右侧，控制时/分的显示和值收集
- 阳干(甲丙戊庚壬)→阳支(子寅辰午申戌)，阴干(乙丁己辛癸)→阴支(丑卯巳未酉亥)

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

### QHBoxLayout 用 sizeHint 排位置 — 不是实际宽度！（耗时最长的坑，2026-06-09 已用 QGridLayout 方案绕过）

- **现象**：想让两个不同行的 QCheckBox 水平左对齐。尝试了以下所有方案都失败了：
  - `QWidget` + `setFixedWidth(w)` 做 spacer → layout 忽略 fixed width，按 sizeHint 排
  - `QLabel` + `setFixedWidth(w)` 做 spacer → 同上
  - `QSpacerItem(w, 0, Fixed, Fixed)` → 被 `addStretch()` 压缩到几乎消失
  - `QCheckBox.setMinimumWidth(w)` → widget 尺寸变了，但 sizeHint 不变，后面兄弟控件位置不变
  - `QCheckBox.setFixedWidth(w)` → 同上
  - `QSizePolicy.Maximum`（不用子类化）→ stretch 仍会撑开 widget

- **根因**：Qt QHBoxLayout 在给子控件分配位置时，**用 `widget.sizeHint()` 计算每个控件应占的宽度，而不是 `widget.width()` / `setFixedWidth()` / `setMinimumWidth()`**。所以任何外部 spacer、setFixedWidth 都无法改变兄弟控件的起始位置。

- **唯一生效方案**：子类化 QCheckBox 覆盖 `sizeHint()` 和 `minimumSizeHint()`，直接修改返回的 QSize 宽度。配合 `QSizePolicy.Maximum`（水平方向）防止 stretch 把 widget 撑大。
  ```python
  class _FixedWidthCheckBox(QCheckBox):
      def sizeHint(self):
          sh = super().sizeHint()
          return QSize(sh.width() + self._extra_width, sh.height())
  ```

- **教训**：Qt 布局引擎中，`sizeHint()` 是排版的核心依据。想要改变布局中控件的"占位宽度"，唯一的方法是改变它的 sizeHint。setFixedWidth、setMinimumWidth、QSpacerItem 都只是改变视觉尺寸或约束，不影响布局引擎对控件"应该占多少地方"的计算。

### Qt addSpacing() 会被压缩

- **现象**：`addSpacing(8)` 实际渲染后间距约 6px，少了约 2px
- **根因**：QHBoxLayout 中有 `addStretch()` 时，spacing 会被压缩
- **影响**：用 gap 值计算对齐位置时，需要加 `-2` 修正（`lock_x_actual = title_text_w + gap_lock - 2`）
- **教训**：依赖 addSpacing 精确像素值时不可靠，排列位置计算必须实测验证

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

### QGridLayout 列对齐方案（2026-06-09，替代 _FixedWidthCheckBox）

手动面板 Lock ↔ 单动爻 对齐问题，经过 9 轮测试后最终方案：

**之前尝试的失败方案**：
- `_FixedWidthCheckBox` + QHBoxLayout：QSizePolicy.Fixed 被 stretch 忽略，widget 被压缩
- `_FixedWidthSpacer` between checkboxes：间距精确，但 macOS QCheckBox 有 -2px 布局偏移
- `setFixedWidth(sizeHint)`：sizeHint 在 show() 前后变化，固定宽度不合理

**macOS QCheckBox -2px 偏移**（重要发现）：
- QCheckBox 跟在 QWidget spacer 后面时，`pos()` 比布局预期位置左偏 2px
- QCheckBox 跟在另一个 QCheckBox 后面时，无偏移
- `contentsMargins()` 返回全 0，无法通过 API 查询此偏移
- 这是 macOS Aqua 样式特有行为

**QGridLayout 方案**（后被 QWidget row wrappers 替代）：
```
col0 = QLabel("动爻设置" bold) / QCheckBox("上爻")
col1 = _FixedWidthSpacer(gap_lock)
col2 = QCheckBox("Lock") / QCheckBox("单动爻")
col3 = setColumnStretch(3, 1)
```
Lock 和 单动爻 在同一列 (col2)，天然水平对齐。所有字号 (15-18) 验证 `diff=0`。

**QGridLayout → QWidget row wrappers 替换**（2026-06-09）：
- **问题**：QGridLayout 用 `sizeHint` 决定行高（QCheckBox=19px），而非 `setFixedHeight(line_h)`，导致行间距缩到 24px（应为 28px），手动面板 checkbox 与卦图爻线不一致
- **根因**：金钱面板使用 QWidget 容器 + `setFixedHeight(line_h)` 保证行高严格等于 line_h，手动面板的 QGridLayout 无法做到
- **修复**：`_make_manual_panel()` 从 QGridLayout 改为 QVBoxLayout + 6 个 QWidget row wrappers（`setFixedHeight(line_h)`），与 `_make_lines_panel()` 同款方案
- **结果**：所有 6 爻对齐 delta=0px（见 test_manual_panel.py 测试10）

**卦图点击行为**（2026-06-09 修正）：
- 点击卦图只翻转阴阳爻线，**不修改动爻复选框**
- 之前点击动爻会自动清除其动爻标记（_changing_lines.discard），现已移除
- 无论点击动爻还是非动爻，`_changing_lines` 和复选框均保持不变

**单动爻功能**（2026-06-08~09）：
- `_single_line_cb`：仅在上爻行右侧，勾选后最多只有一个动爻（单选模式）
- 勾选时自动保留最大动爻数，清空其他；取消时清空所有动爻
- 勾选 → 立即切算卦面板到梅花模式（`_suangua_panel.switch_method("meihua")`）；取消不切回
- Lock 时与动爻复选框一同 disabled
- >1 动爻时自动取消单动爻（`_sync_controls_to_changing_lines`）
- **从不自动勾选**：仅手动勾选激活，减少到 1 个动爻不自动勾选

**HexagramDrawer.get_line_positions()**（2026-06-09 新增）：
- 返回每爻在 widget 本地坐标系中的位置信息（line_num/center_y/top_y/line_h/bar_rect）
- 顺序：初爻(index=0) → 上爻(index=5)
- 用途：对齐调试，与 checkbox 全局坐标比对验证 delta

### 梅花面板 Badge 渲染规则（meihua_panel._LineMarker）

**所有标注一律用 badge 模式**（`_badge_mode = True`），背景色块 + 白色文字：

| 标注类型 | 位置 | Badge 形状 | 背景色 |
|---------|------|-----------|--------|
| 体 | 本卦左侧 | 红色圆角正方形 | `TI_COLOR` (#d94f4f) |
| 用 | 本卦左侧 | 蓝色圆角正方形 | `YONG_COLOR` (#3b56bd) |
| 八卦名（乾坎艮震巽离坤兑）| 互卦左侧 | 五行对应色圆角正方形 | `get_wuxing_color_by_xiantian()` |
| ○（老阳） | 本卦右侧 | **红底圆 + 白环描边**（QPainter 双重 `drawEllipse`，浮点值保证同心） | `O_COLOR` |
| ×（老阴） | 本卦右侧 | **蓝底圆角方 + 白色 X 线**（QPainter `drawLine` x2，RoundCap，字体无关） | `X_COLOR` |

**重要约束**：
- **所有 badge 必须是正方形**：`side = max(fm.height() + 2*pad, text_w + 2*pad)`，严禁细长方形
- ○/× 用 **QPainter 矢量形状**绘制（○=红圆+白环，×=蓝方+白X线），**不用 drawText**，避免字体渲染不一致
- 体/用/八卦名：白色文字（`#ffffff`），手动基线居中 `baseline_y = badge_top + (badge_h + fm.ascent() - fm.descent()) / 2`
- ○ 内层白环使用**浮点值**不取整，Qt 亚像素抗锯齿保证与外圆同心
- zdepth：所有 marker widget 必须在 drawer 上层（`raise_()`）
- 参数字段：`badge_padding_ox` 控制 badge 轮廓比文字大多少 px（0 = 紧贴文字）

### SuanguaPanel header 与 QiguaPanel header 垂直不对齐（2026-06-09 修复）

- **现象**：算卦面板的"算卦"标题看起来比"起卦"标题低一点
- **根因**：两个面板的 title QPushButton 高度计算方式不同
  - QiguaPanel："起卦" title `setFixedHeight(drawer.line_h)` — 随 HexagramDrawer 字体变化
  - SuanguaPanel："算卦" title `setFixedHeight(QFontMetrics(font_size+4 bold).height() + 12)` — 独立计算
  - 两者数值不同（如 16pt 时 34px vs 40px），导致文本在按钮内垂直位置不一致
- **修复**：
  1. SuanguaPanel 的 `_init_ui` 先创建 MeihuaPanel，以获取 `drawer.line_h` 作为 title 高度
  2. `refresh_font_size` 先更新子面板字体（`meihua_panel.set_font_size()`），再取更新后的 `line_h`
- **教训**：并排面板的 header 高度必须来自同一数据源，不能各自独立计算

### 月份计算 bug（2026-06-09 修复）

- **现象**：6月(公历)显示为"未"月而非"午"月
- **根因**：`_compute_current_ganzhi` 中 `(month + 1) % 12` 导致 6→7(未)
- **修复**：改为 `month % 12`（6→午），与 `_gregorian_to_ganzhi_parts` 保持一致

### 三卦列间距规则

- **不强制统一列宽**：变卦列无标注，使用 drawer 自然宽度，不加 `_col_pad` 左侧空填充
- 列间 spacer 使用 `max(gap_marker_to_marker, gap_between_columns)`
- `compute_min_width` 公式区分有标注列（`col_w = col_pad + dw`）和无标注列（`dw`）
  - `min_w = gap_meihua_left + 2*col_w + dw + 2*spacer + gap_meihua_right`

### 六爻面板主事爻选择功能（2026-06-09 新增）

- 点击 HexagramDrawer 爻线选择主事爻，使用 `installEventFilter` 拦截点击（**不能**用 `set_clickable(True)`，因为那会切换爻阴阳）
- `_zhushiyao_line: int` — 0=未选择，1-6=初爻..上爻。再次点击同一爻取消选择
- 状态栏显示 `[Info] 设置主事爻为 {六亲}` / `[Info] 已取消主事爻`，5 秒后自动恢复
- 世应标注同列显示橙色「主」字方块（`set_markers` 追加条目到 `_shiying_marker`）。若与世应重叠，世应颜色变橙色
- 动爻标记联动变色：主事爻的 ○（老阳）→ 橙色 `#ff9500`，×（老阴）→ 紫色 `#af52de`
- 同一卦动爻变更时保留选择，换卦时重置
- 颜色常量放文件顶部（import 后第 3 行），方便快速修改
- QTimer 防堆积：用 `QTimer` 对象（`setSingleShot(True)`），每次点击先 `stop()`+`deleteLater()` 再创建新的
- 主事爻伏神高亮：`hexagram_drawer.py` 新增 `set_fushen_highlight(line_idx)`，在 paintEvent 伏神循环中逐行检测 `_fushen_highlight_line`，高亮行使用放大字体（+2pt）并加粗，位置对齐爻线边缘（⬇️初爻上方：文字底部对齐爻线顶部；⬆️其他爻下方：文字顶部对齐爻线底部）。`liuyao_panel.py` 通过 `_update_fushen_highlight()` 辅助方法联动，取消选择时传 `None` 恢复默认

### Qt eventFilter 双击问题（2026-06-09）

- **现象**：快速连续点击时第二下无反应
- **根因**：Qt 将快速双击识别为 `MouseButtonDblClick` 事件，而非 `MouseButtonPress`。只匹配 Press 的 eventFilter 会漏掉第二下
- **修复**：`event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick)`
