# -*- coding: utf-8 -*-
"""
测试百度街景是否覆盖桂山岛POI
"""
import json, sys, time, random, math, requests
sys.stdout.reconfigure(encoding='utf-8')

# ── 坐标转换 (from full_pipeline.py) ──
PI = 3.14159265358979324
A = 6378245.0
EE = 0.00669342162296594323
x_pi = PI * 3000.0 / 180.0
LLBAND = [75, 60, 45, 30, 15, 0]
LL2MC = [
    [-0.0015702102444, 111320.7020616939, 1704480524535203, -10338987376042340,
     26112667856603880, -35149669176653700, 26595700718403920, -10725012454188240,
     1800819912950474, 82.5],
    [0.0008277824516172526, 111320.7020463578, 647795574.6671607, -4082003173.641316,
     10774905663.51142, -15171875531.51559, 12053065338.62167, -5124939663.577472,
     913311935.9512032, 67.5],
    [0.00337398766765, 111320.7020202162, 4481351.045890365, -23393751.19931662,
     79682215.47186455, -115964993.2797253, 97236711.15602145, -43661946.33752821,
     8477230.501135234, 52.5],
    [0.00220636496208, 111320.7020209128, 51751.86112841131, 3796837.749470245,
     992013.7397791013, -1221952.21711287, 1340652.697009075, -620943.6990984312,
     144416.9293806241, 37.5],
    [-0.0003441963504368392, 111320.7020576856, 278.2353980772752, 2485758.690035394,
     6070.750963243378, 54821.18345352118, 9540.606633304236, -2710.55326746645,
     1405.483844121726, 22.5],
    [-0.0003218135878613132, 111320.7020701615, 0.00369383431289, 823725.6402795718,
     0.46104986909093, 2351.343141331292, 1.58060784298199, 8.77738589078284,
     0.37238884252424, 7.45],
]

def _out_of_china(lng, lat):
    return lng < 72.004 or lng > 137.8347 or lat < 0.8293 or lat > 55.8271

def _transform_lat(lng, lat):
    ret = -100 + 2*lng + 3*lat + 0.2*lat*lat + 0.1*lng*lat + 0.2*math.sqrt(abs(lng))
    ret += (20*math.sin(6*lng*PI) + 20*math.sin(2*lng*PI)) * 2/3
    ret += (20*math.sin(lat*PI) + 40*math.sin(lat/3*PI)) * 2/3
    ret += (160*math.sin(lat/12*PI) + 320*math.sin(lat*PI/30)) * 2/3
    return ret

def _transform_lng(lng, lat):
    ret = 300 + lng + 2*lat + 0.1*lng*lng + 0.1*lng*lat + 0.1*math.sqrt(abs(lng))
    ret += (20*math.sin(6*lng*PI) + 20*math.sin(2*lng*PI)) * 2/3
    ret += (20*math.sin(lng*PI) + 40*math.sin(lng/3*PI)) * 2/3
    ret += (150*math.sin(lng/12*PI) + 300*math.sin(lng/30*PI)) * 2/3
    return ret

def gcj02_to_bd09(lng, lat):
    z = math.sqrt(lng*lng + lat*lat) + 0.00002*math.sin(lat*x_pi)
    theta = math.atan2(lat, lng) + 0.000003*math.cos(lng*x_pi)
    return z*math.cos(theta)+0.0065, z*math.sin(theta)+0.006

class _LLT:
    def __init__(self, x, y): self.x, self.y = x, y

def _getRange(c, b, t):
    if b is not None: c = max(c, b)
    if t is not None: c = min(c, t)
    return c

def _getLoop(c, b, t):
    while c > t: c -= t - b
    while c < b: c += t - b
    return c

def _convertor(cC, cD):
    T = cD[0] + cD[1]*abs(cC.x)
    cB = abs(cC.y)/cD[9]
    cE = cD[2]+cD[3]*cB+cD[4]*cB**2+cD[5]*cB**3+cD[6]*cB**4+cD[7]*cB**5+cD[8]*cB**6
    if cC.x < 0: T = -T
    if cC.y < 0: cE = -cE
    return [T, cE]

def _convertLL2MC(T):
    cD = None
    T.x = _getLoop(T.x, -180, 180)
    T.y = _getRange(T.y, -74, 74)
    cB = T
    for i in range(len(LLBAND)):
        if cB.y >= LLBAND[i]: cD = LL2MC[i]; break
    if cD is not None:
        for i in range(len(LLBAND)-1, -1, -1):
            if cB.y <= -LLBAND[i]: cD = LL2MC[i]; break
    return _convertor(T, cD)

