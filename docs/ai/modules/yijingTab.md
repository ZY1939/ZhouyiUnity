# 易经Tab 架构

> 最后更新：2026-06-10

---

## 文件分层

```
src/yijingTab/
├── __init__.py              # 包导出：QiguaPanel, GuaResult, case CRUD
├── CONST_DEFINE_UI.py       # QiguaConfig / SuanguaConfig / MeihuaConfig 参数集中管理
│
├── com/                     # 通用组件（qigua + suangua 共享）
│   ├── __init__.py            导出 HexagramDrawer, DotButton, MethodLabelBar
│   ├── hexagram_drawer.py     HexagramDrawer — 卦图 QPainter 绘制
│   ├── dot_button.py          DotButton — 圆点选择按钮
│   ├── method_label_bar.py    MethodLabelBar — 方法标签栏公共组件
│   ├── bagua.py               先天八卦常量 + GuaResult 数据类
│   ├── hexagram_calc.py       三位数→卦 / 六爻→卦 核心计算
│   └── hexagram_loader.py     读取 content/*.jsonc，64卦查询 + 缓存
│
├── qigua/                   # 起卦面板
│   ├── divination_panel.py    QiguaPanel 起卦主面板（卦图 + 4输入 + 结果 + Lock + 算卦集成）
│   ├── countdown_timer.py     10秒随机倒计时弹窗
│   ├── stopwatch_timer.py     秒表计时弹窗
│   ├── hexagram_painter.py    🔮 画卦接口空壳
│   ├── case_manager.py        🔮 案例 CRUD → usrCfg/divination_cases.json
│   └── _debug/                调试脚本
│
├── suangua/                 # 算卦面板
│   ├── suangua_panel.py       算卦主面板（算卦标题 + MethodLabelBar + 时间管理 + QStackedWidget）
│   ├── meihua_panel.py        梅花面板（本/互/变三卦 + 体用标注 + 爻辞解读）
│   ├── liuyao_panel.py        六爻面板（主卦 + 六神/世应/动爻/纳音 5列 + 变卦）
│   ├── common.py              公共工具（_LineMarker、干支历法、卦辞解读）
│   ├── Window_timeSetting.py  时间设置弹窗（干支/阳历双模式）
│   └── _debug/                调试脚本
│
├── button/
│   └── button_bar.py         ButtonBar — 截图|AI|保存|读取 工具栏按钮
│
└── _debug/                  测试脚本
```

### 状态标记
| 标记 | 含义 |
|------|------|
| ✅ | 活跃使用 |
| 🔮 | 预留接口，未接入UI |
| 🗑️ | 已被内联替代，可安全删除 |

### 遗留文件（🗑️ 可删除）
| 文件 | 被谁替代 |
|------|----------|
| `lines_input.py` | `divination_panel._make_lines_panel()` |
| `manual_input.py` | `divination_panel._make_manual_panel()` |
| `number_input.py` | `divination_panel._make_three_panel()` |
| `result_view.py` | `divination_panel._build_footer()` + `_show_result()` |

### 预留接口接入提示
- **case_manager**：在 `divination_panel._show_result()` 末尾调用 `save_case(result, method=self._current_method, notes="")` 即可打通。`__init__.py` 已导出 `save_case, load_cases` 等 5 个函数。
- **hexagram_painter**：`GuaPainter.draw_gua()/clear()` 空壳，后续在 QWidget 上绘制图形化卦象。

---

## 调用关系

```
yijing_viewer.py (Tab)
  └── QiguaPanel (divination_panel.py)
        ├── com/bagua.py              常量 + 数据结构
        ├── com/hexagram_calc.py      核心计算
        ├── com/hexagram_loader.py    64卦数据库
        ├── com/hexagram_drawer.py    卦图绘制
        ├── countdown_timer.py        倒计时
        ├── stopwatch_timer.py        秒表
        ├── button/button_bar.py      工具栏按钮
        └── suangua/SuanguaPanel      算卦面板
              ├── MeihuaPanel         梅花断卦
              └── LiuyaoPanel         六爻断卦
```

---

## 关键设计模式

### 字体/颜色刷新链
```
apply_appearance() → yijing_viewer.refresh_font_size(fs)
  → qigua_panel.refresh_font_size(fs)
    → drawer.set_font_size(fs)           # 重算 line_h/bar_h/name_area_h
    → 各面板 _update_panel_layout()       # 行高同步
    → ButtonBar.refresh_font_size()       # 工具栏按钮重定位
    → suangua_panel.refresh_font_size(fs) # 算卦面板
      → meihua_panel / liuyao_panel
```

### 间距体系（以 line_h 为基准）
```python
_gap_xs = max(2, int(line_h * 0.12))   # 极小间距
_gap_sm = max(4, int(line_h * 0.25))   # 小间距
_gap_md = max(6, int(line_h * 0.45))   # 中等间距
```
所有可调参数在 `_init_ui` 集中声明。

### HexagramDrawer 对齐公式
```
bar 中心 y = offset_y + name_area_h + line_h//2 + row * line_h
```
右侧面板 checkbox/label 用 row_wrapper.setFixedHeight(line_h) 保证行高一致。

### Header 对齐
- QiguaPanel "起卦" title 高度 = `drawer.line_h`
- SuanguaPanel "算卦" title 高度 = 同一个 `drawer.line_h`（先创建子面板再取）
- 并排面板 header 必须来自同一数据源

---

## 核心组件 API

