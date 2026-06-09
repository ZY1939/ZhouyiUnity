"""
梅花易数面板 — 本卦/互卦/变卦 横向排列 + 体用/o/x 标注 + 爻辞/卦辞解读

═══════════════════════════════════════════════════════════════
文件职责：提供 MeihuaPanel 组件，根据起卦结果显示梅花易数断卦界面
═══════════════════════════════════════════════════════════════

布局结构：
  ┌─ MeihuaPanel ──────────────────────────────────────────┐
  │  本-乾为天        互-乾为天        变-天风姤            │
  │  [左标注] [卦图]   [左标注] [卦图]   [左标注] [卦图] [右标注] │
  │  ┌─ 蓝/橙色方块 ───────────────────────────────────┐  │
  │  │ 爻辞/卦辞 + 小象/彖曰                              │  │
  │  └──────────────────────────────────────────────────┘  │
  └──────────────────────────────────────────────────────────┘
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics

from ..hexagram_drawer import HexagramDrawer, _app_font
from ..hexagram_loader import get_gua_by_xiantian
from ..hexagram_calc import _yang_to_xiantian
from ..bagua import XIANTIAN
from ..CONST_DEFINE_UI import MeihuaConfig
from ...data.Color_Wuxing import (get_wuxing_color_by_xiantian, TI_COLOR, YONG_COLOR,
                                   O_COLOR, X_COLOR)
from .common import _LineMarker, is_light_color, line_name, build_interpretation


class MeihuaPanel(QWidget):
    """
    梅花易数面板 — 本卦/互卦/变卦 三卦横向布局 + 爻辞/卦辞解读

    根据动爻数量自动切换展示模式：
      - 1 动爻: 显示体用/o/x 标注 + 蓝色方块爻辞+小象
      - 0 动爻: 变卦变灰禁用 + 橙色方块卦辞+彖曰
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_size = 16
        self._text_color = "#1d1d1f"
        self._fs_name = MeihuaConfig.fs_name

        self._ben_drawer = None      # 本卦
        self._hu_drawer = None       # 互卦
        self._bian_drawer = None     # 变卦

        self._ben_left = None        # 本卦左标注（体/用）
        self._ben_right = None       # 本卦右标注（o/x 动爻标记）
        self._hu_left = None         # 互卦左标注（八卦名）

        self._interpret_frame = None  # 底部蓝色/橙色解读方块
        self._interpret_label = None

        self._current_ganzhi: dict | None = None  # 由 SuanguaPanel 传入

        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 创建 3 个 drawer ──
        self._ben_drawer = HexagramDrawer()
        self._hu_drawer = HexagramDrawer()
        self._bian_drawer = HexagramDrawer()

        lh = self._ben_drawer.line_h
        name_h = self._ben_drawer.name_area_h
        dw = self._ben_drawer.minimumWidth()  # drawer 宽度

        # ── 可调参数（集中定义在 CONST_DEFINE_UI.py → MeihuaConfig）──
        self._gap_meihua_left = MeihuaConfig.gap_meihua_left
        self._gap_meihua_right = MeihuaConfig.gap_meihua_right
        self._gap_marker_to_drawer = MeihuaConfig.gap_marker_to_drawer
        self._fs_offset_ox = MeihuaConfig.fs_offset_ox
        self._fs_offset_tiyong = MeihuaConfig.fs_offset_tiyong
        self._gap_between_columns = MeihuaConfig.gap_between_columns
        self._gap_marker_to_marker = MeihuaConfig.gap_marker_to_marker
        self._badge_padding_ox = MeihuaConfig.badge_padding_ox

        g = self._gap_marker_to_drawer
        # ── 标注宽度：根据 badge 正方形尺寸动态计算，+4 安全边距 ──
        # 右标注 (○/× 符号)
        tmp_font_r = _app_font()
        tmp_font_r.setPointSize(self._font_size + self._fs_offset_ox)
        tmp_font_r.setBold(True)
        tmp_fm_r = QFontMetrics(tmp_font_r)
        self._right_marker_w = int(tmp_fm_r.height() + 2 * self._badge_padding_ox + 4)
        # 左标注 (体/用/八卦名)
        tmp_font_l = _app_font()
        tmp_font_l.setPointSize(self._font_size + self._fs_offset_tiyong)
        tmp_font_l.setBold(True)
        tmp_fm_l = QFontMetrics(tmp_font_l)
        self._left_marker_w = int(tmp_fm_l.height() + 2 * self._badge_padding_ox + 4)
        # ben_row: left(L) + g + drawer + g + right(R) = L+R+2g + dw
        # hu_row:  left(L) + g + drawer + right_spacer = L+R+2g + dw
        # bian_row: left_spacer(L+R+2g) + drawer = L+R+2g + dw
        self._col_pad = self._left_marker_w + self._right_marker_w + 2 * g
        self._col_w = self._col_pad + dw  # 单列总宽（含标注）

        # ── 三列 水平排列（固定间距 + 右侧 stretch 吸收额外空间）──
        top_area = QHBoxLayout()
        top_area.setContentsMargins(self._gap_meihua_left, 0, self._gap_meihua_right, 0)
        top_area.setSpacing(0)

        # ── 本卦列：左标注(体/用,右对齐) + gap + drawer + gap + 右标注(o/x,左对齐) ──
        ben_row = QHBoxLayout()
        ben_row.setSpacing(0)
        self._ben_left = _LineMarker(align_right=True)
        self._ben_left.setFixedWidth(self._left_marker_w)
        self._ben_left.configure(name_h, lh, font_size=self._font_size)
        self._ben_left.set_fs_offset(self._fs_offset_tiyong)
        self._ben_left.set_badge_mode(True)
        self._ben_left.set_badge_padding_ox(self._badge_padding_ox)
        ben_row.addWidget(self._ben_left)
        ben_row.addSpacing(g)  # 体/用文字右边缘 → 卦图左边缘
        ben_row.addWidget(self._ben_drawer)
        ben_row.addSpacing(g)  # 卦图右边缘 → o/x文字左边缘
        self._ben_right = _LineMarker(align_right=False)
        self._ben_right.setFixedWidth(self._right_marker_w)
        self._ben_right.configure(name_h, lh, font_size=self._font_size)
        self._ben_right.set_fs_offset(self._fs_offset_ox)
        self._ben_right.set_badge_mode(True)
        self._ben_right.set_badge_padding_ox(self._badge_padding_ox)
        ben_row.addWidget(self._ben_right)
        top_area.addLayout(ben_row)

        # 本卦↔互卦 列间距（取标注最小间距和额外间距的最大值）
        self._gap1_spacer_idx = top_area.count()
        top_area.addSpacing(max(self._gap_marker_to_marker, self._gap_between_columns))

        # ── 互卦列：左标注(八卦名,右对齐) + gap + drawer ──
        hu_row = QHBoxLayout()
        hu_row.setSpacing(0)
        self._hu_left = _LineMarker(align_right=True)
        self._hu_left.setFixedWidth(self._left_marker_w)
        self._hu_left.configure(name_h, lh, font_size=self._font_size)
        self._hu_left.set_fs_offset(self._fs_offset_tiyong)
        self._hu_left.set_badge_mode(True)
        self._hu_left.set_badge_padding_ox(self._badge_padding_ox)
        hu_row.addWidget(self._hu_left)
        hu_row.addSpacing(g)  # 八卦名文字右边缘 → 卦图左边缘
        hu_row.addWidget(self._hu_drawer)
        # 右补间距统一列宽
        hu_row.addSpacing(self._col_pad - (self._left_marker_w + g))
        top_area.addLayout(hu_row)

        # 互卦↔变卦 列间距（取标注最小间距和额外间距的最大值）
        self._gap2_spacer_idx = top_area.count()
        top_area.addSpacing(max(self._gap_marker_to_marker, self._gap_between_columns))

        # ── 变卦列：仅 drawer（自然宽度，不加填充）──
        bian_row = QHBoxLayout()
        bian_row.setSpacing(0)
        bian_row.addWidget(self._bian_drawer)
        top_area.addLayout(bian_row)
        # 右侧 stretch：吸收所有额外空间，使三卦自然靠左
        top_area.addStretch(1)

        root.addLayout(top_area)

        # marker 提到最前层，防止被 drawer 遮挡
        for m in [self._ben_left, self._ben_right, self._hu_left]:
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

    def set_time_ganzhi(self, ganzhi: dict):
        """
        接收 SuanguaPanel 传入的干支时间

        梅花面板当前不依赖时间做分析，预留接口供未来扩展。

        Args:
            ganzhi: 干支 dict (year_ganzhi, month_ganzhi, day_ganzhi, day_gan, hour_ganzhi)
        """
        self._current_ganzhi = ganzhi

    def compute_min_width(self) -> int:
        """
        计算梅花面板的最小宽度（px）

        公式:
          col_w = col_pad + drawer_w  （本卦/互卦单列含标注宽度）
          变卦列 = drawer_w（自然宽度，无标注）
          spacer = max(gap_marker_to_marker, gap_between_columns)
          min_w = gap_meihua_left + 2 * col_w + drawer_w + 2 * spacer + gap_meihua_right

        Returns:
            int: 面板最小宽度（像素）
        """
        dw = self._ben_drawer.minimumWidth() if self._ben_drawer else 100
        col_w = self._col_pad + dw
        spacer = max(self._gap_marker_to_marker, self._gap_between_columns)
        return self._gap_meihua_left + 2 * col_w + dw + 2 * spacer + self._gap_meihua_right

    def set_font_size(self, font_size: int):
        self._font_size = font_size
        for drawer in [self._ben_drawer, self._hu_drawer, self._bian_drawer]:
            if drawer:
                drawer.set_font_size(font_size)
        lh = self._ben_drawer.line_h
        name_h = self._ben_drawer.name_area_h

        for marker in [self._ben_left, self._hu_left]:
            if marker:
                marker.configure(name_h, lh, font_size=font_size)
                marker.set_font_size(font_size)
                marker.set_fs_offset(self._fs_offset_tiyong)
                marker.set_badge_padding_ox(self._badge_padding_ox)
        if self._ben_right:
            self._ben_right.configure(name_h, lh, font_size=font_size)
            self._ben_right.set_font_size(font_size)
            self._ben_right.set_fs_offset(self._fs_offset_ox)
            self._ben_right.set_badge_padding_ox(self._badge_padding_ox)

        self._recalc_col_dims()

        # DEBUG: 打印最小宽度
        import os
        if os.environ.get("ZY_DEBUG"):
            print(f"[DEBUG MeihuaPanel.set_font_size] font_size={font_size} col_pad={self._col_pad} col_w={self._col_w} min_w={self.compute_min_width()}", flush=True)

    def set_text_color(self, text_color: str):
        self._text_color = text_color
        for drawer in [self._ben_drawer, self._hu_drawer, self._bian_drawer]:
            if drawer:
                drawer.set_text_color(text_color)
        for marker in [self._ben_left, self._ben_right, self._hu_left]:
            if marker:
                marker.set_text_color(text_color)

    def set_fs_name(self, offset: int):
        self._fs_name = offset
        for drawer in [self._ben_drawer, self._hu_drawer, self._bian_drawer]:
            if drawer:
                drawer.set_name_fs(offset)

    def configure(self, gap_meihua_left: int | None = None,
                  gap_meihua_right: int | None = None,
                  gap_marker_to_drawer: int | None = None,
                  marker_fs_offset: int | None = None,
                  fs_offset_ox: int | None = None,
                  fs_offset_tiyong: int | None = None,
                  gap_between_columns: int | None = None,
                  gap_marker_to_marker: int | None = None,
                  badge_padding_ox: int | None = None):
        """外部可调整参数"""
        layout = self.layout()
        top_area_item = layout.itemAt(0) if layout else None
        top_layout = top_area_item.layout() if top_area_item else None

        if gap_meihua_left is not None:
            self._gap_meihua_left = gap_meihua_left
        if gap_meihua_right is not None:
            self._gap_meihua_right = gap_meihua_right
        if top_layout and (gap_meihua_left is not None or gap_meihua_right is not None):
            top_layout.setContentsMargins(
                self._gap_meihua_left, 0, self._gap_meihua_right, 0)

        if gap_marker_to_drawer is not None:
            self._gap_marker_to_drawer = gap_marker_to_drawer

        if gap_between_columns is not None:
            self._gap_between_columns = gap_between_columns
            if top_layout:
                self._update_column_gaps(top_layout)

        if gap_marker_to_marker is not None:
            self._gap_marker_to_marker = gap_marker_to_marker

        # marker_fs_offset: 向后兼容，同时设置两种标注
        if marker_fs_offset is not None:
            self._fs_offset_ox = marker_fs_offset
            self._fs_offset_tiyong = marker_fs_offset
        if fs_offset_ox is not None:
            self._fs_offset_ox = fs_offset_ox
        if fs_offset_tiyong is not None:
            self._fs_offset_tiyong = fs_offset_tiyong

        if fs_offset_ox is not None or fs_offset_tiyong is not None or marker_fs_offset is not None:
            if self._ben_left:
                self._ben_left.set_fs_offset(self._fs_offset_tiyong)
            if self._ben_right:
                self._ben_right.set_fs_offset(self._fs_offset_ox)
            if self._hu_left:
                self._hu_left.set_fs_offset(self._fs_offset_tiyong)

        if badge_padding_ox is not None:
            self._badge_padding_ox = badge_padding_ox
            for m in [self._ben_left, self._ben_right, self._hu_left]:
                if m:
                    m.set_badge_padding_ox(badge_padding_ox)

        # 重算列宽（当影响 col_pad 的参数变化时）
        if any(x is not None for x in [gap_marker_to_drawer, fs_offset_ox, fs_offset_tiyong, badge_padding_ox]):
            self._recalc_col_dims()

    def _recalc_col_dims(self):
        """根据当前 font_size / fs_offset / padding / gap 重算列宽"""
        if not self._ben_drawer:
            return
        dw = self._ben_drawer.minimumWidth()
        g = self._gap_marker_to_drawer
        # 右标注 (○/× 符号)
        tmp_font_r = _app_font()
        tmp_font_r.setPointSize(self._font_size + self._fs_offset_ox)
        tmp_font_r.setBold(True)
        tmp_fm_r = QFontMetrics(tmp_font_r)
        self._right_marker_w = int(tmp_fm_r.height() + 2 * self._badge_padding_ox + 4)
        # 左标注 (体/用/八卦名)
        tmp_font_l = _app_font()
        tmp_font_l.setPointSize(self._font_size + self._fs_offset_tiyong)
        tmp_font_l.setBold(True)
        tmp_fm_l = QFontMetrics(tmp_font_l)
        self._left_marker_w = int(tmp_fm_l.height() + 2 * self._badge_padding_ox + 4)
        self._col_pad = self._left_marker_w + self._right_marker_w + 2 * g
        self._col_w = self._col_pad + dw
        if self._ben_left:
            self._ben_left.setFixedWidth(self._left_marker_w)
        if self._ben_right:
            self._ben_right.setFixedWidth(self._right_marker_w)
        if self._hu_left:
            self._hu_left.setFixedWidth(self._left_marker_w)
        # 更新 hu_row 右补间距
        layout = self.layout()
        if layout:
            top = layout.itemAt(0)
            if top and top.layout():
                hu_row = top.layout().itemAt(2).layout() if top.layout().count() > 2 else None
                if hu_row:
                    hu_spacer = hu_row.itemAt(hu_row.count() - 1)
                    if hu_spacer and hu_spacer.spacerItem():
                        hu_spacer.spacerItem().changeSize(self._col_pad - (self._left_marker_w + g), 0)

    def _update_column_gaps(self, top_layout=None):
        """
        更新卦列间距 spacer（gap1: 本卦↔互卦, gap2: 互卦↔变卦）

        gap_between_columns = 标注文字之间的【额外】间距（标注区域已占空间之外）
          实际 spacer = max(gap_marker_to_marker, gap_between_columns)
          → gbc=0 时两列标注文字间距 = gap_marker_to_marker（最小值）
          → gbc=20 时标注文字间距 = 20px
        """
        if top_layout is None:
            layout = self.layout()
            top_area_item = layout.itemAt(0) if layout else None
            top_layout = top_area_item.layout() if top_area_item else None
        if top_layout is None:
            return
        gap = max(self._gap_marker_to_marker, self._gap_between_columns)
        for idx in (self._gap1_spacer_idx, self._gap2_spacer_idx):
            item = top_layout.itemAt(idx)
            if item and item.spacerItem():
                item.spacerItem().changeSize(gap, 0)
        if top_layout:
            top_layout.invalidate()

    def set_gua_result(self, ben_data: dict, changing_lines: list[int]):
        """
        根据本卦数据和动爻列表更新梅花面板全部内容

        动爻流程：
          0 动爻 → 互卦正常显示，变卦灰色禁用，底部显示卦辞+彖曰（橙色方块）
          1 动爻 → 体用/o/x 标注，变卦正常，底部显示爻辞+小象（蓝色方块）
          >1 → 不处理（suangua_panel 会禁用梅花并切到六爻）

        Args:
            ben_data: 本卦数据库 dict
            changing_lines: 动爻列表（1=初爻..6=上爻）
        """
        n = len(changing_lines)

        # ── 本卦 ──
        binary = ben_data.get("binary", "111111")
        yang = [c == "1" for c in binary]
        self._ben_drawer.set_lines(yang)
        self._ben_drawer.set_disabled_look(False)
        self._ben_drawer.set_custom_title(f"本-{ben_data.get('full_name', '?')}")

        # ── 互卦 ──
        hu_yang, hu_data, hu_upper_num, hu_lower_num = self._calc_hugua(yang)
        self._hu_drawer.set_lines(hu_yang)
        self._hu_drawer.set_disabled_look(False)
        self._hu_drawer.set_custom_title(f"互-{hu_data.get('full_name', '?') if hu_data else '?'}")
        # 互卦五行模式：上卦爻线=上卦五行色, 下卦爻线=下卦五行色（梅花易数风格，互卦拆成八卦看）
        hu_upper_color = get_wuxing_color_by_xiantian(hu_upper_num, self._text_color)
        hu_lower_color = get_wuxing_color_by_xiantian(hu_lower_num, self._text_color)
        self._hu_drawer.set_wuxing_mode(True, hu_upper_color, hu_lower_color)

        # 互卦左标注：上/下卦八卦名（五行颜色），在五爻和二爻位置
        upper_trigram = XIANTIAN.get(hu_upper_num, {})
        lower_trigram = XIANTIAN.get(hu_lower_num, {})
        self._hu_left.set_markers([
            (4, upper_trigram.get("name", ""), get_wuxing_color_by_xiantian(hu_upper_num, self._text_color)),
            (1, lower_trigram.get("name", ""), get_wuxing_color_by_xiantian(hu_lower_num, self._text_color)),
        ])

        # ── 变卦 + 底部解读 ──
        if n == 1:
            self._handle_one_changing(binary, yang, changing_lines[0], ben_data)
        elif n == 0:
            self._handle_zero_changing(yang, ben_data)

        # n > 1 由 suangua_panel 处理（禁用梅花），这里不更新

    def _calc_hugua(self, yang: list[bool]) -> tuple[list[bool], dict | None, int, int]:
        """
        计算互卦：下卦取 lines[1:4]（二三四爻），上卦取 lines[2:5]（三四五爻）

        Returns:
            (hu_yang, hu_data, upper_xiantian, lower_xiantian)
        """
        lower_yang = yang[1:4]   # indices 1,2,3 → 二三四爻
        upper_yang = yang[2:5]   # indices 2,3,4 → 三四五爻
        hu_yang = lower_yang + upper_yang  # 6 elements

        lower_num = _yang_to_xiantian(lower_yang)
        upper_num = _yang_to_xiantian(upper_yang)
        hu_data = get_gua_by_xiantian(upper_num, lower_num)
        return hu_yang, hu_data, upper_num, lower_num

    def _handle_one_changing(self, binary: str, yang: list[bool], changing_line: int, ben_data: dict):
        """
        1 动爻：显示变卦 + 体用/o/x 标注 + 蓝色方块爻辞+小象

        Args:
            binary: 本卦 6 位二进制
            yang: 本卦 yang_lines
            changing_line: 动爻位置 (1=初爻..6=上爻)
            ben_data: 本卦数据库 dict
        """
        # ── 变卦 ──
        new_binary = list(binary)
        cl_idx = changing_line - 1
        new_binary[cl_idx] = "0" if binary[cl_idx] == "1" else "1"
        new_binary_str = "".join(new_binary)
        bian_yang = [c == "1" for c in new_binary_str]

        bian_lower = _yang_to_xiantian(bian_yang[:3])
        bian_upper = _yang_to_xiantian(bian_yang[3:])
        bian_data = get_gua_by_xiantian(bian_upper, bian_lower)

        self._bian_drawer.set_lines(bian_yang)
        self._bian_drawer.set_disabled_look(False)
        self._bian_drawer.set_custom_title(f"变-{bian_data.get('full_name', '?') if bian_data else '?'}")

        # ── 本卦左标注：体用（体=红色, 用=蓝色）──
        # 动爻在上卦(爻位4-6) → 体=下卦, 用=上卦
        # 动爻在下卦(爻位1-3) → 体=上卦, 用=下卦
        if changing_line >= 4:
            ti_line, yong_line = 1, 4  # 体在下卦(二爻), 用在上卦(五爻)
        else:
            ti_line, yong_line = 4, 1  # 体在上卦(五爻), 用在下卦(二爻)
        self._ben_left.set_markers([
            (ti_line, "体", TI_COLOR),
            (yong_line, "用", YONG_COLOR),
        ])

        # ── 本卦右标注：o/x（动爻标记，badge 模式）──
        self._ben_right.set_badge_mode(True)
        line_idx = changing_line - 1  # 0-5
        is_yang_yao = binary[cl_idx] == "1"
        mark = "○" if is_yang_yao else "×"
        mark_color = O_COLOR if is_yang_yao else X_COLOR
        self._ben_right.set_markers([
            (line_idx, mark, mark_color),
        ])

        # ── 底部蓝色方块：爻辞 + 小象 ──
        result = build_interpretation(ben_data, [changing_line], self._font_size)
        if result:
            self._set_interpret_block(*result)

    def _handle_zero_changing(self, yang: list[bool], ben_data: dict):
        """
        0 动爻：变卦灰色禁用 + 橙色方块卦辞+彖曰

        Args:
            yang: 本卦 yang_lines
            ben_data: 本卦数据库 dict
        """
        # ── 变卦：位置保留，爻线变灰（与本卦一模一样的阴阳）──
        self._bian_drawer.set_lines(list(yang))

        # 灰色自适应
        is_dark_bg = is_light_color(self._text_color)
        if is_dark_bg:
            gray = "#777777"
        else:
            gray = "#b0b0b0"

        self._bian_drawer.set_disabled_look(True, gray)
        self._bian_drawer.set_custom_title("变-无")

        # ── 本卦左标注：默认体在下卦（二爻）──
        self._ben_left.set_markers([
            (1, "体", TI_COLOR),
        ])

        # ── 本卦右标注："安静"（普通文字模式，非 o/x 不用 badge）──
        self._ben_right.set_badge_mode(False)
        self._ben_right.set_markers([
            (3, "安", self._text_color),
            (2, "静", self._text_color),
        ])

        # ── 互卦左标注：保留卦名（已在 set_gua_result 中设置）──

        # ── 底部橙色方块：卦辞 + 彖曰 ──
        result = build_interpretation(ben_data, [], self._font_size)
        if result:
            self._set_interpret_block(*result)

    def _set_interpret_block(self, html: str, bg_color: str):
        self._interpret_label.setText(html)
        self._interpret_frame.setStyleSheet(f"""
            QFrame {{
                background: {bg_color};
                border-radius: 6px;
            }}
        """)
        self._interpret_frame.setVisible(True)