def gcj02_to_bdmc(lng, lat):
    """GCJ-02 → BD-09 → BD墨卡托"""
    bd_lng, bd_lat = gcj02_to_bd09(lng, lat)
    mc = _convertLL2MC(_LLT(bd_lng, bd_lat))
    return mc[0], mc[1]

# ── 百度CDN ──
UA_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
]

def _headers():
    return {"User-Agent": random.choice(UA_LIST), "Referer": "https://map.baidu.com/", "Accept": "*/*"}

def bd_sid(x, y):
    params = {"udt": time.strftime("%Y%m%d"), "action": 0, "x": x, "y": y,
              "l": 18.367179030452565, "mode": "day", "t": int(time.time()*1000),
              "fn": "jsonp1", "qt": "qsdata"}
    try:
        r = requests.get("https://mapsv0.bdimg.com/?", params=params, headers=_headers(), timeout=(5,10))
        raw = r.content
        s, e = raw.find(b"(")+1, raw.rfind(b")")
        if s > 0 and e > s:
            j = json.loads(raw[s:e].decode("utf-8", errors="replace"))
            if j.get("result",{}).get("error") == 0:
                return j["content"]["id"]
    except Exception as ex:
        print(f"  SID error: {ex}")
    return None

def sid_timeline(sid):
    params = {"sid": sid, "pc": 1, "udt": time.strftime("%Y%m%d"),
              "fn": "jsonp.p3991630", "qt": "sdata"}
    try:
        r = requests.get("https://mapsv0.bdimg.com/?", params=params, headers=_headers(), timeout=(3,7))
        raw = r.content
        s, e = raw.find(b"(")+1, raw.rfind(b")")
        if s > 0 and e > s:
            j = json.loads(raw[s:e].decode("utf-8", errors="replace"))
            content = j.get("content", [])
            if content and isinstance(content, list):
                return float(content[0].get("MoveDir",0)), content[0].get("TimeLine",[])
    except Exception as ex:
        print(f"  Timeline error: {ex}")
    return 0.0, []

def download_img(timeid, heading, direction):
    params = {"fovy": 90, "quality": 100, "panoid": timeid,
              "heading": (heading + direction) % 360,
              "width": 512, "height": 512, "qt": "pr3d"}
    r = requests.get("https://mapsv0.bdimg.com/?", params=params, headers=_headers(), timeout=(3,7))
    if r.content[:2] == b"\xff\xd8":
        return r.content
    return None

# ── 测试桂山岛POI ──
with open(r'E:\珠海桂山岛案例\data\raw\amap_poi_guishan.json', 'r', encoding='utf-8') as f:
    pois = json.load(f)['pois']

# 选3个有代表性的POI测试
test_pois = [
    next(p for p in pois if p['name'] == '桂山码头'),           # 码头(入口)
    next(p for p in pois if p['name'] == '珠海桂山岛智选假日酒店'),  # 中心区酒店
    next(p for p in pois if p['name'] == '桂山岛风景区'),        # 景区
]

for p in test_pois:
    name = p['name']
    gcj_lng = p['location']['lng']
    gcj_lat = p['location']['lat']
    print(f"\n{'='*50}")
    print(f"POI: {name}")
    print(f"GCJ-02: {gcj_lng}, {gcj_lat}")

    # GCJ-02 → BD-09 → BD Mercator
    bd_x, bd_y = gcj02_to_bdmc(gcj_lng, gcj_lat)
    print(f"BD Mercator: {bd_x:.2f}, {bd_y:.2f}")

    # 获取SID
    sid = bd_sid(bd_x, bd_y)
    if not sid:
        print("结果: 无街景覆盖 (no SID)")
        continue

    print(f"SID: {sid}")

    # 获取时间轴
    direction, timeline = sid_timeline(sid)
    if not timeline:
        print("结果: 有SID但无时间轴 (no timeline)")
        continue

    print(f"拍摄方向: {direction}°")
    print(f"可用年份: {len(timeline)}个")
    for item in timeline:
        yr = item.get("Year", "?")
        tid = item.get("ID", "")[:20]
        print(f"  {yr}: {tid}...")

    # 尝试下载最新一年的4方向图片
    latest = timeline[0]
    timeid = latest.get("ID")
    year = latest.get("Year", "unknown")
    print(f"\n下载 {year} 年图片...")

    HEADINGS = {0: "N", 90: "E", 180: "S", 270: "W"}
    for head in [0, 90, 180, 270]:
        img = download_img(timeid, head, direction)
        if img:
            print(f"  {HEADINGS[head]}: {len(img)} bytes OK")
        else:
            print(f"  {HEADINGS[head]}: 下载失败")

print("\n测试完成")
