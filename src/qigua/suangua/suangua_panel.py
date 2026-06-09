"""
算卦主面板 — "算卦"标题 + 梅花/六爻 方法选择器 + 时间显示 + QStackedWidget

═══════════════════════════════════════════════════════════════
文件职责：提供 SuanguaPanel 组件，与 QiguaPanel 并排显示，
         组织梅花易数/六爻的断卦界面，管理共享时间状态
═══════════════════════════════════════════════════════════════

布局结构：
  ┌─ SuanguaPanel (root QVBoxLayout → suangua_frame) ────────┐
  │  header: 算卦 ●梅花 ●六爻  [时间显示 修改 现在]            │
  │  ── spacer ──                                             │
  │  QStackedWidget                                           │
  │    index 0 = MeihuaPanel (梅花)                            │
  │    index 1 = LiuyaoPanel (六爻)                            │
  │  addStretch()                                             │
  └──────────────────────────────────────────────────────────┘
"""
import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QStackedWidget, QLabel, QButtonGroup, QFrame, QDialog)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontMetrics

from ...settings.config_manager import config_manager
from ..dot_button import DotButton
from ..CONST_DEFINE_UI import SuanguaConfig
from .meihua_panel import MeihuaPanel
from .liuyao_panel import LiuyaoPanel
from .common import (_TimePickerDialog, compute_current_ganzhi,
                     ganzhi_to_approx_year, gregorian_to_ganzhi_parts, _DIZHI_LIST)


