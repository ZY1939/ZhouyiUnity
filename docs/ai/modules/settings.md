# 设置系统

> 最后更新：2026-06-08

---

## 架构

```
src/settings/
├── __init__.py             导出 SettingsTab
├── settings_tab.py         主设置页：侧边栏 + QStackedWidget
│                           CATEGORIES 注册表、refresh_sidebar(font_size)
│                           refresh_text_color(text_color)
├── config_manager.py       ConfigManager 单例 → usrCfg/UsrCfg.json
│                           get_project_root() 统一路径入口
├── appearance_manager.py   apply_appearance() 全局外观应用
│                           _scale_and_cache_image() 背景图预缩放
└── panels/
    ├── ai_panel.py            AI 工具（LM Studio/DeepSeek/自定义）
    ├── appearance_panel.py    外观设置（背景/字体/字号/行距）
    ├── solar_time_panel.py    真太阳时和定位
    └── city_picker_dialog.py  城市搜索弹窗（拼音检索，~2600城市）
```

---

## 配置结构 (usrCfg/UsrCfg.json)

```json
{
  "ai": {
    "active_provider": "deepseek",
    "providers": {
      "lmstudio":  { "timeout": 120 },
      "deepseek":  { "timeout": 30 },
      "custom":    { "timeout": 60 }
    }
  },
  "appearance": {
    "background_color/image/mode/opacity": "...",
    "font_family": "...",
    "font_size": 16,
    "line_spacing": 1.5
  },
  "solar_time": {
    "enabled": true,
    "city_name": "杭州",
    "longitude/latitude": "...",
    "use_in_bazi": true,
    "show_in_statusbar": true
  },
  "general": {
    "last_tab_index": 4,
    "suangua_method": "meihua"
  }
}
```

---

## 新增设置面板流程

1. 继承 QWidget 创建面板类
2. 在 `settings_tab.py` CATEGORIES 字典注册（key + display_name + icon）
3. 在 `config_manager.py` DEFAULT_CONFIG 添加默认值
4. 面板样式用 `PANEL_STYLE.format(text_color=)` 模板
5. 实现 `refresh_text_color(tc)` 方法

---

## 外观应用流程

```
appearance_panel 保存 → apply_appearance()
  1. 读取配置
  2. 计算 text_color（背景亮度 → 深色/浅色文字）
  3. setFont() → QApplication
  4. _scale_and_cache_image() → 背景图预缩放
  5. setStyleSheet() → 全局背景
  6. 遍历所有 Tab 调用 refresh_font_size(fs)
  7. 遍历所有 Tab 调用 refresh_text_color(tc)
```

**注意**：首次 resize 立即渲染，后续防抖。禁止 `window.show()` 前调用。

---

## 侧边栏
- macOS 风格 240px 左侧栏
- SVG 图标系统（蓝底白字圆角矩形）
- 透明毛玻璃效果（层层显式设 transparent）
- `refresh_sidebar(font_size)` 动态缩放
- 安全访问：`getattr(self, "_sidebar_list", None)`

---

## 相关文档
- [编码规范](../CONVENTIONS.md) — 外观系统规范
- [踩坑库](../PITFALLS.md) — CSS/样式相关踩坑
