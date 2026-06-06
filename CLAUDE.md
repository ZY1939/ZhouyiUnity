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
│   │   ├── yijing_viewer.py    易经查看器
│   │   ├── qigua.py            起卦
│   │   ├── bazhai.py           八宅
│   │   └── case_manager.py     案例管理
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
- **相对路径**：项目工程会移动，禁止硬编码绝对路径
- **面板模式**：新增设置面板继承 QWidget → 在 settings_tab.py CATEGORIES 注册 → config_manager DEFAULT_CONFIG 加默认值
- **面板文字颜色**：PANEL_STYLE 使用 `.format(text_color=)` 模板，QWidget/QLabel/QGroupBox/QCheckBox 用 `{text_color}` 占位符；输入控件和按钮保持硬编码（有自背景）
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
