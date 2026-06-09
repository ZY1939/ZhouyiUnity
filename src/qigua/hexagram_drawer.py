"""
卦象绘制组件 — 左侧卦象可视化 Widget，支持阴阳爻绘制与交互

═══════════════════════════════════════════════════════════════
文件职责：提供 HexagramDrawer 组件，在起卦面板左侧绘制六爻卦象
═══════════════════════════════════════════════════════════════

绘制内容：
    - 顶部居中显示卦名（如"䷀ 乾为天"，含 Unicode 卦符 + 中文全名）
    - 下方 6 爻从下而上排列（第 1 爻=初爻，第 6 爻=上爻）
    - 阳爻：红色圆角长方形（#e74c3c）整条绘制
    - 阴爻：蓝色圆角长方形（#3498db）分两段绘制，中间留间隙（yin_gap）
    - 手工模式下可点击爻线切换阴阳（line_toggled 信号通知外部同步）

导出类：
    HexagramDrawer(QWidget): 六爻卦象绘制器

导出函数（模块级工具）：
    _app_font()     — 获取当前 QApplication 字体（未初始化时返回默认 16pt）
    compute_sizes() — 近似计算绘制尺寸（模块级默认值，精确计算用 QFontMetrics）

被哪些文件引用：
    - divination_panel.py: QiguaPanel 将此组件嵌入左侧分栏，调用 set_lines() 显示起卦结果
    - result_view.py:      通过 divination_panel 间接使用
    - yijing_viewer.py:    通过 refresh_font_size() → set_font_size() 刷新字体
    - main_window.py:      通过 appearance_manager → refresh_text_color() 刷新文字颜色

依赖关系（本文件导入）：
    - hexagram_loader.py: get_gua_by_xiantian() — 根据上/下卦先天数查找六十四卦数据
    - hexagram_calc.py:   _yang_to_xiantian() — 将 3 爻阴阳列表转换为先天数 1-8
    - PySide6.QtGui:      QPainter/QColor/QFont/QFontMetrics — 矢量绘制

═══════════════════════════════════════════════════════════════
关键公式：bar 中心与右侧面板控件行中心对齐
═══════════════════════════════════════════════════════════════

右侧面板每行是一个固定高度 line_h 的容器，控件垂直居中于行内。
左侧卦象的爻线 bar 中心必须与右侧对应行中心在 Y 方向上严格对齐，
这样才能保证爻线不与相邻行的控件错位。

    center_y = offset_y + name_area_h + (5 - i) * line_h + line_h // 2

    其中：
        offset_y          整体垂直偏移（微调用，默认 0）
        name_area_h       顶部卦名区域高度（必须先加，否则 bar 会偏上）
        (5 - i) * line_h  第 i 爻的起始 Y（i=0 是初爻=最下面=第 6 行，所以 5-i）
        line_h // 2        行高的一半 → 从行顶部偏移到行中心

    对照右侧面板：
        右侧每一行 container.setFixedHeight(line_h)
        checkbox/label 在容器内垂直居中
        所以控件中心 Y = 容器顶部 + line_h // 2

    两边都用 line_h // 2 做中心偏移，因此爻线与控件行严格对齐。

    验证：当 name_area_h = 58, line_h = 40, offset_y = 0
          - 初爻(i=0) bar 中心: 0 + 58 + 5*40 + 20 = 278
          - 上爻(i=5) bar 中心: 0 + 58 + 0*40 + 20 = 78
          - 卦名在 Y=[0, 58] 区域居中，6 爻紧跟其后

═══════════════════════════════════════════════════════════════
可配置参数（通过 configure() 或 set_font_size() 设置）
═══════════════════════════════════════════════════════════════

    line_h      — 每爻行高（与右侧面板行高对齐的关键参数）
                 公式: fm.height() + 12（12 = CSS padding: 6px top + 6px bottom）
    bar_h       — 爻条高度（dfont_size * 0.8，最低 8px）
    bar_w       — 阳爻总宽度（font_size * 6.25）
    yin_gap     — 阴爻中间间隙（font_size * 0.5，最低 4px）
    name_area_h — 顶部卦名区域高度（max(16, fm.height())，确保卦名完整显示）
    offset_y    — 整体垂直偏移（正=下移，负=上移，微调对齐用）

═══════════════════════════════════════════════════════════════
字号传播链（字体变更时）
═══════════════════════════════════════════════════════════════

    apply_appearance() → yijing_viewer.refresh_font_size()
        → qigua_panel.refresh_font_size() → drawer.set_font_size()
        → 所有面板 _update_panel_layout()

═══════════════════════════════════════════════════════════════
颜色传播链（外观背景色变更时）
═══════════════════════════════════════════════════════════════

    apply_appearance() → yijing_viewer.refresh_text_color()
        → qigua_panel.refresh_text_color() → drawer.set_text_color()
"""
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QMouseEvent

from .hexagram_loader import get_gua_by_xiantian
from .hexagram_calc import _yang_to_xiantian


