"""
流人占卜（六爻纳甲）工具 — 根据卦名和日干推演纳甲、六亲、六神、伏神

═══════════════════════════════════════════════════════════════
文件职责：纯计算模块，无 UI 依赖。根据卦名和日干，排出完整的
         六爻纳甲信息（纳甲干支、地支五行、六亲、六神、世应、伏神）
═══════════════════════════════════════════════════════════════

算法五步骤：
  步骤一：安纳甲 — 根据卦宫继承八纯卦纳甲歌诀，每爻分配天干地支
  步骤二：寻宫定"我" — 确定卦宫五行属性（乾兑=金，震巽=木…）
  步骤三：六亲推演 — 以卦宫五行为"我"，与爻支五行比较定六亲
  步骤四：六神排布 — 根据日干定初爻神，依次排列
  步骤五：伏神排布 — 比较本卦与卦宫八纯卦每爻六亲，不同者为伏神

六亲规则（以卦宫五行为"我"）：
  生我者 → 父母    我生者 → 子孙    克我者 → 官鬼
  我克者 → 妻财    同我者 → 兄弟

六神顺序：青龙 → 朱雀 → 勾陈 → 螣蛇 → 白虎 → 玄武
  甲乙日初爻青龙，丙丁日初爻朱雀，戊日初爻勾陈，
  己日初爻螣蛇，庚辛日初爻白虎，壬癸日初爻玄武

导出函数：
  analyze_gua(gua_name, day_gan) → dict  主入口
  get_palace_info(gua_name) → dict       查卦宫+五行+世应
  get_najia(gua_name) → list[dict]       查纳甲
  get_liuqin(palace_wuxing, dizhi) → str 查六亲（委托 wuxingTools）
  get_fushen(gua_name) → list[dict|None] 查伏神

被哪些文件调用：
  - suangua/liuyao_panel.py 六爻面板显示
  - liuyaoTest.py 测试脚本

依赖：
  - algorithms/wuxingTools.py → 五行数据/六亲计算/精简名

用法示例:
  from src.algorithms.liuyao import analyze_gua, get_fushen

  result = analyze_gua("乾为天", day_gan="甲")
  fushen = get_fushen("天风姤")
  for line in result["lines"]:
      print(f"{line['name']}: {line['najia']} {line['liuqin']} {line['liushen']}")
"""

# ── 从公共工具集导入 ──
from .wuxingTools import DIZHI_WUXING, PALACE_WUXING, get_liuqin, compact_liuqin
from .baguaTools import (
    ELEMENT_TO_TRIGRAM, TRIGRAM_TO_BAGUA, BAGUA_SET,
    parse_hexagram_trigrams, get_bagua_full_name,
)

# ═══════════════════════════════════════════════════════════════
#  八纯卦纳甲歌诀 — 六爻天干地支（从初爻到上爻）
# ═══════════════════════════════════════════════════════════════

