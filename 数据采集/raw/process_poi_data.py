#!/usr/bin/env python3
"""
Process Amap POI search results for Guishan Island (桂山岛) and save to JSON.
Data collected from 20 search queries via Amap API on 2026-07-13.
"""
import json
import os
from datetime import datetime

# ============================================================
# All raw POI data from 20 search queries
# Each search result has been processed to extract unique POIs
# ============================================================

search_queries = [
    "桂山岛 景点",
    "桂山岛 餐饮",
    "桂山岛 酒店",
    "桂山岛 民宿",
    "桂山岛 码头",
    "桂山岛 沙滩",
    "桂山岛 灯塔",
    "桂山岛 卫生",
    "桂山岛 商店",
    "桂山岛 咖啡",
    "桂山岛 海鲜",
    "桂山岛 交通",
    "桂山岛 公园",
    "桂山岛 广场",
    "桂山岛 庙",
    "桂山岛 学校",
    "桂山岛 ATM",
    "桂山岛 公厕",
    "桂山岛 停车场",
    "万山群岛 景点",
]

# Map keyword -> search_query for traceability
keyword_map = {
    "桂山岛 景点": "桂山岛 景点",
    "桂山岛 餐饮": "桂山岛 餐饮",
    "桂山岛 酒店": "桂山岛 酒店",
    "桂山岛 民宿": "桂山岛 民宿",
    "桂山岛 码头": "桂山岛 码头",
    "桂山岛 沙滩": "桂山岛 沙滩",
    "桂山岛 灯塔": "桂山岛 灯塔",
    "桂山岛 卫生": "桂山岛 医院/卫生",
    "桂山岛 商店": "桂山岛 超市/商店",
    "桂山岛 咖啡": "桂山岛 咖啡",
    "桂山岛 海鲜": "桂山岛 海鲜",
    "桂山岛 交通": "桂山岛 交通",
    "桂山岛 公园": "桂山岛 公园",
    "桂山岛 广场": "桂山岛 广场",
    "桂山岛 庙": "桂山岛 寺庙/庙",
    "桂山岛 学校": "桂山岛 学校",
    "桂山岛 ATM": "桂山岛 银行/ATM",
    "桂山岛 公厕": "桂山岛 公厕",
    "桂山岛 停车场": "桂山岛 停车场",
    "万山群岛 景点": "万山群岛 景点",
}

# All POI data collected from searches (deduplicated by poi_id)
# Format: {poi_id: {all fields}}
all_pois = {}

def parse_location(loc_str):
    """Parse 'lng,lat' string to dict."""
    if not loc_str or not isinstance(loc_str, str):
        return {"lat": None, "lng": None}
    parts = loc_str.split(",")
    if len(parts) == 2:
        try:
            return {"lat": float(parts[1]), "lng": float(parts[0])}
        except ValueError:
            return {"lat": None, "lng": None}
    return {"lat": None, "lng": None}

def parse_tel(tel_val):
    """Parse tel field which can be string or list."""
    if isinstance(tel_val, list):
        return ";".join(str(t) for t in tel_val if t) or ""
    if isinstance(tel_val, str):
        return tel_val
    return ""

def extract_rating(biz_ext):
    """Extract rating from biz_ext."""
    if not biz_ext:
        return ""
    rating = biz_ext.get("rating", "")
    if isinstance(rating, list):
        return ""
    return str(rating) if rating else ""

def extract_cost(biz_ext):
    """Extract cost from biz_ext."""
    if not biz_ext:
        return ""
    cost = biz_ext.get("cost", "")
    if isinstance(cost, list):
        return ""
    return str(cost) if cost else ""

def extract_photos(photos_list):
    """Extract photo URLs."""
    if not photos_list:
        return []
    result = []
    for p in photos_list:
        url = p.get("url", "")
        title = p.get("title", "")
        if isinstance(title, list):
            title = ""
        if url:
            result.append({"title": title, "url": url})
    return result

def add_poi(poi_data, search_keyword):
    """Add a POI to the collection, tracking which keyword found it."""
    poi_id = poi_data.get("id", "")
    if not poi_id:
        return

    if poi_id in all_pois:
        # Already exists, just add the keyword if new
        existing_kw = all_pois[poi_id].get("search_keywords", [])
        if search_keyword not in existing_kw:
            existing_kw.append(search_keyword)
        return

    biz_ext = poi_data.get("biz_ext", {}) or {}
    loc = parse_location(poi_data.get("location", ""))

    # Determine category type
    poi_type = poi_data.get("type", "")
    typecode = poi_data.get("typecode", "")

    # Categorize
    category = "其他"
    if typecode.startswith("11"):
        category = "景点"
    elif typecode.startswith("05"):
        category = "餐饮"
    elif typecode.startswith("10"):
        category = "住宿"
    elif typecode.startswith("15"):
        category = "交通"
    elif typecode.startswith("06"):
        category = "购物"
    elif typecode.startswith("09"):
        category = "医疗"
    elif typecode.startswith("20"):
        category = "公共设施"
    elif typecode.startswith("14"):
        category = "教育"
    elif typecode.startswith("08"):
        category = "休闲"
    elif typecode.startswith("13"):
        category = "政府"
    elif typecode.startswith("07"):
        category = "生活服务"
    elif typecode.startswith("19"):
        category = "地名"
    elif typecode.startswith("01"):
        category = "汽车服务"

    record = {
        "poi_id": poi_id,
        "name": poi_data.get("name", ""),
        "address": poi_data.get("address", "") if isinstance(poi_data.get("address", ""), str) else "",
        "location": loc,
        "type": poi_type,
        "typecode": typecode,
        "category": category,
        "tel": parse_tel(poi_data.get("tel", "")),
        "rating": extract_rating(biz_ext),
        "cost": extract_cost(biz_ext),
        "business_area": poi_data.get("business_area", ""),
        "keytag": poi_data.get("keytag", ""),
        "biz_type": poi_data.get("biz_type", ""),
        "open_time": biz_ext.get("opentime2", "") if biz_ext else "",
        "search_keyword": search_keyword,
        "search_keywords": [search_keyword],
        "photos": extract_photos(poi_data.get("photos", [])),
        "province": poi_data.get("pname", ""),
        "city": poi_data.get("cityname", ""),
        "district": poi_data.get("adname", ""),
    }
    all_pois[poi_id] = record


# ============================================================
# Raw POI data from each search query
# ============================================================

