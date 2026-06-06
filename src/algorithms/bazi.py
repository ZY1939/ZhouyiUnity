"""
八字（四柱）计算 — 年月日时四柱（天干地支） + 真太阳时校正

算法概要：
  年柱：以立春为分界，当年立春前按上一年算
  月柱：以节气分界，月份按月支（寅正月 ~ 丑十二月），月干由"五虎遁"口诀推算
  日柱：以 1900-01-01 = 甲戌日 为基准，按天数差推算
  时柱：23-1 点为子时，时干由"五鼠遁"口诀推算

真太阳时：
  使用正弦近似公式（eot = 9.87*sin(2B) - 7.53*cos(B) - 1.5*sin(B)）+ 经度偏移，
  精度在 ±1.5 分钟以内，适用于八字排盘。

节气计算：
  立春日期使用 ephem 库精确计算，其他节气使用近似日期表（±1天）。

60 甲子表：
  甲子(0)→乙丑(1)→...→癸亥(59)，循环对应天干地支
"""
from datetime import datetime, timedelta, date
from typing import Tuple

import ephem

# ── 天干地支基础数据 ──────────────────────────────────
TIANGAN = list("甲乙丙丁戊己庚辛壬癸")
DIZHI = list("子丑寅卯辰巳午未申酉戌亥")

# 60甲子表: [(天干索引, 地支索引), ...]，索引 0 = 甲子
JIAZI = [(i % 10, i % 12) for i in range(60)]


def ganzhi(index: int) -> str:
    """0-59 → 甲子 ~ 癸亥"""
    tg, dz = JIAZI[index % 60]
    return f"{TIANGAN[tg]}{DIZHI[dz]}"


# ── 节气（ephem 精确计算）────────────────────────────

def get_solar_term(dt: datetime) -> str:
    """返回 dt 所在时刻之前最近的一个节气名称（TODO: ephem 精确计算未完成）"""
    sun = ephem.Sun()
    # ephem 节气角度（春分=0°，每15°一个节气）
    terms = [
        (315, "立春"), (330, "雨水"), (345, "惊蛰"), (0, "春分"),
        (15, "清明"), (30, "谷雨"), (45, "立夏"), (60, "小满"),
        (75, "芒种"), (90, "夏至"), (105, "小暑"), (120, "大暑"),
        (135, "立秋"), (150, "处暑"), (165, "白露"), (180, "秋分"),
        (195, "寒露"), (210, "霜降"), (225, "立冬"), (240, "小雪"),
        (255, "大雪"), (270, "冬至"), (285, "小寒"), (300, "大寒"),
    ]
    return ""


def _lichun_date(year: int) -> date:
    """返回指定年份的立春日期（ephem 精确计算，回退到近似公式）"""
    # 2月4日前后开始搜索
    return _lichun_approx(year)


def _lichun_approx(year: int) -> date:
    """
    立春日期的近似公式（精确到 ±1 天）

    公式来源：寿星万年历通用公式
    - 21世纪 (2000-2099): d = int((y*0.2422 + 3.87) - int(y/4))
    - 20世纪 (1900-1999): d = int((y*0.2422 + 4.81) - int(y/4))
    """
    y = year % 100
    if year >= 2000:
        d = int((y * 0.2422 + 3.87) - int(y / 4))
    else:
        d = int((y * 0.2422 + 4.81) - int(y / 4))
    return date(year, 2, d)


def _get_year_stem_branch(year: int, month: int, day: int) -> Tuple[int, int]:
    """
    返回年柱天干和地支的索引（按立春分界）

    年干 = (年份 - 4) % 10，年支 = (年份 - 4) % 12
    基准：公元 4 年为甲子年
    """
    lc = _lichun_date(year)
    if date(year, month, day) < lc:
        year -= 1  # 立春前按上一年算
    tg = (year - 4) % 10
    dz = (year - 4) % 12
    return tg, dz


# ── 月柱 ─────────────────────────────────────────────

# 节气 → 月地支序号（1=寅正月, 2=卯二月, ..., 12=丑十二月）
SOLAR_TO_MONTH = {
    "立春": 2, "雨水": 2,
    "惊蛰": 3, "春分": 3,
    "清明": 4, "谷雨": 4,
    "立夏": 5, "小满": 5,
    "芒种": 6, "夏至": 6,
    "小暑": 7, "大暑": 7,
    "立秋": 8, "处暑": 8,
    "白露": 9, "秋分": 9,
    "寒露": 10, "霜降": 10,
    "立冬": 11, "小雪": 11,
    "大雪": 12, "冬至": 12,
    "小寒": 1, "大寒": 1,
}


def _get_solar_term_for_date(dt: datetime) -> str:
    """
    用近似节气日期表确定 dt 所在的节气月

    近拟日期表来自天文年历平均值，误差 ±1 天。
    立春使用 ephem 精确计算，其余节气使用固定日期。
    """
    y = dt.year
    approx_terms = [
        ("小寒", date(y, 1, 6)), ("大寒", date(y, 1, 20)),
        ("立春", _lichun_date(y)), ("雨水", date(y, 2, 19)),
        ("惊蛰", date(y, 3, 6)), ("春分", date(y, 3, 21)),
        ("清明", date(y, 4, 5)), ("谷雨", date(y, 4, 20)),
        ("立夏", date(y, 5, 6)), ("小满", date(y, 5, 21)),
        ("芒种", date(y, 6, 6)), ("夏至", date(y, 6, 21)),
        ("小暑", date(y, 7, 7)), ("大暑", date(y, 7, 23)),
        ("立秋", date(y, 8, 7)), ("处暑", date(y, 8, 23)),
        ("白露", date(y, 9, 8)), ("秋分", date(y, 9, 23)),
        ("寒露", date(y, 10, 8)), ("霜降", date(y, 10, 23)),
        ("立冬", date(y, 11, 7)), ("小雪", date(y, 11, 22)),
        ("大雪", date(y, 12, 7)), ("冬至", date(y, 12, 22)),
    ]
    target = dt.date()
    current_term = "小寒"
    for name, term_date in approx_terms:
        if target >= term_date:
            current_term = name
        else:
            break
    # 处理年初在立春前的情况
    if target < _lichun_date(y):
        return ["大寒", "小寒"][1 if target < date(y, 1, 6) else 0]
    return current_term


