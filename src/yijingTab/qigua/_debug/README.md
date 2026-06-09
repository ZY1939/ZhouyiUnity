# 起卦面板 (qigua) 测试

从项目根目录运行：`cd ~/Desktop/ZhouyiUnity`

## 测试文件一览

| 文件 | 测试内容 | 运行命令 |
|------|---------|---------|
| `test_method_labels.py` | header 方法标签：METHODS结构/点击路由/lines子模式切换/suangua自动跳转/dim_color/样式断言（31项） | `python3 src/yijingTab/qigua/_debug/test_method_labels.py` |
| `test_method_label_bar.py` | MethodLabelBar 公共组件 + suangua集成 + 起卦回归（51项） | `python3 src/yijingTab/qigua/_debug/test_method_label_bar.py` |

## 何时运行

- **改动了 header 方法标签（手工/报数/金钱蓍草）** → `test_method_labels.py`
- **改动了 MethodLabelBar 公共组件** → `test_method_label_bar.py`
- **改动了 suangua header（梅花/六爻切换）** → `test_method_label_bar.py`
- **改动了 lines 子模式（金钱↔蓍草）** → `test_method_labels.py`

## 设计文档

相关设计说明见 [ARCHITECTURE.md](../ARCHITECTURE.md)：
- "Header 方法标签设计" — 布局结构、点击路由、样式规则、下划线对齐踩坑
- "MethodLabelBar（公共组件）" — API、信号、迁移背景、QHBoxLayout 不使用 AlignVCenter