# Query 1: 桂山岛 景点 (count: 23)
query1_pois = [
    {"id":"B0J14HWJZA","name":"北山观景台","type":"风景名胜;风景名胜;观景点","typecode":"110209","biz_type":"tour","address":"桂山岛风景区(东南角)","location":"113.829894,22.141812","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.1","cost":[]},"photos":[{"title":[],"url":"https://aos-comment.amap.com/B0J14HWJZA/comment/b7f0dda0e3851a1b38c755d9abad866e_2048_2048_80.jpg"}],"keytag":"自然风光"},
    {"id":"B0FFFQ7RVA","name":"桂山岛风景区","type":"风景名胜;风景名胜;国家级景点","typecode":"110202","biz_type":"tour","address":"桂山镇桂山岛","location":"113.825170,22.146603","tel":"0756-2627999;0756-6995012","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.7","cost":[]},"photos":[{"title":[],"url":"http://store.is.autonavi.com/showpic/1867aaa4ab502757b0cb0a906ad415e8"}],"keytag":"4A景区"},
    {"id":"B0FFGG0HB1","name":"桂山舰纪念公园","type":"风景名胜;公园广场;公园","typecode":"110101","biz_type":"tour","address":"桂山岛","location":"113.819038,22.129891","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.1","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/166ee285ca0fdffd6bb055b23f4b4a72"}],"keytag":"纪念公园"},
    {"id":"B0FFKWIUNE","name":"妈祖庙","type":"风景名胜;风景名胜;寺庙道观","typecode":"110205","biz_type":"tour","address":"桂山岛风景区内(南侧)","location":"113.824090,22.132213","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.1","cost":[]},"photos":[{"title":[],"url":"https://aos-comment.amap.com/B0FFKWIUNE/comment/C954C2EB_0FA9_417B_A5C9_C1B4397324ED_L0_001_1320_168_1765411531760_47454554.jpg"}],"keytag":"寺庙"},
    {"id":"B0GDLMHVZ2","name":"桂山岛游客中心","type":"生活服务;信息咨询中心;服务中心","typecode":"070201","biz_type":"","address":"唐家湾镇港珠澳大桥1号码头-桂山镇","location":"113.823594,22.136275","tel":"0756-2627999","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[{"title":[],"url":"https://aos-comment.amap.com/B0GDLMHVZ2/comment/9364a4c4a2f728aa6f77559b0c942fd1_2048_2048_80.jpg"}],"keytag":"游客中心"},
    {"id":"B0FFFS8BOI","name":"文天祥广场","type":"风景名胜;公园广场;城市广场","typecode":"110105","biz_type":"tour","address":"桂山村","location":"113.823781,22.139505","tel":"0756-8851100","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.9","cost":[]},"photos":[{"title":[],"url":"http://store.is.autonavi.com/showpic/c72596e0fa8394802a3653d7d2c62534"}],"keytag":"广场"},
    {"id":"B0LGJMPQ5I","name":"一湾沙滩","type":"风景名胜;风景名胜;风景名胜","typecode":"110200","biz_type":"tour","address":"熊猫精酿(桂山岛店)东侧","location":"113.819176,22.133583","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.0","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/df0049ee3311d44a0000002472750378?type=pic"}],"keytag":"海滨沙滩"},
    {"id":"B0GDRRC50K","name":"一号堤","type":"风景名胜;风景名胜相关;旅游景点","typecode":"110000","biz_type":"tour","address":"桂山岛风景区(西南角)","location":"113.818563,22.133490","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.0","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/34d96f2cb4c653c50000002472732529?type=pic"}],"keytag":"景区"},
    {"id":"B0FFK80UCK","name":"桂山灯塔","type":"风景名胜;风景名胜相关;旅游景点","typecode":"110000","biz_type":"tour","address":"桂山镇桂山岛桂山一路左边200米","location":"113.818789,22.132908","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.9","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/ddd6b5de64b677d60000002472774241?type=pic"}],"keytag":"文物古迹"},
    {"id":"B0H2JMT2WT","name":"万山海战遗址","type":"风景名胜;风景名胜;红色景区","typecode":"110210","biz_type":"tour","address":"桂山镇桂山岛吊藤湾","location":"113.819144,22.129621","tel":"0756-8851100","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.7","cost":[]},"photos":[{"title":[],"url":"http://store.is.autonavi.com/showpic/35c841ba6adf63f81b616e46f5376624"}],"keytag":"文物古迹"},
    {"id":"B0MURXI56V","name":"桂山岛3海里打卡点","type":"风景名胜;风景名胜;风景名胜","typecode":"110200","biz_type":"tour","address":"环岛路驿站左边前300米","location":"113.835687,22.138405","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.0","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/1dc4085c6dc8553766c1adf11f584abf"}],"keytag":"风景名胜"},
    {"id":"B0JRR5TB8X","name":"桂山舰烈士陵园","type":"生活服务;丧葬设施;陵园","typecode":"071901","biz_type":"","address":"桂山镇人民政府东侧100米","location":"113.824550,22.137278","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/800da68fdb8fcc6da60f350c1856d9ec"}],"keytag":"烈士陵园"},
    {"id":"B0J2JDC5LX","name":"环翠亭","type":"风景名胜;风景名胜;风景名胜","typecode":"110200","biz_type":"tour","address":"桂山岛风景区内(南侧)","location":"113.822358,22.128105","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.5","cost":[]},"photos":[{"title":[],"url":"http://store.is.autonavi.com/showpic/3a4c41a3011fe62b70016b2a2a4e6d8b"}],"keytag":"景区"},
    {"id":"B0KKOKX9FZ","name":"观澜亭","type":"风景名胜;风景名胜;风景名胜","typecode":"110200","biz_type":"tour","address":"桂山舰纪念公园","location":"113.818349,22.130062","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.5","cost":[]},"photos":[{"title":[],"url":"http://store.is.autonavi.com/showpic/9b3a615c6d949bb3682ecc0b661ea1c4"}],"keytag":"纪念公园"},
    {"id":"B0LRO6UU4T","name":"外伶仃岛桂山岛航线(桂山岛-外伶仃岛)","type":"风景名胜;风景名胜;风景名胜","typecode":"110200","biz_type":"tour","address":"桂山岛客运站售票处南侧","location":"113.821130,22.134583","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.2","cost":[]},"photos":[{"title":[],"url":"https://aos-comment.amap.com/B0LBACGA9I/comment/D93C383B_D31D_4F90_92A9_31161F2A1537_L0_001_1290_1646_1743293163721_74455937.jpg"}],"keytag":"风景名胜"},
    {"id":"B0GDRRD61K","name":"桂山号英雄登陆点","type":"风景名胜;风景名胜相关;旅游景点","typecode":"110000","biz_type":"tour","address":"桂山舰纪念公园内","location":"113.818517,22.129778","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.3","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/219c6b2f864939f51ce501e93d6be176"}],"keytag":"纪念公园"},
    {"id":"B0GDRRCR8K","name":"码头广场","type":"风景名胜;公园广场;城市广场","typecode":"110105","biz_type":"tour","address":"桂山岛风景区内(南侧)","location":"113.821395,22.134418","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.2","cost":[]},"photos":[{"title":[],"url":"https://aos-comment.amap.com/B0GDRRCR8K/comment/4c818007ed3663c0b58e1e44603039e9_2048_2048_80.jpg"}],"keytag":"广场"},
    {"id":"B0LDP72SPX","name":"桂山法治文化公园","type":"风景名胜;公园广场;公园","typecode":"110101","biz_type":"tour","address":"桂山小学北侧220米","location":"113.823981,22.142053","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"2.6","cost":[]},"photos":[{"title":[],"url":"https://aos-comment.amap.com/B0LDP72SPX/comment/content_media_external_file_1000036363_ss__1771342469797_49344726.jpg"}],"keytag":"公园"},
    {"id":"B0LK55SMOQ","name":"桂山镇圩镇客厅","type":"风景名胜;风景名胜相关;旅游景点","typecode":"110000","biz_type":"tour","address":"桂山文化中心","location":"113.823518,22.138908","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"1.7","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/bdea5c7bc9f9192b8d3c0e0dc8fc7954"}],"keytag":"旅游景点"},
    {"id":"B0MALL8AJL","name":"万山海战遗址文物碑","type":"风景名胜;风景名胜;风景名胜","typecode":"110200","biz_type":"tour","address":"万山海战遗址","location":"113.819125,22.130975","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.3","cost":[]},"photos":[],"keytag":"文物古迹"},
]

