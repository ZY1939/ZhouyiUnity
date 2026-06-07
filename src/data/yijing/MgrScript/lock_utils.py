#!/usr/bin/env python3
"""字段锁定工具 — 检查字段是否被锁定，同步新增字段到 lock.jsonc。

lock.jsonc 结构对齐模板(01_乾.jsonc)，但叶子值为整数(0/1)，dict 容器有 all 字段。
  - all: 1 → 该层级下所有字段被锁定（权重最高，覆盖子级设置）
  - 叶子: 1 → 该字段被锁定
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
DATA_DIR = os.path.join(PARENT, "content")
TEMPLATE_FILE = os.path.join(DATA_DIR, "01_乾.jsonc")
LOCK_FILE = os.path.join(DATA_DIR, "lock.jsonc")


def load_jsonc(path):
    """加载 JSONC 文件（支持 // 注释的 JSON 文件）。

    JSONC 是带行注释的 JSON 格式，本函数先用正则去掉所有 // 注释行，
    再用标准 json.loads 解析，让数据文件可以写注释方便人类阅读。

    Args:
        path (str): JSONC 文件的绝对或相对路径。

    Returns:
        dict 或 list: 解析后的 Python 数据结构。与 json.load 返回类型一致，
        通常是 dict（JSON 对象）或 list（JSON 数组）。

    示例:
        >>> data = load_jsonc("content/01_乾.jsonc")
        >>> print(data["name"])
        乾
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    cleaned = re.sub(r"//.*", "", raw)
    return json.loads(cleaned)


def save_jsonc(path, data):
    """保存数据到 JSONC 文件（带缩进格式的 JSON，方便人类阅读）。

    注意：保存的是纯 JSON 格式（带 2 空格缩进），不会写入 // 注释。
    如需保留注释，请在源码中手动维护。

    Args:
        path (str): 目标文件路径。文件不存在则创建，存在则覆盖。
        data (dict 或 list): 要保存的 Python 数据结构。

    Returns:
        None: 无返回值。写入成功则静默完成，失败会抛出异常。

    示例:
        >>> save_jsonc("lock.jsonc", {"name": 1, "description": 0})
        # 文件内容为格式化的 JSON，中文不会转义（ensure_ascii=False）
    """
    text = json.dumps(data, ensure_ascii=False, indent=2)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text + "\n")


def load_lock():
    """加载锁文件 lock.jsonc。

    锁文件记录哪些字段被锁定（以及锁级别），是数据库字段保护的核心配置。
    如果文件不存在，返回 None（调用方应视为"无锁，所有字段可编辑"）。

    Args:
        无参数。

    Returns:
        dict 或 None: 锁数据字典（结构与模板文件对齐，叶子值为 0/1/2）。
        文件不存在时返回 None。

    示例:
        >>> lock = load_lock()
        >>> if lock is None:
        ...     print("锁文件不存在，所有字段可自由编辑")
    """
    if not os.path.exists(LOCK_FILE):
        return None
    return load_jsonc(LOCK_FILE)


def save_lock(data):
    """保存锁数据到 lock.jsonc 文件。

    将内存中的锁数据结构写回磁盘。通常在对锁进行了修改
    （如设置锁定值、新增/删除字段、重建结构）之后调用。

    Args:
        data (dict): 锁数据字典，结构与模板对齐，叶子值为 0（未锁定）、
                     1（结构锁）或 2（内容锁）。

    Returns:
        None: 无返回值。

    示例:
        >>> lock = load_lock()
        >>> lock["nishi"]["description"] = 1  # 锁定描述字段
        >>> save_lock(lock)
    """
    save_jsonc(LOCK_FILE, data)


