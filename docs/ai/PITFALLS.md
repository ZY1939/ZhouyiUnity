# 踩坑库（跨模块通用）

> 按类别组织，不按模块。每条标注适用范围。

---

## 1. Qt 布局引擎

### sizeHint 决定布局，不是 width/setFixedWidth
- **现象**：setFixedWidth/SpacerItem 无法改变兄弟控件在 QHBoxLayout 中的水平位置
- **根因**：QHBoxLayout 用 `widget.sizeHint()` 计算控件占位宽度，不是 `widget.width()`
- **修复**：子类化覆盖 `sizeHint()` 和 `minimumSizeHint()`，返回期望宽度
- **适用范围**：所有 QHBoxLayout/QGridLayout 对齐需求

### addSpacing() 被 Stretch 压缩
- **现象**：`addSpacing(8)` 实际渲染 ~6px
- **根因**：QHBoxLayout 有 `addStretch()` 时 spacing 被压缩
- **修复**：不依赖 addSpacing 精确像素；计算对齐时实测验证
- **适用范围**：所有含 addStretch() 的布局

### QGridLayout 行高 = sizeHint，忽略 setFixedHeight
- **现象**：QGridLayout 行高用 QCheckBox.sizeHint=19px，不用 setFixedHeight(28px)
- **修复**：用 QVBoxLayout + QWidget row wrappers（setFixedHeight(line_h)）替代 QGridLayout
- **适用范围**：所有需要精确行高的网格布局

### QHBoxLayout 不用 AlignVCenter
- **现象**：`addWidget(w, 0, AlignVCenter)` 让控件在行内垂直居中而非填满行高
- **修复**：不加 alignment 参数，widget 自动填满行高
- **适用范围**：所有需要控件填满行高对齐的场景

### macOS QCheckBox -2px 偏移
- **现象**：QCheckBox 跟在 QWidget spacer 后面时，x 坐标比预期偏左 2px
- **根因**：macOS Aqua 样式特有行为，contentsMargins() 返回全 0
- **修复**：QCheckBox 跟在另一个 QCheckBox 后面时无偏移；或计算时 +2px
- **适用范围**：macOS 平台所有 QCheckBox 布局

## 2. Widget 尺寸

### ⚠️ widget.width() 在 resize 事件中返回旧值
- **现象**：resize/refresh_font_size 中 `widget.width()` 返回布局前旧值（0 或 100），非 set_font_size 刚设的新值（130）
- **根因**：resize 事件触发时 Qt 布局尚未完成本轮 layout
- **修复**：统一用 `widget.minimumWidth()` — 显式设置的值，永远准确
- **适用范围**：**所有** resizeEvent/refresh_font_size/refresh_text_color 回调

### setFixedWidth 不影响布局占位
- **现象**：给 widget 设 setFixedWidth(200) 后，布局中它仍按 sizeHint 占位
- **修复**：覆盖 sizeHint() 或使用 QSizePolicy.Fixed
- **适用范围**：所有 QHBoxLayout 中的固定宽度控件

## 3. PySide6 API 陷阱

### QPushButton 不支持 RichText
- **现象**：`btn.setText("<b>金钱</b>/蓍草")` 显示原始 HTML 源码
- **根因**：QPushButton 没有 `setTextFormat()` 方法（QLabel 有）
- **修复**：拆分多个 QPushButton + QLabel 分隔符；或改用 QLabel 做点击
- **适用范围**：所有需要部分加粗/变色的按钮

### QLineEdit 不支持 HTML
- **现象**：QLineEdit 中 `<span style="color:...">` 原样显示
- **修复**：用 QLabel + `setTextFormat(Qt.TextFormat.RichText)` 替代
- **适用范围**：所有状态栏/消息显示

### QPainter drawRect 不支持 (QPointF, QPointF) 重载
- **现象**：`painter.drawRect(topLeft, bottomRight)` 类型错误
- **修复**：用 `QRectF(x, y, w, h)` 或 `(x, y, w, h)` 四参数形式
- **适用范围**：所有 QPainter 绘制

### CSS font-size: px ≠ QFont.setPointSize
- **现象**：QPainter QFont 和 CSS font-size 度量不一致
- **规则**：需与 drawer 对齐的文字用 QFont + setFont()，不用 CSS
- **适用范围**：所有 QPainter + CSS 混用的场景

## 4. 信号/事件安全

### 信号处理器内同步销毁 → SIGSEGV
- **现象**：`itemClicked` 信号处理器中 `popup.close()` → Segmentation fault
- **根因**：信号处理器内同步销毁子控件，Qt 事件循环崩溃
- **修复**：`hide() + deleteLater()` 延迟销毁
- **适用范围**：所有弹窗/对话框的信号处理

### eventFilter 双击丢失
- **现象**：快速连点第二下无反应
- **根因**：Qt 快速双击识别为 `MouseButtonDblClick`，不触发 `MouseButtonPress`
- **修复**：`event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick)`
- **适用范围**：所有 eventFilter 拦截点击

### QTimer 防堆积
- **现象**：快速操作导致多个 QTimer 堆积触发
- **修复**：用 `QTimer.singleShot` 或每次先 `stop()+deleteLater()` 再创建新的
- **适用范围**：所有需要延迟操作的 UI 交互

## 5. CSS/样式

### .format() 模板中大括号必须加倍
- **规则**：除 `{text_color}` 占位符外，所有 `{` `}` 必须写为 `{{` `}}`
- **范例**：`"QWidget {{ background: {bg}; }}"` ✅ | `"QWidget { background: {bg}; }"` ❌
- **适用范围**：所有 Python f-string/.format() 中的 Qt stylesheet

### 透明链必须层层显式设置
- **现象**：侧边栏毛玻璃效果不生效
- **根因**：透明效果需要链路中每一层（widget→scrollArea→viewport→list）都显式设 `background: transparent`
- **适用范围**：所有需要透明/毛玻璃效果的控件层级

### 浅色背景控件文字颜色
- **规则**：有自身背景的控件（按钮、输入框）→ 硬编码深色文字
- **规则**：透明背景控件 → 用 `self._text_color` 跟随主题
- **适用范围**：所有支持深色/浅色模式切换的面板

### border-bottom 对齐陷阱
- **现象**：有 border-bottom 的按钮比无 border 的按钮偏高（少 2px border 占位）
- **修复**：所有按钮统一给 `border-bottom: 2px solid transparent` 占位；或都不给
- **适用范围**：所有相邻按钮需要视觉对齐的场景

## 6. 构建/打包

### PyInstaller __file__ 虚拟路径
- **现象**：`os.path.dirname(__file__) + "/../data"` 在 PyInstaller 中无效
- **根因**：`__file__` 指向 PYZ 归档内的虚拟路径，中间目录不存在
- **修复**：用 `os.path.abspath()` 包裹；或使用 `config_manager.get_project_root()`
- **适用范围**：所有模块级数据路径

### 数据文件收集要递归展开
- **规则**：spec 用 `glob.glob("src/data/**", recursive=True)` 而非 `"src/data"`
- **过滤**：排除 `.DS_Store`/`__pycache__`/`.pyc`/`.7z`
- **适用范围**：所有 PyInstaller 打包

## 7. 通用逻辑

### 索引映射方向验证
- **教训**：改索引映射前先画表验证两端（0→初爻? 5→上爻?）
- **适用范围**：所有数组↔UI列表映射

### 初始化覆盖残留值
- **现象**：切换模式时旧值覆盖正确映射值
- **修复**：仅当来源非相关模式时才执行初始化
- **适用范围**：所有模式切换逻辑
