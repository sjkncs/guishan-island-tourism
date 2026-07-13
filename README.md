# 桂山岛文旅体验现状分析

**Guishan Island Tourism Experience Analysis**

基于多平台社交媒体评论NLP分析与高德云图AOI级客流画像的珠海桂山岛文旅体验研究。

## 研究背景

桂山岛位于珠海市香洲区桂山镇，是万山群岛中距大陆最近的有人居住海岛，国家4A级旅游景区。本项目为城乡规划专业本科生田野调研(2026年7月15-17日)的数据准备，旨在通过多源数据分析揭示桂山岛文旅体验现状与问题。

## 数据来源

### 社交媒体评论 (440条)
- 携程/Trip.com (123条)
- 永安旅游 WingOn Travel (169条)
- 易游网 (105条)
- Tripadvisor (6条)
- 小红书 (5条)
- 知乎 (10条)
- 微博 (2条)
- 黑猫投诉 (5条)
- 南方+ (6条)
- 其他: 珠海票务网/问卷星/珠海新闻网 (9条)

### POI数据 (115个)
- 高德地图API搜索 (via cloudmap-gateway MCP)
- 覆盖: 住宿/餐饮/景点/交通/购物/公共设施

### 客流画像 (高德云图AOI级)
- 桂山岛风景区 AOI (B0FFFQ7RVA, 4A景区)
- 月均日客流UV ~5000
- 8个月时序数据 (2025.11-2026.06)
- 78维画像标签: 年龄/性别/消费/交通/酒店偏好等

## 方法

1. LLM三级场景标签分类 (GPT-5.5): 大类/中类/细类, 100%覆盖
2. 平衡采样: 按平台/月份/类别分层, 防止过拟合
3. 同比环比分析: 2025 vs 2026场景标签变化趋势
4. 跨平台名称标准化: 繁体转简体 + 模糊匹配, POI匹配率100%
5. AOI级客流画像: 高德云图行政区+AOI双尺度对比

## 目录结构

```
数据采集/
  scripts/          分析脚本
    guishan_collector.py      数据采集框架
    merge_and_analyze.py      评论合并与关键词分析
    llm_classify_and_export.py LLM三级分类
    merge_review_poi.py       评论-POI关联
    fix_and_rebuild.py        口径修复与Excel重建
    rebuild_excel.py          Excel生成(旧版)
    real_basemap.py           真实底图生成
    export_poi_map.py         POI地图导出
    export_timeline_ppt.py    时序分析+PPT生成
    export_cloudmap.py        高德云图数据导出
    export_aoi.py             AOI级分析导出
  raw/              原始数据
    amap_poi_guishan.json     高德POI(115个)
    *.json                    各平台评论原始数据
  processed/        处理结果
    all_reviews_llm.json      LLM标注后的440条评论
    桂山岛评论分析.xlsx        评论-POI合并明细(4 sheets)
    桂山岛POI数据.xlsx         POI数据表
    桂山岛_云图时序分析.xlsx    8个月AOI时序数据
    桂山岛_高德云图分析_v2.xlsx AOI vs 行政区对比
    桂山岛游客画像.pptx        游客画像分析PPT(10页)
    桂山岛POI地图_交互版.html  交互式POI地图(Leaflet)
    *.png                      POI分布图/底图
```

## 关键发现

1. 核心客群: 35-54岁家庭客群占比超60%, 19-24岁仅4-5%
2. 消费特征: 中档消费为主(70%), 餐饮定价应控制在人均100元内
3. 住宿偏好: 民宿/经济型占90%, 不宜过度开发高端酒店
4. 交通方式: 火车58%+飞机30%, 远程游客比例大
5. 岛民结构: 居住人口UV 1605, 商业服务从业者占46%, 经济高度依赖旅游

## 技术栈

- Python 3.14 + openpyxl + python-pptx + matplotlib
- 高德云图MCP (cloudmap-gateway)
- LLM API: lanyiapi.com (GPT-5.5)
- 地图: Leaflet.js + 高德卫星瓦片 (免key)
- 底图: contextily (OSM/Esri瓦片)

## License

MIT

## 作者

城乡规划研究组 | 2026年7月
