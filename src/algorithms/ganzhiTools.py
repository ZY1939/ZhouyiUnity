"""
干支工具集 — 干支五行/阴阳/相合/相冲/相刑/相害 统一查询

依赖: algorithms/wuxingTools.py 中的 TIANGAN_WUXING / DIZHI_WUXING

导出函数:
  get_gan_wuxing(gan)        → 天干五行
  get_zhi_wuxing(zhi)        → 地支五行
  get_ganzhi_wuxing(ganzhi)  → 干支五行 (天干五行, 地支五行)
  get_gan_yinyang(gan)       → 天干阴阳
  get_zhi_yinyang(zhi)       → 地支阴阳
  get_ganzhi_yinyang(ganzhi) → 干支阴阳 (天干阴阳, 地支阴阳)
  get_gan_he(gan)            → 天干相合 (合化五行, 合干)
  get_zhi_liuhe(zhi)         → 地支六合 (合化五行, 合支)
  get_zhi_sanhe(zhi)         → 地支三合 (合化五行, 三合支)
  get_zhi_sanhui(zhi)        → 地支三会 (会化五行, 三会支)
  get_zhi_chong(zhi)         → 地支六冲 (冲支)
  get_zhi_xing(zhi)          → 地支相刑 (刑支列表)
  get_zhi_hai(zhi)           → 地支相害 (害支)
  gan_he_each_other(g1, g2)  → 两天干是否相合
  zhi_liuhe_each_other(z1,z2)→ 两地支是否六合
  zhi_chong_each_other(z1,z2)→ 两地支是否相冲
  zhi_hai_each_other(z1,z2)  → 两地支是否相害
  zhi_xing_each_other(z1,z2) → 两地支是否相刑
  get_xunkong(ganzhi)          → 干支旬空二支

被哪些文件调用: (新建，待接入)
"""

from .wuxingTools import TIANGAN_WUXING, DIZHI_WUXING

# ═══════════════════════════════════════════════════════════════
#  天干 → 阴阳
# ═══════════════════════════════════════════════════════════════

TIANGAN_YINYANG: dict[str, str] = {
    "甲": "阳", "丙": "阳", "戊": "阳", "庚": "阳", "壬": "阳",
    "乙": "阴", "丁": "阴", "己": "阴", "辛": "阴", "癸": "阴",
}

# ═══════════════════════════════════════════════════════════════
#  地支 → 阴阳
# ═══════════════════════════════════════════════════════════════

DIZHI_YINYANG: dict[str, str] = {
    "子": "阳", "寅": "阳", "辰": "阳", "午": "阳", "申": "阳", "戌": "阳",
    "丑": "阴", "卯": "阴", "巳": "阴", "未": "阴", "酉": "阴", "亥": "阴",
}

# ═══════════════════════════════════════════════════════════════
#  天干相合 → (合化五行, 对方天干)
#  甲己合土、乙庚合金、丙辛合水、丁壬合木、戊癸合火
# ═══════════════════════════════════════════════════════════════

TIANGAN_HE: dict[str, tuple[str, str]] = {
    "甲": ("土", "己"),
    "己": ("土", "甲"),
    "乙": ("金", "庚"),
    "庚": ("金", "乙"),
    "丙": ("水", "辛"),
    "辛": ("水", "丙"),
    "丁": ("木", "壬"),
    "壬": ("木", "丁"),
    "戊": ("火", "癸"),
    "癸": ("火", "戊"),
}

# ═══════════════════════════════════════════════════════════════
#  地支六合 → (合化五行, 对方地支)
#  子丑合土、寅亥合木、卯戌合火、辰酉合金、巳申合水、午未合土
# ═══════════════════════════════════════════════════════════════

DIZHI_LIUHE: dict[str, tuple[str, str]] = {
    "子": ("土", "丑"),
    "丑": ("土", "子"),
    "寅": ("木", "亥"),
    "亥": ("木", "寅"),
    "卯": ("火", "戌"),
    "戌": ("火", "卯"),
    "辰": ("金", "酉"),
    "酉": ("金", "辰"),
    "巳": ("水", "申"),
    "申": ("水", "巳"),
    "午": ("火", "未"),  # 午未合火（亦有合土之说，此处取火）
    "未": ("火", "午"),
}

# ═══════════════════════════════════════════════════════════════
#  地支三合 → (合化五行, 三合地支元组)
#  申子辰合水、亥卯未合木、寅午戌合火、巳酉丑合金
# ═══════════════════════════════════════════════════════════════

