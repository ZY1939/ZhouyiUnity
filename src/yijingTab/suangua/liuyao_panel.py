"""
六爻面板 — 主卦 + 六神/世应/卦图/动爻/纳音/伏神 多列注解 + 卦辞/爻辞解读

═══════════════════════════════════════════════════════════════
文件职责：提供 LiuyaoPanel 组件，根据起卦结果显示六爻纳甲断卦界面
═══════════════════════════════════════════════════════════════

布局结构：
  ┌─ LiuyaoPanel ─────────────────────────────────────────────────┐
  │                                           [精简/全部]          │
  │  [六神] [世应] [HexagramDrawer] [动爻o/x] [纳音] [伏神]       │
  │   青     世       ████            ○      财甲寅木  伏:孙-甲子  │
  │   朱              ████            ×      官丙午火             │
  │   ...                                                ...      │
  │  ┌─ 蓝/橙色方块 ─────────────────────────────────────────┐    │
  │  │ 爻辞/卦辞 + 小象/彖曰                                   │    │
  │  └──────────────────────────────────────────────────────┘    │
  └──────────────────────────────────────────────────────────────┘
"""
import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QFrame, QApplication)
from PySide6.QtCore import Qt, QTimer, QEvent, QPointF, QRectF
from PySide6.QtGui import QFontMetrics, QColor, QPen, QPainter

from ..com.hexagram_drawer import HexagramDrawer, _app_font
from ..CONST_DEFINE_UI import LiuyaoConfig
from ...settings.config_manager import config_manager
from ...algorithms.liuyao import (analyze_gua, get_fushen, get_gua_type_tags,
                                  get_gua_type_badges, check_hexagram_fanyin_fuyin)
from ...algorithms.wuxingTools import (
    DIZHI_WUXING,
    WUXING_BASE_COLORS,
    WUXING_SHENG,
    WUXING_KE,
    LIUQIN_COMPACT,
    LIUSHEN_INFO,
    TI_COLOR, YONG_COLOR, O_COLOR, X_COLOR,
    compact_liuqin, get_wuxing_base_color, get_liushen_fill,
    get_liuqin,
)
from ..com.bagua import BINARY_TO_GUA
from ..com.hexagram_loader import load_all_gua

# ── 从 common 导入公共组件 ──
from .common import (_LineMarker, is_light_color, build_interpretation)


# ── 主事爻标注颜色 ──
ZHUSHI_COLOR = "#ff9500"    # 橙色
ZHUSHI_X_COLOR = "#af52de"  # 紫色


# ═══════════════════════════════════════════════════════════════
#  精简显示格式函数
# ═══════════════════════════════════════════════════════════════

def _format_nayin_text(line: dict, compact: bool) -> str:
    """
    纳音文字格式化

    Args:
        line: 六爻行数据 (liuqin, najia, zhi, dizhi_wuxing)
        compact: True=精简模式 "(财寅木)", False=完整模式 "妻财甲寅木"

    Returns:
        str: 格式化后的纳音文字
    """
    liuqin = line.get("liuqin", "")
    najia = line.get("najia", "")
    zhi = line.get("zhi", "")
    wx = line.get("dizhi_wuxing", "")

    if compact:
        c = LIUQIN_COMPACT.get(liuqin, liuqin)
        return f"{c}{zhi}{wx}"
    else:
        return f"{liuqin}{najia}{wx}"


def _format_fushen_text(fs: dict) -> str:
    """
    伏神文字格式化（始终使用精简模式）

    Args:
        fs: 伏神数据 (liuqin, zhi, dizhi_wuxing)

    Returns:
        str: 格式化后的伏神文字，如 "伏:孙-酉金"
    """
    liuqin = fs.get("liuqin", "")
    zhi = fs.get("zhi", "")
    wx = fs.get("dizhi_wuxing", "")
    c = LIUQIN_COMPACT.get(liuqin, liuqin)
    return f"伏：{c}-{zhi}{wx}"



# ═══════════════════════════════════════════════════════════════
#  _NayinLabel — 纳音标注（文字 + 五行彩色边框）
# ═══════════════════════════════════════════════════════════════

