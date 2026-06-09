# 踩坑库（跨模块通用）

> 按类别组织。每条记录：现象 → 根因 → 修复 → 来源 → 适用范围。

## 症状速查索引

| 症状关键词 | 根因 | 详见 |
|-----------|------|------|
| 同行控件对不齐，spacer/setFixedWidth/SpacerItem 都无效 | sizeHint 决定布局占位，不是 width | [§1] |
| addSpacing() 间距比预期小 | stretch 压缩 spacing | [§1] |
| QGridLayout 行高不等于 setFixedHeight | 行高 = sizeHint | [§1] |
| `addWidget(w, AlignVCenter)` 控件不填满行高 | 不加 alignment 才填满 | [§1] |
| macOS 上 QCheckBox 比预期左偏 2px | Aqua 样式特有偏移 | [§1] |
| resize/refresh 中 widget.width() 返回旧值（测试过但 app 挂了） | 布局未完成，width 是旧值 | [§2] |
| setFixedWidth 后布局占位不变 | 占位看 sizeHint | [§2] |
| QPushButton 显示 `<b>X</b>` 源码而非加粗 | QPushButton 无 RichText | [§3] |
| QLineEdit 显示 `<span>` 源码 | QLineEdit 无 HTML | [§3] |
| `painter.drawRect(QPointF, QPointF)` 报错 | 不支持此重载 | [§3] |
| QPainter 和 CSS 文字字号不一致 | font-size:px ≠ pointSize | [§3] |
| 弹窗选中项后崩溃 SIGSEGV | 信号处理器内同步销毁 | [§4] |
| 快速连点第二下无反应 | 双击是 DblClick 非 Press | [§4] |
| 快速操作后多个延迟动作堆积 | QTimer 未防抖 | [§4] |
| stylesheet f-string 报 KeyError | `{` 没加倍为 `{{` | [§5] |
| 侧边栏透明不生效 | 透明链某层没设 transparent | [§5] |
| 有/无下划线按钮高度不一致 | border-bottom 占 layout | [§5] |
| PyInstaller 打包后数据文件找不到 | `__file__` 虚拟路径 | [§6] |
| 打包后图标/数据库缺失 | spec 未递归收集 | [§6] |
| 初爻和上爻显示反了 | 索引映射方向不一致 | [§7] |
| 模式切换后旧值覆盖新映射 | 初始化循环无条件执行 | [§7] |
| 并排面板 title 高低不平 | 各自独立算高度 | [§7] |
| 设了 FixedHeight 被覆盖 | _update_panel_layout 批量覆写 | [§7] |
| 干支月比公历月差一位 | (month+1)%12 多+1 | [§7] |
| 点击卦图动爻消失了 | 视觉翻转误联动爻数据 | [§7] |
| 单动爻勾选/取消行为不符合预期 | 边界条件未全定义 | [§7] |
| 箭头与爻线垂直偏移 | offset_y 照搬其他 widget 未调整 | [§7] |

---

## 1. Qt 布局引擎

### ⚠️ sizeHint 决定布局，不是 width/setFixedWidth（耗时最长的坑，9轮测试）

- **目标**：手动面板中，让不同行的两个 QCheckBox（"Lock" 和 "单动爻"）水平左对齐。
- **失败尝试（全部无效）**：
  1. `QWidget` + `setFixedWidth(w)` 做 spacer → layout 忽略 fixed width，按 sizeHint 排
  2. `QLabel` + `setFixedWidth(w)` 做 spacer → 同上
  3. `QSpacerItem(w, 0, Fixed, Fixed)` → 被 `addStretch()` 压缩到几乎消失
  4. `QCheckBox.setMinimumWidth(w)` → widget 尺寸变了，但 sizeHint 不变，兄弟控件位置不变
  5. `QCheckBox.setFixedWidth(w)` → 同上
  6. `QSizePolicy.Maximum`（不用子类化）→ stretch 仍会撑开 widget
  7. QGridLayout 方案 → 行高用 sizeHint=19px 不用 setFixedHeight(28px)，行间距缩到 24px
  8. `_FixedWidthSpacer` between checkboxes → 间距精确，但 macOS QCheckBox 有 -2px 偏移
  9. `setFixedWidth(sizeHint)` → sizeHint 在 show() 前后变化，固定值不合理