DIZHI_SANHE_GROUPS: list[tuple[str, tuple[str, str, str]]] = [
    ("水", ("申", "子", "辰")),
    ("木", ("亥", "卯", "未")),
    ("火", ("寅", "午", "戌")),
    ("金", ("巳", "酉", "丑")),
]

# 地支 → (合化五行, 三合支元组)
DIZHI_SANHE: dict[str, tuple[str, tuple[str, str, str]]] = {}
for _wx, _triple in DIZHI_SANHE_GROUPS:
    for _z in _triple:
        DIZHI_SANHE[_z] = (_wx, _triple)

# ═══════════════════════════════════════════════════════════════
#  地支三会 → (会化五行, 三会支元组)
#  寅卯辰会木、巳午未会火、申酉戌会金、亥子丑会水
# ═══════════════════════════════════════════════════════════════

DIZHI_SANHUI_GROUPS: list[tuple[str, tuple[str, str, str]]] = [
    ("木", ("寅", "卯", "辰")),
    ("火", ("巳", "午", "未")),
    ("金", ("申", "酉", "戌")),
    ("水", ("亥", "子", "丑")),
]

DIZHI_SANHUI: dict[str, tuple[str, tuple[str, str, str]]] = {}
for _wx, _triple in DIZHI_SANHUI_GROUPS:
    for _z in _triple:
        DIZHI_SANHUI[_z] = (_wx, _triple)

# ═══════════════════════════════════════════════════════════════
#  地支六冲 → 对方地支
#  子午冲、丑未冲、寅申冲、卯酉冲、辰戌冲、巳亥冲
# ═══════════════════════════════════════════════════════════════

DIZHI_CHONG: dict[str, str] = {
    "子": "午", "午": "子",
    "丑": "未", "未": "丑",
    "寅": "申", "申": "寅",
    "卯": "酉", "酉": "卯",
    "辰": "戌", "戌": "辰",
    "巳": "亥", "亥": "巳",
}

# ═══════════════════════════════════════════════════════════════
#  地支相刑 — 每种刑返回涉及的所有地支
#  无礼之刑: 子卯  恃势之刑: 寅巳申  无恩之刑: 丑戌未
#  自刑: 辰/午/酉/亥
# ═══════════════════════════════════════════════════════════════

DIZHI_XING: dict[str, list[str]] = {
    "子": ["卯"],              # 子卯无礼之刑
    "卯": ["子"],              # 卯子无礼之刑
    "寅": ["巳", "申"],        # 寅巳申恃势之刑
    "巳": ["寅", "申"],        # 巳寅申恃势之刑
    "申": ["寅", "巳"],        # 申寅巳恃势之刑
    "丑": ["戌", "未"],        # 丑戌未无恩之刑
    "戌": ["丑", "未"],        # 戌丑未无恩之刑
    "未": ["丑", "戌"],        # 未丑戌无恩之刑
    "辰": ["辰"],              # 辰自刑
    "午": ["午"],              # 午自刑
    "酉": ["酉"],              # 酉自刑
    "亥": ["亥"],              # 亥自刑
}

# ═══════════════════════════════════════════════════════════════
#  地支相害 → 对方地支
#  子未害、丑午害、寅巳害、卯辰害、申亥害、酉戌害
# ═══════════════════════════════════════════════════════════════

DIZHI_HAI: dict[str, str] = {
    "子": "未", "未": "子",
    "丑": "午", "午": "丑",
    "寅": "巳", "巳": "寅",
    "卯": "辰", "辰": "卯",
    "申": "亥", "亥": "申",
    "酉": "戌", "戌": "酉",
}

# ═══════════════════════════════════════════════════════════════
#  六十甲子 + 旬空查询
# ═══════════════════════════════════════════════════════════════

_TIANGAN_LIST = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
_DIZHI_LIST = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 六十甲子表（0-59），索引0=甲子 … 索引59=癸亥
_JIAZI_60: list[str] = []
for _i in range(60):
    _JIAZI_60.append(_TIANGAN_LIST[_i % 10] + _DIZHI_LIST[_i % 12])

# 干支 → 旬空二支
_XUNKONG: dict[str, tuple[str, str]] = {}
for _xun in range(6):
    _start = _xun * 10                         # 该旬起始索引（甲X的位置）
    _branch_idx = _start % 12                  # 甲X中X的地支索引
    _kong1 = _DIZHI_LIST[(_branch_idx - 2) % 12]  # 空亡前一支
    _kong2 = _DIZHI_LIST[(_branch_idx - 1) % 12]  # 空亡后一支
    for _j in range(10):
        _XUNKONG[_JIAZI_60[_start + _j]] = (_kong1, _kong2)


