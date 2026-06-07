"""
起卦案例存储管理器 — 保存/加载/查询/删除 起卦历史记录

═══════════════════════════════════════════════════════════════
文件职责：提供完整的案例 CRUD 接口，存储起卦历史到本地 JSON 文件
═══════════════════════════════════════════════════════════════

每个案例记录：
    - 起卦方式（手工/报数/金钱/蓍草）
    - 本卦 + 变卦（ID、名称、符号）
    - 上下卦先天数 + 动爻列表
    - 年月日时（北京时间）
    - 备注

数据存储：默认 usrCfg/divination_cases.json（JSON 数组）
           所有公开函数均接受可选 store_path 参数，可指定自定义路径

设计原则：
    - 数据库路径可传递 — 所有函数接受可选 store_path 参数
    - 未来切换存储位置或测试时，只需传入不同路径，无需修改内部逻辑
    - 不依赖卦名搜索 — 直接通过路径定位数据文件

导出函数：
    save_case()    — 保存案例 → 返回 case_id
    load_cases()   — 加载全部案例
    get_case()     — 按 ID 查询单个案例
    delete_case()  — 按 ID 删除案例
    clear_cases()  — 清空全部案例

被哪些文件调用：
    - divination_panel.py: 起卦完成后调用 save_case 保存
    - 未来：案例管理 Tab 调用 load_cases / get_case / delete_case

依赖：
    - bagua.py: GuaResult dataclass
    - config_manager.py: 风格参考（文件读写模式一致）

用法示例:
    from src.qigua.case_manager import save_case, load_cases, get_case, delete_case

    # 使用默认路径
    result = calc_three_numbers(123, 456, 789)
    case_id = save_case(result, method="three", notes="今日运势")

    # 使用自定义路径
    case_id = save_case(result, method="three", store_path="/custom/cases.json")

    # 加载全部案例
    cases = load_cases()                    # 默认路径
    cases = load_cases(store_path="...")    # 自定义路径
"""
import json
import os
import uuid
from datetime import datetime
from typing import Optional

from .bagua import GuaResult

# ── 默认存储路径（与 usrCfg/UsrCfg.json 同目录）──
_DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "usrCfg")
_DEFAULT_PATH = os.path.join(_DEFAULT_DIR, "divination_cases.json")


def _ensure_store(store_path: str | None = None) -> list:
    """
    读取案例文件，返回案例列表。

    文件不存在或损坏时返回空列表，不抛异常。

    Parameters:
        store_path: str | None — 存储文件路径，None 使用默认路径

    Returns:
        list[dict]: 案例列表（可能为空）

    内部使用，外部代码通过 load_cases() 获取。
    """
    path = store_path or _DEFAULT_PATH
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_store(cases: list, store_path: str | None = None):
    """
    将案例列表写入存储文件。
    自动创建目录（如不存在）。

    Parameters:
        cases: list[dict] — 案例列表
        store_path: str | None — 存储文件路径，None 使用默认路径

    内部使用，自动处理异常。
    """
    path = store_path or _DEFAULT_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cases, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # 写入失败静默处理，不抛异常影响主流程


