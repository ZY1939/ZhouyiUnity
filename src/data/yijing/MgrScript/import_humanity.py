#!/usr/bin/env python3
"""
导入倪师人间道 — 解析「倪海厦天纪系列之人间道.md」，写入各卦 JSONC 的字段。

写入字段：
  history[0].description  ← 此卦***（历史案例）
  xiang_ke                ← XXX之課 XXX之象（象课，拆分到 xiang/ke）
  nishi.diagram.content   ← **xxx** 的内容（卦图内容描述，自动创建字段）
  nishi.interpretation    ← 象课之后的解说文字

自修改机制：
  卦名匹配失败时列出可选 JSONC 文件，用户选择后写入文件映射覆盖，
  下次自动生效。

用法：
    cd src/data/yijing
    python3 MgrScript/import_humanity.py

依赖：
    MgrScript/sync_structure.py — JSONC 模板化格式化
    content/01_乾.jsonc       — 输出格式模板
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
DATA_DIR = os.path.join(PARENT, "content")
SELF = os.path.abspath(__file__)

MD_FILE = os.path.join(PARENT, "nishi_ Humanity", "md", "倪海厦天纪系列之人间道.md")

sys.path.insert(0, HERE)
from sync_core import load_jsonc, format_by_template

TEMPLATE_FILE = os.path.join(DATA_DIR, "01_乾.jsonc")


# ═══════════════════════════════════════════════════════════════
#  === OVERRIDE_START === （文件映射覆盖，脚本自动更新）
# ═══════════════════════════════════════════════════════════════
# MD 卦名(清理后) → JSONC 文件名
NAME_OVERRIDES = {
    # 示例: "天地否": "12_否.jsonc"
}
# ═══════════════════════════════════════════════════════════════
#  === OVERRIDE_END ===


# 繁简对照表
T2S = {
    "爲": "为", "為": "为", "師": "师", "風": "风", "澤": "泽", "謙": "谦",
    "隨": "随", "蠱": "蛊", "臨": "临", "觀": "观", "賁": "贲",
    "剝": "剥", "復": "复", "頤": "颐", "過": "过", "恆": "恒",
    "遯": "遁", "壯": "壮", "晉": "晋", "睽": "睽", "蹇": "蹇",
    "損": "损", "益": "益", "姤": "姤", "萃": "萃", "升": "升",
    "困": "困", "井": "井", "革": "革", "鼎": "鼎", "漸": "渐",
    "歸": "归", "豐": "丰", "巽": "巽", "兌": "兑", "渙": "涣",
    "節": "节", "濟": "济", "離": "离", "爾": "尔", "萬": "万",
    "無": "无",
}


def _clean_name(raw):
    """清理 MD 卦名：去 ** 标记、繁转简。

    功能说明：
        倪师 MD 文件中卦名可能包含 Markdown 加粗标记（**）或繁体字。
        此函数将卦名统一为简体、无标记的干净形式，用于后续匹配 JSONC 文件。

    Args:
        raw (str): MD 文件中提取的原始卦名字符串，可能含 ** 标记或繁体字。
                   例如 "**乾爲天**"、"**澤雷隨**"

    Returns:
        str: 清理后的简体卦名字符串。
             例如 "乾为天"、"泽雷随"

    示例:
        >>> _clean_name("**乾爲天**")
        '乾为天'
        >>> _clean_name("**澤雷隨**")
        '泽雷随'
    """
    name = raw.strip()
    name = re.sub(r"\*\*", "", name)
    for t, s in T2S.items():
        name = name.replace(t, s)
    return name


def save_jsonc(path, data):
    """按模板格式保存 JSONC 文件。

    功能说明：
        从模板文件（01_乾.jsonc）加载格式，将 data 按键顺序和缩进风格
        对齐模板后写入指定路径。这确保了所有 JSONC 文件的格式一致。

    Args:
        path (str): 目标 JSONC 文件的绝对路径，例如 ".../content/01_乾.jsonc"
        data (dict): 要保存的卦数据字典，包含 full_name、upper、lower 等字段

    Returns:
        None: 无返回值，直接写入文件。

    示例:
        >>> data = {"full_name": "乾为天", "upper": "乾", "lower": "乾"}
        >>> save_jsonc("/path/to/content/01_乾.jsonc", data)
        # 文件被覆盖写入，格式与模板对齐
    """
    template = load_jsonc(TEMPLATE_FILE)
    text = format_by_template(data, template, TEMPLATE_FILE)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _load_overrides():
    """从自身源码加载 NAME_OVERRIDES 映射表。

    功能说明：
        脚本支持"自修改"机制：当用户手动指定卦名与 JSONC 文件的对应关系后，
        映射会被写入脚本源码的 NAME_OVERRIDES 字典。此函数运行时重新读取
        源码中的映射表，确保每次运行都能获取最新的覆盖映射。

        与直接 import 模块相比，重新读取源码可避免 Python 模块缓存导致的
        旧数据问题。

    Args:
        无

    Returns:
        dict: 清理后的简体卦名 → JSONC 文件名的映射字典。
              例如 {"天地否": "12_否.jsonc", "泽雷随": "17_随.jsonc"}
              若无有效映射或解析失败，返回空字典 {}。

    示例:
        >>> overrides = _load_overrides()
        >>> overrides.get("天地否")
        '12_否.jsonc'
    """
    import ast
    with open(SELF, "r", encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"NAME_OVERRIDES\s*=\s*(\{[^}]+\})", src, re.DOTALL)
    if m:
        try:
            return ast.literal_eval(m.group(1))
        except (SyntaxError, ValueError):
            pass
    return {}


def _add_override(clean_name, filename):
    """在自身源码的 OVERRIDE 区域插入一条新的卦名→文件名映射。

    功能说明：
        这是"自修改"机制的核心函数。当解析器无法自动匹配某个卦名到
        对应的 JSONC 文件时，用户可手动指定。此函数将该映射持久化写入
        脚本源码中 NAME_OVERRIDES 字典内部，下次运行直接生效。

        定位策略：在源码行中搜索 === OVERRIDE_START === 和
        === OVERRIDE_END === 标记之间的 NAME_OVERRIDES 字典的
        右花括号前插入新条目。

    Args:
        clean_name (str): 清理后的简体卦名，如 "天地否"、"泽雷随"
        filename (str): JSONC 文件名（不含路径），如 "12_否.jsonc"

    Returns:
        bool: True 表示成功插入并保存；False 表示无法定位插入位置。

    示例:
        >>> success = _add_override("天地否", "12_否.jsonc")
          📝 已将 天地否 → 12_否.jsonc 写入 NAME_OVERRIDES
        >>> success
        True
    """
    with open(SELF, "r", encoding="utf-8") as f:
        lines = f.readlines()

    mark_start = "=== OVERRIDE_START ==="
    mark_end = "=== OVERRIDE_END ==="
    target_var = "NAME_OVERRIDES = {"
    in_block = False
    target_line = -1
    insert_line = -1

    for i, line in enumerate(lines):
        if mark_start in line:
            in_block = True
        elif mark_end in line:
            in_block = False
        elif in_block and target_var in line:
            target_line = i
        elif in_block and target_line >= 0 and i > target_line:
            if line.strip() == "}":
                insert_line = i
                break

    if insert_line < 0:
        return False

    indent = "    "
    new_entry = f'{indent}"{clean_name}": "{filename}",\n'
    lines.insert(insert_line, new_entry)

    with open(SELF, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"  📝 已将 {clean_name} → {filename} 写入 NAME_OVERRIDES")
    return True


def _find_jsonc(clean_name):
    """根据清理后的卦名定位对应的 JSONC 文件。

    功能说明：
        这是脚本的"文件发现"中枢，采用三级查找策略：
        1. 先查 NAME_OVERRIDES 覆盖映射（用户之前手动指定过的）
        2. 再遍历所有 JSONC 文件，比对 full_name 字段
        3. 前两步都失败时，列出所有可用文件让用户交互式选择，
           并将选择结果写入自修改覆盖映射，下次自动生效

    Args:
        clean_name (str): 清理后的简体卦名，如 "乾为天"、"泽雷随"

    Returns:
        tuple: (filepath, filename) 两个元素的元组。
               filepath (str|None): JSONC 文件的绝对路径，匹配失败时为 None
               filename (str|None): JSONC 文件名（不含路径），匹配失败时为 None

    示例:
        >>> filepath, fname = _find_jsonc("乾为天")
        >>> filepath
        '/Users/.../content/01_乾.jsonc'
        >>> fname
        '01_乾.jsonc'
    """
    overrides = _load_overrides()
    if clean_name in overrides:
        fname = overrides[clean_name]
        filepath = os.path.join(DATA_DIR, fname)
        if os.path.exists(filepath):
            return filepath, fname

    # 遍历 JSONC 文件的 full_name 字段匹配
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith(".jsonc") or fname == "lock.jsonc":
            continue
        data = load_jsonc(os.path.join(DATA_DIR, fname))
        if data.get("full_name", "") == clean_name:
            return os.path.join(DATA_DIR, fname), fname

    # 匹配失败 — 询问用户
    jsonc_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".jsonc") and f != "lock.jsonc"])
    print(f"\n  ⚠️  找不到卦「{clean_name}」对应的 JSONC 文件")
    print(f"  可用的 JSONC 文件：")
    for j, fn in enumerate(jsonc_files):
        d = load_jsonc(os.path.join(DATA_DIR, fn))
        print(f"    [{j}] {fn}  ({d.get('full_name', '?')})")
    print(f"  请输入对应文件的序号，或回车跳过：")
    try:
        answer = input("  → ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None, None
    if not answer:
        return None, None
    try:
        idx = int(answer)
        if 0 <= idx < len(jsonc_files):
            chosen = jsonc_files[idx]
            _add_override(clean_name, chosen)
            return os.path.join(DATA_DIR, chosen), chosen
    except ValueError:
        pass

    return None, None


def parse_md():
    """解析倪师人间道 MD 文件，提取 64 卦的关键字段。

    功能说明：
        读取「倪海厦天纪系列之人间道.md」文件，按 # 卦名 标题分割 64 卦章节，
        从每章中提取以下信息：
        - cigua: 歷史案例描述（"此卦xxx" 开头的内容）
        - bold_text: 卦图内容描述（**加粗标记**包裹的内容）
        - xiang: 象课前半部分（"xxx之課"）
        - ke: 象课后半部分（"xxx之象"）
        - interpretation: 象课之后的解说文字

        解析过程分 4 步：
        1. 识别所有 # 开头的卦名标题行
        2. 用已知的 64 卦名称集合过滤非卦章节
        3. 按行号排序确定每章范围
        4. 逐章提取 cigua/bold_text/xiang/ke/interpretation

    Args:
        无（MD_FILE 为模块级常量）

    Returns:
        list[dict]: 每个卦一个字典，键名和含义如下：
            - clean_name (str): 清理后的简体卦名，如 "乾为天"
            - cigua (str): 历史案例描述文本，如 "此卦xxx..."
            - bold_text (str): 卦图内容描述（已去除 ** 标记）
            - xiang (str): 象课之"课"部分，如 "天地之課"
            - ke (str): 象课之"象"部分，如 "日月之象"
            - interpretation (str): 解说文字，多行文本用 \\n 分隔

    示例:
        >>> results = parse_md()
        解析到 64 个卦章节
        >>> results[0]
        {'clean_name': '乾为天', 'cigua': '此卦...', 'bold_text': '...',
         'xiang': '天地之課', 'ke': '日月之象', 'interpretation': '...'}
    """
    with open(MD_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Step 1: 找出所有 hexagram section 的起止行号
    # 标题行格式: # 卦名（可能含 ** 标记）
    hex_headers = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 匹配 "# 卦名" 开头，排除已知的非卦标题
        m = re.match(r"^#\s+(.+)$", stripped)
        if not m:
            continue
        raw_name = m.group(1).strip()
        # 去掉 ** 标记后判断
        clean = re.sub(r"\*\*", "", raw_name)
        # 排除非卦章节
        skip = {"校", "自", "郭", "徐", "前", "讀", "易", "倪", "人", "目", "乾", "坤", "屯",
                "蒙", "需", "讼", "师", "比", "小", "履", "泰", "否", "同", "大",
                "谦", "豫", "随", "蛊", "临", "观", "噬", "贲", "剥", "复",
                "无", "大畜", "颐", "大过", "坎", "离", "咸", "恒", "遁", "大壮",
                "晋", "明", "家", "睽", "蹇", "解", "损", "益", "夬", "姤",
                "萃", "升", "困", "井", "革", "鼎", "震", "艮", "渐", "归",
                "丰", "旅", "巽", "兑", "涣", "节", "中", "小", "既", "未"}
        # 标题只有一个字 → 跳过（爻辞等）
        if len(clean) <= 2 and clean not in ("未济", "既济", "中孚", "小过", "大过", "大壮", "无妄", "大畜",
                                          "同人", "大有", "小畜", "明夷", "家人", "归妹", "未濟", "既濟"):
            continue
        # 排除爻辞标题 (如 "初九:", "六二:" 等)
        if re.match(r"^(初|九|六|上|用)[一二三四五六九]+", clean):
            continue
        # 跳过单字（大概率是爻序）
        if len(clean) <= 1:
            continue
        # 跳过 "彖曰", "象曰", "卦圖象解" 等内容标题
        if any(kw in clean for kw in ("彖", "象曰", "卦圖", "卦图", "人间道", "人間道", "爻")):
            continue
        hex_headers.append((i, raw_name, clean))

    # Step 2: 过滤掉那些明显不是卦名的标题（只保留在 64 卦列表中的）
    # 构建已知卦名集合（繁简都包含）
    known_guas = {
        "乾为天", "乾爲天", "坤为地", "坤爲地",
        "水雷屯", "山水蒙", "水天需", "天水讼", "天水訟",
        "地水师", "地水師", "水地比", "风天小畜", "風天小畜",
        "天泽履", "天澤履", "地天泰", "天地否",
        "天火同人", "火天大有", "地山谦", "地山謙",
        "雷地豫", "泽雷随", "澤雷隨", "山风蛊", "山風蠱",
        "地泽临", "地澤臨", "风地观", "風地觀",
        "火雷噬嗑", "山火贲", "山火賁", "山地剥", "山地剝",
        "地雷复", "地雷復", "天雷无妄", "天雷無妄",
        "山天大畜", "山雷颐", "山雷頤", "泽风大过", "澤風大過",
        "坎为水", "坎爲水", "离为火", "離爲火",
        "泽山咸", "澤山咸", "雷风恒", "雷風恆",
        "天山遁", "天山遯", "雷天大壮", "雷天大壯",
        "火地晋", "火地晉", "地火明夷",
        "风火家人", "風火家人", "火泽睽", "火澤睽",
        "水山蹇", "雷水解", "山泽损", "山澤損",
        "风雷益", "風雷益", "泽天夬", "澤天夬",
        "天风姤", "天風姤", "泽地萃", "澤地萃",
        "地风升", "地風升", "泽水困", "澤水困",
        "水风井", "水風井", "泽火革", "澤火革",
        "火风鼎", "火風鼎", "震为雷", "震爲雷",
        "艮为山", "艮爲山", "风山渐", "風山漸",
        "雷泽归妹", "雷澤歸妹", "雷火丰", "雷火豐",
        "火山旅", "巽为风", "巽爲風", "兑为泽", "兌爲澤",
        "风水涣", "風水渙", "水泽节", "水澤節",
        "风泽中孚", "風澤中孚", "雷山小过", "雷山小過",
        "水火既济", "水火既濟", "水火未济", "火水未濟",
    }

    # Also add cleaned versions (繁→简, strip **)
    known_cleaned = set()
    for g in known_guas:
        clean = re.sub(r"\*\*", "", g)
        for t, s in T2S.items():
            clean = clean.replace(t, s)
        known_cleaned.add(clean)

    hex_headers = [(i, r, c) for i, r, c in hex_headers
                   if re.sub(r"\*\*", "", r) in known_guas
                   or _clean_name(r) in known_cleaned]

    # Step 3: 按行号排序，确定每段的结束位置
    hex_headers.sort(key=lambda x: x[0])
    sections = []
    for idx, (start, raw_name, clean) in enumerate(hex_headers):
        end = hex_headers[idx + 1][0] if idx + 1 < len(hex_headers) else len(lines)
        sections.append((start, end, raw_name, _clean_name(raw_name)))

    # Step 4: 解析每段
    results = []
    for start, end, raw_name, clean_name in sections:
        sec_lines = lines[start:end]

        result = {
            "clean_name": clean_name,
            "cigua": "",       # 此卦xxx
            "bold_text": "",   # **xxx**
            "xiang": "",       # XXX之課
            "ke": "",          # XXX之象
            "interpretation": "",  # 解说
        }

        # 找 "此卦" — 在卦名之后、卦圖象解之前
        guatu_line = -1
        c_gua_lines = []
        bol_lines = []
        bol_start = -1

        for i, line in enumerate(sec_lines):
            stripped = line.strip()

            # 找 卦圖象解 位置
            if "卦圖" in stripped or "卦图" in stripped:
                guatu_line = i

            # 在此卦到卦圖象解之前搜索此卦
            if guatu_line < 0:
                if "此卦" in stripped:
                    c_gua_lines.append(stripped)

                # 找 ** 内容
                if bol_start < 0 and "**" in stripped:
                    bol_start = i

        # 提取此卦
        if c_gua_lines:
            # 取第一个匹配
            result["cigua"] = c_gua_lines[0].strip()
            # 如果开头是序号（如"1、"），则去掉
            result["cigua"] = re.sub(r"^\d+[\.\、\s]*此卦", "此卦", result["cigua"])

        # 提取 ** 内容
        if bol_start >= 0:
            bold_parts = []
            for i in range(bol_start, min(bol_start + 10, len(sec_lines))):
                stripped = sec_lines[i].strip()
                # 跳过 span/img 行
                if "<span" in stripped or "![" in stripped:
                    continue
                # 收集包含 ** 的行
                if "**" in stripped:
                    bold_parts.append(stripped)
                elif bold_parts:
                    # 如果已经收集到 ** 内容，遇到不含 ** 的普通文本就停止
                    if stripped and not stripped.startswith("#") and not stripped.startswith("!"):
                        break
                    if not stripped:
                        break
            result["bold_text"] = " ".join(bold_parts)
            # 清理：去掉 ** 标记
            result["bold_text"] = re.sub(r"\*\*", "", result["bold_text"])

        # 提取象课和 interpretation
        # 象课格式: XXX之課 XXX之象 (一行)
        for i, line in enumerate(sec_lines):
            stripped = line.strip()
            if "之課" in stripped and "之象" in stripped:
                # 清理行内杂讯
                clean_line = re.sub(r"^[\d\.\s\-\*#]+", "", stripped)
                # 拆分课和象
                m = re.match(r"(.+之課)\s*(.+之象)", clean_line)
                if m:
                    result["xiang"] = m.group(1).strip()
                    result["ke"] = m.group(2).strip()
                else:
                    result["xiang"] = clean_line

                # 象课下一行开始的解说文字 → interpretation
                interp_start = i + 1
                interp_lines = []
                for j in range(interp_start, min(interp_start + 30, len(sec_lines))):
                    istr = sec_lines[j].strip()
                    # 停止条件：遇到 卦圖象解、# 标题、![图片、空行后接短线项
                    if "卦圖" in istr or "卦图" in istr:
                        break
                    if istr.startswith("#"):
                        break
                    if istr.startswith("!["):
                        break
                    if re.match(r"^[\-\*\d]+[\.\、]", istr):
                        break
                    if istr:
                        interp_lines.append(istr)
                    elif interp_lines:
                        # 空行后如果下一行是短线项就停
                        next_j = j + 1
                        if next_j < len(sec_lines) and re.match(r"^[\-\*\d]+[\.\、]", sec_lines[next_j].strip()):
                            break
                        interp_lines.append(istr)
                result["interpretation"] = "\n".join(interp_lines)
                break

        results.append(result)

    return results


def main():
    """主入口 — 串联解析与写入流程，将倪师人间道 MD 内容导入各卦 JSONC 文件。

    功能说明：
        1. 检查 MD 文件是否存在
        2. 调用 parse_md() 解析 64 卦章节
        3. 逐卦查找对应的 JSONC 文件（通过 _find_jsonc）
        4. 将解析出的 cigua、xiang_ke、diagram.content、interpretation
           分别写入 JSONC 的 history[0].description、xiang_ke、
           nishi.diagram.content、nishi.interpretation 字段
        5. 打印每个文件的更新摘要

        写入策略：
        - history[0].description: 若 history 数组不存在则自动创建
        - xiang_ke: 使用 setdefault 确保字段存在
        - nishi.diagram.content: 若 nishi/diagram 层级不存在则逐层创建
        - nishi.interpretation: 同上逐层创建

    Args:
        无（通过命令行直接运行）

    Returns:
        None: 无返回值，直接修改 content/ 下的 JSONC 文件。

    用法:
        cd src/data/yijing
        python3 MgrScript/import_humanity.py
    """
    if not os.path.exists(MD_FILE):
        print(f"❌ MD 文件不存在: {MD_FILE}")
        return

    results = parse_md()
    print(f"解析到 {len(results)} 个卦章节")

    updated = 0
    for r in results:
        clean_name = r["clean_name"]
        filepath, fname = _find_jsonc(clean_name)
        if not filepath:
            print(f"  ⚠️  {clean_name}: 未找到对应 JSONC 文件，跳过")
            continue

        data = load_jsonc(filepath)

        # 写入 history[0].description
        if r["cigua"]:
            if "history" not in data or not data["history"]:
                data["history"] = [{"source": "", "dynasty": "", "description": ""}]
            data["history"][0]["description"] = r["cigua"]

        # 写入 xiang_ke
        if r["xiang"] or r["ke"]:
            data.setdefault("xiang_ke", {})
            if r["xiang"]:
                data["xiang_ke"]["xiang"] = r["xiang"]
            if r["ke"]:
                data["xiang_ke"]["ke"] = r["ke"]

        # 写入 nishi.diagram.content（新字段）
        if r["bold_text"]:
            data.setdefault("nishi", {}).setdefault("diagram", {})
            data["nishi"]["diagram"]["content"] = r["bold_text"]

        # 写入 nishi.interpretation
        if r["interpretation"]:
            data.setdefault("nishi", {})
            data["nishi"]["interpretation"] = r["interpretation"]

        save_jsonc(filepath, data)
        updated += 1
        tag = ""
        if r["cigua"]:
            tag += " history"
        if r["xiang"]:
            tag += " xiang_ke"
        if r["bold_text"]:
            tag += " diagram.content"
        if r["interpretation"]:
            tag += " interpretation"
        print(f"  ✅ {fname} ← {clean_name}{tag}")

    print(f"\n✅ 已更新 {updated}/{len(results)} 卦")


if __name__ == "__main__":
    main()
