# 起卦面板 (qigua) 测试

> 从项目根目录运行：`cd ~/Desktop/ZhouyiUnity`

## 设计意图

起卦面板 header 的标签系统经过多次重构（独立标签 → MethodLabelBar 公共组件），测试覆盖标签交互 + 子模式切换 + 算卦联动，确保重构不破坏功能。

## 测试文件

| 文件 | 保护的设计要求 | 回归覆盖（之前坏过什么） | 运行 |
|------|-------------|---------------------|------|
| `test_method_labels.py` (31项) | header 标签：METHODS 结构/点击路由/lines 子模式切换/suangua 自动跳转/dim_color/样式断言 | QPushButton 无 RichText → 拆双按钮、border-bottom 三版迭代对齐、lines 未激活时 padding 破坏基线。详见 [PITFALLS §3-RichText](../../../../docs/ai/PITFALLS.md) 和 [§5-border-bottom](../../../../docs/ai/PITFALLS.md) | `python3 src/yijingTab/qigua/_debug/test_method_labels.py` |
| `test_method_label_bar.py` (51项) | MethodLabelBar 公共组件 + suangua 集成 + 起卦回归 | QHBoxLayout AlignVCenter 导致标签 y 不一致、suangua 六爻选中不加粗、间距消失。详见 [PITFALLS §1-AlignVCenter](../../../../docs/ai/PITFALLS.md) | `python3 src/yijingTab/qigua/_debug/test_method_label_bar.py` |

## 何时运行

- **改动了 header 方法标签（手工/报数/金钱蓍草）** → `test_method_labels.py`
- **改动了 MethodLabelBar 公共组件** → `test_method_label_bar.py`
- **改动了 suangua header（梅花/六爻切换）** → `test_method_label_bar.py`
- **改动了 lines 子模式（金钱↔蓍草）** → `test_method_labels.py`

## 设计文档

详见 [易经Tab架构 §Header 方法标签设计](../../../../docs/ai/modules/yijingTab.md) 和 [MethodLabelBar API](../../../../docs/ai/modules/yijingTab.md)。

## 添加新测试

新增测试脚本后必须同步更新本文件的上表。
