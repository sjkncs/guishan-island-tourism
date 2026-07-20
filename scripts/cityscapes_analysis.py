# -*- coding: utf-8 -*-
"""
桂山岛街景 DeepLabV3 语义分割 + 出版级可视化分析
=================================================
使用 torchvision DeepLabV3 ResNet101 (COCO预训练, 21类)
结合 HSV 场景分割，对36张实地照片做多维街景分析，生成9张论文图表。
"""

import os
import sys
import json
import warnings
from pathlib import Path
from collections import defaultdict

# 绕过本地代理以允许直接下载模型权重
os.environ['no_proxy'] = '*'
os.environ['NO_PROXY'] = '*'

import numpy as np
import pandas as pd
import cv2
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ── 全局配置 ──
warnings.filterwarnings('ignore')
plt.rcParams.update({
    'font.sans-serif': ['Microsoft YaHei'],
    'axes.unicode_minus': False,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
})

BASE = Path(r'E:\珠海桂山岛案例')
PHOTO_DIR = BASE / '数据采集' / '桂山岛' / '桂山岛' / '2026-07'
OUTPUT_DIR = BASE / 'output' / 'cityscapes_analysis'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# COCO 21 类标签 (torchvision DeepLabV3 COCO预训练)
COCO_CLASSES = [
    'background', 'aeroplane', 'bicycle', 'bird', 'boat',
    'bottle', 'bus', 'car', 'cat', 'chair',
    'cow', 'diningtable', 'dog', 'horse', 'motorbike',
    'person', 'pottedplant', 'sheep', 'sofa', 'train',
    'tvmonitor'
]

# Cityscapes 19 类标签 (Cityscapes预训练)
CITYSCAPES_CLASSES = [
    'road', 'sidewalk', 'building', 'wall', 'fence',
    'pole', 'traffic_light', 'traffic_sign', 'vegetation', 'terrain',
    'sky', 'person', 'rider', 'car', 'truck',
    'bus', 'train', 'motorcycle', 'bicycle'
]

# 当前使用的模型类型 (运行时设置)
MODEL_TYPE = 'coco'  # 'cityscapes' or 'coco'
ACTIVE_CLASSES = COCO_CLASSES  # 动态切换

# 街景分析关注的语义组
STREET_GROUPS = {
    'vehicles': ['car', 'bus', 'motorbike', 'bicycle', 'train'],
    'people': ['person'],
    'vegetation': ['pottedplant'],
    'animals': ['cat', 'dog', 'horse', 'cow', 'sheep', 'bird'],
    'objects': ['bottle', 'chair', 'sofa', 'tvmonitor', 'diningtable'],
    'watercraft': ['boat'],
}

# Cityscapes 语义组
CITYSCAPES_GROUPS = {
    'road_infra': ['road', 'sidewalk'],
    'buildings': ['building', 'wall', 'fence'],
    'objects': ['pole', 'traffic_light', 'traffic_sign'],
    'nature': ['vegetation', 'terrain'],
    'sky': ['sky'],
    'people': ['person', 'rider'],
    'vehicles': ['car', 'truck', 'bus', 'train', 'motorcycle', 'bicycle'],
}

COCO_COLORS = [
    [0, 0, 0], [128, 0, 0], [0, 128, 0], [128, 128, 0], [0, 0, 128],
    [128, 0, 128], [0, 128, 128], [128, 128, 128], [64, 0, 0], [192, 0, 0],
    [64, 128, 0], [192, 128, 0], [64, 0, 128], [192, 0, 128], [64, 128, 128],
    [192, 128, 128], [0, 64, 0], [128, 64, 0], [0, 192, 0], [128, 192, 0],
    [0, 64, 128]
]

# ── 工具函数 ──

