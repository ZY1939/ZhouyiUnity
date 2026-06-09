# 算卦面板 (suangua) 测试

> 从项目根目录运行：`cd ~/Desktop/ZhouyiUnity`

## 设计意图

算卦面板涉及梅花（三卦+标注）/六爻（5列+变卦）/时间管理三大子系统。每个测试精确锁定一个曾出过问题的对齐/间距/渲染点。

## 测试文件

| 文件 | 保护的设计要求 | 回归覆盖（之前坏过什么） | 运行 |
|------|-------------|---------------------|------|
| `test_common.py` | _LineMarker badge 渲染/干支历法计算/卦辞解读/_TimePickerDialog | × 符号 float→int 截断偏左上、月份计算 (month+1)%12 差一位。详见 [PITFALLS §3-drawRect](../../../../docs/ai/PITFALLS.md) 和 [§7-月份](../../../../docs/ai/PITFALLS.md) | `python3 src/yijingTab/suangua/_debug/test_common.py` |
| `test_liuyao.py` | 六爻面板集成：布局/对齐/数据显示/变卦功能 | ZY_DEBUG=1 输出坐标用于对齐诊断 | `python3 src/yijingTab/suangua/_debug/test_liuyao.py` |
| `test_liuyao_align.py` | 六爻 4 卦例布局对齐：六神/世应/纳音/伏神坐标分析 | 标注统一公式 `center_y = offset_y + name_h + (5-line)*lh + lh//2` | `python3 src/yijingTab/suangua/_debug/test_liuyao_align.py` |
| `test_header_alignment.py` | QiguaPanel vs SuanguaPanel header 垂直对齐：title Y/frame Y/top_spacer 各字号 | 两个面板 title 独立算高度导致视觉不对齐。详见 [PITFALLS §7-header](../../../../docs/ai/PITFALLS.md) | `python3 src/yijingTab/suangua/_debug/test_header_alignment.py` |
| `test_compact_btn_align.py` | 六爻精简按钮左边缘↔六兽 badge 左边缘、右边缘↔世应 badge 右边缘（多字号） | 多列布局 QStackedWidget 拉伸破坏列间距 → setFixedWidth 包裹每列 | `python3 src/yijingTab/suangua/_debug/test_compact_btn_align.py` |
| `test_gaps.py` | 六爻列间水平间距像素诊断：5列全局 x 坐标和间距 | 间距不一致导致标注与 drawer 爻线错位 | `python3 src/yijingTab/suangua/_debug/test_gaps.py` |
| `test_layout_debug.py` | 六爻整体布局诊断：列宽度/间距/总宽度（用地天泰测试长标题） | 长标题超出列宽导致截断 | `python3 src/yijingTab/suangua/_debug/test_layout_debug.py` |

## 辅助文档

| 文件 | 内容 |
|------|------|
| `column_layout_pattern.md` | 多列布局固定列宽容器 — addStretch 只放主行末尾的避坑模式 |

## 何时运行

- **改动了六爻面板 (liuyao_panel.py)** → 全部 5 个六爻测试
- **改动了梅花面板 (meihua_panel.py) / LineMarker** → `test_common.py`
- **改动了 header 对齐/top_spacer** → `test_header_alignment.py`
- **改动了 common.py** → `test_common.py`

## 添加新测试

新增测试脚本后必须同步更新本文件的上表。
