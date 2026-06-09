"""
六爻面板 — 主卦 + 六神/世应/卦图/动爻/纳音 多列注解 + 卦辞/爻辞解读

═══════════════════════════════════════════════════════════════
文件职责：提供 LiuyaoPanel 组件，根据起卦结果显示六爻纳甲断卦界面
═══════════════════════════════════════════════════════════════

布局结构：
  ┌─ LiuyaoPanel ───────────────────────────────────────────────┐
  │  甲子年 丙寅月 甲子日 子时  [现在] [修改]                    │
  │                                                              │
  │  [六神] [世应] [HexagramDrawer] [动爻o/x] [纳音]            │
  │   青     世       ████            ○      妻财甲寅木          │
  │   朱              ████            ×      官鬼丙午火          │
  │   勾     应       ████                   父母壬戌土          │
  │   ...             ████                   ...                 │
  │  ┌─ 蓝/橙色方块 ───────────────────────────────────────┐   │
  │  │ 爻辞/卦辞 + 小象/彖曰                                   │   │
  │  └──────────────────────────────────────────────────────┘   │
  └──────────────────────────────────────────────────────────────┘
"""
import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QFrame, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics, QColor, QPen, QPainter

from ..hexagram_drawer import HexagramDrawer, _app_font
from ..CONST_DEFINE_UI import LiuyaoConfig
from ...data.Color_Wuxing import TI_COLOR, YONG_COLOR, O_COLOR, X_COLOR
from ...algorithms.liuyao import analyze_gua

# ── 从 common 导入公共组件 ──
from .common import (_LineMarker, is_light_color, build_interpretation)


# ═══════════════════════════════════════════════════════════════
#  六神 → (显示单字, 五行填充颜色)
#  白虎颜色在运行时根据背景明暗动态计算
# ═══════════════════════════════════════════════════════════════

LIUSHEN_CHAR_MAP: dict[str, tuple[str, str | None]] = {
    "青龙": ("龙", "#27ae60"),   # 木 — 绿底白字
    "朱雀": ("雀", "#e74c3c"),   # 火 — 红底白字
    "勾陈": ("陈", "#d4a017"),   # 土 — 黄底白字
    "螣蛇": ("蛇", "#d4a017"),   # 土 — 黄底白字
    "白虎": ("虎", None),        # 金 — 透明底+文字色边框（运行时计算）
    "玄武": ("玄", "#3498db"),   # 水 — 蓝底白字
}


# ═══════════════════════════════════════════════════════════════
#  地支五行 → 纳音边框颜色
# ═══════════════════════════════════════════════════════════════

