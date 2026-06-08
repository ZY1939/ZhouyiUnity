# ZhouyiUnity Development Guide

## Project Overview
周易桌面应用 — PySide6 (Qt 6.5+) 多 Tab GUI，跨平台 (macOS/Windows)。

## Tech Stack
- Python 3.12
- PySide6 6.11.1 (Qt for Python, LGPL)
- Qt Designer → `.ui` files in `ui/`
- PyInstaller → `dist/ZhouyiUnity.app` or `.exe`

## Directory Map
```
ZhouyiUnity/
├── main.py                 Entry point
├── ui/zhouyiUnity.ui       Qt Designer 主窗口布局（QTabWidget "mainTab"）
├── src/
│   ├── main_window.py      MainWindow — 加载.ui、注入Tab、外观初始化、状态栏、标签页记忆
│   ├── tabs/               Tab 页逻辑
│   │   ├── yijing_viewer.py    易经与起卦（注入 src/qigua/QiguaPanel）
│   │   ├── bazhai.py           八宅
│   │   └── case_manager.py     案例管理
│   ├── qigua/              起卦工具包（手工指定/三位数/金钱卦/蓍草卦）
│   │   ├── __init__.py        导出 QiguaPanel
│   │   ├── bagua.py           先天八卦常量 + GuaResult dataclass
│   │   ├── hexagram_loader.py  加载 content/*.jsonc，搜索卦
│   │   ├── hexagram_calc.py     核心计算（三位数→卦、六爻→卦）
│   │   ├── hexagram_painter.py  画卦预留接口（空壳）
│   │   ├── manual_input.py      手工指定 Widget
│   │   ├── number_input.py      三位数 Widget（含时间随机/秒表）
│   │   ├── countdown_timer.py   10秒倒计时弹窗
│   │   ├── stopwatch_timer.py   秒表弹窗
│   │   ├── lines_input.py       金钱卦/蓍草卦 6爻输入 Widget
│   │   ├── result_view.py       结果显示 Widget
│   │   └── divination_panel.py  主面板（方法选择+输入区+结果区）
│   ├── settings/           设置系统（macOS风格左侧240px侧边栏 + 右侧面板）
│   │   ├── __init__.py           导出 SettingsTab
│   │   ├── settings_tab.py       主设置页：CATEGORIES注册、侧边栏、QStackedWidget切换
│   │   │                         refresh_sidebar(font_size) / refresh_text_color(text_color)
│   │   ├── config_manager.py     ConfigManager单例 → usrCfg/UsrCfg.json (get/set自动落盘)
│   │   ├── appearance_manager.py apply_appearance()全局生效; _scale_and_cache_image()缩放缓存
│   │   └── panels/
│   │       ├── ai_panel.py          AI工具（LM Studio/DeepSeek/自定义）+ TestWorker + 停止按钮
│   │       ├── appearance_panel.py  外观（背景色/图片/模式/透明度/字体/字号/行距）+ 实时预览
│   │       ├── solar_time_panel.py  真太阳时和定位（IP自动定位/城市选择/手动编辑/网络检查）
│   │       └── city_picker_dialog.py 城市搜索弹窗（拼音检索，~2600城市）
│   ├── algorithms/          纯计算（无UI依赖）
│   │   ├── bazi.py              八字四柱 + 真太阳时校正（ephem节气）
│   │   └── xiaoliuren.py        倪师小六壬（农历月+日+时辰 → 掌诀 + 断辞）
│   ├── utils/
│   │   └── statusbar_manager.py  状态栏（时间/农历/四柱/小六壬 + 智能快慢刷新 + 状态消息）
│   ├── data/
│   │   ├── yijing/          易经64卦数据库 + 倪师卦图 + MgrScript/管理脚本
│   │   ├── stems_branches.py 干支/五行/生肖
│   │   └── ziwei_stars.py   紫微斗数星曜
│   ├── models/              Data structures
│   └── windows/             Independent popup windows
├── usrCfg/                  用户配置（运行时读写）
│   ├── UsrCfg.json          主配置文件（ai/appearance/solar_time/general）
│   └── _bg_cache.png        背景图缓存（缩放+透明度后）
└── build/                   PyInstaller 打包
```