_NAJIA_TABLE: dict[str, list[dict[str, str]]] = {
    "乾为天": [
        {"gan": "甲", "zhi": "子"},  # 初爻
        {"gan": "甲", "zhi": "寅"},  # 二爻
        {"gan": "甲", "zhi": "辰"},  # 三爻
        {"gan": "壬", "zhi": "午"},  # 四爻
        {"gan": "壬", "zhi": "申"},  # 五爻
        {"gan": "壬", "zhi": "戌"},  # 上爻
    ],
    "坎为水": [
        {"gan": "戊", "zhi": "寅"},  # 初爻
        {"gan": "戊", "zhi": "辰"},  # 二爻
        {"gan": "戊", "zhi": "午"},  # 三爻
        {"gan": "戊", "zhi": "申"},  # 四爻
        {"gan": "戊", "zhi": "戌"},  # 五爻
        {"gan": "戊", "zhi": "子"},  # 上爻
    ],
    "艮为山": [
        {"gan": "丙", "zhi": "辰"},  # 初爻
        {"gan": "丙", "zhi": "午"},  # 二爻
        {"gan": "丙", "zhi": "申"},  # 三爻
        {"gan": "丙", "zhi": "戌"},  # 四爻
        {"gan": "丙", "zhi": "子"},  # 五爻
        {"gan": "丙", "zhi": "寅"},  # 上爻
    ],
    "震为雷": [
        {"gan": "庚", "zhi": "子"},  # 初爻
        {"gan": "庚", "zhi": "寅"},  # 二爻
        {"gan": "庚", "zhi": "辰"},  # 三爻
        {"gan": "庚", "zhi": "午"},  # 四爻
        {"gan": "庚", "zhi": "申"},  # 五爻
        {"gan": "庚", "zhi": "戌"},  # 上爻
    ],
    "巽为风": [
        {"gan": "辛", "zhi": "丑"},  # 初爻
        {"gan": "辛", "zhi": "亥"},  # 二爻
        {"gan": "辛", "zhi": "酉"},  # 三爻
        {"gan": "辛", "zhi": "未"},  # 四爻
        {"gan": "辛", "zhi": "巳"},  # 五爻
        {"gan": "辛", "zhi": "卯"},  # 上爻
    ],
    "离为火": [
        {"gan": "己", "zhi": "卯"},  # 初爻
        {"gan": "己", "zhi": "丑"},  # 二爻
        {"gan": "己", "zhi": "亥"},  # 三爻
        {"gan": "己", "zhi": "酉"},  # 四爻
        {"gan": "己", "zhi": "未"},  # 五爻
        {"gan": "己", "zhi": "巳"},  # 上爻
    ],
    "坤为地": [
        {"gan": "乙", "zhi": "未"},  # 初爻
        {"gan": "乙", "zhi": "巳"},  # 二爻
        {"gan": "乙", "zhi": "卯"},  # 三爻
        {"gan": "癸", "zhi": "丑"},  # 四爻
        {"gan": "癸", "zhi": "亥"},  # 五爻
        {"gan": "癸", "zhi": "酉"},  # 上爻
    ],
    "兑为泽": [
        {"gan": "丁", "zhi": "巳"},  # 初爻
        {"gan": "丁", "zhi": "卯"},  # 二爻
        {"gan": "丁", "zhi": "丑"},  # 三爻
        {"gan": "丁", "zhi": "亥"},  # 四爻
        {"gan": "丁", "zhi": "酉"},  # 五爻
        {"gan": "丁", "zhi": "未"},  # 上爻
    ],
}

# ═══════════════════════════════════════════════════════════════
#  64卦八宫归属 + 宫内序号
#  序号含义：1=八纯卦 2=一世 3=二世 4=三世 5=四世 6=五世 7=游魂 8=归魂
# ═══════════════════════════════════════════════════════════════

_GUA_TABLE: dict[str, tuple[str, int]] = {
    # ── 乾宫八卦 ──
    "乾为天": ("乾宫", 1),
    "天风姤": ("乾宫", 2),
    "天山遁": ("乾宫", 3),
    "天地否": ("乾宫", 4),
    "风地观": ("乾宫", 5),
    "山地剥": ("乾宫", 6),
    "火地晋": ("乾宫", 7),  # 游魂
    "火天大有": ("乾宫", 8),  # 归魂
    # ── 坎宫八卦 ──
    "坎为水": ("坎宫", 1),
    "水泽节": ("坎宫", 2),
    "水雷屯": ("坎宫", 3),
    "水火既济": ("坎宫", 4),
    "泽火革": ("坎宫", 5),
    "雷火丰": ("坎宫", 6),
    "地火明夷": ("坎宫", 7),  # 游魂
    "地水师": ("坎宫", 8),  # 归魂
    # ── 艮宫八卦 ──
    "艮为山": ("艮宫", 1),
    "山火贲": ("艮宫", 2),
    "山天大畜": ("艮宫", 3),
    "山泽损": ("艮宫", 4),
    "火泽睽": ("艮宫", 5),
    "天泽履": ("艮宫", 6),
    "风泽中孚": ("艮宫", 7),  # 游魂
    "风山渐": ("艮宫", 8),  # 归魂
    # ── 震宫八卦 ──
    "震为雷": ("震宫", 1),
    "雷地豫": ("震宫", 2),
    "雷水解": ("震宫", 3),
    "雷风恒": ("震宫", 4),
    "地风升": ("震宫", 5),
    "水风井": ("震宫", 6),
    "泽风大过": ("震宫", 7),  # 游魂
    "泽雷随": ("震宫", 8),  # 归魂
    # ── 巽宫八卦 ──
    "巽为风": ("巽宫", 1),
    "风天小畜": ("巽宫", 2),
    "风火家人": ("巽宫", 3),
    "风雷益": ("巽宫", 4),
    "天雷无妄": ("巽宫", 5),
    "火雷噬嗑": ("巽宫", 6),
    "山雷颐": ("巽宫", 7),  # 游魂
    "山风蛊": ("巽宫", 8),  # 归魂
    # ── 离宫八卦 ──
    "离为火": ("离宫", 1),
    "火山旅": ("离宫", 2),
    "火风鼎": ("离宫", 3),
    "火水未济": ("离宫", 4),
    "山水蒙": ("离宫", 5),
    "风水涣": ("离宫", 6),
    "天水讼": ("离宫", 7),  # 游魂
    "天火同人": ("离宫", 8),  # 归魂
    # ── 坤宫八卦 ──
    "坤为地": ("坤宫", 1),
    "地雷复": ("坤宫", 2),
    "地泽临": ("坤宫", 3),
    "地天泰": ("坤宫", 4),
    "雷天大壮": ("坤宫", 5),
    "泽天夬": ("坤宫", 6),
    "水天需": ("坤宫", 7),  # 游魂
    "水地比": ("坤宫", 8),  # 归魂
    # ── 兑宫八卦 ──
    "兑为泽": ("兑宫", 1),
    "泽水困": ("兑宫", 2),
    "泽地萃": ("兑宫", 3),
    "泽山咸": ("兑宫", 4),
    "水山蹇": ("兑宫", 5),
    "地山谦": ("兑宫", 6),
    "雷山小过": ("兑宫", 7),  # 游魂
    "雷泽归妹": ("兑宫", 8),  # 归魂
}