def _parse_path(path_str):
    """解析路径字符串为导航步骤列表。

    将点号分隔的路径字符串拆成一个个 (key, index) 元组，方便后续在 JSON
    树中逐层导航。支持数组索引（[0]、[*]），[*] 表示"数组的任意元素"。

    Args:
        path_str (str): 用 '.' 分隔的路径字符串。
                        例如 "nishi.diagram.description[0]" 或 "trigrams[*].name"。

    Returns:
        list[tuple]: 步骤列表，每个元素为 (key: str, index: str 或 None)。
                     例: "nishi.diagram.description[0]"
                     → [('nishi', None), ('diagram', None), ('description', '0')]

    示例:
        >>> _parse_path("nishi.description[0]")
        [('nishi', None), ('description', '0')]
        >>> _parse_path("trigrams[*].name")
        [('trigrams', '*'), ('name', None)]
    """
    steps = []
    for part in path_str.split("."):
        m = re.match(r'^(.+?)\[(\d+|\*)\]$', part)
        if m:
            steps.append((m.group(1), m.group(2)))
        else:
            steps.append((part, None))
    return steps


def _nav_redirect(current, idx):
    """处理数组包装的重定向。

    锁结构中数组用 {all: N, _items: [...]}  包装。当导航到数组包装节点
    且有数组下标时，自动穿透到 _items 列表。这是内部导航辅助函数。

    Args:
        current (dict 或 list): 当前导航到的节点。
        idx (str 或 None): 数组索引（如 '0'、'*'），None 表示不是数组访问。

    Returns:
        dict 或 list: 如果 current 是数组包装 dict 且 idx 不为 None，
                      返回 current["_items"]；否则返回 current 本身。

    示例:
        >>> node = {"all": 0, "_items": [{"name": 1}]}
        >>> _nav_redirect(node, "0")
        [{"name": 1}]  # 穿透到 _items
        >>> _nav_redirect(node, None)
        {"all": 0, "_items": [...]}  # 无下标，保持原样
    """
    if isinstance(current, dict) and "_items" in current and idx is not None:
        return current["_items"]
    return current


def is_locked(path_str):
    """判断字段是否被锁定（结构锁或内容锁，级别 >= 1）。

    锁分两级：
    - 1 = 结构锁：字段名、类型、结构不可修改，内容可编辑
    - 2 = 内容锁：连内容也不可修改（通常用于经典原文等）

    本函数只要字段被任意级别锁定就返回 True。

    Args:
        path_str (str): 字段路径，如 "nishi.diagram.description[0]"。

    Returns:
        tuple[bool, str]: (是否锁定, 原因说明)。
                          未锁定时 reason 为空字符串。

    示例:
        >>> is_locked("nishi.description")
        (True, "层级「nishi」all=1 结构锁")
        >>> is_locked("name")
        (False, "")
    """
    level, reason = _check_lock(path_str)
    return level >= 1, reason


def is_content_locked(path_str):
    """判断字段是否被内容锁锁定（级别 >= 2）。

    内容锁（级别 2）是最严格的锁：字段名、结构和内容均不可修改。
    通常用于保护经典原文、权威数据等不容更改的内容。

    Args:
        path_str (str): 字段路径，如 "nishi.diagram.description[0]"。

    Returns:
        tuple[bool, str]: (是否内容锁定, 原因说明)。
                          未锁定时 reason 为空字符串。

    示例:
        >>> is_content_locked("nishi.original_text")
        (True, "层级「nishi」all=2 内容锁")
        >>> is_content_locked("nishi.notes")
        (False, "")
    """
    level, reason = _check_lock(path_str)
    return level >= 2, reason


