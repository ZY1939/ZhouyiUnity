# yijingTab 级测试

从项目根目录运行：`cd ~/Desktop/ZhouyiUnity`

## 测试文件一览

| 文件 | 测试内容 | 运行命令 |
|------|---------|---------|
| `test_alignment.py` | QGridLayout 列对齐验证（动爻设置/Lock/单动爻），记录 QHBoxLayout→QGridLayout 的演进过程 | `python3 src/yijingTab/_debug/test_alignment.py` |
| `test_button_alignment.py` | 报数面板按钮对齐：保存↔随机同x、读取↔秒表同x、按钮顺序 | `python3 src/yijingTab/_debug/test_button_alignment.py` |
| `test_grid_row_height.py` | 验证 QGridLayout Row 0 的 setFixedHeight(name_h) 是否被 layout 遵守（多字号 15-18） | `python3 src/yijingTab/_debug/test_grid_row_height.py` |
| `test_gua_picker.py` | 64卦弹窗：弹出+选择+SIGSEGV回归+连续快速选择3次+点击外部关闭 | `python3 src/yijingTab/_debug/test_gua_picker.py` |
| `test_manual_panel.py` | 手工面板交互回归：单动爻/Lock/卦图点击/动爻复选框/suangua转发/梅花切换 | `python3 src/yijingTab/_debug/test_manual_panel.py` |

## 何时运行

- **改动了 divination_panel.py 布局代码** → `test_alignment.py` + `test_button_alignment.py` + `test_grid_row_height.py` + `test_manual_panel.py`
- **改动了弹窗相关代码** → `test_gua_picker.py`
- **改动了手工面板/动爻/锁定逻辑** → `test_manual_panel.py`