# 宫内序号 → 世爻位置(1-6), 应爻位置(1-6)
_SHI_YING_MAP: dict[int, tuple[int, int]] = {
    1: (6, 3),  # 八纯卦：世在上爻，应在三爻
    2: (1, 4),  # 一世卦：世在初爻，应在四爻
    3: (2, 5),  # 二世卦：世在二爻，应在五爻
    4: (3, 6),  # 三世卦：世在三爻，应在六爻
    5: (4, 1),  # 四世卦：世在四爻，应在初爻
    6: (5, 2),  # 五世卦：世在五爻，应在二爻
    7: (4, 1),  # 游魂卦：世在四爻，应在初爻
    8: (3, 6),  # 归魂卦：世在三爻，应在六爻
}

# ═══════════════════════════════════════════════════════════════
#  六冲卦 — 内外卦六爻地支两两相冲（共10个）
#  八纯卦(8) + 雷天大壮 + 天雷无妄
# ═══════════════════════════════════════════════════════════════

LIUCHONG_GUA: set[str] = {
    # 八纯卦
    "乾为天", "兑为泽", "离为火", "震为雷",
    "巽为风", "坎为水", "艮为山", "坤为地",
    # 特例
    "雷天大壮", "天雷无妄",
}

# ═══════════════════════════════════════════════════════════════
#  六合卦 — 内外卦六爻地支两两相合（共8个）
# ═══════════════════════════════════════════════════════════════

LIUHE_GUA: set[str] = {
    "天地否", "地天泰",
    "水泽节", "泽水困",
    "雷地豫", "地雷复",
    "火山旅", "山火贲",
}

# ═══════════════════════════════════════════════════════════════
#  游魂卦 — 八宫每宫第七卦（共8个）
# ═══════════════════════════════════════════════════════════════

YOUHUN_GUA: set[str] = {
    "火地晋",   # 乾宫
    "地火明夷",  # 坎宫
    "风泽中孚",  # 艮宫
    "泽风大过",  # 震宫
    "山雷颐",   # 巽宫
    "天水讼",   # 离宫
    "水天需",   # 坤宫
    "雷山小过",  # 兑宫
}

# ═══════════════════════════════════════════════════════════════
#  归魂卦 — 八宫每宫第八卦（共8个）
# ═══════════════════════════════════════════════════════════════

GUIHUN_GUA: set[str] = {
    "火天大有",  # 乾宫
    "地水师",   # 坎宫
    "风山渐",   # 艮宫
    "泽雷随",   # 震宫
    "山风蛊",   # 巽宫
    "天火同人",  # 离宫
    "水地比",   # 坤宫
    "雷泽归妹",  # 兑宫
}