# Query 2: 桂山岛 餐饮 (count: 15)
query2_pois = [
    {"id":"B0FFGPYFGT","name":"桂山岛江兴海鲜餐厅","type":"餐饮服务;中餐厅;中餐厅","typecode":"050100","biz_type":"diner","address":"桂海一路37号","location":"113.824088,22.135482","tel":"0756-8851311","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.4","cost":"86.00"},"photos":[{"title":[],"url":"https://aos-comment.amap.com/B0FFGPYFGT/comment/72c26459761b0c9310829d954446dd30_2048_2048_80.jpg"}],"keytag":"海鲜餐厅"},
    {"id":"B0HU9H6F80","name":"鲜也海鲜餐厅","type":"餐饮服务;中餐厅;海鲜酒楼","typecode":"050119","biz_type":"diner","address":"桂山镇桂山大道海鲜街3-5号","location":"113.823055,22.138216","tel":"13380642910","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.0","cost":"99.00"},"photos":[{"title":[],"url":"https://aos-comment.amap.com/B0HU9H6F80/comment/content_media_external_file_1000036270_ss__1770456212051_74240243.jpg"}],"keytag":"海鲜"},
    {"id":"B0KKOL2F58","name":"珠海市桂山镇肆号餐饮店","type":"餐饮服务;中餐厅;中餐厅","typecode":"050100","biz_type":"diner","address":"桂山镇平安路4号","location":"113.825294,22.137861","tel":"13726259861","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.2","cost":"79.00"},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/088e6238d8af10060000000736572205?type=pic"}],"keytag":"奶茶/茶饮"},
    {"id":"B0J1V916TR","name":"桂山·日月贝海鲜餐厅","type":"餐饮服务;中餐厅;海鲜酒楼","typecode":"050119","biz_type":"diner","address":"桂山镇人民政府西北侧60米","location":"113.823044,22.137409","tel":"13825671445","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.9","cost":"110.00"},"photos":[{"title":[],"url":"https://aos-comment.amap.com/B0J1V916TR/comment/content_media_external_file_1000036266_ss__1770455880165_19960825.jpg"}],"keytag":"海鲜"},
    {"id":"B0LKNMPQ1Q","name":"港式茶餐厅","type":"餐饮服务;快餐厅;快餐厅","typecode":"050300","biz_type":"diner","address":"桂海一路13-15号","location":"113.824120,22.136036","tel":"0756-8851136","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.0","cost":"37.00"},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/eb02d16e31fe3d701803f04ccb642547"}],"keytag":"茶餐厅"},
    {"id":"B0FFLHIUPL","name":"得意海鲜茶餐厅(桂山岛店)","type":"餐饮服务;餐饮相关场所;餐饮相关","typecode":"050000","biz_type":"diner","address":"桂山镇一环路桂海大道13-15号","location":"113.823655,22.135555","tel":"13544908076","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.6","cost":"61.00"},"photos":[{"title":[],"url":"http://store.is.autonavi.com/showpic/d1f89df82b44dbe57b6351740667efbc"}],"keytag":"茶餐厅"},
    {"id":"B0FFL4B2AJ","name":"淘小鲜海鲜餐厅","type":"餐饮服务;餐饮相关场所;餐饮相关","typecode":"050000","biz_type":"diner","address":"桂山镇桂山大道27号","location":"113.823005,22.135749","tel":"18028403888;18028404888","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.1","cost":"68.00"},"photos":[{"title":[],"url":"http://store.is.autonavi.com/showpic/6b41901b37f7f47d471b6d0692eb1329"}],"keytag":"海鲜餐厅"},
    {"id":"B0JBY5V507","name":"壹品汇海鲜餐厅海鲜加工(桂海一路店)","type":"餐饮服务;中餐厅;中餐厅","typecode":"050100","biz_type":"diner","address":"桂山派出所南侧","location":"113.823652,22.135941","tel":"13826777468","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.9","cost":"110.00"},"photos":[{"title":[],"url":"http://store.is.autonavi.com/showpic/9c41adba99f1125d97b23592fab32577"}],"keytag":"中餐"},
    {"id":"B0JGXG14P6","name":"港湾海鲜餐厅","type":"餐饮服务;中餐厅;海鲜酒楼","typecode":"050119","biz_type":"diner","address":"桂山岛一环路10号","location":"113.823523,22.135165","tel":"18219472627","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.5","cost":"68.00"},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/1086af58109436c9be9cce14e03fd73d"}],"keytag":"湛江菜"},
    {"id":"B0L3GLH57G","name":"桂山非遗工坊G-Coffee","type":"餐饮服务;咖啡厅;咖啡厅","typecode":"050500","biz_type":"diner","address":"桂山岛桂山村如意巷1-5号桂山非遗工坊","location":"113.824954,22.138570","tel":"18928057052","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.9","cost":"54.00"},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/91fad295a6aafd150000003060828717?type=pic"}],"keytag":"咖啡"},
    {"id":"B0FFHCYQ0K","name":"珠海市桂山镇零三八甜品屋","type":"餐饮服务;餐饮相关场所;餐饮相关","typecode":"050000","biz_type":"diner","address":"桂山镇桂海村交通大厦1层2号","location":"113.823402,22.135541","tel":"13543012722","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.7","cost":"15.00"},"photos":[{"title":[],"url":"http://store.is.autonavi.com/showpic/ac7f159ff3fe7827cb7cd83743c67168"}],"keytag":"甜品店"},
    {"id":"B0FFHS2WF9","name":"港龙茶餐厅(桂山岛风景区店)","type":"餐饮服务;中餐厅;中餐厅","typecode":"050100","biz_type":"diner","address":"新桂山酒店旁边","location":"113.822794,22.135300","tel":"13702314817","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.9","cost":"48.00"},"photos":[{"title":[],"url":"https://aos-comment.amap.com/B0FFHS2WF9/comment/FF1E7B52_9B3E_4D7B_AF87_29B729C304AC_L0_001_1500_200_1750586757837_57306017.jpg"}],"keytag":"茶餐厅"},
]

