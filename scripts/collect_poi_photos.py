# -*- coding: utf-8 -*-
"""
桂山岛POI实景照片批量采集
方法: 高德POI详情照片 + 携程酒店照片 (替代百度街景, 海岛无街景车覆盖)

参考: xicha gis 智能定位/自选年份/full_pipeline.py 的采集框架
"""
import json, os, sys, time, random, re, requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.stdout.reconfigure(encoding='utf-8')

# ── 配置 ──
AMAP_KEY = "dd10c4dea07d700b83ae9c09cbaf0aad"  # from full_pipeline.py
POI_FILE = r'E:\珠海桂山岛案例\data\raw\amap_poi_guishan.json'
OUT_DIR = Path(r'E:\珠海桂山岛案例\output\streetview')
OUT_DIR.mkdir(parents=True, exist_ok=True)

UA_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

# ── 加载POI ──
with open(POI_FILE, 'r', encoding='utf-8') as f:
    pois = json.load(f)['pois']

print(f"POI总数: {len(pois)}")

# ── 1. 高德POI详情获取照片URL ──
def fetch_amap_detail(poi_id):
    """获取单个POI的详情(含照片)"""
    url = f"https://restapi.amap.com/v3/place/detail"
    params = {"id": poi_id, "key": AMAP_KEY, "output": "json"}
    try:
        r = requests.get(url, params=params, timeout=10,
                        headers={"User-Agent": random.choice(UA_LIST)})
        data = r.json()
        if data.get("status") == "1" and data.get("pois"):
            poi = data["pois"]
            if isinstance(poi, list) and len(poi) > 0:
                poi = poi[0]
            photos = poi.get("photos", [])
            if isinstance(photos, dict):
                photos = [photos]
            return photos
    except Exception as e:
        pass
    return []

# 先检查已有的照片URL
existing_photos = {}
for p in pois:
    ph = p.get("photos", [])
    if ph:
        existing_photos[p["poi_id"]] = ph

print(f"已有照片URL的POI: {len(existing_photos)}")

# 获取缺失POI的详情
need_detail = [p for p in pois if p["poi_id"] not in existing_photos]
print(f"需要获取详情的POI: {len(need_detail)}")

for i, p in enumerate(need_detail):
    photos = fetch_amap_detail(p["poi_id"])
    if photos:
        existing_photos[p["poi_id"]] = photos
        p["photos"] = photos
    if (i+1) % 10 == 0:
        print(f"  详情获取: {i+1}/{len(need_detail)}")
    time.sleep(0.15)

print(f"总共有照片URL的POI: {len(existing_photos)}")

# 统计总照片数
total_urls = sum(len(v) if isinstance(v, list) else 1 for v in existing_photos.values())
print(f"总照片URL数: {total_urls}")

# ── 2. 下载照片 ──
def safe_filename(name):
    """去除文件名中的非法字符"""
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()

def download_photo(url, filepath):
    """下载单张照片"""
    try:
        r = requests.get(url, timeout=15,
                        headers={"User-Agent": random.choice(UA_LIST),
                                 "Referer": "https://map.baidu.com/"})
        if r.status_code == 200 and len(r.content) > 1000:
            # 检查是否为JPEG/PNG
            if r.content[:2] == b'\xff\xd8' or r.content[:4] == b'\x89PNG':
                with open(filepath, 'wb') as f:
                    f.write(r.content)
                return len(r.content)
    except Exception:
        pass
    return 0

# 创建目录结构: streetview/<POI名>/<POI_ID>/
stats = {"total": 0, "downloaded": 0, "skipped": 0, "failed": 0}
poi_photo_info = []

for p in pois:
    pid = p["poi_id"]
    name = safe_filename(p["name"])
    cat = p.get("category", "其他")

    photos = existing_photos.get(pid, [])
    if not photos:
        continue

    poi_dir = OUT_DIR / f"{cat}_{name}" / pid
    poi_dir.mkdir(parents=True, exist_ok=True)

    photo_list = photos if isinstance(photos, list) else [photos]
    poi_downloaded = 0

    for idx, ph in enumerate(photo_list):
        stats["total"] += 1
        # 提取URL
        if isinstance(ph, dict):
            url = ph.get("url", "")
            title = ph.get("title", f"photo_{idx}")
        elif isinstance(ph, str):
            url = ph
            title = f"photo_{idx}"
        else:
            continue

        if not url or not url.startswith("http"):
            stats["failed"] += 1
            continue

        # 文件路径
        title_safe = safe_filename(str(title)) if title else f"photo_{idx}"
        ext = ".jpg" if ".jpg" in url.lower() or "showpic" in url else ".png"
        fpath = poi_dir / f"{title_safe}{ext}"

        if fpath.exists():
            stats["skipped"] += 1
            poi_downloaded += 1
            continue

        # 下载
        size = download_photo(url, str(fpath))
        if size > 0:
            stats["downloaded"] += 1
            poi_downloaded += 1
        else:
            stats["failed"] += 1

        time.sleep(0.1)  # 限速

    poi_photo_info.append({
        "poi_id": pid,
        "name": p["name"],
        "category": cat,
        "photos": poi_downloaded,
        "dir": str(poi_dir),
    })

print(f"\n下载完成:")
print(f"  总URL: {stats['total']}")
print(f"  成功下载: {stats['downloaded']}")
print(f"  已存在跳过: {stats['skipped']}")
print(f"  失败: {stats['failed']}")

# ── 3. 生成索引文件 ──
index_path = OUT_DIR / "photo_index.json"
with open(index_path, 'w', encoding='utf-8') as f:
    json.dump(poi_photo_info, f, ensure_ascii=False, indent=2)

print(f"\n索引文件: {index_path}")
print(f"\n按类别统计:")
from collections import Counter
cat_cnt = Counter(p["category"] for p in poi_photo_info if p["photos"] > 0)
for cat, cnt in cat_cnt.most_common():
    total_photos = sum(p["photos"] for p in poi_photo_info if p["category"] == cat)
    print(f"  {cat}: {cnt}个POI, {total_photos}张照片")

# 显示前10个有照片的POI
print(f"\nTOP10照片数:")
for p in sorted(poi_photo_info, key=lambda x: -x["photos"])[:10]:
    if p["photos"] > 0:
        print(f"  {p['name']}: {p['photos']}张 ({p['category']})")