def get_gua_type_tags(gua_name: str) -> str:
    """
    返回卦的特殊类型标签（六冲/六合/游魂/归魂）

    Args:
        gua_name: 卦全名（如"乾为天"）

    Returns:
        str: 类型标签，如"六冲"，无特殊类型返回空串
    """
    if gua_name in LIUCHONG_GUA:
        return "冲"
    if gua_name in LIUHE_GUA:
        return "合"
    if gua_name in YOUHUN_GUA:
        return "游"
    if gua_name in GUIHUN_GUA:
        return "归"
    return ""


# ═══════════════════════════════════════════════════════════════
#  卦类型标签颜色 — 心理感受匹配颜色
#  冲=红(冲突) 合=绿(和谐) 游=紫(游离) 归=暖橙(安定)
#  反=深红(反复痛苦) 伏=灰蓝(停滞沉闷)
# ═══════════════════════════════════════════════════════════════

GUA_TYPE_COLORS: dict[str, str] = {
    "冲": "#e74c3c",    # 红色 — 冲突、激烈
    "合": "#27ae60",    # 绿色 — 和谐、融合
    "游": "#8e44ad",    # 紫色 — 游离、飘忽、神秘
    "归": "#e67e22",    # 暖橙 — 回归、安定、温暖
    "反": "#c0392b",    # 深红 — 反复、痛苦、折腾
    "伏": "#546e7a",    # 灰蓝 — 停滞、沉闷、呻吟
}


def get_gua_type_badges(gua_name: str,
                        fanyin_type: str = "",
                        fuyin_type: str = "") -> list[tuple[str, str]]:
    """
    返回卦的类型标签方块列表 [(标签字, 颜色hex), ...]

    包含六冲/六合/游魂/归魂（来自本卦）以及反吟/伏吟（来自变卦比较）。

    Args:
        gua_name: 本卦全名
        fanyin_type: 反吟类型（"内卦"/"外卦"/"全卦"/""）
        fuyin_type: 伏吟类型（"内卦"/"外卦"/"全卦"/""）

    Returns:
        list[tuple[str, str]]: 标签列表，如 [("冲", "#e74c3c"), ("反", "#c0392b")]
    """
    badges = []
    tags = get_gua_type_tags(gua_name)
    if tags:
        badges.append((tags, GUA_TYPE_COLORS[tags]))
    if fanyin_type:
        badges.append(("反", GUA_TYPE_COLORS["反"]))
    if fuyin_type:
        badges.append(("伏", GUA_TYPE_COLORS["伏"]))
    return badges


# get_liuqin() / DIZHI_WUXING / PALACE_WUXING 已从 wuxingTools 导入
# 为向后兼容，保留模块级重导出（供外部直接 import liuyao.DIZHI_WUXING 使用）
# 实际计算统一委托 wuxingTools.get_liuqin()


# ═══════════════════════════════════════════════════════════════
#  六神 — 日干 → 初爻神 → 依次排列
# ═══════════════════════════════════════════════════════════════

_LIUSHEN_ORDER = ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"]

# 日干 → 初爻六神在 _LIUSHEN_ORDER 中的起始索引
_RI_GAN_TO_START: dict[str, int] = {
    "甲": 0, "乙": 0,
    "丙": 1, "丁": 1,
    "戊": 2,
    "己": 3,
    "庚": 4, "辛": 4,
    "壬": 5, "癸": 5,
}

# 爻位名称（1-6 → 初爻 ~ 上爻）
_LINE_NAMES = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]

def _build_najia_rows(gua_name: str) -> list[dict[str, str]] | None:
    """
    组装六爻纳甲 — 下卦用下卦八纯卦的初/二/三爻，上卦用上卦八纯卦的四/五/上爻

    Args:
        gua_name: 卦全名

    Returns:
        list[dict] 或 None: 6爻纳甲 rows
    """
    upper, lower = parse_hexagram_trigrams(gua_name)
    upper_bagua = get_bagua_full_name(upper)
    lower_bagua = get_bagua_full_name(lower)
    upper_rows = _NAJIA_TABLE.get(upper_bagua, [])
    lower_rows = _NAJIA_TABLE.get(lower_bagua, [])
    if len(upper_rows) < 6 or len(lower_rows) < 6:
        return None
    return lower_rows[:3] + upper_rows[3:]