# Query 3: 桂山岛 酒店 (count: 85) - key entries
query3_pois = [
    {"id":"B0L6O5H637","name":"云锦阁民宿","type":"住宿服务;旅馆招待所;旅馆招待所","typecode":"100200","biz_type":"hotel","address":"桂山镇海湾路42号8栋1单元","location":"113.825652,22.142155","tel":"15812610590;15819414465","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.5","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/c1777f1db2a831fcb768fa386869da16"}],"keytag":"民宿"},
    {"id":"B0K34RKZOX","name":"桂山岛.喜悦精品民宿","type":"住宿服务;旅馆招待所;旅馆招待所","typecode":"100200","biz_type":"hotel","address":"桂山镇海湾路42号07栋1单元","location":"113.825652,22.142155","tel":"18933214876","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.8","cost":[]},"photos":[{"title":"休闲室","url":"https://store.is.autonavi.com/showpic/88b21e497b2a075e331a045c4564e067"}],"keytag":"民宿"},
    {"id":"B0I1JY8WL7","name":"里苑·中桂岛度假酒店","type":"住宿服务;宾馆酒店;宾馆酒店","typecode":"100100","biz_type":"hotel","address":"桂山岛爱民路16号","location":"113.826114,22.137778","tel":"19229664026;19276620050","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.6","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/9f4e279be71851a3a4b1d382958be7df"}],"keytag":"度假酒店"},
    {"id":"B0H35X876O","name":"珠海少女小渔民宿(桂山岛店)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山岛桂山村爱民路7号","location":"113.824362,22.137938","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.2","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/61b1848ab1e143c4cb916e1dd3d18417"}],"keytag":"经济型"},
    {"id":"B0I6THMADR","name":"里苑·桂汐湾畔精品海景民宿(珠海桂山岛店)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇永平巷3号","location":"113.825543,22.137883","tel":"17707567590","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.6","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/79f9367fdab9dcedbbac054de470c798"}],"keytag":"舒适型"},
    {"id":"B0L129VEHB","name":"珠海潮信客栈(桂山岛风景区店)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇桂海三路2号","location":"113.824325,22.135975","tel":"13536513369","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.7","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/fd8878d563b9f4b7c71c4e2e844a37f1"}],"keytag":"经济型"},
    {"id":"B0FFFSFWWC","name":"珠海桂山金悦旅店","type":"住宿服务;宾馆酒店;宾馆酒店","typecode":"100100","biz_type":"hotel","address":"桂山镇","location":"113.823560,22.136063","tel":"0756-8851628","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.2","cost":[]},"photos":[{"title":"客房","url":"https://store.is.autonavi.com/showpic/fa7aca4d0f7371f899e921c89b62a914"}],"keytag":"经济型"},
    {"id":"B0FFIQBCBW","name":"珠海桂山道禾璞树海岛花园民宿","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山岛桂山镇新兴巷1号","location":"113.824908,22.138687","tel":"18023073835","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.5","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/870ed6ca49b23f167b9f496276ec6778"}],"keytag":"经济型"},
    {"id":"B0FFG6Q4DP","name":"珠海桂山岛1号客栈","type":"住宿服务;旅馆招待所;旅馆招待所","typecode":"100200","biz_type":"hotel","address":"桂山岛桂山村平安路2号","location":"113.824976,22.137571","tel":"0756-3822923;15919225240","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.5","cost":[]},"photos":[{"title":"酒店外观","url":"https://store.is.autonavi.com/showpic/1da9d311ef503f30523bb4fe70792af3"}],"keytag":"经济型"},
    {"id":"B0G3N6NJEP","name":"SEAWIND微枫海景民宿","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山岛平安路5号","location":"113.825326,22.138046","tel":"18125076003","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.5","cost":[]},"photos":[{"title":"客房","url":"https://store.is.autonavi.com/showpic/cb70e3e9c132a9a9874e0ce203b7ce5c"}],"keytag":"民宿"},
    {"id":"B0FFL5O5XZ","name":"珠海半山石筑民宿(桂山岛店)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇桂山村爱民路12号","location":"113.824937,22.137425","tel":"13360612509","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.7","cost":[]},"photos":[{"title":"酒店外观","url":"https://store.is.autonavi.com/showpic/416c6ba4a368ad7505c13f61c8798949"}],"keytag":"舒适型"},
    {"id":"B0FFH53QEB","name":"珠海海景驿站(桂山岛店)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇交通大厦3楼","location":"113.823419,22.135458","tel":"13527209839","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.7","cost":[]},"photos":[{"title":"其他","url":"https://store.is.autonavi.com/showpic/5998a37ec176011748248f2fbfaa0855"}],"keytag":"经济型"},
    {"id":"B0FFIL64FJ","name":"珠海桂山岛蓝色海岸民宿","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山岛安海一巷1-6号","location":"113.826842,22.134911","tel":"0756-8855648;17707565326","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.7","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/b609ee57951ac54eabbbcd7a20e16044"}],"keytag":"舒适型"},
    {"id":"B0I06ARC1K","name":"览潮花间舍海景民宿(珠海桂山岛)","type":"住宿服务;旅馆招待所;旅馆招待所","typecode":"100200","biz_type":"hotel","address":"桂山镇吉祥巷1号","location":"113.824531,22.138563","tel":"13676047261","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.3","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/eaf78f07da0d150b640d5fee8b442cfc"}],"keytag":"民宿"},
    {"id":"B0G259XBS5","name":"珠海桂山岛桂语香山酒店","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇桂海东巷1号","location":"113.824408,22.135661","tel":"0756-2288630;13928000050","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.5","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/047cf959ca61b18a9c0aa5f9ae48c9de"}],"keytag":"度假酒店"},
    {"id":"B0LATC6VXD","name":"珠海市桂山岛海云民宿","type":"住宿服务;旅馆招待所;旅馆招待所","typecode":"100200","biz_type":"hotel","address":"天祥巷2-3号二楼","location":"113.824675,22.138044","tel":"13825665344;15913284001","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.8","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/fcc511c9b98b5ea76a8d39cea06e2a90"}],"keytag":"民宿"},
    {"id":"B0LAFHRQSG","name":"桂山熹居","type":"住宿服务;旅馆招待所;旅馆招待所","typecode":"100200","biz_type":"hotel","address":"桂山村新发巷6号","location":"113.825210,22.139269","tel":"19575668667","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.6","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/f68314906c8a0f8e45b6f7e7694c6718"}],"keytag":"民宿"},
    {"id":"B0FFKV2H2Z","name":"珠海阅海阁民宿(2号店)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇桂山岛天祥巷四号","location":"113.824632,22.137759","tel":"13927762816","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.7","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/33b0856bcd2d90b3d54480ea9aa24e6d"}],"keytag":"舒适型"},
    {"id":"B0FFKYJGMP","name":"珠海桂山岛小海豚民宿","type":"住宿服务;旅馆招待所;旅馆招待所","typecode":"100200","biz_type":"hotel","address":"桂山镇桂和路24号","location":"113.825197,22.137256","tel":"","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.8","cost":[]},"photos":[{"title":"客房","url":"https://store.is.autonavi.com/showpic/4650eea110587c1f36c4da732ba8ffa0"}],"keytag":"客栈"},
    {"id":"B0KKD71SDJ","name":"览潮居·雅舍(桂山岛店)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇天祥巷6号","location":"113.823961,22.138869","tel":"13676047261","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.8","cost":[]},"photos":[{"title":"客房","url":"https://store.is.autonavi.com/showpic/9f38e0593ec4fb568e04c01bc62cac58"}],"keytag":"住宿服务"},
]

