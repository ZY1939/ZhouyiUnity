"""
五行工具集 — 天干地支/八卦/生克/六亲/颜色 统一管理

═══════════════════════════════════════════════════════════════
文件职责：提供五行相关所有数据定义和计算函数，供 liuyao/梅花/六爻
         等模块统一调用，消除分散在各文件中的重复五行代码

核心数据（唯一真相来源）：
  _TRIGRAM_INFO  → 八卦(先天数,五行,阴阳) — 所有八卦/卦宫映射由此派生
  WUXING_COLORS  → 五行颜色(阳/阴)         — 所有颜色由此派生

派生数据：
  PALACE_WUXING       → {f"{卦名}宫": 五行}  由 _TRIGRAM_INFO 生成
  WUXING_BASE_COLORS  → {五行: 阳色}         由 WUXING_COLORS 生成

导出函数：
  get_wangxiangxiuqiu(main, slave) → str   旺相休囚死
  get_liuqin(palace_wuxing, dizhi) → str
  get_wuxing_color_by_trigram(gua_name) → str
  get_wuxing_color_by_xiantian(num) → str
  get_wuxing_base_color(wuxing) → str
  get_liushen_fill(liushen, is_dark) → str
  get_liushen_char(liushen) → str
  compact_liuqin(liuqin) → str

被哪些文件调用：
  - algorithms/liuyao.py         → DIZHI_WUXING, PALACE_WUXING, get_liuqin
  - algorithms/ganzhiTools.py    → TIANGAN_WUXING, DIZHI_WUXING
  - suangua/liuyao_panel.py      → 六神/纳音颜色, 六亲精简
  - suangua/meihua_panel.py      → 五行颜色 for 互卦
"""

# ═══════════════════════════════════════════════════════════════
#  天干 → 五行
# ═══════════════════════════════════════════════════════════════

TIANGAN_WUXING: dict[str, str] = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}

# ═══════════════════════════════════════════════════════════════
#  地支 → 五行
# ═══════════════════════════════════════════════════════════════

DIZHI_WUXING: dict[str, str] = {
    "子": "水", "亥": "水",
    "寅": "木", "卯": "木",
    "巳": "火", "午": "火",
    "申": "金", "酉": "金",
    "辰": "土", "戌": "土", "丑": "土", "未": "土",
}

# ═══════════════════════════════════════════════════════════════
#  五行相生/相克
# ═══════════════════════════════════════════════════════════════

WUXING_SHENG: dict[str, str] = {
    "金": "水", "水": "木", "木": "火", "火": "土", "土": "金",
}

WUXING_KE: dict[str, str] = {
    "金": "木", "木": "土", "土": "水", "水": "火", "火": "金",
}

# ═══════════════════════════════════════════════════════════════
#  八卦 — 唯一源头：卦名 → (先天数, 五行, 阴阳)
#  PALACE_WUXING、颜色查询均由此派生
# ═══════════════════════════════════════════════════════════════

_TRIGRAM_INFO: dict[str, tuple[int, str, str]] = {
    "乾": (1, "金", "阳"),
    "兑": (2, "金", "阴"),
    "离": (3, "火", "阴"),
    "震": (4, "木", "阳"),
    "巽": (5, "木", "阴"),
    "坎": (6, "水", "阳"),
    "艮": (7, "土", "阳"),
    "坤": (8, "土", "阴"),
}

# 卦宫 → 五行（由 _TRIGRAM_INFO 派生）
PALACE_WUXING: dict[str, str] = {
    f"{k}宫": v[1] for k, v in _TRIGRAM_INFO.items()
}

# 先天数 → (五行, 阴阳) 反向索引
_XIANTIAN_INDEX: dict[int, tuple[str, str]] = {
    v[0]: (v[1], v[2]) for v in _TRIGRAM_INFO.values()
}

# ═══════════════════════════════════════════════════════════════
#  五行 → 颜色 (唯一颜色来源)
#  阳色用于 badge 填充，阴色用于暗底
# ═══════════════════════════════════════════════════════════════

WUXING_COLORS: dict[str, dict[str, str]] = {
    "金": {"阳": "#C47A55", "阴": "#8B634B"},
    "木": {"阳": "#27ae60", "阴": "#1a7a40"},
    "水": {"阳": "#3498db", "阴": "#3498db"},
    "火": {"阳": "#e74c3c", "阴": "#c0392b"},
    "土": {"阳": "#d4a017", "阴": "#a08020"},
}

# 五行基底色（取阳色）— 由 WUXING_COLORS 派生
WUXING_BASE_COLORS: dict[str, str] = {
    k: v["阳"] for k, v in WUXING_COLORS.items()
}

# ═══════════════════════════════════════════════════════════════
#  六亲 → 精简单字
# ═══════════════════════════════════════════════════════════════

LIUQIN_COMPACT: dict[str, str] = {
    "父母": "父",
    "子孙": "孙",
    "官鬼": "官",
    "妻财": "财",
    "兄弟": "兄",
}

# ═══════════════════════════════════════════════════════════════
#  六神 → (显示单字, 五行)
#  颜色由 WUXING_COLORS 派生，不在此重复
# ═══════════════════════════════════════════════════════════════