def _check_lock(path_str):
    """遍历路径检查字段的锁级别（内部核心函数）。

    沿路径逐层导航，追踪所有层级的 all 值和最终叶子值，
    返回沿途遇到的最大锁级别。is_locked / is_content_locked 均基于此函数。

    规则：取路径上所有 all 值和叶子值的最大值作为最终锁级别。
    例如父层 all=2 子层 all=1 → max=2。

    Args:
        path_str (str): 字段路径，如 "nishi.diagram.description[0]"。

    Returns:
        tuple[int, str]: (最大锁级别, 原因说明)。
                         0 = 未锁定，1 = 结构锁，2 = 内容锁。
                         未锁定时 reason 为空字符串。

    示例:
        >>> _check_lock("nishi.description")
        (1, "层级「nishi」all=1 结构锁")
        >>> _check_lock("unknown_field")
        (0, "路径不存在(unknown_field)")
    """
    lock = load_lock()
    if not lock:
        return 0, "无锁文件"

    steps = _parse_path(path_str)
    current = lock
    max_level = 0

    for i, (key, idx) in enumerate(steps):
        # 导航到 key
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list):
            idx_int = 0 if idx in (None, "*") else int(idx)
            if idx_int < len(current):
                current = current[idx_int]
            else:
                return 0, "路径不存在(数组越界)"
            continue
        else:
            return 0, f"路径不存在({key})"

        # 检查当前容器的 all
        all_val = current.get("all", 0) if isinstance(current, dict) else 0
        if all_val > max_level:
            max_level = all_val
            label = "内容锁" if all_val >= 2 else "结构锁"
            path_label = ".".join(s[0] for s in steps[:i+1])
            reason = f"层级「{path_label}」all={all_val} {label}"

        # _items 重定向（数组包装 → 展开为列表）
        if isinstance(current, dict) and "_items" in current and idx is not None:
            current = current["_items"]

        # 数组索引访问
        if isinstance(current, list) and idx is not None:
            idx_int = 0 if idx == "*" else int(idx)
            if idx_int < len(current):
                current = current[idx_int]
            else:
                return 0, "路径不存在(数组越界)"

    # 检查叶子值
    if isinstance(current, (int, float)):
        leaf_val = int(current)
        if leaf_val > max_level:
            max_level = leaf_val
            label = "内容锁" if leaf_val >= 2 else "结构锁"
            reason = f"字段「{path_str}」={leaf_val} {label}"

    if max_level == 0:
        return 0, ""
    return max_level, reason


def get_max_child_lock(path_str):
    """获取容器下所有子节点的最大锁级别。

    递归遍历路径指定的容器，找出其所有后代节点（包括 _items 展开的数组元素）
    中的最高锁值。用于在 UI 中显示"此容器内是否有被锁定的子项"。

    Args:
        path_str (str): 容器路径，如 "nishi" 或 ""（根层级）。

    Returns:
        int: 最大锁级别（0=无锁定, 1=有结构锁, 2=有内容锁）。

    示例:
        >>> get_max_child_lock("nishi")
        2  # nishi 下某个子字段有内容锁
        >>> get_max_child_lock("")
        1  # 整棵树最高锁级别为结构锁
    """
    lock = load_lock()
    if not lock:
        return 0

    steps = _parse_path(path_str)
    current = lock
    for key, idx in steps:
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list):
            idx_int = 0 if idx in (None, "*") else int(idx)
            if idx_int < len(current):
                current = current[idx_int]
            else:
                return 0
            continue
        else:
            return 0
        if isinstance(current, dict) and "_items" in current and idx is not None:
            current = current["_items"]
        if isinstance(current, list) and idx is not None:
            idx_int = 0 if idx == "*" else int(idx)
            if idx_int < len(current):
                current = current[idx_int]
            else:
                return 0

    def _max_in_tree(node):
        """递归遍历锁树节点，返回子树中的最大锁级别。"""
        if isinstance(node, dict):
            best = node.get("all", 0)
            for k, v in node.items():
                if k == "all":
                    continue
                if k == "_items":
                    if isinstance(v, list):
                        for item in v:
                            best = max(best, _max_in_tree(item))
                elif isinstance(v, (int, float)):
                    best = max(best, int(v))
                elif isinstance(v, (dict, list)):
                    best = max(best, _max_in_tree(v))
            return best
        elif isinstance(node, list):
            return max((_max_in_tree(item) for item in node), default=0)
        elif isinstance(node, (int, float)):
            return int(node)
        return 0

    return _max_in_tree(current)