# ═══════════════════════════════════════════════════════════════
#  五行查询
# ═══════════════════════════════════════════════════════════════


def get_gan_wuxing(gan: str) -> str:
    """
    天干 → 五行

    Args:
        gan: 天干（甲/乙/丙/丁/戊/己/庚/辛/壬/癸）

    Returns:
        str: 五行（金/木/水/火/土），未找到返回空串

    Examples:
        >>> get_gan_wuxing("甲")
        '木'
    """
    return TIANGAN_WUXING.get(gan, "")


def get_zhi_wuxing(zhi: str) -> str:
    """
    地支 → 五行

    Args:
        zhi: 地支（子/丑/寅/卯/…/亥）

    Returns:
        str: 五行（金/木/水/火/土），未找到返回空串

    Examples:
        >>> get_zhi_wuxing("子")
        '水'
    """
    return DIZHI_WUXING.get(zhi, "")


def get_ganzhi_wuxing(ganzhi: str) -> tuple[str, str]:
    """
    干支（两字）→ (天干五行, 地支五行)

    Args:
        ganzhi: 干支组合，如 "甲子"、"乙丑"

    Returns:
        tuple[str, str]: (天干五行, 地支五行)

    Examples:
        >>> get_ganzhi_wuxing("甲子")
        ('木', '水')
    """
    gan, zhi = ganzhi[0], ganzhi[1]
    return TIANGAN_WUXING.get(gan, ""), DIZHI_WUXING.get(zhi, "")


# ═══════════════════════════════════════════════════════════════
#  阴阳查询
# ═══════════════════════════════════════════════════════════════


def get_gan_yinyang(gan: str) -> str:
    """
    天干 → 阴阳

    Args:
        gan: 天干

    Returns:
        str: "阳" 或 "阴"

    Examples:
        >>> get_gan_yinyang("甲")
        '阳'
        >>> get_gan_yinyang("乙")
        '阴'
    """
    return TIANGAN_YINYANG.get(gan, "")


def get_zhi_yinyang(zhi: str) -> str:
    """
    地支 → 阴阳

    Args:
        zhi: 地支

    Returns:
        str: "阳" 或 "阴"

    Examples:
        >>> get_zhi_yinyang("子")
        '阳'
    """
    return DIZHI_YINYANG.get(zhi, "")


def get_ganzhi_yinyang(ganzhi: str) -> tuple[str, str]:
    """
    干支（两字）→ (天干阴阳, 地支阴阳)

    Args:
        ganzhi: 干支组合，如 "甲子"

    Returns:
        tuple[str, str]: (天干阴阳, 地支阴阳)
    """
    gan, zhi = ganzhi[0], ganzhi[1]
    return TIANGAN_YINYANG.get(gan, ""), DIZHI_YINYANG.get(zhi, "")


# ═══════════════════════════════════════════════════════════════
#  天干相合
# ═══════════════════════════════════════════════════════════════


def get_gan_he(gan: str) -> tuple[str, str]:
    """
    天干 → 相合信息

    Args:
        gan: 天干

    Returns:
        tuple[str, str]: (合化五行, 相合天干)，未找到返回 ("", "")

    Examples:
        >>> get_gan_he("甲")
        ('土', '己')
    """
    return TIANGAN_HE.get(gan, ("", ""))


def gan_he_each_other(g1: str, g2: str) -> bool:
    """
    两个天干是否相合

    Args:
        g1: 天干1
        g2: 天干2

    Returns:
        bool: True=相合

    Examples:
        >>> gan_he_each_other("甲", "己")
        True
        >>> gan_he_each_other("甲", "乙")
        False
    """
    he_info = TIANGAN_HE.get(g1)
    return he_info is not None and he_info[1] == g2


# ═══════════════════════════════════════════════════════════════
#  地支六合 / 三合 / 三会
# ═══════════════════════════════════════════════════════════════


def get_zhi_liuhe(zhi: str) -> tuple[str, str]:
    """
    地支 → 六合信息

    Args:
        zhi: 地支

    Returns:
        tuple[str, str]: (合化五行, 合支)

    Examples:
        >>> get_zhi_liuhe("子")
        ('土', '丑')
    """
    return DIZHI_LIUHE.get(zhi, ("", ""))


