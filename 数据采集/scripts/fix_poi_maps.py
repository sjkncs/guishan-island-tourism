# -*- coding: utf-8 -*-
"""修复版：桂山岛POI底图生成（坐标轴格式修正）"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

with open(r'E:\珠海桂山岛案例\数据采集\raw\amap_poi_guishan.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
pois = data['pois']

cat_style = {
    '住宿': {'color': '#2196F3', 'marker': 'o', 'size': 60},
    '景点': {'color': '#4CAF50', 'marker': '*', 'size': 120},
    '餐饮': {'color': '#FF9800', 'marker': 's', 'size': 70},
    '购物': {'color': '#9C27B0', 'marker': 'D', 'size': 50},
    '交通': {'color': '#00BCD4', 'marker': '^', 'size': 80},
    '公共设施': {'color': '#FFC107', 'marker': 'P', 'size': 60},
    '休闲': {'color': '#E91E63', 'marker': 'v', 'size': 50},
    '生活服务': {'color': '#8BC34A', 'marker': 'p', 'size': 50},
    '医疗': {'color': '#F44336', 'marker': '+', 'size': 80},
    '教育': {'color': '#3F51B5', 'marker': 'h', 'size': 60},
    '政府': {'color': '#795548', 'marker': 'X', 'size': 70},
    '地名': {'color': '#607D8B', 'marker': '.', 'size': 40},
    '汽车服务': {'color': '#9E9E9E', 'marker': 'd', 'size': 40},
}
cat_label = {
    '住宿': '住宿(民宿/酒店)', '景点': '景点(景区/公园)', '餐饮': '餐饮(餐厅/海鲜)',
    '购物': '购物(商店/超市)', '交通': '交通(码头/车站)', '公共设施': '公共设施(厕所/银行)',
    '休闲': '休闲(咖啡/娱乐)', '生活服务': '生活服务', '医疗': '医疗(卫生院)',
    '教育': '教育(学校)', '政府': '政府(村委会)', '地名': '地名', '汽车服务': '汽车服务',
}

island_pois = [p for p in pois
               if 'location' in p and 22.12 <= p['location']['lat'] <= 22.16
               and 113.81 <= p['location']['lng'] <= 113.85]
other_pois = [p for p in pois if p not in island_pois and 'location' in p]

OUT = r'C:\Users\Administrator\.qoderwork\workspace\mritsdpuqphp34kx\outputs'

# ═══════════════════════════════════════════
# 图1: 全岛总览（双面板：主图聚焦岛内 + 副图珠三角区位）
# ═══════════════════════════════════════════
fig1 = plt.figure(figsize=(12, 9))

# 主图
ax1 = fig1.add_axes([0.08, 0.08, 0.55, 0.82])
ax1.set_facecolor('#E8F4FD')

plotted = set()
for p in island_pois:
    cat = p.get('category', '未知')
    st = cat_style.get(cat, {'color': '#757575', 'marker': '.', 'size': 40})
    loc = p['location']
    lbl = cat_label.get(cat, cat) if cat not in plotted else None
    plotted.add(cat)
    ax1.scatter(loc['lng'], loc['lat'], c=st['color'], s=st['size'] * 1.5,
                marker=st['marker'], alpha=0.85, zorder=3, label=lbl,
                edgecolors='white', linewidth=0.5)

# 关键POI标注
key_names = ['桂山岛风景区', '桂山灯塔', '桂山舰纪念公园', '万山海战遗址',
             '妈祖庙', '文天祥广场', '一湾沙滩', '桂山码头', '桂山客运站',
             '桂山小学', '桂山镇中心卫生院']
for p in island_pois:
    name = p.get('name', '')
    if any(k in name for k in key_names):
        loc = p['location']
        ax1.annotate(name, (loc['lng'], loc['lat']), fontsize=7, fontweight='bold',
                     color='#1A2744', xytext=(4, 4), textcoords='offset points',
                     bbox=dict(boxstyle='round,pad=0.25', facecolor='white',
                               alpha=0.85, edgecolor='#CCCCCC'), zorder=5)

ax1.set_xlim(113.810, 113.845)
ax1.set_ylim(22.122, 22.158)
ax1.xaxis.set_major_formatter(ticker.FormatStrFormatter('%.3f'))
ax1.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.3f'))
ax1.set_xlabel('经度 (Longitude)', fontsize=10)
ax1.set_ylabel('纬度 (Latitude)', fontsize=10)
ax1.set_title('珠海桂山岛 POI 空间分布总览（115个兴趣点）',
              fontsize=14, fontweight='bold', pad=12)
ax1.legend(loc='lower left', fontsize=7, framealpha=0.9, ncol=2,
           title='POI类别', title_fontsize=8)
ax1.grid(True, alpha=0.3, linestyle='--')

# 指北针
ax1.annotate('N', xy=(113.842, 22.155), fontsize=12, fontweight='bold',
             ha='center', color='#1A2744')
ax1.annotate('', xy=(113.842, 22.157), xytext=(113.842, 22.153),
             arrowprops=dict(arrowstyle='->', color='#1A2744', lw=2))

# 比例尺
ax1.plot([113.835, 113.845], [22.124, 22.124], 'k-', linewidth=2)
ax1.annotate('约1km', xy=(113.840, 22.1235), fontsize=8, ha='center', color='#666666')

# 副图：珠三角区位
ax2 = fig1.add_axes([0.68, 0.45, 0.28, 0.45])
ax2.set_facecolor('#F5F5F5')

for p in other_pois:
    loc = p['location']
    ax2.scatter(loc['lng'], loc['lat'], c='#BDBDBD', s=15, marker='.', alpha=0.6)

ax2.scatter([113.828], [22.140], c='#F44336', s=200, marker='*', zorder=5,
            edgecolors='#B71C1C', linewidth=1)
ax2.annotate('桂山岛', (113.828, 22.140), fontsize=9, fontweight='bold',
             color='#B71C1C', xytext=(10, -5), textcoords='offset points')

cities = {'珠海': (113.58, 22.28), '澳门': (113.55, 22.20),
          '香港': (114.17, 22.32), '深圳': (114.06, 22.55)}
for cname, (cx, cy) in cities.items():
    ax2.scatter(cx, cy, c='#1A2744', s=30, marker='o', zorder=4)
    ax2.annotate(cname, (cx, cy), fontsize=8, color='#1A2744',
                 xytext=(3, 3), textcoords='offset points')

ax2.set_xlim(113.4, 114.3)
ax2.set_ylim(22.1, 22.6)
ax2.set_title('珠三角区位', fontsize=10, fontweight='bold')
ax2.set_xlabel('经度', fontsize=8)
ax2.set_ylabel('纬度', fontsize=8)
ax2.xaxis.set_major_formatter(ticker.FormatStrFormatter('%.1f'))
ax2.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.1f'))
ax2.tick_params(labelsize=7)
ax2.grid(True, alpha=0.2, linestyle='--')

fig1.savefig(os.path.join(OUT, '桂山岛POI分布_全岛总览.png'),
             dpi=150, bbox_inches='tight', facecolor='white')
plt.close(fig1)
print('全岛总览 OK')

# ═══════════════════════════════════════════
# 图2: 岛内详图（修复经度轴格式）
# ═══════════════════════════════════════════
fig2, ax3 = plt.subplots(1, 1, figsize=(12, 10))
ax3.set_facecolor('#E8F4FD')

plotted2 = set()
for p in island_pois:
    cat = p.get('category', '未知')
    st = cat_style.get(cat, {'color': '#757575', 'marker': '.', 'size': 40})
    loc = p['location']
    lbl = cat_label.get(cat, cat) if cat not in plotted2 else None
    plotted2.add(cat)
    ax3.scatter(loc['lng'], loc['lat'], c=st['color'], s=st['size'] * 2,
                marker=st['marker'], alpha=0.85, zorder=3, label=lbl,
                edgecolors='white', linewidth=0.8)

# 标注全部POI
for p in island_pois:
    name = p.get('name', '')
    loc = p['location']
    short = name.replace('珠海桂山岛', '').replace('桂山岛', '').replace('(珠海桂山岛店)', '')
    if len(short) > 12:
        short = short[:12] + '..'
    ax3.annotate(short, (loc['lng'], loc['lat']), fontsize=6.5, color='#333333',
                 xytext=(3, 3), textcoords='offset points',
                 bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                           alpha=0.7, edgecolor='#DDDDDD'), zorder=5)

ax3.set_xlim(113.815, 113.840)
ax3.set_ylim(22.125, 22.155)
ax3.xaxis.set_major_formatter(ticker.FormatStrFormatter('%.3f'))
ax3.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.3f'))
ax3.set_xlabel('经度 (Longitude)', fontsize=11)
ax3.set_ylabel('纬度 (Latitude)', fontsize=11)
ax3.set_title('桂山岛本体 POI 详细分布（岛内放大视图）',
              fontsize=14, fontweight='bold', pad=12)
ax3.legend(loc='lower right', fontsize=8, framealpha=0.9, ncol=2,
           title='POI类别', title_fontsize=9)
ax3.grid(True, alpha=0.3, linestyle='--')

# 指北针
ax3.annotate('N', xy=(113.837, 22.152), fontsize=13, fontweight='bold',
             ha='center', color='#1A2744')
ax3.annotate('', xy=(113.837, 22.154), xytext=(113.837, 22.150),
             arrowprops=dict(arrowstyle='->', color='#1A2744', lw=2))

plt.tight_layout()
fig2.savefig(os.path.join(OUT, '桂山岛POI分布_岛内详图.png'),
             dpi=150, bbox_inches='tight', facecolor='white')
plt.close(fig2)
print('岛内详图 OK')

# 验证尺寸
from PIL import Image
for f in ['桂山岛POI分布_全岛总览.png', '桂山岛POI分布_岛内详图.png']:
    img = Image.open(os.path.join(OUT, f))
    sz = os.path.getsize(os.path.join(OUT, f))
    print(f'{f}: {img.size[0]}x{img.size[1]} px, {sz/1024:.0f} KB')
