"""
加载和查询 64 卦 content JSONC 数据 — 整个起卦工具包的数据入口

═══════════════════════════════════════════════════════════════
文件职责：读取 src/data/yijing/content/*.jsonc，提供多种卦查询接口
═══════════════════════════════════════════════════════════════

数据来源：src/data/yijing/content/ 下的 .jsonc 文件（JSON + // 注释）
每文件含一卦的完整数据：id/name/full_name/symbol/binary/upper/lower/...

缓存机制：
    - _cache: dict[int, dict]     — {卦ID: 卦数据} 首次加载后缓存，避免重复读盘
    - _xiantian_index: dict       — {(上卦数, 下卦数): 卦ID} 快速反向查找
    - force_reload=True 可强制重读

设计原则：
    - 数据库路径可传递 — 所有公开函数接受可选 data_dir 参数
    - 调用方决定数据来源，无需修改模块内部逻辑
    - 测试时可指向 mock 数据目录

导出函数：
    load_all_gua(force_reload, data_dir)       → {卦ID: 卦数据} 全部64卦
    get_gua_by_id(gua_id, data_dir)            → 卦数据 | None  按1-64 ID查
    get_gua_by_xiantian(upper, lower, data_dir) → 卦数据 | None 按先天数查（如 1,2→天泽履）
    search_gua(query, data_dir)                 → [(ID, 卦数据), ...] 模糊搜索

搜索支持格式：
    - 数字 "1"      → 八纯卦（上下卦相同）
    - 范围 "1-2"    → 上乾下兑 → 天泽履
    - 卦名 "乾"     → 乾为天
    - 全名 "天泽履"  → 天泽履
    - 拼音首字母 "qwt" → 乾为天（简单拼音映射）

被哪些文件调用：
    - hexagram_calc.py: _build_result → get_gua_by_xiantian
    - hexagram_drawer.py: _update_gua_name → get_gua_by_xiantian
    - divination_panel.py: 间接通过 hexagram_calc
    - manual_input.py: setup_completer/search_gua/get_gua_by_xiantian
    - result_view.py: 间接通过 GuaResult

依赖：
    - bagua.py: NAME_TO_XIANTIAN（卦名→先天数）, BINARY_TO_GUA（binary→卦数据，由本文件填充）

用法示例:
    from src.yijingTab.com.hexagram_loader import load_all_gua, search_gua, get_gua_by_xiantian

    all_gua = load_all_gua()           # {1: {name:"乾", ...}, 2: {...}, ...}
    results = search_gua("乾")          # [(1, {name:"乾", full_name:"乾为天", ...})]
    gua = get_gua_by_xiantian(1, 2)    # 上乾下兑 → {id:10, full_name:"天泽履", ...}

    # 自定义数据目录
    all_gua = load_all_gua(data_dir="/custom/yijing/data/")
"""
import os
import re
import json

from .bagua import NAME_TO_XIANTIAN, BINARY_TO_GUA

# ── 默认数据目录（通过 CONST_DEFINE_UI 统一获取，便于目录结构变更时修改）──
from ..CONST_DEFINE_UI import get_yijing_content_dir
_CONTENT_DIR = get_yijing_content_dir()

# 缓存：避免重复读盘
_cache: dict[int, dict] | None = None
# (上卦先天数, 下卦先天数) → 卦ID
_xiantian_index: dict[tuple, int] | None = None
# 当前缓存对应的数据目录
_cached_dir: str | None = None