_DIZHI_WUXING_BORDER_COLORS: dict[str, str] = {
    "木": "#27ae60",
    "火": "#e74c3c",
    "土": "#d4a017",
    "金": "#C47A55",
    "水": "#3498db",
}


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
        self._fixed_w = 80  # 默认宽度

    def configure(self, name_area_h: int, line_h: int, offset_y: int = 0,
                  font_size: int = 16):
        """匹配关联 drawer 的几何参数，确保与爻行对齐"""
        self._name_area_h = name_area_h
        self._line_h = line_h
        self._offset_y = offset_y
        self._font_size = font_size
        self.setFixedHeight(name_area_h + 6 * line_h)

    def set_border_width(self, px: int):
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
        """根据最宽文字计算固定宽度"""
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
            badge_h = text_h + 2 * pad + 2 * bw
            badge_top = int(center_y - badge_h // 2)
            badge_x = 0  # 左对齐

            # 彩色边框 + 透明填充
            p.setPen(QPen(border_color, bw))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(badge_x, badge_top, badge_w, badge_h, 6, 6)

            # 文字用当前文字颜色
            p.setPen(QColor(self._text_color))
            text_x = badge_x + pad + bw
            baseline_y = badge_top + (badge_h + fm.ascent() - fm.descent()) // 2
            p.drawText(int(text_x), int(baseline_y), text)

        p.end()


# ═══════════════════════════════════════════════════════════════
#  LiuyaoPanel — 六爻主面板
# ═══════════════════════════════════════════════════════════════

class LiuyaoPanel(QWidget):
    """
    六爻面板 — 主卦 + 六神/世应/卦图/动爻/纳音 多列注解

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
        self._badge_padding = LiuyaoConfig.badge_padding
        self._nayin_border_width = LiuyaoConfig.nayin_border_width
        self._nayin_padding = LiuyaoConfig.nayin_padding
        self._fs_offset_liushen = LiuyaoConfig.fs_offset_liushen
        self._fs_offset_shiying = LiuyaoConfig.fs_offset_shiying
        self._fs_offset_dongyao = LiuyaoConfig.fs_offset_dongyao
        self._fs_offset_nayin = LiuyaoConfig.fs_offset_nayin

        # 数据状态
        self._liuyao_result = None
        self._changing_lines: list[int] = []
        self._ben_data = None
        self._current_ganzhi: dict | None = None

        # Widget 引用（_init_ui 中创建）
        self._drawer = None
        self._liushen_marker = None
        self._shiying_marker = None
        self._dongyao_marker = None
        self._nayin_label = None
        self._interpret_frame = None
        self._interpret_label = None
        self._liushen_marker_w = 0
        self._shiying_marker_w = 0
        self._dongyao_marker_w = 0

        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 创建 drawer ──
        self._drawer = HexagramDrawer()
        self._drawer.set_custom_title(None)  # 初始不显示标题
        lh = self._drawer.line_h
        name_h = self._drawer.name_area_h

        g = self._gap_marker_to_drawer

        # ── 六神标注（左1，badge 模式，右对齐）──
        self._liushen_marker = _LineMarker(align_right=True)
        self._liushen_marker.configure(name_h, lh, font_size=self._font_size)
        self._liushen_marker.set_badge_mode(True)
        self._liushen_marker.set_badge_padding_ox(self._badge_padding)
        self._liushen_marker.set_fs_offset(self._fs_offset_liushen)

        # ── 世应标注（左2，badge 模式，右对齐）──
        self._shiying_marker = _LineMarker(align_right=True)
        self._shiying_marker.configure(name_h, lh, font_size=self._font_size)
        self._shiying_marker.set_badge_mode(True)
        self._shiying_marker.set_badge_padding_ox(self._badge_padding)
        self._shiying_marker.set_fs_offset(self._fs_offset_shiying)

        # ── 动爻标注（右1，badge 模式，左对齐）──
        self._dongyao_marker = _LineMarker(align_right=False)
        self._dongyao_marker.configure(name_h, lh, font_size=self._font_size)
        self._dongyao_marker.set_badge_mode(True)
        self._dongyao_marker.set_badge_padding_ox(self._badge_padding)
        self._dongyao_marker.set_fs_offset(self._fs_offset_dongyao)

        # ── 纳音标注（右2，文字+彩色边框，左对齐）──
        self._nayin_label = _NayinLabel()
        self._nayin_label.configure(name_h, lh, font_size=self._font_size)
        self._nayin_label.set_border_width(self._nayin_border_width)
        self._nayin_label.set_padding(self._nayin_padding)

        # ── 计算标注宽度 ──
        self._recalc_all_marker_widths()

        # ── 主卦行：5列标注 + drawer ──
        main_row = QHBoxLayout()
        main_row.setContentsMargins(self._gap_liuyao_left, 0, self._gap_liuyao_right, 0)
        main_row.setSpacing(0)

        # 左列：六神 + 间距 + 世应
        main_row.addWidget(self._liushen_marker)
        main_row.addSpacing(self._gap_liushen_to_shiying)
        main_row.addWidget(self._shiying_marker)

        # 世应右边缘 → drawer 左边缘
        main_row.addSpacing(g)

        # Drawer
        main_row.addWidget(self._drawer)

        # drawer 右边缘 → 动爻左边缘
        main_row.addSpacing(g)

        # 右列：动爻 + 间距 + 纳音
        main_row.addWidget(self._dongyao_marker)
        main_row.addSpacing(self._gap_dongyao_to_nayin)
        main_row.addWidget(self._nayin_label)

        main_row.addStretch()
        root.addLayout(main_row)

        # 提升 marker 层级，防止被 drawer 遮挡
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
        interp_layout.addWidget(self._interpret_label)
        root.addWidget(self._interpret_frame)

        root.addStretch()

    # ═══════════════════════════════════════════════════════════
    #  公共接口
    # ═══════════════════════════════════════════════════════════

    def set_time_ganzhi(self, ganzhi: dict):
        """
        接收 SuanguaPanel 传入的干支时间

        Args:
            ganzhi: 干支 dict (year_ganzhi, month_ganzhi, day_ganzhi, day_gan, hour_ganzhi)
        """
        self._current_ganzhi = ganzhi
        # 如果已有卦数据，用新时间重新分析
        if self._ben_data and self._changing_lines is not None:
            self._refresh_analysis()

    def _refresh_analysis(self):
        """根据当前卦数据和干支时间重新计算六爻内容"""
        gua_name = self._ben_data.get("full_name", "")
        day_gan = self._current_ganzhi["day_gan"]
        result = analyze_gua(gua_name, day_gan)
        if "error" in result:
            return
        self._liuyao_result = result
        self._update_liushen_markers(result)
        self._update_shiying_markers(result)
        self._update_dongyao_markers(self._ben_data, self._changing_lines)
        self._update_nayin_items(result)
        self._update_interpretation()

    def set_gua_result(self, ben_data: dict, changing_lines: list[int]):
        """
        根据本卦数据和动爻列表更新六爻面板全部内容

        Args:
            ben_data: 本卦数据库 dict (from hexagram_loader)
            changing_lines: 动爻列表 (1=初爻..6=上爻)
        """
        self._ben_data = ben_data
        self._changing_lines = changing_lines

        # 六爻分析（时间由 SuanguaPanel.set_time_ganzhi 保证已传入）
        gua_name = ben_data.get("full_name", "")
        day_gan = self._current_ganzhi["day_gan"] if self._current_ganzhi else "甲"
        result = analyze_gua(gua_name, day_gan)
        if "error" in result:
            return
        self._liuyao_result = result

        # ── 更新 drawer ──
        binary = ben_data.get("binary", "111111")
        yang = [c == "1" for c in binary]
        self._drawer.set_lines(yang)
        self._drawer.set_disabled_look(False)
        self._drawer.set_custom_title(f"主-{gua_name}")

        # ── 更新标注 ──
        self._update_liushen_markers(result)
        self._update_shiying_markers(result)
        self._update_dongyao_markers(ben_data, changing_lines)
        self._update_nayin_items(result)

        # ── 底部卦辞/爻辞解读 ──
        self._update_interpretation()

    def _update_interpretation(self):
        """根据当前卦数据和动爻更新底部解读方块"""
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

    def set_font_size(self, font_size: int):
        self._font_size = font_size
        if self._drawer:
            self._drawer.set_font_size(font_size)
            self._drawer.set_name_fs(self._fs_name)

        lh = self._drawer.line_h if self._drawer else 40
        name_h = self._drawer.name_area_h if self._drawer else 16

        # 重新配置标注
        if self._liushen_marker:
            self._liushen_marker.configure(name_h, lh, font_size=font_size)
            self._liushen_marker.set_font_size(font_size)
            self._liushen_marker.set_fs_offset(self._fs_offset_liushen)
            self._liushen_marker.set_badge_padding_ox(self._badge_padding)

        if self._shiying_marker:
            self._shiying_marker.configure(name_h, lh, font_size=font_size)
            self._shiying_marker.set_font_size(font_size)
            self._shiying_marker.set_fs_offset(self._fs_offset_shiying)
            self._shiying_marker.set_badge_padding_ox(self._badge_padding)

        if self._dongyao_marker:
            self._dongyao_marker.configure(name_h, lh, font_size=font_size)
            self._dongyao_marker.set_font_size(font_size)
            self._dongyao_marker.set_fs_offset(self._fs_offset_dongyao)
            self._dongyao_marker.set_badge_padding_ox(self._badge_padding)

        if self._nayin_label:
            self._nayin_label.configure(name_h, lh, font_size=font_size)
            self._nayin_label.set_border_width(self._nayin_border_width)
            self._nayin_label.set_padding(self._nayin_padding)

        self._recalc_all_marker_widths()

        # 字体变化需重建解读 HTML（内嵌 font-size）
        self._update_interpretation()

    def set_text_color(self, text_color: str):
        self._text_color = text_color
        if self._drawer:
            self._drawer.set_text_color(text_color)
        for m in [self._liushen_marker, self._shiying_marker, self._dongyao_marker]:
            if m:
                m.set_text_color(text_color)
        if self._nayin_label:
            self._nayin_label.set_text_color(text_color)
        # 白虎颜色依赖 text_color，需刷新六神标注
        if self._liuyao_result:
            self._update_liushen_markers(self._liuyao_result)

    def set_fs_name(self, offset: int):
        self._fs_name = offset
        if self._drawer:
            self._drawer.set_name_fs(offset)

    def compute_min_width(self) -> int:
        """
        计算六爻面板的最小宽度

        Returns:
            int: 面板最小宽度（像素）
        """
        g = self._gap_marker_to_drawer
        dw = self._drawer.minimumWidth() if self._drawer else 100
        nayin_w = self._nayin_label._fixed_w if self._nayin_label else 80

        left_w = (self._liushen_marker_w + self._gap_liushen_to_shiying +
                  self._shiying_marker_w)
        right_w = self._dongyao_marker_w + self._gap_dongyao_to_nayin + nayin_w

        return (self._gap_liuyao_left + left_w + g + dw + g + right_w +
                self._gap_liuyao_right)

    def configure(self,
                  gap_liuyao_left: int | None = None,
                  gap_liuyao_right: int | None = None,
                  gap_marker_to_drawer: int | None = None,
                  gap_liushen_to_shiying: int | None = None,
                  gap_dongyao_to_nayin: int | None = None,
                  badge_padding: int | None = None,
                  nayin_border_width: int | None = None,
                  nayin_padding: int | None = None,
                  fs_offset_liushen: int | None = None,
                  fs_offset_shiying: int | None = None,
                  fs_offset_dongyao: int | None = None,
                  fs_offset_nayin: int | None = None):
        """外部可调整的布局参数"""
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
        if badge_padding is not None:
            self._badge_padding = badge_padding
        if nayin_border_width is not None:
            self._nayin_border_width = nayin_border_width
            if self._nayin_label:
                self._nayin_label.set_border_width(nayin_border_width)
        if nayin_padding is not None:
            self._nayin_padding = nayin_padding
            if self._nayin_label:
                self._nayin_label.set_padding(nayin_padding)
        if fs_offset_liushen is not None:
            self._fs_offset_liushen = fs_offset_liushen
        if fs_offset_shiying is not None:
            self._fs_offset_shiying = fs_offset_shiying
        if fs_offset_dongyao is not None:
            self._fs_offset_dongyao = fs_offset_dongyao
        if fs_offset_nayin is not None:
            self._fs_offset_nayin = fs_offset_nayin

        # 更新 marker 边距
        self._recalc_all_marker_widths()

    # ═══════════════════════════════════════════════════════════
    #  标注更新
    # ═══════════════════════════════════════════════════════════

    def _update_liushen_markers(self, result: dict):
        """填充六神标注：单字 + 五行颜色 badge"""
        lines = result.get("lines", [])
        # 检测系统颜色模式
        is_dark = self._is_system_dark_mode()

        markers = []
        for line in lines:
            liushen = line.get("liushen")
            if not liushen:
                continue
            char, fill_color = LIUSHEN_CHAR_MAP.get(liushen, (liushen[0], None))
            line_idx = line["position"] - 1  # 1-based → 0-based

            if liushen == "白虎":
                # 白虎：填充badge，颜色跟随系统主题
                #   亮底→暗填充+白字，暗底→亮填充+暗字
                if is_dark:
                    markers.append((line_idx, char, "#cccccc", False, "#1d1d1f"))
                else:
                    markers.append((line_idx, char, "#2c2c2e"))
            else:
                markers.append((line_idx, char, fill_color or "#999999"))
        self._liushen_marker.set_markers(markers)

    @staticmethod
    def _is_system_dark_mode() -> bool:
        """检测系统是否为深色模式"""
        app = QApplication.instance()
        if app:
            return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
        return False

    def _update_shiying_markers(self, result: dict):
        """填充世应标注：世=红，应=蓝"""
        lines = result.get("lines", [])
        markers = []
        for line in lines:
            sy = line.get("shi_ying")
            if not sy:
                continue
            line_idx = line["position"] - 1
            color = TI_COLOR if sy == "世" else YONG_COLOR
            markers.append((line_idx, sy, color))
        self._shiying_marker.set_markers(markers)

    def _update_dongyao_markers(self, ben_data: dict, changing_lines: list[int]):
        """填充动爻标注：0动爻→"安静"，>0→多个 o/x badge"""
        if not changing_lines:
            # 静卦：普通文字模式显示"安静"
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
            line_idx = cl - 1  # 1-based → 0-based
            is_yang = binary[line_idx] == "1"
            mark = "○" if is_yang else "×"
            color = O_COLOR if is_yang else X_COLOR
            markers.append((line_idx, mark, color))
        self._dongyao_marker.set_markers(markers)

    def _update_nayin_items(self, result: dict):
        """填充纳音标注："妻财甲寅木" + 五行边框颜色"""
        lines = result.get("lines", [])
        items = []
        for line in lines:
            line_idx = line["position"] - 1
            text = f"{line['liuqin']}{line['najia']}{line['dizhi_wuxing']}"
            zhi_wx = line.get("dizhi_wuxing", "")
            border_color = _DIZHI_WUXING_BORDER_COLORS.get(zhi_wx, self._text_color)
            items.append((line_idx, text, border_color))
        self._nayin_label.set_items(items)

    # ═══════════════════════════════════════════════════════════
    #  标注宽度计算
    # ═══════════════════════════════════════════════════════════

    def _recalc_all_marker_widths(self):
        self._recalc_liushen_width()
        self._recalc_shiying_width()
        self._recalc_dongyao_width()

    def _recalc_liushen_width(self):
        """六神 badge 宽度：正方形 = fm高度 + 2*pad + 安全边距"""
        font = _app_font()
        font.setPointSize(self._font_size + self._fs_offset_liushen)
        font.setBold(True)
        fm = QFontMetrics(font)
        w = int(fm.height() + 2 * self._badge_padding + 4)
        self._liushen_marker_w = w
        if self._liushen_marker:
            self._liushen_marker.setFixedWidth(w)

    def _recalc_shiying_width(self):
        """世应 badge 宽度"""
        font = _app_font()
        font.setPointSize(self._font_size + self._fs_offset_shiying)
        font.setBold(True)
        fm = QFontMetrics(font)
        w = int(fm.height() + 2 * self._badge_padding + 4)
        self._shiying_marker_w = w
        if self._shiying_marker:
            self._shiying_marker.setFixedWidth(w)

    def _recalc_dongyao_width(self):
        """动爻 badge 宽度"""
        font = _app_font()
        font.setPointSize(self._font_size + self._fs_offset_dongyao)
        font.setBold(True)
        fm = QFontMetrics(font)
        w = int(fm.height() + 2 * self._badge_padding + 4)
        self._dongyao_marker_w = w
        if self._dongyao_marker:
            self._dongyao_marker.setFixedWidth(w)

