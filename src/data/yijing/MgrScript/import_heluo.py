#!/usr/bin/env python3
"""
导入倪师河洛（先天卦/后天卦/流年卦）— 解析 nishi_Heluo/ 目录下 64 卦 MD 文件，
将各段落写入 JSONC 的 nishi.heluo 字段（数组格式）。

写入字段（新建）：
  nishi.heluo.xiantian  ← #### 先天卦 之后的段落（字符串数组）
  nishi.heluo.houtian   ← #### 后天卦 之后的段落（字符串数组）
  nishi.heluo.liunian   ← #### 值年卦 / #### 流年卦 之后的段落（字符串数组）

MD 文件格式：
  - 文件名: {序号}.{卦名}.md（如 "1.乾为天.md"、"16.雷地豫.md"）
  - 段落标题: #### 先天卦 / #### 后天卦 / #### 值年卦（或 #### 流年卦）
  - 内容按空行自然分段，每段一个数组元素

匹配机制：
  1. 文件名序号前缀（如 "1."）→ content/{XX}_*.jsonc
  2. MD 卦名 ↔ JSONC 的 full_name 字段交叉验证（兼容繁简转换）
  3. 匹配失败时列出候选文件让用户选择，自修改 FILE_OVERRIDES

缺段处理：
  若某 MD 缺少先天/后天/流年中某个标题，该字段写空数组并输出 ⚠️ 警告。

用法：
    cd src/data/yijing
    python3 MgrScript/import_heluo.py

依赖：
    MgrScript/sync_core.py — load_jsonc / format_by_template
    content/01_乾.jsonc   — 输出格式模板
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
DATA_DIR = os.path.join(PARENT, "content")
HELUO_DIR = os.path.join(PARENT, "nishi_Heluo")
SELF = os.path.abspath(__file__)

sys.path.insert(0, HERE)
from sync_core import load_jsonc, format_by_template

TEMPLATE_FILE = os.path.join(DATA_DIR, "01_乾.jsonc")


# ═══════════════════════════════════════════════════════════════
#  === OVERRIDE_START === （文件映射覆盖，脚本自动更新）
# ═══════════════════════════════════════════════════════════════
# MD 文件序号(1-based) → JSONC 文件名
FILE_OVERRIDES = {
    # 示例: 1: "01_乾.jsonc"
}
# ═══════════════════════════════════════════════════════════════
#  === OVERRIDE_END ===


# 繁简对照表（与 import_humanity.py 共用同一份）
T2S = {
    "爲": "为", "為": "为", "師": "师", "風": "风", "澤": "泽", "謙": "谦",
    "隨": "随", "蠱": "蛊", "臨": "临", "觀": "观", "賁": "贲",
    "剝": "剥", "復": "复", "頤": "颐", "過": "过", "恆": "恒",
    "遯": "遁", "壯": "壮", "晉": "晋", "睽": "睽", "蹇": "蹇",
    "損": "损", "益": "益", "姤": "姤", "萃": "萃", "升": "升",
    "困": "困", "井": "井", "革": "革", "鼎": "鼎", "漸": "渐",
    "歸": "归", "豐": "丰", "巽": "巽", "兌": "兑", "渙": "涣",
    "節": "节", "濟": "济", "離": "离", "爾": "尔", "萬": "万",
    "無": "无", "習": "习",
}


def t2s(text):
    """繁转简：逐个字符替换繁体为简体。"""
    for t, s in T2S.items():
        text = text.replace(t, s)
    return text


def save_jsonc(path, data):
    """按模板格式保存 JSONC 文件。

    Args:
        path: 目标 JSONC 文件的完整路径
        data: 卦的完整数据字典
    """
    template = load_jsonc(TEMPLATE_FILE)
    text = format_by_template(data, template, TEMPLATE_FILE)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _load_overrides():
    """从自身源码加载 FILE_OVERRIDES。"""
    import ast
    with open(SELF, "r", encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"FILE_OVERRIDES\s*=\s*(\{[^}]+\})", src, re.DOTALL)
    if m:
        try:
            return ast.literal_eval(m.group(1))
        except (SyntaxError, ValueError):
            pass
    return {}


def _add_override(seq, filename):
    """在 OVERRIDE 区域插入新文件映射。

    Args:
        seq: MD 文件序号 (1-based)
        filename: JSONC 文件名，如 "01_乾.jsonc"
    """
    with open(SELF, "r", encoding="utf-8") as f:
        lines = f.readlines()

    mark_start = "=== OVERRIDE_START ==="
    mark_end = "=== OVERRIDE_END ==="
    target_var = "FILE_OVERRIDES = {"
    in_block = False
    target_line = -1
    insert_line = -1

    for i, line in enumerate(lines):
        if mark_start in line:
            in_block = True
        elif mark_end in line:
            in_block = False
        elif in_block and target_var in line:
            target_line = i
        elif in_block and target_line >= 0 and i > target_line:
            if line.strip() == "}":
                insert_line = i
                break

    if insert_line < 0:
        return False

    indent = "    "
    new_entry = f'{indent}{seq}: "{filename}",\n'
    lines.insert(insert_line, new_entry)

    with open(SELF, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"  📝 已将序号 {seq} → {filename} 写入 FILE_OVERRIDES")
    return True


def _find_jsonc_from_md(md_fname):
    """根据 MD 文件名定位对应的 JSONC 文件。

    策略（三级）：
      1. FILE_OVERRIDES 覆盖
      2. 序号前缀匹配（如 MD "01." → JSONC "01_*"）
      3. MD 卦名（繁转简后）↔ JSONC full_name 精确匹配
      4. 匹配失败 → 列出候选让用户选择，自修改覆盖

    Args:
        md_fname: MD 文件名，如 "1.乾为天.md"

    Returns:
        (filepath, jsonc_fname) 或 (None, None) 如果匹配失败
    """
    overrides = _load_overrides()

    # 提取序号和卦名
    m = re.match(r"^(\d+)\.(.+)\.md$", md_fname)
    if not m:
        print(f"  ❌ 文件名格式异常: {md_fname}（期望格式: 序号.卦名.md）")
        return None, None

    seq = int(m.group(1))
    md_name_raw = m.group(2).strip()
    md_name_simple = t2s(md_name_raw)

    # 策略 1: FILE_OVERRIDES
    if seq in overrides:
        fname = overrides[seq]
        filepath = os.path.join(DATA_DIR, fname)
        if os.path.exists(filepath):
            return filepath, fname
        print(f"  ⚠️  FILE_OVERRIDES 中 {seq} → {fname} 文件不存在，已忽略")

    # 策略 2: 序号前缀匹配
    prefix = f"{seq:02d}"
    matches = sorted([f for f in os.listdir(DATA_DIR)
                      if f.startswith(prefix) and f.endswith(".jsonc") and f != "lock.jsonc"])
    if len(matches) == 1:
        filepath = os.path.join(DATA_DIR, matches[0])
        # 验证：MD 卦名与 JSONC full_name 是否一致
        data = load_jsonc(filepath)
        jsonc_full = data.get("full_name", "")
        if jsonc_full and t2s(jsonc_full) == md_name_simple:
            return filepath, matches[0]
        # 前缀匹配但卦名不一致 → 继续尝试策略 3

    # 策略 3: full_name 精确匹配
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith(".jsonc") or fname == "lock.jsonc":
            continue
        data = load_jsonc(os.path.join(DATA_DIR, fname))
        jsonc_full = data.get("full_name", "")
        if jsonc_full and t2s(jsonc_full) == md_name_simple:
            return os.path.join(DATA_DIR, fname), fname

    # 也可以反过来：用 fullName_tc 匹配原始繁体名
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith(".jsonc") or fname == "lock.jsonc":
            continue
        data = load_jsonc(os.path.join(DATA_DIR, fname))
        jsonc_tc = data.get("fullName_tc", "")
        if jsonc_tc and jsonc_tc == md_name_raw:
            return os.path.join(DATA_DIR, fname), fname

    # 策略 4: 匹配失败 → 用户选择
    jsonc_files = sorted([f for f in os.listdir(DATA_DIR)
                          if f.endswith(".jsonc") and f != "lock.jsonc"])
    print(f"\n  ⚠️  MD 文件「{md_fname}」（{md_name_raw}）找不到匹配的 JSONC")
    print(f"  期望序号: {seq}, 清理后卦名: {md_name_simple}")
    print(f"  可用的 JSONC 文件：")
    for j, fn in enumerate(jsonc_files):
        d = load_jsonc(os.path.join(DATA_DIR, fn))
        print(f"    [{j}] {fn}  ({d.get('full_name', '?')})")
    print(f"  请输入对应文件的序号，或回车跳过此卦：")
    try:
        answer = input("  → ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None, None
    if not answer:
        return None, None
    try:
        idx = int(answer)
        if 0 <= idx < len(jsonc_files):
            chosen = jsonc_files[idx]
            _add_override(seq, chosen)
            return os.path.join(DATA_DIR, chosen), chosen
    except ValueError:
        pass

    return None, None


def _split_paragraphs(text):
    """将文本按空行/双换行拆分为段落数组。
    去除首尾空白，过滤掉纯空白段落。

    Args:
        text: 一段连续文本

    Returns:
        list[str]: 段落数组
    """
    # 按双换行切分
    parts = re.split(r'\n\s*\n', text.strip())
    result = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # 合并段落内的单换行（保持语义连贯）
        p = re.sub(r'\n(?!\n)', ' ', p)
        # 清理多余空格
        p = re.sub(r' {2,}', ' ', p)
        result.append(p)
    return result


def parse_heluo_md(filepath):
    """解析单个河洛 MD 文件，提取先天卦/后天卦/流年卦段落。

    MD 段落结构（兼容变体）：
      #### 先天卦     — 先天卦内容
      #### 后天卦     — 后天卦内容
      #### 值年卦     — 流年卦内容（值年卦 = 流年卦）
      #### 流年卦     — 同上

    Args:
        filepath: MD 文件的完整路径

    Returns:
        dict: {
            "filename": str,
            "xiantian": [段落列表],
            "houtian": [段落列表],
            "liunian": [段落列表],
            "errors": [警告信息列表]
        }
    """
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    filename = os.path.basename(filepath)
    result = {
        "filename": filename,
        "xiantian": [],
        "houtian": [],
        "liunian": [],
        "errors": [],
    }

    # 用正则找到所有 #### 标题的位置
    # 匹配: #### 先天卦, #### 后天卦, #### 值年卦, #### 流年卦
    section_pattern = re.compile(
        r'^#{1,4}\s*'           # # ~ #### 号
        r'(\*{0,2})'             # 可选的 ** 标记（兼容 OCR 格式）
        r'(先天卦|后天卦|值年卦|流年卦|後天卦)'  # 标题关键词
        r'(\*{0,2})',           # 可选的 ** 结束标记
        re.MULTILINE
    )

    matches = list(section_pattern.finditer(text))

    if not matches:
        result["errors"].append("未找到任何 ## 段落标题（先天卦/后天卦/值年卦/流年卦）")
        return result

    # 为每个匹配定位它的内容范围
    for i, m in enumerate(matches):
        section_type = m.group(2)  # 先天卦 / 后天卦 / 值年卦 / 流年卦 / 後天卦
        content_start = m.end()
        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[content_start:content_end].strip()

        # 段落拆分
        paragraphs = _split_paragraphs(content)

        # 分类存储
        if section_type == "先天卦":
            result["xiantian"] = paragraphs
        elif section_type in ("后天卦", "後天卦"):
            result["houtian"] = paragraphs
        elif section_type in ("值年卦", "流年卦"):
            result["liunian"] = paragraphs

    # 检查是否有缺失段落
    if not result["xiantian"]:
        result["errors"].append("缺少「先天卦」段落")
    if not result["houtian"]:
        result["errors"].append("缺少「后天卦」段落")
    if not result["liunian"]:
        result["errors"].append("缺少「值年卦/流年卦」段落")

    return result


def main():
    """主入口：批量导入 64 卦河洛数据到 JSONC 数据库。

    工作流程：
      1. 扫描 nishi_Heluo/ 下所有 {序号}.{卦名}.md 文件
      2. 逐文件解析先天卦/后天卦/流年卦段落
      3. 按序号 + 卦名双重匹配定位 JSONC 文件
      4. 写入 nishi.heluo.xiantian / houtian / liunian（数组）
      5. 缺段文件输出 ⚠️ 警告但不阻塞
    """
    if not os.path.exists(HELUO_DIR):
        print(f"❌ 河洛目录不存在: {HELUO_DIR}")
        return

    # 收集 MD 文件（排除 0.八字的排列方法.md 和 65.批卦补充.md）
    md_files = sorted([
        f for f in os.listdir(HELUO_DIR)
        if f.endswith(".md")
        and re.match(r"^\d+\.", f)  # 以数字开头
        and not f.startswith("0.")
        and not f.startswith("65.")
    ])

    if len(md_files) != 64:
        print(f"⚠️  预期 64 个卦文件，实际找到 {len(md_files)} 个")

    print(f"📂 找到 {len(md_files)} 个河洛 MD 文件\n")

    updated = 0
    skipped = 0
    missing_all = 0

    for fname in md_files:
        md_path = os.path.join(HELUO_DIR, fname)
        parsed = parse_heluo_md(md_path)

        # 如果三个段落全空，跳过
        if not parsed["xiantian"] and not parsed["houtian"] and not parsed["liunian"]:
            print(f"  ❌ {fname}: 所有段落均空，跳过")
            for err in parsed["errors"]:
                print(f"     ↳ {err}")
            missing_all += 1
            continue

        # 匹配 JSONC 文件
        filepath, jfname = _find_jsonc_from_md(fname)
        if not filepath:
            print(f"  ⚠️  {fname}: 未找到对应 JSONC 文件，跳过")
            skipped += 1
            continue

        # 加载数据
        data = load_jsonc(filepath)

        # 确保 nishi.heluo 字段存在
        data.setdefault("nishi", {}).setdefault("heluo", {})
        data["nishi"]["heluo"]["xiantian"] = parsed["xiantian"]
        data["nishi"]["heluo"]["houtian"] = parsed["houtian"]
        data["nishi"]["heluo"]["liunian"] = parsed["liunian"]

        # 保存
        save_jsonc(filepath, data)
        updated += 1

        # 构建状态信息
        parts_count = (
            f"先天{len(parsed['xiantian'])}段"
            f"  后天{len(parsed['houtian'])}段"
            f"  流年{len(parsed['liunian'])}段"
        )

        if parsed["errors"]:
            print(f"  ⚠️  {jfname} ← {fname}  ({parts_count})")
            for err in parsed["errors"]:
                print(f"     ↳ {err}")
        else:
            print(f"  ✅ {jfname} ← {fname}  ({parts_count})")

    print(f"\n{'=' * 50}")
    print(f"✅ 已更新: {updated}")
    print(f"⏭️  跳过: {skipped}")
    print(f"❌ 全部为空: {missing_all}")
    print(f"📊 总计: {len(md_files)} 个文件")


if __name__ == "__main__":
    main()
