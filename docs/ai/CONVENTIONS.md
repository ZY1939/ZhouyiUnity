# 编码规范

> 项目级强制约定。违反将导致 UI 错位/崩溃/打包失败。

---

## 代码风格
- **中文注释**（所有函数必须有参数/返回/用法 docstring），英文标识符
- UI 逻辑在 `src/`，UI 布局在 `ui/` — 分离
- 静态数据 → `src/data/`，计算算法 → `src/algorithms/`
- 调试脚本放模块 `_debug/` 子目录，与正式代码分离

## 路径处理
- **统一入口**：`config_manager.get_project_root()` — 兼容 dev 和 PyInstaller frozen
- **禁止**：`os.path.dirname(__file__) + "../.."` 手写相对路径
- **模块级路径**：必须 `os.path.abspath()` 包裹（PyInstaller PYZ 虚拟路径兼容）
- **数据加载失败**：打印诊断（解析路径、`__file__`、`cwd`），格式 `[模块] ❌ 描述`

## 外观系统
- **面板文字颜色**：样式用 `.format(text_color=)` 模板；透明控件用 `{text_color}` 占位符；按钮/输入框硬编码
- **字体刷新链**：`apply_appearance()` → Tab.refresh_font_size() → Panel.refresh_font_size() → Widget.set_font_size()
- **文字颜色刷新链**：同上模式，方法名 `refresh_text_color(tc)`，存 `self._text_color`
- **新增 Tab/面板**：必须实现 `refresh_font_size(fs)` 和 `refresh_text_color(tc)`
- **背景图片**：大图必须 `_scale_and_cache_image()` 预缩放到屏幕分辨率再设 CSS
- **字号范围**：全局 12-24px
- **启动外观**：首次 resize 立即渲染，后续 resize 防抖，禁止 `window.show()` 前调 `apply_appearance()`

## 控件使用
- **新增 Widget**：检查文件顶部 PySide6 imports（QComboBox/QSpinBox 容易遗漏）
- **DotButton 旁标签**：用 flat QPushButton（非 QLabel），点击文字=点击圆点
- **状态栏引用**：`getattr(self.window(), "_statusbar_mgr", None)`，禁止 import（循环导入）
- **状态栏即时刷新**：配置变更后调 `mgr._refresh()`，不等 timer

## 设置面板
- **新增面板**：继承 QWidget → 在 `settings_tab.py` CATEGORIES 注册 → `config_manager` DEFAULT_CONFIG 加默认值

## 参数管理
- **可调参数**：集中在模块的 `CONST_DEFINE_UI.py` 中，其他文件只读不写
- **间距体系**：以 `drawer.line_h` 为基准 `gap = max(N, int(line_h * ratio))`
- **多列布局**：每列用 `setFixedWidth` 包裹，`addStretch` 只放主行末尾

## 多模块对齐
- **并排面板 header 高度**：必须来自同一数据源（如 `drawer.line_h`），不能各自独立计算
- **所有对齐计算**：用 `minimumWidth()` 不用 `width()`
- **badge 渲染**：必须正方形（`side = max(height, width)`），不用长方形
