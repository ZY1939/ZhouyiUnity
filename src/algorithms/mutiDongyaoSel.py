"""
多动爻断法算法 — 根据动爻数量决定应看哪一爻的爻辞
@src/algorithms/动爻断法.md 南师方法
═══════════════════════════════════════════════════════════════
文件职责：纯计算函数，根据卦的阴阳二进制和动爻列表，
         按照南怀瑾《易经杂说》规则返回应参考的爻位及判断依据。
         无 UI 依赖，可被任何起卦流程调用。

规则来源：南怀瑾《易经杂说》第01部分 基础知识（42）— 动爻的断法
═══════════════════════════════════════════════════════════════

返回值含义：
  (0,  "六爻皆静，以本卦卦辞断之")
  (1-6, "一爻动/两爻动/三爻动… → 以XX断之")
  (7,  "六爻皆动，以用九断之")
  (8,  "六爻皆动，以用六断之")
  (9,  "六爻皆动，以变卦彖辞断之")

被哪些文件调用：
  - （后续开发）起卦结果展示、案例保存等需要多动爻判断的场景

用法示例:
    >>> from src.algorithms.mutiDongyaoSel import get_judgment_line
    >>> get_judgment_line("111111", [1])
    (1, '一爻动，以初九爻辞断之')
    >>> get_judgment_line("111111", [1, 5])
    (5, '两爻动，取上动爻九五断之')
    >>> get_judgment_line("111111", [1, 2, 3, 4, 5, 6])
    (7, '六爻皆动，以用九断之')
    >>> get_judgment_line("010101", [])
    (0, '六爻皆静，以本卦卦辞断之')
"""


# ── 爻名映射 ──
_POS_NAMES = ["初", "二", "三", "四", "五", "上"]


def _line_name(binary: str, pos: int) -> str:
    """
    将爻位(1-6)转为卦中爻名，如初九、九二、六三、上六等

    Args:
        binary: 6字符二进制，"1"=阳，"0"=阴（索引0=初爻）
        pos:    爻位 1-6

    Returns:
        str: 如 "初九"、"六三"、"上六"
    """
    yao = "九" if binary[pos - 1] == "1" else "六"
    # 初爻/上爻：位置在前（初九、上六）；二三四五爻：阴阳在前（九二、六三）
    if pos == 1 or pos == 6:
        return f"{_POS_NAMES[pos - 1]}{yao}"
    else:
        return f"{yao}{_POS_NAMES[pos - 1]}"


def _build_reason(binary: str, changing: list[int], n: int, result: int) -> str:
    """
    根据具体动爻情况，智能生成判断依据描述（精简风格）

    Args:
        binary:   6字符二进制
        changing: 已排序去重的动爻列表
        n:        动爻数量
        result:   get_judgment_line 计算出的结果值

    Returns:
        str: 精简判断依据描述
    """
    # ── 0 动爻 ──
    if n == 0:
        return "六爻皆静，以本卦卦辞断之"

    # ── 1 动爻 ──
    if n == 1:
        name = _line_name(binary, changing[0])
        return f"单爻动，以「{name}」爻辞断之"

    # ── 2 动爻 ──
    if n == 2:
        t1, t2 = binary[changing[0] - 1], binary[changing[1] - 1]
        if t1 != t2:
            yin_name = _line_name(binary, changing[0]) if t1 == "0" else _line_name(binary, changing[1])
            return f"双爻动 (一阴一阳)，取阴爻「{yin_name}」断之"
        else:
            upper = _line_name(binary, changing[1])
            tag = "同阳" if t1 == "1" else "同阴"
            return f"双爻动 ({tag})，取上动爻「{upper}」断之"

    # ── 3 动爻 ──
    if n == 3:
        mid = _line_name(binary, changing[1])
        return f"三爻动，取中间爻「{mid}」断之"

    # ── 4 动爻 ──
    if n == 4:
        static_name = _line_name(binary, result)
        return f"四爻动，以下静爻「{static_name}」断之"

    # ── 5 动爻 ──
    if n == 5:
        static_name = _line_name(binary, result)
        return f"五爻动，取静爻「{static_name}」断之"

    # ── 6 动爻 ──
    if n == 6:
        if result == 7:
            return "六爻皆动，以用九断之"
        if result == 8:
            return "六爻皆动，以用六断之"
        return "六爻皆动，以变卦彖辞断之"

    return ""  # fallback（不应到达）


