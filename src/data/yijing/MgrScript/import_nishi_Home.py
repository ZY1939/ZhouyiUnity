#!/usr/bin/env python3
"""
导入倪师阳宅合集（地脈道）→ 写入 JSONC 的 nishi.home.description 字段

功能：
  1. 内存中清理 MD 源文件的 OCR 乱码（多余空格、标题重复、格式不一致）
  2. 智能拆分：每个编号条目（一、二、...）作为一个数组元素
  3. 同时将清理后的内容写回 MD 源文件（--fix-md）

数据源：
  nishi_Home/倪海厦《天纪》阳宅合集.md

目标字段：
  content/XX_*.jsonc 的 nishi.home.description（字符串数组）

匹配方式：
  解析 MD 中每个卦的标题 --> 提取中文序号（一→1, 六十四→64）
  --> 按序号前缀定位对应的 JSONC 文件。

用法：
    cd src/data/yijing
    python3 MgrScript/import_nishi_Home.py              # 仅导入
    python3 MgrScript/import_nishi_Home.py --fix-md     # 导入 + 修复 MD 源文件

依赖：
    MgrScript/sync_core.py — load_jsonc / format_by_template
    content/01_乾.jsonc   — 输出格式模板
"""

import json
import os
import re
import sys

# ═══════════════════════════════════════════════════════
#  路径配置（如项目移动，只需修改此处）
# ═══════════════════════════════════════════════════════
HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)                          # src/data/yijing/
DATA_DIR = os.path.join(PARENT, "content")               # JSONC 数据库目录
HOME_DIR = os.path.join(PARENT, "nishi_Home")            # 倪师阳宅数据源目录
MD_FILE = os.path.join(HOME_DIR, "倪海厦《天纪》阳宅合集.md")  # 源 MD 文件
MD_CLEAN_FILE = os.path.join(HOME_DIR, "倪海厦《天纪》阳宅合集.md")  # 清理后覆盖原文件
TEMPLATE_FILE = os.path.join(DATA_DIR, "01_乾.jsonc")    # 格式模板

sys.path.insert(0, HERE)
from sync_core import load_jsonc, format_by_template


# ═══════════════════════════════════════════════════════
#  中文数字 → 阿拉伯数字 转换
# ═══════════════════════════════════════════════════════
_CN_DIGIT = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9,
}


def cn_to_int(cn):
    """中文数字 → 整数（支持 一 到 六十四）"""
    cn = cn.strip()
    if cn in _CN_DIGIT:
        return _CN_DIGIT[cn]
    if cn == "十":
        return 10
    if cn.startswith("十") and len(cn) == 2:
        return 10 + _CN_DIGIT.get(cn[1], 0)
    if cn.endswith("十") and len(cn) == 2:
        return _CN_DIGIT.get(cn[0], 0) * 10
    parts = cn.split("十")
    if len(parts) == 2 and parts[0] and parts[1]:
        tens = _CN_DIGIT.get(parts[0], 0)
        ones = _CN_DIGIT.get(parts[1], 0)
        return tens * 10 + ones
    return None


# ═══════════════════════════════════════════════════════
#  MD 全文清理
# ═══════════════════════════════════════════════════════

