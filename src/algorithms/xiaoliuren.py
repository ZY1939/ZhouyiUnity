"""
倪师小六壬算法 — 根据农历月+日+时辰推算掌诀

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【什么是小六壬】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  小六壬是民间流传的一种简易占卜方法，在手掌上按"大安→留连→速喜→赤口→小吉→空亡"
  六个位置顺数，根据农历月份、日期和时辰三次计数，最终落位即为断事依据。

  倪师（倪海厦）在小六壬基础上加入了每个掌诀的详细断辞，按吉凶分类。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【六个掌诀】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  位置 0: 大安  — 吉 — 事事昌盛，求谋顺遂
  位置 1: 留连  — 凶 — 事难成就，去者未归
  位置 2: 速喜  — 吉 — 喜事来临，求谋即就
  位置 3: 赤口  — 凶 — 口舌是非，官非切要防
  位置 4: 小吉  — 吉 — 凡事可谋，多吉多利
  位置 5: 空亡  — 凶 — 谋事落空，劳而无成

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【推算方法（三次顺数）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  起点：大安（位置 0）

  第一次（月上起日）：
    从大安开始顺数农历月份 → 例如三月：大安(1)→留连(2)→速喜(3)，落在速喜

  第二次（日上起时）：
    从上一步落位开始顺数农历日期 → 例如十五日：从速喜开始数 15 位

  第三次（时上查掌诀）：
    从上一步落位开始顺数时辰编号 → 最终落位即为结果

  举例：农历三月初三 巳时
    月上：大安(1)→留连(2)→速喜(3) → 速喜
    日上：速喜(1)→赤口(2)→小吉(3) → 小吉
    时上：小吉(1)→空亡(2)→大安(3)→留连(4)→速喜(5)→赤口(6) → 赤口
    结果：赤口（凶）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【时辰编号】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  子(1) 丑(2) 寅(3) 卯(4) 辰(5) 巳(6)
  午(7) 未(8) 申(9) 酉(10) 戌(11) 亥(12)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【依赖】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  - lunardate: 阳历→农历转换
  - datetime: 获取当前时间 + 确定时辰
"""
from datetime import datetime
from lunardate import LunarDate


# ── 六个掌诀（按顺数顺序）────────────────────────────

_POSITIONS = ["大安", "留连", "速喜", "赤口", "小吉", "空亡"]

# 吉凶属性：True=吉, False=凶
_FORTUNE = {
    "大安": True,
    "留连": False,
    "速喜": True,
    "赤口": False,
    "小吉": True,
    "空亡": False,
}

# 倪师断辞 — 每个掌诀的详细解释
_INTERPRETATIONS = {
    "大安": {
        "summary": "事事昌盛，求谋顺遂",
        "detail": (
            "身不动时，五行属木，颜色青色，方位东方。"
            "临青龙，谋事主一、五、七。"
            "有静止、心安、吉祥之含义。"
        ),
    },
    "留连": {
        "summary": "事难成就，去者未归",
        "detail": (
            "卒未归时，五行属水，颜色黑色，方位北方。"
            "临玄武，谋事主二、八、十。"
            "有喑味不明、延迟、纠缠之含义。"
        ),
    },
    "速喜": {
        "summary": "喜事来临，求谋即就",
        "detail": (
            "人便至时，五行属火，颜色红色，方位南方。"
            "临朱雀，谋事主三、六、九。"
            "有快速、喜事、吉利之含义。"
        ),
    },
    "赤口": {
        "summary": "口舌是非，官非切要防",
        "detail": (
            "官事凶时，五行属金，颜色白色，方位西方。"
            "临白虎，谋事主四、七、十。"
            "有不吉、惊恐、口舌是非之含义。"
        ),
    },
    "小吉": {
        "summary": "凡事可谋，多吉多利",
        "detail": (
            "人来喜时，五行属木，颜色青色，方位东方。"
            "临六合，谋事主一、五、七。"
            "有和合、吉利、顺利之含义。"
        ),
    },
    "空亡": {
        "summary": "谋事落空，劳而无成",
        "detail": (
            "音信稀时，五行属土，颜色黄色，方位中央。"
            "临勾陈，谋事主三、六、九。"
            "有落空、徒劳、无果之含义。"
        ),
    },
}


# ── 时辰确定 ────────────────────────────────────────