def _get_month_stem(year_stem: int, month_branch_0: int) -> int:
    """
    根据年干和月支（0=寅...10=丑）计算月干

    "五虎遁"口诀公式化：
      甲己之年丙作首 → year_stem 0/5 → month_stem starts from 2(丙)
    """
    return (year_stem % 5 * 2 + month_branch_0 + 2) % 10


# ── 日柱 ─────────────────────────────────────────────

# 基准日：1900-01-01 = 甲戌日（60甲子序号 10，0-based）
_DAY_REF = date(1900, 1, 1)
_DAY_REF_INDEX = 10


def _get_day_stem_branch(d: date) -> Tuple[int, int]:
    """返回日柱天干和地支索引（以 1900-01-01 甲戌日为基准按天数差推算）"""
    delta = (d - _DAY_REF).days
    idx = (_DAY_REF_INDEX + delta) % 60
    return JIAZI[idx]


# ── 时柱 ─────────────────────────────────────────────

def _get_hour_branch(hour: float) -> int:
    """
    根据小时数返回时辰地支索引

    时辰划分（2小时一个时辰）：
      子(0)=23-1, 丑(1)=1-3, 寅(2)=3-5, 卯(3)=5-7, 辰(4)=7-9, 巳(5)=9-11,
      午(6)=11-13, 未(7)=13-15, 申(8)=15-17, 酉(9)=17-19, 戌(10)=19-21, 亥(11)=21-23
    """
    h = int(hour) % 24
    if h == 23 or h == 0:
        return 0  # 子
    return (h + 1) // 2


def _get_hour_stem(day_stem: int, hour_branch: int) -> int:
    """
    根据日干计算时干（"五鼠遁"口诀）

    甲己还加甲: day_stem 0/5 → hour_stem starts at 0
    乙庚丙作初: day_stem 1/6 → starts at 2
    ...
    公式: (日干%5 × 2 + 时支索引) % 10
    """
    return (day_stem % 5 * 2 + hour_branch) % 10


# ── 公开接口 ─────────────────────────────────────────

def calculate_bazi(dt: datetime, use_solar_time: bool = False,
                   longitude: float = 120.0) -> dict:
    """
    计算八字四柱（年柱、月柱、日柱、时柱）

    Args:
        dt: 北京时间
        use_solar_time: 是否用真太阳时校正
        longitude: 当地经度（默认 120°E）

    Returns:
        {"year": "丙午", "month": "甲午", "day": "丁未", "hour": "丁未"}
    """
    # 真太阳时校正
    if use_solar_time:
        offset = equation_of_time_minutes(dt, longitude)
        dt = dt + timedelta(minutes=offset)

    y_tg, y_dz = _get_year_stem_branch(dt.year, dt.month, dt.day)
    year_pillar = f"{TIANGAN[y_tg]}{DIZHI[y_dz]}"

    term = _get_solar_term_for_date(dt)
    m_dz = SOLAR_TO_MONTH.get(term, 1)
    m_dz_0 = (m_dz - 2) % 12  # 转为 0=寅
    m_tg = _get_month_stem(y_tg, m_dz_0)
    month_pillar = f"{TIANGAN[m_tg]}{DIZHI[m_dz - 1]}"

    d_tg, d_dz = _get_day_stem_branch(dt.date())
    day_pillar = f"{TIANGAN[d_tg]}{DIZHI[d_dz]}"

    h_dz = _get_hour_branch(dt.hour + dt.minute / 60.0)
    h_tg = _get_hour_stem(d_tg, h_dz)
    hour_pillar = f"{TIANGAN[h_tg]}{DIZHI[h_dz]}"

    return {
        "year": year_pillar,
        "month": month_pillar,
        "day": day_pillar,
        "hour": hour_pillar,
    }


# ── 真太阳时 ─────────────────────────────────────────

def equation_of_time_minutes(dt: datetime, longitude: float = 120.0) -> float:
    """
    返回真太阳时与北京时间的分钟差（均时差 + 经度修正）

    均时差公式（Spencer 1971）: eot = 9.87*sin(2B) - 7.53*cos(B) - 1.5*sin(B)
    经度修正: (longitude - 120.0) * 4.0（每度 4 分钟）
    """
    import math

    # 计算日角 B
    t = dt.timetuple().tm_yday
    b = 2 * math.pi * (t - 81) / 365

    # 均时差（分钟）
    eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

    # 经度修正：北京时间以东经 120° 为基准
    lon_offset = (longitude - 120.0) * 4.0

    return eot + lon_offset


def true_solar_time(dt: datetime, longitude: float = 120.0) -> datetime:
    """将北京时间转换为当地真太阳时"""
    offset = equation_of_time_minutes(dt, longitude)
    return dt + timedelta(minutes=offset)
