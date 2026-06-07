"""
结果显示 Widget — 展示起卦结果（本卦/变卦/余数详情）

═══════════════════════════════════════════════════════════════
文件职责：提供 ResultDisplay 组件，以卡片式布局展示起卦结果
═══════════════════════════════════════════════════════════════

显示内容：
    - 本卦：Unicode 卦符 + 中文全名（如"☰ 乾为天"），28px 粗体
    - 箭头：↓ 变（表示本卦 → 变卦的转换）
    - 变卦：Unicode 卦符 + 中文全名；六爻皆静时显示"（六爻皆静，无变卦）"
    - 分隔线
    - 余数详情：下卦符号/名称/先天数，上卦符号/名称/先天数，动爻位置
    - 画卦区域：预留的 QWidget canvas（虚线边框），供 hexagram_painter 绘制爻象

被哪些文件调用：
    - divination_panel.py: QiguaPanel 在右侧显示区嵌入此组件
    - 通过 GuaPainter.draw_gua() 调用画卦接口（预留）

依赖：
    - bagua.py: GuaResult, XIANTIAN
    - hexagram_painter.py: GuaPainter（预留画卦接口）

用法示例:
    display = ResultDisplay()
    display.show_result(my_gua_result)  # 显示起卦结果
    display.clear()                     # 清空显示
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QFrame, QScrollArea)
from PySide6.QtCore import Qt

from .bagua import GuaResult, XIANTIAN
from .hexagram_painter import GuaPainter


class ResultDisplay(QWidget):
    """
    起卦结果显示区

    属性:
        _current_result: GuaResult | None — 当前显示的结果，clear() 后为 None

    UI 组件:
        _label_ben_gua: QLabel — 本卦显示（卦符 + 全名，28px 粗体）
        _label_bian_gua: QLabel — 变卦显示（卦符 + 全名，28px 粗体）
        _label_detail: QLabel — 余数和动爻详情（13px）
        _draw_area: QWidget — 预留画卦 canvas（180px 最小高度，虚线边框）

    UI 结构:
        ┌─────────────────────────────┐
        │ 起卦结果                     │
        │ ┌─────────────────────────┐ │
        │ │ 本卦  ☰ 乾为天          │ │
        │ │       ↓ 变              │ │
        │ │ 变卦  ☱ 泽天夬          │ │
        │ │ ─────────────────────── │ │
        │ │ 下卦: ☰ 乾(1) 上卦: ☰ 乾(1) │
        │ │ 动爻: 第 5 爻           │ │
        │ └─────────────────────────┘ │
        │                             │
        │ 卦象图（待实现）              │
        │ ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ │
        │ │   (虚线边框预留画卦区)    │ │
        │ └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ │
        └─────────────────────────────┘

    用法示例:
        display = ResultDisplay()
        display.show_result(gua_result)  # gua_result: GuaResult
        display.clear()                  # 清空
    """

    def __init__(self, parent=None):
        """
        Parameters:
            parent: QWidget | None — 父组件
        """
        super().__init__(parent)
        self._current_result: GuaResult | None = None
        self._init_ui()

    def _init_ui(self):
        """
        构建界面：
        标题 → 结果卡片（本卦/箭头/变卦/分隔线/余数详情）→ 画卦区域（预留）
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        # 标题
        title = QLabel("起卦结果")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #1d1d1f;
            }
        """)
        root.addWidget(title)

        # ── 卦结果显示卡片 ──
        result_frame = QFrame()
        result_frame.setStyleSheet("""
            QFrame {
                background: #f9f9fb;
                border: 1px solid #e5e5ea;
                border-radius: 12px;
            }
        """)
        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(20, 16, 20, 16)
        result_layout.setSpacing(12)

        # 本卦行
        ben_row = QHBoxLayout()
        ben_row.setSpacing(10)
        ben_label = QLabel("本卦")
        ben_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #86868b;
                border: none;
                background: transparent;
            }
        """)
        ben_row.addWidget(ben_label)
        self._label_ben_gua = QLabel("—")
        self._label_ben_gua.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #1d1d1f;
                border: none;
                background: transparent;
            }
        """)
        ben_row.addWidget(self._label_ben_gua)
        ben_row.addStretch()
        result_layout.addLayout(ben_row)

        # 箭头
        arrow = QLabel("    ↓ 变    ")
        arrow.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #aeaeb2;
                border: none;
                background: transparent;
            }
        """)
        result_layout.addWidget(arrow)

        # 变卦行
        bian_row = QHBoxLayout()
        bian_row.setSpacing(10)
        bian_label = QLabel("变卦")
        bian_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #86868b;
                border: none;
                background: transparent;
            }
        """)
        bian_row.addWidget(bian_label)
        self._label_bian_gua = QLabel("—")
        self._label_bian_gua.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #1d1d1f;
                border: none;
                background: transparent;
            }
        """)
        bian_row.addWidget(self._label_bian_gua)
        bian_row.addStretch()
        result_layout.addLayout(bian_row)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("QFrame { color: #e5e5ea; border: none; }")
        result_layout.addWidget(sep)

        # ── 余数和动爻信息 ──
        self._label_detail = QLabel("")
        self._label_detail.setWordWrap(True)
        self._label_detail.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #86868b;
                border: none;
                background: transparent;
            }
        """)
        result_layout.addWidget(self._label_detail)

        root.addWidget(result_frame)

        # ── 画卦区域（预留接口，后续由 hexagram_painter 实现绘制）──
        draw_label = QLabel("卦象图（待实现）")
        draw_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #aeaeb2;
            }
        """)
        root.addWidget(draw_label)

        self._draw_area = QWidget()
        self._draw_area.setMinimumHeight(180)
        self._draw_area.setStyleSheet("""
            QWidget {
                background: #f9f9fb;
                border: 1px dashed #dcdcdc;
                border-radius: 12px;
            }
        """)
        root.addWidget(self._draw_area, 1)

        self._label_empty = QLabel("")
        self._label_empty.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #aeaeb2;
                border: none;
                background: transparent;
            }
        """)
        root.addWidget(self._label_empty)

    def show_result(self, result: GuaResult):
        """
        显示起卦结果

        更新内部标签：
          - _label_ben_gua: "☰ 乾为天" 格式
          - _label_bian_gua: "☱ 天泽履" 或 "（六爻皆静，无变卦）"
          - _label_detail: 下卦/上卦符号名称先天数 + 动爻位置
          - 调用 GuaPainter.draw_gua() 预留画卦

        Parameters:
            result: GuaResult — 起卦计算结果，含 ben_gua/bian_gua/lower_num/upper_num/changing_line

        用法示例:
            display = ResultDisplay()
            display.show_result(gua_result)
        """
        self._current_result = result

        ben = result.ben_gua
        bian = result.bian_gua

        # 本卦显示
        if ben:
            symbol = ben.get("symbol", "")
            full_name = ben.get("full_name", "?")
            self._label_ben_gua.setText(f"{symbol}  {full_name}")
        else:
            self._label_ben_gua.setText("未找到")

        # 变卦显示
        if bian:
            symbol = bian.get("symbol", "")
            full_name = bian.get("full_name", "?")
            self._label_bian_gua.setText(f"{symbol}  {full_name}")
        elif result.changing_line == 0:
            self._label_bian_gua.setText("（六爻皆静，无变卦）")
        else:
            self._label_bian_gua.setText("未找到")

        # 余数详情
        lower_name = XIANTIAN.get(result.lower_num, {}).get("name", "?")
        upper_name = XIANTIAN.get(result.upper_num, {}).get("name", "?")
        lower_symbol = XIANTIAN.get(result.lower_num, {}).get("symbol", "?")
        upper_symbol = XIANTIAN.get(result.upper_num, {}).get("symbol", "?")

        detail = (
            f"下卦: {lower_symbol} {lower_name} (先天数 {result.lower_num})  |  "
            f"上卦: {upper_symbol} {upper_name} (先天数 {result.upper_num})\n"
            f"动爻: 第 {result.changing_line} 爻"
            if result.changing_line > 0
            else "动爻: 无"
        )
        self._label_detail.setText(detail)

        # 调用画卦接口（预留）
        GuaPainter.draw_gua(self._draw_area, result)

    def clear(self):
        """
        清空结果显示

        重置所有标签为默认占位文字，清空 _current_result，
        调用 GuaPainter.clear() 清空画卦区域
        """
        self._label_ben_gua.setText("—")
        self._label_bian_gua.setText("—")
        self._label_detail.setText("")
        self._current_result = None
        GuaPainter.clear(self._draw_area)
