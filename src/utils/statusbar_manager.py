"""
状态栏管理器 — 实时显示北京时间、真太阳时、农历、四柱

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【这个文件做什么】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  管理主窗口底部状态栏的实时信息显示。状态栏是所有 Tab 共用的底部信息条，
  不属于 settings 系统，独立管理。显示内容包括：
    1. 当前北京时间（HH:MM 格式，无秒）
    2. 真太阳时（如启用，按经度校正后的日晷时间）
    3. 当前农历日期（年/月/日，如"乙巳年三月十五"）
    4. 八字四柱（年柱 月柱 日柱 时柱，可选是否用真太阳时校正）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【外观风格】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  状态栏跟随系统深色/浅色模式自动切换配色（Qt 6.5+ colorScheme API）：
    - 深色模式: 深灰底(#2d2d30) + 白字(#f0f0f0)
    - 浅色模式: 浅灰底(#e8e8e8) + 黑字(#1d1d1f)
  macOS 和 Windows 均兼容，不随设置面板背景色联动。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【智能刷新速率】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  为了减少 CPU 占用，状态栏不是每秒都刷新：
    - 距离下一个时辰交界 > 2 分钟：每 30 秒刷新一次（慢模式）
    - 距离下一个时辰交界 ≤ 2 分钟：每秒刷新一次（快模式）

  这样既保证了时辰切换时的准时性，又避免了全天高频刷新的浪费。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【时辰说明】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  一天分为 12 个时辰，每个时辰 2 小时：
    子时 23:00-01:00   丑时 01:00-03:00   寅时 03:00-05:00
    卯时 05:00-07:00   辰时 07:00-09:00   巳时 09:00-11:00
    午时 11:00-13:00   未时 13:00-15:00   申时 15:00-17:00
    酉时 17:00-19:00   戌时 19:00-21:00   亥时 21:00-23:00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【显示格式】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  各项用 "  |  " 分隔，例如：
    时间 15:30  |  真太阳时 15:12  |  农历 乙巳年三月十五  |  四柱 乙巳 庚辰 壬寅 丙午

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【依赖】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  - lunardate（外部库）: 农历日期换算
  - src/algorithms/bazi.py: 八字四柱计算 + 真太阳时校正
  - src/settings/config_manager.py: 读取真太阳时设置
"""
from datetime import datetime
from PySide6.QtWidgets import QLabel, QStatusBar, QApplication
from PySide6.QtCore import QTimer, Qt

from lunardate import LunarDate

from ..algorithms.bazi import calculate_bazi, true_solar_time
from ..algorithms.xiaoliuren import calculate_now as xiaoliuren_now
from ..settings.config_manager import config_manager

# ── 状态栏外观（跟随系统深色/浅色模式）────────────
# Qt 6.5+ colorScheme() API，macOS 和 Windows 都兼容

def _statusbar_colors():
    """
    根据系统深色/浅色模式返回状态栏配色

    参数:
        （无参数，自动检测系统外观）

    返回:
        tuple[str, str]: (背景色, 文字色)
            - 深色模式: ("#2d2d30", "#f0f0f0") — 深灰底 + 白字
            - 浅色模式: ("#e8e8e8", "#1d1d1f") — 浅灰底 + 黑字

    兼容性:
        Qt 6.5+ 在 macOS 和 Windows 上均支持 colorScheme()。
        旧版本或检测失败时默认使用深色模式。

    用法:
        >>> bg, text = _statusbar_colors()
        >>> self._bar.setStyleSheet(f"QStatusBar {{ background-color: {bg}; }}")
    """
    try:
        app = QApplication.instance()
        if app and hasattr(app, "styleHints"):
            scheme = app.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Light:
                return ("#e8e8e8", "#1d1d1f")  # 浅色模式
    except Exception:
        pass
    return ("#2d2d30", "#f0f0f0")  # 默认深色


# ── 时辰边界计算 ─────────────────────────────────────

# 时辰对应的小时起点（按 24 小时制）
# 子(23), 丑(1), 寅(3), 卯(5), 辰(7), 巳(9),
# 午(11), 未(13), 申(15), 酉(17), 戌(19), 亥(21)
_SHICHEN_HOURS = [23, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21]


