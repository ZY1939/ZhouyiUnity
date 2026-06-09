"""
先天八卦常量 和 六十四卦索引 — 起卦工具包的基础数据层

═══════════════════════════════════════════════════════════════
文件职责：定义起卦所需的全部常量和结果数据结构
═══════════════════════════════════════════════════════════════

先天八卦数（邵雍先天数）：
    乾1 兑2 离3 震4 巽5 坎6 艮7 坤8

    ☰(乾) ☱(兑) ☲(离) ☳(震) ☴(巽) ☵(坎) ☶(艮) ☷(坤)
     1      2      3      4      5      6      7      8

导出常量：
    XIANTIAN:         先天八卦 数→{name, symbol, element}
    NAME_TO_XIANTIAN: 卦名→先天数 的逆映射
    COIN_TO_YAO:      金钱卦 正面数→(爻名, 是否变爻)
    YARROW_TO_YAO:    蓍草数→(爻名, 是否变爻)  [与金钱卦共用同一套逻辑]
    BINARY_TO_GUA:    六十四卦 binary→卦数据 [运行时由 hexagram_loader 填充]

导出类：
    GuaResult: 起卦结果 dataclass（本卦/变卦/上下卦数/动爻/爻详情）

被哪些文件引用：
    - hexagram_calc.py: 使用 GuaResult、COIN_TO_YAO、YARROW_TO_YAO
    - hexagram_loader.py: 使用 NAME_TO_XIANTIAN、BINARY_TO_GUA
    - hexagram_drawer.py: 间接通过 hexagram_calc._yang_to_xiantian
    - divination_panel.py: 使用 GuaResult、COIN_TO_YAO、YARROW_TO_YAO
    - case_manager.py: 使用 GuaResult
"""
from dataclasses import dataclass, field

# ── 先天八卦：数 → 名/符/象 ──
# 键：先天数(1-8)，值：{name: 卦名, symbol: Unicode卦符, element: 五行/自然象征}
# 用法：XIANTIAN[1]["symbol"] → "☰"
XIANTIAN: dict[int, dict] = {
    1: {"name": "乾", "symbol": "☰", "element": "天"},
    2: {"name": "兑", "symbol": "☱", "element": "泽"},
    3: {"name": "离", "symbol": "☲", "element": "火"},
    4: {"name": "震", "symbol": "☳", "element": "雷"},
    5: {"name": "巽", "symbol": "☴", "element": "风"},
    6: {"name": "坎", "symbol": "☵", "element": "水"},
    7: {"name": "艮", "symbol": "☶", "element": "山"},
    8: {"name": "坤", "symbol": "☷", "element": "地"},
}

# 卦名 → 先天数
# 用法：NAME_TO_XIANTIAN["乾"] → 1
# 由 XIANTIAN 自动推导，hexagram_loader 用它构建(上卦数, 下卦数)→卦ID 索引
NAME_TO_XIANTIAN: dict[str, int] = {v["name"]: k for k, v in XIANTIAN.items()}

# ── 爻象映射：数值 → (爻名, 是否变爻) ──
# 金钱卦：3枚铜钱，计正面数（0-3）
# 用法：COIN_TO_YAO[3] → ("老阳 ⚊○", True)
#   ○ = 变爻标记（老阳变少阴），× = 变爻标记（老阴变少阳）
COIN_TO_YAO: dict[int, tuple[str, bool]] = {
    3: ("老阳 ⚊○", True),   # 三个正面 → 老阳 → 变爻
    0: ("老阴 ⚋×", True),   # 零个正面 → 老阴 → 变爻
    1: ("少阳 ⚊", False),   # 一个正面 → 少阳 → 静爻
    2: ("少阴 ⚋", False),   # 两个正面 → 少阴 → 静爻
}

# 蓍草起卦：50根蓍草分策运算，最终得6/7/8/9
# 用法：YARROW_TO_YAO[9] → ("老阳 ⚊○", True)
# 与金钱卦逻辑完全一致，只是输入数值不同
#   hexagram_calc.calc_six_lines() 中根据 mode 参数选择 COIN_TO_YAO 或 YARROW_TO_YAO
YARROW_TO_YAO: dict[int, tuple[str, bool]] = {
    9: ("老阳 ⚊○", True),   # 老阳 → 变爻
    6: ("老阴 ⚋×", True),   # 老阴 → 变爻
    7: ("少阳 ⚊", False),   # 少阳 → 静爻
    8: ("少阴 ⚋", False),   # 少阴 → 静爻
}

# 六十四卦 binary → 卦数据
# binary 格式："111111"（6位，从下而上，初爻在左/索引0）
# 用法：BINARY_TO_GUA["111111"] → {id:1, name:"乾", full_name:"乾为天", ...}
# 由 hexagram_loader.load_all_gua() 在首次加载时自动填充
BINARY_TO_GUA: dict[str, dict] = {}


@dataclass
class GuaResult:
    """
    起卦结果 — hexagram_calc 各计算函数的统一返回类型

    该 dataclass 在起卦→显示→存储 全链路中传递：
        hexagram_calc 创建 → divination_panel._show_result() 显示 → case_manager.save_case() 存储

    Attributes:
        ben_gua:         本卦数据 dict（来自 content/*.jsonc 的 64 卦条目）
                         包含 id/name/full_name/symbol/binary/upper/lower 等字段
                         示例: {"id":1, "full_name":"乾为天", "symbol":"䷀", "binary":"111111", ...}
        bian_gua:        变卦数据 dict，所有动爻取反后得到的卦
                         无动爻时为 None（六爻皆静则无变卦）
        lower_num:       下卦先天数 (1-8)
        upper_num:       上卦先天数 (1-8)
                         示例: upper_num=1(乾), lower_num=2(兑) → 天泽履
        changing_line:   动爻位置 (1-6, 初爻=1..上爻=6)
                         0 = 无动爻（六爻皆静）
                         多动爻时取第一个（兼容 legacy 代码，优先用 changing_lines）
        changing_lines:  所有动爻列表 [1, 2, ...] 或 [] (空=六爻皆静)
        lines_data:      6爻详情 [(爻名, 数值, 是否变爻), ...]
                         从下而上排列（索引0=初爻, 索引5=上爻）
                         示例: [("少阳 ⚊", 1, False), ("老阴 ⚋×", 0, True), ...]

    使用示例:
        result = calc_three_numbers(123, 456, 789)
        print(result.ben_gua["full_name"])   # "乾为天"
        print(result.changing_lines)          # [3] → 第3爻动
        if result.bian_gua:
            print("→", result.bian_gua["full_name"])  # 变卦名
    """
    ben_gua: dict
    bian_gua: dict | None
    lower_num: int
    upper_num: int
    changing_line: int
    lines_data: list = field(default_factory=list)
    changing_lines: list[int] = field(default_factory=list)
