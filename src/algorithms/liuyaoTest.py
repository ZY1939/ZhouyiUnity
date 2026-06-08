#!/usr/bin/env python3
"""
六爻纳甲占卜 — 完整测试脚本

测试范围：
  1. 模块导入 + 基础数据完整性
  2. 64卦卦宫归属（全覆盖）
  3. 世应位置规则（八纯/一世~五世/游魂/归魂）
  4. 纳甲继承（非八纯卦继承本宫八纯卦）
  5. 六亲计算（26组五行生克）
  6. 六神排布（10天干 × 6爻序列）
  7. 完整排盘示例（乾为天 / 天风姤 / 离为火）
  8. 边界情况

用法：
  python3 test_liuren.py          # 直接运行
  bash 一键测试-六爻纳甲.command   # macOS 双击
"""

import sys
import os

# 确保项目根在路径中
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ═══════════════════════════════════════════════════════════════
#  终端颜色
# ═══════════════════════════════════════════════════════════════

_C = {
    "R": "\033[91m",   # 红
    "G": "\033[92m",   # 绿
    "Y": "\033[93m",   # 黄
    "B": "\033[94m",   # 蓝
    "C": "\033[96m",   # 青
    "M": "\033[95m",   # 紫
    "W": "\033[97m",   # 白
    "D": "\033[90m",   # 灰
    "X": "\033[0m",    # 重置
}

def _c(color: str, text: str) -> str:
    """包裹 ANSI 颜色"""
    return f"{_C.get(color, '')}{text}{_C['X']}"

_OK = _c("G", "✅")
_FAIL = _c("R", "❌")
_SEP = _c("D", "─" * 64)
_SEP2 = _c("D", "═" * 64)


# ═══════════════════════════════════════════════════════════════
#  辅助：打印卦线表格
# ═══════════════════════════════════════════════════════════════

def _print_gua_table(result: dict):
    """以对齐表格形式打印 analyze_gua 结果"""
    lines = result.get("lines", [])
    if not lines:
        return

    hdr = f"  {'爻位':<6} {'纳甲':<8} {'地支五行':<8} {'六亲':<6} {'六神':<6} {'世应':<4}"
    print(hdr)
    print(f"  {_c('D', '─' * 48)}")

    for line in lines:
        ls = line["liushen"] or "—"
        sy = line["shi_ying"] or ""
        sy_color = "B" if sy == "世" else ("C" if sy == "应" else "D")
        print(
            f"  {line['name']:<6} "
            f"{_c('Y', line['najia']):<10}"
            f"{line['dizhi_wuxing']:<8} "
            f"{_c('M', line['liuqin']):<8}"
            f"{_c('G', ls):<8}"
            f"{_c(sy_color, sy):<4}"
        )


# ═══════════════════════════════════════════════════════════════
#  测试用例
# ═══════════════════════════════════════════════════════════════

