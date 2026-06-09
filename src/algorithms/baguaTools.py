"""
八卦工具集 — 八卦名称/数字/自然象征 统一管理

═══════════════════════════════════════════════════════════════
文件职责：提供八卦结构性数据（名称映射、先天数、自然象征），
         与 wuxingTools（五行/颜色）职责分离。

导出：
  ELEMENT_TO_TRIGRAM  → 自然元素字 → 八卦名（天→乾, 泽→兑…）
  TRIGRAM_TO_ELEMENT  → 八卦名 → 自然元素字（乾→天, 兑→泽…）
  TRIGRAM_TO_BAGUA    → 八卦名 → 八纯卦全名
  BAGUA_SET           → 八纯卦名集合
  XIANTIAN_NUM        → 八卦名 → 先天数
  XIANTIAN_NAME       → 先天数 → 八卦名

导出函数：
  get_trigram_name(element_char)      元素字 → 八卦名
  get_natural_element(trigram)        八卦名 → 自然象征
  get_bagua_full_name(trigram)        八卦名 → 八纯卦全名
  get_xiantian_num(trigram)           八卦名 → 先天数
  get_trigram_by_xiantian(num)        先天数 → 八卦名

被哪些文件调用：
  - algorithms/liuyao.py → 解析卦名上/下卦、组装纳甲
  - algorithms/wuxingTools.py → 五行/颜色（共享 _TRIGRAM_INFO）
"""

# ═══════════════════════════════════════════════════════════════
#  自然元素字 ↔ 八卦名
# ═══════════════════════════════════════════════════════════════

ELEMENT_TO_TRIGRAM: dict[str, str] = {
    "天": "乾", "泽": "兑", "火": "离", "雷": "震",
    "风": "巽", "水": "坎", "山": "艮", "地": "坤",
    # 同时支持直接用卦名
    "乾": "乾", "兑": "兑", "离": "离", "震": "震",
    "巽": "巽", "坎": "坎", "艮": "艮", "坤": "坤",
}

TRIGRAM_TO_ELEMENT: dict[str, str] = {
    "乾": "天", "兑": "泽", "离": "火", "震": "雷",
    "巽": "风", "坎": "水", "艮": "山", "坤": "地",
}

# ═══════════════════════════════════════════════════════════════
#  八卦名 → 八纯卦全名
# ═══════════════════════════════════════════════════════════════

TRIGRAM_TO_BAGUA: dict[str, str] = {
    "乾": "乾为天", "兑": "兑为泽", "离": "离为火", "震": "震为雷",
    "巽": "巽为风", "坎": "坎为水", "艮": "艮为山", "坤": "坤为地",
}

# 八纯卦全名集合
BAGUA_SET: set[str] = set(TRIGRAM_TO_BAGUA.values())

# ═══════════════════════════════════════════════════════════════
#  先天数 ↔ 八卦名
# ═══════════════════════════════════════════════════════════════

XIANTIAN_NUM: dict[str, int] = {
    "乾": 1, "兑": 2, "离": 3, "震": 4,
    "巽": 5, "坎": 6, "艮": 7, "坤": 8,
}

XIANTIAN_NAME: dict[int, str] = {v: k for k, v in XIANTIAN_NUM.items()}


# ═══════════════════════════════════════════════════════════════
#  公开函数
# ═══════════════════════════════════════════════════════════════

def get_trigram_name(element_char: str) -> str:
    """
    自然元素字 → 八卦名

    Args:
        element_char: 元素字（天/泽/火/雷/风/水/山/地）或卦名本身

    Returns:
        str: 八卦名（乾/兑/离/震/巽/坎/艮/坤），未找到返回空串

    Examples:
        >>> get_trigram_name("天")
        '乾'
        >>> get_trigram_name("乾")
        '乾'
    """
    return ELEMENT_TO_TRIGRAM.get(element_char, "")


def get_natural_element(trigram: str) -> str:
    """
    八卦名 → 自然象征

    Args:
        trigram: 八卦名（乾/兑/离/震/巽/坎/艮/坤）

    Returns:
        str: 自然物体（天/泽/火/雷/风/水/山/地）

    Examples:
        >>> get_natural_element("巽")
        '风'
    """
    return TRIGRAM_TO_ELEMENT.get(trigram, "")


def get_bagua_full_name(trigram: str) -> str:
    """
    八卦名 → 八纯卦全名

    Args:
        trigram: 八卦名

    Returns:
        str: 八纯卦全名（如"乾为天"），未找到返回空串
    """
    return TRIGRAM_TO_BAGUA.get(trigram, "")


def get_xiantian_num(trigram: str) -> int:
    """
    八卦名 → 先天数

    Args:
        trigram: 八卦名

    Returns:
        int: 先天数（1-8），未找到返回 0
    """
    return XIANTIAN_NUM.get(trigram, 0)


def get_trigram_by_xiantian(num: int) -> str:
    """
    先天数 → 八卦名

    Args:
        num: 先天数（1-8）

    Returns:
        str: 八卦名，未找到返回空串
    """
    return XIANTIAN_NAME.get(num, "")


def parse_hexagram_trigrams(gua_name: str) -> tuple[str, str]:
    """
    从卦全名解析上卦和下卦八卦名

    规则：
      - 八纯卦（如"乾为天"）：上下卦相同
      - 其他卦（如"天风姤"）：第一个字=上卦，第二个字=下卦

    Args:
        gua_name: 卦全名

    Returns:
        tuple[str, str]: (上卦名, 下卦名)，解析失败返回 ("", "")
    """
    # 八纯卦：上下相同
    if gua_name in BAGUA_SET:
        trigram = get_trigram_name(gua_name[0])
        return (trigram, trigram)
    # 非八纯卦：第一个字=上卦，第二个字=下卦
    upper = get_trigram_name(gua_name[0]) if len(gua_name) >= 1 else ""
    lower = get_trigram_name(gua_name[1]) if len(gua_name) >= 2 else ""
    return (upper, lower)
