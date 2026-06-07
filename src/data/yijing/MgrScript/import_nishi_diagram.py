#!/usr/bin/env python3
"""
导入倪师卦图解说 — 解析「倪师卦像图解.md」的图解条目，写入各卦 JSONC 的 nishi.diagram.description 字段。

功能：
  1. 解析 diagram/倪师卦像图解.md，提取 64 卦的卦圖象解条目
  2. 自动备份 content/ → content.bkp.zip
  3. 将解说条目按顺序写入对应 JSONC 的 nishi.diagram.description（数组格式）
  4. 覆盖写入 — 无论 description 原有内容是什么，直接替换

MD 文件格式说明：
  - 每卦以 # **卦名** / ## **卦名** 等标题分隔
  - 图解条目在 ### 卦圖象解 之后，以「一、…」「二、…」编号
  - 条目可能跨多行（有空行分隔），脚本自动拼接

自修改机制：
  MD 章节序号(0-based) 默认映射到以 "{i+1:02d}_" 为前缀的 JSONC 文件。
  若文件被重命名导致前缀匹配失败，脚本会列出所有可用 JSONC 文件，
  询问用户该章节应对应哪个文件，然后将映射写入自身源码的 FILE_OVERRIDES 区域。

用法：
    cd src/data/yijing
    python3 MgrScript/import_nishi_diagram.py

依赖：
    MgrScript/sync_structure.py — JSONC 模板化格式化
    content/01_乾.jsonc       — 输出格式模板
    diagram/倪师卦像图解.md   — 数据来源
"""

import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
DATA_DIR = os.path.join(PARENT, "content")
BACKUP_FILE = os.path.join(PARENT, "content.bkp.zip")
DIAGRAM_DIR = os.path.join(PARENT, "diagram")
MD_FILE = os.path.join(DIAGRAM_DIR, "倪师卦像图解.md")
SELF = os.path.abspath(__file__)

sys.path.insert(0, HERE)
from sync_structure import load_jsonc, format_by_template

TEMPLATE_FILE = os.path.join(DATA_DIR, "01_乾.jsonc")


# ═══════════════════════════════════════════════════════════════
#  === OVERRIDE_START === （此区域会被脚本自动更新）
# ═══════════════════════════════════════════════════════════════
# MD 章节序号(0-based) → JSONC 文件名（用于文件重命名后重定向匹配）
FILE_OVERRIDES = {
    # 示例: 0: "01_乾.jsonc"
}
# ═══════════════════════════════════════════════════════════════
#  === OVERRIDE_END ===
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
#  字段路径配置（可被脚本自修改）
# ═══════════════════════════════════════════════════════════════
#  === FIELD_PATH_START ===
NISHI_DIAGRAM_DESC_PATH = None  # None=自动检测, 如 "nishi.diagram.description"
#  === FIELD_PATH_END ===


def _load_path_config():
    """从自身源码读取 NISHI_DIAGRAM_DESC_PATH 字段路径配置。

    功能说明：
        脚本首次运行时，通过 _resolve_diagram_desc_path() 自动检测或让用户
        选择倪师卦图解 description 的字段路径，然后通过 _save_path_config()
        写入源码。此函数从源码中读取已保存的路径配置，避免每次都重新检测。

    Args:
        无

    Returns:
        str | None: 字段路径字符串（如 "nishi.diagram.description"），
                    若未配置或配置为 None 则返回 None。

    示例:
        >>> path = _load_path_config()
        >>> path
        'nishi.diagram.description'
    """
    with open(SELF, "r", encoding="utf-8") as f:
        src = f.read()
    m = re.search(r'NISHI_DIAGRAM_DESC_PATH\s*=\s*"([^"]*)"', src)
    if m:
        val = m.group(1)
        return val if val != "None" else None
    return None