def clean_full_text(text):
    """清理整个 MD 文件的 OCR 乱码 + 修复已知内容错位。

    步骤：
      1. 删除乱码目录（序言之前的所有内容）
      2. 删除第二个乱码目录表（天纪地脈道(倪海廈著) 那一段）
      2.5 修复 47/48/49 卦内容错位（井的条目误放入困，井标题裸写入革）
      3. 清理标题行 OCR 重复
      4. 清理 CJK 字符间的多余空格
      5. 统一编号条目格式：去掉前导 "- " 和多余缩进
      6. 清理 #### 子标题混入

    Args:
        text: MD 文件原始全文

    Returns:
        str: 清理后的全文
    """
    # ── 1. 删除乱码目录 ──
    # 找到「序 言」的位置，之前的内容全部删除
    preface = re.search(r'^# \*\*序\s*言\*\*', text, re.MULTILINE)
    if preface:
        text = text[preface.start():]

    # ── 2. 删除第二个乱码目录表（在 地理篇 和 序言 之间的表格） ──
    # 「# 天纪地脈道(倪海廈著)」之后到「#### **地理篇**」之前有个表格
    # 直接移除这个表格段
    text = re.sub(
        r'# 天纪地脈道.*?\n\n',
        '',
        text,
        flags=re.DOTALL
    )
    # 移除剩余表格行（以 | 开头的行）
    text = re.sub(r'^\|.*$(\n|$)', '', text, flags=re.MULTILINE)

    # ── 2.5. 修复 47/48/49 卦内容错位 ──
    # 源 MD 结构问题：
    #   困(47)下第二组条目（婚事娶二婚妻…→從官招陷…）实际属于井(48)
    #   井(48)的标题裸写在革(49)章节内，导致井无独立章节、革内容被井标题隔断
    # 修正：第二组条目移到新插入的井(48)标题下，删除革(49)内的多余裸井标题
    _fix_474849 = re.compile(
        r'(四、財祿不守.*?解之唯大過可也。)\s*\n\s*'
        r'(- 一、婚事娶二婚妻.*?)'
        r'(# \*\*四十九、澤火革.*?\*\*)\s*\n\s*'
        r'\*\*四十八、水風井.*?\*\*',
        re.DOTALL
    )
    text = _fix_474849.sub(
        r'\1\n\n# **四十八、水風井䷯**\n\n\2\n\n\3',
        text
    )

    # ── 3. 清理标题行 OCR 重复 ──
    # 标题格式: # **N、卦名symbol ...重复垃圾...**
    # 保留: # **N、卦名symbol**
    def _clean_header(m):
        cn = m.group(2)       # e.g. "十一"
        name = m.group(3)     # e.g. "地天泰"
        symbol = m.group(4)   # e.g. "䷊"
        return f"# **{cn}、{name}{symbol}**"

    _header_fix = re.compile(
        r'^(#{1,4}\s+)\*{0,2}'
        r'([一二三四五六七八九十]+)、'
        r'([^\*䷀-䷿]+?)'
        r'([䷀-䷿])'
        r'.*$',
        re.MULTILINE
    )
    text = _header_fix.sub(_clean_header, text)

    # 修复缺 # 的标题: **四十八、水風井䷯** → # **四十八、水風井䷯**
    _no_hash_header = re.compile(
        r'^\*{2}'
        r'([一二三四五六七八九十]+)、'
        r'([^\*䷀-䷿]+?)'
        r'([䷀-䷿])\*{2}'
        r'$',
        re.MULTILINE
    )
    text = _no_hash_header.sub(r'# **\1、\2\3**', text)

    # ── 3.5. 风水篇子标题 OCR 重复修复 ──
    # 标题格式: #... **(N)标题 [(N)标题...重复...]**
    # 清理为: #### **（N）标题**（统一 # 级别 + 中文括号）
    def _fix_fengshui_header(m):
        line = m.group(0).strip()
        line = re.sub(r'^#{1,4}\s+\*{0,2}', '', line)
        line = re.sub(r'\*{0,2}\s*$', '', line)
        mt = re.match(r'\(([一二三四五六七八九十]+)\)([^\(]+)', line)
        if mt:
            num = mt.group(1)
            title = mt.group(2).strip()
            return f'#### **（{num}）{title}**'
        return m.group(0)

    _fengshui_re = re.compile(
        r'^#{1,4}\s+\*{0,2}\([一二三四五六七八九十]+\)[^\n]+$',
        re.MULTILINE
    )
    text = _fengshui_re.sub(_fix_fengshui_header, text)

    # ── 4. 清理 CJK 字符间的多余空格 ──
    # 中文之间不应该有空格（OCR 产物）
    text = re.sub(r'(?<=[一-鿿])\s(?=[一-鿿])', '', text)

    # ── 5. 统一编号条目格式 ──
    # "  - 一、" 或 "- 一、" 或 "  一、" → "一、"
    text = re.sub(r'^\s*-\s+([一二三四五六七八九十]+、)', r'\1', text, flags=re.MULTILINE)
    text = re.sub(r'^\s{2,}([一二三四五六七八九十]+、)', r'\1', text, flags=re.MULTILINE)

    # 清理编号后多余空格: "一、  " → "一、"
    text = re.sub(r'([一二三四五六七八九十]+、)\s{2,}', r'\1', text)

    # ── 6. 清理 #### 子标题混入 ──
    # "#### 出此局其造成:" → "出此局其造成:"
    # "#### 傷害甚大。" → "傷害甚大。"
    # 但保留 "#### **地理篇**" 这类真正的 section 标题
    text = re.sub(r'^####\s+(?!\*\*)', '', text, flags=re.MULTILINE)

    # ── 7. 清理多余空行（3+ 连续空行 → 2 个空行） ──
    text = re.sub(r'\n{3,}', '\n\n', text)

    # ── 8. 西文标点 → 中文标点（仅 CJK 语境，保留 markdown 语法和链接） ──
    text = re.sub(r'(?<=[一-鿿]),', '，', text)        # 逗号：CJK 后
    text = re.sub(r',(?=[一-鿿])', '，', text)        # 逗号：CJK 前
    text = re.sub(r'(?<=[一-鿿]):', '：', text)        # 冒号
    text = re.sub(r':(?=[一-鿿])', '：', text)
    text = re.sub(r'(?<=[一-鿿])\?', '？', text)       # 问号
    text = re.sub(r'\?(?=[一-鿿])', '？', text)
    text = re.sub(r'(?<=[一-鿿])!', '！', text)        # 感叹号
    text = re.sub(r'!(?=[一-鿿])', '！', text)
    text = re.sub(r'(?<=[一-鿿]);', '；', text)        # 分号
    text = re.sub(r';(?=[一-鿿])', '；', text)
    text = re.sub(r'\((?=[一-鿿\d])', '（', text)       # 左括号后接 CJK/数字
    text = re.sub(r'(?<=[一-鿿])\)', '）', text)       # 右括号前是 CJK

    # ── 9. 清理 HTML 标签残留 ──
    text = re.sub(r'<[^>]+>', '', text)

    return text


