"""
chinese_cities.py 自动生成脚本

功能：从 ok_geo.csv.7z（原始坐标数据）提取区县级行政区经纬度，
      GCJ-02 → WGS-84 坐标转换后，自动生成 chinese_cities.py

用法：
  python3 generate_cities.py

输入文件（需放在本目录下）：
  ok_geo.csv.7z — 原始坐标+边界压缩包（14MB）

输出文件：
  chinese_cities.py — 2851 条区县级经纬度数据（194KB）

依赖：
  py7zr — 解压 7z 格式（pip install py7zr）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【本目录各文件说明】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ok_geo.csv.7z         原始坐标压缩包（含 center geo + polygon 边界）
  ok_data_level3.csv    行政区划层级表（仅编码/名称/拼音，不含坐标）
  chinese_cities.py     最终输出：区县级经纬度 Python 数据文件
  数据使用文档.txt       ok_geo.csv 字段说明文档

  ok_geo.csv.7z vs ok_data_level3.csv 的区别：
    - ok_geo.csv.7z:   有经纬度坐标(geo列) + 行政边界(polygon列)，14MB压缩
    - ok_data_level3.csv: 仅有行政区划编码层级关系(id/pid/deep/name/pinyin)，235KB
    两者互补：ok_data_level3.csv 提供区划层级关系，
            ok_geo.csv 在此基础上附加了坐标和边界数据。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【坐标转换说明】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  原始坐标系: GCJ-02（火星坐标系，高德/腾讯地图使用）
  目标坐标系: WGS-84（国际标准，GPS使用）
  转换算法:   eviltransform（开源算法，精度 < 2米）
              参考: https://github.com/googollee/eviltransform

  为什么需要转换：
    高德/腾讯地图出于国家安全考虑使用 GCJ-02 加密坐标系，
    与中国境内的 WGS-84 真实坐标存在 100-700 米偏移。
    真太阳时计算需要 WGS-84 坐标以确保精度。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【数据来源】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GitHub: xiangyuecn/AreaCity-JsSpider-StatsGov
  https://github.com/xiangyuecn/AreaCity-JsSpider-StatsGov
  数据版本: 2024-06-16
  原始数据综合了:
    - 国家统计局 2024 年行政区划代码
    - 民政部行政区划数据
    - 高德地图坐标
    - 腾讯地图行政区划数据
"""
import csv
import math
import os
import sys

# 增大 CSV 字段限制（polygon 列可能很大）
csv.field_size_limit(sys.maxsize)

try:
    import py7zr
except ImportError:
    print("请先安装 py7zr: pip install py7zr")
    sys.exit(1)

# ── GCJ-02 → WGS-84 坐标转换（eviltransform 算法）──
# 来源: https://github.com/googollee/eviltransform
# 这是开源的标准转换算法，非 AI 自行生成。

PI = math.pi
A = 6378245.0  # 椭球长半轴
EE = 0.00669342162296594323  # 椭球偏心率平方


def _transform_lat(x: float, y: float) -> float:
    """GCJ-02 纬度偏移量计算"""
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * PI) + 40.0 * math.sin(y / 3.0 * PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * PI) + 320.0 * math.sin(y * PI / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lon(x: float, y: float) -> float:
    """GCJ-02 经度偏移量计算"""
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * PI) + 40.0 * math.sin(x / 3.0 * PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * PI) + 300.0 * math.sin(x / 15.0 * PI)) * 2.0 / 3.0
    return ret


def gcj02_to_wgs84(lng: float, lat: float) -> tuple:
    """
    GCJ-02(火星坐标系) → WGS-84 单点转换

    算法原理：
      1. 计算 GCJ-02 相对于 WGS-84 的偏移量 (dlng, dlat)
      2. WGS-84 = GCJ-02 - 偏移量
    """
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lon(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * PI
    magic = math.sin(radlat)
    magic = 1 - EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrtmagic) * PI)
    dlng = (dlng * 180.0) / (A / sqrtmagic * math.cos(radlat) * PI)
    return lng - dlng, lat - dlat


# ── 主流程 ──────────────────────────────────────────

