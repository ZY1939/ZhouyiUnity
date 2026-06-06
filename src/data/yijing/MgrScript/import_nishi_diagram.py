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
    """从自身源码读取 NISHI_DIAGRAM_DESC_PATH 配置。"""
    with open(SELF, "r", encoding="utf-8") as f:
        src = f.read()
    m = re.search(r'NISHI_DIAGRAM_DESC_PATH\s*=\s*"([^"]*)"', src)
    if m:
        val = m.group(1)
        return val if val != "None" else None
    return None


def _save_path_config(path):
    """将字段路径配置写入自身源码的 FIELD_PATH 区域。"""
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
    """从模板自动检测倪师卦图解的 description 字段路径。
    策略：在 nishi.diagram 下查找字符串数组字段；若结构不对则遍历整个模板。
    返回路径字符串或 None。
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
    """获取倪师卦图解 description 的字段路径。优先配置，其次自动检测，最后询问用户。"""
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
    """按点分隔路径设置嵌套值，中间 dict 自动创建。"""
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
    template = load_jsonc(TEMPLATE_FILE)
    text = format_by_template(data, template, TEMPLATE_FILE)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def backup():
    if os.path.exists(BACKUP_FILE):
        os.remove(BACKUP_FILE)
    shutil.make_archive(BACKUP_FILE.replace(".zip", ""), "zip", DATA_DIR)
    print(f"✅ 已备份 → {BACKUP_FILE}")


def _load_overrides():
    """从自身源码重新加载 FILE_OVERRIDES"""
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
    """在自身源码的 OVERRIDE 区域内插入新条目"""
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
    """根据 MD 章节序号(0-based)定位 JSONC 文件。
    优先级：FILE_OVERRIDES > 默认前缀匹配 > 询问用户
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
    """解析 MD 文件，返回 list of list of str — 每卦的描述条目数组，同时返回卦名列表"""
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
    if len(sys.argv) > 1 and sys.argv[1] == "--backup-only":
        backup()
        return

    # 解析字段路径
    desc_path = _resolve_diagram_desc_path()
    if not desc_path:
        print("  ❌ 无法确定卦图解字段路径，退出")
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
