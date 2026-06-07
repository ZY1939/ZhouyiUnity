#!/usr/bin/env python3
"""
八字数据库结构同步脚本（格式刷） — 以 00_Model.jsonc 为模板，将其字段结构同步到其他八字文件。

功能：
  1. 结构同步 — 确保所有八字 JSONC 文件拥有与模板一致的字段路径
  2. 字段清理 — 删除目标文件中模板不存在的字段（有内容的字段保留以防误删）
  3. 字段排序 — 按模板的字段顺序重新排列
  4. 格式刷新 — 输出格式严格对齐模板（缩进、注释、数组换行等）

用法：
    cd usrDat/bazi
    python3 MgrScript/sync_structure.py                 # 默认以 00_Model.jsonc 为模板
    python3 MgrScript/sync_structure.py 01_张三.jsonc   # 以指定文件为模板

说明：
  - 运行前自动备份 → bazi.bkp.zip
  - 有内容的字段若不在模板中会被保留并发出警告
  - 可反复运行，已同步的文件仅刷新格式，不会重复修改

依赖：
    00_Model.jsonc — 默认模板文件（其他文件以此为基准对齐）
    *.jsonc        — 八字数据文件
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
SCRIPT_DIR = PARENT  # JSONC 文件在 usrDat/bazi/ 目录
BACKUP_FILE = os.path.join(PARENT, "bazi.bkp.zip")
DEFAULT_TEMPLATE = "00_Model.jsonc"

# 导入共享的 sync_core 模块（项目根目录 → src/data/yijing/MgrScript）
_PROJ_ROOT = os.path.dirname(os.path.dirname(PARENT))
_YIJING_MGR = os.path.join(_PROJ_ROOT, "src", "data", "yijing", "MgrScript")
sys.path.insert(0, _YIJING_MGR)
from sync_core import run_sync


def main():
    template_name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TEMPLATE
    template_path = os.path.join(SCRIPT_DIR, template_name)

    while True:
        run_sync(template_path, SCRIPT_DIR, BACKUP_FILE, template_name, has_lock=False)
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
