#!/usr/bin/env python3
"""
易经数据库结构同步脚本（格式刷） — 以指定卦文件为模板，将其字段结构同步到其他卦文件。

功能：
  1. 结构同步 — 确保所有 64 卦 JSONC 文件拥有与模板一致的字段路径
  2. 字段清理 — 删除目标文件中模板不存在的字段（有内容的字段保留以防误删）
  3. 字段排序 — 按模板的字段顺序重新排列
  4. 格式刷新 — 输出格式严格对齐模板（缩进、注释、数组换行等）

用法：
    cd src/data/yijing
    python3 MgrScript/sync_structure.py              # 默认以 01_乾.jsonc 为模板
    python3 MgrScript/sync_structure.py 02_坤.jsonc  # 以 02_坤.jsonc 为模板

说明：
  - 运行前自动备份 content/ → content.bkp.zip
  - 有内容的字段若不在模板中会被保留并发出警告
  - 可反复运行，已同步的文件仅刷新格式，不会重复修改

依赖：
    content/01_乾.jsonc — 默认模板文件（其他文件以此为基准对齐）
    content/*.jsonc     — 64 卦数据文件
"""

import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
SCRIPT_DIR = os.path.join(PARENT, "content")
BACKUP_FILE = os.path.join(PARENT, "content.bkp.zip")
DEFAULT_TEMPLATE = "01_乾.jsonc"

sys.path.insert(0, HERE)
from lock_utils import sync_lock_structure