LIUSHEN_INFO: dict[str, tuple[str, str]] = {
    "青龙": ("龙", "木"),
    "朱雀": ("雀", "火"),
    "勾陈": ("陈", "土"),
    "螣蛇": ("蛇", "土"),
    "白虎": ("虎", "金"),
    "玄武": ("玄", "水"),
}

# ═══════════════════════════════════════════════════════════════
#  体用/动爻 符号颜色
# ═══════════════════════════════════════════════════════════════

TI_COLOR = "#e74c3c"
YONG_COLOR = "#3498db"
O_COLOR = "#e74c3c"
X_COLOR = "#3498db"


# ═══════════════════════════════════════════════════════════════
#  公开函数
# ═══════════════════════════════════════════════════════════════

def get_wangxiangxiuqiu(main: str, slave: str) -> str:
    """
    旺相休囚死 — 以 main 五行为月建（当令），判断 slave 五行的旺衰状态

    规则：
      同我者 → 旺     main 同 slave
      生我者 → 相     main 生 slave
      我生者 → 休     slave 生 main
      我克者 → 囚     slave 克 main
      克我者 → 死     main 克 slave

    Args:
        main:  月建五行（金/木/水/火/土），当令的一方
        slave: 待测五行（金/木/水/火/土）

    Returns:
        str: "旺"/"相"/"休"/"囚"/"死"，无法判定返回空串

    Examples:
        get_wangxiangxiuqiu("木", "火") → "相"   （春木当令→木生火→火相）
        get_wangxiangxiuqiu("木", "木") → "旺"   （同气→旺）
        get_wangxiangxiuqiu("木", "土") → "死"   （木克土→死）
    """
    if not main or not slave or main not in WUXING_SHENG or slave not in WUXING_SHENG:
        return ""

    if slave == main:
        return "旺"
    if WUXING_SHENG.get(main) == slave:
        return "相"
    if WUXING_SHENG.get(slave) == main:
        return "休"
    if WUXING_KE.get(slave) == main:
        return "囚"
    if WUXING_KE.get(main) == slave:
        return "死"
    return ""


def get_liuqin(palace_wuxing: str, dizhi: str) -> str:
    """
    以卦宫五行为"我"，与地支五行比较 → 返回六亲

    规则：生我者→父母  我生者→子孙  克我者→官鬼  我克者→妻财  同我者→兄弟

    Args:
        palace_wuxing: 卦宫五行（金/木/水/火/土）
        dizhi: 地支（子/丑/寅/卯/…）

    Returns:
        str: 六亲名称，计算失败返回空串
    """
    zhi_wx = DIZHI_WUXING.get(dizhi, "")
    if not zhi_wx or not palace_wuxing:
        return ""

    if zhi_wx == palace_wuxing:
        return "兄弟"
    if WUXING_SHENG.get(palace_wuxing) == zhi_wx:
        return "子孙"
    if WUXING_SHENG.get(zhi_wx) == palace_wuxing:
        return "父母"
    if WUXING_KE.get(palace_wuxing) == zhi_wx:
        return "妻财"
    if WUXING_KE.get(zhi_wx) == palace_wuxing:
        return "官鬼"
    return ""


def compact_liuqin(liuqin: str) -> str:
    """六亲 → 精简单字名（父/孙/官/财/凶）"""
    return LIUQIN_COMPACT.get(liuqin, liuqin)


def get_wuxing_color_by_trigram(gua_name: str, text_color: str = "#1d1d1f") -> str:
    """根据八卦名返回对应的五行颜色"""
    info = _TRIGRAM_INFO.get(gua_name)
    if not info:
        return text_color
    _, element, yin_yang = info
    return WUXING_COLORS.get(element, {}).get(yin_yang, text_color)


def get_wuxing_color_by_xiantian(xiantian_num: int, text_color: str = "#1d1d1f") -> str:
    """根据先天八卦数返回对应的五行颜色"""
    wx = _XIANTIAN_INDEX.get(xiantian_num)
    if not wx:
        return text_color
    element, yin_yang = wx
    return WUXING_COLORS.get(element, {}).get(yin_yang, text_color)


def get_wuxing_base_color(wuxing: str) -> str:
    """五行名 → 基底色（阳色）"""
    return WUXING_BASE_COLORS.get(wuxing, "#1d1d1f")


def get_liushen_fill(liushen: str, is_dark: bool = False) -> str:
    """
    六神 → badge 填充颜色（由 WUXING_COLORS 派生）

    Args:
        liushen: 六神名
        is_dark: 是否深色模式

    Returns:
        CSS hex 颜色
    """
    info = LIUSHEN_INFO.get(liushen)
    if not info:
        return "#999999"
    _, wuxing = info
    # 白虎特殊：亮底→暗填充，暗底→亮填充
    if liushen == "白虎":
        return "#cccccc" if is_dark else "#2c2c2e"
    return WUXING_COLORS.get(wuxing, {}).get("阳", "#999999")


def get_liushen_char(liushen: str) -> str:
    """六神 → 显示单字（龙/雀/陈/蛇/虎/玄）"""
    info = LIUSHEN_INFO.get(liushen)
    return info[0] if info else liushen[0]