def _load_jsonc(path: str) -> dict:
    """
    读取 JSONC 文件，去掉 // 注释行后解析为 dict

    Parameters:
        path: str — .jsonc 文件路径

    Returns:
        dict: 解析后的 JSON 数据
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    # 去掉 // 开头的注释（整行或行尾）
    cleaned = re.sub(r"//.*", "", raw)
    return json.loads(cleaned)


def load_all_gua(force_reload: bool = False, data_dir: str | None = None) -> dict[int, dict]:
    """
    加载全部 64 卦，返回 {gua_id: data_dict}

    首次调用后缓存，force_reload=True 可强制重读。
    不同 data_dir 对应不同缓存，切换目录时自动重新加载。

    Parameters:
        force_reload: bool — True 强制重新读取磁盘，忽略缓存
        data_dir: str | None — 数据目录路径，None 使用默认 src/data/yijing/content/

    Returns:
        dict[int, dict]: 卦数据字典 {卦ID: 卦数据}

    使用示例:
        all_gua = load_all_gua()
        all_gua = load_all_gua(data_dir="/custom/data/")
    """
    global _cache, _xiantian_index, _cached_dir

    content_dir = data_dir or _CONTENT_DIR

    # 切换数据目录时重新加载
    if _cache is not None and not force_reload and _cached_dir == content_dir:
        return _cache

    _cache = {}
    _xiantian_index = {}
    _cached_dir = content_dir

    if not os.path.isdir(content_dir):
        print(f"[卦数据] ❌ 数据目录不存在: {content_dir}")
        print(f"[卦数据]    __file__ = {__file__}")
        return _cache

    print(f"[卦数据] ✓ 数据目录: {content_dir} ({len(os.listdir(content_dir))} 文件)")
    for fname in sorted(os.listdir(content_dir)):
        if not fname.endswith(".jsonc") or fname == "lock.jsonc":
            continue
        try:
            data = _load_jsonc(os.path.join(content_dir, fname))
            gid = data.get("id")
            if gid is None:
                continue
            _cache[gid] = data

            # 构建先天数索引
            upper_name = data.get("upper", "")
            lower_name = data.get("lower", "")
            upper_num = NAME_TO_XIANTIAN.get(upper_name)
            lower_num = NAME_TO_XIANTIAN.get(lower_name)
            if upper_num is not None and lower_num is not None:
                _xiantian_index[(upper_num, lower_num)] = gid

            # 构建 binary 索引
            binary = data.get("binary", "")
            if binary:
                BINARY_TO_GUA[binary] = data
        except (json.JSONDecodeError, KeyError):
            continue

    return _cache


def get_gua_by_id(gua_id: int, data_dir: str | None = None) -> dict | None:
    """
    按 ID (1-64) 获取卦数据

    Parameters:
        gua_id: int — 卦 ID，范围 1-64
        data_dir: str | None — 数据目录路径，None 使用默认路径

    Returns:
        dict | None: 卦数据，找不到返回 None

    使用示例:
        gua = get_gua_by_id(1)  # → 乾为天
    """
    all_gua = load_all_gua(data_dir=data_dir)
    return all_gua.get(gua_id)


def get_gua_by_xiantian(upper_num: int, lower_num: int,
                        data_dir: str | None = None) -> dict | None:
    """
    按先天数查找 64 卦

    Parameters:
        upper_num: int — 上卦先天数 (1-8)
        lower_num: int — 下卦先天数 (1-8)
        data_dir: str | None — 数据目录路径，None 使用默认路径

    Returns:
        dict | None: 卦数据，找不到返回 None

    使用示例:
        gua = get_gua_by_xiantian(1, 2)  # 上乾下兑 → 天泽履
    """
    load_all_gua(data_dir=data_dir)  # 确保索引已构建
    gid = _xiantian_index.get((upper_num, lower_num))
    if gid is None:
        return None
    return _cache.get(gid)


def search_gua(query: str, data_dir: str | None = None) -> list[tuple[int, dict]]:
    """
    搜索卦名，支持多种输入方式

    Parameters:
        query: str — 搜索词，支持：
            - 数字 "1" → 八纯卦
            - 范围 "1-2" → 上乾下兑 = 天泽履
            - 卦名 "乾" / "乾为天" / "天泽履"
            - 拼音首字母 "qwt" → 乾为天
        data_dir: str | None — 数据目录路径，None 使用默认路径

    Returns:
        list[tuple[int, dict]]: 匹配结果列表 [(卦ID, 卦数据), ...]

    使用示例:
        results = search_gua("乾")
        for gid, data in results:
            print(f"{data['symbol']} {data['full_name']} (ID:{gid})")
    """
    all_gua = load_all_gua(data_dir=data_dir)
    if not all_gua:
        return []

    q = query.strip()

    # 数字范围 "1-2"
    range_match = re.match(r"^(\d)\s*[-–]\s*(\d)$", q)
    if range_match:
        upper = int(range_match.group(1))
        lower = int(range_match.group(2))
        if 1 <= upper <= 8 and 1 <= lower <= 8:
            gua = get_gua_by_xiantian(upper, lower, data_dir=data_dir)
            if gua:
                return [(gua["id"], gua)]
        return []

    # 纯数字 "1" → 八纯卦
    digit_match = re.match(r"^(\d)$", q)
    if digit_match:
        num = int(digit_match.group(1))
        if 1 <= num <= 8:
            gua = get_gua_by_xiantian(num, num, data_dir=data_dir)
            if gua:
                return [(gua["id"], gua)]
        return []

    results = []
    q_lower = q.lower()

    for gid, data in all_gua.items():
        name = data.get("name", "")
        full_name = data.get("full_name", "")
        full_name_tc = data.get("fullName_tc", "")
        symbol = data.get("symbol", "")

        # 精确匹配卦名
        if q in (name, full_name, full_name_tc, symbol):
            results.append((gid, data))
            continue

        # 包含匹配
        if q_lower in name or q_lower in full_name or q_lower in full_name_tc:
            results.append((gid, data))
            continue

        # 拼音首字母匹配
        pinyin_initials = _get_pinyin_initials(full_name)
        if q_lower == pinyin_initials:
            results.append((gid, data))

    return results


def _get_pinyin_initials(text: str) -> str:
    """
    简单拼音首字母映射（常用卦名汉字）

    Parameters:
        text: str — 中文卦名（如"乾为天"）

    Returns:
        str: 拼音首字母串（如"qwt"）
    """
    _PINYIN_MAP = {
        "乾": "q", "坤": "k", "震": "z", "巽": "x", "坎": "k", "离": "l", "艮": "g", "兑": "d",
        "天": "t", "地": "d", "水": "s", "火": "h", "山": "s", "泽": "z", "雷": "l", "风": "f",
        "为": "w", "大": "d", "太": "t", "小": "x", "中": "z", "同": "t", "家": "j", "丰": "f",
        "旅": "l", "涣": "h", "节": "j", "孚": "f", "过": "g", "既": "j", "未": "w", "济": "j",
        "需": "x", "讼": "s", "师": "s", "比": "b", "畜": "c", "履": "l", "泰": "t", "否": "p",
        "同": "t", "有": "y", "谦": "q", "豫": "y", "随": "s", "蛊": "g", "临": "l", "观": "g",
        "噬": "s", "嗑": "k", "贲": "b", "剥": "b", "复": "f", "无": "w", "妄": "w", "颐": "y",
        "咸": "x", "恒": "h", "遁": "d", "壮": "z", "晋": "j", "夷": "y", "睽": "k", "蹇": "j",
        "解": "j", "损": "s", "益": "y", "夬": "g", "姤": "g", "萃": "c", "升": "s", "困": "k",
        "井": "j", "革": "g", "鼎": "d", "渐": "j", "归": "g", "妹": "m",
    }
    return "".join(_PINYIN_MAP.get(ch, "") for ch in text)