# ═══════════════════════════════════════════════════════════════
#  公开查询函数
# ═══════════════════════════════════════════════════════════════

def get_palace_info(gua_name: str) -> dict:
    """
    查询卦的宫位、五行、世应信息

    Parameters:
        gua_name: str — 卦全名（如"乾为天"、"天风姤"）

    Returns:
        dict: {
            "gua_name": "乾为天",
            "palace": "乾宫",
            "palace_wuxing": "金",
            "shi_line": 6,
            "ying_line": 3,
        }
        找不到返回空 dict

    示例:
        info = get_palace_info("乾为天")
        print(info["palace"])  # 乾宫
    """
    entry = _GUA_TABLE.get(gua_name)
    if not entry:
        return {}
    palace, order = entry
    shi, ying = _SHI_YING_MAP[order]
    return {
        "gua_name": gua_name,
        "palace": palace,
        "palace_wuxing": PALACE_WUXING.get(palace, ""),
        "shi_line": shi,
        "ying_line": ying,
    }


def get_najia(gua_name: str) -> list[dict]:
    """
    查询卦的六爻纳甲（天干+地支）

    下卦初/二/三爻使用下卦八纯卦的纳甲，上卦四/五/上爻使用上卦八纯卦的纳甲。

    Args:
        gua_name: 卦全名（如"乾为天"、"天风姤"）

    Returns:
        list[dict]: 6爻纳甲列表，找不到返回空列表
    """
    rows = _build_najia_rows(gua_name)
    if not rows:
        return []

    result = []
    for i, row in enumerate(rows):
        result.append({
            "position": i + 1,
            "name": _LINE_NAMES[i],
            "gan": row["gan"],
            "zhi": row["zhi"],
            "najia": f"{row['gan']}{row['zhi']}",
        })
    return result


# ═══════════════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════════════

def analyze_gua(gua_name: str, day_gan: str | None = None) -> dict:
    """
    根据卦名和日干，排出完整的六爻纳甲信息

    综合执行四步骤：
      1. 查卦宫 → 获取八纯卦纳甲 → 分配每爻天干地支
      2. 确定卦宫五行（金/木/水/火/土）
      3. 以卦宫五行为"我"，与爻支五行比较 → 六亲
      4. 根据日干排六神（day_gan=None 则跳过）

    Parameters:
        gua_name: str — 卦全名（如"乾为天"、"天风姤"）
        day_gan: str | None — 日干（"甲"~"癸"），None 则六神字段为空

    Returns:
        dict: {
            "gua_name": "乾为天",
            "palace": "乾宫",
            "palace_wuxing": "金",
            "shi_line": 6,
            "ying_line": 3,
            "lines": [
                {
                    "position": 1,        # 1-6 从初爻到上爻
                    "name": "初爻",
                    "najia": "甲子",       # 天干+地支
                    "gan": "甲",
                    "zhi": "子",
                    "dizhi_wuxing": "水",  # 地支五行
                    "liuqin": "子孙",      # 六亲（卦宫金生水=我生=子孙）
                    "liushen": "青龙",     # 六神（or None if day_gan=None）
                    "shi_ying": "世",      # "世" / "应" / None
                },
                ...
            ]
        }

    示例:
        result = analyze_gua("乾为天", day_gan="甲")
        for line in result["lines"]:
            print(f"{line['name']} {line['najia']} {line['dizhi_wuxing']} {line['liuqin']} {line['liushen']} {line['shi_ying'] or ''}")
        # 初爻 甲子 水 子孙 青龙 世(?) — 乾卦世在上爻
    """
    # 1. 查卦宫信息
    entry = _GUA_TABLE.get(gua_name)
    if not entry:
        return {"gua_name": gua_name, "error": f"未找到卦名: {gua_name}"}

    palace, order = entry
    palace_wuxing = PALACE_WUXING.get(palace, "")
    shi_line, ying_line = _SHI_YING_MAP[order]

    # 2. 获取纳甲（下卦用下卦八纯卦初/二/三爻，上卦用上卦八纯卦四/五/上爻）
    najia_rows = _build_najia_rows(gua_name)
    if not najia_rows:
        return {"gua_name": gua_name, "error": f"无法计算纳甲: {gua_name}"}

    # 3. 计算六神起始索引
    liushen_start = _RI_GAN_TO_START.get(day_gan) if day_gan else None

    # 4. 逐爻计算
    lines = []
    for i, row in enumerate(najia_rows):
        pos = i + 1  # 1-6 从初爻到上爻
        gan, zhi = row["gan"], row["zhi"]
        dizhi_wx = DIZHI_WUXING.get(zhi, "")
        liuqin = get_liuqin(palace_wuxing, zhi)

        # 六神
        liushen = None
        if liushen_start is not None:
            liushen = _LIUSHEN_ORDER[(liushen_start + i) % 6]

        # 世应标记
        shi_ying = None
        if pos == shi_line:
            shi_ying = "世"
        elif pos == ying_line:
            shi_ying = "应"

        lines.append({
            "position": pos,
            "name": _LINE_NAMES[i],
            "najia": f"{gan}{zhi}",
            "gan": gan,
            "zhi": zhi,
            "dizhi_wuxing": dizhi_wx,
            "liuqin": liuqin,
            "liushen": liushen,
            "shi_ying": shi_ying,
        })

    return {
        "gua_name": gua_name,
        "palace": palace,
        "palace_wuxing": palace_wuxing,
        "shi_line": shi_line,
        "ying_line": ying_line,
        "lines": lines,
    }


