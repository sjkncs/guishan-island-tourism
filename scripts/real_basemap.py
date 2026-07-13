# -*- coding: utf-8 -*-
"""
真实底图 + POI叠加（contextily OSM瓦片）
"""
import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

import contextily as cx
import geopandas as gpd
from shapely.geometry import Point

# 加载数据
with open(r'E:\珠海桂山岛案例\数据采集\raw\amap_poi_guishan.json', 'r', encoding='utf-8') as f:
    pois = json.load(f)['pois']

# 过滤岛内POI
island_pois = [p for p in pois
               if 'location' in p
               and 22.12 <= p['location']['lat'] <= 22.16
               and 113.81 <= p['location']['lng'] <= 113.85]

print(f"岛内POI: {len(island_pois)}")

# 构建GeoDataFrame
records = []
for p in island_pois:
    loc = p['location']
    records.append({
        'name': p.get('name', ''),
        'category': p.get('category', ''),
        'rating': p.get('rating', ''),
        'geometry': Point(loc['lng'], loc['lat'])
    })

gdf = gpd.GeoDataFrame(records, crs='EPSG:4326')

# 类别配色
cat_style = {
    '住宿': {'color': '#2196F3', 'marker': 'o', 'size': 50},
    '景点': {'color': '#4CAF50', 'marker': '*', 'size': 100},
    '餐饮': {'color': '#FF9800', 'marker': 's', 'size': 60},
    '购物': {'color': '#9C27B0', 'marker': 'D', 'size': 40},
    '交通': {'color': '#00BCD4', 'marker': '^', 'size': 70},
    '公共设施': {'color': '#FFC107', 'marker': 'P', 'size': 50},
    '休闲': {'color': '#E91E63', 'marker': 'v', 'size': 40},
    '生活服务': {'color': '#8BC34A', 'marker': 'p', 'size': 40},
    '医疗': {'color': '#F44336', 'marker': '+', 'size': 70},
    '教育': {'color': '#3F51B5', 'marker': 'h', 'size': 50},
    '政府': {'color': '#795548', 'marker': 'X', 'size': 60},
    '地名': {'color': '#607D8B', 'marker': '.', 'size': 30},
    '汽车服务': {'color': '#9E9E9E', 'marker': 'd', 'size': 30},
}
cat_label = {
    '住宿': '住宿', '景点': '景点', '餐饮': '餐饮', '购物': '购物',
    '交通': '交通', '公共设施': '公共设施', '休闲': '休闲',
    '生活服务': '生活服务', '医疗': '医疗', '教育': '教育',
    '政府': '政府', '地名': '地名', '汽车服务': '汽车服务',
}

OUT = r'C:\Users\Administrator\.qoderwork\workspace\mritsdpuqphp34kx\outputs'

# ── 图1: 全岛总览 + OSM底图 ──
fig1, ax1 = plt.subplots(figsize=(12, 10))

# 按类别分层绘制
plotted = set()
for cat in cat_style:
    subset = gdf[gdf['category'] == cat]
    if len(subset) == 0:
        continue
    st = cat_style[cat]
    lbl = cat_label.get(cat, cat) if cat not in plotted else None
    plotted.add(cat)
    ax1.scatter(subset.geometry.x, subset.geometry.y,
                marker=st['marker'], c=st['color'], s=st['size'],
                label=lbl, zorder=5, edgecolors='white', linewidths=0.5)

# 标注关键POI
key_names = ['桂山岛风景区', '桂山灯塔', '桂山舰纪念公园', '万山海战遗址',
             '妈祖庙', '文天祥广场', '一湾沙滩', '桂山码头', '桂山小学',
             '桂山镇中心卫生院']
for _, row in gdf.iterrows():
    name = row['name']
    if any(k in name for k in key_names):
        x, y = row.geometry.x, row.geometry.y
        short = name.replace('珠海桂山岛', '').replace('桂山岛', '')
        ax1.annotate(short, (x, y), fontsize=7, fontweight='bold', color='#1A2744',
                     xytext=(5, 5), textcoords='offset points',
                     bbox=dict(boxstyle='round,pad=0.25', facecolor='white',
                               alpha=0.85, edgecolor='#CCCCCC'), zorder=6)