def load_jsonc(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    cleaned = re.sub(r"//.*", "", raw)
    return json.loads(cleaned)


def extract_structure(obj, prefix=()):
    """递归提取数据结构骨架：{(path, tuple): example_value}"""
    structure = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = prefix + (k,)
            if isinstance(v, dict):
                structure.update(extract_structure(v, path))
            elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                structure[path] = "[]"
                structure.update(extract_structure(v[0], path + ("[*]",)))
            else:
                structure[path] = v
    return structure


def _empty_for(val):
    if isinstance(val, list):
        return []
    if isinstance(val, dict):
        return {}
    if val == "[]":
        return [{}]
    if isinstance(val, bool):
        return False
    if isinstance(val, (int, float)):
        return None
    return ""


def _build_level_keys(structure):
    lk = {}
    for path in structure:
        for i in range(len(path)):
            prefix = path[:i]
            if prefix not in lk:
                lk[prefix] = set()
            key = path[i]
            if key != "[*]":
                lk[prefix].add(key)
    return lk


def ensure_structure(data, structure):
    changed = False
    for path, default_val in structure.items():
        current = data
        for i, key in enumerate(path):
            if key == "[*]":
                parent_path = path[:i]
                parent = data
                for pk in parent_path:
                    parent = parent[pk]
                for item in parent:
                    for sub_path, sub_val in structure.items():
                        if sub_path[:i + 1] == path[:i + 1] and len(sub_path) > i + 1:
                            rest_key = sub_path[i + 1]
                            if isinstance(rest_key, str) and rest_key not in item:
                                item[rest_key] = _empty_for(sub_val)
                                changed = True
                break
            else:
                if key not in current:
                    if i < len(path) - 1:
                        current[key] = {}
                    else:
                        current[key] = _empty_for(default_val)
                    changed = True
                current = current[key]
    return changed


def reorder_fields(data, template):
    if not isinstance(data, dict) or not isinstance(template, dict):
        return
    template_order = list(template.keys())
    existing_keys = set(data.keys())
    ordered = {}
    for k in template_order:
        if k in data:
            ordered[k] = data[k]
    for k in data:
        if k not in ordered:
            ordered[k] = data[k]
    data.clear()
    data.update(ordered)
    for k in data:
        if isinstance(data[k], dict) and isinstance(template.get(k), dict):
            reorder_fields(data[k], template[k])
        elif isinstance(data[k], list) and isinstance(template.get(k), list):
            if len(data[k]) > 0 and len(template[k]) > 0:
                if isinstance(data[k][0], dict) and isinstance(template[k][0], dict):
                    for item in data[k]:
                        reorder_fields(item, template[k][0])


def _is_trivial(val):
    if val is None:
        return True
    if isinstance(val, str) and val.strip() in ("", "（待补充）"):
        return True
    if isinstance(val, (list, dict)) and len(val) == 0:
        return True
    if isinstance(val, bool):
        return True
    if isinstance(val, (int, float)):
        return True
    return False


def remove_extra_fields(data, structure):
    changed = False
    warnings = []

    valid_top_keys = set()
    for path in structure:
        valid_top_keys.add(path[0])

    for key in list(data.keys()):
        if key not in valid_top_keys:
            if _is_trivial(data[key]):
                del data[key]
                changed = True
            else:
                warnings.append(f"顶层字段「{key}」不在模板中但有内容，已保留")

    for key in list(data.keys()):
        if key not in data:
            continue
        val = data[key]
        sub_paths = {}
        for path, sv in structure.items():
            if path[0] == key and len(path) > 1:
                sub_paths[path[1:]] = sv
        if not sub_paths:
            continue
        if isinstance(val, dict):
            valid_sub_keys = set()
            for sp in sub_paths:
                if sp[0] != "[*]":
                    valid_sub_keys.add(sp[0])
            for sk in list(val.keys()):
                if sk not in valid_sub_keys:
                    if _is_trivial(val[sk]):
                        del val[sk]
                        changed = True
                    else:
                        warnings.append(f"「{key}.{sk}」不在模板中但有内容，已保留")
        elif isinstance(val, list):
            item_keys = set()
            for sp in sub_paths:
                if sp[0] == "[*]" and len(sp) > 1:
                    item_keys.add(sp[1])
            if item_keys:
                for item in val:
                    if isinstance(item, dict):
                        for ik in list(item.keys()):
                            if ik not in item_keys:
                                if _is_trivial(item[ik]):
                                    del item[ik]
                                    changed = True
                                else:
                                    warnings.append(f"「{key}[*].{ik}」不在模板中但有内容，已保留")
    return changed, warnings


# ═══════════════════════════════════════════════════════════════
#  模板感知的 JSONC 格式化（严格格式刷）
# ═══════════════════════════════════════════════════════════════

def _js(v):
    return json.dumps(v, ensure_ascii=False)


def build_comment_map(template_text):
    lines = template_text.split('\n')
    comment_map = {}
    pending = []
    path = []

    for line in lines:
        s = line.strip()

        if s.startswith('//'):
            pending.append(line)
            continue
        if s == '':
            pending.append(line)
            continue

        m = re.match(r'^(\s*)"([^"]+)"\s*:\s*\{', line)
        if m:
            key = m.group(2)
            cpath = tuple(p[0] for p in path) + (key,)
            if pending:
                comment_map[cpath] = list(pending)
                pending = []
            path.append((key, 'obj'))
            continue

        m = re.match(r'^(\s*)"([^"]+)"\s*:\s*\[', line)
        if m:
            key = m.group(2)
            cpath = tuple(p[0] for p in path) + (key,)
            if pending:
                comment_map[cpath] = list(pending)
                pending = []
            path.append((key, 'arr'))
            continue

        if s in ('}', '},', ']', '],'):
            if path:
                path.pop()
            pending = []
            continue

        m = re.match(r'^(\s*)"([^"]+)"\s*:\s*(.+?)(,?)\s*$', line)
        if m:
            key = m.group(2)
            cpath = tuple(p[0] for p in path) + (key,)
            if pending:
                comment_map[cpath] = list(pending)
                pending = []
            continue

        pending = []

    return comment_map


def format_by_template(data, template_data, template_path):
    """按模板格式输出 JSONC 文本。
    遍历 template_data 定序，从 data 取值，模板中不存在的字段追加在末尾。
    字符串数组会自动换行格式化（如 nishi.diagram.description）。
    """
    with open(template_path, 'r', encoding='utf-8') as f:
        template_text = f.read()
    comment_map = build_comment_map(template_text)

    def _fmt(data, tpl, path=(), indent=0, inline=False):
        pad = "  " * indent

        def _emit_scalar(k, v, comma):
            if v is None:
                return f'{pad}  "{k}": null{comma}'
            if isinstance(v, bool):
                return f'{pad}  "{k}": {"true" if v else "false"}{comma}'
            if isinstance(v, (int, float)):
                return f'{pad}  "{k}": {v}{comma}'
            return f'{pad}  "{k}": {_js(v)}{comma}'

        if isinstance(tpl, dict):
            out = ["{"] if inline else [f"{pad}{{"]
            tpl_keys = [k for k in tpl if k in data]
            extra_keys = [k for k in data if k not in tpl]
            all_keys = tpl_keys + extra_keys
            for i, k in enumerate(all_keys):
                comma = "," if i < len(all_keys) - 1 else ""
                cpath = path + (k,)
                if cpath in comment_map:
                    out.extend(comment_map[cpath])

                dv = data[k]
                is_extra = k in extra_keys

                if is_extra:
                    if isinstance(dv, dict):
                        inner = _fmt(dv, dv, cpath, indent + 1, inline=True)
                        out.append(f'{pad}  "{k}": {inner}{comma}')
                    elif isinstance(dv, list):
                        out.append(f'{pad}  "{k}": {_js(dv)}{comma}')
                    else:
                        out.append(_emit_scalar(k, dv, comma))
                    continue

                tv = tpl[k]

                if isinstance(tv, dict) and isinstance(dv, dict):
                    inner = _fmt(dv, tv, cpath, indent + 1, inline=True)
                    out.append(f'{pad}  "{k}": {inner}{comma}')
                elif isinstance(tv, list) and isinstance(dv, list):
                    if tv and isinstance(tv[0], dict):
                        # 对象数组 — 每个对象独立格式化
                        titem = tv[0]
                        items = []
                        for j, di in enumerate(dv):
                            if isinstance(di, dict):
                                item_inner = _fmt(di, titem, cpath, indent + 2)
                                items.append(item_inner + ("," if j < len(dv) - 1 else ""))
                        if items:
                            inner = "[\n" + "\n".join(items) + f"\n{pad}  ]"
                        else:
                            inner = "[]"
                        out.append(f'{pad}  "{k}": {inner}{comma}')
                    elif tv and isinstance(tv[0], str):
                        # 字符串数组 — 每项换行，便于阅读
                        item_lines = []
                        for j, s in enumerate(dv):
                            c = "," if j < len(dv) - 1 else ""
                            item_lines.append(f'{pad}    {_js(s)}{c}')
                        if item_lines:
                            inner = "[\n" + "\n".join(item_lines) + f"\n{pad}  ]"
                        else:
                            inner = "[]"
                        out.append(f'{pad}  "{k}": {inner}{comma}')
                    else:
                        out.append(f'{pad}  "{k}": {_js(dv)}{comma}')
                else:
                    out.append(_emit_scalar(k, dv, comma))

            out.append(f"{pad}}}")
            return "\n".join(out)

        elif isinstance(tpl, list) and tpl and isinstance(tpl[0], dict):
            out = ["{"] if inline else [f"{pad}{{"]
            tpl_keys = [k for k in tpl[0] if k in data]
            extra_keys = [k for k in data if k not in tpl[0]]
            all_keys = tpl_keys + extra_keys
            for i, k in enumerate(all_keys):
                comma = "," if i < len(all_keys) - 1 else ""
                cpath = path + (k,)
                if cpath in comment_map:
                    out.extend(comment_map[cpath])

                dv = data[k]
                is_extra = k in extra_keys

                if is_extra:
                    if isinstance(dv, dict):
                        inner = _fmt(dv, dv, cpath, indent + 1, inline=True)
                        out.append(f'{pad}  "{k}": {inner}{comma}')
                    elif isinstance(dv, list):
                        out.append(f'{pad}  "{k}": {_js(dv)}{comma}')
                    else:
                        out.append(_emit_scalar(k, dv, comma))
                    continue

                tv = tpl[0][k]

                if isinstance(tv, dict) and isinstance(dv, dict):
                    inner = _fmt(dv, tv, cpath, indent + 1, inline=True)
                    out.append(f'{pad}  "{k}": {inner}{comma}')
                elif isinstance(tv, list):
                    out.append(f'{pad}  "{k}": {_js(dv)}{comma}')
                else:
                    out.append(_emit_scalar(k, dv, comma))

            out.append(f"{pad}}}")
            return "\n".join(out)

        else:
            return _js(data)

    return _fmt(data, template_data) + "\n"


def do_backup():
    """运行前自动备份 content/"""
    with zipfile.ZipFile(BACKUP_FILE, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in sorted(os.listdir(SCRIPT_DIR)):
            if fname.endswith(".jsonc"):
                zf.write(os.path.join(SCRIPT_DIR, fname), fname)


def _check_contentful_renames(template, files):
    structure = extract_structure(template)
    level_keys = _build_level_keys(structure)
    all_warnings = {}

    for fname in files:
        filepath = os.path.join(SCRIPT_DIR, fname)
        data = load_jsonc(filepath)
        warnings = []

        top_valid = level_keys.get((), set())
        for key in list(data.keys()):
            if key not in top_valid and not _is_trivial(data[key]):
                preview = str(data[key])[:40].replace("\n", " ")
                warnings.append(f"顶层「{key}」有内容（{preview}…），但模板中不存在")

        def _check_nested(obj, prefix):
            if not isinstance(obj, dict):
                return
            valid = level_keys.get(prefix, set())
            for key in list(obj.keys()):
                if key not in valid:
                    if not _is_trivial(obj[key]):
                        preview = str(obj[key])[:40].replace("\n", " ")
                        path_str = " > ".join(prefix + (key,))
                        warnings.append(f"「{path_str}」有内容（{preview}…），但模板中不存在")
                elif isinstance(obj[key], dict):
                    _check_nested(obj[key], prefix + (key,))

        for key, val in data.items():
            if isinstance(val, dict) and key in top_valid:
                _check_nested(val, (key,))
            elif isinstance(val, list) and key in top_valid:
                for item in val:
                    if isinstance(item, dict):
                        _check_nested(item, (key, "[*]"))

        if warnings:
            all_warnings[fname] = warnings

    return len(all_warnings) == 0, all_warnings


def run_sync(template_name):
    template_path = os.path.join(SCRIPT_DIR, template_name)

    if not os.path.exists(template_path):
        print(f"❌ 模板文件不存在: {template_path}")
        return

    template = load_jsonc(template_path)
    structure = extract_structure(template)
    files = sorted([f for f in os.listdir(SCRIPT_DIR) if f.endswith(".jsonc") and f != template_name and f != "lock.jsonc"])

    print(f"📐 模板: {template_name}  ({len(structure)} 个字段路径)")
    print(f"🔍 预检 {len(files)} 个文件...")
    safe, content_warnings = _check_contentful_renames(template, files)

    if not safe:
        print(f"\n❌ 格式刷被阻止！检测到 {len(content_warnings)} 个文件存在有内容的旧字段：\n")
        shown = 0
        for fname, warns in sorted(content_warnings.items()):
            if shown >= 5:
                remaining = len(content_warnings) - shown
                print(f"  … 还有 {remaining} 个文件有类似问题")
                break
            print(f"  {fname}:")
            for w in warns[:3]:
                print(f"    ⚠️  {w}")
            if len(warns) > 3:
                print(f"    … 还有 {len(warns) - 3} 个字段")
            shown += 1
        print(f"\n👉 请使用 yijing_manager.py → 批量字段操作 → 重命名字段，先迁移有内容的字段。")
        print(f"   迁移完成后，再运行格式刷。\n")
        return

    print("✅ 无内容丢失风险，执行同步。\n")
    print("📦 自动备份 → content.bkp.zip")
    do_backup()

    updated = 0
    refreshed = 0
    for fname in files:
        filepath = os.path.join(SCRIPT_DIR, fname)
        data = load_jsonc(filepath)

        changed1 = ensure_structure(data, structure)
        changed2, warnings = remove_extra_fields(data, structure)
        reorder_fields(data, template)

        for w in warnings:
            print(f"  ⚠️  {fname}: {w}")

        if changed1 or changed2:
            updated += 1
            tag = "已同步新字段"
        else:
            refreshed += 1
            tag = "已刷新格式"

        text = format_by_template(data, template, template_path)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  ✅ {fname} — {tag}")

    print(f"\n📊 完成：{updated} 个结构同步（补齐模板字段），{refreshed} 个格式刷新（对齐缩进/排序/注释）。")

    # 同步 lock.jsonc 结构（保留已有锁值）
    sync_lock_structure(template_path)
    print("🔒 lock.jsonc 结构已同步")


def main():
    template_name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TEMPLATE

    while True:
        run_sync(template_name)
        print("\n" + "─" * 48)
        try:
            choice = input("按回车键再次刷新，输入 q 返回上级菜单: ").strip()
        except EOFError:
            print()
            break
        if choice.lower() == "q":
            print("返回上级菜单。")
            break
        print()


if __name__ == "__main__":
    main()
