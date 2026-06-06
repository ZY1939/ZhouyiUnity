#!/usr/bin/env python3
"""
易经数据库管理工具 — 命令行交互式管理 64 卦 JSONC 数据库。

功能：
  1. 编辑单卦 — 交互式编辑任意卦的任意字段（含嵌套字段）
  2. 备份数据库 — 将 content/ 下全部 64 个 JSONC 文件压缩备份到 content.bkp.zip
  3. 恢复数据库 — 从 content.bkp.zip 解压恢复全部 JSONC 文件（覆盖当前）
  4. 批量字段操作 — 对所有 64 卦进行「字段重命名」「字段删除」「字段置空」「字段设置」等批量操作
  5. 查看单卦 — 解析并打印任意卦的全部字段内容

用法：
    cd src/data/yijing
    python3 MgrScript/yijing_manager.py

依赖：
    MgrScript/sync_structure.py — 提供 format_by_template 模板化 JSONC 输出
    content/01_乾.jsonc       — 作为输出格式模板
    content/*.jsonc           — 64 卦数据文件（被管理对象）
"""

import json
import os
import re
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
DATA_DIR = os.path.join(PARENT, "content")
TEMPLATE_FILE = os.path.join(DATA_DIR, "01_乾.jsonc")

sys.path.insert(0, HERE)
from sync_structure import format_by_template, load_jsonc as _load_jsonc_sync
sys.path.insert(0, HERE)
from lock_utils import is_locked, is_content_locked, get_max_child_lock, sync_new_field, sync_delete_field, sync_rename_field


def save_jsonc(path, data):
    """写入 JSONC 文件，输出格式与模板（01_乾.jsonc）严格一致"""
    template = _load_jsonc_sync(TEMPLATE_FILE)
    text = format_by_template(data, template, TEMPLATE_FILE)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


XIANTIAN_NUM = {"乾": 1, "兑": 2, "离": 3, "震": 4, "巽": 5, "坎": 6, "艮": 7, "坤": 8}
NUM_TO_XIANTIAN = {v: k for k, v in XIANTIAN_NUM.items()}


# ═══════════════════════════════════════════════════════════════
#  JSONC 读写
# ═══════════════════════════════════════════════════════════════

def load_jsonc(path):
    """读取 JSONC 文件，去掉 // 注释后解析为 dict"""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    cleaned = re.sub(r"//.*", "", raw)
    return json.loads(cleaned)


def load_all():
    """加载全部 64 卦，返回 {id: data}。跳过 lock.jsonc。"""
    result = {}
    for fname in sorted(os.listdir(DATA_DIR)):
        if fname.endswith(".jsonc") and fname != "lock.jsonc":
            data = load_jsonc(os.path.join(DATA_DIR, fname))
            result[data["id"]] = data
    return result


def save_all(hex_dict):
    """将 {id: data} 写回全部 64 个文件"""
    for hid, data in hex_dict.items():
        name = data["name"]
        fname = f"{hid:02d}_{name}.jsonc"
        save_jsonc(os.path.join(DATA_DIR, fname), data)


def get_file_by_id(hid):
    """根据卦 ID(1-64) 返回对应的文件路径，找不到返回 None"""
    prefix = f"{hid:02d}"
    for fname in sorted(os.listdir(DATA_DIR)):
        if fname.startswith(prefix) and fname.endswith(".jsonc"):
            return os.path.join(DATA_DIR, fname)
    return None


# ═══════════════════════════════════════════════════════════════
#  备份 / 恢复
# ═══════════════════════════════════════════════════════════════

def backup():
    """列出 PARENT 下所有目录，用户选择备份。0=全部，q=退出。"""
    SKIP_DIRS = {"__pycache__", ".git", ".claude", "node_modules", ".DS_Store"}
    dirs = [d for d in sorted(os.listdir(PARENT))
            if os.path.isdir(os.path.join(PARENT, d)) and not d.startswith(".") and d not in SKIP_DIRS]
    if not dirs:
        print("❌ 没有可备份的目录")
        return

    print("\n  可备份的目录:")
    print(f"    0. 全部备份")
    for i, d in enumerate(dirs, 1):
        dpath = os.path.join(PARENT, d)
        file_count = len([f for f in os.listdir(dpath) if os.path.isfile(os.path.join(dpath, f))])
        print(f"    {i}. {d}/  ({file_count} 个文件)")
    print(f"    q. 退出")

    try:
        choice = input("  请选择 (0=全部, q=退出): ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice.lower() == "q":
        return

    if choice == "0":
        targets = dirs
    else:
        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(dirs)):
                print("  ❌ 无效选择")
                return
            targets = [dirs[idx]]
        except ValueError:
            print("  ❌ 无效选择")
            return

    for d in targets:
        dpath = os.path.join(PARENT, d)
        bkp_path = os.path.join(PARENT, f"{d}.bkp.zip")
        if os.path.exists(bkp_path):
            os.remove(bkp_path)
        shutil.make_archive(bkp_path.replace(".zip", ""), "zip", dpath)
        file_count = len([f for f in os.listdir(dpath) if os.path.isfile(os.path.join(dpath, f))])
        print(f"  ✅ {d}/ ({file_count} 文件) → {d}.bkp.zip")


