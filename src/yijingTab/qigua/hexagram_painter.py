"""
画卦接口（预留）— 后续在此实现完整的本卦/变卦爻象图绘制

═══════════════════════════════════════════════════════════════
文件职责：提供画卦 API 空壳，避免后续实现时调用方需要大改
═══════════════════════════════════════════════════════════════

当前状态：预留接口（所有方法为 pass）
后续功能：根据 GuaResult 在 QWidget 上绘制：
    - 本卦 6 爻（红色阳爻/蓝色阴爻，长方形）
    - 变卦 6 爻（动爻位置高亮/颜色变化）
    - 卦名和符号标注

被哪些文件调用：
    - result_view.py: ResultDisplay.show_result() → GuaPainter.draw_gua()
    - 未来可在 divination_panel.py 中直接调用以替代 HexagramDrawer

依赖：
    - bagua.py: GuaResult

用法示例（后续实现后）:
    from src.yijingTab.qigua.hexagram_painter import GuaPainter

    painter = GuaPainter()
    painter.draw_gua(my_widget, result)   # 在 my_widget 上绘制
    painter.clear(my_widget)              # 清空画布
"""
from PySide6.QtWidgets import QWidget
from ..com.bagua import GuaResult


class GuaPainter:
    """
    画卦绘制器 — 预留接口

    设计意图：
        - 与 HexagramDrawer（简单 6 爻阴阳显示）互补
        - 后续可绘制更丰富的卦象图（本卦+变卦并排、纳甲、六亲等）
        - 作为独立绘制器，不绑定特定 Widget，可复用到任何 QWidget canvas

    示例（后续实现后）:
        from src.yijingTab.qigua import GuaPainter
        canvas = QWidget()
        GuaPainter.draw_gua(canvas, result)
    """

    @staticmethod
    def draw_gua(canvas: QWidget, result: GuaResult):
        """
        在 canvas 上绘制本卦 + 变卦爻象图（预留接口，当前为空）

        Parameters:
            canvas: QWidget — 目标绘制画布（调用方需保证有足够尺寸）
            result: GuaResult — 起卦结果（含 ben_gua/bian_gua/lines_data 等）

        预期功能（后续实现）：
            1. 左侧绘制本卦 6 爻（红色阳爻/蓝色阴爻）
            2. 动爻位置标记变爻符号（○/×）
            3. 右侧绘制变卦 6 爻
            4. 顶部标注卦名和符号
        """
        pass  # TODO: 后续实现绘制逻辑

    @staticmethod
    def clear(canvas: QWidget):
        """
        清空画布（预留接口，当前为空）

        Parameters:
            canvas: QWidget — 要清空的画布
        """
        pass  # TODO