def zhi_liuhe_each_other(z1: str, z2: str) -> bool:
    """
    两个地支是否六合

    Args:
        z1: 地支1
        z2: 地支2

    Returns:
        bool: True=六合
    """
    he_info = DIZHI_LIUHE.get(z1)
    return he_info is not None and he_info[1] == z2


def get_zhi_sanhe(zhi: str) -> tuple[str, tuple[str, str, str]]:
    """
    地支 → 三合信息

    Args:
        zhi: 地支

    Returns:
        tuple[str, tuple[str, str, str]]: (合化五行, 三合支元组)

    Examples:
        >>> get_zhi_sanhe("申")
        ('水', ('申', '子', '辰'))
    """
    return DIZHI_SANHE.get(zhi, ("", ("", "", "")))


def get_zhi_sanhui(zhi: str) -> tuple[str, tuple[str, str, str]]:
    """
    地支 → 三会信息

    Args:
        zhi: 地支

    Returns:
        tuple[str, tuple[str, str, str]]: (会化五行, 三会支元组)

    Examples:
        >>> get_zhi_sanhui("寅")
        ('木', ('寅', '卯', '辰'))
    """
    return DIZHI_SANHUI.get(zhi, ("", ("", "", "")))


# ═══════════════════════════════════════════════════════════════
#  地支六冲
# ═══════════════════════════════════════════════════════════════


def get_zhi_chong(zhi: str) -> str:
    """
    地支 → 相冲地支

    Args:
        zhi: 地支

    Returns:
        str: 冲支，未找到返回空串

    Examples:
        >>> get_zhi_chong("子")
        '午'
    """
    return DIZHI_CHONG.get(zhi, "")


def zhi_chong_each_other(z1: str, z2: str) -> bool:
    """
    两个地支是否相冲

    Returns:
        bool: True=相冲
    """
    return DIZHI_CHONG.get(z1, "") == z2


# ═══════════════════════════════════════════════════════════════
#  地支相刑
# ═══════════════════════════════════════════════════════════════


def get_zhi_xing(zhi: str) -> list[str]:
    """
    地支 → 相刑地支列表

    自刑（辰/午/酉/亥）返回自身，表示与同支相见为自刑。

    Args:
        zhi: 地支

    Returns:
        list[str]: 相刑的地支列表（可能为空）

    Examples:
        >>> get_zhi_xing("子")
        ['卯']
        >>> get_zhi_xing("寅")
        ['巳', '申']
        >>> get_zhi_xing("辰")
        ['辰']
    """
    return DIZHI_XING.get(zhi, [])


def zhi_xing_each_other(z1: str, z2: str) -> bool:
    """
    两个地支是否相刑

    Args:
        z1: 地支1
        z2: 地支2

    Returns:
        bool: True=相刑（含自刑）
    """
    xing_list = DIZHI_XING.get(z1, [])
    return z2 in xing_list


# ═══════════════════════════════════════════════════════════════
#  地支相害
# ═══════════════════════════════════════════════════════════════


def get_zhi_hai(zhi: str) -> str:
    """
    地支 → 相害地支

    Args:
        zhi: 地支

    Returns:
        str: 害支，未找到返回空串

    Examples:
        >>> get_zhi_hai("子")
        '未'
    """
    return DIZHI_HAI.get(zhi, "")


def zhi_hai_each_other(z1: str, z2: str) -> bool:
    """
    两个地支是否相害

    Returns:
        bool: True=相害
    """
    return DIZHI_HAI.get(z1, "") == z2


# ═══════════════════════════════════════════════════════════════
#  旬空查询
# ═══════════════════════════════════════════════════════════════


def get_xunkong(ganzhi: str) -> tuple[str, str]:
    """
    干支（两字）→ 旬空二支（六甲旬空）

    六十甲子每旬10对干支，对应12地支中缺失的2支即为"旬空/空亡"。
    六旬依次为：甲子旬(空戌亥)、甲戌旬(空申酉)、甲申旬(空午未)、
    甲午旬(空辰巳)、甲辰旬(空寅卯)、甲寅旬(空子丑)。

    Args:
        ganzhi: 干支组合，如 "甲寅"、"丙子"

    Returns:
        tuple[str, str]: 旬空的两个地支，未找到返回 ("", "")

    Examples:
        >>> get_xunkong("甲寅")
        ('子', '丑')
        >>> get_xunkong("甲子")
        ('戌', '亥')
        >>> get_xunkong("丙子")
        ('戌', '亥')
    """
    return _XUNKONG.get(ganzhi, ("", ""))