def _seconds_to_next_shichen(now: datetime) -> float:
    """
    计算距离下一个时辰交界还有多少秒

    参数:
        now (datetime): 当前时间

    返回:
        float: 距离下一个时辰边界的秒数，范围 0 ~ 7200（最大 2 小时）
               例如：现在是 15:25:30，下个时辰边界是 17:00:00
               返回 = (17*60 - 15*60 - 25)*60 - 30 = 5670 秒

    算法:
        1. 将 12 个时辰起点的小时转为分钟数（0-1439 范围内）
        2. 排序后找到第一个大于当前分钟数的边界
        3. 计算剩余秒数 = (边界分钟 - 当前分钟) × 60 - 当前秒

    边界情况:
        - 23:00 之后：下一个边界是明天的 01:00（子时结束→丑时开始）
          通过 +1440（一天的分钟数）来处理跨天

    用法:
        >>> from datetime import datetime
        >>> now = datetime(2026, 6, 7, 15, 25, 30)  # 15:25:30
        >>> _seconds_to_next_shichen(now)
        5670.0  # 约 94.5 分钟后到 17:00（酉时开始）
    """
    current_minutes = now.hour * 60 + now.minute
    # 所有时辰起点转为分钟数
    boundaries = [(h * 60) for h in _SHICHEN_HOURS]
    boundaries.sort()
    # 找下一个比当前分钟数大的边界
    for b in boundaries:
        if b > current_minutes:
            return (b - current_minutes) * 60 - now.second
    # 过了 23 点之后，下一个是明天的 1 点（子时→丑时）
    return (boundaries[1] + 1440 - current_minutes) * 60 - now.second


# ── 农历格式化 ────────────────────────────────────────

_TG = list("甲乙丙丁戊己庚辛壬癸")  # 天干（10 个）
_DZ = list("子丑寅卯辰巳午未申酉戌亥")  # 地支（12 个）
_LM = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]  # 农历月份名
_LD = ["初一","初二","初三","初四","初五","初六","初七","初八","初九","初十",
       "十一","十二","十三","十四","十五","十六","十七","十八","十九","二十",
       "廿一","廿二","廿三","廿四","廿五","廿六","廿七","廿八","廿九","三十"]  # 农历日期名


def _lunar_str(lunar: LunarDate) -> str:
    """
    将 LunarDate 对象格式化为中文农历字符串

    参数:
        lunar (LunarDate): lunardate 库返回的农历日期对象，包含 year/month/day 属性

    返回:
        str: 格式化的农历日期字符串，如 "乙巳年三月十五"

    年份计算:
        天干 = (年份 - 4) % 10，地支 = (年份 - 4) % 12
        例如：2025 年 → (2025-4)%10=1 → 乙, (2025-4)%12=5 → 巳 → "乙巳"

    月份/日期:
        月份：1→正月, 2→二月, ..., 11→冬月, 12→腊月
        日期：1→初一, 2→初二, ..., 10→初十, ..., 30→三十

    用法:
        >>> from lunardate import LunarDate
        >>> lunar = LunarDate.fromSolarDate(2025, 4, 14)  # 2025年4月14日
        >>> _lunar_str(lunar)
        '乙巳年三月十七'
    """
    yr = f"{_TG[(lunar.year - 4) % 10]}{_DZ[(lunar.year - 4) % 12]}"
    mo = _LM[lunar.month - 1] if 1 <= lunar.month <= 12 else str(lunar.month)
    dy = _LD[lunar.day - 1] if 1 <= lunar.day <= 30 else str(lunar.day)
    return f"{yr}年{mo}月{dy}"


# ── 主类 ─────────────────────────────────────────────

