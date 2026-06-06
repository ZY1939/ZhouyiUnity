#!/usr/bin/env python3
"""
自动填充 nishi.home 字段 — 根据卦的上下卦，自动写入家庭成员和方位。

规则：
  - 上卦(upper) → 家庭成员
  - 下卦(lower) → 方位

首次运行时列出模板中所有文本字段，用户选择对应字段后保存配置。
再次运行时直接使用已保存的配置。

八卦映射（内置）：
  乾 → 父亲 / 西北    坤 → 母亲 / 西南
  震 → 长男 / 东      巽 → 长女 / 东南
  坎 → 中男 / 北      离 → 中女 / 南
  艮 → 少男 / 东北    兑 → 少女 / 西

用法：
    cd src/data/yijing
    python3 MgrScript/import_home_fields.py
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
DATA_DIR = os.path.join(PARENT, "content")
SELF = os.path.abspath(__file__)

sys.path.insert(0, HERE)
from sync_structure import load_jsonc, format_by_template

TEMPLATE_FILE = os.path.join(DATA_DIR, "01_乾.jsonc")


def save_jsonc(path, data):
    template = load_jsonc(TEMPLATE_FILE)
    text = format_by_template(data, template, TEMPLATE_FILE)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ═══════════════════════════════════════════════════════════════
#  字段路径配置（可被脚本自修改）
# ═══════════════════════════════════════════════════════════════
#  === FIELD_MAP_START ===
MEMBER_FIELD_PATH = "nishi.home.member"
DIRECTION_FIELD_PATH = "nishi.home.direction"
#  === FIELD_MAP_END ===


def _load_field_config():
    """从自身源码读取 MEMBER_FIELD_PATH / DIRECTION_FIELD_PATH 配置。"""
    with open(SELF, "r", encoding="utf-8") as f:
        src = f.read()
    result = {"member": None, "direction": None}
    for key in ("MEMBER_FIELD_PATH", "DIRECTION_FIELD_PATH"):
        m = re.search(rf'^{key}\s*=\s*"([^"]*)"', src, re.MULTILINE)
        if m:
            val = m.group(1)
            result["member" if "MEMBER" in key else "direction"] = val
    return result["member"], result["direction"]


def _save_field_config(member_path, direction_path):
    """将字段路径写入自身源码。"""
    with open(SELF, "r", encoding="utf-8") as f:
        src = f.read()

    if member_path:
        src = re.sub(
            r'^MEMBER_FIELD_PATH\s*=\s*[^\n]*',
            f'MEMBER_FIELD_PATH = "{member_path}"',
            src,
            flags=re.MULTILINE,
        )
    if direction_path:
        src = re.sub(
            r'^DIRECTION_FIELD_PATH\s*=\s*[^\n]*',
            f'DIRECTION_FIELD_PATH = "{direction_path}"',
            src,
            flags=re.MULTILINE,
        )

    with open(SELF, "w", encoding="utf-8") as f:
        f.write(src)


def _list_text_fields():
    """从模板提取所有文本类型的叶子字段。返回 [(路径, 样例值), ...]"""
    template = load_jsonc(TEMPLATE_FILE)
    fields = []

    def _walk(obj, prefix):
        if isinstance(obj, dict):
            for k, v in obj.items():
                path = f"{prefix}.{k}" if prefix else k
                if isinstance(v, str):
                    fields.append((path, v))
                elif isinstance(v, dict):
                    _walk(v, path)

    _walk(template, "")
    return fields


DEFAULT_MEMBER_PATH = "nishi.home.member"
DEFAULT_DIRECTION_PATH = "nishi.home.direction"


def _resolve_field_paths():
    """获取 member/direction 字段路径。
    优先配置 → 其次检查默认路径 nishi.home.member / nishi.home.direction
    → 最后列出文本字段让用户选择。
    """
    member_path = _load_field_config()[0]
    direction_path = _load_field_config()[1]

    if member_path and direction_path:
        return member_path, direction_path

    text_fields = _list_text_fields()
    text_paths = {p for p, _ in text_fields}

    # 默认路径：nishi.home.member / nishi.home.direction
    if DEFAULT_MEMBER_PATH in text_paths and DEFAULT_DIRECTION_PATH in text_paths:
        print(f"  🔍 检测到默认字段: {DEFAULT_MEMBER_PATH} / {DEFAULT_DIRECTION_PATH}")
        _save_field_config(DEFAULT_MEMBER_PATH, DEFAULT_DIRECTION_PATH)
        return DEFAULT_MEMBER_PATH, DEFAULT_DIRECTION_PATH

    # 找不到默认字段，让用户选择
    print("\n  ── 字段映射配置 ──")
    print("  模板中的文本字段:")
    for i, (path, val) in enumerate(text_fields, 1):
        preview = val[:35] + "…" if len(val) > 35 else val
        print(f"  {i:>3}. {path}: {preview}")
    print()

    try:
        m_choice = input("  上卦→家庭成员, 请输入字段序号 (回车=默认): ").strip()
        d_choice = input("  下卦→方位,       请输入字段序号 (回车=默认): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None, None

    member_path = None
    direction_path = None

    if m_choice:
        try:
            mi = int(m_choice) - 1
            if 0 <= mi < len(text_fields):
                member_path = text_fields[mi][0]
        except ValueError:
            pass
    if d_choice:
        try:
            di = int(d_choice) - 1
            if 0 <= di < len(text_fields):
                direction_path = text_fields[di][0]
        except ValueError:
            pass

    if not member_path or not direction_path:
        print("  ❌ 字段选择无效")
        return None, None

    _save_field_config(member_path, direction_path)
    return member_path, direction_path


def _set_by_path(data, path, value):
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


# ═══════════════════════════════════════════════════════════════
#  === AUTO_MAP_START === （此区域会被脚本自动更新）
# ═══════════════════════════════════════════════════════════════
TRIGRAM_TO_DIRECTION = {
    "乾": "西北",
    "坤": "西南",
    "震": "东",
    "巽": "东南",
    "坎": "北",
    "离": "南",
    "艮": "东北",
    "兑": "西",
}

TRIGRAM_TO_MEMBER = {
    "乾": "父亲",
    "坤": "母亲",
    "震": "长男",
    "巽": "长女",
    "坎": "中男",
    "离": "中女",
    "艮": "少男",
    "兑": "少女",
}
# ═══════════════════════════════════════════════════════════════
#  === AUTO_MAP_END ===
# ═══════════════════════════════════════════════════════════════


def _load_maps():
    """从自身源码重新加载映射表"""
    import ast
    with open(SELF, "r", encoding="utf-8") as f:
        src = f.read()

    def _extract_dict(var_name):
        m = re.search(rf"{var_name}\s*=\s*(\{{.+?\}})", src, re.DOTALL)
        if m:
            try:
                return ast.literal_eval(m.group(1))
            except (SyntaxError, ValueError):
                pass
        return {}

    return _extract_dict("TRIGRAM_TO_DIRECTION"), _extract_dict("TRIGRAM_TO_MEMBER")


def _add_mapping(var_name, key, value):
    """在 AUTO_MAP 区域内插入新的八卦映射条目"""
    with open(SELF, "r", encoding="utf-8") as f:
        lines = f.readlines()

    mark_start = "=== AUTO_MAP_START ==="
    mark_end = "=== AUTO_MAP_END ==="
    target_var = f"{var_name} = {{"

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
        print(f"  ⚠️  无法定位 {var_name} 的插入位置，跳过自修改")
        return False

    indent = "    "
    new_entry = f'{indent}"{key}": "{value}",\n'
    lines.insert(insert_line, new_entry)

    with open(SELF, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"  📝 已将 {key} → {value} 写入 {var_name}")
    return True


def _resolve_mapping(trigram, map_dict, map_name, dict_name):
    """尝试从映射表获取值。若不存在，询问用户并自修改脚本。"""
    if trigram in map_dict:
        return map_dict[trigram], False

    print(f"\n  ⚠️  未知的卦名「{trigram}」不在 {map_name} 映射表中。")
    print(f"  当前 {map_name}：{dict(map_dict)}")
    print(f"  请输入「{trigram}」对应的{map_name}，或回车跳过此卦：")
    try:
        answer = input("  → ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None, False

    if not answer:
        return None, False

    _add_mapping(dict_name, trigram, answer)
    return answer, True


def main():
    member_path, direction_path = _resolve_field_paths()
    if not member_path or not direction_path:
        print("  ❌ 无法确定字段映射，退出")
        return

    print(f"  家庭成员字段: {member_path}")
    print(f"  方位字段:     {direction_path}")

    direction_map, member_map = _load_maps()
    updated = 0
    learned = 0

    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith(".jsonc"):
            continue
        if fname == "lock.jsonc":
            continue
        filepath = os.path.join(DATA_DIR, fname)
        data = load_jsonc(filepath)

        upper = data.get("upper", "")
        lower = data.get("lower", "")
        name = data["name"]

        if not upper or not lower:
            print(f"  ⚠️  {fname}: upper/lower 字段缺失，跳过")
            continue

        member_val, member_learned = _resolve_mapping(
            upper, member_map, "家庭成员", "TRIGRAM_TO_MEMBER"
        )
        dir_val, dir_learned = _resolve_mapping(
            lower, direction_map, "方位", "TRIGRAM_TO_DIRECTION"
        )

        if member_learned or dir_learned:
            learned += 1
            direction_map, member_map = _load_maps()
            member_val = member_map.get(upper) if member_learned else member_val
            dir_val = direction_map.get(lower) if dir_learned else dir_val

        if member_val is None and dir_val is None:
            continue

        if member_val:
            _set_by_path(data, member_path, member_val)
        if dir_val:
            _set_by_path(data, direction_path, dir_val)

        save_jsonc(filepath, data)
        updated += 1
        print(f"  ✅ {fname}: {upper}→{member_val or '?'}, {lower}→{dir_val or '?'}")

    print(f"\n✅ 已更新 {updated}/64 卦" + (f"，学到 {learned} 个新映射" if learned else ""))


if __name__ == "__main__":
    main()