def _app_font() -> QFont:
    """
    获取当前 QApplication 的全局字体（含 family + pointSize）

    设计意图：
        所有绘制参数（行高、条高、间隙）都基于当前应用字体计算，
        确保卦象绘制与右侧面板的控件尺寸保持一致。
        main_window.py 在启动时调用 QApplication.setFont() 设置全局字体，
        本函数读取该字体；如果 QApplication 尚未初始化，返回默认 16pt。

    Returns:
        QFont: 当前应用字体。如果 QApplication 未实例化，返回默认 QFont(16pt)

    使用示例:
        font = _app_font()
        painter.setFont(font)
        print(font.pointSize())  # 16 或用户在设置面板中选择的字号
    """
    app = QApplication.instance()
    if app:
        return QFont(app.font())
    f = QFont()
    f.setPointSize(16)
    return f


def compute_sizes(font_size: int) -> dict:
    """
    近似公式计算绘制尺寸（模块级默认值，不用 QFontMetrics）

    这是一个快速近似函数，用于在 QFontMetrics 不可用时提供默认值。
    实际运行时，HexagramDrawer._apply_font() 会使用 QFontMetrics 做精确计算。
    此函数仅用于初始化模块级常量 _DEFAULT。

    参数:
        font_size: 字体字号（point size），如 16

    返回:
        dict: 包含以下键值
            - "line_h":      每爻行高，max(28, font_size * 2.2)
            - "bar_h":       爻条高度，max(8, font_size * 0.8)
            - "name_area_h": 卦名区域高度，max(8, font_size * 0.55)
            - "bar_w":       阳爻总宽度，font_size * 6.25
            - "yin_gap":     阴爻中间间隙，max(4, font_size * 0.5)

    使用示例:
        sizes = compute_sizes(16)
        print(sizes["line_h"])  # 35
        print(sizes["bar_w"])   # 100

    注意:
        此函数的值是近似的，HexagramDrawer 实例化后会立即用 QFontMetrics
        重新计算并覆盖这些值。保留此函数仅用于模块级默认常量的初始化。
    """
    return {
        "line_h": max(28, int(font_size * 2.2)),
        "bar_h": max(8, int(font_size * 0.8)),
        "name_area_h": max(8, int(font_size * 0.55)),
        "bar_w": int(font_size * 6.25),
        "yin_gap": max(4, int(font_size * 0.5)),
    }


# ── 模块级默认绘制尺寸（在 HexagramDrawer 实例化前使用） ──
# 基于 16pt 字体的近似值，实际运行时会被 QFontMetrics 精确值覆盖
_DEFAULT = compute_sizes(16)
LINE_H = _DEFAULT["line_h"]           # 每爻行高默认值
BAR_H = _DEFAULT["bar_h"]             # 爻条高度默认值
NAME_AREA_H = _DEFAULT["name_area_h"] # 卦名区域高度默认值
BAR_W = _DEFAULT["bar_w"]             # 阳爻总宽度默认值
YIN_GAP = _DEFAULT["yin_gap"]         # 阴爻中间间隙默认值

# 爻线颜色常量（硬编码，不随外观主题变化 — 仅绘图的 QColor 对象）
# 红色传统上象征阳（刚健、光明），蓝色象征阴（柔顺、承载）
_YANG_COLOR = QColor("#e74c3c")  # 红色阳爻 — 用 QColor 避免每帧重复解析字符串
_YIN_COLOR = QColor("#3498db")   # 蓝色阴爻 — 同上