## Key Conventions
- **中文注释**（所有函数必须有参数/返回/用法 docstring），英文标识符
- UI逻辑在 `src/`，UI布局在 `ui/` — 分离
- 静态参考数据 → `src/data/`，计算算法 → `src/algorithms/`
- **相对路径**：项目工程会移动，禁止硬编码绝对路径。计算项目根目录统一用 `config_manager.get_project_root()`（兼容 dev 和 PyInstaller frozen 模式），禁止各文件手写 `os.path.dirname(__file__) + "../.."`
- **模块级数据路径**：所有 `__file__` 相对路径必须用 `os.path.abspath()` 包裹，否则 PyInstaller 虚拟路径中 `..` 无法解析（`__file__` 指向 PYZ 归档内，中间目录不存在）
- **数据加载诊断**：所有从文件系统加载数据的位置（图标、数据库、.ui等），失败时必须打印诊断信息（解析后路径、`__file__`、`cwd`），格式 `[模块] ❌ 描述`
- **面板模式**：新增设置面板继承 QWidget → 在 settings_tab.py CATEGORIES 注册 → config_manager DEFAULT_CONFIG 加默认值
- **面板文字颜色**：PANEL_STYLE 使用 `.format(text_color=)` 模板，QWidget/QLabel/QGroupBox/QCheckBox 用 `{text_color}` 占位符；输入控件和按钮保持硬编码（有自背景）
- **非设置Tab文字颜色联动**：自定义Widget（如QiguaPanel）需实现 `refresh_text_color(text_color: str)` 方法，内部存 `self._text_color`，所有checkbox/label/combo的stylesheet用 f-string 嵌入 `{self._text_color}`。调用链：appearance_manager.apply_appearance() 计算 text_color → yijing_viewer.refresh_text_color() → qigua_panel.refresh_text_color()。新增Tab遵循同样模式
- **获取状态栏引用**：`getattr(self.window(), "_statusbar_mgr", None)`，禁止 import statusbar_manager（循环导入）
- **添加新Widget控件**：检查文件顶部 PySide6 imports，QComboBox/QSpinBox等容易遗漏
- **状态栏即时刷新**：任何改变状态栏显示内容的配置变更后，调用 `mgr._refresh()` 不要等timer tick
- **背景图片**：大图必须 `_scale_and_cache_image()` 预缩放到屏幕分辨率再设CSS，否则卡死
- **CSS模板**：`.format()` 模板中除 `{text_color}` 外所有 `{` `}` 必须加倍为 `{{` `}}`

## 状态栏
- 左侧"就绪"标签，右侧时间|农历|四柱|小六壬
- 智能快慢刷新：距时辰交界≤2分钟每秒刷，否则30秒
- 时辰判断："排八字中使用"勾选→真太阳时，否则→北京时间
- 外观跟随系统深色/浅色模式（Qt colorScheme API），不随设置面板背景

## 配置结构 (usrCfg/UsrCfg.json)
```json
{
  "ai": { "active_provider": "deepseek", "providers": { "lmstudio/deepseek/custom": { 各含独立timeout } } },
  "appearance": { "background_color/image/mode/opacity", "font_family/size", "line_spacing" },
  "solar_time": { "enabled", "auto_locate_on_startup", "manual_edit", "city_name", "longitude/latitude", "use_in_bazi", "show_in_statusbar" },
  "general": { "last_tab_index": 4 }
}
```

## Run
```bash
cd ~/Desktop/ZhouyiUnity && python3 main.py
```

## Build
```bash
bash build/build.sh          # Full build → dist/ZhouyiUnity.app
bash build/build.sh clean    # Clean
```

## Change Timeline

### 2026-06-08 (Build修复)
- **PyInstaller 数据文件收集**：spec 改用 `glob.glob("src/data/**", recursive=True)` 展开所有深度文件（图标、数据库、城市数据等）；过滤 `.DS_Store`/`__pycache__`/`.pyc`/`.7z`
- **get_project_root()**：config_manager.py 新增统一路径函数，`sys.frozen=True` 时用 `sys.executable` 倒推 .app 同级可写目录；dev 模式用 `__file__` 相对路径。所有 usrCfg 路径统一改用此函数
- **可写目录修复**：appearance_manager.py/_BG_CACHE、settings_tab.py/bg_cache+cache_path、appearance_panel.py/usrCfg_dir 全部改用 `get_project_root()`，确保打包后 usrCfg 可写
- **__file__ 虚拟路径修复**：所有模块级数据路径加 `os.path.abspath()` — PyInstaller 中 `__file__` 指向 PYZ 归档内的虚拟路径，中间目录不存在导致 `..` 解析失败（如 `src/settings/` 目录不存在 → `src/settings/../data/` 无效）
- **数据加载诊断**：_load_ui（.ui文件）、_svg_icon（SVG图标）、load_all_gua（JSONC数据库）、_load_cities（城市数据）加载失败时打印详细诊断信息
- **refresh_sidebar 安全访问**：`self._sidebar_list` 改为 `getattr(self, "_sidebar_list", None)` 防止容器未加载时崩溃
- **yijing_manager.py import 修复**：`format_by_template` 从 sync_structure 改为 sync_core

