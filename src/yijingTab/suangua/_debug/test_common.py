"""
综合测试 common.py — LineMarker / 干支历法 / 卦辞解读 / TimePickerDialog

═══════════════════════════════════════════════════════════════
运行: cd ~/Desktop/ZhouyiUnity && ZY_DEBUG=1 python3 src/qigua/suangua/_debug/test_common.py
═══════════════════════════════════════════════════════════════
"""
import sys
import os

# 确保项目根在 path 中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# ── 需要 QApplication 才能测试 QWidget 子类 ──
app = QApplication(sys.argv)

passed = 0
failed = 0

def check(cond, label):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✓ {label}")
    else:
        failed += 1
        print(f"  ✗ FAIL: {label}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ═══════════════════════════════════════════════════════════════
#  1. is_light_color
# ═══════════════════════════════════════════════════════════════
section("1. is_light_color 颜色亮度判断")

from src.yijingTab.suangua.common import is_light_color

check(is_light_color("#ffffff") == True, "#ffffff 亮色→True")
check(is_light_color("#000000") == False, "#000000 暗色→False")
check(is_light_color("#1d1d1f") == False, "#1d1d1f 暗色→False")
check(is_light_color("#ff0000") == False, "#ff0000 纯红→False (亮度约76)")
check(is_light_color("#00ff00") == True, "#00ff00 纯绿→True (亮度约150)")
check(is_light_color("#ffff00") == True, "#ffff00 纯黄→True")
check(is_light_color("fff") == False, "'fff' 短格式→False (len<6)")
check(is_light_color("") == False, "空字符串→False")


# ═══════════════════════════════════════════════════════════════
#  2. line_name
# ═══════════════════════════════════════════════════════════════
section("2. line_name 爻名计算")

from src.yijingTab.suangua.common import line_name

# 乾卦 (111111) — 全是阳爻 → 初九/九二/九三/九四/九五/上九
check(line_name("111111", 1) == "初九", "乾 初爻→初九")
check(line_name("111111", 2) == "九二", "乾 二爻→九二")
check(line_name("111111", 3) == "九三", "乾 三爻→九三")
check(line_name("111111", 4) == "九四", "乾 四爻→九四")
check(line_name("111111", 5) == "九五", "乾 五爻→九五")
check(line_name("111111", 6) == "上九", "乾 上爻→上九")

# 坤卦 (000000) — 全是阴爻 → 初六/六二/六三/六四/六五/上六
check(line_name("000000", 1) == "初六", "坤 初爻→初六")
check(line_name("000000", 2) == "六二", "坤 二爻→六二")
check(line_name("000000", 3) == "六三", "坤 三爻→六三")
check(line_name("000000", 4) == "六四", "坤 四爻→六四")
check(line_name("000000", 5) == "六五", "坤 五爻→六五")
check(line_name("000000", 6) == "上六", "坤 上爻→上六")

# 混合卦（如 既济 101010）
check(line_name("101010", 1) == "初九", "既济 初爻(阳)→初九")
check(line_name("101010", 2) == "六二", "既济 二爻(阴)→六二")
check(line_name("101010", 6) == "上六", "既济 上爻(阴)→上六")


# ═══════════════════════════════════════════════════════════════
#  3. compute_current_ganzhi / compute_day_ganzhi
# ═══════════════════════════════════════════════════════════════
section("3. 干支历法计算")

from src.yijingTab.suangua.common import compute_current_ganzhi, compute_day_ganzhi
import datetime

gz = compute_current_ganzhi()
check("year_ganzhi" in gz, "compute_current_ganzhi 含 year_ganzhi")
check("month_ganzhi" in gz, "compute_current_ganzhi 含 month_ganzhi")
check("day_ganzhi" in gz, "compute_current_ganzhi 含 day_ganzhi")
check("day_gan" in gz, "compute_current_ganzhi 含 day_gan")
check("hour_ganzhi" in gz, "compute_current_ganzhi 含 hour_ganzhi")
check(len(gz["year_ganzhi"]) == 2, f"年干支 {gz['year_ganzhi']} 长度为2")
check(len(gz["day_gan"]) == 1, f"日干 {gz['day_gan']} 长度为1")

# 验证参考日期: 2024-01-01 = 甲子日
day_gan, day_gz = compute_day_ganzhi(datetime.date(2024, 1, 1))
check(day_gan == "甲", f"2024-01-01 日干={day_gan} (期望甲)")
check(day_gz == "甲子", f"2024-01-01 日干支={day_gz} (期望甲子)")

# 验证偏移: 2024-01-02 = 乙丑日
day_gan2, day_gz2 = compute_day_ganzhi(datetime.date(2024, 1, 2))
check(day_gan2 == "乙", f"2024-01-02 日干={day_gan2} (期望乙)")
check(day_gz2 == "乙丑", f"2024-01-02 日干支={day_gz2} (期望乙丑)")

# 验证60天一循环: 2024-03-01 = 2024-01-01 + 60天 = 甲子
day_gan60, day_gz60 = compute_day_ganzhi(datetime.date(2024, 3, 1))
check(day_gan60 == "甲", f"2024-03-01 (+60天) 日干={day_gan60} (期望甲)")
check(day_gz60 == "甲子", f"2024-03-01 (+60天) 日干支={day_gz60} (期望甲子)")


# ═══════════════════════════════════════════════════════════════
#  4. gregorian_to_ganzhi_parts
# ═══════════════════════════════════════════════════════════════
section("4. gregorian_to_ganzhi_parts")

from src.yijingTab.suangua.common import gregorian_to_ganzhi_parts

parts = gregorian_to_ganzhi_parts(datetime.datetime(2024, 1, 1, 0, 0))
check(parts["day_gan"] == "甲", f"公历2024-01-01 日干={parts['day_gan']}")
check(parts["day_zhi"] == "子", f"公历2024-01-01 日支={parts['day_zhi']}")
check("year_gan" in parts, "含 year_gan")
check("year_zhi" in parts, "含 year_zhi")
check("month_gan" in parts, "含 month_gan")
check("month_zhi" in parts, "含 month_zhi")
check("hour_gan" in parts, "含 hour_gan")
check("hour_zhi" in parts, "含 hour_zhi")


# ═══════════════════════════════════════════════════════════════
#  5. ganzhi_to_approx_year
# ═══════════════════════════════════════════════════════════════
section("5. ganzhi_to_approx_year")

from src.yijingTab.suangua.common import ganzhi_to_approx_year

y2024 = ganzhi_to_approx_year("甲辰", 2024)
check(y2024 == 2024, f"甲辰 near 2024 = {y2024} (期望2024)")

y2025 = ganzhi_to_approx_year("乙巳", 2025)
check(y2025 == 2025, f"乙巳 near 2025 = {y2025} (期望2025)")


# ═══════════════════════════════════════════════════════════════
#  6. compatible_zhis
# ═══════════════════════════════════════════════════════════════
section("6. compatible_zhis 天干地支配对")

from src.yijingTab.suangua.common import compatible_zhis

yang_zhis = compatible_zhis("甲")
check(len(yang_zhis) == 6, f"甲(阳干) 兼容地支数={len(yang_zhis)} (期望6)")
check("子" in yang_zhis, "甲配阳支含子")
check("丑" not in yang_zhis, "甲不配阴支丑")

yin_zhis = compatible_zhis("乙")
check(len(yin_zhis) == 6, f"乙(阴干) 兼容地支数={len(yin_zhis)} (期望6)")
check("丑" in yin_zhis, "乙配阴支含丑")
check("子" not in yin_zhis, "乙不配阳支子")


# ═══════════════════════════════════════════════════════════════
#  7. build_interpretation
# ═══════════════════════════════════════════════════════════════
section("7. build_interpretation 卦辞/爻辞解读")

from src.yijingTab.suangua.common import build_interpretation, BLUE_BG, ORANGE_BG
from src.yijingTab.com.hexagram_loader import get_gua_by_xiantian

# 乾为天
qian = get_gua_by_xiantian(1, 1)
check(qian is not None, "加载乾为天数据")

# ── 0动爻 → 卦辞+彖曰（橙色）──
result0 = build_interpretation(qian, [], 16)
check(result0 is not None, "0动爻 返回结果")
if result0:
    html, bg = result0
    check("卦辞" in html, "0动爻 HTML含'卦辞'")
    check("彖曰" in html, "0动爻 HTML含'彖曰'")
    check(bg == ORANGE_BG, f"0动爻 背景色={bg} (期望{ORANGE_BG})")

# ── 1动爻 → 爻辞+象曰（蓝色）──
result1 = build_interpretation(qian, [1], 16)
check(result1 is not None, "1动爻(初九) 返回结果")
if result1:
    html, bg = result1
    check("初九" in html, "1动爻 HTML含'初九'")
    check("象曰" in html, "1动爻 HTML含'象曰'")
    check(bg == BLUE_BG, f"1动爻 背景色={bg} (期望{BLUE_BG})")

# 九五
result5 = build_interpretation(qian, [5], 16)
check(result5 is not None, "1动爻(九五) 返回结果")
if result5:
    html, bg = result5
    check("九五" in html, "5爻 HTML含'九五'")

# ── >1动爻 → 南师断法选爻辞+象曰（蓝色）──
result_multi = build_interpretation(qian, [2, 5], 16)
check(result_multi is not None, "多动爻 返回结果")
if result_multi:
    html, bg = result_multi
    check("九五" in html, "2动爻(同阳[2,5]) 取上动爻=九五")
    check("象曰" in html, "2动爻 含象曰")
    check(bg == BLUE_BG, f"2动爻 背景色={bg} (期望{BLUE_BG})")

# ── 坤卦测试 ──
kun = get_gua_by_xiantian(8, 8)
check(kun is not None, "加载坤为地数据")
result_kun = build_interpretation(kun, [1], 16)
check(result_kun is not None, "坤 1动爻(初六) 返回结果")
if result_kun:
    html, bg = result_kun
    check("初六" in html, "坤 HTML含'初六'")

# ── 字号变化 ──
result_fs20 = build_interpretation(qian, [1], 20)
check(result_fs20 is not None, "字号20 返回结果")
if result_fs20:
    html, bg = result_fs20
    check("font-size:20px" in html, "字号20 HTML含 font-size:20px")

result_fs12 = build_interpretation(qian, [], 12)
check(result_fs12 is not None, "字号12 返回结果")
if result_fs12:
    html, bg = result_fs12
    check("font-size:12px" in html, "字号12 HTML含 font-size:12px")


# ═══════════════════════════════════════════════════════════════
#  7b. build_interpretation 多动爻断法（南师规则）
# ═══════════════════════════════════════════════════════════════
section("7b. build_interpretation 多动爻断法（南师规则）")

from src.algorithms.mutiDongyaoSel import get_judgment_line

# 水火既济 (101010) — 上下卦不同阴阳
jiji = get_gua_by_xiantian(6, 3)
check(jiji is not None, "加载水火既济")

# ── 2动爻: 一阴一阳 → 取阴爻 ──
# 既济 [1(阳), 2(阴)] → 取六二
r2 = build_interpretation(jiji, [1, 2], 16)
check(r2 is not None, "2动爻(一阴一阳) 返回结果")
if r2:
    html, bg = r2
    check(bg == BLUE_BG, f"2动爻(一阴一阳) bg=BLUE_BG")
    check("六二" in html, "2动爻(一阴一阳) 爻名=六二")
    check("象曰" in html, "2动爻(一阴一阳) 含象曰")

# ── 2动爻: 同阳 → 取上动爻 ──
# 乾 [1, 3] 都是阳 → 取九三
r2b = build_interpretation(qian, [1, 3], 16)
check(r2b is not None, "2动爻(同阳) 返回结果")
if r2b:
    html, bg = r2b
    check(bg == BLUE_BG, f"2动爻(同阳) bg=BLUE_BG")
    check("九三" in html, "2动爻(同阳) 爻名=九三")
    check("象曰" in html, "2动爻(同阳) 含象曰")

# ── 2动爻: 同阴 → 取上动爻 ──
# 坤 [1, 3] 都是阴 → 取六三
kun = get_gua_by_xiantian(8, 8)
r2c = build_interpretation(kun, [1, 3], 16)
check(r2c is not None, "2动爻(同阴) 返回结果")
if r2c:
    html, bg = r2c
    check("六三" in html, "2动爻(同阴) 爻名=六三")
    check("象曰" in html, "2动爻(同阴) 含象曰")

# ── 3动爻 → 取中间爻 ──
r3 = build_interpretation(qian, [1, 3, 5], 16)
check(r3 is not None, "3动爻 返回结果")
if r3:
    html, bg = r3
    check(bg == BLUE_BG, f"3动爻 bg=BLUE_BG")
    check("九三" in html, "3动爻[1,3,5] 取中间爻=九三")
    check("象曰" in html, "3动爻 含象曰")

# ── 4动爻 → 取下静之爻（最靠初爻的静爻）──
r4 = build_interpretation(qian, [1, 2, 4, 5], 16)
check(r4 is not None, "4动爻 返回结果")
if r4:
    html, bg = r4
    check(bg == BLUE_BG, f"4动爻 bg=BLUE_BG")
    # 静爻: 3, 6 → 取下静 = 九三
    check("九三" in html, "4动爻[1,2,4,5] 取下静爻=九三")
    check("象曰" in html, "4动爻 含象曰")

# ── 5动爻 → 取静爻 ──
r5 = build_interpretation(qian, [1, 2, 3, 4, 5], 16)
check(r5 is not None, "5动爻 返回结果")
if r5:
    html, bg = r5
    check(bg == BLUE_BG, f"5动爻 bg=BLUE_BG")
    # 静爻: 6 → 上九
    check("上九" in html, "5动爻[1,2,3,4,5] 取静爻=上九")
    check("象曰" in html, "5动爻 含象曰")

# ── 6动爻 乾 → 用九 ──
r6 = build_interpretation(qian, [1, 2, 3, 4, 5, 6], 16)
check(r6 is not None, "6动爻(乾) 返回结果")
if r6:
    html, bg = r6
    check(bg == BLUE_BG, f"6动爻(乾) bg=BLUE_BG")
    check("用九" in html, "6动爻(乾) 爻名=用九")

# ── 6动爻 坤 → 用六 ──
r6b = build_interpretation(kun, [1, 2, 3, 4, 5, 6], 16)
check(r6b is not None, "6动爻(坤) 返回结果")
if r6b:
    html, bg = r6b
    check(bg == BLUE_BG, f"6动爻(坤) bg=BLUE_BG")
    check("用六" in html, "6动爻(坤) 爻名=用六")

# ── 6动爻 其他卦 → 变卦彖辞(橙色) ──
tun = get_gua_by_xiantian(6, 4)  # 水雷屯
if tun:
    r6c = build_interpretation(tun, [1, 2, 3, 4, 5, 6], 16)
    check(r6c is not None, "6动爻(其他卦) 返回结果")
    if r6c:
        html, bg = r6c
        check(bg == ORANGE_BG, f"6动爻(其他卦) bg=ORANGE_BG")
        check("彖辞" in html or "彖曰" in html, "6动爻(其他卦) 含彖辞")

# ── 1动爻 确认爻辞结构正确 ──
r1_check = build_interpretation(qian, [1], 16)
check(r1_check is not None, "1动爻 返回结果")
if r1_check:
    html, bg = r1_check
    check("初九" in html, "1动爻 爻名=初九")
    check("象曰" in html, "1动爻 含象曰")

# ── 0动爻 确认卦辞结构正确 ──
r0_check = build_interpretation(qian, [], 16)
check(r0_check is not None, "0动爻 返回结果")
if r0_check:
    html, bg = r0_check
    check("彖曰" in html, "0动爻 含彖曰")


# ═══════════════════════════════════════════════════════════════
#  8. _LineMarker 组件
# ═══════════════════════════════════════════════════════════════
section("8. _LineMarker 标注组件")

from src.yijingTab.suangua.common import _LineMarker

# ── 创建左标注（右对齐）──
lm_left = _LineMarker(align_right=True, parent=None)
check(lm_left is not None, "创建左标注")
check(lm_left._align_right == True, "左标注 _align_right=True")

# ── 配置几何参数 ──
lm_left.configure(name_area_h=20, line_h=40, offset_y=0, font_size=16)
check(lm_left._name_area_h == 20, "name_area_h=20")
check(lm_left._line_h == 40, "line_h=40")
check(lm_left.height() == 20 + 6 * 40, "总高度=260 (20+6*40)")

# ── 设置 badge 模式 ──
lm_left.set_badge_mode(True)
check(lm_left._badge_mode == True, "badge模式 开启")

lm_left.set_badge_padding_ox(5)
check(lm_left._badge_padding_ox == 5, "badge_padding=5")

# ── 设置 markers ──
lm_left.set_markers([
    (1, "体", "#ff0000"),       # 二爻位置
    (4, "用", "#0000ff"),       # 五爻位置
])
check(len(lm_left._markers) == 2, "设置2个marker")

# ── set_fs_offset ──
lm_left.set_fs_offset(-2)
check(lm_left._fs_offset == -2, "fs_offset=-2")

# ── set_text_color ──
lm_left.set_text_color("#ff0000")
check(lm_left._text_color == "#ff0000", "text_color=#ff0000")

# ── 创建右标注（左对齐）──
lm_right = _LineMarker(align_right=False, parent=None)
check(lm_right._align_right == False, "右标注 _align_right=False")
lm_right.configure(name_area_h=20, line_h=40, font_size=16)

# ── right marker set_markers with outlined mode ──
lm_right.set_markers([
    (2, "虎", "#cccccc", False, "#1d1d1f"),  # outlined=False, text_override="#1d1d1f"
])
check(len(lm_right._markers) == 1, "右标注 set_markers with text_override")

# ── set_text_color 传播 ──
lm_right.set_text_color("#eeeeee")
check(lm_right._text_color == "#eeeeee", "text_color传播到right marker")


# ═══════════════════════════════════════════════════════════════
#  9. _LineMarker 对齐坐标验证
# ═══════════════════════════════════════════════════════════════
section("9. _LineMarker 对齐坐标")

# 模拟 HexagramDrawer 的核心公式:
# center_y = offset_y + name_area_h + (5 - line_idx) * line_h + line_h // 2
name_area_h = 20
line_h = 40
offset_y = 0

def calc_center(line_idx):
    """与 drawer 相同的 center_y 公式"""
    return offset_y + name_area_h + (5 - line_idx) * line_h + line_h // 2

# 验证 6 行 center_y 是单调递减（上爻最小y→初爻最大y，从上到下画）
centers = [calc_center(i) for i in range(6)]
# line_idx 0=初爻(底最大), 5=上爻(顶最小) → 递减
for i in range(5):
    check(centers[i] > centers[i+1], f"line[{i}] center={centers[i]} > line[{i+1}] center={centers[i+1]}")

check(calc_center(0) == 20 + 5*40 + 20, f"初爻(下) center={calc_center(0)} (期望240)")
check(calc_center(5) == 20 + 0*40 + 20, f"上爻(顶) center={calc_center(5)} (期望40)")

# 验证 marker 的 center_y 与 drawer 一致
lm_test = _LineMarker(align_right=True)
lm_test.configure(name_area_h=20, line_h=40, offset_y=0, font_size=16)

# 模拟 paintEvent 中的 calc (无法真正触发,检查参数存储)
check(lm_test._name_area_h == 20, "存储 name_area_h=20")
check(lm_test._line_h == 40, "存储 line_h=40")
check(lm_test._offset_y == 0, "存储 offset_y=0")


# ═══════════════════════════════════════════════════════════════
#  10. MeihuaPanel 集成
# ═══════════════════════════════════════════════════════════════
section("10. MeihuaPanel 集成测试")

from src.yijingTab.suangua.meihua_panel import MeihuaPanel

mp = MeihuaPanel()
check(mp is not None, "创建 MeihuaPanel")
check(mp._ben_drawer is not None, "本卦 drawer 存在")
check(mp._hu_drawer is not None, "互卦 drawer 存在")
check(mp._bian_drawer is not None, "变卦 drawer 存在")
check(mp._interpret_frame is not None, "解读 frame 存在")
check(mp._interpret_label is not None, "解读 label 存在")

# ── 1动爻 ──
mp.set_gua_result(qian, [1])
check(len(mp._interpret_label.text()) > 0, "1动爻 解读label有内容")
check(mp._ben_right._badge_mode == True, "本卦右标注 badge模式")
check(len(mp._ben_right._markers) == 1, "1动爻 右标注1个marker")

# ── 0动爻 ──
mp.set_gua_result(qian, [])
check(len(mp._interpret_label.text()) > 0, "0动爻 解读label有内容")
check(mp._ben_right._badge_mode == False, "0动爻 右标注非badge模式(安静)")

# ── 字体变更 ──
mp.set_font_size(20)
check(mp._font_size == 20, "set_font_size 生效")
mp.set_font_size(16)  # 恢复

# ── 文字颜色变更 ──
mp.set_text_color("#eeeeee")
check(mp._text_color == "#eeeeee", "set_text_color 生效")
mp.set_text_color("#1d1d1f")  # 恢复

# ── compute_min_width ──
min_w = mp.compute_min_width()
check(min_w > 200, f"MeihuaPanel min_width={min_w} > 200")


# ═══════════════════════════════════════════════════════════════
#  11. LiuyaoPanel 集成
# ═══════════════════════════════════════════════════════════════
section("11. LiuyaoPanel 集成测试")

from src.yijingTab.suangua.liuyao_panel import LiuyaoPanel

lp = LiuyaoPanel()
check(lp is not None, "创建 LiuyaoPanel")
check(lp._drawer is not None, "六爻 drawer 存在")
check(lp._liushen_marker is not None, "六神 marker 存在")
check(lp._shiying_marker is not None, "世应 marker 存在")
check(lp._dongyao_marker is not None, "动爻 marker 存在")
check(lp._nayin_label is not None, "纳音 label 存在")
check(lp._interpret_frame is not None, "解读 frame 存在")
check(lp._interpret_label is not None, "解读 label 存在")

# ── 设置时间 ──
lp.set_time_ganzhi(gz)

# ── 1动爻 ──
lp.set_gua_result(qian, [1])
check(lp._liuyao_result is not None, "1动爻 liuyao分析结果存在")
check(len(lp._interpret_label.text()) > 0, "1动爻 解读label有内容")
check(len(lp._dongyao_marker._markers) == 1, "1动爻 动爻marker=1个")

# ── 0动爻 ──
lp.set_gua_result(qian, [])
check(len(lp._interpret_label.text()) > 0, "0动爻 解读label有内容")

# ── 多动爻 ──
lp.set_gua_result(qian, [2, 5])
check(len(lp._interpret_label.text()) > 0, "多动爻 解读label有内容")
check(len(lp._dongyao_marker._markers) == 2, "2动爻 动爻marker=2个")

# ── 字体变更 ──
lp.set_font_size(20)
check(lp._font_size == 20, "set_font_size 生效")
lp.set_font_size(16)

# ── 文字颜色变更 ──
lp.set_text_color("#eeeeee")
check(lp._text_color == "#eeeeee", "set_text_color 生效")
lp.set_text_color("#1d1d1f")

# ── compute_min_width ──
min_w_liu = lp.compute_min_width()
check(min_w_liu > 200, f"LiuyaoPanel min_width={min_w_liu} > 200")


# ═══════════════════════════════════════════════════════════════
#  12. SuanguaPanel 集成
# ═══════════════════════════════════════════════════════════════
section("12. SuanguaPanel 集成测试")

from src.yijingTab.suangua.suangua_panel import SuanguaPanel

sp = SuanguaPanel()
check(sp is not None, "创建 SuanguaPanel")
check(sp._meihua_panel is not None, "梅花子面板存在")
check(sp._liuyao_panel is not None, "六爻子面板存在")

# ── 刷新字体 ──
sp.refresh_font_size(18)
check(sp._font_size == 18, "refresh_font_size 生效")
sp.refresh_font_size(16)

# ── 刷新颜色 ──
sp.refresh_text_color("#cccccc")
check(sp._text_color == "#cccccc", "refresh_text_color 生效")
sp.refresh_text_color("#1d1d1f")

# ── 方法切换 ──
sp.switch_method("liuyao")
check(sp._current_method == "liuyao", "切换到六爻")
sp.switch_method("meihua")
check(sp._current_method == "meihua", "切换回梅花")


# ═══════════════════════════════════════════════════════════════
#  13. 边界条件
# ═══════════════════════════════════════════════════════════════
section("13. 边界条件")

# ── line_name 边界 ──
check(line_name("111111", 1) == "初九", "pos=1 OK")
check(line_name("111111", 6) == "上九", "pos=6 OK")

# ── build_interpretation 不存在的爻 ──
result_bad = build_interpretation(qian, [7], 16)  # 爻位7不存在
check(result_bad is None, "爻位7 返回None")

# ── 空 changing_lines ──
result_empty = build_interpretation(qian, [], 16)
check(result_empty is not None, "空列表 返回卦辞")

# ── build_interpretation 无效数据 ──
result_invalid = build_interpretation({}, [1], 16)
check(result_invalid is None, "空dict 返回None")

# ── _LineMarker 空 markers ──
lm_empty = _LineMarker(align_right=True)
lm_empty.configure(20, 40, font_size=16)
lm_empty.set_markers([])
check(len(lm_empty._markers) == 0, "空markers OK")


# ═══════════════════════════════════════════════════════════════
#  结果汇总
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"  测试结果: {passed} 通过, {failed} 失败 (共 {passed+failed})")
print(f"{'='*60}")

if failed > 0:
    print(f"\n  ❌ {failed} 个测试失败!")
    sys.exit(1)
else:
    print(f"\n  ✓ 全部 {passed} 个测试通过!")
    sys.exit(0)
