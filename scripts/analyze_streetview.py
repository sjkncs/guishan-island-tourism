# -*- coding: utf-8 -*-
import cv2, numpy as np, os, sys, json, math
import pandas as pd
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(r"E:\珠海桂山岛案例")
PHOTO_DIR = BASE / "数据采集" / "桂山岛" / "桂山岛" / "2026-07"
OUT_DIR = BASE / "output" / "streetview_analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def hsv_segmentation(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    total = img.shape[0] * img.shape[1]
    green = ((h >= 35) & (h <= 85) & (s > 40) & (v > 30)).astype(np.uint8)
    sky = ((h >= 90) & (h <= 130) & (s < 80) & (v > 150)).astype(np.uint8)
    cloud = ((s < 30) & (v > 180)).astype(np.uint8)
    sky = np.maximum(sky, cloud)
    bldg = ((s > 10) & (s < 60) & (v > 60) & (v < 180)).astype(np.uint8)
    bldg = np.clip(bldg - green - sky, 0, 1).astype(np.uint8)
    road = ((s < 40) & (v > 20) & (v < 120)).astype(np.uint8)
    road = np.clip(road - green - sky, 0, 1).astype(np.uint8)
    return {"green_ratio": float(green.sum()/total), "sky_ratio": float(sky.sum()/total),
            "building_ratio": float(bldg.sum()/total), "road_ratio": float(road.sum()/total),
            "green_mask": green, "sky_mask": sky, "building_mask": bldg, "road_mask": road}

def visual_quality(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness = float(hsv[:,:,2].mean() / 255.0)
    edges = cv2.Canny(gray, 50, 150)
    complexity = float(edges.sum() / (255 * edges.size))
    contrast = float(hsv[:,:,2].std() / 255.0)
    return {"brightness": brightness, "complexity": complexity, "contrast": contrast}

def estimate_road_width(img, road_mask):
    h, w = road_mask.shape
    lower_start = int(h * 0.7)
    lower_road = road_mask[lower_start:, :]
    if lower_road.sum() < 100:
        return {"road_width_m": None, "road_pixel_width": 0}
    row_widths = []
    for ri in range(lower_road.shape[0]):
        cols = np.where(lower_road[ri] > 0)[0]
        if len(cols) > 0:
            row_widths.append((ri + lower_start, int(cols[-1] - cols[0])))
    if not row_widths:
        return {"road_width_m": None, "road_pixel_width": 0}
    max_row = max(row_widths, key=lambda x: x[1])
    pw = max_row[1]; ry = max_row[0]
    angle = math.radians(max((ry / h - 0.5) * 30 + 10, 1))
    dist = 1.6 / math.tan(angle)
    phys_w = (pw / w) * 2 * dist * math.tan(math.radians(30))
    return {"road_width_m": round(phys_w, 2), "road_pixel_width": pw, "estimated_distance_m": round(dist, 1)}

def analyze_photo(filepath):
    data = np.fromfile(str(filepath), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None: return None
    h, w = img.shape[:2]
    scale = min(1024 / h, 1024 / w)
    ip = cv2.resize(img, (int(w*scale), int(h*scale))) if scale < 1 else img.copy()
    hsv = hsv_segmentation(ip)
    vq = visual_quality(ip)
    rw = estimate_road_width(ip, hsv["road_mask"])
    r = {"file": filepath.name, "folder": filepath.parent.name, "resolution": str(w)+"x"+str(h)}
    for k in ["green_ratio","sky_ratio","building_ratio","road_ratio"]:
        r[k] = hsv[k]
    r.update(vq); r.update(rw)
    vis = ip.copy()
    ov = np.zeros_like(vis)
    ov[hsv["green_mask"]>0] = [0,200,0]; ov[hsv["sky_mask"]>0] = [200,150,50]
    ov[hsv["building_mask"]>0] = [100,100,200]; ov[hsv["road_mask"]>0] = [150,150,150]
    seg_path = str(OUT_DIR / (filepath.stem+"_seg.jpg"))
    ret, buf = cv2.imencode(".jpg", cv2.addWeighted(vis, 0.6, ov, 0.4, 0))
    if ret: buf.tofile(seg_path)
    return r

def main():
    print("=== Guishan Island Street View Analysis ===")
    photos = []
    for folder in ["外围", "桂海村"]:
        fp = PHOTO_DIR / folder
        if fp.exists():
            for f in sorted(fp.glob("*.jpg")):
                if f.name != "地图.jpg": photos.append(f)
    print("Found", len(photos), "photos")
    results = []
    for i, photo in enumerate(photos):
        r = analyze_photo(photo)
        if r:
            results.append(r)
            rw = r.get("road_width_m", "?")
            parts = [str(i+1)+"/"+str(len(photos)), r["folder"]+"/"+r["file"]]
            parts.append("G="+str(round(r["green_ratio"],3)))
            parts.append("S="+str(round(r["sky_ratio"],3)))
            parts.append("B="+str(round(r["building_ratio"],3)))
            parts.append("W="+str(rw)+"m")
            print("  " + " ".join(parts))
    df = pd.DataFrame(results)
    df.to_excel(OUT_DIR / "guishan_streetview_analysis.xlsx", index=False)
    df.to_csv(OUT_DIR / "guishan_streetview_analysis.csv", index=False, encoding="utf-8-sig")
    with open(OUT_DIR / "guishan_streetview_analysis.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(); print("=== Summary ===")
    for col in ["green_ratio","sky_ratio","building_ratio","road_ratio","brightness","complexity","contrast"]:
        if col in df.columns:
            print("  " + col + ": mean=" + str(round(df[col].mean(),4)) + " std=" + str(round(df[col].std(),4)))
    rw = df["road_width_m"].dropna()
    if len(rw) > 0:
        print("  road_width: mean=" + str(round(rw.mean(),1)) + "m median=" + str(round(rw.median(),1)) + "m")
    print("Saved to", OUT_DIR)

if __name__ == "__main__":
    main()
