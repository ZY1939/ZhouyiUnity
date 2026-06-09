"""
qigua 目录 UI 布局参数集中配置

═══════════════════════════════════════════════════════════════
文件职责：统一管理起卦/算卦/梅花面板所有【可手动调整】的 UI 参数
         各面板通过 import 引用，修改默认值只需编辑此文件
═══════════════════════════════════════════════════════════════

使用方式：
    from .CONST_DEFINE_UI import QiguaConfig, SuanguaConfig, MeihuaConfig

    self._gap_module_left = QiguaConfig.gap_module_left

参数命名约定：
    gap_*   = 间距（px）
    fs_*    = 字号偏移（相对全局 font_size 的差值）
    ydist_* = 垂直距离（px）
"""


class QiguaConfig:
    """起卦面板 (divination_panel.py) UI 布局参数"""

    # 状态栏 Info/Warn 消息显示时长（ms）
    STATUS_MSG_DURATION = 5000

    # === header ===
    # 模组到窗口最左侧边缘的留白（px），控制起卦/算卦等所有模组的左侧统一缩进
    gap_module_left = 10
    # 方法选择器中心到面板顶部的垂直距离（px）
    ydist_menu2top = 20

    # === 模组间距 ===
    # 模组到窗口最右侧边缘的留白（px）
    gap_module_right = 10
    # 模组之间的水平间距（px），起卦↔算卦↔后续模组 通用
    gap_between_modules = 12
    # 算卦面板到起卦面板的水平间距（px）— 向后兼容别名
    gap_suangua = gap_between_modules
    # 右边框线距combo下拉框右边缘的留白距离（px）
    # 起点 = combo下拉框右边缘，_update_frame_max_width() 计算: ... + combo宽 + gap_border_right
    gap_border_right = 16
    # 起卦模组，卦图到右侧面板的水平距离（px）
    gap_drawer = 0

    # === 模组宽度控制 ===
    # 起卦模组占窗口可用宽度的百分比（0.0-1.0）
    # 实际宽度 = max(计算最小宽度, tab可用宽度 * panel_width_pct)
    panel_width_pct = 0.38
    # 起卦模组最小宽度额外留白(px)，叠加在计算最小宽度之上便于调试
    panel_min_extra = 0

    # === 起卦模组 -- 复选框 / 下拉框 ===
    # 勾选框到"动"字的距离（px，QCheckBox spacing）
    gap_cb_text = 1
    # "动"复选框到下拉框的额外间距（px），总间距 = "动"字宽度 + 此值
    gap_cb_combo_extra = 2
    # Lock复选框到"动爻设置"文字右边的间距（px）
    gap_lock = 8

    # === 报数面板 ===
    # Lock 文字到刷新按钮的间距（px）
    gap_refresh = 20
    # 刷新按钮图标尺寸比例（相对 name_h，默认 1.0 = name_h 的 100%）
    gap_refresh_icon_scale = 1.0
    # 报数面板按钮水平留白（px），按钮宽 = 两个汉字宽 + 此值
    gap_btn_pad = 30
    # 报数面板按钮高度（px）
    gap_btn_h = 38

    # === 结果区域 ===
    # 结果文字到卦图的垂直距离（px），负值=上移
    gap_result_top = -2
    # 卦图标题（卦名）字号偏移（相对全局字号的差值），正数=比正文大
    fs_name = 2
    # 结果文字字号偏移（相对全局字号的差值），正数=比正文大
    fs_result = 2
    # 动爻判断文字到结果文字的垂直间距（px）
    gap_judgment_top = 4
    # 动爻判断文字字号偏移（相对全局字号的差值）
    fs_judgment = 0

    # === 报数面板 mod / 余数 ===
    # mod 标签字号偏移（相对全局字号的减小量），上行"mod N"用
    fs_mod_top = 3
    # 余数值字号偏移（相对全局字号的减小量），下行余数用
    fs_mod_val = 3


