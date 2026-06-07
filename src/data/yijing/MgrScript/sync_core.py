#!/usr/bin/env python3
"""
JSONC 数据库结构同步核心模块（格式刷） — 可复用的通用函数。

功能：
  1. 结构同步 — 确保目标 JSONC 文件拥有与模板一致的字段路径
  2. 字段清理 — 删除目标文件中模板不存在的字段（有内容的字段保留以防误删）
  3. 字段排序 — 按模板的字段顺序重新排列
  4. 格式刷新 — 输出格式严格对齐模板（缩进、注释、数组换行等）

用法（在具体项目的 sync_structure.py 中调用）：
    from sync_core import run_sync
    run_sync(template_path, script_dir, backup_file, template_display_name, has_lock=False)

说明：
  - 运行前自动备份 script_dir → backup_file.zip
  - 有内容的字段若不在模板中会被保留并发出警告
  - 可反复运行，已同步的文件仅刷新格式，不会重复修改
"""

import json
import os
import re
import sys
import zipfile


def load_jsonc(path):
    """加载 JSONC 文件，自动去除 // 注释行后解析为 Python dict。

    Args:
        path: JSONC 文件的完整路径，例如 "content/01_乾.jsonc"

    Returns:
        dict: 解析后的 Python 字典

    示例:
        data = load_jsonc("content/01_乾.jsonc")
        print(data["name"])  # "乾"
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    cleaned = re.sub(r"//.*", "", raw)
    return json.loads(cleaned)


def extract_structure(obj, prefix=()):
    """递归提取数据结构的字段骨架，用于后续字段补齐和清理。

    遍历 dict 树，记录每个叶子字段的路径和示例值。
    遇到对象数组时，用 "[*]" 通配符表示数组内的元素结构。

    Args:
        obj: 要分析的 dict（通常是模板文件解析后的数据）
        prefix: 当前递归路径（内部使用，调用方不传）

    Returns:
        dict: {(路径元组): 示例值}
              例如 {("name",): "乾", ("nishi", "home", "member"): "父亲"}

    示例:
        structure = extract_structure({"name": "乾", "nishi": {"home": {"member": "父亲"}}})
        # {("name",): "乾", ("nishi", "home", "member"): "父亲"}
    """
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
    """根据模板值的类型，返回对应的"空值"（用于补齐缺失字段）。

    类型映射:
        list → []       dict → {}       bool → False
        数字 → None     字符串 → ""      "[]"(对象数组标记) → [{}]

    Args:
        val: 模板中的示例值

    Returns:
        对应类型的空值/默认值

    示例:
        _empty_for("hello")   # → ""
        _empty_for(42)        # → None
        _empty_for([])        # → []
        _empty_for(True)      # → False
    """
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
    """构建每个层级路径包含的 key 集合，用于快速判断某路径下有哪些合法字段。

    Args:
        structure: extract_structure() 返回的路径字典

    Returns:
        dict: {父路径元组: {子 key 集合}}
              例如 {(): {"name", "nishi"}, ("nishi",): {"home"}}

    示例:
        s = {("name",): "乾", ("nishi", "home", "member"): "父亲"}
        lk = _build_level_keys(s)
        # {(): {"name", "nishi"}, ("nishi",): {"home"}, ("nishi", "home"): {"member"}}
    """
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
    """确保目标数据包含模板定义的所有字段路径，缺失的字段自动补齐空值。

    这是一种"安全补齐"操作：只添加缺失的字段，从不删除或修改已有数据。
    遇到对象数组（[*] 通配符）时，会为数组中的每个元素补齐缺失的子字段。

    Args:
        data: 目标数据字典，例如从某个 JSONC 文件 load_jsonc 后得到的内容
        structure: 字段骨架字典，由 extract_structure(template) 生成，
                   格式为 {(路径元组): 示例值}

    Returns:
        bool: 是否实际修改了 data（True 表示有新字段被补齐，False 表示结构已完整）

    示例:
        data = {"name": "乾"}
        structure = {("name",): "乾", ("description",): ""}
        changed = ensure_structure(data, structure)
        # data 变为 {"name": "乾", "description": ""}，返回 True
    """
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
    """按模板的键顺序重新排列 data 中所有字典的键，递归处理嵌套结构。

    字典在 Python 3.7+ 中保持插入顺序，此函数确保输出文件的字段顺序
    与模板一致，方便人工对比和版本管理。模板中不存在的字段会被追加到末尾。

    Args:
        data: 要重新排序的目标数据字典（原地修改）
        template: 模板数据字典，其键顺序作为排序参照

    Returns:
        None（原地修改 data）

    示例:
        data = {"description": "乾卦", "name": "乾"}
        template = {"name": "乾", "description": "乾卦"}
        reorder_fields(data, template)
        # data 的键顺序变为 name → description
    """
    if not isinstance(data, dict) or not isinstance(template, dict):
        return
    template_order = list(template.keys())
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
    """判断一个值是否为"安全可删除"的空值或默认值。

    以下情况被视为可安全删除：
    - None
    - 空字符串或仅含"（待补充）"的字符串
    - 布尔值（通常为默认 False）
    - 数字（通常为默认 0 或占位 None）
    - 字典/列表：递归检查所有子元素均为 trivial（如 {'a': '', 'b': ''}）

    Args:
        val: 任意 Python 值

    Returns:
        bool: True 表示该值为空/默认值，可以安全删除；False 表示有实际内容

    示例:
        _is_trivial("")           # → True
        _is_trivial("（待补充）")   # → True
        _is_trivial([])           # → True
        _is_trivial({})           # → True
        _is_trivial({"a": ""})    # → True（所有子值空）
        _is_trivial("重要内容")    # → False
        _is_trivial({"a": "x"})  # → False（有非空子值）
    """
    if val is None:
        return True
    if isinstance(val, str) and val.strip() in ("", "（待补充）"):
        return True
    if isinstance(val, bool):
        return True
    if isinstance(val, (int, float)):
        return True
    if isinstance(val, dict):
        return all(_is_trivial(v) for v in val.values())
    if isinstance(val, list):
        return all(_is_trivial(v) for v in val)
    return False


def remove_extra_fields(data, structure):
    """删除目标数据中不在模板定义里的空字段，有内容的字段保留并发出警告。

    这是一个"安全清理"操作：只删除确认无内容的冗余字段，
    有实际内容的字段即使模板中不存在也会保留，防止误删数据。

    Args:
        data: 目标数据字典（原地修改）
        structure: 字段骨架字典，由 extract_structure(template) 生成

    Returns:
        (bool, list): 元组
            - bool: 是否有字段被实际删除
            - list[str]: 警告信息列表，每个元素描述一个被保留的有内容旧字段

    示例:
        data = {"name": "乾", "old_field": "", "legacy": "重要数据"}
        structure = {("name",): "乾"}
        changed, warnings = remove_extra_fields(data, structure)
        # data 变为 {"name": "乾", "legacy": "重要数据"}
        # changed = True（old_field 被删除）
        # warnings = ["顶层字段「legacy」不在模板中但有内容，已保留"]
    """
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
    """将 Python 值序列化为 JSON 字符串，不转义中文等非 ASCII 字符。

    与 json.dumps 默认行为不同，设置 ensure_ascii=False 确保中文、
    日文等 Unicode 字符以原始形式输出，而不是 \\uXXXX 转义序列。

    Args:
        v: 要序列化的 Python 值（str、int、list、dict 等）

    Returns:
        str: JSON 字符串，中文保持原样

    示例:
        _js("乾")       # → '"乾"'
        _js([1, 2, 3])  # → '[1, 2, 3]'
        _js({"a": 1})   # → '{"a": 1}'
    """
    return json.dumps(v, ensure_ascii=False)


def build_comment_map(template_text):
    """解析模板 JSONC 文件的原始文本，提取每个字段前的注释行，建立路径到注释的映射。

    遍历模板的每一行，跟踪当前的 JSON 路径层级（进入 { [ 时压栈，遇到 } ] 时弹栈）。
    遇到字段键名（"key": ...）时，将之前累积的注释行（// 开头或空行）关联到该字段路径。

    Args:
        template_text: 模板 JSONC 文件的完整原始文本内容

    Returns:
        dict: {(路径元组): [注释行列表]}
              例如 {("name",): ["// 卦名"], ("nishi", "home"): ["", "// 家宅"]}
              每行注释保留原始缩进和换行符，精确还原模板格式

    示例:
        text = '''{
          // 卦名
          "name": "乾",
          "nishi": {
            // 家宅
            "home": "..."}}
        '''
        cmap = build_comment_map(text)
        # {("name",): ["  // 卦名\\n"], ("nishi", "home"): ["    // 家宅\\n"]}
    """
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
    """按模板格式将数据输出为格式化 JSONC 文本（格式刷核心）。

    工作方式：
    1. 读取模板文件的原始文本，解析注释位置
    2. 按模板数据的键顺序遍历，从目标数据中提取对应值
    3. 对象的键严格按模板顺序排列，模板中不存在的键追加在末尾
    4. 自动处理嵌套对象、对象数组、字符串数组的缩进和换行
    5. 空值（None/空字符串/空列表/空字典等）视为无内容，输出为 null 或空结构

    Args:
        data: 目标数据字典（要输出的内容）
        template_data: 模板数据字典（load_jsonc(template_path) 的结果，用于定序和结构参考）
        template_path: 模板 JSONC 文件的完整路径（用于读取原始文本和注释）

    Returns:
        str: 格式化后的 JSONC 文本，末尾带换行符

    示例:
        data = {"name": "乾", "description": "元亨利贞"}
        template = {"name": "乾", "description": ""}
        text = format_by_template(data, template, "template.jsonc")
        # 输出格式对齐模板，注释保留原位置
    """
    with open(template_path, 'r', encoding='utf-8') as f:
        template_text = f.read()
    comment_map = build_comment_map(template_text)

    def _fmt(data, tpl, path=(), indent=0, inline=False):
        """递归格式化数据：按模板顺序和缩进风格生成 JSONC 文本。"""
        pad = "  " * indent

        def _emit_scalar(k, v, comma):
            """格式化单个简单值字段（null/bool/数字/字符串），附加尾部逗号。"""
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
                    elif (tv and isinstance(tv[0], str)) or (dv and isinstance(dv[0], str)):
                        # 字符串数组 — 每项换行，便于阅读
                        # 兼容模板为空数组 [] 但数据有内容的情况
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


def do_backup(script_dir, backup_file):
    """运行格式刷前自动备份指定目录下的所有 .jsonc 文件到 zip 压缩包。

    备份按文件名排序，排除 lock.jsonc（锁文件不需要备份）。
    使用 ZIP_DEFLATED 压缩以节省空间。

    Args:
        script_dir: JSONC 数据文件所在目录的完整路径
        backup_file: 备份 zip 文件的完整路径，例如 "content.bkp.zip"

    Returns:
        None

    示例:
        do_backup("content/", "content.bkp.zip")
        # 将 content/ 下所有 .jsonc 打包到 content.bkp.zip
    """
    with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in sorted(os.listdir(script_dir)):
            if fname.endswith(".jsonc"):
                zf.write(os.path.join(script_dir, fname), fname)


def _check_contentful_renames(template, files, script_dir):
    """预检扫描：检测所有目标文件中是否存在模板未定义的、有实际内容的字段。

    在正式执行格式刷之前运行，防止因模板变更导致的数据丢失。
    如果发现任何有内容的"孤儿字段"，会阻止同步并要求用户先手动迁移数据。

    Args:
        template: 模板数据字典（load_jsonc 后的结果）
        files: 要检查的文件名列表（仅文件名，不含路径）
        script_dir: 文件所在目录的完整路径

    Returns:
        (bool, dict): 元组
            - bool: True 表示安全（无内容丢失风险），可以继续同步
            - dict: {文件名: [警告信息列表]}，记录每个文件中有内容的旧字段

    示例:
        template = {"name": "乾"}
        files = ["01_乾.jsonc"]
        safe, warnings = _check_contentful_renames(template, files, "content/")
        # 如果 01_乾.jsonc 有 template 中不存在的有内容字段，safe 为 False
    """
    structure = extract_structure(template)
    level_keys = _build_level_keys(structure)
    all_warnings = {}

    for fname in files:
        filepath = os.path.join(script_dir, fname)
        data = load_jsonc(filepath)
        warnings = []

        top_valid = level_keys.get((), set())
        for key in list(data.keys()):
            if key not in top_valid and not _is_trivial(data[key]):
                preview = str(data[key])[:40].replace("\n", " ")
                warnings.append(f"顶层「{key}」有内容（{preview}…），但模板中不存在")

        def _check_nested(obj, prefix):
            """递归检查嵌套层级中是否存在模板未定义的有内容字段。"""
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


def run_sync(template_path, script_dir, backup_file, template_display_name, has_lock=False):
    """执行完整的格式刷流程 — 以模板文件为基准，批量同步目录下所有 JSONC 文件。

    完整流程（按顺序执行）：
    1. 加载模板文件，提取字段骨架结构（extract_structure）
    2. 预检扫描 — 检测有内容的孤儿字段，有风险则中止并提示用户迁移
    3. 自动备份 — 将所有 JSONC 文件打包为 zip（do_backup）
    4. 逐个文件处理：
       a. 补齐缺失字段（ensure_structure）
       b. 删除空冗余字段（remove_extra_fields）
       c. 按模板顺序重排字段（reorder_fields）
       d. 按模板格式输出（format_by_template）
    5. 可选同步 lock.jsonc（仅当 has_lock=True 且 lock_utils 可用）

    Args:
        template_path: 模板 JSONC 文件的完整路径，例如 "template.jsonc"
        script_dir: 要同步的 JSONC 数据文件所在目录的完整路径
        backup_file: 备份 zip 文件的完整路径，例如 "content.bkp.zip"
        template_display_name: 模板的显示名称，用于控制台打印，例如 "易经内容模板"
        has_lock: 是否需要同步 lock.jsonc 文件结构（默认 False）

    Returns:
        None（结果通过控制台打印输出）

    示例:
        run_sync(
            template_path="template.jsonc",
            script_dir="content/",
            backup_file="content.bkp.zip",
            template_display_name="内容模板",
            has_lock=False
        )
    """
    if not os.path.exists(template_path):
        print(f"❌ 模板文件不存在: {template_path}")
        return

    template = load_jsonc(template_path)
    structure = extract_structure(template)
    template_fname = os.path.basename(template_path)
    files = sorted([f for f in os.listdir(script_dir)
                    if f.endswith(".jsonc") and f != template_fname and f != "lock.jsonc"])

    print(f"📐 模板: {template_display_name}  ({len(structure)} 个字段路径)")
    print(f"🔍 预检 {len(files)} 个文件...")
    safe, content_warnings = _check_contentful_renames(template, files, script_dir)

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
        print(f"\n👉 请先迁移有内容的字段后再运行格式刷。\n")
        return

    print("✅ 无内容丢失风险，执行同步。\n")
    backup_name = os.path.basename(backup_file)
    print(f"📦 自动备份 → {backup_name}")
    do_backup(script_dir, backup_file)

    updated = 0
    refreshed = 0
    for fname in files:
        filepath = os.path.join(script_dir, fname)
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

    # 同步 lock.jsonc（如果存在 lock_utils 且 has_lock=True）
    if has_lock:
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            sys.path.insert(0, here)
            from lock_utils import sync_lock_structure
            sync_lock_structure(template_path)
            print("🔒 lock.jsonc 结构已同步")
        except ImportError:
            print("⚠️  lock_utils 不可用，跳过 lock.jsonc 同步")