# ═══════════════════════════════════════════════════════
#  MD 解析：提取 64 卦章节
# ═══════════════════════════════════════════════════════

# 匹配卦标题行：以 # 或 ** 开头，后跟中文数字 + 、
_HEADER_RE = re.compile(
    r'^(?:#{1,4}\s+\*{0,2}|\*{2})'    # 必须有 # 或 ** 前缀
    r'([一二三四五六七八九十]+)、'      # 中文序号
    r'.+$',
    re.MULTILINE
)

_END_MARKERS = ["導言", "風水篇", "結語"]


def _find_section_boundaries(text):
    """扫描清理后的 MD 全文，返回 64 卦章节范围 [(hex_num, start, end), ...]。

    章节范围 = [标题行开头, 下一个标题行开头)。
    最后一个卦在 導言/風水篇/結語 之前截断。
    """
    sections = []
    for m in _HEADER_RE.finditer(text):
        cn_num = m.group(1)
        hex_num = cn_to_int(cn_num)
        if hex_num is None or hex_num < 1 or hex_num > 64:
            continue
        sections.append((hex_num, m.start()))

    if not sections:
        return []

    sections.sort(key=lambda x: x[1])

    result = []
    for i, (hex_num, start) in enumerate(sections):
        if i + 1 < len(sections):
            end = sections[i + 1][1]
        else:
            end = len(text)
            for marker in _END_MARKERS:
                em = re.search(
                    r'^#{1,4}\s+\*{0,2}' + re.escape(marker),
                    text[start:],
                    re.MULTILINE
                )
                if em:
                    end = min(end, start + em.start())

        if hex_num not in {r[0] for r in result}:
            result.append((hex_num, start, end))

    result.sort(key=lambda x: x[0])
    return result


def _extract_body(text, start, end):
    """提取章节正文（去掉标题行）。"""
    line_end = text.find('\n', start)
    if line_end == -1 or line_end >= end:
        return ""
    return text[line_end:end].strip()


# ═══════════════════════════════════════════════════════
#  智能段落拆分：每个编号条目 = 一个数组元素
# ═══════════════════════════════════════════════════════

# 检测一行是否以中文序号开头（一、二、...）
_ITEM_START_RE = re.compile(r'^[一二三四五六七八九十]+、')


