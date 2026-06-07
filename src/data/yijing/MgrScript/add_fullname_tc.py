#!/usr/bin/env python3
"""
为所有 64 卦 JSONC 文件添加 fullName_tc（繁体全名）字段。

64 卦 full_name（简体）→ fullName_tc（繁体）映射表硬编码于此脚本中。
若文件已有 fullName_tc 且内容非空则跳过。

用法：
    cd src/data/yijing
    python3 MgrScript/add_fullname_tc.py

依赖：
    MgrScript/sync_core.py — load_jsonc / format_by_template
    content/01_乾.jsonc   — 输出格式模板
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
DATA_DIR = os.path.join(PARENT, "content")
TEMPLATE_FILE = os.path.join(DATA_DIR, "01_乾.jsonc")

sys.path.insert(0, HERE)
from sync_core import load_jsonc, format_by_template


# 64 卦简体 full_name → 繁体 fullName_tc
FULLNAME_TC_MAP = {
    "乾为天": "乾爲天",
    "坤为地": "坤爲地",
    "水雷屯": "水雷屯",
    "山水蒙": "山水蒙",
    "水天需": "水天需",
    "天水讼": "天水訟",
    "地水师": "地水師",
    "水地比": "水地比",
    "风天小畜": "風天小畜",
    "天泽履": "天澤履",
    "地天泰": "地天泰",
    "天地否": "天地否",
    "天火同人": "天火同人",
    "火天大有": "火天大有",
    "地山谦": "地山謙",
    "雷地豫": "雷地豫",
    "泽雷随": "澤雷隨",
    "山风蛊": "山風蠱",
    "地泽临": "地澤臨",
    "风地观": "風地觀",
    "火雷噬嗑": "火雷噬嗑",
    "山火贲": "山火賁",
    "山地剥": "山地剝",
    "地雷复": "地雷復",
    "天雷无妄": "天雷無妄",
    "山天大畜": "山天大畜",
    "山雷颐": "山雷頤",
    "泽风大过": "澤風大過",
    "坎为水": "坎爲水",
    "离为火": "離爲火",
    "泽山咸": "澤山咸",
    "雷风恒": "雷風恆",
    "天山遁": "天山遯",
    "雷天大壮": "雷天大壯",
    "火地晋": "火地晉",
    "地火明夷": "地火明夷",
    "风火家人": "風火家人",
    "火泽睽": "火澤睽",
    "水山蹇": "水山蹇",
    "雷水解": "雷水解",
    "山泽损": "山澤損",
    "风雷益": "風雷益",
    "泽天夬": "澤天夬",
    "天风姤": "天風姤",
    "泽地萃": "澤地萃",
    "地风升": "地風升",
    "泽水困": "澤水困",
    "水风井": "水風井",
    "泽火革": "澤火革",
    "火风鼎": "火風鼎",
    "震为雷": "震爲雷",
    "艮为山": "艮爲山",
    "风山渐": "風山漸",
    "雷泽归妹": "雷澤歸妹",
    "雷火丰": "雷火豐",
    "火山旅": "火山旅",
    "巽为风": "巽爲風",
    "兑为泽": "兌爲澤",
    "风水涣": "風水渙",
    "水泽节": "水澤節",
    "风泽中孚": "風澤中孚",
    "雷山小过": "雷山小過",
    "水火既济": "水火既濟",
    "火水未济": "火水未濟",
}


def save_jsonc(path, data):
    """将卦数据按模板格式写入 JSONC 文件。

    功能说明：
        从模板文件（01_乾.jsonc）提取格式骨架，通过 format_by_template
        将数据格式化为与模板一致的 JSONC 文本（缩进、注释、字段顺序完全对齐），
        然后写入目标文件。覆盖写入，调用前应确保 data 字段完整。

    Args:
        path (str): 目标 JSONC 文件的完整路径，如 "/path/to/content/01_乾.jsonc"
        data (dict): 卦的完整数据字典

    Returns:
        None: 直接将格式化文本写入文件，无返回值

    示例:
        >>> data = {"id": 1, "name": "乾", "fullName_tc": "乾爲天"}
        >>> save_jsonc("content/01_乾.jsonc", data)
    """
    template = load_jsonc(TEMPLATE_FILE)
    text = format_by_template(data, template, TEMPLATE_FILE)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    """批量添加 64 卦的 fullName_tc（繁体全名）字段。

    功能说明：
        遍历 content/ 目录下所有 64 卦 JSONC 文件，根据内置的简→繁映射表
        （FULLNAME_TC_MAP）为每卦写入 fullName_tc 字段。已存在非空值的文件
        自动跳过，缺少 full_name 字段或不在映射表中的卦会输出警告并跳过。

    Args:
        无（通过命令行直接运行：python3 MgrScript/add_fullname_tc.py）

    Returns:
        None: 执行结果通过控制台打印输出（更新数/跳过数/缺失数）

    示例:
        $ cd src/data/yijing
        $ python3 MgrScript/add_fullname_tc.py
          ✅ 01_乾.jsonc: 乾为天 → 乾爲天
          ...
          ✅ 已更新 64，跳过 0，缺失 0
    """
    updated = 0
    skipped = 0
    missing = 0

    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith(".jsonc") or fname == "lock.jsonc":
            continue
        filepath = os.path.join(DATA_DIR, fname)
        data = load_jsonc(filepath)

        full_name = data.get("full_name", "")
        if not full_name:
            print(f"  ⚠️  {fname}: 缺少 full_name 字段，跳过")
            missing += 1
            continue

        # 已有内容则跳过
        existing = data.get("fullName_tc", "")
        if existing and existing.strip():
            print(f"  ⏭️  {fname}: fullName_tc 已有值「{existing}」，跳过")
            skipped += 1
            continue

        tc_name = FULLNAME_TC_MAP.get(full_name)
        if not tc_name:
            print(f"  ⚠️  {fname}: full_name「{full_name}」不在映射表中，跳过")
            missing += 1
            continue

        data["fullName_tc"] = tc_name
        save_jsonc(filepath, data)
        updated += 1
        print(f"  ✅ {fname}: {full_name} → {tc_name}")

    print(f"\n✅ 已更新 {updated}，跳过 {skipped}，缺失 {missing}")


if __name__ == "__main__":
    main()
