"""
工具栏按钮栏 — 截图 | AI | 保存 | 读取

═══════════════════════════════════════════════════════════════
文件职责：提供 ButtonBar 按钮栏，4个按钮各弹出预留新窗口
         截图/保存/读取 对接后续案例管理功能，AI 对接智能分析功能
═══════════════════════════════════════════════════════════════

布局（手动定位，单行，位于 border_frame 内部）：
  ┌─ ButtonBar ───────────────────────────────────────────────┐
  │  [截图] [AI] [保存] [读取]        ← 所有 gap 相等(=btn_gap)│
  │   x=0         x=保存.x=随机.x  x=读取.x=秒表.x             │
  └──────────────────────────────────────────────────────────┘

对齐规则：
  - _gap_btn_pad 由 divination_panel 动态计算，保证：
    截图.w + gap + AI.w + gap = drawer.width = 保存.x = 随机.x
  - 读取.x = 保存.x + 保存.w + gap = 秒表.x
  - 截图.x = 0；AI.x = 截图.x + 截图.w + gap

按钮风格与报数面板"随机"/"秒表"完全一致：
  - 浅灰底 #f5f5f7 + 深色文字 #1d1d1f（硬编码，不随主题变化）
  - 圆角 6px + 细边框 #dcdcdc
  - hover 边框变蓝 #007aff
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics


class _PlaceholderWindow(QWidget):
    """预留弹窗"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(480, 320)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(f"{title}\n\n功能开发中...")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 16px; color: #86868b;")
        layout.addWidget(label)