def sync_new_field(parent_path, field_name, is_dict=False):
    """新增字段后自动同步 lock.jsonc（在正确位置插入默认锁值）。

    当数据文件中新增了一个字段，调用此函数在锁文件中对应位置
    插入默认值（未锁定状态），确保锁结构始终与数据文件对齐。

    Args:
        parent_path (str): 父容器路径。'' 或 '.' 表示根层级。
                          例如 "nishi.diagram" 表示在 diagram 下添加。
        field_name (str): 新字段的名称，如 "new_note"。
        is_dict (bool): 新字段是否为对象类型（dict）。
                        True → 插入 {"all": 0}（对象节点带 all 控制）
                        False → 插入 0（叶子节点，纯锁值）

    Returns:
        None: 无返回值。若锁文件不存在或路径无效则静默跳过。

    示例:
        >>> sync_new_field("nishi", "author", is_dict=False)
        # 在 lock["nishi"]["author"] = 0
        >>> sync_new_field("", "extra", is_dict=True)
        # 在 lock["extra"] = {"all": 0}
    """
    lock = load_lock()
    if not lock:
        return

    if not parent_path:
        target = lock
    else:
        steps = _parse_path(parent_path)
        current = lock
        for key, idx in steps:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list):
                idx_int = 0 if idx in (None, "*") else int(idx)
                if idx_int < len(current):
                    current = current[idx_int]
                else:
                    return
                continue
            else:
                return

            # _items 重定向
            if isinstance(current, dict) and "_items" in current and idx is not None:
                current = current["_items"]

            # 数组索引
            if isinstance(current, list) and idx is not None:
                idx_int = 0 if idx == "*" else int(idx)
                if idx_int < len(current):
                    current = current[idx_int]
                else:
                    return

        # 若容器是数组包装，在 _items[0] 中添加
        if isinstance(current, dict) and "_items" in current:
            target = current["_items"][0] if current["_items"] else {}
        else:
            target = current

    if isinstance(target, dict) and field_name not in target:
        target[field_name] = {"all": 0} if is_dict else 0
        save_lock(lock)


def sync_delete_field(path_str):
    """删除字段后自动同步 lock.jsonc（移除对应锁条目）。

    当数据文件中删除了一个字段，调用此函数从锁文件中删除对应位置的锁记录，
    保证锁文件不包含"幽灵字段"。

    Args:
        path_str (str): 要删除的字段完整路径，如 "nishi.diagram.old_field"。

    Returns:
        None: 无返回值。若锁文件不存在、路径无效或字段不存在则静默跳过。

    示例:
        >>> sync_delete_field("nishi.obsolete_note")
        # 从 lock["nishi"] 中删除 "obsolete_note" 键
        >>> sync_delete_field("trigrams[*].temp")
        # 从数组包装 _items[0] 中删除 "temp"
    """
    lock = load_lock()
    if not lock:
        return

    steps = _parse_path(path_str)
    if not steps:
        return

    # 导航到父容器
    *parent_steps, (last_key, last_idx) = steps
    current = lock
    for key, idx in parent_steps:
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list):
            idx_int = 0 if idx in (None, "*") else int(idx)
            if idx_int < len(current):
                current = current[idx_int]
            else:
                return
            continue
        else:
            return

        # _items 重定向
        if isinstance(current, dict) and "_items" in current and idx is not None:
            current = current["_items"]

        # 数组索引
        if isinstance(current, list) and idx is not None:
            idx_int = 0 if idx == "*" else int(idx)
            if idx_int < len(current):
                current = current[idx_int]
            else:
                return

    # 若容器是数组包装，从 _items[0] 中删除
    if isinstance(current, dict) and "_items" in current:
        target = current["_items"][0] if current["_items"] else {}
    else:
        target = current

    if isinstance(target, dict) and last_key in target:
        del target[last_key]
        save_lock(lock)