# Query 4-5 (民宿/码头) already covered above. Add new unique ones:
query4_extra = [
    {"id":"B0FFLJWNBW","name":"珠海SEA·WIND海枫海景民宿","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山村天祥巷11号","location":"113.824653,22.139330","tel":"15363958448","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.7","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/f839d100fb1c19a5d257f7e78954cd5e"}],"keytag":"民宿"},
    {"id":"B0HDKNDII5","name":"珠海桂山岛赶海屋民宿(桂山村店)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇桂山村永安巷2号","location":"113.824760,22.137808","tel":"13580586632","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.8","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/cdc21c7101834238febebe550170bfdb"}],"keytag":"客栈"},
    {"id":"B0J2NAB7GR","name":"清枫民宿(桂山岛店)","type":"住宿服务;旅馆招待所;旅馆招待所","typecode":"100200","biz_type":"hotel","address":"桂山岛桂山镇桂和路4号","location":"113.824713,22.137542","tel":"18125068813","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.8","cost":[]},"photos":[{"title":"酒店外观","url":"https://store.is.autonavi.com/showpic/60cabc025eab7934124789d1b93059f9"}],"keytag":"客栈"},
    {"id":"B0KA3APS2O","name":"半山诗意民宿(桂山镇)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇桂海中巷15号","location":"113.824959,22.136555","tel":"15992693996","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.8","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/1e6f73580458395e85ca4d75082d8e7e"}],"keytag":"民宿"},
    {"id":"B0K24GCHGV","name":"雅石缘民宿(桂山岛店)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇桂山村新建巷10号","location":"113.825450,22.138381","tel":"13726278559","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.9","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/75ad4dc40f62595b950ec8e4b3b068eb"}],"keytag":"民宿"},
    {"id":"B0K06S9X7H","name":"悦隐·山海雅筑海景民宿(珠海桂山岛店)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇桂山村爱民路21号","location":"113.826228,22.137318","tel":"18902874560","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.7","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/080b29a077eff71932f341cf9e677c1c"}],"keytag":"民宿"},
    {"id":"B0KRZ1FJDX","name":"珠海桂山岛半缘居","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇新建巷09号","location":"113.825381,22.138380","tel":"13660018018;18902874832","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.7","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/4c52e93b295908cd45e17ef7f4ed4562"}],"keytag":"民宿"},
    {"id":"B0L6F9I3V9","name":"桂山岛一方小院","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇新发巷1号","location":"113.824796,22.138623","tel":"18666144234","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.9","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/589c26392e2efa95411428a8cf199e93"}],"keytag":"民宿"},
]

# Query 5: 码头 - unique POIs
query5_pois = [
    {"id":"B0FFFTO1D8","name":"桂山码头","type":"交通设施服务;港口码头;货运港口码头","typecode":"150304","biz_type":"","address":"桂山镇桂海三路2号","location":"113.821112,22.134633","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[{"title":[],"url":"https://aos-comment.amap.com/B0FFFTO1D8/comment/40fde643ed92d34f74ed19473b293a5f_2048_2048_80.jpg"}],"keytag":"港口码头"},
    {"id":"BV09313932","name":"珠海桂山岛(轮渡站)","type":"交通设施服务;轮渡站;轮渡站","typecode":"151200","biz_type":"","address":"深圳机场码头-桂山岛;深圳蛇口-桂山岛","location":"113.821002,22.134602","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/30c5c14f6f2b40600000000739276232?type=pic"}],"keytag":"轮渡"},
    {"id":"B0L62MDAQW","name":"桂山岛客运站","type":"交通设施服务;港口码头;客运港","typecode":"150301","biz_type":"","address":"","location":"113.821084,22.134616","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[{"title":[],"url":"https://aos-comment.amap.com/B0L62MDAQW/comment/content_media_external_file_1812786_ss__1751433661199_34682699.jpg"}],"keytag":"港口码头"},
    {"id":"B0LAS50Q7Y","name":"众归休闲渔业码头","type":"交通设施服务;交通服务相关;交通服务相关","typecode":"150000","biz_type":"","address":"桂山岛桂山大道海鲜街3号","location":"113.823039,22.138017","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[{"title":[],"url":"http://store.is.autonavi.com/showpic/1c04bd4bc7bc2476bf2cfa90da92d63f"}],"keytag":"港口码头"},
    {"id":"B0IBH7IP1Q","name":"中国珠海万山港海事处","type":"政府机构及社会团体;政府机关;政府机关相关","typecode":"130100","biz_type":"","address":"桂山镇桂山岛商业一路11号","location":"113.823064,22.134702","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/855442c0b1517e91827267b8a78c4b36"}],"keytag":"政府机关"},
    {"id":"B0FFF5QJY6","name":"珠海桂山岛听涛居客栈","type":"住宿服务;宾馆酒店;宾馆酒店","typecode":"100100","biz_type":"hotel","address":"桂山镇桂山岛桂海二路21号(桂山岛码头)","location":"113.824201,22.136659","tel":"0756-8851399;0756-8851699;15363989369","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.4","cost":[]},"photos":[{"title":"酒店外观","url":"https://store.is.autonavi.com/showpic/22b4eb012c9297392740a69338548521"}],"keytag":"经济型"},
    {"id":"B0LR5OCH8K","name":"桂山岛胶己人休闲渔家乐","type":"体育休闲服务;休闲场所;休闲场所","typecode":"080500","biz_type":"","address":"桂山镇万山边检专用码头北方向183米","location":"113.823375,22.142375","tel":"15015938538","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.0","cost":[]},"photos":[{"title":"酒店外观","url":"https://store.is.autonavi.com/showpic/86e988d9660b6ead55275f88d6eff095"}],"keytag":"农家乐"},
    {"id":"B0L62MMI6T","name":"桂山岛客运站售票处","type":"生活服务;售票处;售票处","typecode":"070300","biz_type":"","address":"万山海关西侧90米","location":"113.821119,22.134616","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[],"keytag":"售票"},
]

# Query 6: 沙滩 - unique new POIs
query6_extra = [
    {"id":"B0JGHBP0GG","name":"九天海岸水上运动中心(桂山岛风景区一湾店)","type":"体育休闲服务;休闲场所;水上活动中心","typecode":"080505","biz_type":"","address":"桂山岛一号堤一湾沙滩旁","location":"113.818897,22.133404","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.7","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/5a2ca5bc5fdd69515c6e691915056679"}],"keytag":"水上活动中心"},
    {"id":"B0FFF6WILG","name":"珠海海星度假酒店","type":"住宿服务;宾馆酒店;四星级宾馆","typecode":"100103","biz_type":"hotel","address":"桂山镇桂山岛桂山一路","location":"113.820226,22.133285","tel":"0756-8851138","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.3","cost":[]},"photos":[{"title":"酒店外观","url":"https://store.is.autonavi.com/showpic/5e91dba4c83c24d35f221d4ebec4d476"}],"keytag":"舒适型"},
    {"id":"B0FFFV3R8M","name":"珠海桂山岛家庭休闲度假公寓","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山岛海湾路42号追月山庄","location":"113.823383,22.138376","tel":"13016309233","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.0","cost":[]},"photos":[{"title":"客房","url":"https://store.is.autonavi.com/showpic/dd948e42ef9892560c440999ea48bda8"}],"keytag":"经济型"},
    {"id":"B0J1GS6L6R","name":"珠海桂山岛智选假日酒店","type":"住宿服务;宾馆酒店;宾馆酒店","typecode":"100100","biz_type":"hotel","address":"桂山镇桂山大道32号","location":"113.822910,22.135100","tel":"0756-3888188","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.7","cost":[]},"photos":[{"title":"酒店外观","url":"https://store.is.autonavi.com/showpic/d49595a2a0055564cb905d2c104b5b2e"}],"keytag":"高档型"},
    {"id":"B0G0XSXUQO","name":"桂山岛尚岛小居民宿","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂和路2号尚岛小居民宿","location":"113.824424,22.137426","tel":"","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.9","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/d1d943f74d4613764b742710d1c27da9"}],"keytag":"民宿"},
    {"id":"B0JAPG5CWS","name":"桂山岛心语民宿","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山岛风景区(西北角)","location":"113.824025,22.148375","tel":"","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.2","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/fba0b51df68e42010e70ae071e1f742f"}],"keytag":"民宿"},
    {"id":"B0KGDHRHP8","name":"珠海渔家·海景民宿(桂山岛店)","type":"住宿服务;旅馆招待所;旅馆招待所","typecode":"100200","biz_type":"hotel","address":"桂山镇桂山大道57号","location":"113.823394,22.136625","tel":"13168894446","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.4","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/776999babc405df042f3ba6840d035bd"}],"keytag":"民宿"},
    {"id":"B0J6YU5O2Z","name":"桂山岛2127贰楼民宿","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇永康巷6号2层","location":"113.825359,22.138176","tel":"13702326197","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.8","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/b41c94483425dd8dc8c38bf1b67d55ee"}],"keytag":"民宿"},
    {"id":"B0I69N4KBQ","name":"闲云居精品民宿(珠海桂山岛店)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇桂山大道48号交通大厦二层","location":"113.823197,22.135429","tel":"13128563666;13823087256","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.4","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/babbc28459b4099ec04958cecbef5a23"}],"keytag":"舒适型"},
]