- **根因**：Qt QHBoxLayout 在给子控件分配位置时，**核心依据是 `widget.sizeHint()`**，不是 `widget.width()` / `setFixedWidth()` / `setMinimumWidth()`。任何外部 spacer 或尺寸约束都无法改变兄弟控件的起始位置。唯一方法是改变控件的 sizeHint 返回值。
- **最终修复**：
  ```python
  class _FixedWidthCheckBox(QCheckBox):
      def sizeHint(self):
          sh = super().sizeHint()
          return QSize(sh.width() + self._extra_width, sh.height())
  ```
  配合 `QSizePolicy.Maximum`（水平）防止 stretch 撑大。
  随后又从 _FixedWidthCheckBox 方案迁移到 QWidget row wrappers（`setFixedHeight(line_h)`）+ QVBoxLayout，与 `_make_lines_panel()` 同款方案，确保所有 6 爻对齐 delta=0px。
- **来源**：`yijingTab/qigua/divination_panel.py` — 手动面板 _make_manual_panel()，Lock 与单动爻两列对齐
- **教训**：Qt 布局引擎中 sizeHint() 是排版的核心，setFixedWidth/MinimumWidth 都只是视觉约束。想要改变控件的「占位」，只能改 sizeHint。
- **适用范围**：所有 QHBoxLayout/QGridLayout/QVBoxLayout 对齐需求，尤其是跨行对齐

### addSpacing() 被 Stretch 压缩
- **现象**：`addSpacing(8)` 实际渲染 ~6px
- **根因**：QHBoxLayout 有 `addStretch()` 时 spacing 被压缩
- **修复**：不依赖 addSpacing 精确像素；计算对齐时实测验证
- **来源**：`yijingTab/qigua/divination_panel.py` — header 标签间距 Lock 位置计算 +2px 修正
- **适用范围**：所有含 addStretch() 的布局

### QGridLayout 行高 = sizeHint，忽略 setFixedHeight
- **现象**：QGridLayout 行高用 QCheckBox.sizeHint=19px，不用 setFixedHeight(28px)
- **修复**：用 QVBoxLayout + QWidget row wrappers（setFixedHeight(line_h)）替代 QGridLayout
- **来源**：`yijingTab/qigua/divination_panel.py` — 手动面板 _make_manual_panel()，行高缩到 24px 而非 28px
- **适用范围**：所有需要精确行高的网格布局

### QHBoxLayout 不用 AlignVCenter
- **现象**：`addWidget(w, 0, AlignVCenter)` 让控件在行内垂直居中而非填满行高
- **修复**：不加 alignment 参数，widget 自动填满行高
- **来源**：`yijingTab/suangua/suangua_panel.py` — 算卦 header 标签 y 位置与起卦不一致；`yijingTab/com/method_label_bar.py` — 统一 fill-height 布局
- **适用范围**：所有需要控件填满行高对齐的场景

### macOS QCheckBox -2px 偏移
- **现象**：QCheckBox 跟在 QWidget spacer 后面时，x 坐标比预期偏左 2px
- **根因**：macOS Aqua 样式特有行为，contentsMargins() 返回全 0
- **修复**：QCheckBox 跟在另一个 QCheckBox 后面时无偏移；或计算时 +2px
- **来源**：`yijingTab/qigua/divination_panel.py` — 手动面板 Lock checkbox 跟在 spacer 后左偏
- **适用范围**：macOS 平台所有 QCheckBox 布局

## 2. Widget 尺寸

### ⚠️ widget.width() 在 resize 事件中返回旧值（最隐蔽的坑）

- **现象**：ButtonBar 工具栏按钮（截图|AI|保存|读取）在 app 启动时**消失或严重偏移**，但 `_debug/test_button_alignment.py` 测试脚本中一切正常。同一个计算逻辑，测试过但 app 挂了——这是最让人怀疑人生的时刻。
- **为什么测试过但实际不行**：测试脚本在 `QiguaPanel.show()` 之后手动调用 `refresh_font_size()`，此时 Qt 布局已完成，`width()` 返回正确值。但在真实启动流程中，`apply_appearance()` → `refresh_font_size()` 在**首次 resizeEvent 回调**中被触发，Qt 布局引擎还没完成本轮 layout，`drawer.width()` 返回的是**布局前旧值**（可能是 0 或默认值 100），而不是 `set_font_size()` 刚设的新值（130）。结果 `left_offset` 算成 0 或错误值，按钮定位到屏幕外或被遮挡。
- **代码对比**：
  ```python
  # ❌ 错误 — _init_ui 中 work，refresh_font_size 中不 work
  left_offset = self._drawer.width() + _gap_drawer
  
  # ✅ 正确 — 永远准确，不依赖布局完成状态
  left_offset = self._drawer.minimumWidth() + _gap_drawer
  ```
