# ZhouyiUnity Development Guide

## Project Overview
周易桌面应用 — PySide6 (Qt 6.5+) 多 Tab GUI，跨平台 (macOS/Windows)。

## AI Navigation（按需读取）

| 场景 | 读取文件 |
|------|----------|
| **开始写代码前** | [编码规范](docs/ai/CONVENTIONS.md) + [行为规则](docs/ai/README.md) — 先读这两个 |
| **遇到 UI 布局/对齐 bug** | [踩坑库](docs/ai/PITFALLS.md) — **先读顶部索引（~30行），匹配症状再跳章节** |
| **修改 yijingTab 相关** | [易经Tab架构](docs/ai/modules/yijingTab.md) |
| **修改设置/外观** | [设置系统](docs/ai/modules/settings.md) |
| **修改状态栏** | [状态栏](docs/ai/modules/statusbar.md) |
| **了解历史变更** | [变更历史](docs/ai/CHANGELOG.md) |
| **PySide6 API 不确定** | [踩坑库 §3](docs/ai/PITFALLS.md) — PySide6 API 陷阱 |
| **对齐/间距计算** | [踩坑库 §1-2](docs/ai/PITFALLS.md) — 布局引擎 + Widget 尺寸 |
| **修改 八宅/案例管理** | 暂无模块文档，直接读 `src/tabs/bazhai.py` / `src/tabs/case_manager.py`，遵循 [编码规范](docs/ai/CONVENTIONS.md) |
| **修改 八字/小六壬 算法** | 直接读 `src/algorithms/` 对应文件 |
| **新增 Tab/模块** | [新增 Tab 开发 Checklist](docs/ai/CONVENTIONS.md#新增-tab-开发-checklist) |
| **完成代码后维护文档** | [维护说明](docs/ai/README.md) — checklist 判断哪些 doc 需要同步更新 |

## Tech Stack
- Python 3.12 + PySide6 6.11.1 (Qt for Python, LGPL)
- Qt Designer → `.ui` files in `ui/`
- PyInstaller → `dist/ZhouyiUnity.app` or `.exe`

## Directory Map
```
ZhouyiUnity/
├── main.py                 Entry point
├── ui/zhouyiUnity.ui       Qt Designer 主窗口（QTabWidget "mainTab"）
├── src/
│   ├── main_window.py      MainWindow — 加载.ui、注入Tab、外观初始化、状态栏、标签页记忆
│   ├── tabs/               Tab 页逻辑
│   │   ├── yijing_viewer.py    易经与起卦（注入 QiguaPanel + SuanguaPanel）
│   │   ├── bazhai.py           八宅
│   │   └── case_manager.py     案例管理
│   ├── yijingTab/          易经Tab 完整模块
│   │   ├── CONST_DEFINE_UI.py     QiguaConfig/SuanguaConfig/MeihuaConfig 参数集中管理
│   │   ├── com/                   通用组件（HexagramDrawer/DotButton/MethodLabelBar/八卦/计算/加载）
│   │   ├── qigua/                 起卦面板（divination_panel/倒计时/秒表/案例CRUD）
│   │   ├── suangua/               算卦面板（梅花易数/六爻/时间设置）
│   │   ├── button/                ButtonBar 工具栏按钮
│   │   └── _debug/                测试脚本
│   ├── settings/           设置系统（macOS侧边栏 + QStackedWidget）
│   │   ├── config_manager.py     ConfigManager单例 + get_project_root()
│   │   ├── appearance_manager.py apply_appearance() + 背景图预缩放
│   │   └── panels/               AI/外观/真太阳时/城市选择
│   ├── algorithms/          纯计算（八字/小六壬）
│   ├── utils/              工具（statusbar_manager.py）
│   ├── data/                静态数据（易经数据库/干支/紫微）
│   └── models/ / windows/  Data structures / 独立弹窗
├── usrCfg/                  用户配置（运行时读写）
│   ├── UsrCfg.json          ai/appearance/solar_time/general
│   └── _bg_cache.png        背景图缓存
└── build/                   PyInstaller 打包
```

## Key Conventions
- **中文注释**（函数必须有参数/返回/用法 docstring），英文标识符
- UI逻辑在 `src/`，UI布局在 `ui/` — 分离
- 静态数据 → `src/data/`，算法 → `src/algorithms/`
- **路径**：统一用 `config_manager.get_project_root()`，禁止手写相对路径；模块级路径加 `os.path.abspath()`
- **数据加载失败**：打印诊断（路径、`__file__`、`cwd`），格式 `[模块] ❌ 描述`
- **样式模板**：`.format(text_color=)` 模板，`{text_color}` 占位符透明控件，按钮/输入框硬编码；其他 `{` `}` 加倍为 `{{` `}}`
- **外观刷新**：新增 Tab/Panel 必须实现 `refresh_font_size(fs)` + `refresh_text_color(tc)`
- **状态栏引用**：`getattr(self.window(), "_statusbar_mgr", None)`，禁 import
- **间距**：以 `drawer.line_h` 为动态基准 `max(N, int(line_h * ratio))`
- **对齐**：所有对齐计算用 `minimumWidth()` 不用 `width()`
- **设置面板**：继承 QWidget → CATEGORIES 注册 → DEFAULT_CONFIG 加默认值
- **调试脚本**：放模块 `_debug/` 子目录
- 详细规范见 [编码规范](docs/ai/CONVENTIONS.md)，踩坑先查 [踩坑库](docs/ai/PITFALLS.md)

## 配置结构 (usrCfg/UsrCfg.json)
```json
{
  "ai": { "active_provider": "deepseek", "providers": { "lmstudio/deepseek/custom": { 独立timeout } } },
  "appearance": { "background_color/image/mode/opacity", "font_family/size", "line_spacing" },
  "solar_time": { "enabled", "city_name", "longitude/latitude", "use_in_bazi", "show_in_statusbar" },
  "general": { "last_tab_index": 4, "suangua_method": "meihua" }
}
```

## Run
```bash
python3 main.py
```

## Build
```bash
bash build/build.sh          # Full build → dist/ZhouyiUnity.app
bash build/build.sh clean    # Clean
```