def get_judgment_line(binary: str, changing_lines: list[int]) -> tuple[int, str]:
    """
    根据动爻数量和阴阳属性，返回应参考的爻位及判断依据描述

    规则速查表：
      动爻数  判断规则
      ─────  ──────────────────────────────
      0      以本卦卦辞断之 → 返回 (0, 描述)
      1      以动爻之爻辞断之 → 返回 (爻位, 描述)
      2      一阴一阳取阴爻；同阴/同阳取上动之爻 → 返回 (爻位, 描述)
      3      取中间一爻之爻辞 → 返回 (爻位, 描述)
      4      取下静之爻辞（最靠初爻的静爻）→ 返回 (爻位, 描述)
      5      取静爻之爻辞 → 返回 (爻位, 描述)
      6      乾坤→用九/用六；其余→变卦彖辞 → 返回 (7/8/9, 描述)

    Args:
        binary:         6字符字符串，"1"=阳爻，"0"=阴爻
                        索引0=初爻 .. 索引5=上爻（自下而上）
        changing_lines: 动爻列表，元素为1-6（1=初爻, 6=上爻），
                        已去重但未排序

    Returns:
        tuple[int, str]:
          (0,  "六爻皆静，以本卦卦辞断之")
          (1-6, "一爻动/两爻动… → 以XX断之")
          (7,  "六爻皆动，以用九断之")
          (8,  "六爻皆动，以用六断之")
          (9,  "六爻皆动，以变卦彖辞断之")

    Raises:
        ValueError: binary 长度不为6 或 含非法字符
        ValueError: changing_lines 中有超出1-6范围的值

    用法示例:
        >>> get_judgment_line("111111", [1])
        (1, '一爻动，以初九爻辞断之')
        >>> get_judgment_line("010101", [1, 2])
        (2, '两爻动，取阴爻六二断之')
        >>> get_judgment_line("000000", [1,2,3,4,5,6])
        (8, '六爻皆动，以用六断之')
    """
    # ── 参数校验 ──
    if len(binary) != 6:
        raise ValueError(f"binary 长度必须为 6，实际为 {len(binary)}")
    if not all(c in "01" for c in binary):
        raise ValueError(f"binary 只能包含 '0' 或 '1'，实际为 {binary!r}")

    for ln in changing_lines:
        if not isinstance(ln, int) or ln < 1 or ln > 6:
            raise ValueError(f"changing_lines 中爻位必须为 1-6，实际包含 {ln}")

    changing = sorted(set(changing_lines))
    n = len(changing)

    # ── 0 动爻：六爻安静 → 用本卦卦辞 ──
    if n == 0:
        result = 0

    # ── 1 动爻：以动爻之爻辞断之 ──
    elif n == 1:
        result = changing[0]

    # ── 2 动爻 ──
    elif n == 2:
        yin_yang = [(ln, binary[ln - 1]) for ln in changing]
        types = [t for _, t in yin_yang]
        if types[0] != types[1]:
            # 一阴一阳：取阴爻（'0'）
            for ln, t in yin_yang:
                if t == "0":
                    result = ln
                    break
            else:
                result = changing[0]  # fallback
        else:
            # 同阴或同阳：取上动之爻
            result = max(changing)

    # ── 3 动爻：取中间一爻 ──
    elif n == 3:
        result = changing[1]

    # ── 4 动爻：取下静之爻（最靠初爻的静爻）──
    elif n == 4:
        static = [ln for ln in range(1, 7) if ln not in changing]
        result = static[0]

    # ── 5 动爻：取静爻之爻辞 ──
    elif n == 5:
        static = [ln for ln in range(1, 7) if ln not in changing]
        result = static[0]

    # ── 6 动爻：六爻皆动 ──
    elif n == 6:
        if binary == "111111":
            result = 7
        elif binary == "000000":
            result = 8
        else:
            result = 9

    else:
        result = 0  # fallback（不应到达）

    reason = _build_reason(binary, changing, n, result)
    return result, reason