# 添加底图
try:
    cx.add_basemap(ax1, crs=gdf.crs, source=cx.providers.OpenStreetMap.Mapnik,
                   attribution='© OpenStreetMap', zoom=14)
    print("底图加载成功: OpenStreetMap.Mapnik")
except Exception as e:
    print(f"底图加载失败: {e}, 尝试备用源...")
    try:
        cx.add_basemap(ax1, crs=gdf.crs, source=cx.providers.CartoDB.Positron, zoom=14)
        print("备用底图: CartoDB.Positron")
    except Exception as e2:
        print(f"备用也失败: {e2}")

ax1.set_title('桂山岛 POI 空间分布（真实底图叠加）', fontsize=14, fontweight='bold', pad=12)
ax1.legend(loc='lower left', fontsize=8, framealpha=0.9, ncol=2,
           title='POI类别', title_fontsize=9)

fig1.savefig(os.path.join(OUT, '桂山岛POI_真实底图.png'), dpi=150, bbox_inches='tight', facecolor='white')
plt.close(fig1)
print(f"保存: 桂山岛POI_真实底图.png")

# ── 图2: 岛内详图 + 卫星影像底图 ──
fig2, ax2 = plt.subplots(figsize=(12, 12))

plotted2 = set()
for cat in cat_style:
    subset = gdf[gdf['category'] == cat]
    if len(subset) == 0:
        continue
    st = cat_style[cat]
    lbl = cat_label.get(cat, cat) if cat not in plotted2 else None
    plotted2.add(cat)
    ax2.scatter(subset.geometry.x, subset.geometry.y,
                marker=st['marker'], c=st['color'], s=st['size'] * 1.5,
                label=lbl, zorder=5, edgecolors='white', linewidths=0.8)

# 标注全部POI
for _, row in gdf.iterrows():
    name = row['name']
    x, y = row.geometry.x, row.geometry.y
    short = name.replace('珠海桂山岛', '').replace('桂山岛', '').replace('(珠海桂山岛店)', '')
    if len(short) > 10:
        short = short[:10] + '..'
    ax2.annotate(short, (x, y), fontsize=6, color='#333333',
                 xytext=(3, 3), textcoords='offset points',
                 bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                           alpha=0.75, edgecolor='#DDDDDD'), zorder=6)

# 卫星影像底图
try:
    cx.add_basemap(ax2, crs=gdf.crs, source=cx.providers.Esri.WorldImagery,
                   attribution='© Esri', zoom=16)
    print("卫星底图: Esri.WorldImagery")
except Exception as e:
    print(f"卫星底图失败: {e}, 尝试OSM...")
    try:
        cx.add_basemap(ax2, crs=gdf.crs, source=cx.providers.OpenStreetMap.Mapnik, zoom=16)
        print("降级: OpenStreetMap.Mapnik")
    except:
        pass

ax2.set_title('桂山岛 POI 详细分布（卫星影像叠加）', fontsize=14, fontweight='bold', pad=12)
ax2.legend(loc='lower right', fontsize=8, framealpha=0.9, ncol=2,
           title='POI类别', title_fontsize=9)

fig2.savefig(os.path.join(OUT, '桂山岛POI_卫星底图.png'), dpi=150, bbox_inches='tight', facecolor='white')
plt.close(fig2)
print(f"保存: 桂山岛POI_卫星底图.png")

# 验证尺寸
from PIL import Image
for f in ['桂山岛POI_真实底图.png', '桂山岛POI_卫星底图.png']:
    fp = os.path.join(OUT, f)
    if os.path.exists(fp):
        img = Image.open(fp)
        sz = os.path.getsize(fp)
        print(f'{f}: {img.size[0]}x{img.size[1]} px, {sz/1024:.0f} KB')
