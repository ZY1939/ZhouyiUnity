# 算卦面板 (suangua) 测试

从项目根目录运行：`cd ~/Desktop/ZhouyiUnity`

## 测试文件一览

| 文件 | 测试内容 | 运行命令 |
|------|---------|---------|
| `test_common.py` | common.py 综合测试：_LineMarker badge 渲染/干支历法计算/卦辞解读/_TimePickerDialog | `python3 src/yijingTab/suangua/_debug/test_common.py` |
| `test_liuyao.py` | 六爻面板集成调试：布局/对齐/数据显示/变卦功能，支持 ZY_DEBUG=1 输出坐标 | `python3 src/yijingTab/suangua/_debug/test_liuyao.py` |
| `test_liuyao_align.py` | 六爻布局对齐：4个测试用例（天风姤/乾为天/风地观/火山旅），精简按钮/六神/世应/纳音/伏神坐标分析 | `python3 src/yijingTab/suangua/_debug/test_liuyao_align.py` |
| `test_header_alignment.py` | QiguaPanel vs SuanguaPanel header 垂直对齐测量：title Y坐标/frame Y坐标/top_spacer 各字号值 | `python3 src/yijingTab/suangua/_debug/test_header_alignment.py` |
| `test_compact_btn_align.py` | 六爻精简按钮水平对齐：左边缘↔六兽badge左边缘、右边缘↔世应badge右边缘（多字号14/16/20） | `python3 src/yijingTab/suangua/_debug/test_compact_btn_align.py` |
| `test_gaps.py` | 六爻列间水平间距像素级诊断：六神/世应/卦图/动爻/纳音列的全局x坐标和间距 | `python3 src/yijingTab/suangua/_debug/test_gaps.py` |
| `test_layout_debug.py` | 六爻整体布局诊断：打印所有列宽度/间距/总宽度（用地天泰测试长标题） | `python3 src/yijingTab/suangua/_debug/test_layout_debug.py` |

## 辅助文档

| 文件 | 内容 |
|------|------|
| `column_layout_pattern.md` | 多列布局固定列宽容器模式 — QStackedWidget 拉伸破坏列间距的避坑指南 |

## 何时运行

- **改动了六爻面板 (liuyao_panel.py)** → `test_liuyao.py` + `test_liuyao_align.py` + `test_gaps.py` + `test_layout_debug.py` + `test_compact_btn_align.py`
- **改动了梅花面板 (meihua_panel.py) / LineMarker** → `test_common.py`
- **改动了 header 对齐/top_spacer** → `test_header_alignment.py`
- **改动了 common.py（干支历法/时间选择器）** → `test_common.py`
