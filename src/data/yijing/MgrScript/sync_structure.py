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

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
SCRIPT_DIR = os.path.join(PARENT, "content")
BACKUP_FILE = os.path.join(PARENT, "content.bkp.zip")
DEFAULT_TEMPLATE = "01_乾.jsonc"

sys.path.insert(0, HERE)
from sync_core import run_sync


def main():
    """结构同步交互式入口（格式刷），以模板卦文件为基准同步所有 64 卦。

    运行流程：
    1. 从命令行参数获取模板文件名，默认使用 "01_乾.jsonc"
    2. 调用 sync_core.run_sync() 执行同步（备份 → 结构对齐 → 字段清理 → 排序 → 格式刷）
    3. 同步完成后进入"按回车再次刷新 / 输入 q 退出"的循环

    同步包括：
    - 确保所有卦文件拥有与模板一致的字段路径
    - 删除目标文件中模板不存在的字段（有内容则保留并警告）
    - 按模板的字段顺序重新排列
    - 输出格式严格对齐模板（缩进、注释、数组换行等）

    运行前自动备份 content/ → content.bkp.zip，可反复运行无副作用。

    Args:
        无参数，通过 sys.argv[1] 接收可选模板文件名，通过 sys.stdin 与用户交互。

    Returns:
        None: 不返回值，printf 风格输出到终端。

    示例：
        $ cd src/data/yijing
        $ python3 MgrScript/sync_structure.py                     # 以 01_乾 为模板
        $ python3 MgrScript/sync_structure.py 02_坤.jsonc         # 以 02_坤 为模板
    """
    template_name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TEMPLATE
    template_path = os.path.join(SCRIPT_DIR, template_name)

    while True:
        run_sync(template_path, SCRIPT_DIR, BACKUP_FILE, template_name, has_lock=True)
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