def read_image_cv(filepath):
    """解决 Windows 中文路径问题"""
    data = np.fromfile(str(filepath), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        print(f"  [WARN] 无法读取: {filepath}")
    return img


def collect_photos():
    """遍历所有子目录收集 JPG 照片"""
    photos = []
    for root, dirs, files in os.walk(str(PHOTO_DIR)):
        for f in sorted(files):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                full = Path(root) / f
                rel = full.relative_to(PHOTO_DIR)
                # 推断位置类别
                parts = rel.parts
                if len(parts) >= 2:
                    location = parts[0]
                else:
                    location = 'unknown'
                photos.append({
                    'path': full,
                    'filename': f,
                    'location': location,
                    'relative': str(rel),
                })
    return photos


# ── HSV 扩展指标 ──

def compute_hsv_indicators(img):
    """计算16维HSV色彩指标"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    total = img.shape[0] * img.shape[1]

    # 1. 绿视率 GVI
    green_mask = (h >= 35) & (h <= 85) & (s > 40) & (v > 30)
    gvi = green_mask.sum() / total

    # 2. 天空比
    sky_mask = ((h >= 90) & (h <= 130) & (s < 80) & (v > 150))
    sky_ratio = sky_mask.sum() / total

    # 3. 海面比
    sea_mask = (h >= 90) & (h <= 120) & (s >= 40) & (s <= 120) & (v >= 80) & (v <= 180)
    sea_ratio = sea_mask.sum() / total

    # 4. 建筑比
    bld_mask = (s >= 10) & (s <= 60) & (v >= 60) & (v <= 180)
    building_ratio = bld_mask.sum() / total

    # 5. 路面比
    road_mask = (s < 40) & (v >= 20) & (v <= 120)
    road_ratio = road_mask.sum() / total

    # 6. 亮度均值
    brightness = v.mean() / 255.0

    # 7. 饱和度均值
    saturation = s.mean() / 255.0

    # 8. 色彩丰富度 (hue 标准差)
    color_richness = h.std() / 180.0

    # 9. 暖色比 (红/橙/黄)
    warm_mask = ((h < 35) | (h > 155)) & (s > 30)
    warm_ratio = warm_mask.sum() / total

    # 10. 冷色比 (蓝/青)
    cool_mask = (h >= 85) & (h <= 130) & (s > 20)
    cool_ratio = cool_mask.sum() / total

    # 11. 围合度 (建筑+墙+围栏 的垂直条带占比)
    enclosure = building_ratio * 0.6 + (1 - sky_ratio) * 0.2 + (1 - gvi) * 0.2

    # 12. 开放度
    openness = sky_ratio + sea_ratio + gvi

    # 13. 边缘密度 (Canny)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = (edges > 0).sum() / total

    # 14. 纹理复杂度 (Laplacian 方差)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    texture = np.log1p(lap.var()) / 10.0

    # 15. 对比度
    contrast = v.std() / 128.0

    # 16. 色温指标 (暖冷比)
    color_temp = warm_ratio / (cool_ratio + 1e-6)

    return {
        'GVI': gvi, 'sky_ratio': sky_ratio, 'sea_ratio': sea_ratio,
        'building_ratio': building_ratio, 'road_ratio': road_ratio,
        'brightness': brightness, 'saturation': saturation,
        'color_richness': color_richness, 'warm_ratio': warm_ratio,
        'cool_ratio': cool_ratio, 'enclosure': enclosure,
        'openness': openness, 'edge_density': edge_density,
        'texture': texture, 'contrast': contrast, 'color_temp': color_temp,
    }


# ── 语义分割 (torchvision DeepLabV3 COCO + HSV 场景分割) ──

def load_segmentation_model():
    """优先加载 Cityscapes 预训练 DeepLabV3, 失败则回退 COCO"""
    global MODEL_TYPE, ACTIVE_CLASSES
    import torch

    # ── 尝试 1: Cityscapes 预训练 (Koushim/deeplabv3-resnet50-cityscapes) ──
    # 注意: Koushim 模型使用 backbone. 前缀, 与 torchvision deeplabv3_resnet50 的 key 结构不完全匹配
    # 加载后推理结果异常 (building=0%, person=51%), 暂禁用, 待修复 key 映射
    cs_weights_candidates = []
    cs_weights = None
    for p in cs_weights_candidates:
        if p.exists() and p.stat().st_size > 160_000_000:
            cs_weights = p
            break

    if cs_weights:
        print(f"[INFO] 加载 Cityscapes DeepLabV3 ResNet50 (19类)...")
        print(f"  权重文件: {cs_weights} ({cs_weights.stat().st_size/1e6:.0f}MB)")
        try:
            from torchvision.models.segmentation import deeplabv3_resnet50
            # 先创建无权重模型 (避免额外下载 backbone)
            model = deeplabv3_resnet50(weights=None, num_classes=19, aux_loss=None)
            state = torch.load(str(cs_weights), map_location='cpu', weights_only=False)
            if isinstance(state, dict) and 'state_dict' in state:
                state = state['state_dict']
            elif isinstance(state, dict) and 'model' in state:
                state = state['model']
            # Filter out unexpected keys
            model_sd = model.state_dict()
            filtered = {k: v for k, v in state.items() if k in model_sd and v.shape == model_sd[k].shape}
            missing = model.load_state_dict(filtered, strict=False)
            print(f"  Cityscapes 权重加载成功!")
            print(f"  匹配层: {len(filtered)}, 缺失: {len(missing.missing_keys)}, 多余: {len(missing.unexpected_keys)}")
            MODEL_TYPE = 'cityscapes'
            ACTIVE_CLASSES = CITYSCAPES_CLASSES
            model.eval()
            return model
        except Exception as e:
            print(f"  [WARN] Cityscapes 加载失败: {e}")

    # ── 回退: COCO 预训练 (torchvision) ──
    print("[INFO] 回退: 加载 torchvision DeepLabV3 ResNet101 (COCO预训练, 21类)...")
    try:
        from torchvision.models.segmentation import deeplabv3_resnet101, DeepLabV3_ResNet101_Weights
        weights = DeepLabV3_ResNet101_Weights.DEFAULT
        model = deeplabv3_resnet101(weights=weights)
        print("  COCO预训练权重加载成功")
    except Exception as e:
        print(f"  [WARN] COCO也失败: {e}")
        from torchvision.models.segmentation import deeplabv3_resnet101
        model = deeplabv3_resnet101(weights=None)

    MODEL_TYPE = 'coco'
    ACTIVE_CLASSES = COCO_CLASSES
    model.eval()
    return model


def preprocess_for_deeplab(img, target_size=(1024, 512)):
    """预处理图片为 torchvision DeepLabV3 输入格式"""
    import torch
    from torchvision import transforms

    resized = cv2.resize(img, target_size, interpolation=cv2.INTER_LINEAR)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])
    tensor = transform(pil_img).unsqueeze(0)
    return tensor


def hsv_scene_segmentation(img):
    """基于 HSV 的场景分割：天空/海面/植被/建筑/路面/其他"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    total = img.shape[0] * img.shape[1]

    # 各场景要素 mask
    sky = (h >= 90) & (h <= 130) & (s < 80) & (v > 150)
    sea = (h >= 90) & (h <= 120) & (s >= 40) & (s <= 120) & (v >= 80) & (v <= 180)
    green = (h >= 35) & (h <= 85) & (s > 40) & (v > 30)
    building = (s >= 10) & (s <= 60) & (v >= 60) & (v <= 180) & ~sky & ~sea & ~green
    road = (s < 40) & (v >= 20) & (v <= 120) & ~sky & ~sea
    # 排除已分配的像素
    assigned = sky | sea | green | building | road
    other = ~assigned

    return {
        'hsv_sky': sky.sum() / total,
        'hsv_sea': sea.sum() / total,
        'hsv_green': green.sum() / total,
        'hsv_building': building.sum() / total,
        'hsv_road': road.sum() / total,
        'hsv_other': other.sum() / total,
    }


def run_semantic_segmentation(model, img):
    """对单张图片执行语义分割 + HSV 场景分割，返回综合结果"""
    import torch

    # DeepLabV3 推理
    with torch.no_grad():
        x = preprocess_for_deeplab(img)
        output = model(x)
        pred = output['out'].argmax(dim=1).squeeze().numpy()

    total = pred.size
    seg_ratios = {}
    for i, cls_name in enumerate(ACTIVE_CLASSES):
        if i < pred.max() + 1 or i == 0:
            count = (pred == i).sum()
            seg_ratios[cls_name] = count / total
        else:
            seg_ratios[cls_name] = 0.0

    # HSV 场景分割补充
    hsv_scene = hsv_scene_segmentation(img)

    return seg_ratios, hsv_scene, pred


# ── 主分析流程 ──

def main():
    print("=" * 60)
    print("桂山岛街景 DeepLabV3 语义分割 + HSV 场景分析")
    print("=" * 60)

    # 1. 收集照片
    photos = collect_photos()
    print(f"\n[INFO] 共发现 {len(photos)} 张照片")
    if not photos:
        print("[ERROR] 未找到照片")
        return

    # 2. 加载模型
    model = load_segmentation_model()
    if model is None:
        print("[ERROR] 模型加载失败，退出")
        return

    # 3. 逐张分析
    results = []
    for idx, photo in enumerate(photos):
        print(f"\n[{idx+1}/{len(photos)}] {photo['filename']} ({photo['location']})")

        img = read_image_cv(photo['path'])
        if img is None:
            continue

        # 缩放到合理尺寸以节省内存 (保留宽高比, 最长边 1024)
        h, w = img.shape[:2]
        max_dim = 1024
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # HSV 指标
        hsv = compute_hsv_indicators(img)

        # 语义分割 (Cityscapes 或 COCO + HSV场景)
        try:
            seg_ratios, hsv_scene, pred_mask = run_semantic_segmentation(model, img)
        except Exception as e:
            print(f"  [ERROR] 分割失败: {e}")
            seg_ratios = {c: 0.0 for c in ACTIVE_CLASSES}
            hsv_scene = {k: 0.0 for k in ['hsv_sky', 'hsv_sea', 'hsv_green', 'hsv_building', 'hsv_road', 'hsv_other']}

        row = {
            'filename': photo['filename'],
            'location': photo['location'],
            'relative_path': photo['relative'],
            'model_type': MODEL_TYPE,
        }
        # HSV 指标
        for k, v in hsv.items():
            row[f'hsv_{k}'] = v
        # 语义分割类别比 (Cityscapes 或 COCO)
        for cls, ratio in seg_ratios.items():
            row[f'seg_{cls}'] = ratio
        # HSV 场景分割
        for k, v in hsv_scene.items():
            row[f'scene_{k}'] = v

        # 复合指标 (根据模型类型)
        if MODEL_TYPE == 'cityscapes':
            seg_vehicle = sum(seg_ratios.get(c, 0) for c in ['car', 'truck', 'bus', 'train', 'motorcycle', 'bicycle'])
            seg_people = sum(seg_ratios.get(c, 0) for c in ['person', 'rider'])
            seg_veg = sum(seg_ratios.get(c, 0) for c in ['vegetation', 'terrain'])
            seg_road = sum(seg_ratios.get(c, 0) for c in ['road', 'sidewalk'])
            seg_built = sum(seg_ratios.get(c, 0) for c in ['building', 'wall', 'fence'])
        else:
            seg_vehicle = sum(seg_ratios.get(c, 0) for c in ['car', 'bus', 'motorbike', 'bicycle', 'train'])
            seg_people = seg_ratios.get('person', 0)
            seg_veg = seg_ratios.get('pottedplant', 0)
            seg_road = 0.0
            seg_built = 0.0

        scene_natural = hsv_scene['hsv_sky'] + hsv_scene['hsv_green'] + hsv_scene['hsv_sea']
        scene_built = hsv_scene['hsv_building'] + hsv_scene['hsv_road']

        row['seg_vehicle_total'] = seg_vehicle
        row['seg_people_total'] = seg_people
        row['seg_veg_total'] = seg_veg
        row['seg_road_total'] = seg_road
        row['seg_built_total'] = seg_built
        row['scene_natural_ratio'] = scene_natural
        row['scene_built_ratio'] = scene_built
        row['scene_natural_built_ratio'] = scene_natural / (scene_built + 1e-6)
        row['scene_urban_intensity'] = scene_built + seg_vehicle + seg_people

        results.append(row)

    df = pd.DataFrame(results)
    print(f"\n[INFO] 完成分析，共 {len(df)} 条记录")

    # 4. 保存数据
    xlsx_path = OUTPUT_DIR / 'guishan_cityscapes_results.xlsx'
    df.to_excel(str(xlsx_path), index=False, engine='openpyxl')
    print(f"[INFO] 数据已保存: {xlsx_path}")

    csv_path = OUTPUT_DIR / 'guishan_cityscapes_results.csv'
    df.to_csv(str(csv_path), index=False, encoding='utf-8-sig')

    # 5. 异常检测 (Z-score)
    numeric_cols = [c for c in df.columns if c.startswith('hsv_') or c.startswith('scene_') or c.startswith('seg_')]
    anomaly_df = df[['filename', 'location']].copy()
    for col in numeric_cols:
        if col in df.columns:
            z = np.abs(stats.zscore(df[col], nan_policy='omit'))
            anomaly_df[f'z_{col}'] = z
            anomaly_df[f'anomaly_{col}'] = (z > 2.0).astype(int)

    anomaly_df['anomaly_count'] = anomaly_df[[c for c in anomaly_df.columns if c.startswith('anomaly_')]].sum(axis=1)
    anomaly_df['max_zscore'] = anomaly_df[[c for c in anomaly_df.columns if c.startswith('z_')]].max(axis=1)

    anomaly_path = OUTPUT_DIR / 'anomaly_detection.xlsx'
    anomaly_df.to_excel(str(anomaly_path), index=False, engine='openpyxl')
    print(f"[INFO] 异常检测已保存: {anomaly_path}")

    # 6. 聚类分析
    features_for_cluster = [c for c in numeric_cols if c in df.columns]
    X_cluster = df[features_for_cluster].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_cluster)

    n_clusters = min(4, len(df) - 1)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df['cluster'] = kmeans.fit_predict(X_scaled)

    # 7. 生成 9 张出版级图表
    print("\n[INFO] 生成可视化图表...")
    generate_fig1_radar(df)
    generate_fig2_bar(df)
    generate_fig3_heatmap(df)
    generate_fig4_scatter(df)
    generate_fig5_boxplot(df)
    generate_fig6_cluster(df)
    generate_fig7_cityscapes_dist(df)
    generate_fig8_anomaly(df, anomaly_df)
    generate_fig9_comparison(df)

    print("\n" + "=" * 60)
    print("全部完成! 图表保存在:", OUTPUT_DIR)
    print("=" * 60)