class ButtonBar(QWidget):
    """
    工具栏按钮栏 — 单行手动定位

    保存 ↔ 随机 同 x 坐标（垂直对齐）
    读取 ↔ 秒表 同 x 坐标（垂直对齐）
    截图、AI 放置在最左侧

    Args:
        font_size: 全局字号(px)
        btn_h:     按钮固定高度(px)，= _gap_btn_h (38)
        h_pad:     按钮水平留白(px)，= _gap_btn_pad (30)
        btn_gap:   按钮间距(px)，= _gap_sm（lh * 0.25）
        left_offset: 保存按钮的 x 坐标，= drawer.width() + _gap_drawer
        screenshot_target: 截图目标控件引用
    """

    BUTTONS = [
        ("截图", "Screenshot"),
        ("AI",   "AI"),
        ("保存", "Save"),
        ("读取", "Load"),
    ]
    _I_JIETU = 0
    _I_AI = 1
    _I_SAVE = 2
    _I_LOAD = 3

    def __init__(self, font_size: int = 14,
                 btn_h: int = 38, h_pad: int = 30,
                 btn_gap: int = 6, left_offset: int = 0,
                 screenshot_target: QWidget | None = None,
                 parent=None):
        super().__init__(parent)
        self._font_size = font_size
        self._btn_h = btn_h
        self._h_pad = h_pad
        self._btn_gap = btn_gap
        self._left_offset = left_offset
        self._screenshot_target = screenshot_target
        self._btns: list[QPushButton] = []
        self._init_ui()

    def _init_ui(self):
        """创建按钮 + 手动定位（move），不用 layout 避免 maxWidth 压缩 spacer"""
        from .screenshot import _ensure_shutter_loaded
        _ensure_shutter_loaded()

        fs = self._font_size
        f = QFont()
        f.setPointSize(fs)
        fm = QFontMetrics(f)

        # 创建 4 个按钮 — AI 按实际文字宽，其余与报数按钮(随机/秒表)同宽
        for label, obj_name in self.BUTTONS:
            text_w = fm.horizontalAdvance(label)
            btn_w = text_w + self._h_pad
            btn = QPushButton(label)
            btn.setObjectName(obj_name)
            btn.setFixedSize(btn_w, self._btn_h)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setParent(self)

            if obj_name == "Screenshot":
                btn.clicked.connect(self._on_screenshot)
            else:
                btn.clicked.connect(self._make_click_handler(label))

            self._btns.append(btn)
            self._apply_btn_style(btn)

        # 手动定位
        self._reposition()

    def _reposition(self):
        """
        手动计算并设置 4 个按钮的 (x, y) 位置。

        定位规则（所有按钮同一行）：
          1. 先确定 保存.x = left_offset（与 随机 同 x）
          2. 读取.x = 保存.x + 保存.w + gap（与 秒表 同 x）
          3. 截图、AI 填在 保存 左侧，用 left_pad 补齐不足空间
        """
        if len(self._btns) < 4:
            return

        gap = self._btn_gap
        v_pad = max(0, int((self._btn_h - self._font_size * 1.4) / 2))
        y = v_pad

        jietu = self._btns[self._I_JIETU]
        ai = self._btns[self._I_AI]
        save = self._btns[self._I_SAVE]
        load = self._btns[self._I_LOAD]

        # ── 第1步：保存、读取 — x 与报数面板 随机/秒表 对齐 ──
        save_x = self._left_offset
        save.move(save_x, y)

        load_x = save_x + save.width() + gap
        load.move(load_x, y)

        # ── 第2步：截图、AI — 填在 保存 左侧，用 left_pad 补足 ──
        content_before_save = jietu.width() + gap + ai.width() + gap
        left_pad = max(0, save_x - content_before_save)
        jietu.move(left_pad, y)
        ai.move(left_pad + jietu.width() + gap, y)

        # ── Widget 总尺寸 ──
        rightmost = max(ai.x() + ai.width(), load.x() + load.width())
        total_h = self._btn_h + 2 * v_pad
        self.setFixedSize(rightmost, total_h)

    def _on_screenshot(self):
        """截图按钮 → capture_screenshot"""
        from .screenshot import capture_screenshot
        target = self._screenshot_target or self.window()
        path = capture_screenshot(target)
        if path:
            import os
            filename = os.path.basename(path)
            mgr = getattr(self.window(), "_statusbar_mgr", None)
            if mgr:
                mgr.show_status(
                    f'<span style="color:#007aff;">[Info] 图片已保存到 {filename}</span>')

    def _make_click_handler(self, title: str):
        def handler():
            win = _PlaceholderWindow(title, parent=self.window())
            win.show()
        return handler

    def _apply_btn_style(self, btn: QPushButton):
        """按钮样式 — 与报数面板"随机"/"秒表"完全一致"""
        btn.setStyleSheet(f"""
            QPushButton {{
                padding: 4px 0px;
                border: 1px solid #dcdcdc;
                border-radius: 6px;
                background: #f5f5f7;
                color: #1d1d1f;
                font-size: {self._font_size}px;
            }}
            QPushButton:hover {{
                border-color: #007aff;
            }}
        """)

    def total_button_width(self) -> int:
        """按钮区域总宽度，用于 frame max_width"""
        if len(self._btns) < 4:
            return self._left_offset
        load = self._btns[self._I_LOAD]
        return load.x() + load.width()

    def set_left_offset(self, offset: int):
        """更新 left_offset → 重算保存/读取位置"""
        self._left_offset = offset
        self._reposition()

    def refresh_font_size(self, font_size: int, btn_gap: int = 0, left_offset: int | None = None,
                          h_pad: int = 0, btn_h: int = 0):
        """全局字体变更 → 重算按钮尺寸 + 重新定位

        ⚠️ 重要踩坑：left_offset 必须由调用方用 drawer.minimumWidth() 计算，
        不能在这里用 self.width() — resize 事件链中 width() 返回布局前旧值。
        见 memory: widget-width-vs-minimumwidth
        """
        self._font_size = font_size
        if btn_gap:
            self._btn_gap = btn_gap
        if left_offset is not None:
            self._left_offset = left_offset
        if h_pad:
            self._h_pad = h_pad
        if btn_h:
            self._btn_h = btn_h

        fs = font_size
        f = QFont()
        f.setPointSize(fs)
        fm = QFontMetrics(f)

        for label, btn in zip([b[0] for b in self.BUTTONS], self._btns):
            text_w = fm.horizontalAdvance(label)
            btn.setFixedSize(text_w + self._h_pad, self._btn_h)
            self._apply_btn_style(btn)

        self._reposition()

    def refresh_text_color(self, text_color: str):
        """按钮硬编码颜色，不随主题变化（空实现）"""
        pass