### HexagramDrawer
| 方法 | 说明 |
|------|------|
| `set_font_size(fs)` | 重算所有几何参数 |
| `set_text_color(tc)` | 卦名/爻名文字颜色 |
| `set_wuxing_mode(enabled)` | 五行着色模式 |
| `set_disabled_look(enabled, color)` | 灰色禁用外观 |
| `set_clickable(enabled)` | 点击翻转阴阳 |
| `set_line_color_overrides({idx: color})` | 逐爻颜色覆盖 |
| `get_line_positions()` | 返回每爻坐标信息（对齐调试） |
| `configure(**kwargs)` | 手动覆盖几何参数 |

### MethodLabelBar
| 方法 | 说明 |
|------|------|
| `current_method() → str` | 当前选中方法 |
| `set_current_method(key)` | 程序切换（无信号） |
| `set_label_enabled(idx, enabled)` | 禁用/启用标签 |
| `refresh_font_size(fs)` / `refresh_text_color(tc)` | 外观刷新 |

信号：`method_selected(key: str)`

### ButtonBar
- 4 按钮：截图 | AI | 保存 | 读取
- 定位：`move()` 手动定位
- 对齐：保存.x = 随机.x，读取.x = 秒表.x
- 尺寸参数：`QiguaConfig.gap_btn_pad` / `gap_btn_h`

---

## SuanguaPanel 时间管理

```
SuanguaPanel._current_ganzhi (权威来源)
  ├── 计算：_compute_current_ganzhi()（首次 set_gua_result 时）
  ├── 修改：Window_timeSetting（干支/阳历双模式）
  ├── 重置："现在"按钮 → 系统当前时间
  └── 传播：→ LiuyaoPanel.set_time_ganzhi() 重算纳甲
```

---

## MeihuaPanel Badge 规则

| 标注 | 位置 | 形状 | 颜色 |
|------|------|------|------|
| 体 | 本卦左 | 红底方 | `TI_COLOR` #d94f4f |
| 用 | 本卦左 | 蓝底方 | `YONG_COLOR` #3b56bd |
| 八卦名 | 互卦左 | 五行色底方 | `get_wuxing_color_by_xiantian()` |
| ○ 老阳 | 本卦右 | 红圆+白环描边 | `O_COLOR` |
| × 老阴 | 本卦右 | 蓝方+白X线 | `X_COLOR` |

- 所有 badge 必须正方形
- ○/× 用 QPainter 矢量形状，不用 drawText
- 体/用/八卦名：白字居中

---

## LiuyaoPanel 六爻

### 5 列标注布局
```
[六神] [世应] [HexagramDrawer] [动爻] [纳音]
```

### 六神颜色
| 六神 | 显示 | 颜色 |
|------|------|------|
| 青龙 | 龙 | #27ae60 绿 |
| 朱雀 | 雀 | #e74c3c 红 |
| 勾陈 | 陈 | #d4a017 黄 |
| 螣蛇 | 蛇 | #d4a017 黄 |
| 白虎 | 虎 | 系统深/浅自适应 |
| 玄武 | 玄 | #3498db 蓝 |

### 变卦区域
- 本卦六亲 → 箭头(生克方向) → 变卦drawer → 变卦六亲(按本卦宫五行)
- 静卦(0动爻)时整体隐藏
- 箭头指向受作用方；比和=双箭头

---

## CONST_DEFINE_UI 参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `QiguaConfig.fs_lines_inactive_reduce` | 2 | lines 未选中字号缩减 |
| `QiguaConfig.lines_underline` | True | 选中子模式下划线 |
| `QiguaConfig.gap_btn_pad` | 30 | 按钮水平留白 |
| `QiguaConfig.gap_btn_h` | 38 | 按钮高度 |
| `SuanguaConfig.ydist_menu2top` | 20 | 菜单距顶 |
| `MeihuaConfig.badge_padding_ox` | — | badge 内边距 |
| `LiuyaoConfig.arrow_color_*` | — | 生克箭头颜色 |

---

## 调试测试

> 每个 `_debug/README.md` 记录完整的设计意图 + 回归覆盖，先读 README 再跑脚本。

| _debug 目录 | 测试范围 | 关键回归项 |
|-------------|---------|-----------|
| [`_debug/`](../../src/yijingTab/_debug/README.md) | 起卦全局：对齐验证/按钮对齐/网格行高/64卦弹窗/手工面板交互 (5个脚本) | sizeHint 9轮修复、widget.width() 陷阱、SIGSEGV、单动爻边界 |
| [`qigua/_debug/`](../../src/yijingTab/qigua/_debug/README.md) | 起卦标签：方法标签交互/MethodLabelBar 公共组件 (2个脚本, 82项) | QPushButton RichText、border-bottom 三版迭代、AlignVCenter |
| [`suangua/_debug/`](../../src/yijingTab/suangua/_debug/README.md) | 算卦面板：梅花badge/六爻对齐/header对齐/列间距/布局诊断 (7个脚本) | × float→int 偏移、月份计算、header 高度不一致、列固定宽度 |

### 运行策略
- 改 `divination_panel.py` → 先跑 `_debug/` + `qigua/_debug/`
- 改 `liuyao_panel.py` → 跑 `suangua/_debug/` 全部六爻相关
- 改 `meihua_panel.py` / common.py → 跑 `suangua/_debug/test_common.py`
- 改 header / 方法标签 → 跑 `qigua/_debug/`
- 只跑相关的，不使用 `python3 -m pytest` 全量（token 浪费）

## 相关文档
- 通用踩坑：[../PITFALLS.md](../PITFALLS.md)
- 编码规范：[../CONVENTIONS.md](../CONVENTIONS.md)
