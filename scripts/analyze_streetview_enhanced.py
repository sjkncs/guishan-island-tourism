# -*- coding: utf-8 -*-
"""Enhanced Guishan Island Street View Analysis
DeepLabV3+ segmentation + extended indicators + anomaly detection"""
import cv2, numpy as np, os, sys, json, math, warnings
import pandas as pd
from pathlib import Path
from collections import defaultdict
warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(r'E:\珠海桂山岛案例')
PHOTO_DIR = BASE / '数据采集' / '桂山岛' / '桂山岛' / '2026-07'
OUT_DIR = BASE / 'output' / 'streetview_analysis'
OUT_DIR.mkdir(parents=True, exist_ok=True)

VOC_CLASSES = ['background','aeroplane','bicycle','bird','boat','bottle',
               'bus','car','cat','chair','cow','diningtable','dog','horse',
               'motorbike','person','pottedplant','sheep','sofa','train','tv']

def read_img(path):
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)

def save_img(path, img):
    ret, buf = cv2.imencode('.jpg', img)
    if ret: buf.tofile(str(path))

def load_deeplab():
    import torch, torchvision
    from torchvision import transforms
    from PIL import Image
    model = torchvision.models.segmentation.deeplabv3_resnet101(
        weights=torchvision.models.segmentation.DeepLabV3_ResNet101_Weights.DEFAULT)
    model.eval()
    transform = transforms.Compose([
        transforms.Resize(520), transforms.CenterCrop(520),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])])
    return model, transform, Image