def restore():
    """列出 PARENT 下所有 .bkp.zip 文件，用户选择恢复。0=全部，q=退出。"""
    bkps = sorted([f for f in os.listdir(PARENT) if f.endswith(".bkp.zip")])
    if not bkps:
        print("❌ 没有找到 .bkp.zip 备份文件")
        return

    print("\n  可恢复的备份:")
    print(f"    0. 全部恢复")
    for i, f in enumerate(bkps, 1):
        fpath = os.path.join(PARENT, f)
        size_kb = os.path.getsize(fpath) // 1024
        print(f"    {i}. {f}  ({size_kb} KB)")
    print(f"    q. 退出")

    try:
        choice = input("  请选择 (0=全部, q=退出): ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice.lower() == "q":
        return

    if choice == "0":
        targets = bkps
    else:
        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(bkps)):
                print("  ❌ 无效选择")
                return
            targets = [bkps[idx]]
        except ValueError:
            print("  ❌ 无效选择")
            return

    print(f"\n  [警告] 恢复将覆盖 {', '.join(t.replace('.bkp.zip', '') + '/' for t in targets)}中的现有文件")
    confirm = input("  [确认] 恢复？(y/1=继续, 其他取消): ").strip()
    if confirm.lower() not in ("y", "yes", "1"):
        print("  ❌ 已取消")
        return

    for f in targets:
        fpath = os.path.join(PARENT, f)
        dirname = f.replace(".bkp.zip", "")
        extract_dir = os.path.join(PARENT, dirname)
        with zipfile.ZipFile(fpath, "r") as zf:
            zf.extractall(extract_dir)
        count = len(zf.namelist())
        print(f"  ✅ {f} → {dirname}/ ({count} 文件已恢复)")


# ═══════════════════════════════════════════════════════════════
#  路径解析 & 编辑
# ═══════════════════════════════════════════════════════════════

def _parse_path(path):
    """解析路径字符串 'nishi.diagram.description[0]' 或 'lines[*].nishi'
    返回 [(key, index_or_None_or_wildcard), ...]
    idx='*' 表示通配符（遍历数组所有元素）"""
    steps = []
    for part in path.split("."):
        m = re.match(r'^(.+?)\[(\d+|\*)\]$', part)
        if m:
            idx_str = m.group(2)
            steps.append((m.group(1), "*" if idx_str == "*" else int(idx_str)))
        else:
            steps.append((part, None))
    return steps


def _get_nested(data, path):
    """读取嵌套值，支持数组下标 [0] 和通配符 [*]（返回第一个元素的值）。"""
    steps = _parse_path(path)
    current = data
    for key, idx in steps:
        # 导航到 key
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
        # 通配符：取第一个元素
        if idx == "*":
            if isinstance(current, list) and len(current) > 0:
                current = current[0]
            else:
                return None
        elif idx is not None:
            if isinstance(current, list) and idx < len(current):
                current = current[idx]
            else:
                return None
    return current


def _set_nested(data, path, value):
    """设置嵌套值，支持数组下标 [0] 和通配符 [*]（遍历所有元素）。"""
    steps = _parse_path(path)
    _set_nested_steps(data, steps, value)


def _set_nested_steps(data, steps, value):
    """递归实现 _set_nested，支持 [*] 通配符。"""
    if not steps:
        return
    key, idx = steps[0]
    rest = steps[1:]

    if idx == "*":
        # 通配符：对数组每个元素递归
        lst = data.get(key, []) if isinstance(data, dict) else data
        if isinstance(lst, list):
            for item in lst:
                if isinstance(item, dict):
                    _set_nested_steps(item, rest, value)
        return

    if len(steps) == 1:
        # 最后一层：写入值
        if isinstance(data, list):
            while len(data) <= idx:
                data.append("")
            data[idx] = value
        else:
            if idx is not None:
                if key not in data:
                    data[key] = []
                lst = data[key]
                while len(lst) <= idx:
                    lst.append("")
                lst[idx] = value
            else:
                data[key] = value
    else:
        # 中间层：导航
        if isinstance(data, list):
            while len(data) <= idx:
                data.append({})
            _set_nested_steps(data[idx], rest, value)
        else:
            if key not in data:
                next_idx = rest[0][1] if rest else None
                data[key] = [] if next_idx is not None else {}
            child = data[key]
            if idx is not None and isinstance(child, list):
                while len(child) <= idx:
                    child.append({} if rest else "")
                _set_nested_steps(child[idx], rest, value)
            else:
                _set_nested_steps(child, rest, value)