- **修复**：项目中所有 `refresh_font_size`/`refresh_text_color`/resizeEvent 回调链中的 `.width()` / `.height()` 替换为 `.minimumWidth()` / `.minimumHeight()`。`minimumWidth()` 是 `set_font_size()` 中显式 set 的，不依赖 Qt 布局完成，永远准确。
- **来源**：`yijingTab/button/button_bar.py` — `refresh_font_size()` 用 `drawer.width()` 计算 `left_offset`，导致按钮定位失败；`yijingTab/qigua/divination_panel.py` — 同样的 `.width()` 问题
- **检测方法**：`grep -n "\.width()\|\.height()"` 所有在 resize 事件链中被调用的函数，一律替换
- **适用范围**：**所有** resizeEvent / refresh_font_size / refresh_text_color / apply_appearance 回调链中的 widget 尺寸获取

### setFixedWidth 不影响布局占位
- **现象**：给 widget 设 setFixedWidth(200) 后，布局中它仍按 sizeHint 占位
- **修复**：覆盖 sizeHint() 或使用 QSizePolicy.Fixed
- **来源**：`yijingTab/qigua/divination_panel.py` — 手动面板列宽容器
- **适用范围**：所有 QHBoxLayout 中的固定宽度控件

## 3. PySide6 API 陷阱

### QPushButton 不支持 RichText
- **现象**：`btn.setText("<b>金钱</b>/蓍草")` 显示原始 HTML 源码
- **根因**：QPushButton 没有 `setTextFormat()` 方法（QLabel 有）
- **修复**：拆分多个 QPushButton + QLabel 分隔符；或改用 QLabel 做点击
- **来源**：`yijingTab/qigua/divination_panel.py` — 金钱/蓍草标签想部分加粗，单按钮方案失败
- **适用范围**：所有需要部分加粗/变色的按钮

### QLineEdit 不支持 HTML
- **现象**：QLineEdit 中 `<span style="color:...">` 原样显示
- **修复**：用 QLabel + `setTextFormat(Qt.TextFormat.RichText)` 替代
- **来源**：`utils/statusbar_manager.py` — 状态消息传 HTML span 后显示原始源码
- **适用范围**：所有状态栏/消息显示

### QPainter drawRect 不支持 (QPointF, QPointF) 重载
- **现象**：`painter.drawRect(topLeft, bottomRight)` 类型错误
- **修复**：用 `QRectF(x, y, w, h)` 或 `(x, y, w, h)` 四参数形式
- **来源**：`yijingTab/suangua/meihua_panel.py` — _LineMarker ○/× 矢量绘制；`yijingTab/suangua/liuyao_panel.py` — 生克 badge
- **适用范围**：所有 QPainter 绘制

### CSS font-size: px ≠ QFont.setPointSize
- **现象**：QPainter QFont 和 CSS font-size 度量不一致
- **规则**：需与 drawer 对齐的文字用 QFont + setFont()，不用 CSS
- **来源**：`yijingTab/com/hexagram_drawer.py` — QPainter 卦名文字与 stylesheet 标签字号对不齐
- **适用范围**：所有 QPainter + CSS 混用的场景

## 4. 信号/事件安全

### 信号处理器内同步销毁 → SIGSEGV
- **现象**：点击"起卦"标题→弹出 64 卦列表→选中某项→ **Segmentation fault: 11**，整个 app 崩溃
- **根因**：`_on_picker_selected` 是 `itemClicked` 信号处理器，在其内部调用 `popup.close()` 同步销毁了 picker 自身。Qt 事件循环在信号处理返回后还要访问 picker → 悬空指针 → SIGSEGV
- **修复**：改用 `popup.hide()` + `popup.deleteLater()` 延迟销毁。额外处理：手动恢复 Lock 状态（如果弹出前是 locked），清理 `_gua_picker` 引用防止悬空
- **来源**：`yijingTab/qigua/divination_panel.py` — `_GuaPickerPopup` + `_show_gua_picker()` + `_on_picker_selected()`
- **教训**：在信号/事件处理器内**永远不要同步销毁触发该信号的控件**。`deleteLater()` 是 Qt 安全的延迟销毁方式，控件会在事件循环返回后再被清理
- **适用范围**：所有弹窗/对话框/菜单的信号处理；任何在事件处理器内需要销毁控件自身的场景

### eventFilter 双击丢失
- **现象**：快速连点第二下无反应
- **根因**：Qt 快速双击识别为 `MouseButtonDblClick`，不触发 `MouseButtonPress`
- **修复**：`event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick)`
- **来源**：`yijingTab/suangua/liuyao_panel.py` — HexagramDrawer eventFilter 拦截点击选主事爻
- **适用范围**：所有 eventFilter 拦截点击