def deeplab_segment(img, model, transform, Image):
    import torch
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    inp = transform(pil).unsqueeze(0)
    with torch.no_grad():
        out = model(inp)['out'][0]
    seg = out.argmax(0).cpu().numpy()
    seg = cv2.resize(seg.astype(np.uint8), (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
    total = seg.size
    ratios = {}
    for i, cls in enumerate(VOC_CLASSES):
        ratios['dl_' + cls] = float(np.sum(seg == i) / total)
    return ratios, seg

def extended_indicators(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, s, v = cv2.split(hsv)
    total = img.shape[0] * img.shape[1]
    result = {}

    # Color segmentation
    green = ((h >= 35) & (h <= 85) & (s > 40) & (v > 30)).astype(np.uint8)
    sky = ((h >= 90) & (h <= 130) & (s < 80) & (v > 150)).astype(np.uint8)
    cloud = ((s < 30) & (v > 180)).astype(np.uint8)
    sky = np.maximum(sky, cloud)
    sea = ((h >= 90) & (h <= 120) & (s > 40) & (s < 120) & (v > 80) & (v < 180)).astype(np.uint8)
    sea = np.clip(sea - sky - green, 0, 1).astype(np.uint8)
    bldg = ((s > 10) & (s < 60) & (v > 60) & (v < 180)).astype(np.uint8)
    bldg = np.clip(bldg - green - sky - sea, 0, 1).astype(np.uint8)
    road = ((s < 40) & (v > 20) & (v < 120)).astype(np.uint8)
    road = np.clip(road - green - sky, 0, 1).astype(np.uint8)
    non_sky = total - sky.sum()

    result['green_ratio'] = float(green.sum() / total)
    result['sky_ratio'] = float(sky.sum() / total)
    result['sea_ratio'] = float(sea.sum() / total)
    result['building_ratio'] = float(bldg.sum() / total)
    result['road_ratio'] = float(road.sum() / total)
    result['gvi'] = float(green.sum() / max(non_sky, 1))

    # Enclosure: vertical elements on left/right strips
    left = img[:, :img.shape[1]//4, :]
    right = img[:, 3*img.shape[1]//4:, :]
    l_hsv = cv2.cvtColor(left, cv2.COLOR_BGR2HSV)
    r_hsv = cv2.cvtColor(right, cv2.COLOR_BGR2HSV)
    lh, ls, lv = cv2.split(l_hsv)
    rh, rs, rv = cv2.split(r_hsv)
    l_vert = (((lh >= 35) & (lh <= 85) & (ls > 40)) | ((ls > 10) & (ls < 60) & (lv > 60))).sum()
    r_vert = (((rh >= 35) & (rh <= 85) & (rs > 40)) | ((rs > 10) & (rs < 60) & (rv > 60))).sum()
    side_total = left.shape[0] * left.shape[1] + right.shape[0] * right.shape[1]
    result['enclosure_index'] = float((l_vert + r_vert) / max(side_total, 1))

    # Openness: sky+sea in upper half
    mid_h = img.shape[0] // 2
    upper_sky = sky[:mid_h, :].sum()
    upper_sea = sea[:mid_h, :].sum()
    result['openness'] = float((upper_sky + upper_sea) / max(mid_h * img.shape[1], 1))

    # Visual complexity
    edges1 = cv2.Canny(gray, 50, 150)
    edges2 = cv2.Canny(gray, 100, 200)
    result['edge_density'] = float(edges1.sum() / (255 * edges1.size))
    result['fine_detail'] = float(edges2.sum() / (255 * edges2.size))

    # Color metrics
    result['brightness'] = float(v.mean() / 255.0)
    result['saturation'] = float(s.mean() / 255.0)
    result['contrast'] = float(v.std() / 255.0)
    result['color_richness'] = float(h.std() / 180.0)
    warm = ((h < 30) | (h > 150)).sum()
    cool = ((h >= 90) & (h <= 150)).sum()
    result['warm_cool_ratio'] = float(warm / max(cool, 1))

    # Texture
    blur = cv2.GaussianBlur(gray, (15, 15), 0)
    result['texture_roughness'] = float(np.abs(gray.astype(float) - blur.astype(float)).mean() / 255.0)

    # Road width
    lower = road[int(img.shape[0]*0.7):, :]
    if lower.sum() > 100:
        widths = []
        for ri in range(lower.shape[0]):
            cols = np.where(lower[ri] > 0)[0]
            if len(cols) > 0: widths.append(int(cols[-1] - cols[0]))
        if widths:
            max_pw = max(widths)
            result['road_pixel_width'] = max_pw
            angle = math.radians(max(15, 10 + 5 * (max_pw / img.shape[1])))
            dist = 1.6 / math.tan(angle) if math.tan(angle) > 0 else 10
            result['road_width_m'] = round((max_pw / img.shape[1]) * 2 * dist * math.tan(math.radians(30)), 2)
    else:
        result['road_pixel_width'] = 0
        result['road_width_m'] = None

    return result

def detect_anomalies(df):
    from scipy import stats
    numeric_cols = [c for c in df.columns if df[c].dtype in ['float64','int64','float32']
                    and c not in ['road_pixel_width','cluster']]
    z_scores = pd.DataFrame(index=df.index)
    for col in numeric_cols:
        vals = df[col].dropna()
        if len(vals) < 5: continue
        z = np.abs(stats.zscore(vals.values))
        z_scores.loc[vals.index, col] = z
    df['anomaly_score'] = z_scores.mean(axis=1)
    df['is_anomaly'] = df['anomaly_score'] > 2.0
    return df

def cluster_locations(df):
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    feat_cols = ['green_ratio','sky_ratio','sea_ratio','building_ratio','road_ratio',
                 'enclosure_index','openness','brightness','edge_density','texture_roughness',
                 'saturation','contrast']
    avail = [c for c in feat_cols if c in df.columns and df[c].notna().all()]
    if len(avail) < 3: return df
    X = StandardScaler().fit_transform(df[avail].values)
    k = min(4, max(2, len(df) // 5))
    df['cluster'] = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X)
    return df

def main():
    print('=== Enhanced Guishan Island Street View Analysis ===')

    model, transform, PILImage = None, None, None
    try:
        model, transform, PILImage = load_deeplab()
        print('DeepLabV3+ loaded')
    except Exception as e:
        print(f'DeepLab not available: {e}')

    photos = []
    for folder in ['外围', '桂海村']:
        fp = PHOTO_DIR / folder
        if fp.exists():
            for f in sorted(fp.glob('*.jpg')):
                if f.name != '地图.jpg': photos.append(f)
    print(f'Found {len(photos)} photos')

    results = []
    for i, photo in enumerate(photos):
        img = read_img(photo)
        if img is None:
            print(f'  [{i+1}] SKIP {photo.name}')
            continue

        h, w = img.shape[:2]
        scale = min(1024/h, 1024/w)
        ip = cv2.resize(img, (int(w*scale), int(h*scale))) if scale < 1 else img.copy()

        r = extended_indicators(ip)
        r['file'] = photo.name
        r['folder'] = photo.parent.name
        r['location'] = photo.stem

        if model is not None:
            small = cv2.resize(img, (520, 520))
            dl_ratios, seg = deeplab_segment(small, model, transform, PILImage)
            r.update(dl_ratios)

        results.append(r)
        rw = r.get('road_width_m', '?')
        gvi = r.get('gvi', 0)
        enc = r.get('enclosure_index', 0)
        opn = r.get('openness', 0)
        print(f'  [{i+1}/{len(photos)}] {r["folder"]}/{r["location"]}: '
              f'G={r["green_ratio"]:.3f} S={r["sky_ratio"]:.3f} Sea={r["sea_ratio"]:.3f} '
              f'GVI={gvi:.3f} Enc={enc:.3f} Opn={opn:.3f} W={rw}m')

    df = pd.DataFrame(results)
    df = detect_anomalies(df)
    df = cluster_locations(df)

    # Save
    df.to_excel(OUT_DIR / 'guishan_enhanced_analysis.xlsx', index=False)
    df.to_csv(OUT_DIR / 'guishan_enhanced_analysis.csv', index=False, encoding='utf-8-sig')
    with open(OUT_DIR / 'guishan_enhanced_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    # Summary
    print()
    print('=' * 60)
    print('EXTENDED INDICATOR SUMMARY')
    print('=' * 60)
    indicators = ['green_ratio','sky_ratio','sea_ratio','building_ratio','road_ratio',
                  'gvi','enclosure_index','openness','brightness','edge_density',
                  'fine_detail','texture_roughness','saturation','contrast',
                  'color_richness','warm_cool_ratio']
    for col in indicators:
        if col in df.columns and df[col].notna().any():
            print(f'  {col:22s}: mean={df[col].mean():.4f} std={df[col].std():.4f} '
                  f'[{df[col].min():.4f}, {df[col].max():.4f}]')

    rw = df['road_width_m'].dropna()
    if len(rw) > 0:
        print(f'  {"road_width_m":22s}: mean={rw.mean():.1f}m median={rw.median():.1f}m')

    # DeepLab class summary
    dl_cols = [c for c in df.columns if c.startswith('dl_')]
    if dl_cols:
        print()
        print('DEEPLAB SEGMENTATION (PASCAL VOC 21 classes):')
        for col in sorted(dl_cols, key=lambda x: -df[x].mean()):
            if df[col].mean() > 0.001:
                print(f'  {col:25s}: mean={df[col].mean():.4f}')

    # Anomaly report
    print()
    print('=' * 60)
    print('ANOMALY DETECTION (Z-score > 2.0)')
    print('=' * 60)
    anomalies = df[df['is_anomaly'] == True]
    print(f'  Anomalies: {len(anomalies)}/{len(df)}')
    for _, row in anomalies.iterrows():
        print(f'  >> {row["folder"]}/{row["location"]}: score={row["anomaly_score"]:.3f}')
        for col in indicators[:10]:
            if col in row.index and df[col].std() > 0:
                z = abs(row[col] - df[col].mean()) / df[col].std()
                if z > 2.0:
                    direction = 'HIGH' if row[col] > df[col].mean() else 'LOW'
                    print(f'     {col}: {row[col]:.4f} (z={z:.1f}, {direction})')

    # Location comparison
    print()
    print('=' * 60)
    print('LOCATION COMPARISON')
    print('=' * 60)
    for folder in df['folder'].unique():
        sub = df[df['folder'] == folder]
        print(f'  {folder} ({len(sub)} photos):')
        for col in ['green_ratio','sky_ratio','sea_ratio','gvi','enclosure_index',
                     'openness','edge_density','brightness']:
            if col in sub.columns:
                print(f'    {col}: {sub[col].mean():.4f} (std={sub[col].std():.4f})')

    # Cluster analysis
    if 'cluster' in df.columns:
        print()
        print('=' * 60)
        print('SCENE CLUSTERS (KMeans on visual features)')
        print('=' * 60)
        for c in sorted(df['cluster'].unique()):
            sub = df[df['cluster'] == c]
            print(f'  Cluster {c} ({len(sub)} photos):')
            for col in ['green_ratio','sky_ratio','building_ratio','enclosure_index','openness']:
                if col in sub.columns:
                    print(f'    {col}: {sub[col].mean():.4f}')
            locs = sub['location'].tolist()
            for loc in locs[:5]:
                print(f'    - {loc}')
            if len(locs) > 5:
                print(f'    ... +{len(locs)-5} more')

    print(f'\nAll results saved to {OUT_DIR}')

if __name__ == '__main__':
    main()
