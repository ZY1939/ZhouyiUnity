"""
核心起卦计算 — 纯数学逻辑，不依赖任何 UI 组件

═══════════════════════════════════════════════════════════════
文件职责：将原始输入数值（三位数/六爻值/阴阳列表）转换为 GuaResult
═══════════════════════════════════════════════════════════════

支持四种起卦方式的计算：
    1. calc_three_numbers(n1, n2, n3)      — 三位数起卦（报数模式）
    2. calc_six_lines(lines, mode)          — 六爻起卦（金钱卦/蓍草卦共用）
    3. calc_from_yang_lines(yang, changing)  — 手工阴阳指定
    4. _build_result(lower, upper, changing) — 内部：上下卦先天数 → GuaResult

计算规则：
    - 下卦 = n1 % 8（余0→8坤），上卦 = n2 % 8（余0→8坤）
    - 动爻 = n3 % 6（余0→6爻，即上爻）
    - 变卦 = 本卦 binary 中所有动爻位取反后得到的卦

三爻→先天数 映射表（_yang_to_xiantian）：
    阳=1(—), 阴=0(- -)
    111→乾(1), 110→兑(2), 101→离(3), 100→震(4)
    011→巽(5), 010→坎(6), 001→艮(7), 000→坤(8)

被哪些文件调用：
    - divination_panel.py: _on_calc() → calc_three_numbers / calc_six_lines / calc_from_yang_lines
    - hexagram_drawer.py: _update_gua_name() → _yang_to_xiantian（获取卦名）

依赖：
    - bagua.py: GuaResult, COIN_TO_YAO, YARROW_TO_YAO
    - hexagram_loader.py: get_gua_by_xiantian
"""
from .bagua import GuaResult, COIN_TO_YAO, YARROW_TO_YAO
from .hexagram_loader import get_gua_by_xiantian


def calc_three_numbers(n1: int, n2: int, n3: int) -> GuaResult:
    """三位数起卦

    Parameters:
        n1: 第一个三位数 → 下卦
        n2: 第二个三位数 → 上卦
        n3: 第三个三位数 → 动爻

    Returns:
        GuaResult: 包含本卦、变卦、余数等信息
    """
    # 先天数（1-8），余0对应8坤
    lower_raw = n1 % 8
    upper_raw = n2 % 8
    lower_num = lower_raw if lower_raw != 0 else 8
    upper_num = upper_raw if upper_raw != 0 else 8

    # 动爻（1-6），余0对应第6爻
    changing_raw = n3 % 6
    changing_line = changing_raw if changing_raw != 0 else 6

    return _build_result(lower_num, upper_num, [changing_line] if changing_line > 0 else [])


def calc_six_lines(lines: list[int], mode: str = "coin") -> GuaResult:
    """六爻起卦（金钱卦/蓍草卦共用）

    Parameters:
        lines: 6个数值，从下而上 [初爻, 二爻, 三爻, 四爻, 五爻, 上爻]
               金钱模式: 0-3（正面数）
               蓍草模式: 6/7/8/9
        mode: "coin" 或 "yarrow"

    Returns:
        GuaResult: 包含本卦、变卦信息
    """
    if len(lines) != 6:
        raise ValueError(f"需要6个爻值，得到 {len(lines)}")

    # 映射表
    yao_map = COIN_TO_YAO if mode == "coin" else YARROW_TO_YAO

    # 解析每一爻
    lines_data = []
    changing_lines = []  # 哪些爻是变爻 (1-6)
    lower_yang = []  # 下卦三爻的阴阳 (True=阳)
    upper_yang = []  # 上卦三爻的阴阳

    for i, val in enumerate(lines):
        yao_name, is_changing = yao_map.get(val, (f"未知({val})", False))
        lines_data.append((yao_name, val, is_changing))

        # 判断阴阳：3/9=阳, 0/6=阴, 1/7=阳, 2/8=阴
        is_yang = val in (1, 3, 7, 9)

        if i < 3:
            lower_yang.append(is_yang)
        else:
            upper_yang.append(is_yang)

        if is_changing:
            changing_lines.append(i + 1)  # 1-based

    # 从阴阳序列确定上下卦先天数
    # 下卦：第1-3爻（从下而上）；上卦：第4-6爻
    lower_num = _yang_to_xiantian(lower_yang)  # [初,二,三]
    upper_num = _yang_to_xiantian(upper_yang)  # [四,五,上]

    # 所有变爻逐一取反构建变卦
    return _build_result(lower_num, upper_num, changing_lines, lines_data)