# ═══════════════════════════════════════════════════════════════
#  伏神计算
# ═══════════════════════════════════════════════════════════════

def get_fushen(gua_name: str) -> list[dict | None]:
    """
    计算伏神 — 本卦六亲不全时，缺失之六亲伏藏于本宫八纯卦同位爻下

    规则：
      1. 统计本卦中出现的六亲类型
      2. 找出缺失的六亲类型（5种六亲不全者）
      3. 从本宫八纯卦中查找缺失六亲所在的爻位
      4. 该爻位的纳甲/六亲即为伏神，对应到本卦同位爻之下

    Args:
        gua_name: 卦全名（如"天风姤"、"地风升"）

    Returns:
        list: 6元素列表（index 0=初爻..5=上爻），每个元素为 None（无伏神）或
              {"liuqin": "妻财", "najia": "甲寅", "gan": "甲", "zhi": "寅", "dizhi_wuxing": "木"}

    示例:
        fushen = get_fushen("天风姤")
        # 天风姤(乾宫金)：六亲有{父母,子孙,兄弟,官鬼}，缺{妻财}
        # 乾为天二爻甲寅木=妻财 → 伏神在二爻: 妻财-甲寅

        fushen = get_fushen("地风升")
        # 地风升(震宫木)：六亲有{妻财,父母,官鬼}，缺{兄弟,子孙}
        # 震为雷二爻庚寅木=兄弟 → 伏神在二爻: 兄弟-庚寅
        # 震为雷四爻庚午火=子孙 → 伏神在四爻: 子孙-庚午
    """
    # 获取本卦卦宫
    entry = _GUA_TABLE.get(gua_name)
    if not entry:
        return [None] * 6

    palace = entry[0]
    palace_wuxing = PALACE_WUXING.get(palace, "")
    ben_gong_name = get_bagua_full_name(palace[0])

    # 本宫卦（八纯卦）的纳甲
    ben_gong_rows = _build_najia_rows(ben_gong_name)
    if not ben_gong_rows:
        return [None] * 6

    # 当前卦的纳甲
    current_rows = _build_najia_rows(gua_name)
    if not current_rows:
        return [None] * 6

    # 统计本卦中出现的六亲类型
    present_liuqin: set[str] = set()
    for row in current_rows:
        liuqin = get_liuqin(palace_wuxing, row["zhi"])
        if liuqin:
            present_liuqin.add(liuqin)

    # 找出缺失的六亲类型
    all_liuqin = {"父母", "兄弟", "妻财", "子孙", "官鬼"}
    missing_liuqin = all_liuqin - present_liuqin

    # 无缺失 → 无伏神
    if not missing_liuqin:
        return [None] * 6

    # 从本宫卦中查找缺失六亲所在的爻位
    result: list[dict | None] = [None] * 6
    for i in range(6):
        bg_row = ben_gong_rows[i]
        bg_gan, bg_zhi = bg_row["gan"], bg_row["zhi"]
        bg_liuqin = get_liuqin(palace_wuxing, bg_zhi)

        if bg_liuqin in missing_liuqin:
            bg_dizhi_wx = DIZHI_WUXING.get(bg_zhi, "")
            result[i] = {
                "liuqin": bg_liuqin,
                "najia": f"{bg_gan}{bg_zhi}",
                "gan": bg_gan,
                "zhi": bg_zhi,
                "dizhi_wuxing": bg_dizhi_wx,
            }

    return result


