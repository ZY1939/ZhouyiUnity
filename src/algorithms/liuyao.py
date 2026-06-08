"""
流人占卜（六爻纳甲）工具 — 根据卦名和日干推演纳甲、六亲、六神

═══════════════════════════════════════════════════════════════
文件职责：纯计算模块，无 UI 依赖。根据卦名和日干，排出完整的
         六爻纳甲信息（纳甲干支、地支五行、六亲、六神、世应）
═══════════════════════════════════════════════════════════════

算法四步骤：
  步骤一：安纳甲 — 根据卦宫继承八纯卦纳甲歌诀，每爻分配天干地支
  步骤二：寻宫定"我" — 确定卦宫五行属性（乾兑=金，震巽=木…）
  步骤三：六亲推演 — 以卦宫五行为"我"，与爻支五行比较定六亲
  步骤四：六神排布 — 根据日干定初爻神，依次排列

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
  get_liuqin(palace_wuxing, dizhi) → str 查六亲

被哪些文件调用：
  - 未来：result_view.py 显示六爻纳甲结果
  - 未来：hexagram_painter.py 绘制完整卦图

依赖：
  - 无外部依赖，所有数据均为模块级常量

用法示例:
  from src.algorithms.liuren import analyze_gua, get_palace_info, get_najia

  result = analyze_gua("乾为天", day_gan="甲")
  for line in result["lines"]:
      print(f"{line['name']}: {line['najia']} {line['liuqin']} {line['liushen']}")
"""

# ═══════════════════════════════════════════════════════════════
#  基础数据：地支五行
# ═══════════════════════════════════════════════════════════════

DIZHI_WUXING: dict[str, str] = {
    "子": "水", "亥": "水",
    "寅": "木", "卯": "木",
    "巳": "火", "午": "火",
    "申": "金", "酉": "金",
    "辰": "土", "戌": "土", "丑": "土", "未": "土",
}

# ═══════════════════════════════════════════════════════════════
#  八卦宫位五行
# ═══════════════════════════════════════════════════════════════

PALACE_WUXING: dict[str, str] = {
    "乾宫": "金",
    "兑宫": "金",
    "震宫": "木",
    "巽宫": "木",
    "坎宫": "水",
    "离宫": "火",
    "坤宫": "土",
    "艮宫": "土",
}

# 卦宫 → 八纯卦名（用于查纳甲）
_PALACE_TO_BAGUA: dict[str, str] = {
    "乾宫": "乾为天",
    "兑宫": "兑为泽",
    "震宫": "震为雷",
    "巽宫": "巽为风",
    "坎宫": "坎为水",
    "离宫": "离为火",
    "坤宫": "坤为地",
    "艮宫": "艮为山",
}

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
#  六亲 — 五行生克规则
# ═══════════════════════════════════════════════════════════════

def get_liuqin(palace_wuxing: str, dizhi: str) -> str:
    """
    以卦宫五行为"我"，与地支五行比较 → 返回六亲

    规则：
      生我者 → 父母    我生者 → 子孙    克我者 → 官鬼
      我克者 → 妻财    同我者 → 兄弟

    Parameters:
        palace_wuxing: str — 卦宫五行（金/木/水/火/土）
        dizhi: str — 地支（子/丑/寅/卯/…）

    Returns:
        str: 六亲名称（父母/子孙/官鬼/妻财/兄弟）

    示例:
        get_liuqin("金", "子")  → "妻财"  (金生水=我生者=子孙？不…
            金生水 → 我生者 → 子孙。但乾卦初爻甲子，六亲是妻财。
            查：乾宫金，子水。金生水 = 我生 → 子孙。
            Wait，用户说乾卦初爻甲子是妻财。那金克木=妻财...
            子不是木。用户原文是"乾宫五行属金。甲寅的地支是寅，五行属木。金克木=妻财"
            子属水，金生水 → 我生者 → 子孙。

            但等等，我需要重新验证。用户的原例是"妻财甲寅木"，说的是
            寅木。乾卦初爻是甲子，不是甲寅。乾卦初爻甲子水，卦宫金生水 → 我生=子孙。

            让我重新查一下。京房纳甲中乾卦初爻甲子，六亲是什么？

            实际上京房纳甲中：
            乾卦(乾宫金)：
            - 初爻甲子(子=水): 金生水 → 我生=子孙 ✓
            - 二爻甲寅(寅=木): 金克木 → 我克=妻财 ✓
            - 三爻甲辰(辰=土): 土生金 → 生我=父母 ✓

            所以实际上乾卦初爻的六亲是"子孙"！

            OK 那让我修正。用户给的例子"妻财甲寅木"是乾卦二爻，不是初爻。

    其实，让我直接实现五行生克关系。
    """
    zhi_wuxing = DIZHI_WUXING.get(dizhi, "")
    if not zhi_wuxing or not palace_wuxing:
        return ""

    if zhi_wuxing == palace_wuxing:
        return "兄弟"

    # 五行相生：金→水→木→火→土→金
    _SHENG_MAP = {"金": "水", "水": "木", "木": "火", "火": "土", "土": "金"}
    # 五行相克：金→木→土→水→火→金
    _KE_MAP = {"金": "木", "木": "土", "土": "水", "水": "火", "火": "金"}

    if _SHENG_MAP.get(palace_wuxing) == zhi_wuxing:
        return "子孙"  # 我生者
    if _SHENG_MAP.get(zhi_wuxing) == palace_wuxing:
        return "父母"  # 生我者
    if _KE_MAP.get(palace_wuxing) == zhi_wuxing:
        return "妻财"  # 我克者
    if _KE_MAP.get(zhi_wuxing) == palace_wuxing:
        return "官鬼"  # 克我者

    return ""


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

    非八纯卦的纳甲继承所属卦宫的八纯卦纳甲（同行位置相同）。

    Parameters:
        gua_name: str — 卦全名（如"乾为天"、"天风姤"）

    Returns:
        list[dict]: 6爻纳甲列表（从初爻到上爻），每个元素为
                    {"position": 1, "name": "初爻", "gan": "甲", "zhi": "子", "najia": "甲子"}
                    找不到返回空列表

    示例:
        najia = get_najia("天风姤")
        for line in najia:
            print(f"{line['name']}: {line['najia']}")
    """
    entry = _GUA_TABLE.get(gua_name)
    if not entry:
        return []
    palace = entry[0]
    bagua_name = _PALACE_TO_BAGUA.get(palace, "")
    najia_rows = _NAJIA_TABLE.get(bagua_name, [])
    if not najia_rows:
        return []

    result = []
    for i, row in enumerate(najia_rows):
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

    # 2. 获取纳甲（继承所属卦宫的八纯卦纳甲）
    bagua_name = _PALACE_TO_BAGUA.get(palace, "")
    najia_rows = _NAJIA_TABLE.get(bagua_name, [])

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