def _split_items(body):
    """将正文拆分为独立条目数组。

    规则：
      - 以「N、」开头的行 → 新条目开始
      - 非「N、」开头的行 → 续接当前条目
      - 空行 → 结束当前条目，但不创建空白条目
      - 同时处理 OCR 把多条合并到一行的情况（。后紧跟下一个 N、）

    Args:
        body: 清理后的章节正文

    Returns:
        list[str]: 条目列表
    """
    if not body:
        return []

    lines = body.split('\n')
    raw_items = []       # 按行聚合后的原始条目
    current_lines = []   # 当前条目累积的行

    for line in lines:
        stripped = line.strip()

        if not stripped:
            # 空行 → 刷新当前条目
            if current_lines:
                raw_items.append(''.join(current_lines))
                current_lines = []
            continue

        # 检查本行是否包含「N、」（中间某处） → 可能 intro 和 item 被 OCR 合并
        item_pos = re.search(r'[一二三四五六七八九十]+、', stripped)
        if item_pos and not stripped.startswith(item_pos.group()):
            # 行内合并：intro文字 + N、item → 拆成两段
            intro_part = stripped[:item_pos.start()].strip()
            item_part = stripped[item_pos.start():]
            if current_lines:
                raw_items.append(''.join(current_lines))
            if intro_part:
                raw_items.append(intro_part)
            current_lines = [item_part]
        elif _ITEM_START_RE.match(stripped):
            if current_lines:
                raw_items.append(''.join(current_lines))
            current_lines = [stripped]
        else:
            # 续接行
            current_lines.append(stripped)

    # 最后一个条目
    if current_lines:
        raw_items.append(''.join(current_lines))

    # ── 进一步拆分：处理 OCR 把多条合并到一行的情况 ──
    # 如：「一、内容A。二、内容B。三、内容C。」
    # 按 。/；后紧跟「N、」的位置切分
    result = []
    for item in raw_items:
        sub_items = _split_inline(item)
        result.extend(sub_items)

    return result


def _split_inline(text):
    """拆分同一行中被 OCR 合并的多条编号条目。

    切分点：句号/分号 之后紧跟下一个「N、」

    Example:
        "一、内容A。二、内容B。" → ["一、内容A。", "二、内容B。"]
    """
    parts = re.split(r'(?<=[。；])(?=[一二三四五六七八九十]+、)', text)
    cleaned = []
    for p in parts:
        p = p.strip()
        if p:
            cleaned.append(p)
    return cleaned if len(cleaned) > 1 else [text]


# ═══════════════════════════════════════════════════════
#  JSONC 文件匹配 & 写入
# ═══════════════════════════════════════════════════════

def _find_jsonc(hex_num):
    """根据卦序号（1-64）按 "XX_" 前缀匹配 JSONC 文件。"""
    prefix = f"{hex_num:02d}_"
    for fname in sorted(os.listdir(DATA_DIR)):
        if fname.startswith(prefix) and fname.endswith(".jsonc") and fname != "lock.jsonc":
            return os.path.join(DATA_DIR, fname), fname
    return None, None


def save_jsonc(path, data):
    """按模板格式保存 JSONC 文件。"""
    template = load_jsonc(TEMPLATE_FILE)
    text = format_by_template(data, template, TEMPLATE_FILE)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ═══════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════

def main():
    fix_md = "--fix-md" in sys.argv

    if not os.path.exists(MD_FILE):
        print(f"❌ 源文件不存在: {MD_FILE}")
        return

    with open(MD_FILE, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # ── 清理全文 ──
    text = clean_full_text(raw_text)

    # ── 写回清理后的 MD ──
    if fix_md:
        with open(MD_CLEAN_FILE, "w", encoding="utf-8") as f:
            f.write(text)
        print("📝 已写回清理后的 MD 文件\n")

    # ── 解析 64 卦章节 ──
    sections = _find_section_boundaries(text)
    print(f"📂 解析到 {len(sections)} 个卦章节\n")

    if len(sections) != 64:
        found = {s[0] for s in sections}
        missing = sorted(set(range(1, 65)) - found)
        if missing:
            print(f"⚠️  缺失序号: {missing}\n")

    updated = 0
    skipped = 0
    empty_count = 0

    for hex_num, start, end in sections:
        body = _extract_body(text, start, end)
        items = _split_items(body)

        filepath, jfname = _find_jsonc(hex_num)
        if not filepath:
            print(f"  ⚠️  卦{hex_num}: 未找到对应 JSONC 文件（前缀 {hex_num:02d}_），跳过")
            skipped += 1
            continue

        data = load_jsonc(filepath)
        hex_name = data.get("full_name", f"卦{hex_num}")

        data.setdefault("nishi", {}).setdefault("home", {})
        data["nishi"]["home"]["description"] = items

        save_jsonc(filepath, data)
        updated += 1

        if not items:
            print(f"  ⚠️  {jfname} ({hex_name}): 描述为空")
            empty_count += 1
        else:
            print(f"  ✅ {jfname} ({hex_name}): {len(items)} 段")

    print(f"\n{'=' * 50}")
    print(f"✅ 已更新: {updated}")
    print(f"⏭️  跳过: {skipped}")
    print(f"⚠️  描述为空: {empty_count}")
    print(f"📊 总计: {len(sections)} 个章节")


if __name__ == "__main__":
    main()
