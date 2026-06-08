"""
多动爻断法算法 — 根据动爻数量决定应看哪一爻的爻辞

═══════════════════════════════════════════════════════════════
文件职责：纯计算函数，根据卦的阴阳二进制和动爻列表，
         按照南怀瑾《易经杂说》规则返回应参考的爻位。
         无 UI 依赖，可被任何起卦流程调用。

规则来源：南怀瑾《易经杂说》第01部分 基础知识（42）— 动爻的断法
═══════════════════════════════════════════════════════════════

返回值含义：
  0  — 六爻安静，以本卦卦辞断之
  1-6 — 应以该爻爻辞断之（1=初爻..6=上爻）
  7  — 用九（乾卦六爻皆动）
  8  — 用六（坤卦六爻皆动）
  9  — 以变卦彖辞断之（其余卦六爻皆动）

被哪些文件调用：
  - （后续开发）起卦结果展示、案例保存等需要多动爻判断的场景

用法示例:
    >>> from src.algorithms.mutiDongyaoSel import get_judgment_line
    >>> get_judgment_line("111111", [1])        # 乾卦，初爻动 → 1
    1
    >>> get_judgment_line("111111", [1, 5])     # 乾卦，初九+九五动（皆阳爻）→ 5（上动之爻）
    5
    >>> get_judgment_line("111111", [1, 2, 3, 4, 5, 6])  # 乾卦六爻皆动 → 7（用九）
    7
    >>> get_judgment_line("010101", [])         # 未济卦，六爻安静 → 0（卦辞）
    0
"""


def get_judgment_line(binary: str, changing_lines: list[int]) -> int:
    """
    根据动爻数量和阴阳属性，返回应该参考的爻位

    规则速查表：
      动爻数  判断规则
      ─────  ──────────────────────────────
      0      以本卦卦辞断之 → 返回 0
      1      以动爻之爻辞断之 → 返回该爻位(1-6)
      2      一阴一阳取阴爻；同阴/同阳取上动之爻 → 返回爻位
      3      取中间一爻之爻辞 → 返回爻位
      4      取下静之爻辞（最靠初爻的静爻）→ 返回爻位
      5      取静爻之爻辞 → 返回爻位
      6      乾坤→用九/用六；其余→变卦彖辞

    Args:
        binary:         6字符字符串，"1"=阳爻，"0"=阴爻
                        索引0=初爻 .. 索引5=上爻（自下而上）
        changing_lines: 动爻列表，元素为1-6（1=初爻, 6=上爻），
                        已去重但未排序

    Returns:
        int:
          0  — 六爻安静，用本卦卦辞
          1-6 — 应看爻辞的爻位（1=初爻..6=上爻）
          7  — 用九（乾卦 binary="111111" 六爻皆动）
          8  — 用六（坤卦 binary="000000" 六爻皆动）
          9  — 变卦彖辞（其余卦六爻皆动）

    Raises:
        ValueError: binary 长度不为6 或 含非法字符
        ValueError: changing_lines 中有超出1-6范围的值

    用法示例:
        >>> get_judgment_line("111111", [1])        # 乾卦初爻动
        1
        >>> get_judgment_line("010101", [1, 2])     # 未济卦两爻动，一阴一阳取阴
        2
        >>> get_judgment_line("000000", [1,2,3,4,5,6])  # 坤卦六爻皆动
        8
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
        return 0

    # ── 1 动爻：以动爻之爻辞断之 ──
    if n == 1:
        return changing[0]

    # ── 2 动爻 ──
    if n == 2:
        # 判断两爻的阴阳属性（binary 索引 0=初爻..5=上爻）
        yin_yang = [(ln, binary[ln - 1]) for ln in changing]
        # "阳主过去，阴主未来" — 一阴一阳取阴爻
        types = [t for _, t in yin_yang]
        if types[0] != types[1]:
            # 一阴一阳：取阴爻（'0'）
            for ln, t in yin_yang:
                if t == "0":
                    return ln
        # 同阴或同阳：取上动之爻（line number 大的）
        return max(changing)

    # ── 3 动爻：取中间一爻 ──
    if n == 3:
        return changing[1]  # 排序后取中间（索引1）

    # ── 4 动爻：取下静之爻（最靠初爻的静爻）──
    if n == 4:
        static = [ln for ln in range(1, 7) if ln not in changing]
        return static[0]  # 排序后取最小（最靠近初爻）

    # ── 5 动爻：取静爻之爻辞 ──
    if n == 5:
        static = [ln for ln in range(1, 7) if ln not in changing]
        return static[0]  # 只有一个静爻

    # ── 6 动爻：六爻皆动 ──
    if n == 6:
        if binary == "111111":
            return 7  # 乾卦 → 用九
        if binary == "000000":
            return 8  # 坤卦 → 用六
        return 9  # 其余卦 → 变卦彖辞

    return 0  # fallback（不应到达）
