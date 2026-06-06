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
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    cleaned = re.sub(r"//.*", "", raw)
    return json.loads(cleaned)


def save_jsonc(path, data):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text + "\n")


def load_lock():
    if not os.path.exists(LOCK_FILE):
        return None
    return load_jsonc(LOCK_FILE)


def save_lock(data):
    save_jsonc(LOCK_FILE, data)


def _parse_path(path_str):
    """解析路径 'nishi.diagram.description[0]' → [(key, index_or_None), ...]"""
    steps = []
    for part in path_str.split("."):
        m = re.match(r'^(.+?)\[(\d+|\*)\]$', part)
        if m:
            steps.append((m.group(1), m.group(2)))
        else:
            steps.append((part, None))
    return steps


def _nav_redirect(current, idx):
    """若 current 是数组包装 dict（有 _items），且有数组下标，则重定向到 _items。"""
    if isinstance(current, dict) and "_items" in current and idx is not None:
        return current["_items"]
    return current


def is_locked(path_str):
    """检查字段路径是否被锁定（结构锁：≥1）。
    规则：遍历完整路径，取所有层级 all 和叶子值的最大锁级别。
    返回 (locked: bool, reason: str)
    """
    level, reason = _check_lock(path_str)
    return level >= 1, reason


def is_content_locked(path_str):
    """检查字段路径是否被内容锁定（内容锁：≥2）。
    返回 (content_locked: bool, reason: str)
    """
    level, reason = _check_lock(path_str)
    return level >= 2, reason


def _check_lock(path_str):
    """检查字段路径的锁定状态。
    遍历完整路径，追踪沿途所有层级 all 和叶子值的最大锁级别。
    返回 (max_level: int, reason: str)
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
    """获取容器路径下所有子字段的最大锁级别（0/1/2），用于父容器显示子级锁状态。"""
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
    """新增字段后同步 lock.jsonc。
    parent_path: 父容器路径，'' 表示根层级
    field_name: 新字段名
    is_dict: True=对象, False=文本/数组
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
    """删除字段后同步 lock.jsonc。"""
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
    """重命名字段后同步 lock.jsonc。"""
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
    """获取锁树结构，用于展示。返回 {path: value} 映射。"""
    lock = load_lock()
    if not lock:
        return {}

    def _walk(obj, prefix):
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
    """设置字段的锁定值(0或1)。支持 all 字段和 _items 数组包装。"""
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
    """根据模板重建 lock.jsonc 结构，保留已有的锁定值。

    做什么：
      - 新增字段 → 默认 unlocked（0）
      - 删除字段 → 从 lock 中移除
      - 排序 → 按模板顺序排列（all 恒在最前，_items 在最后）
      - 已有锁值 → 保留（all 保持原值，叶子 0/1 保持原值）

    应在 sync_structure.py 修改完数据文件后调用。
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