# ═══════════════════════════════════════════════════════════════
#  地支六冲 — 子午冲、丑未冲、寅申冲、卯酉冲、辰戌冲、巳亥冲
# ═══════════════════════════════════════════════════════════════

_DIZHI_CHONG: dict[str, str] = {
    "子": "午", "午": "子",
    "丑": "未", "未": "丑",
    "寅": "申", "申": "寅",
    "卯": "酉", "酉": "卯",
    "辰": "戌", "戌": "辰",
    "巳": "亥", "亥": "巳",
}


# ═══════════════════════════════════════════════════════════════
#  卦变反吟八卦对 — 乾↔巽、震↔兑、坎↔离、艮↔坤
#  上下卦互换且为反吟对时，即卦变反吟
# ═══════════════════════════════════════════════════════════════

_BAGUA_FANYIN_PAIR: dict[str, str] = {
    "乾": "巽", "巽": "乾",
    "震": "兑", "兑": "震",
    "坎": "离", "离": "坎",
    "艮": "坤", "坤": "艮",
}


# ═══════════════════════════════════════════════════════════════
#  反吟 / 伏吟 判断
# ═══════════════════════════════════════════════════════════════

def check_hexagram_fanyin_fuyin(gua_name: str) -> dict:
    """
    判断单卦自身的反吟/伏吟（基于上下卦结构，固定属性，不依赖变卦/动爻）

    反吟：上下卦为反吟八卦对（乾↔巽、震↔兑、坎↔离、艮↔坤）
         如天风姤(上乾下巽)、风天小畜(上巽下乾)
    伏吟：上下卦相同（八纯卦），如乾为天、坤为地…

    与 check_fanyin_fuyin() 的区别：
      该函数检查单卦内部结构（固定属性），不比较两卦。
      用于卦类型标签方块显示（与六冲/六合/游魂/归魂同级）。

    Args:
        gua_name: 卦全名（如"乾为天"、"天风姤"）

    Returns:
        dict: {
            "has_fanyin": bool,
            "has_fuyin": bool,
            "fanyin_type": str,   # "全卦" / ""
            "fuyin_type": str,    # "全卦" / ""
        }
    """
    upper, lower = parse_hexagram_trigrams(gua_name)
    if not upper or not lower:
        return {"has_fanyin": False, "has_fuyin": False,
                "fanyin_type": "", "fuyin_type": ""}

    has_fanyin = _BAGUA_FANYIN_PAIR.get(lower, "") == upper
    has_fuyin = (lower == upper)

    return {
        "has_fanyin": has_fanyin,
        "has_fuyin": has_fuyin,
        "fanyin_type": "全卦" if has_fanyin else "",
        "fuyin_type": "全卦" if has_fuyin else "",
    }


