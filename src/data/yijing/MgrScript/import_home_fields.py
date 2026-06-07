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
        >>> data = {"id": 1, "name": "乾", "nishi": {"home": {"member": "父亲"}}}
        >>> save_jsonc("content/01_乾.jsonc", data)
    """
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
    """从自身源码读取字段路径配置（MEMBER_FIELD_PATH / DIRECTION_FIELD_PATH）。

    功能说明：
        脚本首次运行时会检测或让用户选择家庭成员和方位的目标字段路径，
        然后通过 _save_field_config 写入源码。此函数从源码中正则提取
        这两个变量的值，避免每次都重新检测或询问。

    Args:
        无

    Returns:
        tuple: (member_path, direction_path) 两个元素的元组。
            member_path (str): 家庭成员字段路径，如 "nishi.home.member"
            direction_path (str): 方位字段路径，如 "nishi.home.direction"
            若源码中未找到有效配置，对应元素为 None。

    示例:
        >>> member_path, direction_path = _load_field_config()
        >>> member_path
        'nishi.home.member'
        >>> direction_path
        'nishi.home.direction'
    """
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
    """将字段路径配置持久化写入自身源码。

    功能说明：
        这是"自修改"机制的一部分。用户选择字段路径后，脚本通过正则替换
        将路径写入源码中 MEMBER_FIELD_PATH 和 DIRECTION_FIELD_PATH 变量
        的赋值行，下次运行无需重新配置。

    Args:
        member_path (str): 家庭成员字段路径，如 "nishi.home.member"
        direction_path (str): 方位字段路径，如 "nishi.home.direction"

    Returns:
        None: 无返回值，直接修改自身 .py 源码文件。

    示例:
        >>> _save_field_config("nishi.home.member", "nishi.home.direction")
        # 源码中 MEMBER_FIELD_PATH 和 DIRECTION_FIELD_PATH 的值被更新
    """
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
    """从模板提取所有文本类型（str）的叶子字段路径和样例值。

    功能说明：
        递归遍历模板 JSONC（01_乾.jsonc）的所有 dict 嵌套层级，
        收集所有值为 str 类型的叶子字段。用于在首次运行时向用户展示
        可选的目标字段列表，以便将家庭成员和方位写入正确的字段。

        list、int、bool 等非字符串类型字段会被跳过，
        因为家庭成员（"父亲"）和方位（"西北"）都是字符串。

    Args:
        无

    Returns:
        list[tuple]: 每个元素为 (路径, 样例值) 的元组列表。
            路径如 "nishi.home.member"，样例值如 "父亲"。
            列表按遍历顺序排列（深层嵌套的 dict 键有序）。

    示例:
        >>> fields = _list_text_fields()
        >>> fields[:3]
        [('full_name', '乾为天'), ('nishi.home.member', '父亲'), ('nishi.home.direction', '西北')]
    """
    template = load_jsonc(TEMPLATE_FILE)
    fields = []

    def _walk(obj, prefix):
        """递归遍历 dict 树，收集所有 str 类型的叶子字段路径。"""
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
    """获取 member/direction 字段路径，三级决策。

    功能说明：
        这是路径解析的总控函数，采用三级决策链：
        1. 优先读取已保存的配置（_load_field_config）
        2. 其次检查默认路径 nishi.home.member / nishi.home.direction
           是否在模板中存在（_list_text_fields），存在则保存配置供下次使用
        3. 最后列出模板中所有文本字段，让用户交互式选择家庭成员和方位
           各自对应的字段，选择后保存配置

    Args:
        无

    Returns:
        tuple: (member_path, direction_path) 两个元素的元组。
            member_path (str|None): 家庭成员字段路径，无法确定时为 None
            direction_path (str|None): 方位字段路径，无法确定时为 None

    示例:
        >>> member_path, dir_path = _resolve_field_paths()
          🔍 检测到默认字段: nishi.home.member / nishi.home.direction
        >>> member_path
        'nishi.home.member'
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
    """按点分隔路径设置嵌套字典值，中间层级自动创建。

    功能说明：
        例如路径 "nishi.home.member"，会在 data 中逐层创建
        data["nishi"]、data["nishi"]["home"]（若不存在），然后
        设置 data["nishi"]["home"]["member"] = value。

        与 import_nishi_diagram.py 中的 _set_nested_path 功能相同。

    Args:
        data (dict): 目标字典（通常是 load_jsonc 返回的卦数据）
        path (str): 点分隔的字段路径，如 "nishi.home.member"
        value (any): 要设置的值（通常是 str 或 dict）

    Returns:
        None: 直接修改传入的 data 字典（原地修改）。

    示例:
        >>> data = {}
        >>> _set_by_path(data, "nishi.home.member", "父亲")
        >>> data
        {'nishi': {'home': {'member': '父亲'}}}
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
    """从自身源码重新加载八卦映射表（TRIGRAM_TO_DIRECTION 和 TRIGRAM_TO_MEMBER）。

    功能说明：
        脚本支持"自修改"机制：当遇到内置映射表中没有的卦名时，用户可手动
        输入对应值，脚本将其写入源码的 AUTO_MAP 区域。此函数重新从源码读取
        映射表，确保在用户新增映射后立即生效。

        使用 ast.literal_eval 安全解析字典（比 exec/eval 更安全）。

    Args:
        无

    Returns:
        tuple: (direction_map, member_map) 两个元素的元组。
            direction_map (dict): 八卦名(str) → 方位(str) 的映射，
                                  如 {"乾": "西北", "坤": "西南", ...}
            member_map (dict): 八卦名(str) → 家庭成员(str) 的映射，
                               如 {"乾": "父亲", "坤": "母亲", ...}

    示例:
        >>> dir_map, mem_map = _load_maps()
        >>> dir_map["乾"]
        '西北'
        >>> mem_map["震"]
        '长男'
    """
    import ast
    with open(SELF, "r", encoding="utf-8") as f:
        src = f.read()

    def _extract_dict(var_name):
        """从源码中用正则提取指定变量名的字典字面量并解析。"""
        m = re.search(rf"{var_name}\s*=\s*(\{{.+?\}})", src, re.DOTALL)
        if m:
            try:
                return ast.literal_eval(m.group(1))
            except (SyntaxError, ValueError):
                pass
        return {}

    return _extract_dict("TRIGRAM_TO_DIRECTION"), _extract_dict("TRIGRAM_TO_MEMBER")


def _add_mapping(var_name, key, value):
    """在自身源码的 AUTO_MAP 区域内插入一条新的八卦映射条目。

    功能说明：
        这是"自修改"机制的核心函数。当遇到内置映射表中没有的卦名时，
        用户输入对应的值后，此函数将该映射持久化写入脚本源码中对应字典的
        内部（TRIGRAM_TO_DIRECTION 或 TRIGRAM_TO_MEMBER）。

        定位策略：在源码行中搜索 === AUTO_MAP_START === 和
        === AUTO_MAP_END === 标记之间的目标字典的右花括号前插入新条目。

    Args:
        var_name (str): 目标字典变量名，如 "TRIGRAM_TO_DIRECTION" 或 "TRIGRAM_TO_MEMBER"
        key (str): 八卦名（键），如 "乾"、"震"
        value (str): 映射值（值），如 "西北"、"长男"

    Returns:
        bool: True 表示成功插入并保存；False 表示无法定位插入位置。

    示例:
        >>> success = _add_mapping("TRIGRAM_TO_DIRECTION", "乾", "西北")
          📝 已将 乾 → 西北 写入 TRIGRAM_TO_DIRECTION
        >>> success
        True
    """
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
    """尝试从映射表获取八卦对应的值，若不存在则询问用户并自修改脚本。

    功能说明：
        这是映射解析的入口函数。给定一个八卦名（如"乾"、"震"），
        先从内存中的映射字典查找。如果找不到（说明是脚本内置映射表
        未覆盖的卦名），则提示用户输入对应值，并通过 _add_mapping
        将新映射写入脚本源码，以便下次自动生效。

    Args:
        trigram (str): 八卦名，如 "乾"、"坤"、"震" 等
        map_dict (dict): 当前已加载的映射字典，如 {"乾": "西北", "坤": "西南"}
        map_name (str): 映射的中文名称（用于提示信息），如 "方位"、"家庭成员"
        dict_name (str): 映射表的变量名（用于 _add_mapping），
                         如 "TRIGRAM_TO_DIRECTION"、"TRIGRAM_TO_MEMBER"

    Returns:
        tuple: (value, learned) 两个元素的元组。
            value (str|None): 映射值（如 "西北"、"父亲"），
                              映射失败或用户跳过时为 None
            learned (bool): True 表示这是一个新学到的映射（用户刚输入的），
                           False 表示来自已有映射表

    示例:
        >>> dir_map = {"乾": "西北", "坤": "西南"}
        >>> val, learned = _resolve_mapping("乾", dir_map, "方位", "TRIGRAM_TO_DIRECTION")
        >>> val
        '西北'
        >>> learned
        False
        >>> # 如果遇到未知卦名（如"离"），用户会被提示输入：
        >>> val, learned = _resolve_mapping("离", dir_map, "方位", "TRIGRAM_TO_DIRECTION")
          ⚠️  未知的卦名「离」不在 方位 映射表中。
          当前 方位：{'乾': '西北', '坤': '西南'}
          请输入「离」对应的方位，或回车跳过此卦：
          → 南
          📝 已将 离 → 南 写入 TRIGRAM_TO_DIRECTION
        >>> val
        '南'
        >>> learned
        True
    """
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
    """自动填充 64 卦的 nishi.home 字段（家庭成员和方位）。

    功能说明：
        根据每卦的上卦(upper)确定家庭成员、下卦(lower)确定方位，
        将结果写入对应 JSONC 文件的 nishi.home 字段。
        首次运行自动检测或让用户选择字段路径并保存配置，
        再次运行时直接使用已保存的配置。映射表内置在脚本源码中，
        遇到未知卦名会交互式询问用户并自修改脚本以持久化新映射。

    Args:
        无（通过命令行直接运行：python3 MgrScript/import_home_fields.py）

    Returns:
        None: 执行结果通过控制台打印输出

    示例:
        $ cd src/data/yijing
        $ python3 MgrScript/import_home_fields.py
        🔍 检测到默认字段: nishi.home.member / nishi.home.direction
        家庭成员字段: nishi.home.member
        方位字段:     nishi.home.direction
          ✅ 01_乾.jsonc: 乾→父亲, 乾→西北
          ...
        ✅ 已更新 64/64 卦
    """
    member_path, direction_path = _resolve_field_paths()
    if not member_path or not direction_path:
        print("  ❌ 无法确定字段映射，退出")
        return
    # 防御：确保路径不包含格式字符串残留
    for label, p in [("家庭成员字段", member_path), ("方位字段", direction_path)]:
        if "{" in p or "}" in p or p.strip() == "":
            print(f"  ❌ {label}路径「{p}」非法，请检查脚本源码中的 FIELD_PATH 配置")
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
