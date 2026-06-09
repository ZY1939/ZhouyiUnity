"""
通用组件 — 被 qigua + suangua 共享引用

UI 组件：
    HexagramDrawer — 卦图绘制 QWidget（QPainter 六爻线）
    DotButton      — 圆点选择按钮（选中实心/未选中空心）
    _app_font      — 应用全局字体获取函数

核心计算/数据：
    GuaResult      — 起卦结果 dataclass
    XIANTIAN       — 先天八卦常量
    calc_three_numbers / calc_from_yang_lines / calc_six_lines — 核心计算
    load_all_gua / get_gua_by_xiantian / search_gua — 64卦查询
"""
from .hexagram_drawer import HexagramDrawer, _app_font
from .dot_button import DotButton