def save_case(result: GuaResult, method: str, notes: str = "",
              store_path: str | None = None) -> str:
    """
    保存一个起卦案例到本地 JSON 文件。

    Parameters:
        result:     GuaResult — 起卦结果（来自 hexagram_calc）
        method:     str — 起卦方式 ("manual" / "three" / "coin" / "yarrow")
        notes:      str — 备注（可选，如"今日运势"）
        store_path: str | None — 存储文件路径，None 使用默认 usrCfg/divination_cases.json

    Returns:
        str: 案例 ID（UUID[:8] 格式，可用于后续查询/删除）

    使用示例:
        from src.qigua.hexagram_calc import calc_three_numbers
        from src.qigua.case_manager import save_case

        result = calc_three_numbers(123, 456, 789)
        case_id = save_case(result, method="three", notes="问事业")
        # 自定义路径示例
        case_id = save_case(result, method="three", store_path="/my/cases.json")

    存储字段说明:
        - id:              唯一标识（UUID[:8]）
        - timestamp:       保存时间 ISO 格式
        - method:          起卦方式
        - ben_gua_id:      本卦 ID (1-64)
        - ben_gua_name:    本卦全名（如"乾为天"）
        - ben_gua_symbol:  本卦符号（如"䷀"）
        - bian_gua_id:     变卦 ID，无变卦时 null
        - bian_gua_name:   变卦全名
        - bian_gua_symbol: 变卦符号
        - lower_num:       下卦先天数 (1-8)
        - upper_num:       上卦先天数 (1-8)
        - changing_lines:  动爻列表 [1..6]，空列表=六爻皆静
        - year/month/day/hour: 保存时的北京时间
        - notes:           备注
    """
    now = datetime.now()
    ben = result.ben_gua or {}
    bian = result.bian_gua

    case = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": now.isoformat(),
        "method": method,
        # 本卦
        "ben_gua_id": ben.get("id"),
        "ben_gua_name": ben.get("full_name", ""),
        "ben_gua_symbol": ben.get("symbol", ""),
        # 变卦
        "bian_gua_id": bian.get("id") if bian else None,
        "bian_gua_name": bian.get("full_name", "") if bian else None,
        "bian_gua_symbol": bian.get("symbol", "") if bian else None,
        # 先天数
        "lower_num": result.lower_num,
        "upper_num": result.upper_num,
        # 动爻
        "changing_lines": sorted(result.changing_lines) if result.changing_lines else [],
        # 时间
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "hour": now.hour,
        # 备注
        "notes": notes,
    }

    cases = _ensure_store(store_path)
    cases.insert(0, case)  # 最新案例在最前面
    _write_store(cases, store_path)
    return case["id"]


def load_cases(store_path: str | None = None) -> list[dict]:
    """
    加载全部起卦案例，按时间倒序排列（最新在前）。

    Parameters:
        store_path: str | None — 存储文件路径，None 使用默认路径

    Returns:
        list[dict]: 案例列表，每个元素为 dict（字段见 save_case 文档）。
                    无案例时返回空列表。

    使用示例:
        cases = load_cases()
        for c in cases:
            print(f"[{c['method']}] {c['ben_gua_name']} → {c.get('bian_gua_name')}")
    """
    return _ensure_store(store_path)


def get_case(case_id: str, store_path: str | None = None) -> Optional[dict]:
    """
    按 ID 查询单个案例。

    Parameters:
        case_id:    str — save_case 返回的案例 ID
        store_path: str | None — 存储文件路径，None 使用默认路径

    Returns:
        dict | None: 案例数据，找不到返回 None

    使用示例:
        case = get_case("a1b2c3d4")
        if case:
            print(case["ben_gua_name"])
    """
    for c in _ensure_store(store_path):
        if c.get("id") == case_id:
            return c
    return None


def delete_case(case_id: str, store_path: str | None = None) -> bool:
    """
    按 ID 删除案例。

    Parameters:
        case_id:    str — 要删除的案例 ID
        store_path: str | None — 存储文件路径，None 使用默认路径

    Returns:
        bool: 是否成功删除（True=已删除，False=未找到）

    使用示例:
        if delete_case("a1b2c3d4"):
            print("已删除")
    """
    cases = _ensure_store(store_path)
    new_list = [c for c in cases if c.get("id") != case_id]
    if len(new_list) < len(cases):
        _write_store(new_list, store_path)
        return True
    return False


def clear_cases(store_path: str | None = None) -> int:
    """
    清空所有案例。

    Parameters:
        store_path: str | None — 存储文件路径，None 使用默认路径

    Returns:
        int: 被删除的案例数量

    使用示例:
        n = clear_cases()
        print(f"已清空 {n} 条案例")
    """
    cases = _ensure_store(store_path)
    if cases:
        _write_store([], store_path)
        return len(cases)
    return 0