def _current_shichen_index(now: datetime) -> int:
    """
    根据当前时间返回时辰编号（1-12）

    参数:
        now (datetime): 当前时间

    返回:
        int: 时辰编号 1-12
             1=子(23-1), 2=丑(1-3), 3=寅(3-5), 4=卯(5-7),
             5=辰(7-9), 6=巳(9-11), 7=午(11-13), 8=未(13-15),
             9=申(15-17), 10=酉(17-19), 11=戌(19-21), 12=亥(21-23)

    算法:
        将 24 小时制的起点偏移 +1 小时，使得 23-1 点映射到同一个时辰。
        (hour + 1) // 2 % 12 + 1

        例如: 15:30 → (15+1)//2=8, 8%12=8, 8+1=9 → 申时

    用法:
        >>> from datetime import datetime
        >>> _current_shichen_index(datetime(2026, 6, 7, 15, 30))
        9  # 申时
    """
    return ((now.hour + 1) // 2) % 12 + 1


def _shichen_name(index: int) -> str:
    """
    将时辰编号转为中文名称

    参数:
        index (int): 时辰编号 1-12

    返回:
        str: 时辰名称，如 "申时"、"子时"

    用法:
        >>> _shichen_name(9)
        '申时'
    """
    names = ["子", "丑", "寅", "卯", "辰", "巳",
             "午", "未", "申", "酉", "戌", "亥"]
    return f"{names[index - 1]}时"


# ── 核心推算 ────────────────────────────────────────

def calculate(lunar_month: int, lunar_day: int, shichen_index: int) -> dict:
    """
    根据农历月、日、时辰编号推算小六壬掌诀

    参数:
        lunar_month (int): 农历月份 1-12
        lunar_day (int): 农历日期 1-30
        shichen_index (int): 时辰编号 1-12

    返回:
        dict: {
            "position": str,        # 掌诀名称 "大安"/"留连"/"速喜"/"赤口"/"小吉"/"空亡"
            "fortune": True/False,  # True=吉, False=凶
            "interpretation": str,  # 总断语
            "detail": str,          # 详细断辞
            "steps": [str, ...],    # 推算过程（每一步的落位）
        }

    用法:
        >>> result = calculate(3, 3, 6)  # 农历三月三日 巳时
        >>> result["position"]
        '赤口'
        >>> result["fortune"]
        False

    推算过程说明:
        三次顺数，每一步都是从 1 开始数到目标数，落在六个位置之一。
        公式: (上一步位置 + 数字 - 1) % 6

        例如：三月三日巳时
          月上：大安(0) + 3月 - 1 = 2 → 速喜
          日上：速喜(2) + 3日 - 1 = 4 → 小吉
          时上：小吉(4) + 6(巳时) - 1 = 9, 9%6 = 3 → 赤口
    """
    steps = []

    # 第一步：月上起日（从大安 = 0 开始）
    pos = (lunar_month - 1) % 6
    steps.append(f"月上: 大安→{_POSITIONS[pos]} (数 {lunar_month} 位)")

    # 第二步：日上起时（从上一步落位开始）
    pos = (pos + lunar_day - 1) % 6
    steps.append(f"日上: →{_POSITIONS[pos]} (数 {lunar_day} 位)")

    # 第三步：时上查掌诀（从上一步落位开始）
    pos = (pos + shichen_index - 1) % 6
    steps.append(f"时上: →{_POSITIONS[pos]} (数 {shichen_index} 位, {_shichen_name(shichen_index)})")

    position = _POSITIONS[pos]
    interp = _INTERPRETATIONS[position]

    return {
        "position": position,
        "fortune": _FORTUNE[position],
        "interpretation": interp["summary"],
        "detail": interp["detail"],
        "steps": steps,
    }


def calculate_now(use_solar_time: bool = False, longitude: float = 120.0) -> dict:
    """
    根据当前时间自动计算小六壬（阳历自动转农历，自动确定时辰）

    参数:
        use_solar_time (bool): 是否用真太阳时校正时辰（默认False，用北京时间）
        longitude (float): 当地经度，用于真太阳时校正（默认120°E）

    返回:
        dict: 与 calculate() 返回值结构相同，额外包含:
            - "lunar_month": 农历月份
            - "lunar_day": 农历日期
            - "shichen": 时辰名称（如"申时"）

    用法:
        >>> from src.algorithms.xiaoliuren import calculate_now
        >>> result = calculate_now(use_solar_time=True, longitude=116.4)
        >>> print(f"{result['position']}({'吉' if result['fortune'] else '凶'})")
        小吉(吉)
    """
    from .bazi import true_solar_time

    now = datetime.now()
    lunar = LunarDate.fromSolarDate(now.year, now.month, now.day)

    # 用北京时间还是真太阳时来确定时辰
    ref_time = true_solar_time(now, longitude) if use_solar_time else now
    shichen_idx = _current_shichen_index(ref_time)

    result = calculate(lunar.month, lunar.day, shichen_idx)
    result["lunar_month"] = lunar.month
    result["lunar_day"] = lunar.day
    result["shichen"] = _shichen_name(shichen_idx)
    return result