def sync_rename_field(path_str, old_key, new_key):
    """重命名字段后自动同步 lock.jsonc（保留原有锁值）。

    当数据文件中某字段改名，调用此函数在锁文件中同步重命名，
    原有锁值（0/1/2）会保留到新字段名下。

    Args:
        path_str (str): 父容器路径（非包含旧字段名的完整路径）。
                        例如字段 "nishi.old_name" 改名时，传 "nishi"。
        old_key (str): 旧字段名，如 "old_name"。
        new_key (str): 新字段名，如 "new_name"。

    Returns:
        None: 无返回值。若锁文件不存在、路径无效或旧字段不存在则静默跳过。

    示例:
        >>> sync_rename_field("nishi", "old_title", "new_title")
        # lock["nishi"]["new_title"] = lock["nishi"].pop("old_title")
        >>> sync_rename_field("trigrams[*]", "old_name", "new_name")
        # 在数组包装 _items[0] 中完成重命名
    """
    lock = load_lock()
    if not lock:
        return

    steps = _parse_path(path_str)
    *parent_steps, (_, last_idx) = steps
    current = lock
    for key, idx in parent_steps:
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list):
            idx_int = 0 if idx in (None, "*") else int(idx)
            if idx_int < len(current):
                current = current[idx_int]
            else:
                return
            continue
        else:
            return

        # _items 重定向
        if isinstance(current, dict) and "_items" in current and idx is not None:
            current = current["_items"]

        # 数组索引
        if isinstance(current, list) and idx is not None:
            idx_int = 0 if idx == "*" else int(idx)
            if idx_int < len(current):
                current = current[idx_int]
            else:
                return

    # 若容器是数组包装，在 _items[0] 中重命名
    if isinstance(current, dict) and "_items" in current:
        target = current["_items"][0] if current["_items"] else {}
    else:
        target = current

    if isinstance(target, dict) and old_key in target:
        target[new_key] = target.pop(old_key)
        save_lock(lock)


def get_lock_tree():
    """获取完整的锁状态树，展开为扁平化 {路径: 锁值} 字典。

    递归遍历锁文件的整个 JSON 树，将所有叶子节点的锁值展开为
    路径→值的映射。_items 数组包装会被透明展开（用 [*] 表示），
    方便展示和调试。

    Args:
        无参数。

    Returns:
        dict[str, int]: 路径到锁值的映射。
                        键: 如 "nishi.description" 或 "trigrams[*].name"
                        值: 0（未锁定）/ 1（结构锁）/ 2（内容锁）

    示例:
        >>> tree = get_lock_tree()
        >>> for path, val in tree.items():
        ...     if val >= 2:
        ...         print(f"内容锁: {path}")
        nishi.original_text
    """
    lock = load_lock()
    if not lock:
        return {}

    def _walk(obj, prefix):
        """递归遍历锁树，将叶子节点的锁值展开为 {路径: 锁值} 映射。"""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "_items":
                    continue  # _items 是内部包装，对外透明
                path = f"{prefix}.{k}" if prefix else k
                if k == "all":
                    yield (path, v)
                elif isinstance(v, dict):
                    # 数组包装：展开 _items
                    if "_items" in v and isinstance(v["_items"], list) and len(v["_items"]) > 0:
                        yield from _walk(v["_items"][0], f"{path}[*]")
                    else:
                        yield from _walk(v, path)
                elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                    yield from _walk(v[0], f"{path}[*]")
                else:
                    yield (path, v)

    return dict(_walk(lock, ""))