def _save_path_config(path):
    """将字段路径配置持久化写入自身源码。

    功能说明：
        这是"自修改"机制的一部分。当脚本自动检测或用户手动选择
        description 字段路径后，通过正则替换将路径写入源码中
        NISHI_DIAGRAM_DESC_PATH 变量的赋值行，下次运行无需重新配置。

    Args:
        path (str): 字段路径字符串，如 "nishi.diagram.description"

    Returns:
        None: 无返回值，直接修改自身 .py 源码文件。

    示例:
        >>> _save_path_config("nishi.diagram.description")
        # 源码中 NISHI_DIAGRAM_DESC_PATH = None 被替换为
        # NISHI_DIAGRAM_DESC_PATH = "nishi.diagram.description"
    """
    with open(SELF, "r", encoding="utf-8") as f:
        src = f.read()
    src = re.sub(
        r'NISHI_DIAGRAM_DESC_PATH\s*=\s*[^\n]*',
        f'NISHI_DIAGRAM_DESC_PATH = "{path}"',
        src,
    )
    with open(SELF, "w", encoding="utf-8") as f:
        f.write(src)


def _detect_diagram_desc_path():
    """从模板自动检测倪师卦图解 description 的字段路径。

    功能说明：
        从模板文件（01_乾.jsonc）中自动寻找适合存放卦图解 description
        数组的字段路径。采用两级查找策略：
        1. 优先在 nishi.diagram 下查找字符串数组字段（如 description）
        2. 若结构不匹配，则遍历整个模板的 dict 嵌套，收集所有字符串数组字段
        3. 只有一个候选时自动选择，多个候选时返回 None 交给上层处理

    Args:
        无

    Returns:
        str | None: 检测到的字段路径（如 "nishi.diagram.description"），
                    无法确定唯一路径时返回 None。

    示例:
        >>> path = _detect_diagram_desc_path()
        >>> path
        'nishi.diagram.description'
    """
    template = load_jsonc(TEMPLATE_FILE)
    nishi = template.get("nishi", {})
    if isinstance(nishi, dict):
        diagram = nishi.get("diagram", {})
        if isinstance(diagram, dict):
            for k, v in diagram.items():
                if isinstance(v, list) and (len(v) == 0 or isinstance(v[0], str)):
                    return f"nishi.diagram.{k}"

    # 结构不匹配 — 遍历模板找字符串数组字段
    candidates = []

    def _walk(obj, prefix):
        """递归遍历模板 dict，收集字符串数组字段的路径。"""
        if isinstance(obj, dict):
            for k, v in obj.items():
                path = f"{prefix}.{k}" if prefix else k
                if isinstance(v, list) and (len(v) == 0 or isinstance(v[0], str)):
                    candidates.append(path)
                elif isinstance(v, dict):
                    _walk(v, path)

    _walk(template, "")
    if len(candidates) == 1:
        return candidates[0]
    return None