class SuanguaPanel(QWidget):
    """
    算卦主面板 — 梅花/六爻方法选择 + 面板切换

    与 QiguaPanel 配合使用，接收起卦结果后更新梅花面板显示。
    """

    METHODS = [
        {"key": "meihua", "label": "梅花"},
        {"key": "liuyao", "label": "六爻"},
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_size = 16
        self._text_color = "#1d1d1f"
        self._current_method = "meihua"
        self._header_row_h = 0
        self._ydist_menu2top = SuanguaConfig.ydist_menu2top
        self._gap_suangua_left = SuanguaConfig.gap_suangua_left
        self._fs_name = SuanguaConfig.fs_name
        self._panel_width_pct = SuanguaConfig.panel_width_pct
        self._panel_min_extra = SuanguaConfig.panel_min_extra

        self._gua_result = None
        self._changing_lines: list[int] = []
        self._current_ganzhi: dict | None = None
        self._gregorian_dt: datetime.datetime | None = None

        self._init_ui()

    def _init_ui(self):
        # ── 先创建子面板，以获取 drawer.line_h 对齐 QiguaPanel title 高度 ──
        self._meihua_panel = MeihuaPanel()
        self._liuyao_panel = LiuyaoPanel()
        lh = self._meihua_panel._ben_drawer.line_h if self._meihua_panel._ben_drawer else 40
        self._title_lh = lh
        self._header_row_h = lh

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── suangua_frame（右边框+下边框圆角矩形）──
        self._suangua_frame = QFrame()
        self._suangua_frame.setObjectName("suangua_frame")
        self._suangua_frame.setStyleSheet(f"""
            QFrame#suangua_frame {{
                border: 1px solid {self._text_color};
                border-left: none;
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 10px;
                background: transparent;
            }}
        """)
        self._frame_layout = QVBoxLayout(self._suangua_frame)
        self._frame_layout.setContentsMargins(0, 0, 0, 0)
        self._frame_layout.setSpacing(0)

        # ── top_spacer ──
        top_gap = max(0, self._ydist_menu2top - self._header_row_h // 2)
        self._frame_layout.addSpacing(top_gap)

        # ── header ──
        self._header_layout = QHBoxLayout()
        self._header_layout.setContentsMargins(self._gap_suangua_left, 0, 0, 0)
        self._header_layout.setSpacing(0)
        self._build_header()
        self._frame_layout.addLayout(self._header_layout)

        # hdr_spacer
        self._hdr_spacer_idx = self._frame_layout.count()
        self._frame_layout.addSpacing(4)  # 会被 refresh_font_size 更新

        # ── QStackedWidget ──
        self._stack = QStackedWidget()
        self._stack.addWidget(self._meihua_panel)  # index 0 (已在 _init_ui 开头创建)
        self._stack.addWidget(self._liuyao_panel)  # index 1 (已在 _init_ui 开头创建)

        self._frame_layout.addWidget(self._stack, 1)
        self._frame_layout.addStretch()

        root.addWidget(self._suangua_frame, 1)

        # ── 加载上次选择的方法 ──
        saved = config_manager.get("general", "suangua_method") or "meihua"
        idx = next((i for i, m in enumerate(self.METHODS) if m["key"] == saved), 0)
        self._dots[idx].setChecked(True)
        self._switch_method(saved)

    def _build_header(self):
        self._title_label = QPushButton("算卦")
        self._title_label.setFlat(True)
        self._title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._title_label.setFixedHeight(self._title_lh)
        title_font = QFont()
        title_font.setPointSize(self._font_size + 4)
        title_font.setBold(True)
        title_fm = QFontMetrics(title_font)
        self._title_label.setMinimumWidth(title_fm.horizontalAdvance("算卦") + 4)
        self._title_label.setStyleSheet(f"""
            QPushButton {{
                font-size: {self._font_size + 4}px;
                font-weight: bold;
                color: #007aff;
                border: none;
                background: transparent;
                text-align: left;
            }}
            QPushButton:hover {{ color: #0056cc; }}
        """)
        self._header_layout.addWidget(self._title_label, 0, Qt.AlignmentFlag.AlignVCenter)

        # gap after title — 使用与 qigua header 一致的公式
        self._gap_md = max(6, int(28 * 0.45))  # 默认值，refresh_font_size 会更新
        self._header_layout.addSpacing(self._gap_md)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        self._dots: list[DotButton] = []
        self._header_labels: list[QPushButton] = []

        for i, m in enumerate(self.METHODS):
            dot = DotButton()
            self._btn_group.addButton(dot, i)
            self._dots.append(dot)
            self._header_layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)

            lbl = QPushButton(m["label"])
            lbl.setFlat(True)
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            lbl.setStyleSheet(f"""
                QPushButton {{
                    color: #86868b; border: none; background: transparent;
                    font-size: {self._font_size}px;
                }}
                QPushButton:hover {{ color: {self._text_color}; }}
            """)
            lbl.clicked.connect(lambda checked, idx=i: self._dots[idx].click())
            self._header_labels.append(lbl)
            self._header_layout.addWidget(lbl, 0, Qt.AlignmentFlag.AlignVCenter)

            if i < len(self.METHODS) - 1:
                # 使用与 qigua header 一致的间距方法
                self._header_layout.addSpacing(20)  # 会被 _update_header_spacing 更新

        self._header_layout.addStretch()

        # ── 时间显示 ──
        self._time_label = QLabel("")
        self._time_label.setStyleSheet(
            f"font-size: {self._font_size}px; color: #ffffff; background: transparent;"
        )
        self._header_layout.addWidget(self._time_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self._header_layout.addSpacing(8)

        self._edit_btn = QPushButton("修改")
        self._edit_btn.setFlat(True)
        self._edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        self._edit_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {self._font_size - 1}px;
                color: #007aff;
                background: transparent;
                border: none;
                padding: 2px 6px;
            }}
            QPushButton:hover {{ color: #0056cc; }}
        """)
        self._header_layout.addWidget(self._edit_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self._header_layout.addSpacing(4)

        self._now_btn = QPushButton("现在")
        self._now_btn.setFlat(True)
        self._now_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._now_btn.clicked.connect(self._on_now_clicked)
        self._now_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {self._font_size - 1}px;
                color: #007aff;
                background: transparent;
                border: none;
                padding: 2px 6px;
            }}
            QPushButton:hover {{ color: #0056cc; }}
        """)
        self._header_layout.addWidget(self._now_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # 右侧留白
        self._header_layout.addSpacing(12)

        self._btn_group.buttonClicked.connect(self._on_dot_clicked)

    def _on_dot_clicked(self, btn):
        idx = self._btn_group.id(btn)
        key = self.METHODS[idx]["key"]
        # 多动爻(>1)不支持梅花 → 回退 dot 状态 + 状态栏警告，不切换
        if key == "meihua" and len(self._changing_lines) > 1:
            # QButtonGroup 已将梅花选蓝、六爻取消 → 回退（不 blockSignals，
            # 让 _on_toggled 正常更新样式，且程序化 setChecked 不触发 buttonClicked）
            self._dots[0].setChecked(False)
            self._dots[1].setChecked(True)
            mgr = getattr(self.window(), "_statusbar_mgr", None)
            if mgr:
                mgr.show_status('<span style="color:#f0a030;">[Warn] 多动爻不支持梅花易数，请使用六爻</span>')
                QTimer.singleShot(5000, mgr.reset_status)
            return
        self._switch_method(key)

    def switch_method(self, key: str):
        """
        公开方法 — 切换算卦方法并同步更新 dot 按钮选中状态

        与 _switch_method 的区别：同时更新 dot 按钮的 checked 状态，
        供外部（如 divination_panel 自适应切换）调用。

        Args:
            key: 算卦方法标识 ("meihua" / "liuyao")
        """
        idx = {"meihua": 0, "liuyao": 1}[key]
        self._dots[idx].setChecked(True)
        self._switch_method(key)

    def _switch_method(self, key: str):
        self._current_method = key
        idx = {"meihua": 0, "liuyao": 1}[key]
        self._stack.setCurrentIndex(idx)
        config_manager.set("general", "suangua_method", value=key)

    # ═══════════════════════════════════════════════════════════
    #  时间管理
    # ═══════════════════════════════════════════════════════════

    def _ensure_time(self):
        """确保时间已初始化（延迟到首次 set_gua_result 时计算）"""
        if self._current_ganzhi is None:
            self._current_ganzhi = compute_current_ganzhi()
            self._gregorian_dt = datetime.datetime.now()
            self._update_time_display()

    def _update_time_display(self):
        """根据当前干支和公历时间更新 header 时间标签"""
        if self._current_ganzhi is None or self._gregorian_dt is None:
            return
        gz = self._current_ganzhi
        dt = self._gregorian_dt
        text = (f"时间：{dt.year}-{dt.month:02d}-{dt.day:02d}  "
                f"{gz['year_ganzhi']}年 {gz['month_ganzhi']}月 "
                f"{gz['day_ganzhi']}日 {gz['hour_ganzhi']}时")
        self._time_label.setText(text)

    def _on_edit_clicked(self):
        """打开时间选择器弹窗"""
        self._ensure_time()
        dlg = _TimePickerDialog(self._current_ganzhi, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result = dlg.result()
            if result:
                self._current_ganzhi = result
                # 从干支反推公历近似日期
                self._gregorian_dt = self._init_gregorian_from_ganzhi(result)
                self._update_time_display()
                self._propagate_time()

    def _on_now_clicked(self):
        """重置为当前系统时间"""
        self._current_ganzhi = compute_current_ganzhi()
        self._gregorian_dt = datetime.datetime.now()
        self._update_time_display()
        self._propagate_time()

    def _propagate_time(self):
        """将时间变更传播给梅花和六爻子面板"""
        gz = self._current_ganzhi
        self._meihua_panel.set_time_ganzhi(gz)
        self._liuyao_panel.set_time_ganzhi(gz)

    def _init_gregorian_from_ganzhi(self, ganzhi: dict) -> datetime.datetime:
        """从干支 dict 推算近似的公历 datetime（委托给 liuyao_panel 的工具函数）"""
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

    def set_gua_result(self, ben_data: dict, changing_lines: list[int],
                        bian_data: dict | None = None):
        """
        接收起卦结果，更新算卦面板

        Args:
            ben_data: 本卦数据 dict
            changing_lines: 动爻列表
            bian_data: 变卦数据 dict（None=无变卦）

        行为：
          - >1 动爻: 梅花选项禁用，强制六爻
          - ≤1 动爻: 梅花可用，仅更新数据不切换方法
        """
        self._gua_result = ben_data
        self._changing_lines = changing_lines
        self._bian_data = bian_data
        n = len(changing_lines)

        # 确保时间已初始化
        self._ensure_time()
        self._propagate_time()

        # 始终更新六爻面板（无论动爻数）
        self._liuyao_panel.set_gua_result(ben_data, changing_lines, bian_data)

        if n > 1:
            # 多动爻：梅花不可用（灰色但仍可点击 → 点击时状态栏警告）
            self._dots[0].setEnabled(True)
            self._header_labels[0].setEnabled(True)
            self._header_labels[0].setStyleSheet(f"""
                QPushButton {{ color: #aaa; border: none; background: transparent; font-size: {self._font_size}px; }}
            """)
            if self._current_method == "meihua":
                self._dots[1].setChecked(True)
                self._switch_method("liuyao")
                mgr = getattr(self.window(), "_statusbar_mgr", None)
                if mgr:
                    mgr.show_status('<span style="color:#007aff;">[Info] 多动爻不支持梅花，已切换为六爻</span>')
                    QTimer.singleShot(5000, mgr.reset_status)
            return

        # n <= 1: 梅花可用，更新数据
        self._dots[0].setEnabled(True)
        self._header_labels[0].setEnabled(True)
        self._header_labels[0].setStyleSheet(f"""
            QPushButton {{
                color: #86868b; border: none; background: transparent;
                font-size: {self._font_size}px;
            }}
            QPushButton:hover {{ color: {self._text_color}; }}
        """)
        self._meihua_panel.set_gua_result(ben_data, changing_lines)

    def refresh_font_size(self, font_size: int):
        self._font_size = font_size

        # ── 先更新子面板字体（drawer.line_h 会随之更新）──
        self._meihua_panel.set_font_size(font_size)
        self._meihua_panel.set_fs_name(self._fs_name)
        self._liuyao_panel.set_font_size(font_size)
        self._liuyao_panel.set_fs_name(self._fs_name)

        # ── 从更新后的 drawer 获取 line_h ──
        lh = self._meihua_panel._ben_drawer.line_h if self._meihua_panel._ben_drawer else 40

        # ── 标题：使用 drawer.line_h 与 QiguaPanel 的"起卦"title 高度一致 ──
        self._title_lh = lh
        self._header_row_h = lh

        tf4 = QFont()
        tf4.setPointSize(font_size + 4)
        tf4.setBold(True)
        tfm = QFontMetrics(tf4)

        self._title_label.setFixedHeight(self._title_lh)
        self._title_label.setMinimumWidth(tfm.horizontalAdvance("算卦") + 4)
        self._title_label.setStyleSheet(f"""
            QPushButton {{
                font-size: {font_size + 4}px;
                font-weight: bold;
                color: #007aff;
                border: none;
                background: transparent;
                text-align: left;
            }}
            QPushButton:hover {{ color: #0056cc; }}
        """)

        # ── top_spacer ──
        top_spacer = self._frame_layout.itemAt(0)
        if top_spacer and top_spacer.spacerItem():
            top_spacer.spacerItem().changeSize(0, max(0, self._ydist_menu2top - self._header_row_h // 2))

        # ── gap_md (标题→第一个dot间距) ──
        self._gap_md = max(6, int(lh * 0.45))
        gap_item = self._header_layout.itemAt(1)
        if gap_item and gap_item.spacerItem():
            gap_item.spacerItem().changeSize(self._gap_md, 0)

        # ── method labels ──
        for lbl in self._header_labels:
            if lbl.isEnabled():
                lbl.setStyleSheet(f"""
                    QPushButton {{
                        color: #86868b; border: none; background: transparent;
                        font-size: {font_size}px;
                    }}
                    QPushButton:hover {{ color: {self._text_color}; }}
                """)
            else:
                lbl.setStyleSheet(f"""
                    QPushButton {{ color: #aaa; border: none; background: transparent; font-size: {font_size}px; }}
                """)

        # ── 时间标签 ──
        self._time_label.setStyleSheet(
            f"font-size: {font_size}px; color: #ffffff; background: transparent;"
        )

        # ── 修改/现在按钮 ──
        btn_style = f"""
            QPushButton {{
                font-size: {font_size - 1}px;
                color: #007aff;
                background: transparent;
                border: none;
                padding: 2px 6px;
            }}
            QPushButton:hover {{ color: #0056cc; }}
        """
        self._edit_btn.setStyleSheet(btn_style)
        self._now_btn.setStyleSheet(btn_style)

        # ── hdr_spacer ──
        xs_gap = max(2, int(lh * 0.12))
        hdr_spacer = self._frame_layout.itemAt(self._hdr_spacer_idx)
        if hdr_spacer and hdr_spacer.spacerItem():
            hdr_spacer.spacerItem().changeSize(0, xs_gap)

        self._frame_layout.invalidate()
        self._header_layout.invalidate()

    def refresh_text_color(self, text_color: str):
        self._text_color = text_color

        # ── 边框 ──
        if hasattr(self, "_suangua_frame"):
            self._suangua_frame.setStyleSheet(f"""
                QFrame#suangua_frame {{
                    border: 1px solid {text_color};
                    border-left: none;
                    border-top: none;
                    border-top-left-radius: 0px;
                    border-top-right-radius: 0px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 10px;
                    background: transparent;
                }}
            """)

        # ── method labels hover color ──
        for lbl in self._header_labels:
            if lbl.isEnabled():
                lbl.setStyleSheet(f"""
                    QPushButton {{
                        color: #86868b; border: none; background: transparent;
                        font-size: {self._font_size}px;
                    }}
                    QPushButton:hover {{ color: {text_color}; }}
                """)

        # ── 梅花面板 ──
        self._meihua_panel.set_text_color(text_color)

        # ── 六爻面板 ──
        self._liuyao_panel.set_text_color(text_color)

    def configure(self, ydist_menu2top: int | None = None,
                  gap_suangua_left: int | None = None,
                  gap_meihua_left: int | None = None,
                  gap_meihua_right: int | None = None,
                  gap_marker_to_drawer: int | None = None,
                  marker_fs_offset: int | None = None,
                  fs_offset_ox: int | None = None,
                  fs_offset_tiyong: int | None = None,
                  fs_name: int | None = None,
                  panel_width_pct: float | None = None,
                  panel_min_extra: int | None = None,
                  gap_between_columns: int | None = None,
                  gap_marker_to_marker: int | None = None,
                  badge_padding_ox: int | None = None):
        """外部可调整参数"""
        if ydist_menu2top is not None:
            self._ydist_menu2top = ydist_menu2top
            if hasattr(self, "_frame_layout") and hasattr(self, "_header_row_h"):
                top_spacer = self._frame_layout.itemAt(0)
                if top_spacer and top_spacer.spacerItem():
                    top_spacer.spacerItem().changeSize(0, max(0, self._ydist_menu2top - self._header_row_h // 2))
        if gap_suangua_left is not None:
            self._gap_suangua_left = gap_suangua_left
        if panel_width_pct is not None:
            self._panel_width_pct = panel_width_pct
        if panel_min_extra is not None:
            self._panel_min_extra = panel_min_extra
        # 透传梅花面板参数
        meihua_kw = {}
        if gap_meihua_left is not None:
            meihua_kw["gap_meihua_left"] = gap_meihua_left
        if gap_meihua_right is not None:
            meihua_kw["gap_meihua_right"] = gap_meihua_right
        if gap_marker_to_drawer is not None:
            meihua_kw["gap_marker_to_drawer"] = gap_marker_to_drawer
        if marker_fs_offset is not None:
            meihua_kw["marker_fs_offset"] = marker_fs_offset
        if fs_offset_ox is not None:
            meihua_kw["fs_offset_ox"] = fs_offset_ox
        if fs_offset_tiyong is not None:
            meihua_kw["fs_offset_tiyong"] = fs_offset_tiyong
        if gap_between_columns is not None:
            meihua_kw["gap_between_columns"] = gap_between_columns
        if gap_marker_to_marker is not None:
            meihua_kw["gap_marker_to_marker"] = gap_marker_to_marker
        if badge_padding_ox is not None:
            meihua_kw["badge_padding_ox"] = badge_padding_ox
        if meihua_kw:
            self._meihua_panel.configure(**meihua_kw)
        if fs_name is not None:
            self._fs_name = fs_name

    def compute_min_width(self) -> int:
        """
        计算算卦面板最小宽度（px）

        委托给梅花面板计算：3个卦图列宽 + 列间距 + 左右边距
        加上 suangua_frame 的左边距（gap_suangua_left）

        Returns:
            int: 算卦面板最小宽度（像素）
        """
        meihua_min = self._meihua_panel.compute_min_width()
        liuyao_min = self._liuyao_panel.compute_min_width()
        return self._gap_suangua_left + max(meihua_min, liuyao_min) + self._panel_min_extra

    def apply_max_width(self, available_width: int):
        """
        根据百分比和最小宽度计算并应用 suangua_frame 的最大宽度

        实际宽度 = max(compute_min_width(), available_width * panel_width_pct)

        Args:
            available_width: tab 可用宽度（px）

        调用时机：
          - divination_panel 的 resizeEvent / _manage_module_widths
          - refresh_font_size 后
        """
        target_w = max(self.compute_min_width(), int(available_width * self._panel_width_pct))
        self._suangua_frame.setMaximumWidth(target_w)
        import os
        if os.environ.get("ZY_DEBUG"):
            print(f"[DEBUG SuanguaPanel.apply_max_width] available={available_width} "
                  f"min_w={self.compute_min_width()} pct={self._panel_width_pct} "
                  f"target={target_w}", flush=True)

    @property
    def frame(self) -> QFrame:
        return self._suangua_frame