def check_fanyin_fuyin(ben_gua_name: str, bian_gua_name: str) -> dict:
    """
    判断本卦→变卦是否存在反吟（地支相冲/卦变反吟）或伏吟（地支相同/卦不变）

    反吟两种：
      爻反吟 — 同位爻地支相冲（如子-午、丑-未…），主反复、冲突
      卦反吟 — 上下卦互换且为反吟八卦对（乾↔巽、震↔兑、坎↔离、艮↔坤）

    伏吟两种：
      爻伏吟 — 同位爻地支相同（如子-子、寅-寅…），主呻吟、停滞
      卦伏吟 — 内/外卦未变（上下卦相同）

    Args:
        ben_gua_name: 本卦全名（如"乾为天"）
        bian_gua_name: 变卦全名（如"坤为地"）

    Returns:
        dict: {
            "has_fanyin": bool,       # 是否存在反吟
            "has_fuyin": bool,        # 是否存在伏吟
            "fanyin_type": str,       # "内卦" / "外卦" / "全卦" / ""
            "fuyin_type": str,        # "内卦" / "外卦" / "全卦" / ""
            "lines": [                # 逐爻分析（index 0=初爻..5=上爻）
                {
                    "fanyin": bool,         # 该爻是否反吟
                    "fuyin": bool,          # 该爻是否伏吟
                    "ben_zhi": str,         # 本卦该爻地支
                    "bian_zhi": str,        # 变卦该爻地支
                },
                ...
            ]
        }

    示例:
        result = check_fanyin_fuyin("乾为天", "坤为地")
        # 乾→坤 非反吟八卦对，地支也非全冲 → has_fanyin=False
    """
    ben_rows = _build_najia_rows(ben_gua_name)
    bian_rows = _build_najia_rows(bian_gua_name)
    if not ben_rows or not bian_rows:
        return {
            "has_fanyin": False, "has_fuyin": False,
            "fanyin_type": "", "fuyin_type": "",
            "lines": [],
        }

    # ── 1. 爻级别反吟/伏吟：逐爻比较地支 ──
    lines = []
    for i in range(6):
        ben_zhi = ben_rows[i]["zhi"]
        bian_zhi = bian_rows[i]["zhi"]
        is_chong = _DIZHI_CHONG.get(ben_zhi, "") == bian_zhi
        is_tong = ben_zhi == bian_zhi
        lines.append({
            "fanyin": is_chong,
            "fuyin": is_tong,
            "ben_zhi": ben_zhi,
            "bian_zhi": bian_zhi,
        })

    nei_yao_fanyin = all(ln["fanyin"] for ln in lines[0:3])
    wai_yao_fanyin = all(ln["fanyin"] for ln in lines[3:6])
    nei_yao_fuyin = all(ln["fuyin"] for ln in lines[0:3])
    wai_yao_fuyin = all(ln["fuyin"] for ln in lines[3:6])

    # ── 2. 卦级别反吟/伏吟：上下卦互换/不变 ──
    ben_upper, ben_lower = parse_hexagram_trigrams(ben_gua_name)
    bian_upper, bian_lower = parse_hexagram_trigrams(bian_gua_name)

    # 卦反吟：本身上下卦是反吟八卦对 且 上下卦互换位置
    _gua_swap_fanyin = (
        ben_upper and ben_lower and bian_upper and bian_lower
        and _BAGUA_FANYIN_PAIR.get(ben_upper, "") == ben_lower  # 本身是反吟对
        and ben_upper == bian_lower and ben_lower == bian_upper  # 互换
    )
    # 八纯卦反吟：乾↔巽、震↔兑、坎↔离、艮↔坤
    _bagua_fanyin = (
        ben_gua_name in BAGUA_SET and bian_gua_name in BAGUA_SET
        and _BAGUA_FANYIN_PAIR.get(ben_upper, "") == bian_lower
    )
    gua_fanyin = _gua_swap_fanyin or _bagua_fanyin

    # 卦伏吟：内/外卦不变
    nei_gua_fuyin = (ben_lower == bian_lower)
    wai_gua_fuyin = (ben_upper == bian_upper)

    # ── 3. 综合判断 ──
    has_any_fanyin = any(ln["fanyin"] for ln in lines) or gua_fanyin
    has_any_fuyin = any(ln["fuyin"] for ln in lines) or nei_gua_fuyin or wai_gua_fuyin

    # 反吟类型
    if nei_yao_fanyin and wai_yao_fanyin:
        fanyin_type = "全卦"
    elif gua_fanyin:
        fanyin_type = "全卦"  # 卦变反吟视为全卦反吟
    elif nei_yao_fanyin:
        fanyin_type = "内卦"
    elif wai_yao_fanyin:
        fanyin_type = "外卦"
    elif has_any_fanyin:
        fanyin_type = "爻"  # 仅个别爻反吟
    else:
        fanyin_type = ""

    # 伏吟类型
    if nei_gua_fuyin and wai_gua_fuyin:
        fuyin_type = "全卦"
    elif nei_yao_fuyin and wai_yao_fuyin:
        fuyin_type = "全卦"
    elif nei_gua_fuyin or nei_yao_fuyin:
        fuyin_type = "内卦"
    elif wai_gua_fuyin or wai_yao_fuyin:
        fuyin_type = "外卦"
    else:
        fuyin_type = ""

    return {
        "has_fanyin": has_any_fanyin,
        "has_fuyin": has_any_fuyin,
        "fanyin_type": fanyin_type,
        "fuyin_type": fuyin_type,
        "lines": lines,
    }