def generate(script_dir: str):
    """从 ok_geo.csv.7z 提取数据并生成 chinese_cities.py"""

    archive_path = os.path.join(script_dir, "ok_geo.csv.7z")
    if not os.path.exists(archive_path):
        print(f"错误：找不到 {archive_path}")
        print("请确保 ok_geo.csv.7z 与本脚本在同一目录下")
        sys.exit(1)

    # 步骤1: 从 7z 压缩包中解压 ok_geo.csv（145MB）
    print("步骤1: 解压 ok_geo.csv ...")
    extract_dir = os.path.join(script_dir, "_temp_extract")
    with py7zr.SevenZipFile(archive_path, 'r') as z:
        z.extractall(extract_dir)

    csv_path = os.path.join(extract_dir, "ok_geo.csv")

    # 步骤2: 解析 CSV，提取 deep=2（区县级）的条目
    print("步骤2: 解析 CSV 提取区县级数据 ...")
    entries = []
    skipped = 0

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)  # 跳过表头: id,pid,deep,name,ext_path,geo,polygon

        for row in reader:
            deep = int(row[2])
            if deep != 2:  # 只取区县级（deep=2），跳过省(0)市(1)
                continue

            ext_path = row[4]  # 全路径，如 "广东省 深圳市 南山区"
            geo = row[5]        # GCJ-02 坐标，如 "116.407387 39.904179"

            if not geo or not ext_path:
                skipped += 1
                continue

            # 解析省/市/区
            parts = ext_path.split()
            if len(parts) < 3:
                skipped += 1
                continue

            prov, city, district = parts[0], parts[1], parts[2]

            # 解析 GCJ-02 坐标
            try:
                gcj_lng, gcj_lat = geo.split()
                gcj_lng, gcj_lat = float(gcj_lng), float(gcj_lat)
            except ValueError:
                skipped += 1
                continue

            # 步骤3: GCJ-02 → WGS-84 转换
            wgs_lng, wgs_lat = gcj02_to_wgs84(gcj_lng, gcj_lat)

            entries.append((prov, city, district, round(wgs_lng, 4), round(wgs_lat, 4)))

    # 清理临时解压文件
    import shutil
    shutil.rmtree(extract_dir, ignore_errors=True)

    print(f"  提取到 {len(entries)} 条区县级数据（跳过 {skipped} 条）")

    # 步骤4: 去重
    seen = set()
    unique = []
    for e in entries:
        key = (e[0], e[1], e[2])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    print(f"  去重后: {len(unique)} 条")

    # 步骤5: 排序（按省→市→区）
    unique.sort(key=lambda x: (x[0], x[1], x[2]))

    # 步骤6: 写入 chinese_cities.py
    output_path = os.path.join(script_dir, "chinese_cities.py")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('"""\n')
        f.write('中国行政区划经纬度数据（区县级） — 供真太阳时定位使用\n')
        f.write('格式: (省, 市, 区/县, 经度, 纬度)  五元组\n')
        f.write('\n')
        f.write('⚠️ 此文件由 generate_cities.py 自动生成，请勿手动编辑\n')
        f.write('   运行 python3 generate_cities.py 即可重新生成\n')
        f.write('\n')
        f.write('数据来源:\n')
        f.write('  GitHub: xiangyuecn/AreaCity-JsSpider-StatsGov\n')
        f.write('  https://github.com/xiangyuecn/AreaCity-JsSpider-StatsGov\n')
        f.write('  原始数据: ok_geo.csv (2024-06-16 版)\n')
        f.write('  坐标系: GCJ-02 → WGS-84 (eviltransform 算法转换)\n')
        f.write('\n')
        f.write('数据文件:\n')
        f.write(f'  共 {len(unique)} 个县级行政区（区/县/县级市）\n')
        f.write('  覆盖 31 个省/自治区/直辖市 + 港澳台\n')
        f.write('"""\n')
        f.write('CITIES = [\n')

        current_prov = ""
        for prov, city, district, lng, lat in unique:
            if prov != current_prov:
                if current_prov:
                    f.write('\n')
                f.write(f'    # ── {prov} ──\n')
                current_prov = prov
            f.write(f'    ({prov!r}, {city!r}, {district!r}, {lng}, {lat}),\n')

        f.write(']\n')

    print(f"步骤3: 已生成 {output_path}")
    print(f"  文件大小: {os.path.getsize(output_path) / 1024:.0f} KB")
    print("完成！")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    generate(script_dir)