def _resolve_diagram_desc_path():
    """获取倪师卦图解 description 字段路径，三级决策。

    功能说明：
        这是路径解析的总控函数，采用三级决策链：
        1. 优先读取已保存的配置（_load_path_config）
        2. 其次尝试自动检测模板中的字段路径（_detect_diagram_desc_path），
           检测成功则保存配置供下次使用
        3. 最后让用户从模板中所有数组字段里交互式选择，选择后同样保存配置

    Args:
        无

    Returns:
        str | None: 字段路径字符串（如 "nishi.diagram.description"），
                    无法确定时返回 None。

    示例:
        >>> path = _resolve_diagram_desc_path()
          🔍 自动检测到卦图解路径: nishi.diagram.description
        >>> path
        'nishi.diagram.description'
    """
    path = _load_path_config()
    if path:
        return path

    auto_path = _detect_diagram_desc_path()
    if auto_path:
        print(f"  🔍 自动检测到卦图解路径: {auto_path}")
        _save_path_config(auto_path)
        return auto_path

    # 无法自动检测 — 让用户选择
    template = load_jsonc(TEMPLATE_FILE)
    candidates = []

    def _walk(obj, prefix):
        """递归遍历模板 dict，收集数组字段的路径、大小和元素类型。"""
        if isinstance(obj, dict):
            for k, v in obj.items():
                path = f"{prefix}.{k}" if prefix else k
                if isinstance(v, list):
                    candidates.append((path, f"[{len(v)} items]", type(v[0]).__name__ if v else "?"))
                elif isinstance(v, dict):
                    _walk(v, path)

    _walk(template, "")
    print(f"\n  ⚠️  无法自动检测卦图解字段路径")
    print(f"  模板中的数组字段：")
    for i, (p, size, item_type) in enumerate(candidates, 1):
        print(f"    {i}. {p}  ({size}, 元素类型: {item_type})")
    print(f"  请输入对应序号，或回车跳过：")
    try:
        choice = input("  → ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None

    if not choice:
        return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(candidates):
            path = candidates[idx][0]
            _save_path_config(path)
            return path
    except ValueError:
        pass

    print("  ❌ 无法确定卦图解路径，跳过")
    return None


def _set_nested_path(data, path, value):
    """按点分隔路径设置嵌套字典值，中间层级自动创建。

    功能说明：
        例如路径 "nishi.diagram.description"，会在 data 中逐层创建
        data["nishi"]、data["nishi"]["diagram"]（若不存在），然后
        设置 data["nishi"]["diagram"]["description"] = value。

    Args:
        data (dict): 目标字典（通常是 load_jsonc 返回的卦数据）
        path (str): 点分隔的字段路径，如 "nishi.diagram.description"
        value (any): 要设置的值（可以是 str、list、dict 等任意类型）

    Returns:
        None: 直接修改传入的 data 字典（原地修改）。

    示例:
        >>> data = {}
        >>> _set_nested_path(data, "nishi.diagram.description", ["条目一", "条目二"])
        >>> data
        {'nishi': {'diagram': {'description': ['条目一', '条目二']}}}
    """
    parts = path.split(".")
    current = data
    for i, part in enumerate(parts):
        if i == len(parts) - 1:
            current[part] = value
        else:
            if part not in current:
                current[part] = {}
            current = current[part]


def save_jsonc(path, data):
    """按模板格式保存 JSONC 文件。

    功能说明：
        从模板文件（01_乾.jsonc）加载格式，将 data 按键顺序和缩进风格
        对齐模板后写入指定路径。这确保了所有 JSONC 文件的格式一致。

    Args:
        path (str): 目标 JSONC 文件的绝对路径，例如 ".../content/01_乾.jsonc"
        data (dict): 要保存的卦数据字典

    Returns:
        None: 无返回值，直接写入文件。

    示例:
        >>> data = {"full_name": "乾为天", "nishi": {"diagram": {"description": [...]}}}
        >>> save_jsonc("/path/to/content/01_乾.jsonc", data)
        # 文件被覆盖写入，格式与模板对齐
    """
    template = load_jsonc(TEMPLATE_FILE)
    text = format_by_template(data, template, TEMPLATE_FILE)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def backup():
    """备份整个 content/ 目录为 ZIP 压缩包。

    功能说明：
        在批量修改 JSONC 文件之前，将整个 content/ 目录打包为 ZIP 文件。
        若备份文件已存在，先删除旧的再创建新的。备份文件路径由 BACKUP_FILE
        常量指定（通常是 .../content.bkp.zip）。

        这是防误操作的安全措施：如果导入结果不理想，可以手动解压 ZIP 恢复。

    Args:
        无

    Returns:
        None: 无返回值，打印备份成功信息。

    示例:
        >>> backup()
        ✅ 已备份 → /Users/.../content.bkp.zip
    """
    if os.path.exists(BACKUP_FILE):
        os.remove(BACKUP_FILE)
    shutil.make_archive(BACKUP_FILE.replace(".zip", ""), "zip", DATA_DIR)
    print(f"✅ 已备份 → {BACKUP_FILE}")


def _load_overrides():
    """从自身源码重新加载 FILE_OVERRIDES 映射表。

    功能说明：
        脚本支持"自修改"机制：当 MD 章节序号无法通过默认前缀匹配到
        JSONC 文件时，用户可手动指定。映射被写入脚本源码的 FILE_OVERRIDES
        字典后，此函数重新读取源码获取最新映射。

        使用 ast.literal_eval 安全解析字典，比直接 exec 更安全。

    Args:
        无

    Returns:
        dict: MD 章节序号(0-based int) → JSONC 文件名(str) 的映射字典。
              例如 {0: "01_乾.jsonc", 11: "12_否.jsonc"}
              若解析失败或文件不存在，返回空字典 {}。

    示例:
        >>> overrides = _load_overrides()
        >>> overrides.get(0)
        '01_乾.jsonc'
    """
    import ast
    with open(SELF, "r", encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"FILE_OVERRIDES\s*=\s*(\{[^}]+\})", src, re.DOTALL)
    if m:
        try:
            return ast.literal_eval(m.group(1))
        except (SyntaxError, ValueError):
            pass
    return {}


def _add_override(idx, filename):
    """在自身源码的 OVERRIDE 区域插入一条 MD 章节序号→文件名的映射。

    功能说明：
        这是"自修改"机制的核心函数。当 _find_file 无法通过默认序号前缀
        匹配到 JSONC 文件时，用户可手动指定。此函数将该映射持久化写入
        脚本源码中 FILE_OVERRIDES 字典内部，下次运行直接生效。

        定位策略：在源码行中搜索 === OVERRIDE_START === 和
        === OVERRIDE_END === 标记之间的 FILE_OVERRIDES 字典的
        右花括号前插入新条目。

    Args:
        idx (int): MD 章节序号（0-based），即 64 卦在 MD 文件中的排列顺序。
                   例如 0 表示第 1 卦（乾）
        filename (str): JSONC 文件名（不含路径），如 "01_乾.jsonc"

    Returns:
        bool: True 表示成功插入并保存；False 表示无法定位插入位置。

    示例:
        >>> success = _add_override(11, "12_否.jsonc")
          📝 已将 MD 章节 11 → 12_否.jsonc 写入 FILE_OVERRIDES
        >>> success
        True
    """
    with open(SELF, "r", encoding="utf-8") as f:
        lines = f.readlines()

    mark_start = "=== OVERRIDE_START ==="
    mark_end = "=== OVERRIDE_END ==="
    target_var = "FILE_OVERRIDES = {"
    in_block = False
    target_line = -1
    insert_line = -1

    for i, line in enumerate(lines):
        if mark_start in line:
            in_block = True
            continue
        if mark_end in line:
            in_block = False
            continue
        if in_block and target_var in line:
            target_line = i
        if in_block and target_line >= 0 and i > target_line:
            if line.strip() == "}":
                insert_line = i
                break

    if insert_line < 0:
        print(f"  ⚠️  无法定位 FILE_OVERRIDES 插入位置，跳过自修改")
        return False

    indent = "    "
    new_entry = f'{indent}{idx}: "{filename}",\n'
    lines.insert(insert_line, new_entry)

    with open(SELF, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"  📝 已将 MD 章节 {idx} → {filename} 写入 FILE_OVERRIDES")
    return True


def _find_file(idx):
    """根据 MD 章节序号(0-based)定位对应的 JSONC 文件。

    功能说明：
        这是"文件发现"中枢，采用三级查找策略：
        1. 优先查 FILE_OVERRIDES 覆盖映射（用户之前手动指定过的）
        2. 再按默认前缀匹配：章节 idx=0（第1卦乾）→ 前缀 "01_"，
           idx=1（第2卦坤）→ 前缀 "02_"，以此类推
        3. 前两步都失败时，列出所有可用 JSONC 文件让用户交互式选择，
           并将选择结果写入自修改覆盖映射，下次自动生效

    Args:
        idx (int): MD 章节序号（0-based），即 64 卦在 MD 文件中的排列顺序。
                   例如 0 表示第 1 卦（乾为天），11 表示第 12 卦（天地否）

    Returns:
        str | None: JSONC 文件的绝对路径，匹配失败时返回 None。

    示例:
        >>> filepath = _find_file(0)
        >>> filepath
        '/Users/.../content/01_乾.jsonc'
        >>> _find_file(999)  # 无效序号
          ⚠️  MD 第 1000 章节找不到对应的 JSONC 文件（前缀 1000_）
        None
    """
    overrides = _load_overrides()
    if idx in overrides:
        fname = overrides[idx]
        filepath = os.path.join(DATA_DIR, fname)
        if os.path.exists(filepath):
            return filepath
        print(f"  ⚠️  FILE_OVERRIDES 中 {idx} → {fname} 文件不存在，已忽略该覆盖")

    # 默认前缀匹配
    num = idx + 1
    prefix = f"{num:02d}"
    matches = [f for f in os.listdir(DATA_DIR) if f.startswith(prefix) and f.endswith(".jsonc")]
    if len(matches) == 1:
        return os.path.join(DATA_DIR, matches[0])
    if len(matches) > 1:
        # 多个匹配，用第一个
        return os.path.join(DATA_DIR, matches[0])

    # 匹配失败 — 询问用户
    jsonc_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".jsonc") and f != "lock.jsonc"])
    print(f"\n  ⚠️  MD 第 {num} 章节找不到对应的 JSONC 文件（前缀 {prefix}_）")
    print(f"  可用的 JSONC 文件：")
    for j, fn in enumerate(jsonc_files):
        print(f"    [{j}] {fn}")
    print(f"  请输入对应文件的序号，或回车跳过此章节：")
    try:
        answer = input("  → ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None

    if not answer:
        return None

    try:
        file_idx = int(answer)
        if 0 <= file_idx < len(jsonc_files):
            chosen = jsonc_files[file_idx]
            _add_override(idx, chosen)
            return os.path.join(DATA_DIR, chosen)
    except ValueError:
        pass

    print(f"  ⚠️  无效输入，跳过此章节")
    return None


def parse_md():
    """解析倪师卦像图解 MD 文件，提取 64 卦的图解条目。

    功能说明：
        读取「倪师卦像图解.md」文件，按卦名标题（# **卦名** 格式）分割章节，
        在每个章节的 ### 卦圖象解 之后提取以中文数字编号（一、二、...）的
        图解条目。条目可能跨多行（有空行分隔），脚本自动拼接为完整条目。

        解析步骤：
        1. 按 # **卦名** 标题正则分割全文
        2. 过滤掉非卦章节标题（如 "注:"等）
        3. 在 ### 卦圖象解 之后逐行收集编号条目
        4. 条目之间以中文数字编号（一、二、...）为分隔符

    Args:
        无（MD_FILE 为模块级常量）

    Returns:
        tuple: (results, names) 两个元素的元组。
            results (list[list[str]]): 外层是 64 卦，内层是该卦的图解条目字符串列表。
                                       例如 [["条目一", "条目二"], ...]
            names (list[str]): 64 卦的卦名列表，与 results 一一对应。
                               例如 ["乾为天", "坤为地", ...]

    示例:
        >>> results, names = parse_md()
        >>> len(results)
        64
        >>> names[0]
        '乾为天'
        >>> results[0][:2]  # 乾卦的前两条图解条目
        ['一、第一个条目内容...', '二、第二个条目内容...']
    """
    with open(MD_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    sections = re.split(r"\n(?=#{1,3}\s\*\*[^*]+\*\*\s*\n)", text)

    results = []
    names = []
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue

        h_match = re.match(r"^#{1,3}\s\*\*([^*]+)\*\*", sec)
        if not h_match:
            continue
        title = h_match.group(1).strip()

        if "卦圖象解" in title or title in ("注:", "注："):
            continue

        parts = re.split(r"###\s*卦圖象解\s*\n", sec)
        if len(parts) < 2:
            results.append([])
            names.append(title)
            continue

        body = parts[1]
        cn_nums = "[一二三四五六七八九十]+"
        lines = body.strip().split("\n")
        items = []
        current_item = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if re.match(rf"^{cn_nums}[、,，.]", stripped):
                if current_item:
                    items.append("".join(current_item))
                current_item = [stripped]
            else:
                if re.match(r"^#{1,3}\s", stripped) or re.match(r"^!\[", stripped):
                    break
                if current_item:
                    current_item.append(stripped)

        if current_item:
            items.append("".join(current_item))

        results.append(items)
        names.append(title)

    return results, names


def main():
    """主入口 — 串联解析与写入流程，将倪师卦图解说导入各卦 JSONC 文件。

    功能说明：
        1. 支持 --backup-only 参数：仅备份 content/ 目录，不执行导入
        2. 解析字段路径（_resolve_diagram_desc_path），确定写入目标字段
        3. 调用 parse_md() 解析 64 卦的图解条目
        4. 备份 content/ 目录（防误操作）
        5. 逐卦查找对应 JSONC 文件，将图解条目数组写入
           nishi.diagram.description 字段（覆盖写入）
        6. 打印每卦的更新摘要

        写入策略：
        - 先确保 parent 路径存在（如 nishi.diagram），再调用
          _set_nested_path 写入完整路径
        - 覆盖写入：无论 description 原有内容是什么，直接替换为
          parse_md 返回的 items 数组

    Args:
        无（通过命令行直接运行，可选参数 --backup-only）

    Returns:
        None: 无返回值，直接修改 content/ 下的 JSONC 文件。

    用法:
        cd src/data/yijing
        python3 MgrScript/import_nishi_diagram.py            # 正常导入
        python3 MgrScript/import_nishi_diagram.py --backup-only  # 仅备份
    """
    if len(sys.argv) > 1 and sys.argv[1] == "--backup-only":
        backup()
        return

    # 解析字段路径
    desc_path = _resolve_diagram_desc_path()
    if not desc_path:
        print("  ❌ 无法确定卦图解字段路径，退出")
        return
    # 防御：确保路径是合法的点分隔字段路径，不是残留的格式字符串
    if "{" in desc_path or "}" in desc_path:
        print(f"  ❌ 卦图解路径「{desc_path}」包含非法字符 {{/}}，请检查 NISHI_DIAGRAM_DESC_PATH 配置")
        return
    if not desc_path or desc_path.strip() == "":
        print("  ❌ 卦图解路径为空，请检查 NISHI_DIAGRAM_DESC_PATH 配置")
        return
    print(f"  卦图解路径: {desc_path}")

    # 预计算 parent 路径（用于 setdefault）
    parts = desc_path.split(".")
    parent_path = ".".join(parts[:-1])  # e.g. "nishi.diagram"

    descriptions, names = parse_md()
    print(f"解析到 {len(descriptions)} 条卦图解说")

    if len(descriptions) != 64:
        print(f"⚠️  预期 64 条，实际 {len(descriptions)} 条，请检查 MD 文件")

    backup()

    updated = 0
    for i, items in enumerate(descriptions):
        md_name = names[i] if i < len(names) else f"第{i+1}卦"
        filepath = _find_file(i)
        if not filepath:
            print(f"  ⚠️  {md_name}: 未找到对应文件，跳过")
            continue

        fname = os.path.basename(filepath)
        data = load_jsonc(filepath)

        # 确保 parent 路径存在
        parent_parts = parent_path.split(".")
        current = data
        for p in parent_parts:
            if p not in current:
                current[p] = {}
            current = current[p]
        _set_nested_path(data, desc_path, items)

        save_jsonc(filepath, data)
        updated += 1
        print(f"  ✅ {fname} ← {md_name} ({len(items)} 条目)")

    print(f"\n✅ 已更新 {updated}/{len(descriptions)} 卦")


if __name__ == "__main__":
    main()