# Query 8: 卫生
query8_pois = [
    {"id":"B0FFL1YQDT","name":"珠海市桂山镇中心卫生院","type":"医疗保健服务;医疗保健服务场所;医疗保健服务场所","typecode":"090000","biz_type":"","address":"桂山镇桂海三路51号","location":"113.823788,22.134493","tel":"0756-8851204","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[{"title":[],"url":"http://store.is.autonavi.com/showpic/84a5db2669537d2a6a99e9c8d01f2e16"}],"keytag":"卫生院"},
]

# Query 9: 商店
query9_pois = [
    {"id":"B0K0HDNM3D","name":"7-ELEVEn(桂山岛风景区店)","type":"购物服务;便民商店/便利店;便民商店/便利店","typecode":"060200","biz_type":"","address":"桂山派出所东南侧","location":"113.824009,22.136017","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.4","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/6aad422886452b68c72895c381fd2f4d"}],"keytag":"便利店"},
    {"id":"B0J1DYZ3FN","name":"日升商店(珠海农商银行桂山支行店)","type":"购物服务;便民商店/便利店;便民商店/便利店","typecode":"060200","biz_type":"","address":"桂山派出所西北侧50米","location":"113.823389,22.136569","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.3","cost":[]},"photos":[],"keytag":"日杂店"},
    {"id":"B0KR59YULS","name":"肥仔商行","type":"购物服务;便民商店/便利店;便民商店/便利店","typecode":"060200","biz_type":"","address":"桂山镇交通大厦121号地下","location":"113.823187,22.135164","tel":"18923364838","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.2","cost":[]},"photos":[],"keytag":"便利店"},
    {"id":"B0FFKJNLLN","name":"李记百货商场","type":"购物服务;便民商店/便利店;便民商店/便利店","typecode":"060200","biz_type":"","address":"桂山派出所西南侧70米","location":"113.823375,22.135575","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.4","cost":[]},"photos":[],"keytag":"日杂店"},
    {"id":"B0JGHKPUGC","name":"赖记百货商行","type":"购物服务;便民商店/便利店;便民商店/便利店","typecode":"060200","biz_type":"","address":"桂山派出所西南侧50米","location":"113.823382,22.135770","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.9","cost":[]},"photos":[],"keytag":"日杂店"},
    {"id":"B0L0MN7H9V","name":"裕华商店(桂山岛风景区店)","type":"购物服务;便民商店/便利店;便民商店/便利店","typecode":"060200","biz_type":"","address":"桂山派出所西南侧110米","location":"113.823265,22.135220","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"2.3","cost":[]},"photos":[],"keytag":"日杂店"},
    {"id":"B0H2A77032","name":"合兴商店","type":"购物服务;便民商店/便利店;便民商店/便利店","typecode":"060200","biz_type":"","address":"一环路60号桂山市场1楼","location":"113.823577,22.134758","tel":"0756-8851002","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.1","cost":[]},"photos":[],"keytag":"日杂店"},
    {"id":"B0FFHHCGAB","name":"肥妹商店","type":"购物服务;便民商店/便利店;便民商店/便利店","typecode":"060200","biz_type":"","address":"商业一街13正北方向80米","location":"113.823154,22.135144","tel":"13527243066","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.3","cost":[]},"photos":[],"keytag":"日杂店"},
]

# Query 11: 海鲜 - unique new POIs
query11_extra = [
    {"id":"B0HG71KIQC","name":"屿景湾海鲜酒家","type":"餐饮服务;中餐厅;广东菜(粤菜)","typecode":"050103","biz_type":"diner","address":"桂山镇桂山大道海鲜街2号","location":"113.823019,22.137815","tel":"13825671445","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.9","cost":"101.00"},"photos":[],"keytag":"粤菜"},
    {"id":"B0FFKK9NQX","name":"粤湘情","type":"餐饮服务;中餐厅;湖南菜(湘菜)","typecode":"050108","biz_type":"diner","address":"桂山镇桂海二路58号负一层A铺","location":"113.823406,22.136561","tel":"13570611447;13750005371","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.4","cost":"50.00"},"photos":[],"keytag":"湘菜"},
    {"id":"B0IAJSWEFP","name":"雄烽海鲜美食","type":"餐饮服务;中餐厅;海鲜酒楼","typecode":"050119","biz_type":"diner","address":"桂山镇桂湾一路桂海大楼102铺","location":"113.823434,22.135656","tel":"0756-8851668","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.1","cost":"98.00"},"photos":[],"keytag":"粤式茶点"},
    {"id":"B0GDRRBPQS","name":"桂海鲜美食","type":"餐饮服务;中餐厅;海鲜酒楼","typecode":"050119","biz_type":"diner","address":"桂山大道38号桂海鲜美食","location":"113.823925,22.135625","tel":"18666959515;18688177565","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.9","cost":"68.00"},"photos":[],"keytag":"中餐"},
    {"id":"B0JGRZ7ZJ3","name":"麦记美食店","type":"餐饮服务;中餐厅;中餐厅","typecode":"050100","biz_type":"diner","address":"中国珠海万山港海事处东北侧70米","location":"113.823321,22.135035","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.7","cost":"61.00"},"photos":[],"keytag":"中餐"},
    {"id":"B0L1UB29FV","name":"屿光漫调烧烤店(庄记海鲜餐厅分店)","type":"体育休闲服务;娱乐场所;酒吧","typecode":"080304","biz_type":"","address":"桂山派出所西南侧70米","location":"113.823127,22.135743","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.7","cost":"106.00"},"photos":[],"keytag":"烤串"},
    {"id":"B0MBKCR239","name":"智选海鲜酒家(珠海桂山岛智选假日酒店分店)","type":"餐饮服务;中餐厅;海鲜酒楼","typecode":"050119","biz_type":"diner","address":"桂山镇桂山大道32号302房","location":"113.822837,22.135307","tel":"0756-3888188","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.8","cost":[]},"photos":[],"keytag":"中餐"},
    {"id":"B0FFKZ2CC5","name":"桂山海鲜市场(农贸市场)","type":"购物服务;综合市场;农副产品市场|购物服务;综合市场;水产海鲜市场","typecode":"060703|060706","biz_type":"","address":"桂山镇一环路60号","location":"113.821845,22.135030","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.1","cost":[]},"photos":[],"keytag":"水产海鲜市场"},
]

# Query 12: 交通 - unique
query12_extra = [
    {"id":"B0K39A1X9J","name":"中国石油桂山岛加油站","type":"汽车服务;加油站;中国石油","typecode":"010102","biz_type":"","address":"桂山岛风景区(西北角)","location":"113.820223,22.153219","tel":"13417724527","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.0","cost":"7.00"},"photos":[],"keytag":"加油站"},
    {"id":"B0LBHHZDEG","name":"珠海中燃桂山水上加油站","type":"交通设施服务;交通服务相关;交通服务相关","typecode":"150000","biz_type":"","address":"","location":"113.820087,22.126385","tel":"13326681410","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.9","cost":[]},"photos":[],"keytag":"加油站"},
]

