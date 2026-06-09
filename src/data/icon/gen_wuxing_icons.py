"""
五行图标生成脚本

═══════════════════════════════════════════════════════════════
用法：python3 gen_wuxing_icons.py
输出：src/data/icon/wuxing/ 下 10 个 SVG 图标

阴阳对应（1=阳，0=阴）：
  木_1 = 大树(松树)      木_0 = 藤蔓
  火_1 = 太阳             火_0 = 红蜡烛
  水_1 = 波浪(江河)       水_0 = 单滴水滴 💧
  金_1 = 铁块(金属锭)     金_0 = 钻石
  土_1 = 砖墙             土_0 = 沙子
═══════════════════════════════════════════════════════════════
"""
import os

# 输出目录（相对于本脚本）
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wuxing")
os.makedirs(OUT_DIR, exist_ok=True)

# ── 图标定义：(文件名, svg内容) ──
ICONS = {
    # ═══════════════════════════════════════════
    # 木
    # ═══════════════════════════════════════════
    "wood_1.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <!-- 阳木：大树 — 松树造型，绿色 -->
  <rect x="10" y="16" width="4" height="5" rx="1" fill="#5D4037" stroke="none"/>
  <polygon points="12,1 3,10 7,10 5,16 19,16 17,10 21,10" fill="#4CAF50" stroke="none"/>
  <polygon points="12,1 3,10 7,10 5,16 19,16 17,10 21,10" fill="none" stroke="#2E7D32" stroke-width="0.8" stroke-linejoin="round"/>
</svg>''',

    "wood_0.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <!-- 阴木：藤蔓 — 弯曲蔓藤 + 小叶，浅绿 -->
  <path d="M4 22 Q8 9 12 6 Q15 4 18 3" stroke="#66BB6A" stroke-width="1.8" stroke-linecap="round" fill="none"/>
  <path d="M8 14 Q4 11 5 8" stroke="#81C784" stroke-width="1.8" stroke-linecap="round" fill="none"/>
  <circle cx="5" cy="7.5" r="2" fill="#A5D6A7" stroke="none"/>
  <path d="M13 7 Q16 4 17 2" stroke="#81C784" stroke-width="1.8" stroke-linecap="round" fill="none"/>
  <circle cx="17.5" cy="2" r="1.8" fill="#A5D6A7" stroke="none"/>
  <path d="M10 10.5 Q8 8 6 7.5" stroke="#A5D6A7" stroke-width="1.5" stroke-linecap="round" fill="none"/>
  <circle cx="5.5" cy="7" r="1.3" fill="#C8E6C9" stroke="none"/>
</svg>''',

    # ═══════════════════════════════════════════
    # 火
    # ═══════════════════════════════════════════
    "fire_1.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <!-- 阳火：太阳 — 圆面 + 光芒射线 -->
  <circle cx="12" cy="12" r="5" fill="#FF9800" stroke="none"/>
  <!-- 8条光芒 -->
  <line x1="12" y1="3" x2="12" y2="5.5" stroke="#FF9800" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="12" y1="18.5" x2="12" y2="21" stroke="#FF9800" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="3" y1="12" x2="5.5" y2="12" stroke="#FF9800" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="18.5" y1="12" x2="21" y2="12" stroke="#FF9800" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="5.6" y1="5.6" x2="7.4" y2="7.4" stroke="#FF9800" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="16.6" y1="16.6" x2="18.4" y2="18.4" stroke="#FF9800" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="5.6" y1="18.4" x2="7.4" y2="16.6" stroke="#FF9800" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="16.6" y1="7.4" x2="18.4" y2="5.6" stroke="#FF9800" stroke-width="2.5" stroke-linecap="round"/>
</svg>''',

    "fire_0.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <!-- 阴火：红色蜡烛 — 烛身 + 火焰 + 光晕 -->
  <!-- 光晕 -->
  <circle cx="12" cy="6" r="5" fill="#FFCDD2" stroke="none" opacity="0.4"/>
  <!-- 火焰外层 -->
  <path d="M12 1 Q14.5 4 14 7 Q13.5 9 12 11 Q10.5 9 10 7 Q9.5 4 12 1Z" fill="#FF5722" stroke="none"/>
  <!-- 火焰内层 -->
  <path d="M12 2.5 Q13.5 5 13.2 7 Q12.8 8.5 12 10 Q11.2 8.5 10.8 7 Q10.5 5 12 2.5Z" fill="#FFEB3B" stroke="none"/>
  <!-- 烛身 -->
  <rect x="9" y="11" width="6" height="9" rx="1" fill="#F44336" stroke="none"/>
  <!-- 烛身高光 -->
  <rect x="10" y="11" width="2" height="9" rx="0.5" fill="#EF9A9A" stroke="none" opacity="0.5"/>
  <!-- 烛芯 -->
  <rect x="11.5" y="9.5" width="1" height="2" rx="0.3" fill="#212121" stroke="none"/>
</svg>''',

    # ═══════════════════════════════════════════
    # 水
    # ═══════════════════════════════════════════
    "water_1.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <!-- 阳水：波浪 — 代表江河奔流 -->
  <path d="M1 8 Q5 3 9 8 Q13 13 17 8 Q21 3 23 8" stroke="#1565C0" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <path d="M1 13 Q5 8 9 13 Q13 18 17 13 Q21 8 23 13" stroke="#1976D2" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <path d="M1 18 Q5 13 9 18 Q13 23 17 18 Q21 13 23 18" stroke="#1E88E5" stroke-width="2.5" stroke-linecap="round" fill="none"/>
</svg>''',

    "water_0.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <!-- 阴水：单滴水滴 💧 — 代表小溪/小水 -->
  <!-- 水滴主体 -->
  <path d="M12 2.5 Q12 2.5 8.5 8 Q5.5 13 5.5 17 Q5.5 21 8.5 22 Q10.5 22.8 12 22 Q13.5 22.8 15.5 22 Q18.5 21 18.5 17 Q18.5 13 15.5 8 Q12 2.5 12 2.5Z" fill="#64B5F6" stroke="#42A5F5" stroke-width="1" stroke-linejoin="round"/>
  <!-- 高光 -->
  <path d="M12 5 Q10.5 8 9.5 12 Q8.8 15 9 17" fill="none" stroke="#BBDEFB" stroke-width="1.5" stroke-linecap="round" opacity="0.7"/>
</svg>''',

    # ═══════════════════════════════════════════
    # 金
    # ═══════════════════════════════════════════
    "metal_1.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <!-- 阳金：铁块 — 3D立体金属锭 -->
  <!-- 顶面 -->
  <polygon points="12,2 20,6 12,10 4,6" fill="#B0BEC5" stroke="#78909C" stroke-width="1" stroke-linejoin="round"/>
  <!-- 正面 -->
  <polygon points="4,6 12,10 12,19 4,15" fill="#90A4AE" stroke="#78909C" stroke-width="1" stroke-linejoin="round"/>
  <!-- 右侧面 -->
  <polygon points="12,10 20,6 20,15 12,19" fill="#78909C" stroke="#607D8B" stroke-width="1" stroke-linejoin="round"/>
  <!-- 高光线 -->
  <line x1="8" y1="8" x2="8" y2="17" stroke="#CFD8DC" stroke-width="0.8" stroke-linecap="round" opacity="0.6"/>
</svg>''',

    "metal_0.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <!-- 阴金：钻石 — 宝石切割面造型 -->
  <!-- 钻石主体 -->
  <polygon points="12,1 21,8 12,22 3,8" fill="#80DEEA" stroke="#00BCD4" stroke-width="1" stroke-linejoin="round"/>
  <!-- 切面线 -->
  <line x1="12" y1="1" x2="12" y2="22" stroke="#4DD0E1" stroke-width="0.8"/>
  <line x1="3" y1="8" x2="21" y2="8" stroke="#4DD0E1" stroke-width="0.8"/>
  <!-- 高光 -->
  <polygon points="12,1 7,6 12,8 17,6" fill="#E0F7FA" stroke="none" opacity="0.6"/>
  <!-- 底尖高光 -->
  <polygon points="12,12 12,22 8,15" fill="#B2EBF2" stroke="none" opacity="0.3"/>
</svg>''',

    # ═══════════════════════════════════════════
    # 土
    # ═══════════════════════════════════════════
    "earth_1.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <!-- 阳土：砖墙 — 砖块堆叠图案 -->
  <rect x="2" y="2" width="20" height="20" rx="1" fill="#A1887F" stroke="#8D6E63" stroke-width="0.8"/>
  <line x1="2" y1="7.5" x2="22" y2="7.5" stroke="#8D6E63" stroke-width="1"/>
  <line x1="2" y1="13" x2="22" y2="13" stroke="#8D6E63" stroke-width="1"/>
  <line x1="2" y1="18.5" x2="22" y2="18.5" stroke="#8D6E63" stroke-width="1"/>
  <line x1="12" y1="2" x2="12" y2="7.5" stroke="#8D6E63" stroke-width="1"/>
  <line x1="6" y1="7.5" x2="6" y2="13" stroke="#8D6E63" stroke-width="1"/>
  <line x1="18" y1="7.5" x2="18" y2="13" stroke="#8D6E63" stroke-width="1"/>
  <line x1="12" y1="13" x2="12" y2="18.5" stroke="#8D6E63" stroke-width="1"/>
  <line x1="6" y1="18.5" x2="6" y2="22" stroke="#8D6E63" stroke-width="1"/>
  <line x1="18" y1="18.5" x2="18" y2="22" stroke="#8D6E63" stroke-width="1"/>
</svg>''',

    "earth_0.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <!-- 阴土：沙子 — 沙粒/小点簇 -->
  <path d="M3 20 Q6 15 9 18 Q12 13 15 17 Q18 14 21 19 L21 22 L3 22Z" fill="#D7CCC8" stroke="#BCAAA4" stroke-width="0.8" stroke-linejoin="round"/>
  <circle cx="5" cy="19" r="0.8" fill="#A1887F" stroke="none"/>
  <circle cx="7.5" cy="17.5" r="0.7" fill="#8D6E63" stroke="none"/>
  <circle cx="9" cy="20" r="0.9" fill="#A1887F" stroke="none"/>
  <circle cx="11" cy="18" r="0.7" fill="#8D6E63" stroke="none"/>
  <circle cx="13" cy="19.5" r="0.8" fill="#A1887F" stroke="none"/>
  <circle cx="15" cy="17" r="0.7" fill="#8D6E63" stroke="none"/>
  <circle cx="16.5" cy="20" r="0.9" fill="#A1887F" stroke="none"/>
  <circle cx="18" cy="18.5" r="0.6" fill="#8D6E63" stroke="none"/>
  <circle cx="6" cy="21.2" r="0.6" fill="#8D6E63" stroke="none"/>
  <circle cx="12" cy="21" r="0.7" fill="#8D6E63" stroke="none"/>
  <circle cx="17" cy="21.5" r="0.6" fill="#8D6E63" stroke="none"/>
  <circle cx="8" cy="16" r="0.6" fill="#D7CCC8" stroke="none"/>
  <circle cx="14" cy="15" r="0.5" fill="#D7CCC8" stroke="none"/>
  <circle cx="11" cy="14.5" r="0.6" fill="#D7CCC8" stroke="none"/>
</svg>''',
}


def gen():
    """生成所有五行图标到 OUT_DIR"""
    for name, svg in ICONS.items():
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg.strip() + "\n")
        size = os.path.getsize(path)
        print(f"  ✓ {name} ({size}B)")

    print(f"\n已生成 {len(ICONS)} 个图标 → {OUT_DIR}")


if __name__ == "__main__":
    gen()