class SuanguaConfig:
    """算卦面板 (suangua/suangua_panel.py) UI 布局参数"""

    # 方法选择器中心到面板顶部的垂直距离（px），与 QiguaConfig.ydist_menu2top 保持一致
    ydist_menu2top = 20
    # "算卦"标题距 suangua_frame 左边的距离（px）
    gap_suangua_left = 10
    # 卦图标题（卦名）字号偏移
    fs_name = 2

    # === 模组宽度控制 ===
    # 算卦模组占窗口可用宽度的百分比（0.0-1.0）
    # 实际宽度 = max(计算最小宽度, tab可用宽度 * panel_width_pct)
    panel_width_pct = 0.55
    # 算卦模组最小宽度额外留白(px)
    panel_min_extra = 0


class MeihuaConfig:
    """梅花面板 (suangua/meihua_panel.py) UI 布局参数"""

    # 卦图标题（卦名）字号偏移
    fs_name = 2
    # 三卦左边缘距面板左边缘的距离（px）
    gap_meihua_left = 0
    # 三卦右边缘距面板右边缘的最小距离（px）
    gap_meihua_right = 0
    # 标注文字到卦图的距离（px）
    #   左侧标注（体用/八卦名）：文字右边缘 → 卦图左边缘
    #   右侧标注（o/x）：       卦图右边缘 → 文字左边缘
    gap_marker_to_drawer = -4
    # 动爻符号（o/x）字号偏移（相对全局 font_size，正=更大）
    fs_offset_ox = 0
    # 体用/八卦名 字号偏移（相对全局 font_size，正=更大）
    fs_offset_tiyong = 0
    # o/x badge 轮廓比文字大的内边距（px），文字边缘到 badge 边缘的距离
    #   badge = 正方形 (w = h = fm_height + 2 * badge_padding_ox)
    #   o → 红圆（drawEllipse），x → 蓝圆角正方形（drawRoundedRect）
    badge_padding_ox = 0

    # === 卦列间距 ===
    # 卦列标注文字之间的额外间距（px），标注区域之外追加的留白
    #   = 0: 标注间距 = gap_marker_to_marker（最小值）
    #   > 0: 标注间距 = max(gap_marker_to_marker, gap_between_columns)
    gap_between_columns = 0
    # 两列标注文字之间的最小留白（px），防止标注贴在一起
    gap_marker_to_marker = 2


class LiuyaoConfig:
    """六爻面板 (suangua/liuyao_panel.py) UI 布局参数"""

    # 卦图标题（卦名）字号偏移
    fs_name = 2

    # 三卦左边缘距面板左边缘的距离（px）
    gap_liuyao_left = 0
    # 右边缘距面板右边缘的最小距离（px）
    gap_liuyao_right = 0

    # 标注文字到卦图的距离（px），负值=标注叠入卦图留白区
    gap_marker_to_drawer = -8

    # 六神标注 → 世应标注 水平间距（px）
    gap_liushen_to_shiying = 4

    # 动爻标注 → 纳音标注 水平间距（px）
    gap_dongyao_to_nayin = 2
    # 纳音标注 → 伏神标注 水平间距（px）
    gap_nayin_to_fushen = 2

    # badge 轮廓比文字大的内边距（px），六神/世应/动爻共用
    badge_padding = 0

    # 纳音边框线宽（px）
    nayin_border_width = 1
    # 纳音文字到边框的内边距（px）
    nayin_padding = 2

    # 六神字号偏移（相对全局 font_size，正=更大）
    fs_offset_liushen = 0
    # 世应字号偏移
    fs_offset_shiying = 0
    # 动爻符号字号偏移
    fs_offset_dongyao = 0
    # 纳音字号偏移
    fs_offset_nayin = 0

    # === 变卦相关 ===
    # 箭头宽度比例（相对 line_h，默认 0.55 = line_h 的 55%）
    arrow_width_scale = 0.55
    # 箭头及生克文字的间距统一复用 gap_liushen_to_shiying

    # === 动爻生克箭头/文字颜色 ===
    arrow_color_he = "#8e44ad"      # 比和（紫色）
    arrow_color_ke = "#e74c3c"      # 克（红色）
    arrow_color_sheng = "#27ae60"   # 生（绿色）
    # 生克文字 badge 内边距（px），badge = 正方形 (side = fm_height + 2 * padding)
    arrow_badge_padding = 1