# Query 15: 庙 - already have 妈祖庙 (B0FFKWIUNE). Add island POI:
query15_extra = [
    {"id":"B02F402SJ3","name":"桂山岛","type":"地名地址信息;自然地名;岛屿","typecode":"190202","biz_type":"","address":"香洲区","location":"113.830122,22.141482","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[{"title":[],"url":"https://store.is.autonavi.com/showpic/1bb149a337887f67b180288517cc9f20"}],"keytag":"岛屿"},
]

# Query 16: 学校
query16_pois = [
    {"id":"B0FFL0H0PE","name":"桂山小学","type":"科教文化服务;学校;小学","typecode":"141203","biz_type":"","address":"珠海SEA·WIND海枫民宿北侧80米","location":"113.824491,22.140080","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[{"title":[],"url":"http://store.is.autonavi.com/showpic/3aa03f1aacdd8a9b63e45e82394a9354"}],"keytag":"小学"},
]

# Query 18: 公厕
query18_pois = [
    {"id":"B0FFLHZAQG","name":"公共厕所","type":"公共设施;公共厕所;公共厕所","typecode":"200300","biz_type":"","address":"桂山小学北侧220米","location":"113.823944,22.142124","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[],"keytag":"公厕"},
    {"id":"B0J1MZS9BW","name":"桂海村公共厕所","type":"公共设施;公共厕所;公共厕所","typecode":"200300","biz_type":"","address":"桂山镇桂海村","location":"113.825094,22.136592","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[],"keytag":"公厕"},
    {"id":"B0FFKUF99T","name":"公共厕所","type":"公共设施;公共厕所;公共厕所","typecode":"200300","biz_type":"","address":"桂山文化中心南侧80米","location":"113.823364,22.138205","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[],"keytag":"公厕"},
    {"id":"B0FFLHZ96C","name":"公共厕所","type":"公共设施;公共厕所;公共厕所","typecode":"200300","biz_type":"","address":"桂山镇中心卫生院南侧210米","location":"113.824019,22.132564","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[],"keytag":"公厕"},
    {"id":"B0FFKU2SLX","name":"公共厕所","type":"公共设施;公共厕所;公共厕所","typecode":"200300","biz_type":"","address":"桂山灯塔东北侧50米","location":"113.819128,22.133266","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[],"keytag":"公厕"},
]

# Query 19: 停车场 - unique
query19_extra = [
    {"id":"B0H1TRK7WS","name":"桂山岛风景区地面停车点","type":"交通设施服务;停车场;公共停车场","typecode":"150904","biz_type":"","address":"桂山岛风景区","location":"113.582500,22.289500","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[],"keytag":"地面停车场"},
    {"id":"B0FFJTBI4I","name":"珠海九龙塘客栈(桂山岛店)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇桂海一路3号","location":"113.823686,22.135341","tel":"15889861717","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.3","cost":[]},"photos":[],"keytag":"经济型"},
    {"id":"B0FFHQPJF1","name":"珠海裕和宾馆(桂山岛店)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇一环路51号","location":"113.823932,22.134829","tel":"0756-8851545;17875602744","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.6","cost":[]},"photos":[],"keytag":"经济型"},
]

# Query 20: 万山群岛 景点
query20_pois = [
    {"id":"B0LAV16Q74","name":"万山群岛联合指挥部旧址","type":"风景名胜;风景名胜;纪念馆|风景名胜;风景名胜;红色景区","typecode":"110204|110210","biz_type":"tour","address":"唐家湾镇山房路234号共乐园(西南角)","location":"113.588269,22.361962","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.1","cost":[]},"photos":[],"keytag":"文物古迹"},
    {"id":"B0KUFCY0HW","name":"解放万山群岛联合指挥部旧址","type":"风景名胜;风景名胜;红色景区","typecode":"110210","biz_type":"tour","address":"山房路与龙岗街交叉口东60米","location":"113.595107,22.358093","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.3","cost":[]},"photos":[],"keytag":"文物古迹"},
    {"id":"B0FFGD9V4P","name":"解放万山群岛烈士纪念碑","type":"风景名胜;风景名胜;红色景区","typecode":"110210","biz_type":"tour","address":"山房路与华夏路交叉口东260米","location":"113.588478,22.361683","tel":[],"pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.5","cost":[]},"photos":[{"title":[],"url":"http://store.is.autonavi.com/showpic/238c28c24ea9e872a2cdad91bce272d4"}],"keytag":"烈士陵园"},
    {"id":"B02F40PMC6","name":"望慈山房","type":"风景名胜;风景名胜相关;旅游景点","typecode":"110000","biz_type":"tour","address":"万山群岛联合指挥部旧址","location":"113.595108,22.358047","tel":"0756-3313966","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.7","cost":[]},"photos":[],"keytag":"景区"},
]

# Additional unique POIs from remaining searches
query_extra_hotels = [
    {"id":"B0MAGDYD0Y","name":"珠海桂山岛屿家民宿","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇天祥巷3号","location":"113.824625,22.137825","tel":"15913284819","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"5.0","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/54b1f9cbb26a621f685c4ce1965ff5c2"}],"keytag":"民宿"},
    {"id":"B0L6RZRWYF","name":"桂山岛逸海居特色民宿","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"逸海居民宿广东省珠海市香洲区桂山镇桂山村平安路3号","location":"113.825283,22.137815","tel":"13417789483","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.9","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/52e700573c1f7d2624a4aac5664e465f"}],"keytag":"民宿"},
    {"id":"B0K6MSDZVK","name":"珠海桂山岛元本桂舍民宿","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇桂和路6号","location":"113.824577,22.136762","tel":"13719893450","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"4.0","cost":[]},"photos":[{"title":"Logo","url":"https://store.is.autonavi.com/showpic/3babdc4167be8fcd578b2d174e4454dd"}],"keytag":"住宿服务"},
    {"id":"B0LG9DT7E3","name":"淑芳斋海景民宿(桂山岛风景区店)","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇交通大厦(一环路)","location":"113.823325,22.135425","tel":"","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"","cost":[]},"photos":[],"keytag":"民宿"},
    {"id":"B0HRBZXNMN","name":"珠海桂山岛上岛民宿","type":"住宿服务;住宿服务相关;住宿服务相关","typecode":"100000","biz_type":"hotel","address":"桂山镇交通大厦二楼202室","location":"113.822971,22.135470","tel":"18933204550","pname":"广东省","cityname":"珠海市","adname":"香洲区","biz_ext":{"rating":"3.7","cost":[]},"photos":[],"keytag":"经济型"},
]

# ============================================================
# Now assemble all POIs with their search keywords
# ============================================================

# Assign search keywords to each batch
batches = [
    (query1_pois, "桂山岛 景点"),
    (query2_pois, "桂山岛 餐饮"),
    (query3_pois, "桂山岛 酒店"),
    (query4_extra, "桂山岛 民宿"),
    (query5_pois, "桂山岛 码头"),
    (query6_extra, "桂山岛 沙滩"),
    (query8_pois, "桂山岛 医院/卫生"),
    (query9_pois, "桂山岛 超市/商店"),
    (query11_extra, "桂山岛 海鲜"),
    (query12_extra, "桂山岛 交通"),
    (query15_extra, "桂山岛 寺庙/庙"),
    (query16_pois, "桂山岛 学校"),
    (query18_pois, "桂山岛 公厕"),
    (query19_extra, "桂山岛 停车场"),
    (query20_pois, "万山群岛 景点"),
    (query_extra_hotels, "桂山岛 酒店/民宿"),
]

for batch_pois, keyword in batches:
    for poi in batch_pois:
        add_poi(poi, keyword)

# ============================================================
# Top 10 POI details (from detail API queries)
# ============================================================
detail_pois = {
    "B0FFFQ7RVA": {
        "business_area": "桂山岛",
        "gridcode": "3313167610",
        "entr_location": "113.582158,22.289699",
        "timestamp": "2026-07-13 17:00:53",
        "adcode": "440402",
        "citycode": "0756",
        "postcode": "440000",
    },
    "B0FFGPYFGT": {
        "business_area": "桂山岛",
        "gridcode": "3313166502",
        "entr_location": "113.8240201360568,22.135519528564313",
        "timestamp": "2026-07-03 23:31:35",
        "adcode": "440402",
        "citycode": "0756",
        "postcode": "440000",
        "tags": "生菜,干煸鱼,清蒸鱼,辣炒花蛤,豉蒸排骨,海虹,招牌小炒王,蒜蓉粉丝蒸沙白,椒盐九吐,清蒸斑鱼,姜葱炒红蟹,大排档",
    },
    "B0K24GCHGV": {
        "business_area": "桂山岛",
        "gridcode": "3313166610",
        "entr_location": "113.825543,22.138337",
        "timestamp": "2026-07-12 01:02:08",
        "adcode": "440402",
        "citycode": "0756",
        "postcode": "440000",
    },
    "B0I1JY8WL7": {
        "business_area": "桂山岛",
        "gridcode": "3313166610",
        "entr_location": "113.826926,22.137482",
        "timestamp": "2026-07-12 01:01:00",
        "adcode": "440402",
        "citycode": "0756",
        "postcode": "440000",
    },
    "B0FFK80UCK": {
        "business_area": "",
        "gridcode": "3313165521",
        "entr_location": "",
        "timestamp": "2026-06-30 06:31:02",
        "adcode": "440402",
        "citycode": "0756",
        "postcode": "440000",
    },
    "B0FFGG0HB1": {
        "business_area": "",
        "gridcode": "3313165511",
        "entr_location": "",
        "timestamp": "2026-07-13 00:10:27",
        "adcode": "440402",
        "citycode": "0756",
        "postcode": "440000",
    },
    "B0L6F9I3V9": {
        "business_area": "桂山岛",
        "gridcode": "3313166512",
        "entr_location": "113.824491,22.138447",
        "timestamp": "2026-07-12 01:02:15",
        "adcode": "440402",
        "citycode": "0756",
        "postcode": "440000",
    },
    "B0K34RKZOX": {
        "business_area": "桂山岛",
        "gridcode": "3313167600",
        "entr_location": "113.825569,22.142447",
        "timestamp": "2026-07-13 02:47:25",
        "adcode": "440402",
        "citycode": "0756",
        "postcode": "440000",
    },
    "B0J1GS6L6R": {
        "business_area": "桂山岛",
        "gridcode": "3313166502",
        "entr_location": "113.822733,22.134903",
        "timestamp": "2026-07-12 00:59:36",
        "adcode": "440402",
        "citycode": "0756",
        "postcode": "440000",
    },
    "B0G0XSXUQO": {
        "business_area": "桂山岛",
        "gridcode": "3313166512",
        "entr_location": "113.824587,22.137569",
        "timestamp": "2026-07-12 00:58:35",
        "adcode": "440402",
        "citycode": "0756",
        "postcode": "440000",
    },
}

# Enrich POIs with detail data
for poi_id, details in detail_pois.items():
    if poi_id in all_pois:
        all_pois[poi_id]["business_area"] = details.get("business_area", "")
        all_pois[poi_id]["detail_fetched"] = True
        all_pois[poi_id]["gridcode"] = details.get("gridcode", "")
        all_pois[poi_id]["entr_location"] = details.get("entr_location", "")
        if details.get("tags"):
            all_pois[poi_id]["tags"] = details["tags"]

# ============================================================
# Count POIs per search query category
# ============================================================
category_counts = {}
for kw in search_queries:
    mapped = keyword_map.get(kw, kw)
    count = sum(1 for p in all_pois.values() if kw in p.get("search_keywords", []) or mapped in p.get("search_keywords", []))
    category_counts[kw] = count

# ============================================================
# Build final output
# ============================================================
pois_list = []
for poi_id, data in all_pois.items():
    # Clean up internal fields
    record = {k: v for k, v in data.items() if k != "search_keywords"}
    pois_list.append(record)

# Sort by rating (descending), then by name
pois_list.sort(key=lambda x: (
    -float(x["rating"]) if x["rating"] and x["rating"].replace(".", "").isdigit() else 0,
    x["name"]
))

output = {
    "metadata": {
        "collection_date": "2026-07-13",
        "total_pois": len(pois_list),
        "unique_pois": len(pois_list),
        "search_queries": search_queries,
        "city": "珠海",
        "citylimit": True,
        "detail_fetched_count": len(detail_pois),
        "detail_poi_ids": list(detail_pois.keys()),
        "category_counts": {
            "桂山岛 景点": 23,
            "桂山岛 餐饮": 15,
            "桂山岛 酒店": 85,
            "桂山岛 民宿": 57,
            "桂山岛 码头": 13,
            "桂山岛 沙滩": 33,
            "桂山岛 灯塔": 3,
            "桂山岛 医院/卫生": 2,
            "桂山岛 超市/商店": 13,
            "桂山岛 咖啡": 2,
            "桂山岛 海鲜": 15,
            "桂山岛 交通": 4,
            "桂山岛 公园": 4,
            "桂山岛 广场": 2,
            "桂山岛 寺庙/庙": 93,
            "桂山岛 学校": 1,
            "桂山岛 银行/ATM": 97,
            "桂山岛 公厕": 6,
            "桂山岛 停车场": 10,
            "万山群岛 景点": 4,
        },
        "note": "API返回的count为搜索命中总数(含岛外结果),实际采集为去重后的桂山岛相关POI"
    },
    "pois": pois_list,
}

# ============================================================
# Save to file
# ============================================================
output_dir = r"E:\珠海桂山岛案例\数据采集\raw"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "amap_poi_guishan.json")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"[OK] POI data saved to: {output_path}")
print(f"[OK] Total unique POIs: {len(pois_list)}")
print(f"[OK] Detail queries completed for top 10 POIs")
print()
print("=" * 60)
print("POI Category Summary (unique POIs collected on Guishan Island)")
print("=" * 60)

# Count by category
cat_summary = {}
for p in pois_list:
    cat = p.get("category", "其他")
    cat_summary[cat] = cat_summary.get(cat, 0) + 1

for cat, count in sorted(cat_summary.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {count}")

print(f"\n  Total: {len(pois_list)}")
print()
print("Top 10 rated POIs (with detail data):")
print("-" * 60)
for i, p in enumerate(pois_list[:10], 1):
    rating = p.get("rating", "N/A")
    print(f"  {i}. {p['name']} (rating: {rating}, category: {p.get('category', '')})")
    print(f"     POI ID: {p['poi_id']}, Address: {p.get('address', 'N/A')}")
