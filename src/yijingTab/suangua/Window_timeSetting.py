"""
时间设置弹窗 — 天干地支 / 阳历 双模式

从 suangua/common.py 中 _TimePickerDialog 独立提取，
修复深色模式下按钮/标签文字颜色不可见的问题。
"""
import datetime

from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout,
                                QLabel, QPushButton, QComboBox, QFormLayout,
                                QSpinBox, QCheckBox, QStackedWidget, QButtonGroup,
                                QApplication)
from PySide6.QtCore import Qt

from ..com.dot_button import DotButton
from .common import (_TIANGAN, _DIZHI_LIST, compatible_zhis,
                     ganzhi_to_approx_year, gregorian_to_ganzhi_parts)


class Window_timeSetting(QDialog):
    """
    时间选择器 — 天干地支 / 阳历 双模式

    天干地支模式：天干(10选1) + 地支(根据天干阴阳过滤6选1) 分开选择
    阳历模式：年/月/日 QSpinBox，时/分 QSpinBox（需启用时辰）

    自动跟随系统深色/浅色模式调整文字颜色。
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

        # 检测系统颜色主题
        self._is_dark = self._detect_dark_mode()
        self._label_color = "#f0f0f0" if self._is_dark else "#1d1d1f"

        self._gregorian_dt = self._init_gregorian_from_ganzhi(current_ganzhi)

        self._init_ui()
        self._init_values()

    @staticmethod
    def _detect_dark_mode() -> bool:
        """检测系统是否为深色模式（Qt 6.5+ colorScheme API）"""
        try:
            app = QApplication.instance()
            if app and hasattr(app, "styleHints"):
                scheme = app.styleHints().colorScheme()
                return scheme == Qt.ColorScheme.Dark
        except Exception:
            pass
        return True  # 默认深色

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
        lbl_ganzhi.setStyleSheet(
            f"color: {self._label_color}; background: transparent; border: none;"
        )
        lbl_ganzhi.clicked.connect(self._dot_ganzhi.click)
        mode_row.addWidget(lbl_ganzhi)

        mode_row.addSpacing(8)

        self._dot_gregorian = DotButton()
        self._mode_group.addButton(self._dot_gregorian, self.MODE_GREGORIAN)
        mode_row.addWidget(self._dot_gregorian)

        lbl_greg = QPushButton("阳历")
        lbl_greg.setFlat(True)
        lbl_greg.setCursor(Qt.CursorShape.PointingHandCursor)
        lbl_greg.setStyleSheet(
            f"color: {self._label_color}; background: transparent; border: none;"
        )
        lbl_greg.clicked.connect(self._dot_gregorian.click)
        mode_row.addWidget(lbl_greg)

        mode_row.addSpacing(16)

        self._hour_cb = QCheckBox("启用时辰")
        self._hour_cb.setStyleSheet(
            f"color: {self._label_color}; background: transparent;"
        )
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

        now_btn_hover = ("rgba(0, 122, 255, 0.15)" if self._is_dark
                         else "#e8f0fe")
        self._now_btn = QPushButton("设为现在")
        self._now_btn.clicked.connect(self._on_set_now)
        self._now_btn.setStyleSheet(f"""
            QPushButton {{
                color: #007aff; background: transparent;
                border: 1px solid #007aff;
                border-radius: 5px; padding: 6px 14px;
            }}
            QPushButton:hover {{ background: {now_btn_hover}; }}
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

        # 取消按钮 — 跟随系统主题
        if self._is_dark:
            cancel_style = """
                QPushButton {
                    background: #555555; color: #f0f0f0;
                    border-radius: 5px; padding: 6px 20px;
                    border: none;
                }
                QPushButton:hover { background: #6a6a6a; }
            """
        else:
            cancel_style = """
                QPushButton {
                    background: #e0e0e0; color: #1d1d1f;
                    border-radius: 5px; padding: 6px 20px;
                    border: none;
                }
                QPushButton:hover { background: #c0c0c0; }
            """
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(cancel_style)
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
        self._gz_hour_label.setStyleSheet(
            f"color: {self._label_color}; background: transparent;"
        )
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
        self._greg_hour_label.setStyleSheet(
            f"color: {self._label_color}; background: transparent;"
        )
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