### 2026-06-08
- **起卦面板**：src/qigua/divination_panel.py — QiguaPanel 主面板，左侧 HexagramDrawer + 右侧 QStackedWidget 切换 4 种输入方式
- **HexagramDrawer 对齐**：bar 中心公式 `name_area_h + line_h//2 + row * line_h`，与右侧面板 checkbox/label 的 row center 完全一致，确保爻与控件行严格对齐
- **HexagramDrawer 参数**：`_apply_font(QFont, font_size)` 用 QFontMetrics 精确计算 line_h / bar_h / name_area_h / bar_w / yin_gap；`configure()` 可手动覆盖；`set_font_size()` 供全局字体变更调用；`offset_y` 微调整体垂直偏移
- **macOS 统一标题栏**：main_window.py `_setup_unified_tabs()` — 隐藏 QTabWidget 原生 tab bar，在 QToolBar 中创建独立 QTabBar 并双向同步；`setUnifiedTitleAndToolBarOnMac(True)` 让 toolbar 和红绿灯按钮同行；左右 QWidget spacer (Expanding) 实现 tab 居中
- **Tab 标签栏样式**：toolbar/QTabBar 背景 transparent，让 macOS 原生统一标题栏材质透过来；文字颜色跟随 Qt.ColorScheme（深色→白字，浅色→黑字）；tab 内边距 `font_size * 0.35`(v) `* 0.95`(h) 随字号动态缩放；toolbar 设 WA_TranslucentBackground 属性确保原生材质穿透
- **QiguaPanel 字体刷新链**：apply_appearance() → yijing_viewer.refresh_font_size() → qigua_panel.refresh_font_size() → drawer.set_font_size() → 所有面板 _update_panel_layout()
- **QiguaPanel 间距体系**：所有间距以 drawer.line_h 为基准 — gap_xs = lh*0.12, gap_sm = lh*0.25, gap_md = lh*0.45；root 底部 addStretch() 保证额外空间全部沉底
- **UI 布局清理**：ui/zhouyiUnity.ui verticalLayout 所有 margin=0；tab_qigua 旧控件清空；src/tabs/qigua.py 删除
- **金钱/蓍草面板合并**：删除 _make_coin_panel / _make_yarrow_panel，统一为 _make_lines_panel()，共用 _lines_cbs / _lines_inputs / _lines_rows；切换模式时 _update_lines_combo_options() 更新下拉选项 + cross_map 值映射（0↔6, 1↔7, 2↔8, 3↔9）
- **行高精确控制**：金钱/蓍草每行包裹在 setFixedHeight(line_h) 的 QWidget 容器中，combo padding 压缩为 2px 6px + border 1px，确保行高不受 combo 影响，与 drawer bar 严格对齐
- **文字颜色联动链**：apply_appearance() → yijing_viewer.refresh_text_color() → qigua_panel.refresh_text_color()；QiguaPanel 存 self._text_color，所有 checkbox/label/combo/result 的 stylesheet 用 f-string 嵌入 {self._text_color}；新增Tab须遵循同样模式
- **方法标签可点击**：header 中"手工/报数/金钱/蓍草"标签改为 flat QPushButton，hover 变色，clicked → dot.click() 切换方法
- **默认值优化**：金钱/蓍草 combo 默认选中"少阳"（index 2），combo 用 AdjustToContents 自适应宽度
- **CLAUDE.md**：新增"非设置Tab文字颜色联动"规范 + Change Timeline 记录

### 2026-06-07
- **状态栏**：新增左侧"就绪"标签 + show_status/reset_status 状态消息机制；合并时间显示为 `时间(真) 14:30 (14:12)` 精简格式；删除"农历""小六壬"冗余标签；四柱显示 `(真)/(平)`
- **AI面板**：添加"停止"按钮强制终止 TestWorker；扫描/测试时状态栏显示状态文字
- **小六壬**：src/algorithms/xiaoliuren.py — 倪师掌诀推算（农历月+日+时辰），含六位断辞
- **面板文字颜色**：PANEL_STYLE 改为 .format() 模板，appearance_manager 调用 refresh_text_color() 联动背景色
- **背景图片**：拉伸模式（fill/fit/center/tile）+ 透明度（10%-100%）；预缩放缓存防卡死
- **Tab记忆**：切换标签页保存到 general.last_tab_index，启动恢复，默认"设置"
- **配置文件名**：aiCfg.json → UsrCfg.json；新增 general 分类
- **真太阳时面板**：经纬度同行对齐；手动编辑复选框；启动自动定位（无网络→杭州降级）；定位/网络检查显示状态栏文字
- **状态栏即时刷新**：solar_time_panel._save_config() 末尾调 mgr._refresh()；快慢刷新按 use_in_bazi 判断
- **刷新速率**：按"排八字中使用"勾选决定用真太阳时还是北京时间判断时辰交界
- **LM Studio 扫描优化**：模型按大小（_model_rank）降序排列；扫描时状态栏显示"正在扫描 LM Studio..."
- **每个AI提供商独立配置超时**：lmstudio(120s)/deepseek(30s)/custom(60s)，步进10秒，建议提示
- **自定义AI提供商**：兼容 OpenAI API 格式的任意服务
- **状态栏系统主题**：Qt 6.5+ colorScheme() 检测深色/浅色模式，不随设置面板背景联动
- **网络检查**：trust_env=False 绕过VPN；3秒超时；无网络→杭州降级
- **CLAUDE.md / 项目记忆**：同步更新

### Earlier
- 城市选择器 city_picker_dialog.py（拼音搜索，~2600城市，GCJ-02→WGS-84）
- 外观面板（背景色/图片/字体/字号/行距/预览）
- AI面板（LM Studio/DeepSeek 配置 + 连接测试）
- ConfigManager 单例配置系统
- 设置 Tab macOS 风格侧边栏布局 + SVG 图标系统