### QTimer 防堆积
- **现象**：快速操作导致多个 QTimer 堆积触发
- **修复**：用 `QTimer.singleShot` 或每次先 `stop()+deleteLater()` 再创建新的
- **来源**：`yijingTab/suangua/liuyao_panel.py` — 主事爻选择状态栏消息 5 秒恢复，快速点击堆积
- **适用范围**：所有需要延迟操作的 UI 交互

## 5. CSS/样式

### .format() 模板中大括号必须加倍
- **规则**：除 `{text_color}` 占位符外，所有 `{` `}` 必须写为 `{{` `}}`
- **范例**：`"QWidget {{ background: {bg}; }}"` ✅ | `"QWidget { background: {bg}; }"` ❌
- **来源**：全局 stylesheet 模板系统 — `settings/panels/*.py` `.format()` 调用
- **适用范围**：所有 Python f-string/.format() 中的 Qt stylesheet

### 透明链必须层层显式设置
- **现象**：侧边栏毛玻璃效果不生效
- **根因**：透明效果需要链路中每一层（widget→scrollArea→viewport→list）都显式设 `background: transparent`
- **来源**：`settings/settings_tab.py` — macOS 侧边栏 NSAutomaticWindowTabbing 毛玻璃材质
- **适用范围**：所有需要透明/毛玻璃效果的控件层级

### 浅色背景控件文字颜色
- **规则**：有自身背景的控件（按钮、输入框）→ 硬编码深色文字
- **规则**：透明背景控件 → 用 `self._text_color` 跟随主题
- **来源**：全局外观系统 — `appearance_manager.apply_appearance()` → 各面板 refresh_text_color 链
- **适用范围**：所有支持深色/浅色模式切换的面板

### border-bottom 对齐陷阱（三版迭代）

- **目标**：金钱/蓍草双按钮，选中子模式加下划线，未选中无下划线。但两个按钮必须水平对齐。
- **第一版（失败）**：选中加 `border-bottom: 2px solid`，未选中无 border。结果未选中按钮比选中按钮**偏高**（少了 border 的 2px 占位），视觉不对齐。
- **第二版（失败）**：未选中也加 `border-bottom: 2px solid transparent` + `padding-bottom: 2px` 占位保持对齐。但 lines **未激活**时（切到手工/报数），这两个按钮仍带透明 border+padding，导致比同行的"手工""报数"按钮**偏高 2px**。
- **最终修复**：
  ```python
  ul = QiguaConfig.lines_underline and is_active  # 关键条件
  # lines 激活 → 无论选中/未选中都给 padding（透明 border 占位）
  # lines 未激活 → 不给任何 padding/border，与手工/报数同一基线
  ```
- **来源**：`yijingTab/qigua/divination_panel.py` — 金钱/蓍草标签下划线 + `/` 分隔符对齐
- **教训**：CSS border 占 layout 空间，相邻按钮有/无 border 会导致垂直位置偏移。统一给透明 border 占位是最稳妥的方案，但要注意只在激活状态下才给。
- **适用范围**：所有相邻按钮需要视觉对齐、且部分有下划线的场景

## 6. 构建/打包

### PyInstaller __file__ 虚拟路径
- **现象**：`os.path.dirname(__file__) + "/../data"` 在 PyInstaller 中无效
- **根因**：`__file__` 指向 PYZ 归档内的虚拟路径，中间目录不存在
- **修复**：用 `os.path.abspath()` 包裹；或使用 `config_manager.get_project_root()`
- **来源**：全局 build 修复 (2026-06-08) — `settings/appearance_manager.py`, `settings/config_manager.py`, `data/` 加载
- **适用范围**：所有模块级数据路径

### 数据文件收集要递归展开
- **规则**：spec 用 `glob.glob("src/data/**", recursive=True)` 而非 `"src/data"`
- **过滤**：排除 `.DS_Store`/`__pycache__`/`.pyc`/`.7z`
- **来源**：`build/` PyInstaller spec (2026-06-08) — 打包后图标/数据库/城市数据缺失
- **适用范围**：所有 PyInstaller 打包

## 7. 通用逻辑

### 索引映射方向验证
- **现象**：初爻和上爻两端搞反，UI 显示上下颠倒
- **教训**：改索引映射前先画表验证两端（0→初爻? 5→上爻?）
- **来源**：`yijingTab/com/hexagram_drawer.py` — _yang_lines[0]=初爻；`yijingTab/qigua/divination_panel.py` — manual_cbs[0]=上爻（UI从上而下）
- **适用范围**：所有数组↔UI列表映射

