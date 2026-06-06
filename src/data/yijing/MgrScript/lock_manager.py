#!/usr/bin/env python3
"""锁管理工具 — 查看/设置/清除字段锁定状态。

字段被锁定后，yijing_manager.py 的 重命名/删除/移动 操作会拒绝执行。

锁文件: content/lock.jsonc
  - dict 容器有 all 字段，all=1 则整个层级锁定
  - 叶子字段值为 1 则锁定
  - 新增字段自动同步到 lock.jsonc（默认 unlocked=0）

用法:
    cd src/data/yijing
    python3 MgrScript/lock_manager.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lock_utils import (
    load_lock, save_lock, get_lock_tree, set_lock, is_locked, is_content_locked,
    LOCK_FILE, TEMPLATE_FILE,
)
from sync_structure import load_jsonc


def _list_template_fields():
    """从模板提取所有字段路径（含容器和叶子）。"""
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


def _show_lock_status(fields):
    """显示所有字段及锁定状态"""
    print("\n  " + "─" * 60)
    print(f"  {'#':>3}  {'状态':5}  字段路径")
    print("  " + "─" * 60)

    for i, (path, val, typ) in enumerate(fields, 1):
        cl, _ = is_content_locked(path)
        sl, _ = is_locked(path)
        if cl:
            status = "🔒*"
        elif sl:
            status = "🔒"
        else:
            status = "0"
        print(f"  {i:>3}  {status:4}   {path}  ({typ})")

    print("  " + "─" * 60)


def main():
    if not os.path.exists(LOCK_FILE):
        print(f"❌ {LOCK_FILE} 不存在，请先创建 lock.jsonc")
        return

    while True:
        print("\n  ═══ 字段锁管理 ═══")
        print("  1. 查看全部锁状态")
        print("  2. 锁定字段（结构锁 🔒）")
        print("  3. 锁定内容（内容锁 🔒*）")
        print("  4. 解锁字段")
        print("  q. 退出")

        try:
            choice = input("  请选择: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice.lower() == "q":
            break
        elif choice == "1":
            fields = _list_template_fields()
            _show_lock_status(fields)

        elif choice in ("2", "3", "4"):
            if choice == "2":
                value = 1
                action = "结构锁"
                icon = "🔒"
            elif choice == "3":
                value = 2
                action = "内容锁"
                icon = "🔒*"
            else:
                value = 0
                action = "解锁"
                icon = ""
            fields = _list_template_fields()

            while True:
                _show_lock_status(fields)
                print(f"\n  选择要{action}的字段 (支持多选: 1 3 5-7, 0返回):")
                try:
                    sel = input("  → ").strip()
                except (EOFError, KeyboardInterrupt):
                    break

                if sel in ("0", "\\0", ""):
                    break

                # 解析多选
                indices = set()
                for part in sel.replace(",", " ").split():
                    part = part.strip()
                    if not part:
                        continue
                    if "-" in part:
                        try:
                            a, b = part.split("-", 1)
                            for n in range(int(a), int(b) + 1):
                                if 1 <= n <= len(fields):
                                    indices.add(n - 1)
                        except ValueError:
                            pass
                    else:
                        try:
                            n = int(part) - 1
                            if 0 <= n < len(fields):
                                indices.add(n)
                        except ValueError:
                            pass

                if not indices:
                    print("  ❌ 无效选择")
                    continue

                warnings = []
                for idx in indices:
                    path = fields[idx][0]
                    locked_now, reason = is_locked(path)
                    cl_now, _ = is_content_locked(path)
                    if value == 2 and cl_now:
                        warnings.append(f"  [警告] {path} 已被内容锁定: {reason}")
                    elif value == 1 and locked_now:
                        warnings.append(f"  [警告] {path} 已被锁定: {reason}")
                    elif value == 0 and not locked_now:
                        warnings.append(f"  [警告] {path} 当前未锁定")

                if warnings:
                    for w in warnings:
                        print(w)

                confirm = input(f"  [确认] {action}？(y/1=继续, 其他取消): ").strip()
                if confirm.lower() not in ("y", "yes", "1"):
                    print("  ❌ 已取消")
                    continue

                for idx in indices:
                    path, _sample, typ = fields[idx]
                    # 容器（dict/list[dict]）设 all 字段，叶子直接设值
                    lock_path = f"{path}.all" if typ in ("dict", "list[dict]") else path
                    ok = set_lock(lock_path, value)
                    if ok:
                        status = f"{icon} 已{action}" if value else action
                        print(f"  ✅ {path} → {status}")
                    else:
                        print(f"  ❌ {path} 操作失败，lock 结构可能已损坏，请运行格式刷修复")

                # 操作后刷新显示
                print()
                fields = _list_template_fields()
                _show_lock_status(fields)
                input("  按回车返回主菜单...")
                break

        else:
            print("  无效选择")


if __name__ == "__main__":
    main()