class StatusBarManager:
    """
    主窗口底部状态栏的实时信息管理器

    参数:
        status_bar (QStatusBar): 主窗口的状态栏对象（QStatusBar 实例）

    生命周期:
        - main_window.py 构造时创建: StatusBarManager(status_bar)
        - 内部 QTimer 定时刷新，根据距时辰交界的远近自动切换快/慢速率
        - appearance_manager 应用外观时主动调用 _refresh() 即时更新文字颜色

    做的事:
        1. 创建一个 QLabel 作为状态栏的永久 Widget
        2. 启动 QTimer 定时刷新显示内容
        3. 每次刷新时读取时间/太阳时/农历/四柱并格式化显示

    用法:
        # 在 main_window.py 中：
        from src.utils.statusbar_manager import StatusBarManager
        self._statusbar_mgr = StatusBarManager(self.statusBar())
    """

    def __init__(self, status_bar: QStatusBar):
        """
        构造 StatusBarManager 实例

        参数:
            status_bar (QStatusBar): 主窗口的状态栏，通常是 main_window.statusBar()

        做的事:
            1. 保存状态栏引用
            2. 创建 QLabel（显示文字用），添加为状态栏的永久 Widget
            3. 创建 QTimer 并连接 timeout → _refresh
            4. 初始以慢速（30 秒）启动
            5. 立即执行一次 _refresh() 显示初始信息
        """
        self._bar = status_bar

        # 根据系统深色/浅色模式自动选择配色
        bg, text = _statusbar_colors()
        self._bar.setStyleSheet(
            f"QStatusBar {{ background-color: {bg}; }}"
        )

        # 左侧永久状态标签（"就绪" / "定位中..." / "AI 等待回答..."）
        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet(f"font-size: 13px; color: {text}; padding: 0 12px;")
        self._bar.addWidget(self._status_label)

        # QLabel 作为永久 Widget 添加到状态栏右侧（时间/农历/四柱）
        self._label = QLabel()
        self._label.setStyleSheet(f"font-size: 14px; color: {text};")
        self._bar.addPermanentWidget(self._label)

        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh)
        self._start_slow()  # 初始慢速（30 秒），首次刷新后会根据时辰交界调整
        self._refresh()

    # ── 动态速率 ──────────────────────────────────────

    def _start_fast(self):
        """
        （内部方法）切换到每秒刷新模式

        调用时机：距离下一个时辰交界 ≤ 2 分钟时
        频率: 1000ms（每秒 1 次）
        用途: 确保时辰切换时状态栏更新准时（误差不超过 1 秒）
        """
        self._timer.start(1000)

    def _start_slow(self):
        """
        （内部方法）切换到每 30 秒刷新模式

        调用时机：距离下一个时辰交界 > 2 分钟时（日常模式）
        频率: 30000ms（每 30 秒 1 次）
        用途: 平时不需要那么频繁更新，降低 CPU 占用
        """
        self._timer.start(30000)

    def _pick_rate(self, now: datetime):
        """
        （内部方法）根据距离下一个时辰交界的时间选择刷新速率

        参数:
            now (datetime): 当前时间

        返回:
            None

        做的事:
            1. 计算距下一个时辰交界还有多少秒
            2. 如果 ≤ 120 秒 → 切换到每秒刷新（快模式）
            3. 如果 > 120 秒 → 切换到每 30 秒刷新（慢模式）
            4. 只有速率真正变化时才切换（避免重复设置 timer）

        用法:
            # 在 _refresh() 内部调用
            self._pick_rate(datetime.now())
        """
        secs = _seconds_to_next_shichen(now)
        if secs <= 120:  # 2 分钟内 → 快模式
            if self._timer.interval() != 1000:
                print(f"[状态栏] 距时辰交界 {int(secs)}s → 切换每秒刷新")
                self._start_fast()
        else:
            if self._timer.interval() != 30000:
                print(f"[状态栏] 距时辰交界 {int(secs)}s → 恢复30秒刷新")
                self._start_slow()

    # ── 刷新 ──────────────────────────────────────────

    def _refresh(self):
        """
        核心刷新方法 — 读取当前时间/太阳时/农历/四柱，更新状态栏显示

        参数:
            （无参数，从系统时间和 usrCfg 配置中读取所需数据）

        返回:
            None（直接更新状态栏 QLabel 的文本和样式）

        显示格式（四项用 "  |  " 分隔）:
            时间 15:30  |  真太阳时 15:12  |  农历 乙巳年三月十五  |  四柱 乙巳 庚辰 壬寅 丙午

        做的事（按顺序）:
            1. 获取当前时间
            2. 根据时辰交界远近调整刷新速率
            3. 读取真太阳时配置（是否启用、是否显示、是否用于八字）
            4. 格式化各项信息
            5. 更新 QLabel 显示文字（固定深灰底 + 白字，不随外观联动）

        异常处理:
            农历换算或八字计算失败时不崩溃，仅跳过对应项的显示。
            例如：某个 lunardate 版本不支持某年日期 → 跳过农历那一项。
        """
        now = datetime.now()

        cfg = config_manager.get("solar_time") or {}
        solar_enabled = cfg.get("enabled", False)
        show_solar = cfg.get("show_in_statusbar", True)
        use_bazi_solar = cfg.get("use_in_bazi", True)
        lon = cfg.get("longitude", 120.0)

        # 时辰交界判断：
        #   "排八字中使用" 勾选 → 用真太阳时判断时辰边界（乌鲁木齐午时比北京晚约 2 小时）
        #   否则 → 用北京时间判断
        #   与"状态栏中显示"无关 —— 快慢刷新只取决于时辰确认方式
        use_solar_for_rate = solar_enabled and use_bazi_solar
        ref_time = true_solar_time(now, lon) if use_solar_for_rate else now
        self._pick_rate(ref_time)

        parts = []

        # 1) 时间（精简格式）
        #    启用真太阳时 → "时间(真) 14:30(14:12)"  北京时间(真太阳时)
        #    否则         → "时间 14:30"
        time_str = now.strftime("%H:%M")
        if solar_enabled and show_solar:
            solar_now = true_solar_time(now, lon)
            solar_str = solar_now.strftime("%H:%M")
            parts.append(f"时间(真) {time_str} ({solar_str})")
        else:
            parts.append(f"时间 {time_str}")

        # 2) 农历（通过 lunardate 库换算）
        try:
            lunar = LunarDate.fromSolarDate(now.year, now.month, now.day)
            parts.append(_lunar_str(lunar))
        except Exception:
            pass  # 换算失败静默跳过，不影响其他项的显示

        # 3) 四柱（根据"排八字使用真太阳时"开关决定是否用太阳时校正）
        bazi_solar = solar_enabled and use_bazi_solar
        try:
            bazi = calculate_bazi(now, use_solar_time=bazi_solar, longitude=lon)
            p = f"{bazi['year']} {bazi['month']} {bazi['day']} {bazi['hour']}"
            tag = "四柱(真)" if bazi_solar else "四柱(平)"
            parts.append(f"{tag} {p}")
        except Exception:
            pass  # 计算失败静默跳过

        # 4) 小六壬（仅显示掌诀名称，不显示断语）
        try:
            xlr = xiaoliuren_now()
            fortune = "吉" if xlr["fortune"] else "凶"
            parts.append(f"{xlr['position']}({fortune})")
        except Exception:
            pass  # 计算失败静默跳过

        self._label.setText("  |  ".join(parts))

    # ── 状态消息（供外部调用）──────────────────────────

    def show_status(self, text: str):
        """
        更新状态栏左侧的状态文字

        参数:
            text (str): 要显示的状态文字，如 "定位中..."、"AI 等待回答..."

        返回:
            None

        用法:
            >>> # 从任意面板中调用（通过 _get_statusbar_mgr 辅助函数）
            >>> mgr = _get_statusbar_mgr(self)
            >>> mgr.show_status("定位中...")
        """
        self._status_label.setText(text)

    def reset_status(self):
        """
        将状态栏左侧文字恢复为默认的"就绪"

        参数:
            （无参数）

        返回:
            None

        用法:
            >>> mgr = _get_statusbar_mgr(self)
            >>> mgr.reset_status()
        """
        self._status_label.setText("就绪")


def _get_statusbar_mgr(widget):
    """
    从任意 Widget 向上查找主窗口的 StatusBarManager 实例

    参数:
        widget (QWidget): 任意在窗口层级中的 Widget

    返回:
        StatusBarManager 或 None: 如果找到主窗口且其有 _statusbar_mgr 属性则返回，否则返回 None

    原理:
        通过 widget.window() 获取顶层窗口（即 MainWindow），
        然后读取其 _statusbar_mgr 属性（main_window.py 中设置）。

    用法:
        >>> from src.utils.statusbar_manager import _get_statusbar_mgr
        >>> mgr = _get_statusbar_mgr(self)
        >>> if mgr:
        >>>     mgr.show_status("定位中...")
    """
    top = widget.window()
    return getattr(top, "_statusbar_mgr", None)
