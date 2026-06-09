# 变更历史

> 关键架构变更摘要。详细代码级变更见 git log。

---

## 2026-06-10 — ButtonBar 工具栏 + 公共组件提取
- ButtonBar: 截图|AI|保存|读取 4按钮，手动 move() 定位
- CONST_DEFINE_UI 统一管理 `gap_btn_pad`/`gap_btn_h`
- MethodLabelBar 公共组件：起卦/算卦共享方法标签栏，解决样式不一致
- 修复 `widget.width()` 陷阱：resize 事件中用 `minimumWidth()` 替代 `width()`

## 2026-06-09 — 六爻变卦 + 对齐修复
- 六爻变卦功能：本卦→变卦 生克箭头 + 变卦六亲(按本卦宫五行)
- SuanguaPanel header 与 QiguaPanel header 垂直对齐修复
- QGridLayout 替代方案：QWidget row wrappers 精确控制行高
- HexagramDrawer.get_line_positions() 对齐调试接口
- 月份计算 bug 修复（6月→午月）
- eventFilter 双击支持

## 2026-06-08 — 算卦面板 + 起卦面板重构
- SuanguaPanel 算卦面板：梅花易数/六爻断卦，与起卦面板并排
- QiguaPanel 起卦面板重构：4种输入方式 + HexagramDrawer 精确对齐
- macOS 统一标题栏：隐藏 QTabBar，QToolBar 居中 tab
- 间距体系：以 line_h 为动态基准
- DotButton 提取为共享组件
- 字体/颜色刷新链建立
- Build 修复：PyInstaller 数据收集、__file__ 虚拟路径、get_project_root()

## 2026-06-07 — 状态栏 + 外观系统
- 状态栏：智能快慢刷新、状态消息、系统主题跟随
- 外观面板：背景色/图片/字体/字号/行距 + 实时预览
- AI 面板：LM Studio/DeepSeek/自定义 + 独立超时
- 真太阳时面板：IP定位/城市选择/手动编辑
- 小六壬算法
- ConfigManager 单例配置系统
- Tab 标签页记忆

## Earlier
- 城市选择器 city_picker_dialog.py（拼音搜索，~2600城市）
- 设置 Tab macOS 风格侧边栏布局 + SVG 图标系统
