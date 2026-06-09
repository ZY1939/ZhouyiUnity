"""
八卦五行颜色定义 — 根据八卦名称、阴阳属性和当前文字颜色返回对应的五行颜色

八卦五行归属：
    乾(☰)=阳金  兑(☱)=阴金  离(☲)=阴火  震(☳)=阳木
    巽(☴)=阴木  坎(☵)=阳水  艮(☶)=阳土  坤(☷)=阴土

颜色规则：
    金: 阳金=紫铜色(亮铜), 阴金=暗铜色(氧化紫铜)
    木: 阳木=鲜绿色, 阴木=暗绿色
    水: 阳水=蓝色
    火: 阴火=暗红色（唯一火卦为离=阴火）
    土: 阳土=黄褐色, 阴土=暗黄色

体用标记：
    体=红色(#e74c3c), 用=蓝色(#3498db)
"""

# ── 八卦 → (五行, 阴阳) 映射 ──
_TRIGRAM_WUXING: dict[str, tuple[str, str]] = {
    "乾": ("金", "阳"),
    "兑": ("金", "阴"),
    "离": ("火", "阴"),
    "震": ("木", "阳"),
    "巽": ("木", "阴"),
    "坎": ("水", "阳"),
    "艮": ("土", "阳"),
    "坤": ("土", "阴"),
}

# ── 八卦先天数 → (五行, 阴阳) ──
_XIANTIAN_WUXING: dict[int, tuple[str, str]] = {
    1: ("金", "阳"),  # 乾
    2: ("金", "阴"),  # 兑
    3: ("火", "阴"),  # 离
    4: ("木", "阳"),  # 震
    5: ("木", "阴"),  # 巽
    6: ("水", "阳"),  # 坎
    7: ("土", "阳"),  # 艮
    8: ("土", "阴"),  # 坤
}

# ── 体用符号颜色 ──
TI_COLOR = "#e74c3c"   # 体 = 红色
YONG_COLOR = "#3498db"  # 用 = 蓝色

# ── 动爻符号颜色 ──
O_COLOR = "#e74c3c"     # o(老阳) = 红色
X_COLOR = "#3498db"     # x(老阴) = 蓝色


def get_wuxing_color(gua_name: str, text_color: str = "#1d1d1f") -> str:
    """
    根据八卦名返回对应的五行颜色

    Args:
        gua_name: 八卦名称，如 "乾"、"兑"、"离" 等
        text_color: 当前文字颜色(hex)，金卦用此颜色作为基础

    Returns:
        CSS hex 颜色字符串
    """
    wx = _TRIGRAM_WUXING.get(gua_name)
    if not wx:
        return text_color

    element, yin_yang = wx

    if element == "金":
        return "#C47A55" if yin_yang == "阳" else "#8B634B"  # 模拟紫铜：阳=亮铜色，阴=氧化暗铜色

    elif element == "木":
        return "#27ae60" if yin_yang == "阳" else "#1a7a40"

    elif element == "水":
        return "#3498db"  # 蓝色

    elif element == "火":
        return "#e74c3c" if yin_yang == "阳" else "#c0392b"  # 大红 / 暗红

    elif element == "土":
        return "#d4a017" if yin_yang == "阳" else "#a08020"

    return text_color


def get_wuxing_color_by_xiantian(xiantian_num: int, text_color: str = "#1d1d1f") -> str:
    """
    根据先天八卦数返回对应的五行颜色

    Args:
        xiantian_num: 先天数 (1-8)
        text_color: 当前文字颜色(hex)

    Returns:
        CSS hex 颜色字符串
    """
    wx = _XIANTIAN_WUXING.get(xiantian_num)
    if not wx:
        return text_color

    element, yin_yang = wx

    if element == "金":
        return "#C47A55" if yin_yang == "阳" else "#8B634B"  # 模拟紫铜：阳=亮铜色，阴=氧化暗铜色
    elif element == "木":
        return "#27ae60" if yin_yang == "阳" else "#1a7a40"
    elif element == "水":
        return "#3498db"
    elif element == "火":
        return "#e74c3c" if yin_yang == "阳" else "#c0392b"
    elif element == "土":
        return "#d4a017" if yin_yang == "阳" else "#a08020"

    return text_color


def _blend_with_gray(hex_color: str) -> str:
    """将颜色与50%灰色混合，用于阴金"""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = (r + 128) // 2
    g = (g + 128) // 2
    b = (b + 128) // 2
    return f"#{r:02x}{g:02x}{b:02x}"
