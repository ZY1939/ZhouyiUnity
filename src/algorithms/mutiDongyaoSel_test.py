"""
mutiDongyaoSel 自动测试脚本
═══════════════════════════════════════════════════════════════
测试 get_judgment_line 所有动爻断法规则的正确性
═══════════════════════════════════════════════════════════════
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from src.algorithms.mutiDongyaoSel import get_judgment_line


def test():
    errors = []

    def check(name, binary, changing, expected):
        result = get_judgment_line(binary, changing)
        ok = "PASS" if result == expected else f"FAIL(got {result}, want {expected})"
        if not ok.startswith("PASS"):
            errors.append(f"  {name}: {ok}")
        print(f"  {ok}: {name}")

    # ═══ 0 动爻：六爻安静 → 卦辞 ═══
    check("0动 六爻安静→卦辞", "111111", [], 0)

    # ═══ 1 动爻 ═══
    check("1动 初爻", "111111", [1], 1)
    check("1动 上爻", "000000", [6], 6)
    check("1动 含重复去重", "111111", [3, 3], 3)

    # ═══ 2 动爻 ═══
    # 随卦 "100011": 初九(阳)+六二(阴)动 → 一阴一阳取阴(2)
    check("2动 一阴一阳取阴(随卦初九+六二)", "100011", [1, 2], 2)
    # 既济卦 "101010": 初九(阳)+九五(阳)动 → 同阳取上(5)
    check("2动 同阳取上(既济初九+九五)", "101010", [1, 5], 5)
    # 坤卦 同阴取上
    check("2动 同阴取上", "000000", [2, 4], 4)

    # ═══ 3 动爻 ═══
    check("3动 取中间(乾九二+九四+九五→九四)", "111111", [2, 4, 5], 4)
    check("3动 无序输入取中间", "111111", [5, 1, 3], 3)

    # ═══ 4 动爻 ═══
    # 未济 "010101": 九二+六三+九四+六五动 → 静:初六+上九 → 下静=1
    check("4动 取下静初爻(未济)", "010101", [2, 3, 4, 5], 1)
    # 初六+六三+九四+六五动 → 静:九二+上九 → 下静=2
    check("4动 取下静二爻(未济)", "010101", [1, 3, 4, 5], 2)

    # ═══ 5 动爻 ═══
    check("5动 取唯一静爻", "111111", [1, 2, 3, 4, 5], 6)
    check("5动 静爻在中间", "111111", [1, 2, 4, 5, 6], 3)

    # ═══ 6 动爻 ═══
    check("6动 乾→用九(7)", "111111", [1, 2, 3, 4, 5, 6], 7)
    check("6动 坤→用六(8)", "000000", [1, 2, 3, 4, 5, 6], 8)
    check("6动 屯→变卦彖辞(9)", "100010", [1, 2, 3, 4, 5, 6], 9)
    check("6动 姤→变卦彖辞(9)", "110111", [1, 2, 3, 4, 5, 6], 9)

    # ═══ 参数校验 ═══
    for bad_binary, bad_lines, desc in [
        ("11111", [], "binary len=5"),
        ("11111X", [], "binary 含非法字符"),
        ("111111", [0], "line=0 超出范围"),
        ("111111", [7], "line=7 超出范围"),
    ]:
        try:
            get_judgment_line(bad_binary, bad_lines)
            errors.append(f"  {desc}: 应抛 ValueError 但没抛")
        except ValueError:
            print(f"  PASS: ValueError → {desc}")

    print()
    if errors:
        for e in errors:
            print(e)
        print(f"\n{len(errors)} 项失败")
        return 1
    else:
        print("全部测试通过!")
        return 0


if __name__ == "__main__":
    sys.exit(test())