def calc_from_yang_lines(yang_lines: list[bool], changing_indices: list[int] | None = None) -> GuaResult:
    """手工指定：6 个阴阳 + 动爻 → GuaResult

    Parameters:
        yang_lines: 6 个 bool，从下而上 [初爻..上爻]，True=阳 False=阴
        changing_indices: 动爻索引列表 (1-6)，None 或空列表 = 无动爻

    Returns:
        GuaResult
    """
    if len(yang_lines) != 6:
        raise ValueError(f"需要6个爻值，得到 {len(yang_lines)}")

    if changing_indices is None:
        changing_indices = []

    lower_num = _yang_to_xiantian(yang_lines[:3])
    upper_num = _yang_to_xiantian(yang_lines[3:])

    # 构建 lines_data
    lines_data = []
    for i, is_yang in enumerate(yang_lines):
        is_changing = (i + 1) in changing_indices
        if is_yang:
            name = "老阳 ⚊○" if is_changing else "少阳 ⚊"
        else:
            name = "老阴 ⚋×" if is_changing else "少阴 ⚋"
        lines_data.append((name, -1, is_changing))

    return _build_result(lower_num, upper_num, changing_indices, lines_data)


def _yang_to_xiantian(yang_list: list[bool]) -> int:
    """三爻阴阳 → 先天卦数

    爻序: [初, 二, 三] 从下而上
    阳=1(—), 阴=0(- -)

    八卦:
        乾☰ 111=1  兑☱ 110=2  离☲ 101=3  震☳ 100=4
        巽☴ 011=5  坎☵ 010=6  艮☶ 001=7  坤☷ 000=8
    """
    binary = "".join("1" if y else "0" for y in yang_list)
    mapping = {
        "111": 1,  # 乾
        "110": 2,  # 兑
        "101": 3,  # 离
        "100": 4,  # 震
        "011": 5,  # 巽
        "010": 6,  # 坎
        "001": 7,  # 艮
        "000": 8,  # 坤
    }
    return mapping.get(binary, 8)


def _build_result(lower_num: int, upper_num: int, changing_lines: list[int] | None = None,
                  lines_data: list | None = None) -> GuaResult:
    """根据上下卦先天数和动爻构建 GuaResult

    Parameters:
        lower_num: 下卦先天数 (1-8)
        upper_num: 上卦先天数 (1-8)
        changing_lines: 所有动爻位置列表 [1..6]，空列表或 None = 六爻皆静
        lines_data: 6爻详情
    """
    if changing_lines is None:
        changing_lines = []

    ben_gua = get_gua_by_xiantian(upper_num, lower_num)
    bian_gua = None

    if changing_lines and ben_gua:
        # 所有动爻逐一取反 → 变卦
        binary = ben_gua.get("binary", "000000")
        # binary 从下而上（初爻在左，索引0）
        new_binary = list(binary)
        for cl in changing_lines:
            idx = cl - 1  # 0-based
            new_binary[idx] = "0" if binary[idx] == "1" else "1"
        new_binary = "".join(new_binary)

        new_lower_yang = [c == "1" for c in new_binary[:3]]
        new_upper_yang = [c == "1" for c in new_binary[3:]]
        new_lower_num = _yang_to_xiantian(new_lower_yang)
        new_upper_num = _yang_to_xiantian(new_upper_yang)

        bian_gua = get_gua_by_xiantian(new_upper_num, new_lower_num)

    if lines_data is None:
        lines_data = []

    return GuaResult(
        ben_gua=ben_gua or {},
        bian_gua=bian_gua,
        lower_num=lower_num,
        upper_num=upper_num,
        changing_line=changing_lines[0] if changing_lines else 0,
        changing_lines=sorted(changing_lines),
        lines_data=lines_data,
    )
