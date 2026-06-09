# yijingTab 级测试

> 从项目根目录运行：`cd ~/Desktop/ZhouyiUnity`

## 设计意图

这些测试不是随手写的——每个都对应一个曾经踩过、花大量时间才修好的坑。跑通这些测试 = 保证这些坑不会复现。

## 测试文件

| 文件 | 保护的设计要求 | 回归覆盖（之前坏过什么） | 运行 |
|------|-------------|---------------------|------|
| `test_alignment.py` | 手动面板 Lock 与 单动爻 两列水平对齐 | sizeHint 陷阱 → QGridLayout → row wrappers 9轮迭代才修好。详见 [PITFALLS §1-sizeHint](../../../docs/ai/PITFALLS.md) | `python3 src/yijingTab/_debug/test_alignment.py` |
| `test_button_alignment.py` | 工具栏按钮 保存↔随机、读取↔秒表 x 坐标对齐 | widget.width() 陷阱 — 测试过但真实 app 按钮消失。详见 [PITFALLS §2-width](../../../docs/ai/PITFALLS.md) | `python3 src/yijingTab/_debug/test_button_alignment.py` |
| `test_grid_row_height.py` | QGridLayout 行高 = setFixedHeight(line_h)，多字号验证 | QGridLayout 用 sizeHint(19px) 忽略 setFixedHeight(28px)，行缩到 24px | `python3 src/yijingTab/_debug/test_grid_row_height.py` |
| `test_gua_picker.py` | 64卦弹窗：弹出+选择+SIGSEGV 不崩溃+连续快速选择+外部关闭 | SIGSEGV — 信号处理器内同步 close() 崩溃。详见 [PITFALLS §4-SIGSEGV](../../../docs/ai/PITFALLS.md) | `python3 src/yijingTab/_debug/test_gua_picker.py` |
| `test_manual_panel.py` | 手工面板：单动爻勾选/取消/连锁反应/Lock/卦图点击不联动爻/梅花切换 | 卦图点击误联动爻标记、单动爻边界条件 6 条、多动爻自动取消单动爻 | `python3 src/yijingTab/_debug/test_manual_panel.py` |

## 何时运行

- **改动了 divination_panel.py 任何布局代码** → 全部 5 个
- **改动了 header 方法标签** → 加跑 `qigua/_debug/test_method_labels.py`
- **改动了 ButtonBar 按钮** → `test_button_alignment.py`
- **改动了弹窗** → `test_gua_picker.py`
- **改动了 HexagramDrawer 对齐** → `test_alignment.py` + `test_grid_row_height.py`

## 添加新测试

新增测试脚本后必须同步更新本文件的上表。格式：保护什么设计 + 防止什么回归 + 运行命令。
