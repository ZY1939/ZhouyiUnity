"""
算卦公共模块 — LineMarker / 干支历法 / 时间选择 / 卦辞解读

═══════════════════════════════════════════════════════════════
被 meihua_panel / liuyao_panel / suangua_panel 共享使用
═══════════════════════════════════════════════════════════════
"""
import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QDialog, QComboBox, QFormLayout,
                                QSpinBox, QCheckBox, QStackedWidget, QButtonGroup)
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QColor, QPen

from ..hexagram_drawer import _app_font
from ..dot_button import DotButton


# ═══════════════════════════════════════════════════════════════
#  颜色工具
# ═══════════════════════════════════════════════════════════════

def is_light_color(hex_color: str) -> bool:
    """判断 hex 颜色是否为亮色（亮度 > 128）"""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) < 6:
        return False
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return luminance > 128


# ═══════════════════════════════════════════════════════════════
#  _LineMarker — 卦图侧边文字/图标标注
# ═══════════════════════════════════════════════════════════════

class _LineMarker(QWidget):
    """
    在卦图侧边绘制文字标注，与特定爻行垂直居中对齐

    用于显示 体/用（本卦左侧）、八卦名（互卦左侧）、o/x（本卦右侧）等标注。
    高度与关联的 HexagramDrawer 一致，通过 markers 列表指定每行标注内容。

    对齐模式：
      _align_right=True  → 文字靠右对齐（左侧标注：体/用、八卦名）
      _align_right=False → 文字靠左对齐（右侧标注：o/x）

    Badge 模式（set_badge_mode(True)）：
      o/x 符号绘制为彩色圆角矩形 + 白色文字，更显眼。
    """

    def __init__(self, align_right: bool = False, parent=None):
        super().__init__(parent)
        self._markers: list[tuple[int, str, QColor]] = []
        self._name_area_h = 0
        self._line_h = 0
        self._offset_y = 0
        self._font_size = 16
        self._text_color = "#1d1d1f"
        self._align_right = align_right  # True=文字靠右(左侧标注), False=文字靠左(右侧标注)
        self._fs_offset = 0              # 字体偏移(相对font_size)
        self._badge_mode = False         # badge模式（彩色圆角矩形+白字）
        self._badge_padding_ox = 5       # 轮廓比文字大的内边距（px）

    def configure(self, name_area_h: int, line_h: int, offset_y: int = 0, font_size: int = 16):
        """匹配关联 drawer 的几何参数，确保标注与爻行对齐"""
        self._name_area_h = name_area_h
        self._line_h = line_h
        self._offset_y = offset_y
        self._font_size = font_size
        self.setFixedHeight(name_area_h + 6 * line_h)

    def set_fs_offset(self, offset: int):
        """设置标注字号偏移（相对全局font_size）"""
        self._fs_offset = offset
        self.update()

    def set_badge_mode(self, enabled: bool):
        """启用/禁用 badge 模式（o/x 符号显示为彩色圆角矩形+白字）"""
        self._badge_mode = enabled
        self.update()

    def set_badge_padding_ox(self, px: int):
        """设置 badge 轮廓比文字大的内边距（px）"""
        self._badge_padding_ox = px
        self.update()

    def set_markers(self, markers: list):
        """
        设置标注内容

        Args:
            markers: [(line_idx, text, color_hex), ...]  或
                     [(line_idx, text, color_hex, outlined), ...]  或
                     [(line_idx, text, color_hex, outlined, text_override_hex), ...]
                     line_idx: 0=初爻..5=上爻
                     outlined: True=透明填充+彩色边框, False/省略=填充badge(若badge_mode)
                     text_override: 覆盖badge模式下的白色文字（用于白虎等特殊颜色）
        """
        result = []
        for m in markers:
            ln, txt, clr = m[0], m[1], m[2]
            outlined = m[3] if len(m) > 3 else False
            text_override = m[4] if len(m) > 4 else None
            result.append((ln, txt, QColor(clr), outlined, text_override))
        self._markers = result
        self.update()

    def set_text_color(self, text_color: str):
        self._text_color = text_color
        self.update()

    def set_font_size(self, fs: int):
        self._font_size = fs
        self.update()

    def paintEvent(self, event):
        if not self._markers:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = _app_font()
        font.setPointSize(self._font_size + self._fs_offset)
        font.setBold(True)
        p.setFont(font)
        fm = QFontMetrics(font)

        w = self.width()
        for line_idx, text, color, outlined, text_override in self._markers:
            center_y = self._offset_y + self._name_area_h + (5 - line_idx) * self._line_h + self._line_h // 2

            if outlined:
                # ── outlined badge 模式：透明填充 + 彩色边框 + 正常颜色文字 ──
                pad = self._badge_padding_ox
                text_w = fm.horizontalAdvance(text)
                badge_w = text_w + 2 * pad + 4  # +4 for border (2px each side)
                badge_h = fm.height() + 2 * pad + 4
                badge_top = int(center_y - badge_h // 2)
                if self._align_right:
                    badge_x = w - badge_w
                else:
                    badge_x = 0
                # 透明填充 + 彩色边框
                p.setPen(QPen(color, 2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(badge_x, badge_top, badge_w, badge_h, 6, 6)
                # 文字：优先 text_override，否则反色（亮底→白字，暗底→黑字）
                if text_override:
                    text_c = text_override
                else:
                    text_c = "#ffffff" if not is_light_color(self._text_color) else "#1d1d1f"
                p.setPen(QColor(text_c))
                text_x = badge_x + pad + 2
                baseline_y = badge_top + (badge_h + fm.ascent() - fm.descent()) // 2
                p.drawText(int(text_x), int(baseline_y), text)
            elif self._badge_mode:
                # ── badge 模式 ──
                #   ○ = 纯红圆（QPainter 画，不依赖字体）
                #   × = 蓝圆角方 + 白色 X 线条（QPainter 画，不依赖字体）
                #   体/用/八卦名 = 圆角矩形 + 白色文字
                pad = self._badge_padding_ox
                is_circle = (text == "○")
                is_cross = (text == "×")
                if is_circle or is_cross:
                    side = fm.height() + 2 * pad
                else:
                    text_w = fm.horizontalAdvance(text)
                    side = max(fm.height() + 2 * pad, text_w + 2 * pad)
                badge_h = side
                badge_w = side
                # 浮点 badge 中心坐标 — 保证 ○/× 精确居中于 center_y
                badge_top = center_y - side / 2.0
                if self._align_right:
                    badge_x = float(w - badge_w)
                else:
                    badge_x = 0.0
                cx = badge_x + side / 2.0  # badge 几何中心 x
                cy = badge_top + side / 2.0  # badge 几何中心 y
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(color)
                if is_circle:
                    p.drawEllipse(QRectF(badge_x, badge_top, badge_w, badge_h))
                    inner_margin = side * 0.22
                    ring_w = max(2.0, side * 0.12)
                    p.setPen(QPen(QColor("#ffffff"), ring_w, Qt.PenStyle.SolidLine))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawEllipse(QRectF(
                        cx - side / 2.0 + inner_margin, cy - side / 2.0 + inner_margin,
                        side - 2 * inner_margin, side - 2 * inner_margin))
                elif is_cross:
                    p.drawRoundedRect(QRectF(badge_x, badge_top, badge_w, badge_h), 6, 6)
                    line_w = max(2.0, side * 0.15)
                    pen = QPen(QColor("#ffffff"), line_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                    p.setPen(pen)
                    # 以 badge 几何中心 (cx, cy) 为基准画交叉线 — 确保 × 精确居中
                    inset = side * 0.28
                    half = side / 2.0 - inset
                    p.drawLine(QPointF(cx - half, cy - half), QPointF(cx + half, cy + half))
                    p.drawLine(QPointF(cx + half, cy - half), QPointF(cx - half, cy + half))
                else:
                    p.drawRoundedRect(badge_x, badge_top, badge_w, badge_h, 6, 6)
                    text_c = text_override if text_override else "#ffffff"
                    p.setPen(QColor(text_c))
                    text_w = fm.horizontalAdvance(text)
                    text_x = badge_x + (badge_w - text_w) // 2
                    baseline_y = badge_top + (badge_h + fm.ascent() - fm.descent()) // 2
                    p.drawText(int(text_x), int(baseline_y), text)
                import os
                if os.environ.get("ZY_DEBUG_BADGE"):
                    print(f"[DEBUG badge] text={text} pad={pad} widget_w={w} "
                          f"badge(x={badge_x},top={badge_top},w={badge_w:.0f},h={badge_h:.0f}) "
                          f"center_y={center_y} "
                          f"fm(ascent={fm.ascent()},descent={fm.descent()},h={fm.height()})", flush=True)
            else:
                # ── 普通文字模式 ──
                text_h = fm.height()
                align = Qt.AlignmentFlag.AlignRight if self._align_right else Qt.AlignmentFlag.AlignLeft
                p.setPen(color)
                p.drawText(0, int(center_y - text_h // 2), w, text_h,
                           align | Qt.AlignmentFlag.AlignVCenter, text)
        p.end()


# ═══════════════════════════════════════════════════════════════
#  爻名计算
# ═══════════════════════════════════════════════════════════════

def line_name(binary: str, pos: int) -> str:
    """将爻位(1-6)转为爻名，如 初九、六三；越界返回空串"""
    if pos < 1 or pos > 6 or len(binary) < 6:
        return ""
    POS_NAMES = ["初", "二", "三", "四", "五", "上"]
    yao = "九" if binary[pos - 1] == "1" else "六"
    if pos == 1 or pos == 6:
        return f"{POS_NAMES[pos - 1]}{yao}"
    else:
        return f"{yao}{POS_NAMES[pos - 1]}"


# ═══════════════════════════════════════════════════════════════
#  卦辞/爻辞 解读 HTML 构建
# ═══════════════════════════════════════════════════════════════

# 方块颜色
BLUE_BG = "rgb(59, 86, 189)"
ORANGE_BG = "rgb(211, 107, 0)"


def _find_line_by_attribute(lines_data: list[dict], attr_name: str) -> dict | None:
    """在 lines 数组中按 attribute 查找爻辞条目"""
    for ln in lines_data:
        if ln.get("attribute", "").startswith(attr_name):
            return ln
    return None


def _build_yaoci_html(font_size: int, attr: str, scripture: str, xiang: str) -> str:
    """构建爻辞 HTML（蓝色方块）"""
    parts = [
        f'<span style="font-size:{font_size}px; color:#ffffff;">'
        f'<b>{attr}</b>&nbsp;&nbsp;{scripture}'
        f'</span>',
    ]
    if xiang:
        parts.append(
            f'<br><span style="font-size:{font_size - 1}px; color:#d0d5f0;">'
            f'象曰&nbsp;&nbsp;{xiang}'
            f'</span>'
        )
    return ''.join(parts)


def _build_guaci_html(font_size: int, scripture: str, tuan: str) -> str:
    """构建卦辞 HTML（橙色方块）"""
    parts = [
        f'<span style="font-size:{font_size}px; color:#ffffff;">'
        f'<b>卦辞</b>&nbsp;&nbsp;{scripture}'
        f'</span>',
    ]
    if tuan:
        parts.append(
            f'<br><span style="font-size:{font_size - 1}px; color:#ffe0c0;">'
            f'彖曰&nbsp;&nbsp;{tuan}'
            f'</span>'
        )
    return ''.join(parts)


def build_interpretation(ben_data: dict, changing_lines: list[int], font_size: int) -> tuple[str, str] | None:
    """
    根据动爻数量构建卦辞/爻辞解读 HTML

    1 动爻 → 爻辞+象曰（蓝色）
    0 动爻 → 卦辞+彖曰（橙色）
    >1 动爻 → 调用 get_judgment_line (南师多动爻断法) 选爻后展示爻辞/卦辞

    Args:
        ben_data: 本卦数据库 dict
        changing_lines: 动爻列表 (1=初爻..6=上爻)
        font_size: 基准字号

    Returns:
        (html, bg_color) 或 None（无法构建时）
    """
    n = len(changing_lines)
    binary = ben_data.get("binary", "111111")
    lines_data = ben_data.get("lines", [])

    # ── 统一通过南师断法获取判断依据 ──
    from ...algorithms.mutiDongyaoSel import get_judgment_line
    try:
        result, reason = get_judgment_line(binary, changing_lines)
    except ValueError:
        return None

    if result == 0:
        # ── 静卦 → 卦辞 + 彖曰（橙色）──
        scripture = ben_data.get("scripture", "")
        tuan = ben_data.get("tuan", "")
        if not scripture and not tuan:
            return None
        return _build_guaci_html(font_size, scripture, tuan), ORANGE_BG

    elif 1 <= result <= 6:
        # ── 具体爻辞 + 象曰（蓝色）──
        yao_name = line_name(binary, result)
        if not yao_name:
            return None
        line_info = _find_line_by_attribute(lines_data, yao_name)
        if not line_info:
            return None
        html = _build_yaoci_html(
            font_size,
            line_info.get("attribute", "?"),
            line_info.get("scripture", ""),
            line_info.get("xiang", ""),
        )
        return html, BLUE_BG

    elif result == 7:
        # 用九（乾卦六爻皆动）
        line_info = _find_line_by_attribute(lines_data, "用九")
        if line_info:
            html = _build_yaoci_html(
                font_size, "用九",
                line_info.get("scripture", ""),
                line_info.get("xiang", ""),
            )
        else:
            html = _build_guaci_html(
                font_size,
                ben_data.get("scripture", ""),
                ben_data.get("tuan", ""),
            )
        return html, BLUE_BG

    elif result == 8:
        # 用六（坤卦六爻皆动）
        line_info = _find_line_by_attribute(lines_data, "用六")
        if line_info:
            html = _build_yaoci_html(
                font_size, "用六",
                line_info.get("scripture", ""),
                line_info.get("xiang", ""),
            )
        else:
            html = _build_guaci_html(
                font_size,
                ben_data.get("scripture", ""),
                ben_data.get("tuan", ""),
            )
        return html, BLUE_BG

    elif result == 9:
        # 变卦彖辞 — 无变卦数据，展示本卦彖辞
        html = _build_guaci_html(
            font_size,
            ben_data.get("scripture", ""),
            ben_data.get("tuan", ""),
        )
        return html, ORANGE_BG

    return None


# ═══════════════════════════════════════════════════════════════
#  干支历法工具
# ═══════════════════════════════════════════════════════════════

_TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
_DIZHI_LIST = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 参考日期: 2024-01-01 = 甲子日 (日干支索引 0)
_REF_DATE = datetime.date(2024, 1, 1)

# 年干 → 正月(寅月)天干起始索引
_YEAR_GAN_TO_MONTH_START: dict[str, int] = {
    "甲": 2, "乙": 4, "丙": 6, "丁": 8, "戊": 0,
    "己": 2, "庚": 4, "辛": 6, "壬": 8, "癸": 0,
}

# 日干 → 子时天干起始索引
_DAY_GAN_TO_HOUR_START: dict[str, int] = {
    "甲": 0, "乙": 2, "丙": 4, "丁": 6, "戊": 8,
    "己": 0, "庚": 2, "辛": 4, "壬": 6, "癸": 8,
}

# 阴阳干支
_YANG_GAN = ["甲", "丙", "戊", "庚", "壬"]
_YIN_GAN = ["乙", "丁", "己", "辛", "癸"]
_YANG_ZHI = ["子", "寅", "辰", "午", "申", "戌"]
_YIN_ZHI = ["丑", "卯", "巳", "未", "酉", "亥"]


def compute_day_ganzhi(d: datetime.date) -> tuple[str, str]:
    """
    计算指定日期的日干支

    Returns:
        (day_gan, day_ganzhi) 如 ("甲", "甲子")
    """
    delta = (d - _REF_DATE).days
    total_idx = delta % 60
    gan_idx = total_idx % 10
    zhi_idx = total_idx % 12
    return _TIANGAN[gan_idx], _TIANGAN[gan_idx] + _DIZHI_LIST[zhi_idx]


def compute_current_ganzhi() -> dict:
    """
    根据当前系统时间计算年/月/日/时 干支

    Returns:
        {"year_ganzhi": "甲辰", "month_ganzhi": "丙寅",
         "day_ganzhi": "甲子", "day_gan": "甲",
         "hour_ganzhi": "甲子"}
    """
    now = datetime.datetime.now()

    year_idx = (now.year - 4) % 60
    year_gan = _TIANGAN[year_idx % 10]
    year_ganzhi = year_gan + _DIZHI_LIST[year_idx % 12]

    month_zhi_idx = now.month % 12
    month_zhi = _DIZHI_LIST[month_zhi_idx]
    month_gan_start = _YEAR_GAN_TO_MONTH_START[year_gan]
    if now.month >= 2:
        month_offset = now.month - 2
    else:
        month_offset = now.month + 10
    month_gan = _TIANGAN[(month_gan_start + month_offset) % 10]
    month_ganzhi = month_gan + month_zhi

    day_gan, day_ganzhi = compute_day_ganzhi(now.date())

    hour_zhi_idx = ((now.hour + 1) // 2) % 12
    hour_zhi = _DIZHI_LIST[hour_zhi_idx]
    hour_gan_start = _DAY_GAN_TO_HOUR_START[day_gan]
    hour_gan = _TIANGAN[(hour_gan_start + hour_zhi_idx) % 10]
    hour_ganzhi = hour_gan + hour_zhi

    return {
        "year_ganzhi": year_ganzhi,
        "month_ganzhi": month_ganzhi,
        "day_ganzhi": day_ganzhi,
        "day_gan": day_gan,
        "hour_ganzhi": hour_ganzhi,
    }


def find_ganzhi_index(gz: str) -> int:
    """在60甲子中找到干支的索引（甲子=0）"""
    gan = gz[0]
    zhi = gz[1]
    g_idx = _TIANGAN.index(gan)
    z_idx = _DIZHI_LIST.index(zhi)
    for i in range(60):
        if i % 10 == g_idx and i % 12 == z_idx:
            return i
    return 0


def is_yang_gan(gan: str) -> bool:
    return _TIANGAN.index(gan) % 2 == 0


def compatible_zhis(gan: str) -> list[str]:
    """返回与指定天干兼容的地支列表（阳干配阳支，阴干配阴支）"""
    return _YANG_ZHI if is_yang_gan(gan) else _YIN_ZHI


def ganzhi_to_approx_year(ganzhi: str, ref_year: int | None = None) -> int:
    """
    干支年份 → 近似公历年份

    找到 ref_year 附近匹配该干支的年份（60年一周期的最近值）。
    """
    if ref_year is None:
        ref_year = datetime.datetime.now().year
    target_idx = find_ganzhi_index(ganzhi)
    base = target_idx + 4
    k = round((ref_year - base) / 60)
    return base + 60 * k


def gregorian_to_ganzhi_parts(dt: datetime.datetime) -> dict:
    """
    公历时间 → 天干地支分量（年/月/日/时 各分 天干+地支）

    Returns:
        {"year_gan": "甲", "year_zhi": "辰",
         "month_gan": "丙", "month_zhi": "寅",
         "day_gan": "甲", "day_zhi": "子",
         "hour_gan": "甲", "hour_zhi": "子"}
    """
    year_idx = (dt.year - 4) % 60
    year_gan = _TIANGAN[year_idx % 10]
    year_zhi = _DIZHI_LIST[year_idx % 12]

    month_zhi_idx = dt.month % 12
    month_zhi = _DIZHI_LIST[month_zhi_idx]
    month_gan_start = _YEAR_GAN_TO_MONTH_START[year_gan]
    if dt.month >= 2:
        month_offset = dt.month - 2
    else:
        month_offset = dt.month + 10
    month_gan = _TIANGAN[(month_gan_start + month_offset) % 10]

    day_gan, day_ganzhi = compute_day_ganzhi(dt.date())

    hour_zhi_idx = ((dt.hour + 1) // 2) % 12
    hour_zhi = _DIZHI_LIST[hour_zhi_idx]
    hour_gan_start = _DAY_GAN_TO_HOUR_START[day_gan]
    hour_gan = _TIANGAN[(hour_gan_start + hour_zhi_idx) % 10]

    return {
        "year_gan": year_gan, "year_zhi": year_zhi,
        "month_gan": month_gan, "month_zhi": month_zhi,
        "day_gan": day_gan, "day_zhi": day_ganzhi[1],
        "hour_gan": hour_gan, "hour_zhi": hour_zhi,
    }


# ═══════════════════════════════════════════════════════════════
#  _TimePickerDialog — 双模式时间选择弹窗
# ═══════════════════════════════════════════════════════════════

class _TimePickerDialog(QDialog):
    """
    时间选择器 — 天干地支 / 阳历 双模式

    天干地支模式：天干(10选1) + 地支(根据天干阴阳过滤6选1) 分开选择
    阳历模式：年/月/日 QSpinBox，时/分 QSpinBox（需启用时辰）
    """

    MODE_GANZHI = 0
    MODE_GREGORIAN = 1

    def __init__(self, current_ganzhi: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("修改时间")
        self.setMinimumWidth(340)
        self._current = current_ganzhi
        self._result = None
        self._active_mode = self.MODE_GANZHI

        self._gregorian_dt = self._init_gregorian_from_ganzhi(current_ganzhi)

        self._init_ui()
        self._init_values()

    def _init_gregorian_from_ganzhi(self, ganzhi: dict) -> datetime.datetime:
        """从干支 dict 推算近似的公历 datetime"""
        now = datetime.datetime.now()
        year = ganzhi_to_approx_year(ganzhi["year_ganzhi"], now.year)
        month_gz = ganzhi["month_ganzhi"]
        month_zhi = month_gz[1]
        month_zhi_idx = _DIZHI_LIST.index(month_zhi)
        month = month_zhi_idx if month_zhi_idx > 0 else 12
        day = min(now.day, 28)
        hour_gz = ganzhi["hour_ganzhi"]
        hour_zhi = hour_gz[1]
        hour_zhi_idx = _DIZHI_LIST.index(hour_zhi)
        hour = hour_zhi_idx * 2
        if hour == 0 and hour_zhi_idx == 0:
            hour = 0
        return datetime.datetime(year, month, day, hour, 0)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # ── 模式切换 ──
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)

        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)

        self._dot_ganzhi = DotButton()
        self._mode_group.addButton(self._dot_ganzhi, self.MODE_GANZHI)
        mode_row.addWidget(self._dot_ganzhi)

        lbl_ganzhi = QPushButton("天干地支")
        lbl_ganzhi.setFlat(True)
        lbl_ganzhi.setCursor(Qt.CursorShape.PointingHandCursor)
        lbl_ganzhi.setStyleSheet("color: #1d1d1f; background: transparent; border: none;")
        lbl_ganzhi.clicked.connect(self._dot_ganzhi.click)
        mode_row.addWidget(lbl_ganzhi)

        mode_row.addSpacing(8)

        self._dot_gregorian = DotButton()
        self._mode_group.addButton(self._dot_gregorian, self.MODE_GREGORIAN)
        mode_row.addWidget(self._dot_gregorian)

        lbl_greg = QPushButton("阳历")
        lbl_greg.setFlat(True)
        lbl_greg.setCursor(Qt.CursorShape.PointingHandCursor)
        lbl_greg.setStyleSheet("color: #1d1d1f; background: transparent; border: none;")
        lbl_greg.clicked.connect(self._dot_gregorian.click)
        mode_row.addWidget(lbl_greg)

        self._hour_cb = QCheckBox("启用时辰")
        self._hour_cb.setStyleSheet("color: #1d1d1f; background: transparent;")
        self._hour_cb.toggled.connect(self._on_hour_toggled)
        mode_row.addWidget(self._hour_cb)

        mode_row.addStretch()
        layout.addLayout(mode_row)

        self._mode_group.buttonClicked.connect(self._on_mode_changed)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_ganzhi_panel())
        self._stack.addWidget(self._build_gregorian_panel())
        layout.addWidget(self._stack)

        # ── 按钮行 ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._now_btn = QPushButton("设为现在")
        self._now_btn.clicked.connect(self._on_set_now)
        self._now_btn.setStyleSheet("""
            QPushButton {
                color: #007aff; background: transparent;
                border: 1px solid #007aff;
                border-radius: 5px; padding: 6px 14px;
            }
            QPushButton:hover { background: #e8f0fe; }
        """)
        btn_layout.addWidget(self._now_btn)

        btn_layout.addStretch()

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        ok_btn.setStyleSheet("""
            QPushButton {
                background: #007aff; color: #ffffff;
                border-radius: 5px; padding: 6px 20px;
                border: none;
            }
            QPushButton:hover { background: #0056cc; }
        """)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #e0e0e0; color: #1d1d1f;
                border-radius: 5px; padding: 6px 20px;
                border: none;
            }
            QPushButton:hover { background: #c0c0c0; }
        """)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    # ── 天干地支面板 ──

    def _build_ganzhi_panel(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(0, 6, 0, 0)
        form.setSpacing(8)

        self._gz_year_gan = self._make_gan_combo()
        self._gz_year_zhi = self._make_styled_combo([])
        self._gz_year_gan.currentTextChanged.connect(
            lambda g: self._filter_zhi_combo(g, self._gz_year_zhi))
        row = QHBoxLayout()
        row.setSpacing(4)
        row.addWidget(self._gz_year_gan)
        row.addWidget(self._gz_year_zhi)
        form.addRow("年:", row)

        self._gz_month_gan = self._make_gan_combo()
        self._gz_month_zhi = self._make_styled_combo([])
        self._gz_month_gan.currentTextChanged.connect(
            lambda g: self._filter_zhi_combo(g, self._gz_month_zhi))
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        row2.addWidget(self._gz_month_gan)
        row2.addWidget(self._gz_month_zhi)
        form.addRow("月:", row2)

        self._gz_day_gan = self._make_gan_combo()
        self._gz_day_zhi = self._make_styled_combo([])
        self._gz_day_gan.currentTextChanged.connect(
            lambda g: self._filter_zhi_combo(g, self._gz_day_zhi))
        row3 = QHBoxLayout()
        row3.setSpacing(4)
        row3.addWidget(self._gz_day_gan)
        row3.addWidget(self._gz_day_zhi)
        form.addRow("日:", row3)

        self._gz_hour_gan = self._make_gan_combo()
        self._gz_hour_zhi = self._make_styled_combo([])
        self._gz_hour_gan.currentTextChanged.connect(
            lambda g: self._filter_zhi_combo(g, self._gz_hour_zhi))
        self._gz_hour_row = QHBoxLayout()
        self._gz_hour_row.setSpacing(4)
        self._gz_hour_row.addWidget(self._gz_hour_gan)
        self._gz_hour_row.addWidget(self._gz_hour_zhi)
        self._gz_hour_label = QLabel("时:")
        self._gz_hour_label.setStyleSheet("color: #1d1d1f; background: transparent;")
        form.addRow(self._gz_hour_label, self._gz_hour_row)

        return w

    _COMBO_STYLE = """
        QComboBox QAbstractItemView::item:selected {
            background-color: #007aff;
            color: #ffffff;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: #e8f0fe;
        }
    """

    def _make_gan_combo(self) -> QComboBox:
        cb = QComboBox()
        cb.addItems(_TIANGAN)
        cb.setStyleSheet(self._COMBO_STYLE)
        return cb

    def _make_styled_combo(self, items: list[str]) -> QComboBox:
        cb = QComboBox()
        cb.addItems(items)
        cb.setStyleSheet(self._COMBO_STYLE)
        return cb

    def _filter_zhi_combo(self, gan: str, zhi_cb: QComboBox):
        zhi_cb.clear()
        zhi_cb.addItems(compatible_zhis(gan))

    # ── 阳历面板 ──

    def _build_gregorian_panel(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(0, 6, 0, 0)
        form.setSpacing(8)

        self._greg_year = QSpinBox()
        self._greg_year.setRange(1900, 2100)
        self._greg_year.setFixedWidth(80)
        self._greg_month = QSpinBox()
        self._greg_month.setRange(1, 12)
        self._greg_month.setFixedWidth(60)
        self._greg_day = QSpinBox()
        self._greg_day.setRange(1, 31)
        self._greg_day.setFixedWidth(60)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("年"))
        row.addWidget(self._greg_year)
        row.addWidget(QLabel("月"))
        row.addWidget(self._greg_month)
        row.addWidget(QLabel("日"))
        row.addWidget(self._greg_day)
        row.addStretch()
        form.addRow(row)

        self._greg_hour = QSpinBox()
        self._greg_hour.setRange(0, 23)
        self._greg_hour.setFixedWidth(60)
        self._greg_minute = QSpinBox()
        self._greg_minute.setRange(0, 59)
        self._greg_minute.setFixedWidth(60)

        self._greg_hour_row = QHBoxLayout()
        self._greg_hour_row.setSpacing(8)
        self._greg_hour_row.addWidget(QLabel("时"))
        self._greg_hour_row.addWidget(self._greg_hour)
        self._greg_hour_row.addWidget(QLabel("分"))
        self._greg_hour_row.addWidget(self._greg_minute)
        self._greg_hour_row.addStretch()
        self._greg_hour_label = QLabel("时/分:")
        self._greg_hour_label.setStyleSheet("color: #1d1d1f; background: transparent;")
        form.addRow(self._greg_hour_label, self._greg_hour_row)

        return w

    # ── 初始化 ──

    def _init_values(self):
        parts = gregorian_to_ganzhi_parts(self._gregorian_dt)
        self._set_ganzhi_parts(parts)

        self._greg_year.setValue(self._gregorian_dt.year)
        self._greg_month.setValue(self._gregorian_dt.month)
        self._greg_day.setValue(self._gregorian_dt.day)
        self._greg_hour.setValue(self._gregorian_dt.hour)
        self._greg_minute.setValue(self._gregorian_dt.minute)

        self._dot_ganzhi.setChecked(True)
        self._stack.setCurrentIndex(self.MODE_GANZHI)

        self._hour_cb.setChecked(False)
        self._on_hour_toggled(False)

    def _set_ganzhi_parts(self, parts: dict):
        for prefix, key_gan, key_zhi in [
            ("_gz_year", "year_gan", "year_zhi"),
            ("_gz_month", "month_gan", "month_zhi"),
            ("_gz_day", "day_gan", "day_zhi"),
            ("_gz_hour", "hour_gan", "hour_zhi"),
        ]:
            gan_cb = getattr(self, f"{prefix}_gan")
            zhi_cb = getattr(self, f"{prefix}_zhi")
            gan = parts[key_gan]
            zhi = parts[key_zhi]
            gan_cb.setCurrentIndex(_TIANGAN.index(gan))
            self._filter_zhi_combo(gan, zhi_cb)
            zhi_cb.setCurrentText(zhi)

    # ── 模式切换 ──

    def _on_mode_changed(self, btn):
        idx = self._mode_group.id(btn)
        if idx == self._active_mode:
            return

        if self._active_mode == self.MODE_GANZHI:
            gz = self._collect_ganzhi()
            self._gregorian_dt = self._init_gregorian_from_ganzhi(gz)
            self._greg_year.setValue(self._gregorian_dt.year)
            self._greg_month.setValue(self._gregorian_dt.month)
            self._greg_day.setValue(self._gregorian_dt.day)
        else:
            self._gregorian_dt = self._collect_gregorian()
            parts = gregorian_to_ganzhi_parts(self._gregorian_dt)
            self._set_ganzhi_parts(parts)

        self._active_mode = idx
        self._stack.setCurrentIndex(idx)

    # ── 启用时辰 ──

    def _on_hour_toggled(self, checked: bool):
        for w in self._get_hour_widgets():
            w.setVisible(checked)

    def _get_hour_widgets(self) -> list:
        gz_widgets = ([self._gz_hour_label] +
                      [self._gz_hour_row.itemAt(i).widget()
                       for i in range(self._gz_hour_row.count())
                       if self._gz_hour_row.itemAt(i) and self._gz_hour_row.itemAt(i).widget()])
        greg_widgets = ([self._greg_hour_label] +
                        [self._greg_hour_row.itemAt(i).widget()
                         for i in range(self._greg_hour_row.count())
                         if self._greg_hour_row.itemAt(i) and self._greg_hour_row.itemAt(i).widget()])
        return gz_widgets + greg_widgets

    # ── 设为现在 ──

    def _on_set_now(self):
        now = datetime.datetime.now()
        self._gregorian_dt = now

        parts = gregorian_to_ganzhi_parts(now)
        self._set_ganzhi_parts(parts)

        self._greg_year.setValue(now.year)
        self._greg_month.setValue(now.month)
        self._greg_day.setValue(now.day)
        self._greg_hour.setValue(now.hour)
        self._greg_minute.setValue(now.minute)

    # ── 数据收集 ──

    def _collect_ganzhi(self) -> dict:
        yg = self._gz_year_gan.currentText()
        yz = self._gz_year_zhi.currentText()
        mg = self._gz_month_gan.currentText()
        mz = self._gz_month_zhi.currentText()
        dg = self._gz_day_gan.currentText()
        dz = self._gz_day_zhi.currentText()
        hg = self._gz_hour_gan.currentText()
        hz = self._gz_hour_zhi.currentText()
        return {
            "year_ganzhi": yg + yz,
            "month_ganzhi": mg + mz,
            "day_ganzhi": dg + dz,
            "day_gan": dg,
            "hour_ganzhi": hg + hz,
        }

    def _collect_gregorian(self) -> datetime.datetime:
        h = self._greg_hour.value() if self._hour_cb.isChecked() else 0
        m = self._greg_minute.value() if self._hour_cb.isChecked() else 0
        return datetime.datetime(
            self._greg_year.value(),
            self._greg_month.value(),
            self._greg_day.value(),
            h, m)

    def _on_ok(self):
        if self._active_mode == self.MODE_GANZHI:
            gz = self._collect_ganzhi()
            if not self._hour_cb.isChecked():
                gz["hour_ganzhi"] = self._current["hour_ganzhi"]
        else:
            dt = self._collect_gregorian()
            if self._hour_cb.isChecked():
                parts = gregorian_to_ganzhi_parts(dt)
            else:
                parts = gregorian_to_ganzhi_parts(datetime.datetime(
                    dt.year, dt.month, dt.day, 0, 0))
            gz = {
                "year_ganzhi": parts["year_gan"] + parts["year_zhi"],
                "month_ganzhi": parts["month_gan"] + parts["month_zhi"],
                "day_ganzhi": parts["day_gan"] + parts["day_zhi"],
                "day_gan": parts["day_gan"],
                "hour_ganzhi": (parts["hour_gan"] + parts["hour_zhi"]
                                if self._hour_cb.isChecked()
                                else self._current["hour_ganzhi"]),
            }
        self._result = gz
        self.accept()

    def result(self) -> dict | None:
        return self._result