def main():
    from src.algorithms.liuyao import (
        analyze_gua, get_palace_info, get_najia, get_liuqin,
        DIZHI_WUXING, PALACE_WUXING, _GUA_TABLE, _NAJIA_TABLE,
        _LIUSHEN_ORDER, _SHI_YING_MAP, _RI_GAN_TO_START,
    )

    passed = 0
    failed = 0
    errors = []

    def check(cond, msg):
        nonlocal passed, failed
        if cond:
            passed += 1
        else:
            failed += 1
            errors.append(msg)

    # ── 1. 基础数据完整性 ──
    print(f"\n{_c('W', '╔══════════════════════════════════════════════╗')}")
    print(f"{_c('W', '║')}  {_c('B', '1. 基础数据完整性')}" + " " * 35 + f"{_c('W', '║')}")
    print(f"{_c('W', '╚══════════════════════════════════════════════╝')}")

    check(len(DIZHI_WUXING) == 12, f"地支五行应有12条目, 当前{len(DIZHI_WUXING)}")
    print(f"  {_OK} 地支五行: {len(DIZHI_WUXING)}条目")

    check(len(PALACE_WUXING) == 8, f"卦宫五行应有8条目, 当前{len(PALACE_WUXING)}")
    print(f"  {_OK} 卦宫五行: {len(PALACE_WUXING)}条目")

    check(len(_NAJIA_TABLE) == 8, f"八纯卦纳甲应有8卦, 当前{len(_NAJIA_TABLE)}")
    for name, rows in _NAJIA_TABLE.items():
        check(len(rows) == 6, f"{name}纳甲应有6爻")
    print(f"  {_OK} 八纯卦纳甲: 8卦×6爻 完整")

    check(len(_GUA_TABLE) == 64, f"64卦表应有64条目, 当前{len(_GUA_TABLE)}")
    print(f"  {_OK} 64卦宫位表: {len(_GUA_TABLE)}条目")

    check(len(_SHI_YING_MAP) == 8, f"世应规则应有8条目")
    print(f"  {_OK} 世应规则: {len(_SHI_YING_MAP)}条目 (八纯/一世~五世/游魂/归魂)")

    check(len(_LIUSHEN_ORDER) == 6, f"六神列表应有6个")
    print(f"  {_OK} 六神列表: {' → '.join(_LIUSHEN_ORDER)}")

    check(len(_RI_GAN_TO_START) == 10, f"日干映射应有10条目")
    print(f"  {_OK} 日干映射: {len(_RI_GAN_TO_START)}条目")

    # ── 2. 64卦全覆盖 ──
    print(f"\n{_c('W', '╔══════════════════════════════════════════════╗')}")
    print(f"{_c('W', '║')}  {_c('B', '2. 64卦宫位全覆盖验证')}" + " " * 30 + f"{_c('W', '║')}")
    print(f"{_c('W', '╚══════════════════════════════════════════════╝')}")

    palaces = {}
    for gua_name, (palace, order) in _GUA_TABLE.items():
        check(1 <= order <= 8, f"{gua_name} 序号异常: {order}")
        check(palace in PALACE_WUXING, f"{gua_name} 卦宫未知: {palace}")
        info = get_palace_info(gua_name)
        check(info["palace"] == palace, f"{gua_name} get_palace_info 卦宫不匹配")
        palaces.setdefault(palace, []).append(gua_name)

    for palace in ["乾宫","坎宫","艮宫","震宫","巽宫","离宫","坤宫","兑宫"]:
        wuxing = PALACE_WUXING[palace]
        gua_list = " ".join(palaces.get(palace, []))
        print(f"  {_c('M', palace)}({_c('Y', wuxing)}): {gua_list}")

    # ── 3. 世应位置 ──
    print(f"\n{_c('W', '╔══════════════════════════════════════════════╗')}")
    print(f"{_c('W', '║')}  {_c('B', '3. 世应位置验证')}" + " " * 39 + f"{_c('W', '║')}")
    print(f"{_c('W', '╚══════════════════════════════════════════════╝')}")

    shiying_tests = [
        ("乾为天", 6, 3, "八纯卦"),
        ("天风姤", 1, 4, "一世卦"),
        ("天山遁", 2, 5, "二世卦"),
        ("天地否", 3, 6, "三世卦"),
        ("风地观", 4, 1, "四世卦"),
        ("山地剥", 5, 2, "五世卦"),
        ("火地晋", 4, 1, "游魂卦"),
        ("火天大有", 3, 6, "归魂卦"),
    ]
    for name, exp_shi, exp_ying, category in shiying_tests:
        info = get_palace_info(name)
        check(info["shi_line"] == exp_shi, f"{name} 世爻期望{exp_shi}得{info['shi_line']}")
        check(info["ying_line"] == exp_ying, f"{name} 应爻期望{exp_ying}得{info['ying_line']}")
        print(f"  {_OK} {name} ({category}): 世{info['shi_line']} 应{info['ying_line']}")

    # ── 4. 纳甲继承 ──
    print(f"\n{_c('W', '╔══════════════════════════════════════════════╗')}")
    print(f"{_c('W', '║')}  {_c('B', '4. 纳甲继承验证')}" + " " * 39 + f"{_c('W', '║')}")
    print(f"{_c('W', '╚══════════════════════════════════════════════╝')}")

    # 每宫抽一个非八纯卦验证
    najia_samples = [
        ("乾宫", "天风姤"),
        ("坎宫", "水雷屯"),
        ("艮宫", "山火贲"),
        ("震宫", "雷地豫"),
        ("巽宫", "风天小畜"),
        ("离宫", "火山旅"),
        ("坤宫", "地雷复"),
        ("兑宫", "泽水困"),
    ]
    for palace, gua_name in najia_samples:
        bagua_name = {v: k for k, v in {
            "乾宫": "乾为天", "坎宫": "坎为水", "艮宫": "艮为山", "震宫": "震为雷",
            "巽宫": "巽为风", "离宫": "离为火", "坤宫": "坤为地", "兑宫": "兑为泽",
        }.items()}.get(palace, "") or {
            "乾宫": "乾为天", "坎宫": "坎为水", "艮宫": "艮为山", "震宫": "震为雷",
            "巽宫": "巽为风", "离宫": "离为火", "坤宫": "坤为地", "兑宫": "兑为泽",
        }[palace]

        bagua_najia = get_najia(bagua_name)
        gua_najia = get_najia(gua_name)
        for i in range(6):
            check(
                bagua_najia[i]["gan"] == gua_najia[i]["gan"] and
                bagua_najia[i]["zhi"] == gua_najia[i]["zhi"],
                f"{gua_name} 第{i+1}爻纳甲与{bagua_name}不一致"
            )
        print(f"  {_OK} {gua_name} → 继承{bagua_name}纳甲")

    # ── 5. 六亲计算 ──
    print(f"\n{_c('W', '╔══════════════════════════════════════════════╗')}")
    print(f"{_c('W', '║')}  {_c('B', '5. 六亲计算（五行生克）')}" + " " * 30 + f"{_c('W', '║')}")
    print(f"{_c('W', '╚══════════════════════════════════════════════╝')}")

    liuqin_cases = [
        # (卦宫五行, 地支, 期望六亲, 关系说明)
        ("金", "子", "子孙", "金生水=我生"),
        ("金", "寅", "妻财", "金克木=我克"),
        ("金", "辰", "父母", "土生金=生我"),
        ("金", "午", "官鬼", "火克金=克我"),
        ("金", "申", "兄弟", "金=金同我"),
        ("金", "戌", "父母", "土生金=生我"),
        ("水", "寅", "子孙", "水生木=我生"),
        ("水", "午", "妻财", "水克火=我克"),
        ("水", "辰", "官鬼", "土克水=克我"),
        ("水", "申", "父母", "金生水=生我"),
        ("水", "子", "兄弟", "水=水同我"),
        ("木", "子", "父母", "水生木=生我"),
        ("木", "午", "子孙", "木生火=我生"),
        ("木", "申", "官鬼", "金克木=克我"),
        ("木", "辰", "妻财", "木克土=我克"),
        ("木", "寅", "兄弟", "木=木同我"),
        ("火", "子", "官鬼", "水克火=克我"),
        ("火", "午", "兄弟", "火=火同我"),
        ("火", "辰", "子孙", "火生土=我生"),
        ("火", "申", "妻财", "火克金=我克"),
        ("火", "寅", "父母", "木生火=生我"),
        ("土", "子", "妻财", "土克水=我克"),
        ("土", "午", "父母", "火生土=生我"),
        ("土", "辰", "兄弟", "土=土同我"),
        ("土", "申", "子孙", "土生金=我生"),
        ("土", "寅", "官鬼", "木克土=克我"),
    ]
    for wx, zhi, expected, desc in liuqin_cases:
        result = get_liuqin(wx, zhi)
        check(result == expected, f"{wx}+{zhi}: 期望{expected}({desc}) 得{result}")

    # 按五行分组展示
    print(f"  {'卦宫五行':<8} {'地支':<6} {'关系':<14} {'六亲':<6}")
    print(f"  {_c('D', '─' * 40)}")
    shown = set()
    for wx, zhi, expected, desc in liuqin_cases:
        key = (wx, desc)
        if key not in shown:
            shown.add(key)
            print(f"  {_c('M', wx):<10} {_c('Y', zhi):<8} {_c('D', desc):<16} {_c('G', expected):<8}")
    print(f"  {_OK} 全部26组六亲计算正确")

    # ── 6. 六神排布 ──
    print(f"\n{_c('W', '╔══════════════════════════════════════════════╗')}")
    print(f"{_c('W', '║')}  {_c('B', '6. 六神排布（日干→初爻→全序列）')}" + " " * 19 + f"{_c('W', '║')}")
    print(f"{_c('W', '╚══════════════════════════════════════════════╝')}")

    for gan in ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]:
        start_idx = _RI_GAN_TO_START[gan]
        result = analyze_gua("乾为天", day_gan=gan)
        seq = [l["liushen"] for l in result["lines"]]
        check(seq[0] == _LIUSHEN_ORDER[start_idx], f"{gan}日初爻应为{_LIUSHEN_ORDER[start_idx]}")
        for i, s in enumerate(seq):
            expected = _LIUSHEN_ORDER[(start_idx + i) % 6]
            check(s == expected, f"{gan}日第{i+1}爻应为{expected}得{s}")
        seq_str = " → ".join(seq)
        print(f"  {_OK} {gan}日: {seq_str}")

    # ── 7. 完整排盘示例 ──
    print(f"\n{_c('W', '╔══════════════════════════════════════════════╗')}")
    print(f"{_c('W', '║')}  {_c('B', '7. 完整排盘示例')}" + " " * 38 + f"{_c('W', '║')}")
    print(f"{_c('W', '╚══════════════════════════════════════════════╝')}")

    # 7.1 乾为天 (甲日)
    result = analyze_gua("乾为天", day_gan="甲")
    print(f"\n  {_c('W', '▎乾为天')}  {_c('D', '乾宫·金')}  世{result['shi_line']}应{result['ying_line']}  日干甲")
    _print_gua_table(result)

    # 7.2 天风姤 (庚日)
    result = analyze_gua("天风姤", day_gan="庚")
    print(f"\n  {_c('W', '▎天风姤')}  {_c('D', '乾宫·金')}  世{result['shi_line']}应{result['ying_line']}  日干庚（初爻白虎）")
    _print_gua_table(result)

    # 7.3 离为火 (丙日)
    result = analyze_gua("离为火", day_gan="丙")
    print(f"\n  {_c('W', '▎离为火')}  {_c('D', '离宫·火')}  世{result['shi_line']}应{result['ying_line']}  日干丙（初爻朱雀）")
    _print_gua_table(result)

    # 7.4 坎为水 (壬日)
    result = analyze_gua("坎为水", day_gan="壬")
    print(f"\n  {_c('W', '▎坎为水')}  {_c('D', '坎宫·水')}  世{result['shi_line']}应{result['ying_line']}  日干壬（初爻玄武）")
    _print_gua_table(result)

    # 7.5 坤为地 (戊日)
    result = analyze_gua("坤为地", day_gan="戊")
    print(f"\n  {_c('W', '▎坤为地')}  {_c('D', '坤宫·土')}  世{result['shi_line']}应{result['ying_line']}  日干戊（初爻勾陈）")
    _print_gua_table(result)

    # ── 8. 边界情况 ──
    print(f"\n{_c('W', '╔══════════════════════════════════════════════╗')}")
    print(f"{_c('W', '║')}  {_c('B', '8. 边界情况')}" + " " * 43 + f"{_c('W', '║')}")
    print(f"{_c('W', '╚══════════════════════════════════════════════╝')}")

    r = analyze_gua("不存在的卦")
    check("error" in r, "未知卦名应返回error")
    print(f"  {_OK} 未知卦名 → 返回 error 信息")

    r = get_palace_info("xxxx")
    check(r == {}, "未知卦名 get_palace_info 应返回空dict")
    print(f"  {_OK} 未知卦名 get_palace_info → 空dict")

    r = get_najia("xxxx")
    check(r == [], "未知卦名 get_najia 应返回空list")
    print(f"  {_OK} 未知卦名 get_najia → 空list")

    r = analyze_gua("天风姤", day_gan=None)
    check(all(l["liushen"] is None for l in r["lines"]), "day_gan=None 时六神应全为None")
    print(f"  {_OK} day_gan=None → 六神全部为 None")

    # 验证所有64卦都能正常排盘
    for gua_name in _GUA_TABLE:
        r = analyze_gua(gua_name, day_gan="甲")
        check(len(r["lines"]) == 6, f"{gua_name} 应有6爻")
        for line in r["lines"]:
            check(line["liuqin"] in ["父母","子孙","官鬼","妻财","兄弟"], f"{gua_name} {line['name']} liuqin异常")
            check(line["dizhi_wuxing"] in ["金","木","水","火","土"], f"{gua_name} {line['name']} wuxing异常")
            check(line["liushen"] in _LIUSHEN_ORDER, f"{gua_name} {line['name']} liushen异常")
            check(line["najia"], f"{gua_name} {line['name']} najia为空")
    print(f"  {_OK} 64卦全覆盖排盘验证 (每卦6爻 × 六亲/五行/六神/纳甲)")

    # ── 总结 ──
    print(f"\n{_SEP2}")
    print(f"  {_c('W', '测试结果:')}  总计 {passed + failed} 项  "
          f"{_c('G', f'{passed} 通过')}  "
          f"{_c('R', f'{failed} 失败') if failed else ''}")
    if failed:
        print(f"\n  {_c('R', '失败项:')}")
        for err in errors:
            print(f"    {_c('R', '✗')} {err}")
    else:
        print(f"\n  {_c('G', '🎉 全部测试通过！六爻纳甲模块工作正常。')}")
    print(f"{_SEP2}\n")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