### 模式切换时旧值覆盖正确映射值
- **现象**：金钱↔蓍草互切时，`cross_map` 正确将少阳→少阳、老阳→老阳等映射完毕，但随后 `_update_lines_combo_options()` 中的初始化循环用简单阴阳值覆盖了所有 combo，正确的映射被冲掉
- **根因**：初始化循环无条件执行，不管来源模式是谁
- **修复**：仅当 `prev not in ("coin", "yarrow")`（即从手工/报数切过来）时才执行初始化循环。金钱↔蓍草之间互切时保留 cross_map 结果
- **来源**：`yijingTab/qigua/divination_panel.py` — `_update_lines_combo_options()` + `_set_lines_mode()`
- **教训**：模式切换时，「初始化填充」和「跨模式保留」是互斥的——需要根据来源模式判断走哪条路径
- **适用范围**：所有模式切换逻辑，尤其是涉及值映射转换的

### Header 并排面板高度必须同源
- **现象**：并排两个面板的 title 视觉上高低不平
- **根因**：两个面板独立计算 title 高度（一个用 drawer.line_h，一个用 QFontMetrics.height()+12）
- **修复**：统一来自同一个 `drawer.line_h`
- **来源**：`yijingTab/qigua/divination_panel.py` + `yijingTab/suangua/suangua_panel.py` — "起卦""算卦"标题高度不一致
- **适用范围**：所有并排面板的 header 对齐

### _update_panel_layout 覆盖 widget 高度
- **现象**：新增 QLabel 设了 FixedHeight，渲染后被覆盖成 line_h
- **根因**：该方法遍历所有顶层 widget 强制设为 line_h
- **修复**：设 objectName 并在遍历时跳过
- **来源**：`yijingTab/qigua/divination_panel.py` — _update_panel_layout() 批量行高同步
- **适用范围**：所有有批量尺寸同步的面板

### 生克箭头 offset_y 取决于 widget 垂直起点
- **现象**：箭头三角形与爻线不对齐，偏移约 name_h 像素
- **根因**：照搬 _LineMarker 的 offset_y=-name_h，但 _ArrowColumn 无上方 header，起点不同
- **修复**：offset_y=0（widget 顶部 = drawer 顶部）
- **来源**：`yijingTab/suangua/liuyao_panel.py` — _ArrowColumn 变卦生克箭头
- **适用范围**：所有 QPainter 绘制 + 垂直偏移量配置

### 月份计算 bug（干支月差一位）
- **现象**：公历 6 月显示为"未"月而非"午"月（差了一个月）
- **根因**：`_compute_current_ganzhi` 中 `(month + 1) % 12` 导致 6→7(未)
- **修复**：改为 `month % 12`（6→午），与 `_gregorian_to_ganzhi_parts` 保持一致
- **来源**：`yijingTab/suangua/suangua_panel.py` — `_compute_current_ganzhi()`
- **教训**：干支月与公历月的映射公式需要和项目中其他干支计算函数交叉验证，不能独立实现
- **适用范围**：所有干支/农历日期计算

### Header 标签间距对齐只动标签间 gap
- **规则**：标题 → 第一个 dot 的间距固定为 `_gap_md`，不随对齐计算变动
- **规则**：只方法标签之间的 3 个 gap 参与均分计算
- **规则**：gap 设下限 `max(4, ...)` 防止负数
- **来源**：`yijingTab/qigua/divination_panel.py` — `_update_header_alignment()`
- **适用范围**：所有 header 中多个标签的水平对齐计算

### 卦图点击：阴阳翻转 ≠ 动爻标记
- **修正前**：点击卦图动爻会自动清除其动爻标记（`_changing_lines.discard`），用户点多了动爻消失造成困惑
- **修正后**：点击卦图只翻转阴阳爻线，**不修改动爻复选框和 _changing_lines**
- **来源**：`yijingTab/qigua/divination_panel.py` — HexagramDrawer click 处理
- **适用范围**：所有「显示」和「数据」分离的交互——点击视觉元素不应偷偷改数据

### 单动爻模式的边界条件
- 勾选单动爻 → 自动保留最大动爻数，清空其他 → 切算卦面板到梅花
- 取消单动爻 → 清空所有动爻 → 不切回其他模式
- Lock 时与动爻复选框一同 disabled
- >1 动爻时自动取消单动爻（`_sync_controls_to_changing_lines` 触发）
- **从不自动勾选**：减少到 1 个动爻不会自动勾选，仅手动激活
- **来源**：`yijingTab/qigua/divination_panel.py` — `_single_line_cb` + `_sync_controls_to_changing_lines()`
- **适用范围**：所有「单选模式」checkbox — 勾选/取消的连锁反应需要明确定义每一条边界