def _print_fields(data, prefix="", show_empty=True):
    """递归打印一个 dict 的所有叶子字段路径和值，数组逐元素展示"""
    if isinstance(data, dict):
        for k, v in data.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                _print_fields(v, full_key, show_empty)
            elif isinstance(v, list):
                if len(v) > 0 and isinstance(v[0], dict):
                    for i, item in enumerate(v):
                        _print_fields(item, f"{full_key}[{i}]", show_empty)
                else:
                    # 非对象数组（字符串等）：逐条展示
                    for i, item in enumerate(v):
                        val_str = str(item) if item is not None else "null"
                        if show_empty or (item and item != "（待补充）" and item != ""):
                            print(f"  {full_key}[{i}]: {_trunc(val_str, 100)}")
                    if len(v) == 0:
                        print(f"  {full_key}: []")
            else:
                val_str = str(v) if v is not None else "null"
                if show_empty or (v and v != "（待补充）" and v != ""):
                    print(f"  {full_key}: {_trunc(val_str, 80)}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                _print_fields(item, f"{prefix}[{i}]", show_empty)
            else:
                val_str = str(item) if item is not None else "null"
                print(f"  {prefix}[{i}]: {_trunc(val_str, 80)}")


def _trunc(s, max_len):
    return s if len(s) <= max_len else s[:max_len] + "…"


def _list_data_fields(data):
    """从实际数据提取所有叶子字段路径和值，返回 [(path, value), ...]"""
    fields = []

    def _walk(obj, prefix):
        if isinstance(obj, dict):
            for k, v in obj.items():
                path = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    _walk(v, path)
                elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                    for i, item in enumerate(v):
                        _walk(item, f"{path}[{i}]")
                elif isinstance(v, list):
                    for i, item in enumerate(v):
                        fields.append((f"{path}[{i}]", item))
                    if len(v) == 0:
                        fields.append((path, v))
                else:
                    fields.append((path, v))

    _walk(data, "")
    return fields


def edit_hexagram(hid):
    """交互式编辑单卦 — 列出所有字段，按序号选择编辑"""
    filepath = get_file_by_id(hid)
    if not filepath:
        print(f"❌ 未找到 ID={hid} 的卦文件")
        return

    while True:
        data = load_jsonc(filepath)
        fields = _list_data_fields(data)

        print(f"\n  正在编辑: {data['name']} ({data.get('full_name', '')})")
        print("  " + "─" * 55)
        for i, (path, val) in enumerate(fields, 1):
            if val in (None, "", "（待补充）", [], {}):
                val_str = "(空)"
            else:
                val_str = _trunc(str(val), 50).replace("\n", " ")
            print(f"  {i:>3}. {path}: {val_str}")
        print(f"    0. 返回上级")
        print("  " + "─" * 55)

        try:
            choice = input("  选择字段序号 (0返回): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice in ("0", "\\0", "q", "Q"):
            break

        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(fields)):
                print("  ❌ 无效序号")
                continue
        except ValueError:
            print("  ❌ 无效输入")
            continue

        path, old_val = fields[idx]

        # 检查内容锁
        content_locked, lock_reason = is_content_locked(path)
        if content_locked:
            print(f"  🔒* {lock_reason}，无法编辑内容")
            input("  按回车继续...")
            continue

        print(f"\n  📝 {path}")
        print(f"  当前值: {_trunc(str(old_val), 200)}")
        try:
            new_val = input("  新值 (回车取消): ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not new_val:
            continue

        # 类型转换
        if isinstance(old_val, bool):
            new_val = new_val.lower() in ("true", "1", "yes")
        elif isinstance(old_val, (int, float)):
            try:
                new_val = int(new_val) if isinstance(old_val, int) else float(new_val)
            except ValueError:
                pass
        elif isinstance(old_val, list):
            try:
                new_val = json.loads(new_val)
            except json.JSONDecodeError:
                pass

        _set_nested(data, path, new_val)
        save_jsonc(filepath, data)
        print(f"  ✅ 已更新 {path}")


# ═══════════════════════════════════════════════════════════════
#  批量字段操作
# ═══════════════════════════════════════════════════════════════

def _list_template_fields():
    """从模板提取所有字段路径（含容器和叶子）。返回 [(路径字符串, 样例值, 类型名), ...]"""
    template = load_jsonc(TEMPLATE_FILE)
    fields = []

    def _walk(obj, prefix):
        if isinstance(obj, dict):
            for k, v in obj.items():
                path = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    fields.append((path, f"{{{len(v)} fields}}", "dict"))
                    _walk(v, path)
                elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                    fields.append((path, f"[{len(v)} items]", "list[dict]"))
                    _walk(v[0], f"{path}[*]")
                elif isinstance(v, list):
                    fields.append((path, f"[{len(v)} items]", "list"))
                else:
                    fields.append((path, v, type(v).__name__))

    _walk(template, "")
    return fields


def _show_field_list(fields):
    """打印带序号的字段列表（单行格式）"""
    print("  " + "─" * 55)
    for i, (path, val, typ) in enumerate(fields, 1):
        if val in (None, "", "（待补充）", [], {}):
            preview = "(空)"
        else:
            preview = str(val)[:40].replace("\n", " ")
        print(f"  {i:>3}. {path}: {preview}  ({typ})")
    print(f"    0. 返回")
    print("  " + "─" * 55)


def _pick_field(fields, prompt="请选择字段"):
    """让用户按序号选择字段，循环直到选中或按0退出。
    返回 (path_str, field_name) 或 (None, None)。
    """
    while True:
        _show_field_list(fields)
        choice = input(f"  {prompt} (输入序号): ").strip()
        if choice in ("0", "\\0", "q", "Q"):
            return None, None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(fields):
                path = fields[idx][0]
                leaf = path.split(".")[-1].replace("[*]", "")
                return path, leaf
        except ValueError:
            pass

        print("  ❌ 无效选择")


def _parse_selection(choice, max_n):
    """解析多选输入，支持 单个序号 / 空格逗号分隔 / 范围(如 1-3)。
    返回已去重的有序索引列表(0-based)。无效索引被忽略。"""
    indices = []
    choice = choice.replace(",", " ")
    for part in choice.split():
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                a, b = part.split("-", 1)
                start, end = int(a), int(b)
                for n in range(start, end + 1):
                    idx = n - 1
                    if 0 <= idx < max_n:
                        indices.append(idx)
            except ValueError:
                pass
        else:
            try:
                idx = int(part) - 1
                if 0 <= idx < max_n:
                    indices.append(idx)
            except ValueError:
                pass
    # 去重并保持顺序
    seen = set()
    result = []
    for i in indices:
        if i not in seen:
            seen.add(i)
            result.append(i)
    return result


def _pick_fields(fields, prompt="请选择字段"):
    """多选版字段选择 — 支持 25 26 1-3 格式。返回 [(path_str, leaf), ...]"""
    while True:
        _show_field_list(fields)
        choice = input(f"  {prompt} (支持多选: 1 3 5-7): ").strip()
        if choice in ("0", "\\0", "q", "Q"):
            return []
        indices = _parse_selection(choice, len(fields))
        if indices:
            result = []
            for idx in indices:
                path = fields[idx][0]
                leaf = path.split(".")[-1].replace("[*]", "")
                result.append((path, leaf))
            return result
        print("  ❌ 无效选择")


# ═══════════════════════════════════════════════════════════════
#  锁管理（集成在 yijing_manager 中）
# ═══════════════════════════════════════════════════════════════

def _lock_level_icon(level, inherited=False):
    """锁级别 → 图标。0→'0', 1→'🔒', 2→'🔒*'。inherited=True 加 ↑。"""
    if level >= 2:
        return '🔒*↑' if inherited else '🔒*'
    if level == 1:
        return '🔒↑' if inherited else '🔒'
    return '0'


def _get_lock_display(path_str, is_container, child_level=0):
    """获取字段的锁定显示状态。
    - 自身锁图标: '🔒*', '🔒', '0'
    - 被上级锁定: '🔒*↑', '🔒↑'
    - 容器有更高子级锁: '🔒(🔒*)', '0(🔒*)' 等
    """
    from lock_utils import load_lock
    lock = load_lock()
    if not lock:
        return '0'

    steps = _parse_path(path_str)
    if not steps:
        return '0'

    current = lock
    own_level = 0
    inherited = False

    for i, (key, idx) in enumerate(steps):
        is_last = (i == len(steps) - 1)

        # 导航到 key
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list):
            idx_int = 0 if idx is None else idx
            if idx_int < len(current):
                current = current[idx_int]
                continue
            else:
                return '0'
        else:
            return '0'

        # 检查 all 锁值
        all_val = current.get("all", 0) if isinstance(current, dict) else 0
        if all_val > own_level:
            own_level = all_val
            inherited = not is_last

        # _items 重定向
        if isinstance(current, dict) and "_items" in current and idx is not None:
            current = current["_items"]

        # 数组索引
        if isinstance(current, list) and idx is not None:
            idx_int = 0 if idx == "*" else int(idx)
            if idx_int < len(current):
                current = current[idx_int]
            else:
                return '0'

    # 检查叶子自身锁定
    if is_container:
        leaf_val = current.get("all", 0) if isinstance(current, dict) else 0
    else:
        leaf_val = int(current) if isinstance(current, (int, float)) else 0

    if leaf_val > own_level:
        own_level = leaf_val
        inherited = False

    icon = _lock_level_icon(own_level, inherited)

    # 容器：如果子级锁级别更高，追加 (子图标)
    if is_container and child_level > own_level:
        icon = f"{icon}({_lock_level_icon(child_level)})"

    return icon



def manage_locks():
    """交互式字段锁管理 — 列出字段，支持导航进入子目录、多选锁定/解锁"""
    from lock_utils import load_lock

    template = load_jsonc(TEMPLATE_FILE)
    nav_stack = []  # [(full_path, display_name), ...]

    while True:
        # 导航到当前位置
        current_data = template
        if nav_stack:
            steps = _parse_path(nav_stack[-1][0])
            for key, idx in steps:
                if isinstance(current_data, dict) and key in current_data:
                    current_data = current_data[key]
                elif isinstance(current_data, list) and idx is not None and idx < len(current_data):
                    current_data = current_data[idx]
                else:
                    current_data = {}
                    break

        # 构建当前层级的字段列表
        fields = []  # [(display_name, full_path, is_container, type_desc), ...]
        if isinstance(current_data, dict):
            for k, v in current_data.items():
                full_path = f"{nav_stack[-1][0]}.{k}" if nav_stack else k
                if isinstance(v, dict):
                    fields.append((k, full_path, True, f"{{{len(v)} fields}}"))
                elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                    fields.append((k, full_path, True, f"[{len(v)} items] list[dict]"))
                elif isinstance(v, list):
                    fields.append((k, full_path, False, f"[{len(v)} items] list"))
                else:
                    fields.append((k, full_path, False, type(v).__name__))
        elif isinstance(current_data, list) and len(current_data) > 0 and isinstance(current_data[0], dict):
            # 数组取首项为模板，[*] 代表全部元素，不逐条展开
            item = current_data[0]
            base = nav_stack[-1][0] if nav_stack else ""
            for k, v in item.items():
                full_path = f"{base}[*].{k}" if base else f"[*].{k}"
                if isinstance(v, dict):
                    fields.append((k, full_path, True, f"{{{len(v)} fields}}"))
                elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                    fields.append((k, full_path, True, f"[{len(v)} items] list[dict]"))
                elif isinstance(v, list):
                    fields.append((k, full_path, False, f"[{len(v)} items] list"))
                else:
                    fields.append((k, full_path, False, type(v).__name__))

        # 面包屑
        breadcrumb = " > ".join([name for _, name in nav_stack]) if nav_stack else "根层级"
        print(f"\n  ═══ 字段锁管理 [{breadcrumb}] ═══")
        print("  " + "─" * 60)
        print(f"  {'#':>3}  {'锁':7}  字段")
        print("  " + "─" * 60)

        for i, (name, full_path, is_container, type_desc) in enumerate(fields, 1):
            child_level = get_max_child_lock(full_path) if is_container else 0
            icon = _get_lock_display(full_path, is_container, child_level)
            nav_hint = "  ▶" if is_container else ""
            print(f"  {i:>3}  {icon:<7}  {name}{nav_hint}  ({type_desc})")

        print("  " + "─" * 60)
        print(f"  多选: 1 3 5-7 | * 全选 | --序号 进入子目录 | 0 返回 | q 退出")

        try:
            choice = input("  → ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice in ("q", "Q"):
            return
        if choice in ("0", "\\0"):
            if nav_stack:
                nav_stack.pop()
            else:
                return
            continue

        # 导航：--序号 进入子目录
        if choice.startswith("--"):
            try:
                target_idx = int(choice[2:]) - 1
                if 0 <= target_idx < len(fields):
                    name, full_path, is_container, _ = fields[target_idx]
                    if is_container:
                        nav_stack.append((full_path, name))
                    else:
                        print(f"  ❌ 「{name}」不是容器，无法进入")
                else:
                    print(f"  ❌ 序号超出范围")
            except ValueError:
                print(f"  ❌ 无效序号")
            continue

        # 解析选择：* 全选，或数字多选
        if choice == "*":
            indices = list(range(len(fields)))
        else:
            indices = _parse_selection(choice, len(fields))

        if not indices:
            print("  ❌ 无效选择")
            continue

        # 显示已选字段
        print()
        print(f"  已选 {len(indices)} 个字段:")
        for idx in indices:
            name, full_path, is_container, _ = fields[idx]
            child_level = get_max_child_lock(full_path) if is_container else 0
            icon = _get_lock_display(full_path, is_container, child_level)
            print(f"    {name}  (当前: {icon})")

        # 选择锁级别
        print(f"\n  设置锁级别:")
        print(f"    0 = 解锁")
        print(f"    1 = 🔒  结构锁")
        print(f"    2 = 🔒* 内容锁")
        try:
            level_choice = input("  → 锁级别 (0/1/2, 回车取消): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            continue

        if not level_choice:
            continue
        if level_choice not in ("0", "1", "2"):
            print("  ❌ 无效选择")
            continue

        target_val = int(level_choice)
        if target_val == 2:
            icon_label = "🔒*"
            action_label = "内容锁"
        elif target_val == 1:
            icon_label = "🔒"
            action_label = "结构锁"
        else:
            icon_label = ""
            action_label = "解锁"

        from lock_utils import set_lock as _set_lock
        print()
        for idx in indices:
            name, full_path, is_container, _ = fields[idx]
            lock_path = f"{full_path}.all" if is_container else full_path
            ok = _set_lock(lock_path, target_val)
            if ok:
                status = f"{icon_label} 已{action_label}" if target_val else "已解锁"
                print(f"  ✅ {full_path} → {status}")
            else:
                print(f"  ❌ 无法操作 {full_path}")
        print()


def _resolve_field_path(path_str):
    """把模板路径字符串解析为 (parent_keys, leaf_key)。
    parent_keys 不含 [*]，用于定位容器。"""
    parts = path_str.split(".")
    *parent_keys, leaf = parts
    # 清理 parent_keys 中的 [*] 标记
    clean_parents = [p.replace("[*]", "") for p in parent_keys]
    return clean_parents, leaf


def _find_container_by_keys(data, keys):
    """根据 keys 列表在 data 中定位容器。如果是 list 则返回 list 本身。"""
    current = data
    for k in keys:
        if isinstance(current, list):
            break
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return None
    return current


def batch_rename_field():
    """批量重命名 — 循环列出字段，0返回"""
    print("\n  ── 批量字段重命名 ──")
    while True:
        fields = _list_template_fields()
        path_str, old_key = _pick_field(fields, "选择要重命名的字段")
        if not path_str:
            return

        locked, reason = is_locked(path_str)
        if locked:
            print(f"  🔒 {reason}，无法重命名")
            input("  按回车继续...")
            continue

        new_key = input(f"  「{old_key}」→ 新字段名 (0取消): ").strip()
        if new_key in ("0", "\\0"):
            continue
        if not new_key or new_key == old_key:
            print("  已取消")
            continue

        print(f"  [警告] 将对64个文件执行重命名: {path_str} → {new_key}")
        confirm = input("  [确认] 重命名？(y/1=继续, 其他取消): ").strip()
        if confirm.lower() not in ("y", "yes", "1"):
            print("  ❌ 已取消")
            continue

        parent_keys, _ = _resolve_field_path(path_str)
        updated = 0
        for fname in sorted(os.listdir(DATA_DIR)):
            if not fname.endswith(".jsonc") or fname == "lock.jsonc":
                continue
            filepath = os.path.join(DATA_DIR, fname)
            data = load_jsonc(filepath)
            container = _find_container_by_keys(data, parent_keys)
            if container is None:
                continue
            items = [container] if not isinstance(container, list) else container
            for item in items:
                if isinstance(item, dict) and old_key in item:
                    item[new_key] = item.pop(old_key)
                    updated += 1
            save_jsonc(filepath, data)

        sync_rename_field(path_str, old_key, new_key)
        print(f"  ✅ 已更新 {updated} 处: {old_key} → {new_key}")
        input("  按回车继续...")
        print()


def batch_delete_field():
    """批量删除字段 — 多选支持 1 3 5-7 格式，0返回"""
    print("\n  ── 批量删除字段 ──")
    while True:
        fields = _list_template_fields()
        selections = _pick_fields(fields, "选择要删除的字段")
        if not selections:
            return

        # 检查锁
        locked_fields = []
        for path_str, key in selections:
            locked, reason = is_locked(path_str)
            if locked:
                locked_fields.append(f"{path_str} ({reason})")
        if locked_fields:
            print(f"  🔒 以下字段被锁定，无法删除:")
            for lf in locked_fields:
                print(f"     {lf}")
            input("  按回车继续...")
            continue

        # 收集所有警告信息
        warnings = []
        items_with_content = []
        for path_str, key in selections:
            parent_keys, _ = _resolve_field_path(path_str)
            has = False
            for fname in sorted(os.listdir(DATA_DIR)):
                if not fname.endswith(".jsonc") or fname == "lock.jsonc":
                    continue
                data = load_jsonc(os.path.join(DATA_DIR, fname))
                container = _find_container_by_keys(data, parent_keys)
                if container is None:
                    continue
                items = [container] if not isinstance(container, list) else container
                for item in items:
                    if isinstance(item, dict) and key in item:
                        val = item[key]
                        if val not in (None, "", "（待补充）", [], {}, False, 0):
                            has = True
                            break
            if has:
                items_with_content.append(path_str)

        warnings.append(f"  [警告] 选择删除: {'  '.join(p for p, _ in selections)}")
        if items_with_content:
            warnings.append(f"  [警告] 以下字段含有实际内容: {'  '.join(items_with_content)}")

        for w in warnings:
            print(w)

        confirm = input("  [确认] 删除？(y/1=继续, 其他取消): ").strip()
        if confirm.lower() not in ("y", "yes", "1"):
            print("  ❌ 已取消")
            continue

        for path_str, key in selections:
            parent_keys, _ = _resolve_field_path(path_str)
            updated = 0
            for fname in sorted(os.listdir(DATA_DIR)):
                if not fname.endswith(".jsonc") or fname == "lock.jsonc":
                    continue
                filepath = os.path.join(DATA_DIR, fname)
                data = load_jsonc(filepath)
                container = _find_container_by_keys(data, parent_keys)
                if container is None:
                    continue
                items = [container] if not isinstance(container, list) else container
                for item in items:
                    if isinstance(item, dict) and key in item:
                        del item[key]
                        updated += 1
                save_jsonc(filepath, data)
            sync_delete_field(path_str)
            print(f"  ✅ 已从 {updated} 处删除「{key}」")
        input("  按回车继续...")
        print()


def batch_clear_field():
    """批量置空 — 多选支持 1 3 5-7 格式，0返回"""
    print("\n  ── 批量字段置空 ──")
    while True:
        fields = _list_template_fields()
        selections = _pick_fields(fields, "选择要置空的字段")
        if not selections:
            return

        template_data = load_jsonc(TEMPLATE_FILE)

        # 检查内容锁
        locked_content = []
        for path_str, key in selections:
            cl, reason = is_content_locked(path_str)
            if cl:
                locked_content.append(f"{path_str} ({reason})")
        if locked_content:
            print(f"  🔒* 以下字段被内容锁定，无法置空:")
            for lc in locked_content:
                print(f"     {lc}")
            input("  按回车继续...")
            continue

        warnings = []
        for path_str, key in selections:
            sample = _get_nested(template_data, path_str)
            if sample is None:
                sample = ""
            if isinstance(sample, bool):
                ev = False
            elif isinstance(sample, (int, float)):
                ev = None
            elif isinstance(sample, list):
                ev = []
            elif isinstance(sample, dict):
                ev = {}
            else:
                ev = ""
            warnings.append(f"  [警告] 将「{path_str}」重置为空值: {repr(ev)}")

        for w in warnings:
            print(w)

        confirm = input("  [确认] 置空？(y/1=继续, 其他取消): ").strip()
        if confirm.lower() not in ("y", "yes", "1"):
            print("  ❌ 已取消")
            continue

        for path_str, key in selections:
            sample = _get_nested(template_data, path_str)
            if sample is None:
                sample = ""
            if isinstance(sample, bool):
                empty_val = False
            elif isinstance(sample, (int, float)):
                empty_val = None
            elif isinstance(sample, list):
                empty_val = []
            elif isinstance(sample, dict):
                empty_val = {}
            else:
                empty_val = ""
            updated = 0
            for fname in sorted(os.listdir(DATA_DIR)):
                if not fname.endswith(".jsonc") or fname == "lock.jsonc":
                    continue
                filepath = os.path.join(DATA_DIR, fname)
                data = load_jsonc(filepath)
                _set_nested(data, path_str, empty_val)
                save_jsonc(filepath, data)
                updated += 1
            print(f"  ✅ 已置空 {updated} 个文件的「{key}」")
        input("  按回车继续...")
        print()


def _list_template_containers():
    """从模板提取所有可作为容器的路径（dict 和包含 dict 的 list）。
    返回 [(路径字符串, 容器类型), ...]，如 [('', '根层级'), ('nishi', 'dict'), ('lines[*]', 'list')]
    """
    template = load_jsonc(TEMPLATE_FILE)
    containers = [("", "根层级")]

    def _walk(obj, prefix):
        if isinstance(obj, dict):
            for k, v in obj.items():
                path = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    containers.append((path, f"{{{len(v)} fields}}"))
                    _walk(v, path)
                elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                    list_path = f"{path}[*]"
                    containers.append((list_path, f"[{len(v)} items]"))
                    _walk(v[0], list_path)

    _walk(template, "")
    return containers


def batch_add_field():
    """批量添加字段 — 选位置后循环添加，0返回上级，/q直接退到主菜单"""
    print("\n  ── 批量添加字段 ──")
    containers = _list_template_containers()

    while True:
        print("\n  选择添加位置:")
        print("  " + "─" * 50)
        for i, (path, desc) in enumerate(containers, 1):
            label = path if path else "根层级"
            print(f"  {i:>3}. {label}  ({desc})")
        print(f"    0. 返回上级")
        print("  " + "─" * 50)

        choice = input("  请选择目标位置 (输入序号): ").strip()
        if choice in ("0", "\\0", "q", "Q"):
            return

        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(containers)):
                print("  ❌ 无效选择")
                continue
        except ValueError:
            print("  ❌ 无效选择")
            continue

        dest_path, dest_desc = containers[idx]
        dest_label = dest_path if dest_path else "根层级"

        # 检查目标容器是否被锁定
        locked_dest, lock_reason = is_locked(dest_path.replace("[*]", "[0]") if dest_path else "all")
        if locked_dest:
            print(f"  🔒 「{dest_label}」已锁定({lock_reason})，无法在此添加字段")
            input("  按回车继续...")
            continue

        parent_keys = [p for p in dest_path.replace("[*]", "").split(".") if p] if dest_path else []

        while True:
            print(f"\n  当前位置: {dest_label} ({dest_desc})")
            new_name = input("  新字段名 (0返回位置选择, /q退出): ").strip()
            if new_name in ("/0", "/q", "/Q"):
                return
            if new_name in ("0", "\\0"):
                break
            if not new_name:
                continue

            # 检查是否重名
            template = load_jsonc(TEMPLATE_FILE)
            container = _find_container_by_keys(template, parent_keys) if parent_keys else template
            if container and isinstance(container, dict) and new_name in container:
                print(f"  ❌ 「{new_name}」在该位置已存在")
                continue

            print("  字段类型: 1.文本/数字  2.对象{}  3.数组[]")
            ftype = input("  请选择 (0取消, /q退出, 默认1): ").strip()
            if ftype in ("/0", "/q", "/Q"):
                return
            if ftype in ("0", "\\0"):
                continue
            if ftype == "2":
                default_val = {}
                type_label = "对象"
            elif ftype == "3":
                default_val = []
                type_label = "数组"
            else:
                default_val = ""
                type_label = "字段"

            updated = 0
            for fname in sorted(os.listdir(DATA_DIR)):
                if not fname.endswith(".jsonc") or fname == "lock.jsonc":
                    continue
                filepath = os.path.join(DATA_DIR, fname)
                data = load_jsonc(filepath)
                target = _find_container_by_keys(data, parent_keys) if parent_keys else data
                if target is None:
                    continue
                items = [target] if not isinstance(target, list) else target
                for item in items:
                    if isinstance(item, dict) and new_name not in item:
                        item[new_name] = default_val
                        updated += 1
                save_jsonc(filepath, data)

            print(f"  ✅ 已添加{type_label}「{new_name}」到 {updated} 处")
            # 同步到 lock
            sync_new_field(dest_path, new_name, is_dict=(ftype == "2"))
            input("  按回车继续...")
            # 添加后刷新容器列表（结构可能变了）
            containers = _list_template_containers()
            break  # 回到位置选择，展示刷新后的列表


def batch_move_field():
    """批量移动字段 — 选择源字段，再选择目标位置"""
    print("\n  ── 批量移动字段 ──")

    # Step 1: 选择源字段
    fields = _list_template_fields()
    path_str, key = _pick_field(fields, "选择要移动的字段")
    if not path_str:
        return

    locked, reason = is_locked(path_str)
    if locked:
        print(f"  🔒 {reason}，无法移动")
        input("  按回车继续...")
        return

    parent_keys, _ = _resolve_field_path(path_str)

    # Step 2: 选择目标位置
    containers = _list_template_containers()
    print(f"\n  [警告] 「{key}」将被移动。选择目标位置:")
    print("  " + "─" * 50)
    for i, (cpath, desc) in enumerate(containers, 1):
        label = cpath if cpath else "根层级"
        print(f"  {i:>3}. {label}  ({desc})")
    print(f"    0. 返回")
    print("  " + "─" * 50)

    choice = input("  请选择目标位置 (输入序号): ").strip()
    if choice in ("0", "\\0", "q", "Q"):
        return

    try:
        idx = int(choice) - 1
        if not (0 <= idx < len(containers)):
            print("  ❌ 无效选择")
            return
    except ValueError:
        print("  ❌ 无效选择")
        return

    dest_path, _ = containers[idx]
    dest_label = dest_path if dest_path else "根层级"
    dest_parent_keys = [p for p in dest_path.replace("[*]", "").split(".") if p] if dest_path else []

    if parent_keys == dest_parent_keys:
        print(f"  ❌ 目标位置与当前位置相同")
        return

    print(f"\n  [警告] 移动「{path_str}」→ {dest_label}")
    confirm = input("  [确认] 移动？(y/1=继续, 其他取消): ").strip()
    if confirm.lower() not in ("y", "yes", "1"):
        print("  ❌ 已取消")
        return

    updated = 0
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith(".jsonc") or fname == "lock.jsonc":
            continue
        filepath = os.path.join(DATA_DIR, fname)
        data = load_jsonc(filepath)

        src_container = _find_container_by_keys(data, parent_keys)
        if src_container is None:
            continue
        src_items = [src_container] if not isinstance(src_container, list) else src_container

        dest_container = _find_container_by_keys(data, dest_parent_keys) if dest_parent_keys else data
        if dest_container is None:
            continue
        dest_items = [dest_container] if not isinstance(dest_container, list) else dest_container

        for si, src_item in enumerate(src_items):
            if isinstance(src_item, dict) and key in src_item:
                val = src_item.pop(key)
                if isinstance(dest_container, list):
                    if si < len(dest_items) and isinstance(dest_items[si], dict):
                        dest_items[si][key] = val
                        updated += 1
                else:
                    if isinstance(dest_items[0], dict):
                        dest_items[0][key] = val
                        updated += 1
        save_jsonc(filepath, data)

    print(f"  ✅ 已将「{key}」从 {updated} 处移动到「{dest_label}」")
    input("  按回车继续...")


def view_hexagram(hid):
    """查看单卦全部字段"""
    filepath = get_file_by_id(hid)
    if not filepath:
        print(f"❌ 未找到 ID={hid} 的卦文件")
        return
    data = load_jsonc(filepath)
    print(f"\n  ═══ {data['name']} ({data.get('full_name', '')}) ═══")
    _print_fields(data, show_empty=True)


def _lookup_by_xiantian(upper_num, lower_num):
    """通过先天八卦数(1-8)查找卦ID。1=乾 2=兑 3=离 4=震 5=巽 6=坎 7=艮 8=坤"""
    upper_name = NUM_TO_XIANTIAN.get(upper_num)
    lower_name = NUM_TO_XIANTIAN.get(lower_num)
    if not upper_name or not lower_name:
        return None
    hex_dict = load_all()
    for hid, data in hex_dict.items():
        if data.get("upper") == upper_name and data.get("lower") == lower_name:
            return hid
    return None


def _resolve_hexagram(prompt_text):
    """解析卦输入。支持:
       - 卦ID (1-64)
       - 先天八卦数 (上卦-下卦, 如 1-2=天泽履, 1=乾 2=兑 3=离 4=震 5=巽 6=坎 7=艮 8=坤)
       - 0 / \\0 / q 返回上级
    返回卦ID 或 None
    """
    hint = "卦ID(1-64) 或 上卦-下卦先天数(如1-2=天泽履)"

    # 首次进入时打印先天数对照表
    if not hasattr(_resolve_hexagram, "_shown_xiantian"):
        _resolve_hexagram._shown_xiantian = True
        items = sorted(XIANTIAN_NUM.items(), key=lambda x: x[1])
        print(f"  先天数: {'  '.join(f'{n}{name}' for name, n in items[:4])}")
        print(f"          {'  '.join(f'{n}{name}' for name, n in items[4:])}")

    while True:
        try:
            user_input = input(f"  {prompt_text} [{hint}, 0返回]: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

        if user_input in ("0", "\\0", "q", "Q"):
            return None

        # 先天数格式: X-X
        if "-" in user_input:
            try:
                parts = user_input.split("-")
                if len(parts) == 2:
                    upper_num = int(parts[0])
                    lower_num = int(parts[1])
                    if upper_num not in NUM_TO_XIANTIAN or lower_num not in NUM_TO_XIANTIAN:
                        print("  ❌ 先天数范围 1-8")
                        continue
                    hid = _lookup_by_xiantian(upper_num, lower_num)
                    if hid:
                        return hid
                    print(f"  ❌ 未找到 上卦={NUM_TO_XIANTIAN[upper_num]}({upper_num}) 下卦={NUM_TO_XIANTIAN[lower_num]}({lower_num}) 的卦")
                    continue
            except (ValueError, IndexError):
                pass
            print("  ❌ 格式错误，请使用 卦ID 或 上卦-下卦先天数(如 1-2)")
            continue

        # 简单 ID
        try:
            hid = int(user_input)
            if 1 <= hid <= 64:
                return hid
            print("  ⚠️  卦ID范围 1-64")
        except ValueError:
            print("  ❌ 无效输入，请使用卦ID(1-64)或上卦-下卦先天数(如 1-2=天泽履)")


# ═══════════════════════════════════════════════════════════════
#  主菜单
# ═══════════════════════════════════════════════════════════════

def main():
    while True:
        print("\n" + "═" * 48)
        print("  易经数据库管理工具")
        print("═" * 48)
        print("  1. 编辑单卦    2. 查看单卦")
        print("  3. 备份数据库  4. 恢复数据库")
        print("  5. 批量字段操作 - 删除/重命名/新增/移动")
        print("  6. 🔒字段锁管理")
        print("  q. 退出")
        print("─" * 48)

        try:
            choice = input("  请选择 (0返回): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice in ("0", "\\0"):
            continue

        if choice == "1":
            hid = _resolve_hexagram("编辑卦")
            if hid:
                edit_hexagram(hid)

        elif choice == "2":
            hid = _resolve_hexagram("查看卦")
            if hid:
                view_hexagram(hid)

        elif choice == "3":
            backup()

        elif choice == "4":
            restore()

        elif choice == "5":
            while True:
                print("\n  批量字段操作:  [a]添加字段  [c]批量清空字段值  [d]删除字段  [m]移动字段  [r]重命名字段")
                try:
                    sub = input("  请选择 (0返回): ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    break

                if sub in ("0", "\\0"):
                    break
                elif sub == "r":
                    batch_rename_field()
                elif sub == "d":
                    batch_delete_field()
                elif sub == "c":
                    batch_clear_field()
                elif sub == "a":
                    batch_add_field()
                elif sub == "m":
                    batch_move_field()
                else:
                    print("  无效选择")

        elif choice == "6":
            manage_locks()

        elif choice.lower() == "q":
            print("  再见")
            break

        else:
            print("  无效选择")


if __name__ == "__main__":
    main()
