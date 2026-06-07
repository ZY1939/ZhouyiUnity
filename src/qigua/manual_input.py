"""
手工指定 Widget — 输入框支持数字/范围/卦名/下拉选择

═══════════════════════════════════════════════════════════════
文件职责：提供 ManualInputWidget，通过输入框搜索和选择六十四卦
═══════════════════════════════════════════════════════════════

支持输入格式：
    - 数字 "1"      → 八纯卦（上下卦相同，如 1→乾为天）
    - 范围 "1-2"    → 上乾下兑 = 天泽履
    - 卦名 "乾"     → 模糊搜索匹配
    - 全名 "天泽履"  → 精确匹配
    - 拼音首字母 "qwt" → 乾为天（简单拼音映射）

自动补全：
    - QCompleter：加载所有 64 卦全名 + 数字快捷方式
    - 实时搜索提示：输入变化时在下方的 _label_match 显示匹配结果

被哪些文件调用：
    - divination_panel.py: QiguaPanel 已将手工指定功能整合到 _make_manual_panel()
    - 本文件保留作为独立组件参考和备选

依赖：
    - hexagram_loader.py: load_all_gua(), search_gua(), get_gua_by_xiantian()
    - bagua.py: XIANTIAN, NAME_TO_XIANTIAN
    - hexagram_calc.py: calc_three_numbers(), calc_six_lines()

用法示例:
    widget = ManualInputWidget()
    widget.setup_completer()  # 必须在加载数据后调用
    widget.set_on_result(lambda result: print(f"选中: {result.ben_gua}"))
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QLineEdit, QCompleter, QPushButton)
from PySide6.QtCore import Qt, QStringListModel

from .hexagram_loader import load_all_gua, search_gua, get_gua_by_xiantian
from .bagua import XIANTIAN, NAME_TO_XIANTIAN
from .hexagram_calc import calc_three_numbers, calc_six_lines


class ManualInputWidget(QWidget):
    """
    手工指定起卦输入区

    属性:
        _all_gua: dict[int, dict] — 全部 64 卦数据缓存 {卦ID: 卦数据}
        _completer_names: list[str] — QCompleter 用的名称列表
        _input: QLineEdit — 主输入框
        _btn_calc: QPushButton — 「起卦」按钮
        _label_match: QLabel — 匹配结果提示区
        _on_result: Callable[[GuaResult], None] | None — 结果回调

    UI 结构:
        ┌─────────────────────────────┐
        │ 卦名 / 数字 / "1-2" 范围     │
        │ [___________________] [起卦] │
        │ ☰ 乾为天 (ID:1)             │
        └─────────────────────────────┘

    用法示例:
        widget = ManualInputWidget()
        widget.setup_completer()
        widget.set_on_result(lambda result: print(result.ben_gua.get("full_name")))
    """

    def __init__(self, parent=None):
        """
        Parameters:
            parent: QWidget | None — 父组件
        """
        super().__init__(parent)
        self._all_gua = {}
        self._completer_names: list[str] = []
        self._on_result = None
        self._init_ui()

    def _init_ui(self):
        """
        构建界面：
        说明标签 → 输入行（QLineEdit + 起卦按钮）→ 匹配结果提示
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # 说明
        hint = QLabel('卦名 / 数字 / "1-2" 范围')
        hint.setStyleSheet("""
            QLabel { font-size: 11px; color: #86868b; }
        """)
        root.addWidget(hint)

        # ── 输入行 ──
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self._input = QLineEdit()
        self._input.setPlaceholderText("乾 / 天泽履 / 1 / 1-2 …")
        self._input.setFixedHeight(30)
        self._input.setStyleSheet("""
            QLineEdit {
                padding: 4px 8px; border: 1.5px solid #dcdcdc; border-radius: 5px;
                font-size: 13px; background: #ffffff; color: #1d1d1f;
            }
            QLineEdit:focus { border-color: #007aff; }
        """)
        input_row.addWidget(self._input, 1)

        self._btn_calc = QPushButton("起卦")
        self._btn_calc.setFixedSize(56, 30)
        self._btn_calc.setStyleSheet("""
            QPushButton {
                border: none; border-radius: 6px; background: #007aff;
                font-size: 12px; font-weight: bold; color: #ffffff;
            }
            QPushButton:hover { background: #0062cc; }
        """)
        self._btn_calc.clicked.connect(self._on_calc)
        input_row.addWidget(self._btn_calc)

        root.addLayout(input_row)

        # ── 匹配结果提示 ──
        self._label_match = QLabel("")
        self._label_match.setWordWrap(True)
        self._label_match.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #aeaeb2;
            }
        """)
        root.addWidget(self._label_match)

        root.addStretch()

    def setup_completer(self):
        """
        从 64 卦数据构建 QCompleter 自动补全列表

        补全项包括：
          - 卦名（如"乾"）
          - 全名（如"乾为天"）
          - 繁体全名（如"乾為天"）
          - 数字快捷方式（如"1-1 → 乾为天"）

        同时连接 textChanged 信号 → _on_text_changed 实时搜索提示
        """
        self._all_gua = load_all_gua()
        names = []
        for gid, data in self._all_gua.items():
            name = data.get("name", "")
            full = data.get("full_name", "")
            full_tc = data.get("fullName_tc", "")
            symbol = data.get("symbol", "")
            for n in (name, full, full_tc):
                if n:
                    names.append(n)
            # 数字快捷方式
            upper = data.get("upper", "")
            lower = data.get("lower", "")
            upper_num = NAME_TO_XIANTIAN.get(upper)
            lower_num = NAME_TO_XIANTIAN.get(lower)
            if upper_num and lower_num:
                names.append(f"{upper_num}-{lower_num} → {full}")

        self._completer_names = sorted(set(names))
        model = QStringListModel()
        model.setStringList(self._completer_names)
        completer = QCompleter(model, self._input)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._input.setCompleter(completer)

        # 实时搜索提示
        self._input.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self, text: str):
        """
        输入变化时实时显示匹配提示（最多 5 条）

        调用链：
            QLineEdit.textChanged → _on_text_changed → search_gua(query)
              → 匹配结果格式化显示在 _label_match

        Parameters:
            text: str — 当前输入文本
        """
        if not text.strip():
            self._label_match.setText("")
            return

        results = search_gua(text)
        if results:
            lines = []
            for gid, data in results[:5]:
                lines.append(f"{data.get('symbol','')} {data.get('full_name','')} (ID:{gid})")
            self._label_match.setText("\n".join(lines))
        else:
            self._label_match.setText("未找到匹配的卦")

    def _on_calc(self):
        """
        解析输入并计算起卦结果

        解析优先级：
          1. search_gua() 模糊搜索 → 找唯一匹配 → 直接作为本卦（无动爻）
          2. 数字范围 "1-2" → 上乾下兑 → get_gua_by_xiantian()
          3. 以上都不匹配 → 显示错误提示

        注意：手工指定默认无动爻（changing_line=0），用户需后续指定动爻
        """
        text = self._input.text().strip()
        if not text:
            return

        # 搜索匹配
        results = search_gua(text)

        if results:
            # 找到唯一匹配 → 直接使用该卦作为本卦（无动爻）
            gid, data = results[0]
            if len(results) == 1:
                from .bagua import GuaResult
                upper_name = data.get("upper", "")
                lower_name = data.get("lower", "")
                upper_num = NAME_TO_XIANTIAN.get(upper_name, 1)
                lower_num = NAME_TO_XIANTIAN.get(lower_name, 1)
                result = GuaResult(
                    ben_gua=data,
                    bian_gua=None,
                    lower_num=lower_num,
                    upper_num=upper_num,
                    changing_line=0,
                )
                self._label_match.setText(f"已选择: {data.get('symbol','')} {data.get('full_name','')}")
                if self._on_result:
                    self._on_result(result)
                return

        # 数字范围 "1-2"
        import re
        range_match = re.match(r"^(\d)\s*[-–]\s*(\d)$", text)
        if range_match:
            upper = int(range_match.group(1))
            lower = int(range_match.group(2))
            if 1 <= upper <= 8 and 1 <= lower <= 8:
                gua = get_gua_by_xiantian(upper, lower)
                if gua:
                    from .bagua import GuaResult
                    result = GuaResult(
                        ben_gua=gua,
                        bian_gua=None,
                        lower_num=lower,
                        upper_num=upper,
                        changing_line=0,
                    )
                    self._label_match.setText(f"已选择: {gua.get('symbol','')} {gua.get('full_name','')}")
                    if self._on_result:
                        self._on_result(result)
                    return

        self._label_match.setText("未能识别的输入，请重试")

    def set_on_result(self, callback):
        """
        设置结果回调

        Parameters:
            callback: Callable[[GuaResult], None] — 接收 GuaResult 的回调函数
        """
        self._on_result = callback