def set_lock(path_str, value):
    """设置指定字段的锁定值。

    沿路径导航到目标字段，将其锁值设为指定整数（通常 0=解锁, 1=结构锁, 2=内容锁）。
    支持设置普通叶子节点、容器的 all 字段，以及 _items 数组包装内的元素。

    Args:
        path_str (str): 字段路径，如 "nishi.all" 或 "nishi.description"。
        value (int): 新的锁值。0=解锁, 1=结构锁, 2=内容锁。

    Returns:
        bool: True=设置成功并已保存到文件, False=失败（路径不存在或锁文件缺失）。

    示例:
        >>> set_lock("nishi.all", 1)
        True  # nishi 容器下所有字段被结构锁保护
        >>> set_lock("nishi.description", 2)
        True  # 描述字段被内容锁保护（不可修改内容）
        >>> set_lock("nonexistent.field", 0)
        False  # 路径不存在
    """
    lock = load_lock()
    if not lock:
        print("  ❌ lock.jsonc 不存在")
        return False

    steps = _parse_path(path_str)
    if not steps:
        return False

    current = lock
    for i, (key, idx) in enumerate(steps):
        is_last = (i == len(steps) - 1)

        # 导航到 key
        if isinstance(current, dict) and key in current:
            if is_last:
                # 最后一层：直接设置值
                current[key] = value
                save_lock(lock)
                return True
            current = current[key]
        elif isinstance(current, list):
            idx_int = 0 if idx in (None, "*") else int(idx)
            if idx_int < len(current):
                if is_last:
                    current[idx_int] = value
                    save_lock(lock)
                    return True
                current = current[idx_int]
            else:
                return False
        else:
            return False

        # _items 重定向
        if isinstance(current, dict) and "_items" in current and idx is not None:
            current = current["_items"]

        # 数组索引
        if isinstance(current, list) and idx is not None:
            idx_int = 0 if idx == "*" else int(idx)
            if idx_int < len(current):
                if is_last:
                    current[idx_int] = value
                    save_lock(lock)
                    return True
                current = current[idx_int]
            else:
                return False

    return False


def sync_lock_structure(template_path=None):
    """根据模板文件重建 lock.jsonc 的完整结构。

    以模板（通常是 01_乾.jsonc）的 JSON 结构为基准，递归构建锁文件结构：
    - 模板中有但锁文件中没有的字段 → 新增，默认值 0（未锁定）
    - 锁文件中有但模板中没有的字段 → 删除（清理幽灵字段）
    - 模板和锁文件都有的字段 → 保留锁文件中已有的锁值
    - 键顺序 → 按模板顺序排列，all 永远在最前面

    通常在 sync_structure.py 修改完所有数据文件后调用此函数，
    确保锁文件结构与数据文件结构一致。

    Args:
        template_path (str 或 None): 模板文件路径。默认 None 使用
                                      content/01_乾.jsonc（第一卦作为标准模板）。

    Returns:
        None: 无返回值。直接写入 lock.jsonc 文件。

    示例:
        >>> sync_lock_structure()
        # 以 01_乾.jsonc 为基准重建 lock.jsonc
        >>> sync_lock_structure("content/02_坤.jsonc")
        # 以坤卦为模板重建（结构与乾卦相同，结果一样）
    """
    if template_path is None:
        template_path = TEMPLATE_FILE

    tpl = load_jsonc(template_path)
    old = load_lock()

    def _build(tpl_node, old_node):
        """递归构建 lock 节点，从 old_node 继承已有锁值。"""
        if isinstance(tpl_node, dict):
            result = {}
            # all: 继承旧值，没有则默认 0
            if isinstance(old_node, dict):
                result["all"] = old_node.get("all", 0)
            else:
                result["all"] = 0

            for k, v in tpl_node.items():
                old_child = old_node.get(k) if isinstance(old_node, dict) else None
                result[k] = _build(v, old_child)
            return result

        if isinstance(tpl_node, list) and len(tpl_node) > 0 and isinstance(tpl_node[0], dict):
            # 数组包装: {"all": N, "_items": [{...}]}
            result = {}
            if isinstance(old_node, dict):
                result["all"] = old_node.get("all", 0)
            else:
                result["all"] = 0

            old_items = old_node.get("_items", [{}]) if isinstance(old_node, dict) else [{}]
            old_item = old_items[0] if isinstance(old_items, list) and old_items else {}
            result["_items"] = [_build(tpl_node[0], old_item)]
            return result

        if isinstance(tpl_node, list):
            # 普通数组（非对象数组），暂不支持嵌套锁，存 0
            return 0

        # 叶子：继承旧 int 值，默认 0
        if isinstance(old_node, (int, float)):
            return int(old_node)
        return 0

    new_lock = _build(tpl, old if old else {})
    save_lock(new_lock)


if __name__ == "__main__":
    # 测试
    print("lock.jsonc 状态:")
    for path, val in get_lock_tree().items():
        if val >= 2:
            print(f"  🔒* {path}")
        elif val == 1:
            print(f"  🔒 {path}")