class _NayinLabel(QWidget):
    """
    在每爻位置绘制纳音文字（如"妻财甲寅木"）+ 五行彩色边框

    与 HexagramDrawer 使用相同的 center_y 公式确保对齐。
    宽度根据所有行中最宽的文字动态计算，左对齐。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[tuple[int, str, QColor]] = []  # (line_idx, text, border_color)
        self._name_area_h = 0
        self._line_h = 0
        self._offset_y = 0
        self._font_size = 16
        self._text_color = "#1d1d1f"
        self._border_width = 2
        self._padding = 4
        self._fixed_w = 80

    def configure(self, name_area_h: int, line_h: int, offset_y: int = 0,
                  font_size: int = 16):
        self._name_area_h = name_area_h
        self._line_h = line_h
        self._offset_y = offset_y
        self._font_size = font_size
        self.setFixedHeight(name_area_h + 6 * line_h)

    def set_border_width(self, px: float):
        self._border_width = px
        self._recalc_width()
        self.update()

    def set_padding(self, px: int):
        self._padding = px
        self._recalc_width()
        self.update()

    def set_text_color(self, text_color: str):
        self._text_color = text_color
        self.update()

    def set_font_size(self, fs: int):
        self._font_size = fs
        self._recalc_width()
        self.update()

    def set_items(self, items: list[tuple[int, str, str]]):
        """
        设置纳音内容

        Args:
            items: [(line_idx, text, border_color_hex), ...]
                   line_idx: 0=初爻..5=上爻
        """
        self._items = [(ln, txt, QColor(clr)) for ln, txt, clr in items]
        self._recalc_width()
        self.update()

    def _recalc_width(self):
        if not self._items:
            self._fixed_w = 80
        else:
            font = _app_font()
            font.setPointSize(self._font_size)
            fm = QFontMetrics(font)
            max_w = max(fm.horizontalAdvance(txt) for _, txt, _ in self._items)
            self._fixed_w = max_w + 2 * self._padding + 2 * self._border_width
        self.setFixedWidth(self._fixed_w)
        self.setMinimumWidth(self._fixed_w)

    def paintEvent(self, event):
        if not self._items:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = _app_font()
        font.setPointSize(self._font_size)
        p.setFont(font)
        fm = QFontMetrics(font)

        w = self.width()
        bw = self._border_width
        pad = self._padding

        for line_idx, text, border_color in self._items:
            center_y = (self._offset_y + self._name_area_h +
                        (5 - line_idx) * self._line_h + self._line_h // 2)

            text_w = fm.horizontalAdvance(text)
            text_h = fm.height()
            badge_w = text_w + 2 * pad + 2 * bw
            badge_h = min(text_h + 2 * pad + 2 * bw, self._line_h)
            badge_top = int(center_y - badge_h // 2)
            badge_x = 0

            p.setPen(QPen(border_color, bw))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(badge_x, badge_top, badge_w, badge_h, 6, 6)

            p.setPen(QColor(self._text_color))
            text_x = badge_x + pad + bw
            baseline_y = badge_top + (badge_h + fm.ascent() - fm.descent()) // 2
            p.drawText(int(text_x), int(baseline_y), text)

        p.end()


# ═══════════════════════════════════════════════════════════════
#  _FushenLabel — 伏神标注
# ═══════════════════════════════════════════════════════════════

class _FushenLabel(QWidget):
    """
    在每爻位置绘制伏神文字（如"伏:孙-酉金"）+ 六亲彩色方框

    与 _NayinLabel 类似，但文本格式采用伏神精简样式，
    使用六亲颜色作为边框色（而非地支五行颜色）。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[tuple[int, str, QColor]] = []  # (line_idx, text, liuqin_color)
        self._name_area_h = 0
        self._line_h = 0
        self._offset_y = 0
        self._font_size = 16
        self._text_color = "#1d1d1f"
        self._border_width = 2
        self._padding = 4
        self._fixed_w = 80

    def configure(self, name_area_h: int, line_h: int, offset_y: int = 0,
                  font_size: int = 16):
        self._name_area_h = name_area_h
        self._line_h = line_h
        self._offset_y = offset_y
        self._font_size = font_size
        self.setFixedHeight(name_area_h + 6 * line_h)

    def set_border_width(self, px: float):
        self._border_width = px
        self._recalc_width()
        self.update()

    def set_padding(self, px: int):
        self._padding = px
        self._recalc_width()
        self.update()

    def set_text_color(self, text_color: str):
        self._text_color = text_color
        self.update()

    def set_font_size(self, fs: int):
        self._font_size = fs
        self._recalc_width()
        self.update()

    def set_items(self, items: list[tuple[int, str, str]]):
        """
        设置伏神内容

        Args:
            items: [(line_idx, text, liuqin_color_hex), ...]
                   line_idx: 0=初爻..5=上爻
                   text: 如"伏:孙-酉金"
                   liuqin_color_hex: 六亲颜色
        """
        self._items = [(ln, txt, QColor(clr)) for ln, txt, clr in items]
        self._recalc_width()
        self.update()

    def _recalc_width(self):
        if not self._items:
            self._fixed_w = 80
        else:
            font = _app_font()
            font.setPointSize(self._font_size)
            fm = QFontMetrics(font)
            max_w = max(fm.horizontalAdvance(txt) for _, txt, _ in self._items)
            self._fixed_w = max_w + 2 * self._padding + 2 * self._border_width
        self.setFixedWidth(self._fixed_w)
        self.setMinimumWidth(self._fixed_w)

    def paintEvent(self, event):
        if not self._items:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = _app_font()
        font.setPointSize(self._font_size)
        p.setFont(font)
        fm = QFontMetrics(font)

        bw = self._border_width
        pad = self._padding

        for line_idx, text, liuqin_color in self._items:
            center_y = (self._offset_y + self._name_area_h +
                        (5 - line_idx) * self._line_h + self._line_h // 2)

            text_w = fm.horizontalAdvance(text)
            text_h = fm.height()
            badge_w = text_w + 2 * pad + 2 * bw
            badge_h = min(text_h + 2 * pad + 2 * bw, self._line_h)
            badge_top = int(center_y - badge_h // 2)
            badge_x = 0

            p.setPen(QPen(liuqin_color, bw))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(badge_x, badge_top, badge_w, badge_h, 6, 6)

            p.setPen(QColor(self._text_color))
            text_x = badge_x + pad + bw
            baseline_y = badge_top + (badge_h + fm.ascent() - fm.descent()) // 2
            p.drawText(int(text_x), int(baseline_y), text)

        p.end()


# ═══════════════════════════════════════════════════════════════
#  _TypeBadgeBar — 卦类型小方块（冲/合/游/归/反/伏）
# ═══════════════════════════════════════════════════════════════

class _TypeBadgeBar(QWidget):
    """卦类型标签小方块 — 彩色方块+白字，水平排列，字号与六兽/世应 markers 一致"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._badges: list[tuple[str, str]] = []  # [(tag_text, color_hex), ...]
        self._font_size = 16
        self._side = 20
        self._padding = 0

    def set_padding(self, px: int):
        self._padding = px
        self.update()

    def set_badges(self, badges: list[tuple[str, str]], font_size: int = 16):
        self._badges = badges
        self._font_size = font_size
        font = _app_font()
        font.setPointSize(font_size)
        font.setBold(True)
        fm = QFontMetrics(font)
        self._side = int(fm.height() + 2 * self._padding)
        n = len(badges)
        gap = max(2, self._side // 5)
        self.setFixedWidth(max(0, n * self._side + (n - 1) * gap))
        self.setFixedHeight(self._side)
        self.update()

    def paintEvent(self, event):
        if not self._badges:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = self._side
        gap = max(2, side // 5)

        font = _app_font()
        font.setPointSize(self._font_size)
        font.setBold(True)
        p.setFont(font)

        x = 0
        for tag, color_hex in self._badges:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(color_hex))
            p.drawRoundedRect(x, 0, side, side, 3, 3)
            p.setPen(QColor("#ffffff"))
            p.drawText(x, 0, side, side,
                       Qt.AlignmentFlag.AlignCenter, tag)
            x += side + gap
        p.end()


# ═══════════════════════════════════════════════════════════════
#  _ArrowColumn — 本卦→变卦 动爻箭头列
# ═══════════════════════════════════════════════════════════════

class _ArrowColumn(QWidget):
    """
    在每爻动爻位置绘制箭头 + 生克 badge（圆角矩形白字彩色底），连接本卦六亲和变卦

    变克/生本 → 左箭头（←），本克/生变 → 右箭头（→），比和 → 双箭头（↔）
    克=红色，生=绿色，比和=紫色
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._arrows: list[tuple[int, str, str, str]] = []  # [(line_idx, direction, color, label), ...]
        self._name_area_h = 0
        self._line_h = 0
        self._offset_y = 0
        self._arrow_w_scale = LiuyaoConfig.arrow_width_scale
        self._label_gap = 2
        self._badge_padding = 1
        self._font_size = 16

    def configure(self, name_area_h: int, line_h: int, offset_y: int = 0,
                  label_gap: int = 2, font_size: int = 16, badge_padding: int = 1):
        self._name_area_h = name_area_h
        self._line_h = line_h
        self._offset_y = offset_y
        self._label_gap = label_gap
        self._font_size = font_size
        self._badge_padding = badge_padding
        self.setFixedHeight(name_area_h + 6 * line_h)
        self._update_width()

    def set_arrow_width_scale(self, scale: float):
        self._arrow_w_scale = scale
        self._update_width()
        self.update()

    def set_arrows(self, arrows: list[tuple[int, str, str, str]]):
        """
        设置箭头数据

        Args:
            arrows: [(line_idx, direction, color, label), ...]
                    line_idx: 0=初爻..5=上爻
                    direction: "left" 或 "right"
                    color: hex 颜色字符串（箭头/badge 共用）
                    label: "生"/"克"/"和"
        """
        self._arrows = arrows
        self._update_width()
        self.update()

    def _badge_side(self) -> int:
        """badge 正方形边长 = fm 高度 + 2 * 内边距"""
        font = _app_font()
        font.setPointSize(self._font_size)
        font.setBold(True)
        fm = QFontMetrics(font)
        return int(fm.height() + 2 * self._badge_padding)

    def _update_width(self):
        """宽度 = 三角 + 间距 + badge正方形 + 留白"""
        tri_w = max(6, int(self._line_h * self._arrow_w_scale))
        badge_w = self._badge_side()
        total = int(2 + tri_w + self._label_gap + badge_w + 2)
        self.setFixedWidth(total)
        self.setMinimumWidth(total)

    def paintEvent(self, event):
        if not self._arrows:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        tri_w = max(6, int(self._line_h * self._arrow_w_scale))
        tri_h = self._line_h * 0.5

        font = _app_font()
        font.setPointSize(self._font_size)
        font.setBold(True)
        p.setFont(font)

        badge_side = self._badge_side()
        tri_left = 2
        tri_right = tri_left + tri_w
        badge_x = tri_right + self._label_gap
        corner_r = max(2, badge_side // 5)

        for line_idx, direction, color_hex, label in self._arrows:
            center_y = (self._offset_y + self._name_area_h +
                       (5 - line_idx) * self._line_h + self._line_h // 2)
            cy = center_y

            # ── 画箭头 ──
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(color_hex))
            if direction == "both":
                # 双箭头 ↔：杆 + 左右两个三角
                shaft_h = tri_h * 0.35
                p.drawRect(QRectF(tri_left, cy - shaft_h / 2.0,
                                  tri_right - tri_left, shaft_h))
                pts_r = [QPointF(tri_right - tri_h * 0.55, cy - tri_h / 2.0),
                         QPointF(tri_right - tri_h * 0.55, cy + tri_h / 2.0),
                         QPointF(tri_right, cy)]
                pts_l = [QPointF(tri_left + tri_h * 0.55, cy - tri_h / 2.0),
                         QPointF(tri_left + tri_h * 0.55, cy + tri_h / 2.0),
                         QPointF(tri_left, cy)]
                p.drawPolygon(pts_r)
                p.drawPolygon(pts_l)
            elif direction == "right":
                points = [
                    QPointF(tri_left, cy - tri_h / 2.0),
                    QPointF(tri_left, cy + tri_h / 2.0),
                    QPointF(tri_right, cy),
                ]
                p.drawPolygon(points)
            else:
                points = [
                    QPointF(tri_right, cy - tri_h / 2.0),
                    QPointF(tri_right, cy + tri_h / 2.0),
                    QPointF(tri_left, cy),
                ]
                p.drawPolygon(points)

            # ── 画生克 badge（圆角矩形 + 白色文字）──
            badge_top = int(cy - badge_side / 2.0)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(color_hex))
            p.drawRoundedRect(int(badge_x), badge_top, badge_side, badge_side,
                            corner_r, corner_r)

            p.setPen(QColor("#ffffff"))
            p.drawText(int(badge_x), badge_top, badge_side, badge_side,
                       Qt.AlignmentFlag.AlignCenter, label)

        p.end()


# ═══════════════════════════════════════════════════════════════
#  LiuyaoPanel — 六爻主面板
# ═══════════════════════════════════════════════════════════════

class LiuyaoPanel(QWidget):
    """
    六爻面板 — 主卦 + 六神/世应/卦图/动爻/纳音/伏神 多列注解

    根据卦名和日干（来自 SuanguaPanel 共享时间），调用 analyze_gua()
    计算完整的六爻纳甲信息，并在 HexagramDrawer 左右两侧显示标注。

    时间由 SuanguaPanel 统一管理，通过 set_time_ganzhi() 传入。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_size = 16
        self._text_color = "#1d1d1f"
        self._fs_name = LiuyaoConfig.fs_name

        # 配置参数
        self._gap_liuyao_left = LiuyaoConfig.gap_liuyao_left
        self._gap_liuyao_right = LiuyaoConfig.gap_liuyao_right
        self._gap_marker_to_drawer = LiuyaoConfig.gap_marker_to_drawer
        self._gap_liushen_to_shiying = LiuyaoConfig.gap_liushen_to_shiying
        self._gap_dongyao_to_nayin = LiuyaoConfig.gap_dongyao_to_nayin
        self._gap_nayin_to_fushen = LiuyaoConfig.gap_nayin_to_fushen
        self._badge_padding = LiuyaoConfig.badge_padding
        self._nayin_border_width = LiuyaoConfig.nayin_border_width
        self._nayin_padding = LiuyaoConfig.nayin_padding
        self._fs_offset_liushen = LiuyaoConfig.fs_offset_liushen
        self._fs_offset_shiying = LiuyaoConfig.fs_offset_shiying
        self._fs_offset_dongyao = LiuyaoConfig.fs_offset_dongyao
        self._fs_offset_nayin = LiuyaoConfig.fs_offset_nayin

        # ── 变卦配置 ──
        self._arrow_width_scale = LiuyaoConfig.arrow_width_scale
        self._arrow_color_he = LiuyaoConfig.arrow_color_he
        self._arrow_color_ke = LiuyaoConfig.arrow_color_ke
        self._arrow_color_sheng = LiuyaoConfig.arrow_color_sheng
        self._arrow_badge_padding = LiuyaoConfig.arrow_badge_padding
        self._biangua_dongyao_yang = LiuyaoConfig.biangua_dongyao_yang
        self._biangua_dongyao_yin = LiuyaoConfig.biangua_dongyao_yin

        # ── 精简模式 ──
        self._compact = config_manager.get("general", "liuyao_compact")
        if self._compact is None:
            self._compact = False

        # 数据状态
        self._liuyao_result = None
        self._changing_lines: list[int] = []
        self._ben_data = None
        self._bian_data = None  # 变卦数据（用于反吟/伏吟判断）
        self._current_ganzhi: dict | None = None
        self._fushen_data: list[dict | None] = []

        # Widget 引用
        self._drawer = None
        self._liushen_marker = None
        self._shiying_marker = None
        self._dongyao_marker = None
        self._nayin_label = None
        self._fushen_label = None
        self._compact_btn = None
        self._interpret_frame = None
        self._interpret_label = None
        self._type_badge_bar = None
        self._liushen_marker_w = 0
        self._shiying_marker_w = 0
        self._dongyao_marker_w = 0
        self._zhushiyao_line: int = 0   # 0=未选择，1-6=初爻..上爻
        self._status_timer = None       # 状态栏恢复定时器（防堆积）

        # ── 变卦 Widget 引用 ──
        self._arrow_column = None       # _ArrowColumn
        self._bian_drawer = None        # HexagramDrawer 变卦
        self._bian_nayin_label = None   # _NayinLabel 变卦六亲
        self._bian_type_bar = None      # _TypeBadgeBar 变卦类型标签
        self._bian_info: dict | None = None  # 变卦计算结果缓存
        self._bian_section: QWidget | None = None  # 变卦整体容器（含箭头+drawer+六亲）

        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 创建 drawer ──
        self._drawer = HexagramDrawer()
        self._drawer.set_custom_title(None)
        self._drawer.setCursor(Qt.CursorShape.PointingHandCursor)
        self._drawer.installEventFilter(self)
        lh = self._drawer.line_h
        name_h = self._drawer.name_area_h

        g = self._gap_marker_to_drawer

        # ── 六神标注（VBox中有按钮在上方，offset_y 补偿）──
        self._liushen_marker = _LineMarker(align_right=True)
        self._liushen_marker.configure(name_h, lh, offset_y=-name_h,
                                       font_size=self._font_size)
        self._liushen_marker.setFixedHeight(6 * lh)
        self._liushen_marker.set_badge_mode(True)
        self._liushen_marker.set_badge_padding_ox(self._badge_padding)
        self._liushen_marker.set_fs_offset(self._fs_offset_liushen)

        # ── 世应标注（VBox中有按钮在上方，offset_y 补偿）──
        self._shiying_marker = _LineMarker(align_right=True)
        self._shiying_marker.configure(name_h, lh, offset_y=-name_h,
                                       font_size=self._font_size)
        self._shiying_marker.setFixedHeight(6 * lh)
        self._shiying_marker.set_badge_mode(True)
        self._shiying_marker.set_badge_padding_ox(self._badge_padding)
        self._shiying_marker.set_fs_offset(self._fs_offset_shiying)

        # ── 动爻标注 ──
        self._dongyao_marker = _LineMarker(align_right=False)
        self._dongyao_marker.configure(name_h, lh, offset_y=-name_h,
                                       font_size=self._font_size)
        self._dongyao_marker.setFixedHeight(6 * lh)
        self._dongyao_marker.set_badge_mode(True)
        self._dongyao_marker.set_badge_padding_ox(self._badge_padding)
        self._dongyao_marker.set_fs_offset(self._fs_offset_dongyao)

        # ── 纳音标注 ──
        self._nayin_label = _NayinLabel()
        self._nayin_label.configure(name_h, lh, offset_y=-name_h,
                                    font_size=self._font_size)
        self._nayin_label.setFixedHeight(6 * lh)
        self._nayin_label.set_border_width(self._nayin_border_width)
        self._nayin_label.set_padding(self._nayin_padding)

        # ── 计算标注宽度 ──
        self._recalc_all_marker_widths()

        liushen_w = self._liushen_marker_w
        shiying_w = self._shiying_marker_w

        # 计算 badge 实际正方形边长（用于按钮水平对齐）
        liushen_badge_side = self._calc_badge_side(self._font_size + self._fs_offset_liushen)
        badge_left_offset = max(0, liushen_w - liushen_badge_side)  # badge 在 marker 内的左缩进

        # ── 精简/全部 切换按钮 ──
        # 左对齐 六兽 badge 左边缘，右对齐 世应 badge 右边缘
        btn_text = "精简" if self._compact else "全部"
        self._compact_btn = QPushButton(btn_text)
        self._compact_btn.setFlat(True)
        self._compact_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._compact_btn.clicked.connect(self._toggle_compact)
        self._compact_btn.setFixedHeight(name_h)
        btn_w = liushen_badge_side + self._gap_liushen_to_shiying + shiying_w
        self._compact_btn.setFixedWidth(btn_w)
        self._compact_btn.setMinimumWidth(btn_w)
        self._compact_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {self._font_size - 1}px;
                color: #1d1d1f;
                background: #f5f5f7;
                border: 1px solid #dcdcdc;
                border-radius: 5px;
                padding: 1px 8px;
            }}
            QPushButton:hover {{ background: #e8e8ed; border-color: #007aff; }}
        """)

        # 按钮水平容器 — 左缩进让按钮左边缘与 六兽 badge 左边缘对齐
        self._btn_wrapper = QHBoxLayout()
        self._btn_wrapper.setContentsMargins(badge_left_offset, 0, 0, 0)
        self._btn_wrapper.setSpacing(0)
        self._btn_wrapper.addWidget(self._compact_btn)

        # ── 左列固定宽度容器（防止布局拉伸破坏间距）──
        left_total = liushen_w + self._gap_liushen_to_shiying + shiying_w
        left_w = max(left_total, btn_w + badge_left_offset)
        self._left_container = QWidget()
        self._left_container.setFixedWidth(left_w)
        self._left_vbox = QVBoxLayout(self._left_container)
        self._left_vbox.setContentsMargins(0, 0, 0, 0)
        self._left_vbox.setSpacing(0)
        self._left_vbox.addLayout(self._btn_wrapper)

        # 六神+世应 水平排
        ls_row = QHBoxLayout()
        ls_row.setContentsMargins(0, 0, 0, 0)
        ls_row.setSpacing(0)
        ls_row.addWidget(self._liushen_marker)
        ls_row.addSpacing(self._gap_liushen_to_shiying)
        ls_row.addWidget(self._shiying_marker)
        self._left_vbox.addLayout(ls_row)

        # ── 类型标签方块栏（name_h 高度，与卦title对齐）──
        self._type_badge_bar = _TypeBadgeBar()
        self._type_badge_bar.set_padding(self._badge_padding)
        self._type_badge_bar.setFixedHeight(name_h)
        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        badge_row.setSpacing(0)
        badge_row.addWidget(self._type_badge_bar)
        badge_row.addStretch()

        # ── 右列固定宽度容器 ──
        right_total = self._dongyao_marker_w + self._gap_dongyao_to_nayin + self._nayin_label._fixed_w
        self._right_container = QWidget()
        self._right_container.setFixedWidth(right_total)
        right_vbox = QVBoxLayout(self._right_container)
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.setSpacing(0)
        right_vbox.addLayout(badge_row)
        right_row = QHBoxLayout()
        right_row.setContentsMargins(0, 0, 0, 0)
        right_row.setSpacing(0)
        right_row.addWidget(self._dongyao_marker)
        right_row.addSpacing(self._gap_dongyao_to_nayin)
        right_row.addWidget(self._nayin_label)
        right_vbox.addLayout(right_row)

        # ── 变卦整体容器（含箭头+drawer+六亲，静卦时整体隐藏）──
        self._bian_section = QWidget()
        self._bian_section.setVisible(False)
        bian_section_row = QHBoxLayout(self._bian_section)
        bian_section_row.setContentsMargins(0, 0, 0, 0)
        bian_section_row.setSpacing(0)

        # 变卦 arrow column（高度 = name_h + 6*lh，offset_y=0 直接对齐 drawer 顶部）
        self._arrow_column = _ArrowColumn()
        self._arrow_column.configure(name_h, lh, offset_y=0,
                                     label_gap=self._gap_liushen_to_shiying,
                                     font_size=self._font_size,
                                     badge_padding=self._arrow_badge_padding)

        # 变卦 drawer
        self._bian_drawer = HexagramDrawer()
        self._bian_drawer.set_custom_title(None)

        # 变卦六亲标注
        self._bian_nayin_label = _NayinLabel()
        self._bian_nayin_label.configure(name_h, lh, offset_y=-name_h,
                                          font_size=self._font_size)
        self._bian_nayin_label.setFixedHeight(6 * lh)
        self._bian_nayin_label.set_border_width(self._nayin_border_width)
        self._bian_nayin_label.set_padding(self._nayin_padding)

        # 变卦类型标签
        self._bian_type_bar = _TypeBadgeBar()
        self._bian_type_bar.set_padding(self._badge_padding)
        self._bian_type_bar.setFixedHeight(name_h)

        bian_badge_row = QHBoxLayout()
        bian_badge_row.setContentsMargins(0, 0, 0, 0)
        bian_badge_row.setSpacing(0)
        bian_badge_row.addWidget(self._bian_type_bar)
        bian_badge_row.addStretch()

        # 变卦右列固定宽度容器
        self._bian_right_container = QWidget()
        self._bian_right_container.setFixedWidth(self._nayin_label._fixed_w)
        bian_right_vbox = QVBoxLayout(self._bian_right_container)
        bian_right_vbox.setContentsMargins(0, 0, 0, 0)
        bian_right_vbox.setSpacing(0)
        bian_right_vbox.addLayout(bian_badge_row)
        bian_right_row = QHBoxLayout()
        bian_right_row.setContentsMargins(0, 0, 0, 0)
        bian_right_row.setSpacing(0)
        bian_right_row.addWidget(self._bian_nayin_label)
        bian_right_vbox.addLayout(bian_right_row)

        # ── 变卦容器内布局（间距统一使用 _gap_liushen_to_shiying）──
        arrow_gap = self._gap_liushen_to_shiying
        bian_section_row.addSpacing(arrow_gap)
        bian_section_row.addWidget(self._arrow_column)
        bian_section_row.addSpacing(arrow_gap)
        bian_section_row.addWidget(self._bian_drawer)
        bian_section_row.addSpacing(arrow_gap)
        bian_section_row.addWidget(self._bian_right_container)

        # ── 调试输出 ──
        print(f"[liuyao_panel] liushen_w={liushen_w} shiying_w={shiying_w} "
              f"left_w={left_w} dongyao_w={self._dongyao_marker_w} "
              f"nayin_w={self._nayin_label._fixed_w} right_w={right_total}", flush=True)

        # ── 主卦行：固定宽度的左/右容器 + drawer + 变卦区域 ──
        main_row = QHBoxLayout()
        main_row.setContentsMargins(self._gap_liuyao_left, 0, self._gap_liuyao_right, 0)
        main_row.setSpacing(0)
        main_row.addWidget(self._left_container)
        main_row.addSpacing(g)
        main_row.addWidget(self._drawer)
        main_row.addSpacing(g)
        main_row.addWidget(self._right_container)
        main_row.addWidget(self._bian_section)
        main_row.addStretch()
        root.addLayout(main_row)

        for m in [self._liushen_marker, self._shiying_marker, self._dongyao_marker]:
            if m:
                m.raise_()

        root.addSpacing(8)

        # ── 底部解读方块 ──
        self._interpret_frame = QFrame()
        self._interpret_frame.setVisible(False)
        self._interpret_frame.setStyleSheet("border-radius: 6px; padding: 8px 12px;")
        interp_layout = QVBoxLayout(self._interpret_frame)
        interp_layout.setContentsMargins(12, 8, 12, 8)
        self._interpret_label = QLabel("")
        self._interpret_label.setWordWrap(True)
        self._interpret_label.setTextFormat(Qt.TextFormat.RichText)
        self._interpret_label.setStyleSheet("background: transparent;")
        interp_layout.addWidget(self._interpret_label)
        root.addWidget(self._interpret_frame)

        root.addStretch()

    # ═══════════════════════════════════════════════════════════
    #  精简模式切换
    # ═══════════════════════════════════════════════════════════

    def _toggle_compact(self):
        self._compact = not self._compact
        config_manager.set("general", "liuyao_compact", value=self._compact)
        self._compact_btn.setText("精简" if self._compact else "全部")
        # 刷新纳音和伏神显示
        if self._liuyao_result:
            self._update_nayin_items(self._liuyao_result)
            self._update_fushen_items()
            self._update_container_widths()
            # ── 变卦六亲同步刷新 ──
            self._update_biangua_display()

    # ═══════════════════════════════════════════════════════════
    #  公共接口
    # ═══════════════════════════════════════════════════════════

    def set_time_ganzhi(self, ganzhi: dict):
        self._current_ganzhi = ganzhi
        if self._ben_data and self._changing_lines is not None:
            self._refresh_analysis()

    def _refresh_analysis(self):
        gua_name = self._ben_data.get("full_name", "")
        day_gan = self._current_ganzhi["day_gan"]
        result = analyze_gua(gua_name, day_gan)
        if "error" in result:
            return
        self._liuyao_result = result
        self._fushen_data = get_fushen(gua_name)
        self._update_liushen_markers(result)
        self._update_shiying_markers(result)
        self._update_dongyao_markers(self._ben_data, self._changing_lines)
        self._update_nayin_items(result)
        self._update_fushen_items()
        self._update_type_badges(gua_name)
        self._update_container_widths()
        self._update_zhushi_markers()
        self._update_interpretation()
        # ── 变卦刷新 ──
        self._compute_biangua_info()
        self._update_biangua_display()

    # ═══════════════════════════════════════════════════════════════
    #  变卦数据计算
    # ═══════════════════════════════════════════════════════════════

    def _compute_biangua_info(self):
        """
        计算变卦数据：binary翻转 → 卦名查找 → 纳甲 → 六亲(按本卦宫) → 箭头数据

        变卦六亲按本卦宫五行计算（非变卦自身宫位），这是六爻纳甲的标准规则。
        箭头方向：被动爻克/生 → 左箭头；其他 → 右箭头
        箭头颜色：克=红，生=绿，比和=蓝
        """
        if not self._ben_data or not self._changing_lines:
            self._bian_info = None
            return

        if not self._liuyao_result:
            self._bian_info = None
            return

        ben_binary = self._ben_data.get("binary", "111111")
        # 翻转动爻位得到变卦 binary
        bian_chars = list(ben_binary)
        for cl in self._changing_lines:
            idx = cl - 1
            bian_chars[idx] = "0" if ben_binary[idx] == "1" else "1"
        bian_binary = "".join(bian_chars)

        # 查变卦数据
        load_all_gua()
        bian_gua_data = BINARY_TO_GUA.get(bian_binary)
        if not bian_gua_data:
            self._bian_info = None
            return

        bian_name = bian_gua_data.get("full_name", "")
        day_gan = self._current_ganzhi["day_gan"] if self._current_ganzhi else "甲"
        bian_result = analyze_gua(bian_name, day_gan)
        if "error" in bian_result:
            self._bian_info = None
            return

        # 变卦六亲按本卦宫五行计算
        ben_palace_wx = self._liuyao_result.get("palace_wuxing", "")
        for line in bian_result["lines"]:
            zhi = line["zhi"]
            line["liuqin"] = get_liuqin(ben_palace_wx, zhi)

        # 计算箭头数据（颜色来自 LiuyaoConfig）
        arrows = []
        ben_lines = self._liuyao_result.get("lines", [])
        bian_lines = bian_result.get("lines", [])
        for cl in self._changing_lines:
            idx = cl - 1
            ben_wx = DIZHI_WUXING.get(ben_lines[idx]["zhi"], "")
            bian_wx = DIZHI_WUXING.get(bian_lines[idx].get("zhi", ""), "")

            if not ben_wx or not bian_wx:
                continue

            if ben_wx == bian_wx:
                direction, color, label = "both", self._arrow_color_he, "和"
            elif WUXING_KE.get(bian_wx) == ben_wx:
                direction, color, label = "left", self._arrow_color_ke, "克"
            elif WUXING_SHENG.get(bian_wx) == ben_wx:
                direction, color, label = "left", self._arrow_color_sheng, "生"
            elif WUXING_KE.get(ben_wx) == bian_wx:
                direction, color, label = "right", self._arrow_color_ke, "克"
            elif WUXING_SHENG.get(ben_wx) == bian_wx:
                direction, color, label = "right", self._arrow_color_sheng, "生"
            else:
                direction, color, label = "both", self._arrow_color_he, "和"

            arrows.append((idx, direction, color, label))

        self._bian_info = {
            "bian_name": bian_name,
            "bian_binary": bian_binary,
            "bian_result": bian_result,
            "bian_gua_data": bian_gua_data,
            "arrows": arrows,
        }

    def _update_biangua_display(self):
        """根据 _bian_info 更新变卦相关所有 widget"""
        if not self._bian_info:
            # 无变卦（静卦）→ 隐藏整个变卦区域
            if self._bian_section:
                self._bian_section.setVisible(False)
            return

        bian_info = self._bian_info
        bian_binary = bian_info["bian_binary"]
        bian_result = bian_info["bian_result"]
        bian_name = bian_info["bian_name"]

        # 显示变卦区域
        if self._bian_section:
            self._bian_section.setVisible(True)

        # 变卦 drawer
        if self._bian_drawer:
            yang = [c == "1" for c in bian_binary]
            self._bian_drawer.set_lines(yang)
            self._bian_drawer.set_disabled_look(False)
            self._bian_drawer.set_custom_title(f"变·{bian_name}")
            # 动爻位置加深着色
            overrides = {}
            for cl in self._changing_lines:
                idx = cl - 1
                is_yang = bian_binary[idx] == "1"
                overrides[idx] = self._biangua_dongyao_yang if is_yang else self._biangua_dongyao_yin
            self._bian_drawer.set_line_color_overrides(overrides)

        # 箭头
        if self._arrow_column:
            self._arrow_column.set_arrows(bian_info["arrows"])

        # 变卦六亲
        if self._bian_nayin_label:
            lines = bian_result.get("lines", [])
            items = []
            for line in lines:
                line_idx = line["position"] - 1
                text = _format_nayin_text(line, self._compact)
                zhi_wx = line.get("dizhi_wuxing", "")
                border_color = get_wuxing_base_color(zhi_wx)
                items.append((line_idx, text, border_color))
            self._bian_nayin_label.set_items(items)

        # 变卦类型标签
        if self._bian_type_bar:
            fy_result = check_hexagram_fanyin_fuyin(bian_name)
            fanyin_type = fy_result.get("fanyin_type", "")
            fuyin_type = fy_result.get("fuyin_type", "")
            if fuyin_type and get_gua_type_tags(bian_name) == "冲":
                fuyin_type = ""
            badges = get_gua_type_badges(bian_name, fanyin_type, fuyin_type)
            self._bian_type_bar.set_badges(badges, self._font_size)

        self._update_container_widths()

    def set_gua_result(self, ben_data: dict, changing_lines: list[int],
                        bian_data: dict | None = None):
        new_name = ben_data.get("full_name", "")
        if self._ben_data and self._ben_data.get("full_name", "") != new_name:
            self._zhushiyao_line = 0

        self._ben_data = ben_data
        self._changing_lines = changing_lines
        self._bian_data = bian_data

        gua_name = ben_data.get("full_name", "")
        day_gan = self._current_ganzhi["day_gan"] if self._current_ganzhi else "甲"
        result = analyze_gua(gua_name, day_gan)
        if "error" in result:
            return
        self._liuyao_result = result
        self._fushen_data = get_fushen(gua_name)

        binary = ben_data.get("binary", "111111")
        yang = [c == "1" for c in binary]
        self._drawer.set_lines(yang)
        self._drawer.set_disabled_look(False)
        self._drawer.set_custom_title(f"主·{gua_name}")

        # ── 类型标签方块 ──
        self._update_type_badges(gua_name)

        self._update_liushen_markers(result)
        self._update_shiying_markers(result)
        self._update_dongyao_markers(ben_data, changing_lines)
        self._update_nayin_items(result)
        self._update_fushen_items()
        self._update_container_widths()
        self._update_zhushi_markers()
        self._update_interpretation()
        # ── 变卦计算和显示 ──
        self._compute_biangua_info()
        self._update_biangua_display()

    def _update_interpretation(self):
        if not self._ben_data:
            return
        result = build_interpretation(self._ben_data, self._changing_lines, self._font_size)
        if result:
            html, bg_color = result
            self._interpret_label.setText(html)
            self._interpret_frame.setStyleSheet(f"""
                QFrame {{
                    background: {bg_color};
                    border-radius: 6px;
                }}
            """)
            self._interpret_frame.setVisible(True)
        else:
            self._interpret_frame.setVisible(False)

    # ═══════════════════════════════════════════════════════════
    #  外观刷新
    # ═══════════════════════════════════════════════════════════

    def set_font_size(self, font_size: int):
        self._font_size = font_size
        if self._drawer:
            self._drawer.set_font_size(font_size)
            self._drawer.set_name_fs(self._fs_name)

        lh = self._drawer.line_h if self._drawer else 40
        name_h = self._drawer.name_area_h if self._drawer else 16

        if self._liushen_marker:
            self._liushen_marker.configure(name_h, lh, offset_y=-name_h,
                                           font_size=font_size)
            self._liushen_marker.setFixedHeight(6 * lh)
            self._liushen_marker.set_font_size(font_size)
            self._liushen_marker.set_fs_offset(self._fs_offset_liushen)
            self._liushen_marker.set_badge_padding_ox(self._badge_padding)

        if self._shiying_marker:
            self._shiying_marker.configure(name_h, lh, offset_y=-name_h,
                                           font_size=font_size)
            self._shiying_marker.setFixedHeight(6 * lh)
            self._shiying_marker.set_font_size(font_size)
            self._shiying_marker.set_fs_offset(self._fs_offset_shiying)
            self._shiying_marker.set_badge_padding_ox(self._badge_padding)

        if self._dongyao_marker:
            self._dongyao_marker.configure(name_h, lh, offset_y=-name_h,
                                           font_size=font_size)
            self._dongyao_marker.setFixedHeight(6 * lh)
            self._dongyao_marker.set_font_size(font_size)
            self._dongyao_marker.set_fs_offset(self._fs_offset_dongyao)
            self._dongyao_marker.set_badge_padding_ox(self._badge_padding)

        if self._nayin_label:
            self._nayin_label.configure(name_h, lh, offset_y=-name_h,
                                        font_size=font_size)
            self._nayin_label.setFixedHeight(6 * lh)
            self._nayin_label.set_border_width(self._nayin_border_width)
            self._nayin_label.set_padding(self._nayin_padding)

        # ── 变卦 widgets 刷新 ──
        if self._arrow_column:
            self._arrow_column.configure(name_h, lh, offset_y=0,
                                         label_gap=self._gap_liushen_to_shiying,
                                         font_size=font_size,
                                         badge_padding=self._arrow_badge_padding)

        if self._bian_drawer:
            self._bian_drawer.set_font_size(font_size)
            self._bian_drawer.set_name_fs(self._fs_name)

        if self._bian_nayin_label:
            self._bian_nayin_label.configure(name_h, lh, offset_y=-name_h,
                                              font_size=font_size)
            self._bian_nayin_label.setFixedHeight(6 * lh)
            self._bian_nayin_label.set_border_width(self._nayin_border_width)
            self._bian_nayin_label.set_padding(self._nayin_padding)

        if self._bian_type_bar and self._bian_info:
            self._bian_type_bar.set_padding(self._badge_padding)
            bian_name = self._bian_info.get("bian_name", "")
            if bian_name:
                fy_result = check_hexagram_fanyin_fuyin(bian_name)
                fanyin_type = fy_result.get("fanyin_type", "")
                fuyin_type = fy_result.get("fuyin_type", "")
                if fuyin_type and get_gua_type_tags(bian_name) == "冲":
                    fuyin_type = ""
                badges = get_gua_type_badges(bian_name, fanyin_type, fuyin_type)
                self._bian_type_bar.set_badges(badges, font_size)

        if self._type_badge_bar and self._ben_data:
            self._type_badge_bar.set_padding(self._badge_padding)
            gua_name = self._ben_data.get("full_name", "")
            if gua_name:
                self._update_type_badges(gua_name)

        self._recalc_all_marker_widths()

        # 更新 toggle 按钮 + 容器边距
        if self._compact_btn:
            liushen_badge_side = self._calc_badge_side(font_size + self._fs_offset_liushen)
            badge_left_offset = max(0, self._liushen_marker_w - liushen_badge_side)

            self._compact_btn.setFixedHeight(name_h)
            self._compact_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: {font_size - 1}px;
                    color: #1d1d1f;
                    background: #f5f5f7;
                    border: 1px solid #dcdcdc;
                    border-radius: 5px;
                    padding: 1px 8px;
                }}
                QPushButton:hover {{ background: #e8e8ed; border-color: #007aff; }}
            """)
            btn_w = (liushen_badge_side + self._gap_liushen_to_shiying +
                     self._shiying_marker_w)
            self._compact_btn.setFixedWidth(btn_w)
            self._compact_btn.setMinimumWidth(btn_w)

            if self._btn_wrapper:
                self._btn_wrapper.setContentsMargins(badge_left_offset, 0, 0, 0)

        # 更新固定宽度容器的尺寸
        self._update_container_widths()
        self._update_interpretation()

    def set_text_color(self, text_color: str):
        self._text_color = text_color
        if self._drawer:
            self._drawer.set_text_color(text_color)
        if self._bian_drawer:
            self._bian_drawer.set_text_color(text_color)
        for m in [self._liushen_marker, self._shiying_marker, self._dongyao_marker]:
            if m:
                m.set_text_color(text_color)
        if self._nayin_label:
            self._nayin_label.set_text_color(text_color)
        if self._bian_nayin_label:
            self._bian_nayin_label.set_text_color(text_color)
        if self._liuyao_result:
            self._update_liushen_markers(self._liuyao_result)
            self._update_fushen_items()
        if self._ben_data and self._changing_lines is not None:
            self._update_dongyao_markers(self._ben_data, self._changing_lines)

    def set_fs_name(self, offset: int):
        self._fs_name = offset
        if self._drawer:
            self._drawer.set_name_fs(offset)
        if self._bian_drawer:
            self._bian_drawer.set_name_fs(offset)

    # ═══════════════════════════════════════════════════════════
    #  最小宽度
    # ═══════════════════════════════════════════════════════════

    def compute_min_width(self) -> int:
        g = self._gap_marker_to_drawer
        dw = self._drawer.minimumWidth() if self._drawer else 100
        nayin_w = self._nayin_label._fixed_w if self._nayin_label else 80

        left_w = (self._liushen_marker_w + self._gap_liushen_to_shiying +
                  self._shiying_marker_w)
        right_w = (self._dongyao_marker_w + self._gap_dongyao_to_nayin + nayin_w)

        # 变卦区域宽度
        arrow_w = (self._arrow_column.width() if self._arrow_column
                   else max(6, int(40 * self._arrow_width_scale)))
        bian_dw = self._bian_drawer.minimumWidth() if self._bian_drawer else 90
        bian_nayin_w = self._bian_nayin_label._fixed_w if self._bian_nayin_label else 80

        g = self._gap_liushen_to_shiying
        bian_total = g + arrow_w + g + bian_dw + g + bian_nayin_w

        return (self._gap_liuyao_left + left_w + g + dw + g + right_w +
                bian_total + self._gap_liuyao_right)

    # ═══════════════════════════════════════════════════════════
    #  configure
    # ═══════════════════════════════════════════════════════════

    def configure(self,
                  gap_liuyao_left: int | None = None,
                  gap_liuyao_right: int | None = None,
                  gap_marker_to_drawer: int | None = None,
                  gap_liushen_to_shiying: int | None = None,
                  gap_dongyao_to_nayin: int | None = None,
                  gap_nayin_to_fushen: int | None = None,
                  badge_padding: int | None = None,
                  nayin_border_width: int | None = None,
                  nayin_padding: int | None = None,
                  fs_offset_liushen: int | None = None,
                  fs_offset_shiying: int | None = None,
                  fs_offset_dongyao: int | None = None,
                  fs_offset_nayin: int | None = None,
                  arrow_width_scale: float | None = None,
                  arrow_badge_padding: int | None = None,
                  biangua_dongyao_yang: str | None = None,
                  biangua_dongyao_yin: str | None = None):
        if gap_liuyao_left is not None:
            self._gap_liuyao_left = gap_liuyao_left
        if gap_liuyao_right is not None:
            self._gap_liuyao_right = gap_liuyao_right
        if gap_marker_to_drawer is not None:
            self._gap_marker_to_drawer = gap_marker_to_drawer
        if gap_liushen_to_shiying is not None:
            self._gap_liushen_to_shiying = gap_liushen_to_shiying
        if gap_dongyao_to_nayin is not None:
            self._gap_dongyao_to_nayin = gap_dongyao_to_nayin
        if gap_nayin_to_fushen is not None:
            self._gap_nayin_to_fushen = gap_nayin_to_fushen
        if badge_padding is not None:
            self._badge_padding = badge_padding
        if nayin_border_width is not None:
            self._nayin_border_width = nayin_border_width
            if self._nayin_label:
                self._nayin_label.set_border_width(nayin_border_width)
            if self._bian_nayin_label:
                self._bian_nayin_label.set_border_width(nayin_border_width)
        if nayin_padding is not None:
            self._nayin_padding = nayin_padding
            if self._nayin_label:
                self._nayin_label.set_padding(nayin_padding)
            if self._bian_nayin_label:
                self._bian_nayin_label.set_padding(nayin_padding)
        if fs_offset_liushen is not None:
            self._fs_offset_liushen = fs_offset_liushen
        if fs_offset_shiying is not None:
            self._fs_offset_shiying = fs_offset_shiying
        if fs_offset_dongyao is not None:
            self._fs_offset_dongyao = fs_offset_dongyao
        if fs_offset_nayin is not None:
            self._fs_offset_nayin = fs_offset_nayin

        # ── 变卦参数 ──
        if arrow_width_scale is not None:
            self._arrow_width_scale = arrow_width_scale
            if self._arrow_column:
                self._arrow_column.set_arrow_width_scale(arrow_width_scale)
        if arrow_badge_padding is not None:
            self._arrow_badge_padding = arrow_badge_padding
        if biangua_dongyao_yang is not None:
            self._biangua_dongyao_yang = biangua_dongyao_yang
        if biangua_dongyao_yin is not None:
            self._biangua_dongyao_yin = biangua_dongyao_yin

        self._recalc_all_marker_widths()

    # ═══════════════════════════════════════════════════════════
    #  标注更新
    # ═══════════════════════════════════════════════════════════

    def _update_liushen_markers(self, result: dict):
        """填充六神标注：单字 + 五行颜色 badge（颜色由 WUXING_COLORS 派生）"""
        lines = result.get("lines", [])
        is_dark = self._is_system_dark_mode()

        markers = []
        for line in lines:
            liushen = line.get("liushen")
            if not liushen:
                continue
            info = LIUSHEN_INFO.get(liushen)
            if not info:
                continue
            char, wuxing = info
            line_idx = line["position"] - 1

            fill_color = get_liushen_fill(liushen, is_dark)

            if liushen == "白虎":
                if is_dark:
                    markers.append((line_idx, char, "#cccccc", False, "#1d1d1f"))
                else:
                    markers.append((line_idx, char, "#2c2c2e"))
            else:
                markers.append((line_idx, char, fill_color))
        self._liushen_marker.set_markers(markers)

    @staticmethod
    def _is_system_dark_mode() -> bool:
        app = QApplication.instance()
        if app:
            return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
        return False

    def _update_shiying_markers(self, result: dict):
        """填充世/应 + 主事爻标注（同一列）"""
        lines = result.get("lines", [])
        markers = []
        for line in lines:
            sy = line.get("shi_ying")
            pos = line["position"]
            line_idx = pos - 1
            if sy:
                if (self._zhushiyao_line and
                        pos == self._zhushiyao_line):
                    color = ZHUSHI_COLOR
                else:
                    color = TI_COLOR if sy == "世" else YONG_COLOR
                markers.append((line_idx, sy, color))
            elif (self._zhushiyao_line and
                  pos == self._zhushiyao_line):
                markers.append((line_idx, "主", ZHUSHI_COLOR))
        self._shiying_marker.set_markers(markers)

    def _update_dongyao_markers(self, ben_data: dict, changing_lines: list[int]):
        if not changing_lines:
            self._dongyao_marker.set_badge_mode(False)
            self._dongyao_marker.set_markers([
                (3, "安", self._text_color),
                (2, "静", self._text_color),
            ])
            return

        self._dongyao_marker.set_badge_mode(True)
        binary = ben_data.get("binary", "111111")
        markers = []
        for cl in changing_lines:
            line_idx = cl - 1
            is_yang = binary[line_idx] == "1"
            mark = "○" if is_yang else "×"
            if self._zhushiyao_line == cl:
                color = ZHUSHI_COLOR if is_yang else ZHUSHI_X_COLOR
            else:
                color = O_COLOR if is_yang else X_COLOR
            markers.append((line_idx, mark, color))
        self._dongyao_marker.set_markers(markers)

    def _update_nayin_items(self, result: dict):
        """填充纳音标注 — 边框颜色始终使用地支五行"""
        lines = result.get("lines", [])
        items = []
        for line in lines:
            line_idx = line["position"] - 1
            text = _format_nayin_text(line, self._compact)
            zhi_wx = line.get("dizhi_wuxing", "")
            border_color = get_wuxing_base_color(zhi_wx)
            items.append((line_idx, text, border_color))
        self._nayin_label.set_items(items)

    def _update_fushen_items(self):
        """填充伏神到 drawer 爻线下方/上方（小字加粗，自动适配间距）

        初爻(索引0)伏神显示在1/2爻之间用⬇️，其他爻显示在下方用⬆️
        """
        texts = [None] * 6
        for i, fs in enumerate(self._fushen_data):
            if fs is not None:
                arrow = "⬇️ " if i == 0 else "⬆️ "
                texts[i] = f"{arrow}{_format_fushen_text(fs)}"
        if self._drawer:
            self._drawer.set_fushen_texts(texts, font_size_offset=-5,
                                          color=self._text_color, bold=True)
        self._update_fushen_highlight()

    def _update_fushen_highlight(self):
        """根据主事爻和伏神数据，设置 drawer 的伏神高亮行"""
        if not self._drawer:
            return
        if self._zhushiyao_line and self._fushen_data:
            pos = self._zhushiyao_line - 1
            if 0 <= pos < 6 and self._fushen_data[pos] is not None:
                self._drawer.set_fushen_highlight(pos)
                return
        self._drawer.set_fushen_highlight(None)

    def _update_type_badges(self, gua_name: str):
        """更新卦类型标签方块（冲/合/游/归/反/伏）— 基于单卦内部结构，不依赖变卦/动爻"""
        fy_result = check_hexagram_fanyin_fuyin(gua_name)
        fanyin_type = fy_result.get("fanyin_type", "")
        fuyin_type = fy_result.get("fuyin_type", "")

        # 八纯卦：六冲优先于伏吟（避免冲+伏同时显示）
        if fuyin_type and get_gua_type_tags(gua_name) == "冲":
            fuyin_type = ""

        badges = get_gua_type_badges(gua_name, fanyin_type, fuyin_type)
        if self._type_badge_bar:
            self._type_badge_bar.set_badges(badges, self._font_size)

    # ═══════════════════════════════════════════════════════════
    #  主事爻
    # ═══════════════════════════════════════════════════════════

    def eventFilter(self, obj, event):
        if obj == self._drawer and event.type() in (QEvent.Type.MouseButtonPress,
                                                     QEvent.Type.MouseButtonDblClick):
            self._on_line_clicked(event)
            return True
        return super().eventFilter(obj, event)

    def _on_line_clicked(self, event):
        """处理 drawer 点击 — 选择主事爻"""
        if not self._liuyao_result:
            return
        y = event.pos().y()
        lh = self._drawer.line_h
        name_h = self._drawer.name_area_h
        offset_y = self._drawer._offset_y
        y_adj = y - offset_y
        if y_adj < name_h:
            return
        line_idx = 5 - (y_adj - name_h) // lh
        if 0 <= line_idx <= 5:
            new_val = line_idx + 1
            if self._zhushiyao_line == new_val:
                self._zhushiyao_line = 0  # 再次点击同一爻 → 取消选择
            else:
                self._zhushiyao_line = new_val
            self._update_zhushi_markers()
            self._update_fushen_highlight()
            self._update_container_widths()
            self._show_zhushiyao_status()

    def _update_zhushi_markers(self):
        """刷新世应标注（已内含主事爻'主'字）和动爻标注（颜色联动）"""
        if self._liuyao_result:
            self._update_shiying_markers(self._liuyao_result)
        if self._ben_data and self._changing_lines is not None:
            self._update_dongyao_markers(self._ben_data, self._changing_lines)

    def _show_zhushiyao_status(self):
        """在状态栏显示主事爻信息（取消旧定时器防堆积）"""
        if not self._liuyao_result:
            return
        mgr = getattr(self.window(), "_statusbar_mgr", None)
        if not mgr:
            return
        if self._status_timer is not None:
            self._status_timer.stop()
            self._status_timer.deleteLater()
            self._status_timer = None
        if self._zhushiyao_line:
            liuqin = ""
            for line in self._liuyao_result.get("lines", []):
                if line["position"] == self._zhushiyao_line:
                    liuqin = line.get("liuqin", "")
                    break
            if liuqin:
                mgr.show_status(f"[Info] 设置主事爻为 {liuqin}")
        else:
            mgr.show_status("[Info] 已取消主事爻")
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(mgr.reset_status)
        self._status_timer.start(5000)

    # ═══════════════════════════════════════════════════════════
    #  标注宽度计算
    # ═══════════════════════════════════════════════════════════

    def _recalc_all_marker_widths(self):
        self._recalc_liushen_width()
        self._recalc_shiying_width()
        self._recalc_dongyao_width()

    def _calc_badge_side(self, fs: int) -> int:
        """
        计算 badge 模式下正方形的边长（不含 marker 额外边距）

        Args:
            fs: 字号（含偏移）

        Returns:
            int: 正方形边长 px
        """
        font = _app_font()
        font.setPointSize(fs)
        font.setBold(True)
        fm = QFontMetrics(font)
        return int(fm.height() + 2 * self._badge_padding)

    def _recalc_liushen_width(self):
        font = _app_font()
        font.setPointSize(self._font_size + self._fs_offset_liushen)
        font.setBold(True)
        fm = QFontMetrics(font)
        w = int(fm.height() + 2 * self._badge_padding)
        self._liushen_marker_w = w
        if self._liushen_marker:
            self._liushen_marker.setFixedWidth(w)

    def _recalc_shiying_width(self):
        font = _app_font()
        font.setPointSize(self._font_size + self._fs_offset_shiying)
        font.setBold(True)
        fm = QFontMetrics(font)
        w = int(fm.height() + 2 * self._badge_padding)
        self._shiying_marker_w = w
        if self._shiying_marker:
            self._shiying_marker.setFixedWidth(w)

    def _recalc_dongyao_width(self):
        font = _app_font()
        font.setPointSize(self._font_size + self._fs_offset_dongyao)
        font.setBold(True)
        fm = QFontMetrics(font)
        w = int(fm.height() + 2 * self._badge_padding)
        self._dongyao_marker_w = w
        if self._dongyao_marker:
            self._dongyao_marker.setFixedWidth(w)

    def _update_container_widths(self):
        """更新左/右/变卦 固定宽度容器的尺寸（字号/内容变更后调用）"""
        left_total = (self._liushen_marker_w + self._gap_liushen_to_shiying +
                      self._shiying_marker_w)
        if self._compact_btn:
            btn_w = self._compact_btn.width()
            badge_offset = self._btn_wrapper.contentsMargins().left()
            left_w = max(left_total, btn_w + badge_offset)
        else:
            left_w = left_total
        if hasattr(self, '_left_container') and self._left_container:
            self._left_container.setFixedWidth(left_w)

        if hasattr(self, '_right_container') and self._right_container:
            nayin_w = self._nayin_label._fixed_w if self._nayin_label else 80
            right_total = self._dongyao_marker_w + self._gap_dongyao_to_nayin + nayin_w
            self._right_container.setFixedWidth(right_total)

        if hasattr(self, '_bian_right_container') and self._bian_right_container:
            bian_nayin_w = self._bian_nayin_label._fixed_w if self._bian_nayin_label else 80
            self._bian_right_container.setFixedWidth(bian_nayin_w)