# ── 图表生成函数 ──

def _location_colors(location):
    """位置颜色映射"""
    colors_map = {
        '外围': '#2E75B6',
        '桂海村': '#C0392B',
        '桂山村': '#27AE60',
        'unknown': '#95A5A6',
    }
    return colors_map.get(location, '#7F8C8D')


def generate_fig1_radar(df):
    """图1: 雷达图 - 外围 vs 桂海村 多维指标对比"""
    indicators = ['hsv_GVI', 'hsv_sky_ratio', 'hsv_building_ratio', 'hsv_road_ratio',
                  'hsv_brightness', 'hsv_edge_density', 'hsv_openness', 'hsv_enclosure',
                  'scene_hsv_green', 'scene_hsv_building', 'scene_hsv_road', 'scene_built_ratio']
    labels = ['绿视率', '天空比', '建筑比', '路面比',
              '亮度', '边缘密度', '开放度', '围合度',
              '场景植被', '场景建筑', '场景路面', '场景建成度']

    locations = [loc for loc in df['location'].unique() if loc != 'unknown']
    if len(locations) < 2:
        print("  [SKIP] 图1: 位置不足2个")
        return

    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    angles = np.linspace(0, 2 * np.pi, len(indicators), endpoint=False).tolist()
    angles += angles[:1]

    colors_list = ['#2E75B6', '#C0392B', '#27AE60', '#F39C12']
    for i, loc in enumerate(locations):
        subset = df[df['location'] == loc]
        values = [subset[ind].mean() for ind in indicators]
        values += values[:1]

        ax.plot(angles, values, 'o-', linewidth=2, label=loc,
                color=colors_list[i % len(colors_list)], markersize=6)
        ax.fill(angles, values, alpha=0.15, color=colors_list[i % len(colors_list)])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_title('桂山岛不同区域街景指标雷达对比', fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)
    ax.grid(True, alpha=0.3)

    fig.savefig(str(OUTPUT_DIR / 'fig1_radar_comparison.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("  [OK] 图1: 雷达对比图")


def generate_fig2_bar(df):
    """图2: 分组柱状图 + 误差棒 + 显著性标记"""
    key_metrics = [
        ('hsv_GVI', '绿视率'),
        ('hsv_sky_ratio', '天空比'),
        ('hsv_building_ratio', '建筑比'),
        ('scene_hsv_green', '场景植被'),
        ('scene_hsv_building', '场景建筑'),
        ('scene_built_ratio', '场景建成'),
        ('hsv_brightness', '亮度'),
        ('hsv_openness', '开放度'),
    ]

    locations = sorted([loc for loc in df['location'].unique() if loc != 'unknown'])
    if len(locations) < 2:
        print("  [SKIP] 图2: 位置不足2个")
        return

    fig, ax = plt.subplots(figsize=(16, 8))
    n_locs = len(locations)
    x = np.arange(len(key_metrics))
    width = 0.8 / n_locs
    colors_list = ['#2E75B6', '#C0392B', '#27AE60', '#F39C12']

    for i, loc in enumerate(locations):
        subset = df[df['location'] == loc]
        means = [subset[m[0]].mean() for m in key_metrics]
        stds = [subset[m[0]].std() for m in key_metrics]
        offset = (i - (n_locs - 1) / 2) * width
        bars = ax.bar(x + offset, means, width * 0.9, yerr=stds,
                       label=loc, color=colors_list[i % len(colors_list)],
                       capsize=4, alpha=0.85, edgecolor='white', linewidth=0.5)

    # 显著性标记 (t-test)
    if n_locs == 2:
        loc_a, loc_b = locations[0], locations[1]
        for j, (col, _) in enumerate(key_metrics):
            a_vals = df[df['location'] == loc_a][col].dropna()
            b_vals = df[df['location'] == loc_b][col].dropna()
            if len(a_vals) > 2 and len(b_vals) > 2:
                t, p = stats.ttest_ind(a_vals, b_vals)
                if p < 0.01:
                    marker = '**'
                elif p < 0.05:
                    marker = '*'
                else:
                    marker = ''
                if marker:
                    y_max = max(
                        df[df['location'] == loc_a][col].mean() + df[df['location'] == loc_a][col].std(),
                        df[df['location'] == loc_b][col].mean() + df[df['location'] == loc_b][col].std(),
                    )
                    ax.text(x[j], y_max + 0.02, marker, ha='center', fontsize=14,
                            fontweight='bold', color='#333333')

    ax.set_xticks(x)
    ax.set_xticklabels([m[1] for m in key_metrics], fontsize=11)
    ax.set_ylabel('指标值', fontsize=12)
    ax.set_title('桂山岛不同区域关键街景指标对比 (均值 +/- 标准差)', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='upper right')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_ylim(bottom=0)

    fig.savefig(str(OUTPUT_DIR / 'fig2_grouped_bar.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("  [OK] 图2: 分组柱状图")


def generate_fig3_heatmap(df):
    """图3: 相关性热力图"""
    # 选取关键指标
    cols = ['hsv_GVI', 'hsv_sky_ratio', 'hsv_building_ratio', 'hsv_road_ratio',
            'hsv_brightness', 'hsv_openness', 'hsv_enclosure', 'hsv_edge_density',
            'scene_hsv_green', 'scene_hsv_building', 'scene_hsv_road', 'scene_built_ratio',
            'scene_natural_built_ratio', 'scene_hsv_sky']
    labels = ['GVI', '天空', '建筑', '路面', '亮度', '开放度', '围合度', '边缘',
              '场景绿', '场景建筑', '场景路面', '场景建成', '自然建成比', '场景天空']

    available = [c for c in cols if c in df.columns]
    avail_labels = [labels[cols.index(c)] for c in available]

    corr = df[available].corr()

    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(corr.values, cmap='RdBu_r', vmin=-1, vmax=1, aspect='equal')

    ax.set_xticks(range(len(avail_labels)))
    ax.set_yticks(range(len(avail_labels)))
    ax.set_xticklabels(avail_labels, rotation=45, ha='right', fontsize=10)
    ax.set_yticklabels(avail_labels, fontsize=10)

    # 数值标注
    for i in range(len(avail_labels)):
        for j in range(len(avail_labels)):
            val = corr.values[i, j]
            color = 'white' if abs(val) > 0.6 else 'black'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                    fontsize=8, color=color)

    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Pearson 相关系数', fontsize=11)
    ax.set_title('桂山岛街景指标相关性矩阵', fontsize=14, fontweight='bold')

    fig.savefig(str(OUTPUT_DIR / 'fig3_correlation_heatmap.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("  [OK] 图3: 相关性热力图")


def generate_fig4_scatter(df):
    """图4: 关键散点图 + 回归线"""
    pairs = [
        ('hsv_GVI', 'hsv_openness', 'GVI vs 开放度'),
        ('hsv_building_ratio', 'hsv_enclosure', '建筑比 vs 围合度'),
        ('scene_hsv_green', 'hsv_GVI', '场景植被 vs HSV绿视率'),
        ('seg_vehicle_total', 'scene_urban_intensity', '车辆比 vs 场景城市强度'),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    axes = axes.flatten()

    locations = df['location'].unique()
    for idx, (x_col, y_col, title) in enumerate(pairs):
        ax = axes[idx]
        if x_col not in df.columns or y_col not in df.columns:
            continue

        for loc in locations:
            subset = df[df['location'] == loc]
            ax.scatter(subset[x_col], subset[y_col],
                       c=_location_colors(loc), label=loc,
                       s=60, alpha=0.7, edgecolors='white', linewidth=0.5)

        # 全局回归线
        valid = df[[x_col, y_col]].dropna()
        if len(valid) > 3 and valid[x_col].std() > 1e-8 and valid[y_col].std() > 1e-8:
            slope, intercept, r_val, p_val, std_err = stats.linregress(valid[x_col], valid[y_col])
            x_line = np.linspace(valid[x_col].min(), valid[x_col].max(), 100)
            ax.plot(x_line, slope * x_line + intercept, 'k--', alpha=0.5, linewidth=1.5)
            ax.text(0.05, 0.95, f'R={r_val:.3f}, p={p_val:.3f}',
                    transform=ax.transAxes, fontsize=9, va='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        ax.set_xlabel(x_col, fontsize=10)
        ax.set_ylabel(y_col, fontsize=10)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    axes[0].legend(fontsize=9, loc='lower right')
    fig.suptitle('桂山岛街景指标关键散点关系', fontsize=14, fontweight='bold', y=1.01)
    fig.tight_layout()

    fig.savefig(str(OUTPUT_DIR / 'fig4_scatter_regression.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("  [OK] 图4: 散点回归图")


def generate_fig5_boxplot(df):
    """图5: 箱线图 + 散点抖动"""
    key_cols = ['hsv_GVI', 'hsv_sky_ratio', 'hsv_building_ratio',
                'scene_hsv_green', 'scene_hsv_building', 'hsv_openness']
    labels = ['GVI', '天空比', '建筑比', '场景植被', '场景建筑', '开放度']

    locations = sorted([loc for loc in df['location'].unique() if loc != 'unknown'])

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()

    for idx, (col, label) in enumerate(zip(key_cols, labels)):
        ax = axes[idx]
        data_by_loc = []
        for loc in locations:
            vals = df[df['location'] == loc][col].dropna().values
            data_by_loc.append(vals)

        bp = ax.boxplot(data_by_loc, labels=locations, patch_artist=True,
                        widths=0.5, showfliers=False)
        colors_list = ['#2E75B6', '#C0392B', '#27AE60', '#F39C12']
        for i, patch in enumerate(bp['boxes']):
            patch.set_facecolor(colors_list[i % len(colors_list)])
            patch.set_alpha(0.4)

        # 抖动散点
        for i, (loc, vals) in enumerate(zip(locations, data_by_loc)):
            jitter = np.random.normal(i + 1, 0.04, size=len(vals))
            ax.scatter(jitter, vals, c=colors_list[i % len(colors_list)],
                       s=30, alpha=0.6, edgecolors='white', linewidth=0.3, zorder=3)

        ax.set_title(label, fontsize=12, fontweight='bold')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    fig.suptitle('桂山岛各区域街景指标分布 (箱线图+散点)', fontsize=14, fontweight='bold', y=1.02)
    fig.tight_layout()

    fig.savefig(str(OUTPUT_DIR / 'fig5_boxplot_jitter.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("  [OK] 图5: 箱线图")


def generate_fig6_cluster(df):
    """图6: 场景聚类雷达 + 成员条形图"""
    if 'cluster' not in df.columns:
        print("  [SKIP] 图6: 无聚类结果")
        return

    cluster_means = df.groupby('cluster').agg({
        'hsv_GVI': 'mean', 'hsv_sky_ratio': 'mean',
        'hsv_building_ratio': 'mean', 'hsv_road_ratio': 'mean',
        'scene_hsv_green': 'mean', 'scene_hsv_building': 'mean',
        'scene_hsv_road': 'mean', 'seg_vehicle_total': 'mean',
    })

    indicators = list(cluster_means.columns)
    labels = ['GVI', '天空', '建筑', '路面', '场景绿', '场景建筑', '场景路面', '车辆']

    n_clusters = len(cluster_means)
    cluster_names = {
        0: '绿色廊道', 1: '开阔道路', 2: '建筑密集', 3: '观景点'
    }

    fig = plt.figure(figsize=(18, 8))

    # 左: 聚类雷达
    ax_radar = fig.add_subplot(121, polar=True)
    angles = np.linspace(0, 2 * np.pi, len(indicators), endpoint=False).tolist()
    angles += angles[:1]
    colors_list = ['#2E75B6', '#C0392B', '#27AE60', '#F39C12']

    for cid in range(n_clusters):
        vals = cluster_means.iloc[cid].values.tolist()
        vals += vals[:1]
        name = cluster_names.get(cid, f'簇{cid}')
        ax_radar.plot(angles, vals, 'o-', linewidth=2, label=name,
                      color=colors_list[cid % len(colors_list)], markersize=5)
        ax_radar.fill(angles, vals, alpha=0.1, color=colors_list[cid % len(colors_list)])

    ax_radar.set_xticks(angles[:-1])
    ax_radar.set_xticklabels(labels, fontsize=9)
    ax_radar.set_title('场景聚类特征雷达', fontsize=13, fontweight='bold', pad=15)
    ax_radar.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=10)

    # 右: 聚类成员分布
    ax_bar = fig.add_subplot(122)
    loc_cluster = pd.crosstab(df['location'], df['cluster'])
    loc_cluster.plot(kind='bar', stacked=True, ax=ax_bar,
                     color=colors_list[:n_clusters], alpha=0.8, edgecolor='white')
    ax_bar.set_title('各区域场景聚类成员分布', fontsize=13, fontweight='bold')
    ax_bar.set_xlabel('')
    ax_bar.set_ylabel('照片数量')
    ax_bar.legend([cluster_names.get(c, f'簇{c}') for c in range(n_clusters)],
                  fontsize=10, loc='upper right')
    ax_bar.spines['top'].set_visible(False)
    ax_bar.spines['right'].set_visible(False)
    plt.xticks(rotation=0)

    fig.tight_layout()
    fig.savefig(str(OUTPUT_DIR / 'fig6_cluster_analysis.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("  [OK] 图6: 聚类分析图")


def generate_fig7_cityscapes_dist(df):
    """图7: 语义分割类别分布 + HSV场景分割 综合图"""
    locations = sorted([loc for loc in df['location'].unique() if loc != 'unknown'])

    fig, axes = plt.subplots(1, 2, figsize=(18, 8))

    # 左: HSV 场景分割堆叠柱 (各位置平均)
    ax = axes[0]
    scene_labels = ['hsv_sky', 'hsv_sea', 'hsv_green', 'hsv_building', 'hsv_road', 'hsv_other']
    scene_names = ['天空', '海面', '植被', '建筑', '路面', '其他']
    scene_colors = ['#87CEEB', '#4682B4', '#228B22', '#808080', '#A0522D', '#D3D3D3']

    bottom = np.zeros(len(locations))
    for i, (col, name, color) in enumerate(zip(scene_labels, scene_names, scene_colors)):
        full_col = f'scene_{col}'
        if full_col not in df.columns:
            continue
        vals = []
        for loc in locations:
            vals.append(df[df['location'] == loc][full_col].mean())
        vals = np.array(vals)
        ax.bar(range(len(locations)), vals, bottom=bottom,
               color=color, label=name, alpha=0.85, edgecolor='white', linewidth=0.5)
        bottom += vals

    ax.set_xticks(range(len(locations)))
    ax.set_xticklabels(locations, fontsize=11)
    ax.set_ylabel('像素占比', fontsize=11)
    ax.set_title('各区域 HSV 场景分割平均分布', fontsize=13, fontweight='bold')
    ax.legend(fontsize=9, ncol=2, loc='upper right')
    ax.spines['top'].set_visible(False)

    # 右: 语义分割非背景/非主类分布
    ax2 = axes[1]
    # 获取所有 seg_ 列
    seg_cols = [c for c in df.columns if c.startswith('seg_')]
    # 排除聚合列
    skip = ['seg_vehicle_total', 'seg_people_total', 'seg_veg_total',
            'seg_road_total', 'seg_built_total']
    seg_cols = [c for c in seg_cols if c not in skip]
    # 提取类名
    seg_names = [c.replace('seg_', '') for c in seg_cols]

    if seg_cols:
        means = [df[c].mean() for c in seg_cols]
        # 排除占比最大的背景类(如果是COCO的background)
        non_bg_idx = [i for i, n in enumerate(seg_names) if n not in ('background',)]
        if non_bg_idx:
            filtered_names = [seg_names[i] for i in non_bg_idx]
            filtered_means = [means[i] for i in non_bg_idx]
        else:
            filtered_names = seg_names
            filtered_means = means

        sorted_idx = np.argsort(filtered_means)[::-1]
        sorted_labels = [filtered_names[i] for i in sorted_idx]
        sorted_vals = [filtered_means[i] for i in sorted_idx]
        bar_colors = ['#2E75B6' if v > 0.001 else '#CCCCCC' for v in sorted_vals]
        ax2.barh(range(len(sorted_labels)), sorted_vals, color=bar_colors,
                 alpha=0.85, edgecolor='white', linewidth=0.5)
        ax2.set_yticks(range(len(sorted_labels)))
        ax2.set_yticklabels(sorted_labels, fontsize=9)
        ax2.set_xlabel('平均像素占比', fontsize=11)
        model_label = 'Cityscapes' if MODEL_TYPE == 'cityscapes' else 'COCO'
        ax2.set_title(f'{model_label} 语义分割类别分布 (非背景)', fontsize=13, fontweight='bold')
        ax2.invert_yaxis()
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    fig.tight_layout()
    fig.savefig(str(OUTPUT_DIR / 'fig7_cityscapes_distribution.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("  [OK] 图7: 语义分割分布图")


def generate_fig8_anomaly(df, anomaly_df):
    """图8: 异常检测可视化"""
    fig, axes = plt.subplots(1, 3, figsize=(20, 7))

    # 左: 异常数量分布
    ax = axes[0]
    counts = anomaly_df['anomaly_count'].value_counts().sort_index()
    ax.bar(counts.index.astype(str), counts.values, color='#2E75B6', alpha=0.8, edgecolor='white')
    ax.set_xlabel('异常指标数量 (Z>2)', fontsize=11)
    ax.set_ylabel('照片数量', fontsize=11)
    ax.set_title('各照片异常指标计数分布', fontsize=13, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # 中: 最大Z-score 散点
    ax2 = axes[1]
    locations = anomaly_df.merge(df[['filename', 'location']], on=['filename', 'location'], how='left')
    for loc in locations['location'].unique():
        subset = locations[locations['location'] == loc]
        ax2.scatter(range(len(subset)), subset['max_zscore'],
                    c=_location_colors(loc), label=loc, s=60, alpha=0.7,
                    edgecolors='white', linewidth=0.5)
    ax2.axhline(y=2.0, color='red', linestyle='--', alpha=0.5, label='阈值 Z=2')
    ax2.axhline(y=3.0, color='darkred', linestyle='--', alpha=0.5, label='阈值 Z=3')
    ax2.set_xlabel('照片序号', fontsize=11)
    ax2.set_ylabel('最大 Z-score', fontsize=11)
    ax2.set_title('各照片最大异常Z-score', fontsize=13, fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    # 右: 关键指标Z-score热力图
    ax3 = axes[2]
    z_cols = [c for c in anomaly_df.columns if c.startswith('z_hsv_') or c.startswith('z_scene_') or c.startswith('z_seg_')]
    z_labels = [c.replace('z_hsv_', 'HSV-').replace('z_scene_', 'Scene-').replace('z_seg_', 'Seg-') for c in z_cols]
    z_data = anomaly_df[z_cols].values.T

    im = ax3.imshow(z_data, aspect='auto', cmap='YlOrRd', vmin=0, vmax=4)
    ax3.set_yticks(range(len(z_labels)))
    ax3.set_yticklabels(z_labels, fontsize=8)
    ax3.set_xlabel('照片序号', fontsize=11)
    ax3.set_title('指标异常Z-score热力图', fontsize=13, fontweight='bold')
    plt.colorbar(im, ax=ax3, shrink=0.8, label='Z-score')

    fig.tight_layout()
    fig.savefig(str(OUTPUT_DIR / 'fig8_anomaly_detection.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("  [OK] 图8: 异常检测图")


def generate_fig9_comparison(df):
    """图9: 与深圳城中村街景指标对比"""
    # 深圳城中村参考值 (来自已有分析)
    shenzhen_ref = {
        'GVI': 0.15,
        'sky_ratio': 0.12,
        'building_ratio': 0.35,
        'road_ratio': 0.18,
        'brightness': 0.55,
        'openness': 0.30,
    }

    guishan_means = {}
    for key, hsv_key in [('GVI', 'hsv_GVI'), ('sky_ratio', 'hsv_sky_ratio'),
                          ('building_ratio', 'hsv_building_ratio'),
                          ('road_ratio', 'hsv_road_ratio'),
                          ('brightness', 'hsv_brightness'),
                          ('openness', 'hsv_openness')]:
        if hsv_key in df.columns:
            guishan_means[key] = df[hsv_key].mean()

    if not guishan_means:
        print("  [SKIP] 图9: 无对比数据")
        return

    common_keys = [k for k in shenzhen_ref if k in guishan_means]
    labels_cn = {'GVI': '绿视率', 'sky_ratio': '天空比', 'building_ratio': '建筑比',
                 'road_ratio': '路面比', 'brightness': '亮度', 'openness': '开放度'}

    fig, ax = plt.subplots(figsize=(14, 8))
    x = np.arange(len(common_keys))
    width = 0.35

    gs_vals = [guishan_means[k] for k in common_keys]
    sz_vals = [shenzhen_ref[k] for k in common_keys]

    bars1 = ax.bar(x - width/2, gs_vals, width, label='桂山岛 (均值)',
                    color='#2E75B6', alpha=0.85, edgecolor='white')
    bars2 = ax.bar(x + width/2, sz_vals, width, label='深圳城中村 (参考)',
                    color='#C0392B', alpha=0.85, edgecolor='white')

    # fold-change 标注
    for i, k in enumerate(common_keys):
        gv = guishan_means[k]
        sv = shenzhen_ref[k]
        if sv > 0:
            fc = gv / sv
            if fc > 1.5:
                annotate = f'{fc:.1f}x'
            elif fc < 0.67:
                annotate = f'{1/fc:.1f}x'
            else:
                annotate = f'~1x'

            y_top = max(gv, sv)
            ax.text(x[i], y_top + 0.02, annotate, ha='center', fontsize=10,
                    fontweight='bold', color='#333',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFFFCC', alpha=0.8))

    ax.set_xticks(x)
    ax.set_xticklabels([labels_cn.get(k, k) for k in common_keys], fontsize=12)
    ax.set_ylabel('指标值', fontsize=12)
    ax.set_title('桂山岛 vs 深圳城中村街景指标对比 (标注倍数差异)', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='upper right')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_ylim(bottom=0)

    fig.savefig(str(OUTPUT_DIR / 'fig9_shenzhen_comparison.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("  [OK] 图9: 深圳对比图")


if __name__ == '__main__':
    main()