class HexagramDrawer(QWidget):
    """
    六爻卦象绘制器 — 在起卦面板左侧显示卦名的可视化组件

    布局结构:
        ┌──────────────────────┐
        │   ䷀ 乾为天  (卦名区)    │ ← name_area_h 高度，粗体居中
        ├──────────────────────┤
        │  ═══════════  (上爻)  │ ← 第 6 爻，index=5
        │  ═══════════  (五爻)  │
        │  ═══╗   ╔═══  (四爻)  │ ← 阴爻分两段，中留 gap
        │  ═══════════  (三爻)  │
        │  ═══╗   ╔═══  (二爻)  │
        │  ═══════════  (初爻)  │ ← 第 1 爻，index=0
        └──────────────────────┘

    爻序约定:
        - 列表索引 0 = 初爻（最下面），索引 5 = 上爻（最上面）
        - 绘制时从下而上：Y 坐标用 (5 - i) * line_h 实现视觉上的自下而上
        - 这与《易经》传统读法一致（从下往上读）

    交互模式:
        - 非手工模式：仅显示卦象，鼠标不响应点击
        - 手工模式（set_clickable(True)）：点击爻线切换阴阳，发射 line_toggled 信号

    Class Attributes:
        line_toggled: Signal(int) — 爻被点击切换后发射，参数为爻索引 (0-5)

    Instance Attributes:
        _yang_lines:   list[bool] — 6 爻当前阴阳状态，True=阳 False=阴，索引 0=初爻
        _clickable:    bool       — 是否允许点击切换爻线（手工模式为 True）
        _gua_name:     str        — 当前卦名（含 Unicode 符号），如 "䷀ 乾为天"
        _text_color:   str        — 卦名文字颜色 CSS 字符串，如 "#1d1d1f"
        _font_size:    int        — 当前字体字号 (pointSize)
        _line_h:       int        — 每爻行高，由 QFontMetrics 精确计算
        _bar_h:        int        — 爻条高度
        _bar_w:        int        — 阳爻总宽度
        _yin_gap:      int        — 阴爻中间间隙
        _name_area_h:  int        — 卦名区域高度
        _offset_y:     int        — 整体垂直偏移（微调与右侧面板对齐）
    """

    # ── 信号 ──
    # 当爻线被点击切换阴阳时发射，参数为被切换的爻索引 (0-5, 0=初爻)
    # 连接方：divination_panel.py 中接收此信号以同步手动输入面板的复选框状态
    line_toggled = Signal(int)

    def __init__(self, parent=None):
        """
        构造 HexagramDrawer 实例

        初始化流程：
        1. 设置默认 6 爻全为阳爻（_yang_lines = [True]*6）
        2. 从 QApplication 获取当前字体，用 QFontMetrics 精确计算所有绘制尺寸
        3. 启用鼠标追踪（setMouseTracking(True)），以便在手工模式下实时响应鼠标
        4. 计算并固定 widget 尺寸（宽度由卦名宽度 + bar_w 决定，高度由 name_area_h + 6*line_h 决定）

        参数:
            parent: QWidget | None — 父控件，通常为 divination_panel 中的左侧容器

        使用示例:
            drawer = HexagramDrawer(parent=left_container)
            drawer.set_lines([True, False, True, True, False, True])  # 设置具体卦象
        """
        super().__init__(parent)
        # 初始状态：6 爻全阳（乾卦），后续由 set_lines() 覆盖
        self._yang_lines: list[bool] = [True] * 6
        self._clickable = False                  # 默认不可点击，仅显示
        self._gua_name = ""                      # 卦名初始为空，set_lines() 后自动更新
        self._text_color = "#1d1d1f"             # 卦名文字颜色默认值（浅底黑字）
        self._name_fs = 0                         # 卦名字号偏移（相对系统字号的差值）
        self._disabled_mode = False               # 灰色禁用模式（0动爻时变卦用）
        self._disabled_color = QColor("#999999")  # 禁用时的爻线颜色
        self._wuxing_mode = False                 # 五行颜色模式（互卦用，上下卦分色）
        self._wuxing_upper_color = QColor("#e74c3c")  # 上卦五行颜色（爻线4-6）
        self._wuxing_lower_color = QColor("#e74c3c")  # 下卦五行颜色（爻线1-3）
        self._custom_title = ...                  # 自定义标题：...=默认gua_name, None=不画, str=替换
        self._fushen_texts: list[str | None] = [None] * 6  # 伏神文字（0=初爻..5=上爻）
        self._fushen_fs_offset = -4
        self._fushen_color = "#999999"
        self._fushen_bold = True
        self._fushen_highlight_line: int | None = None  # 高亮行索引（0=初爻..5=上爻），None=不高亮
        self._fushen_highlight_shift = 4  # 高亮行垂直偏移（px），正=远离爻线

        # ── 绘制参数（由 QFontMetrics 精确计算） ──
        # 获取当前应用字体作为基准，后续 set_font_size() 只改字号不改 family
        app_font = _app_font()
        self._font_size = app_font.pointSize()   # 记录当前字号
        self._line_h = 0                         # 每爻行高，_apply_font() 中赋值
        self._bar_h = 0                          # 爻条高度，同上
        self._bar_w = 0                          # 阳爻总宽度，同上
        self._yin_gap = 0                        # 阴爻间隙，同上
        self._name_area_h = 0                    # 卦名区高度，同上
        self._offset_y = 0                       # 整体垂直偏移，默认 0

        # 用当前字体初次计算所有绘制尺寸（_line_h / _bar_h / _name_area_h 等）
        self._apply_font(app_font, self._font_size)

        # 启用鼠标追踪 — 虽然当前未使用 hover 效果，但保留以支持未来扩展
        self.setMouseTracking(True)

    def _apply_font(self, font: QFont, font_size: int):
        """
        根据 QFont + 字号精确计算所有绘制尺寸（核心尺寸计算函数）

        这是 HexagramDrawer 最重要的内部函数，所有绘制坐标都基于这里的计算结果。
        使用 QFontMetrics 获取字体的精确度量值，确保跨平台一致性。
        字号变更时（用户调整设置面板字号），此函数会被 set_font_size() 重新调用。

        计算逻辑：
            - line_h = fm.height() + 12
              理由：右侧面板输入框 CSS 有 padding: 6px 10px（上下各 6px）。
              输入框自然高度 = 字体行高 + 上下 padding（12px）。
              让左侧行高与此一致，保证爻线与右侧控件行严格对齐。
            - name_area_h = max(16, fm.height())
              理由：卦名区域高度至少为字体行高，确保卦名完整显示（含 Unicode 卦符）。
              最低 16px 防止极小字号时卦名被裁切。
            - bar_h / bar_w / yin_gap 用 fontSize 比例计算，与 compute_sizes() 公式一致
            - 同时更新 widget 的固定宽高（_update_width / _update_height）

        参数:
            font:      QFont — 当前使用的字体对象（含 family, weight, italic 等属性）
            font_size: int   — 字号（pointSize），用于尺寸比例计算

        注意:
            - 此函数不触发重绘，调用方需要随后调用 self.update()
            - font 参数用于 QFontMetrics 获取精确字符度量，font_size 用于比例公式
        """
        self._font_size = font_size
        fm = QFontMetrics(font)
        # 输入框自然高度 = 字体行高 + 上下padding(12)，与 CSS padding: 6px 10px 一致
        self._line_h = fm.height() + 12
        self._bar_h = max(8, int(font_size * 0.8))
        # 卦名区用 fm.height() 确保含 Unicode 卦符的完整显示；最低 16px 防裁切
        self._name_area_h = max(16, fm.height())
        self._bar_w = int(font_size * 6.25)
        self._yin_gap = max(4, int(font_size * 0.5))
        self._update_width(font)
        self._update_height()

    def _update_width(self, font: QFont | None = None):
        """
        根据 bar_w 和卦名宽度动态计算 widget 的 min/max 宽度

        宽度由两个因素中的较大者决定：
            1. bar_w + 30（爻条宽度 + 左右留白）
            2. 最长卦名宽度（粗体 "䷀ 火水未济" + 12px padding）

        使用粗体 QFontMetrics 测量卦名宽度，因为卦名在 paintEvent 中以粗体绘制。
        """
        if font is None:
            font = _app_font()
        bold_font = QFont(font)
        bold_font.setBold(True)
        bfm = QFontMetrics(bold_font)
        name_w = bfm.horizontalAdvance("䷀ 火水未济") + 12
        min_w = max(self._bar_w + 30, name_w)
        self.setMinimumWidth(max(90, min_w))
        self.setMaximumWidth(max(110, min_w + 20))

    def _update_height(self):
        """
        根据 name_area_h 和 6 爻行高计算并设置 widget 的固定高度

        公式:
            fixed_height = name_area_h + 6 * line_h

        固定高度的原因：
            左侧卦象绘图区高度必须与右侧 6 行控件的总高度一致，
            以保证两侧在布局中上下对齐。使用 setFixedHeight 而非 setMinimumHeight
            防止 layout 额外拉伸产生空白。
        """
        self.setFixedHeight(self._name_area_h + 6 * self._line_h)

    # ── 尺寸属性（供外部面板对齐）──

    @property
    def line_h(self) -> int:
        """
        每爻行高（只读属性）

        外部面板（divination_panel.py）使用此值与右侧控件行高保持一致。
        右侧每行 container.setFixedHeight(drawer.line_h) 确保行高严格匹配。

        Returns:
            int: 当前每爻行高（像素），由 QFontMetrics 精确计算

        使用示例:
            drawer.line_h  # 例如 44（16pt 字体时）
            row_container.setFixedHeight(drawer.line_h)  # 右侧行与左侧爻对齐
        """
        return self._line_h

    @property
    def name_area_h(self) -> int:
        """
        顶部卦名区域高度（只读属性）

        外部面板可能需要知道卦名区域的高度来调整布局偏移。
        目前主要用于面板内部的对齐计算。

        Returns:
            int: 卦名区域高度（像素）
        """
        return self._name_area_h

    # ── 公共接口 ──

    def configure(self, line_h: int | None = None, bar_h: int | None = None,
                  bar_w: int | None = None, yin_gap: int | None = None,
                  name_area_h: int | None = None, offset_y: int | None = None):
        """
        手动覆盖绘制参数（未提供的参数保持不变）

        允许外部面板精细控制绘制尺寸。通常在面板初始化或布局调整时调用，
        用于微调卦象绘制与右侧控件之间的像素级对齐。
        与 set_font_size() 的区别：configure() 是逐个参数手动设置，
        set_font_size() 是用字体自动计算所有参数。

        参数:
            line_h:      int | None — 每爻行高（与右侧面板行对齐的关键值），None=保持当前
            bar_h:       int | None — 爻条高度，None=保持
            bar_w:       int | None — 阳爻总宽度，None=保持（变更时触发 _update_width）
            yin_gap:     int | None — 阴爻中间间隙，None=保持
            name_area_h: int | None — 顶部卦名区域高度，None=保持（变更时触发 _update_height）
            offset_y:    int | None — 整体垂直偏移（正=下移，负=上移），None=保持

        使用示例:
            # 微调垂直对齐
            drawer.configure(offset_y=2)  # 整体下移 2px
            # 自定义所有参数
            drawer.configure(line_h=44, bar_h=12, bar_w=100, yin_gap=8)
            # 只改行高，其他不变
            drawer.configure(line_h=48)

        注意:
            - 修改 bar_w 会自动触发 _update_width() 重新计算 widget 宽度
            - 修改 name_area_h 会自动触发 _update_height() 重新计算 widget 高度
            - 修改后自动调用 self.update() 触发重绘
        """
        if line_h is not None:
            self._line_h = line_h
        if bar_h is not None:
            self._bar_h = bar_h
        if bar_w is not None:
            self._bar_w = bar_w
        if yin_gap is not None:
            self._yin_gap = yin_gap
        if name_area_h is not None:
            self._name_area_h = name_area_h
        if offset_y is not None:
            self._offset_y = offset_y
        # bar_w 变更影响 widget 宽度，需重新计算 min/max width
        if bar_w is not None:
            self._update_width()
        # name_area_h 变更影响 widget 高度
        self._update_height()
        self.update()

    def set_font_size(self, font_size: int):
        """
        全局字体变更时调用 — 继承应用字体 family，只改字号

        此方法在用户通过设置面板调整字号时被触发。
        调用链：
            appearance_panel.on_font_size_changed()
                → appearance_manager.apply_appearance() (QApplication.setFont)
                → yijing_viewer.refresh_font_size()
                → qigua_panel.refresh_font_size() (遍历所有 QiguaPanel 实例)
                → drawer.set_font_size() (当前方法)

        行为：
            1. 从 QApplication 获取当前字体（保留 family / weight 等属性）
            2. 仅修改 pointSize
            3. 调用 _apply_font() 重新计算所有绘制尺寸
            4. 触发重绘

        参数:
            font_size: int — 新字号（pointSize），如 12, 16, 20

        使用示例:
            drawer.set_font_size(18)  # 整体字号变大，行高/条高/间隙等比例缩放
        """
        app_font = _app_font()
        app_font.setPointSize(font_size)
        self._apply_font(app_font, font_size)
        self.update()

    def set_text_color(self, text_color: str):
        """
        文字颜色变更时调用（深底白字/浅底黑字），触发重绘

        此方法在用户修改外观背景色/模式时被触发。
        调用链：
            appearance_panel.on_color_changed()
                → appearance_manager.apply_appearance()
                → yijing_viewer.refresh_text_color()
                → qigua_panel.refresh_text_color()
                → drawer.set_text_color() (当前方法)

        参数:
            text_color: str — CSS 颜色字符串，如 "#1d1d1f"（浅底黑字）或 "#f5f5f7"（深底白字）

        使用示例:
            drawer.set_text_color("#f5f5f7")  # 深色背景用白字
            drawer.set_text_color("#1d1d1f")  # 浅色背景用黑字
        """
        self._text_color = text_color
        self.update()

    def set_name_fs(self, offset: int):
        """
        设置卦名字号偏移（相对系统字号的差值）并触发重绘

        卦名最终字号 = 系统字号 + offset。
        offset 为正 → 卦名比正文大；offset 为负 → 卦名比正文小。

        Args:
            offset: int — 字号偏移量(pt)，如 4 表示卦名 = 系统字号 + 4

        使用示例:
            drawer.set_name_fs(4)   # 卦名比正文大 4pt
            drawer.set_name_fs(-2)  # 卦名比正文小 2pt
        """
        self._name_fs = offset
        self.update()

    def set_disabled_look(self, enabled: bool, color_hex: str = "#999999"):
        """
        设置灰色禁用模式（0动爻时变卦用）

        启用后所有爻线使用指定灰色绘制，营造"无变化/禁用"的视觉效果。
        set_lines() 不会自动关闭此模式，需显式调用 set_disabled_look(False) 恢复。

        Args:
            enabled: True=灰色禁用模式, False=正常颜色
            color_hex: CSS颜色字符串，如 "#b0b0b0"（浅底）或 "#777777"（深底）
        """
        self._disabled_mode = enabled
        self._disabled_color = QColor(color_hex)
        self.update()

    def set_wuxing_mode(self, enabled: bool, upper_color_hex: str = "#e74c3c",
                        lower_color_hex: str = ""):
        """
        设置五行颜色模式（互卦用，上下卦分色）

        互卦在梅花易数中拆成上下两个八卦来看：
          - 上卦（爻线 4-6/上三爻）→ upper_color_hex
          - 下卦（爻线 1-3/下三爻）→ lower_color_hex

        启用后不再使用默认红蓝配色，改为上下卦各自五行颜色。
        与互卦左侧八卦名标注的五行颜色保持一致。

        Args:
            enabled: True=五行颜色模式, False=正常红蓝配色
            upper_color_hex: 上卦五行颜色（爻线4-6），如 "#27ae60"（阳木绿）
            lower_color_hex: 下卦五行颜色（爻线1-3），空字符串=与上卦同色
        """
        self._wuxing_mode = enabled
        self._wuxing_upper_color = QColor(upper_color_hex)
        self._wuxing_lower_color = QColor(lower_color_hex or upper_color_hex)
        self.update()

    def set_custom_title(self, title):
        """
        设置自定义标题，覆盖默认的 卦符+卦名

        Args:
            title: ... = 使用默认 _gua_name（symbol + full_name）
                   None = 不绘制标题
                   str  = 用该字符串替换标题，字体样式不变
        """
        self._custom_title = title
        self.update()

    def set_fushen_texts(self, texts: list[str | None],
                          font_size_offset: int = -4,
                          color: str = "#999999",
                          bold: bool = True):
        """
        设置每爻下方显示的伏神文字（None = 该爻无伏神）

        Args:
            texts: list[str|None] — 长度6，索引0=初爻..5=上爻
            font_size_offset: 相对主字号的偏移（默认-4）
            color: 文字颜色
            bold: 是否加粗
        """
        self._fushen_texts = texts
        self._fushen_fs_offset = font_size_offset
        self._fushen_color = color
        self._fushen_bold = bold
        self.update()

    def set_fushen_highlight(self, line_idx: int | None):
        """
        设置伏神高亮行（主事爻对应伏神放大加粗贴近爻线）

        Args:
            line_idx: 0=初爻..5=上爻, None=取消高亮
        """
        self._fushen_highlight_line = line_idx
        self.update()

    def set_lines(self, yang_lines: list[bool]):
        """
        设置 6 爻阴阳状态（从下而上 [初..上]）

        这是外部设置卦象的主要入口。设置完成后：
        1. 自动调用 _update_gua_name() 通过 hexagram_calc 反查卦名
        2. 触发重绘显示新卦象

        参数:
            yang_lines: list[bool] — 长度必须为 6，索引 0=初爻, True=阳 False=阴
                        例如 [True, False, True, True, False, True] 表示
                        初爻阳、二爻阴、三爻阳、四爻阳、五爻阴、上爻阳

        使用示例:
            # 设置乾卦（6 阳）
            drawer.set_lines([True, True, True, True, True, True])
            # 设置坤卦（6 阴）
            drawer.set_lines([False, False, False, False, False, False])
            # 手动卦设置（从 hexagram_calc 返回的 lines_data 推导）
            drawer.set_lines([True, False, True, True, False, True])
            print(drawer.gua_name())  # "䷾ 水火既济" 或对应卦名

        注意:
            - 如果 yang_lines 长度不是 6，方法静默忽略（不更新、不报错）
            - set_lines() 覆盖所有 6 爻，不会保留之前的状态
            - 手工模式中单个爻的切换通过 mousePressEvent 处理，不调用此方法
        """
        if len(yang_lines) == 6:
            self._yang_lines = list(yang_lines)
            self._update_gua_name()
            self.update()

    def set_clickable(self, enabled: bool):
        """
        设置是否允许点击爻线切换阴阳（手工模式开关）

        启用时：
            - 鼠标悬停变为手型光标（PointingHandCursor）
            - 点击爻线触发 mousePressEvent → 切换阴阳 → 发射 line_toggled 信号

        禁用时：
            - 鼠标恢复默认箭头光标（ArrowCursor）
            - 点击爻线无响应

        参数:
            enabled: bool — True=启用手工点击切换, False=仅显示

        使用示例:
            # 进入手工模式
            drawer.set_clickable(True)
            # 退出手工模式（显示起卦结果时）
            drawer.set_clickable(False)
        """
        self._clickable = enabled
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)

    def yang_lines(self) -> list[bool]:
        """
        获取当前 6 爻阴阳状态的副本

        Returns:
            list[bool]: 长度为 6，索引 0=初爻, True=阳 False=阴
                        返回的是副本，修改返回值不影响内部状态

        使用示例:
            lines = drawer.yang_lines()
            yang_count = sum(lines)  # 阳爻数量
            print(f"阳爻: {yang_count}, 阴爻: {6 - yang_count}")
        """
        return list(self._yang_lines)

    def gua_name(self) -> str:
        """
        获取当前卦名（含 Unicode 卦符 + 中文全名）

        卦名由 _update_gua_name() 通过查询 hexagram_loader 自动生成。
        如果当前 6 爻组合不对应任何已知卦（理论上不会发生），返回空字符串。

        Returns:
            str: 卦名，格式如 "䷀ 乾为天"。无有效卦时返回 ""

        使用示例:
            name = drawer.gua_name()
            if name:
                symbol, full_name = name.split(" ", 1)
                print(f"Unicode卦符: {symbol}, 全名: {full_name}")
        """
        return self._gua_name

    def get_line_positions(self) -> list[dict]:
        """
        返回每爻在 widget 本地坐标系中的位置信息，用于对齐调试

        返回值顺序：初爻(index=0) → ... → 上爻(index=5)

        Returns:
            list[dict]: 每爻位置信息，包含:
                - line_num: int        爻序号 (1=初爻..6=上爻)
                - center_y: int        爻线中心 Y (widget 本地坐标)
                - top_y: int           爻线所在行顶部 Y
                - line_h: int          行高
                - bar_rect: (x,y,w,h)  爻条矩形 (widget 本地坐标)
        """
        positions = []
        bar_w = self._bar_w
        bar_h = self._bar_h
        bar_x = (self.width() - bar_w) // 2
        for i in range(6):
            row_top = self._offset_y + self._name_area_h + (5 - i) * self._line_h
            center_y = row_top + self._line_h // 2
            bar_y = center_y - bar_h // 2
            positions.append({
                "line_num": i + 1,
                "center_y": center_y,
                "top_y": row_top,
                "line_h": self._line_h,
                "bar_rect": (bar_x, bar_y, bar_w, bar_h),
            })
        return positions

    # ── 绘制 ──

    def paintEvent(self, event):
        """
        重绘事件 — 绘制卦名和 6 爻线（Qt 自动调用）

        这是 HexagramDrawer 的核心绘制方法。Qt 在以下情况自动调用：
        - widget 首次显示
        - 调用 self.update() 后
        - 窗口尺寸变化时（但本 widget 使用固定尺寸，通常不会）

        绘制步骤：
        1. 绘制卦名（顶部居中，粗体，颜色跟随 _text_color）
        2. 绘制 6 爻线（从下而上 = 视觉从上爻到初爻）
           - 阳爻：一条整红色圆角矩形
           - 阴爻：两条蓝色圆角矩形，中间留 _yin_gap 间隙

        坐标计算（核心对齐公式）：
            center_y = offset_y + name_area_h + (5 - i) * line_h + line_h // 2

            - offset_y:        整体垂直偏移（微调用）
            - name_area_h:     卦名区域高度，先越过卦名区
            - (5 - i) * line_h: 从卦名底部到第 i 爻行顶部的距离
                                i=0(初爻/最下) → 5*line_h
                                i=5(上爻/最上) → 0*line_h
            - line_h // 2:     行高的一半 → 行顶部偏移到行中心

        参数:
            event: QPaintEvent — Qt 传递的重绘事件对象（本方法不使用它）
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 获取 widget 当前宽度，每次 paintEvent 重新读取（支持 resize）
        w = self.width()
        cx = w // 2                      # 水平中心 X 坐标
        offset = self._offset_y          # 整体垂直偏移
        line_h = self._line_h            # 每爻行高
        bar_h = self._bar_h              # 爻条高度
        bar_w = self._bar_w              # 阳爻总宽度
        yin_gap = self._yin_gap          # 阴爻中间间隙
        name_h = self._name_area_h       # 卦名区域高度

        # ── 1. 卦名（顶部居中，粗体，字号跟随全局字体） ──
        # _custom_title: ... = 默认 _gua_name, None = 不画, str = 替换标题
        if self._custom_title is ...:
            title_text = self._gua_name
        else:
            title_text = self._custom_title

        if title_text:
            font = _app_font()
            font.setPointSize(self._font_size + self._name_fs)
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor(self._text_color))
            # drawText 在 Y=[offset, offset+name_h] 区域内水平+垂直居中绘制卦名
            p.drawText(0, offset, w, name_h,
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                       title_text)

        # ── 2. 爻线：bar 中心与右侧面板行中心对齐 ──
        # i=0 → 初爻（最下面），i=5 → 上爻（最上面）
        # 视觉上从上往下排列（上爻→五爻→四爻→三爻→二爻→初爻）
        for i in range(6):
            # bar 中心 Y = 偏移 + 卦名区 + 距卦名底部的行偏移 + 行内中心偏移
            # (5 - i): 上爻(i=5)紧贴卦名底部(偏移0)，初爻(i=0)在最下方(偏移5行)
            center_y = offset + name_h + (5 - i) * line_h + line_h // 2
            bar_top = int(center_y - bar_h // 2)  # bar 顶部 = 中心 - 半高
            is_yang = self._yang_lines[i]
            if self._wuxing_mode:
                # 五行模式：上下卦分色（i=0-2下卦, i=3-5上卦）
                color = self._wuxing_upper_color if i >= 3 else self._wuxing_lower_color
            elif self._disabled_mode:
                color = self._disabled_color  # 禁用模式：灰色
            else:
                color = _YANG_COLOR if is_yang else _YIN_COLOR  # 默认：红/蓝

            p.setPen(Qt.PenStyle.NoPen)  # 无边框，纯色填充
            p.setBrush(color)

            half_w = bar_w // 2  # 阳爻半宽（用于水平居中定位）
            if is_yang:
                # 阳爻：单条整矩形，从 cx - half_w 开始画 bar_w 宽
                # 圆角半径 3px，四个角均匀圆滑
                p.drawRoundedRect(int(cx - half_w), bar_top, bar_w, bar_h, 3, 3)
            else:
                # 阴爻：两条矩形，中间留 yin_gap 宽度的空隙
                # 左段宽 = (bar_w - yin_gap) // 2，右段同样宽
                # 左段从 cx - half_w 开始，右段从 cx + half_w - seg_w 结束
                seg_w = (bar_w - yin_gap) // 2  # 每段宽度
                p.drawRoundedRect(int(cx - half_w), bar_top, seg_w, bar_h, 3, 3)
                p.drawRoundedRect(int(cx + half_w - seg_w), bar_top, seg_w, bar_h, 3, 3)

        # ── 3. 伏神文字（爻线下方/上方空隙处） ──
        # 初爻(i=0)伏神显示在1/2爻之间（爻线上方），避免被底部解读方块遮挡
        if any(t for t in self._fushen_texts):
            fs_font = _app_font()
            fs_font.setPointSize(max(8, self._font_size + self._fushen_fs_offset))
            fs_font.setBold(self._fushen_bold)
            fm = QFontMetrics(fs_font)
            # 高亮字体（+2pt，加粗）
            hl_font = None
            hl_fm = None
            if self._fushen_highlight_line is not None:
                hl_font = _app_font()
                hl_font.setPointSize(max(9, self._font_size + self._fushen_fs_offset + 2))
                hl_font.setBold(True)
                hl_fm = QFontMetrics(hl_font)
            p.setPen(QColor(self._fushen_color))
            for i in range(6):
                txt = self._fushen_texts[i]
                if not txt:
                    continue
                bar_center_y = offset + name_h + (5 - i) * line_h + line_h // 2
                bar_h = self._bar_h
                is_hl = (i == self._fushen_highlight_line) and hl_font is not None
                if is_hl:
                    p.setFont(hl_font)
                    cur_fm = hl_fm
                    if i == 0:
                        # ⬇️ 初爻上方：文字底部对齐爻线顶部
                        draw_y = bar_center_y - bar_h // 2 - cur_fm.descent()
                    else:
                        # ⬆️ 其他爻下方：文字顶部对齐爻线底部
                        draw_y = bar_center_y + bar_h // 2 + cur_fm.ascent()
                else:
                    p.setFont(fs_font)
                    cur_fm = fm
                    if i == 0:
                        fushen_y = bar_center_y - line_h // 2
                    else:
                        fushen_y = bar_center_y + line_h // 2
                    draw_y = fushen_y + cur_fm.ascent() // 2
                tw = cur_fm.horizontalAdvance(txt)
                p.drawText(int(cx - tw // 2), int(draw_y), txt)

        p.end()

    def mousePressEvent(self, event: QMouseEvent):
        """
        鼠标点击事件 — 在手工艺模式下切换爻的阴阳状态

        点击检测流程：
        1. 检查 _clickable 是否为 True，否则忽略点击
        2. 将点击 Y 坐标减去 _offset_y 和 _name_area_h，排除卦名区域的点击
        3. 用整除计算点击落在哪一爻：(y - name_h) // line_h → 从上往下数
        4. 反转到从下往上的索引：line_idx = 5 - 行号
        5. 翻转该爻的状态，更新卦名，触发重绘，发射 line_toggled 信号

        参数:
            event: QMouseEvent — Qt 传递的鼠标事件对象
                   event.pos().y() 获取点击的 Y 坐标（相对于 widget 左上角）

        信号:
            发射 line_toggled(int) — 携带被切换的爻索引 (0-5, 0=初爻)

        使用示例（内部自动触发，无需手动调用）:
            # 在手工模式下，用户点击初爻位置：
            # 1. mousePressEvent 被调用
            # 2. _yang_lines[0] 从 True 翻转为 False
            # 3. _update_gua_name() 更新卦名
            # 4. line_toggled.emit(0) 通知外部面板同步复选框
        """
        if not self._clickable:
            return

        # 减去垂直偏移，使点击坐标与绘制坐标对齐
        y = event.pos().y() - self._offset_y
        # 点击在卦名区域内 → 忽略
        if y < self._name_area_h:
            return

        # 计算爻索引：(y - name_h) 是距卦名底部的距离
        # // line_h 得到从上往下第几行（0=紧贴卦名=上爻）
        # 5 - row 反转到从下往上的索引（0=初爻）
        line_idx = 5 - (y - self._name_area_h) // self._line_h
        if 0 <= line_idx <= 5:
            self._yang_lines[line_idx] = not self._yang_lines[line_idx]
            self._update_gua_name()
            self.update()
            # 发射信号通知外部面板同步状态（e.g., 手工输入面板的复选框）
            self.line_toggled.emit(line_idx)

    def _update_gua_name(self):
        """
        根据当前 6 爻阴阳状态反查六十四卦并更新 _gua_name

        计算流程：
        1. 取前 3 爻 (索引 0-2) → _yang_to_xiantian() → 下卦先天数 (1-8)
        2. 取后 3 爻 (索引 3-5) → _yang_to_xiantian() → 上卦先天数 (1-8)
        3. 以 (上卦数, 下卦数) 调用 get_gua_by_xiantian() 查询六十四卦数据
        4. 从结果中提取 symbol（Unicode 卦符）和 full_name（中文全名）
        5. 拼接为 "symbol full_name" 格式存入 _gua_name
        6. 未找到时 _gua_name = ""（理论上不会发生，所有 64 种组合都有对应卦）

        依赖:
            _yang_to_xiantian() (hexagram_calc): 3 爻阴阳 → 先天数
                [True, True, True]  → 1 (乾)    [True, False, True]  → 3 (离)
                [True, True, False] → 2 (兑)    [False, True, True]  → 4 (震)
                [True, False, False]→ 5 (巽)    [False, True, False] → 6 (坎)
                [False, False, True]→ 7 (艮)    [False, False, False]→ 8 (坤)
            get_gua_by_xiantian() (hexagram_loader): (上卦数, 下卦数) → 卦数据 dict
                示例: get_gua_by_xiantian(1, 2) → {"id":10, "full_name":"天泽履", "symbol":"䷉", ...}

        使用示例:
            # set_lines() 和 mousePressEvent 会自动调用此方法，
            # 通常不需要手动调用。
            drawer._yang_lines = [True, True, True, True, True, True]
            drawer._update_gua_name()
            print(drawer._gua_name)  # "䷀ 乾为天"
        """
        lower = _yang_to_xiantian(self._yang_lines[:3])   # 下卦 3 爻 → 先天数
        upper = _yang_to_xiantian(self._yang_lines[3:])   # 上卦 3 爻 → 先天数
        gua = get_gua_by_xiantian(upper, lower)
        if gua:
            self._gua_name = f"{gua.get('symbol', '')} {gua.get('full_name', '')}"
        else:
            self._gua_name = ""
