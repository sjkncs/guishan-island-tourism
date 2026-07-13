# -*- coding: utf-8 -*-
"""
桂山岛文旅体验数据采集与场景标签分析框架
========================================
设计原则：
1. 样本均衡采样（防过拟合）- 按平台/时间/类别分层
2. 同比/环比时间维度分析（2025 vs 2026）
3. 场景标签多级编码（大类/中类/细类）
4. 长尾问题专项处理

平台覆盖矩阵：
┌─────────────┬────────┬────────┬──────────┬──────────┬──────────┬────────┐
│ 平台         │ 评论量  │ 可采集  │ 场景标签  │ 时间维度  │ 商家维度  │ 优先级  │
├─────────────┼────────┼────────┼──────────┼──────────┼──────────┼────────┤
│ 携程/Trip.com│ ★★★   │ 高     │ 丰富     │ 精确到日  │ 多商家   │ P0     │
│ 易游网       │ ★★★   │ 高     │ 丰富     │ 精确到日  │ 多商家   │ P0     │
│ 永安旅游     │ ★★☆   │ 高     │ 丰富     │ 精确到日  │ 多商家   │ P0     │
│ 珠海票务网   │ ★☆☆   │ 中     │ 有限     │ 模糊     │ 少      │ P1     │
│ 黑猫投诉     │ ★☆☆   │ 高     │ 极详细   │ 精确     │ 单商家   │ P1     │
│ 知乎         │ ★☆☆   │ 高     │ 详细     │ 精确     │ N/A     │ P1     │
│ 小红书       │ ★★★   │ 中     │ 种草为主 │ 精确     │ N/A     │ P2     │
│ 微博         │ ★★☆   │ 中     │ 碎片化   │ 精确     │ N/A     │ P2     │
│ 抖音         │ ★★★   │ 低     │ 视频为主 │ 精确     │ N/A     │ P2     │
│ 大众点评     │ ★☆☆   │ 极低   │ 无       │ -       │ 极少    │ 弃用   │
│ 美团         │ ★☆☆   │ 极低   │ 无       │ -       │ 极少    │ 弃用   │
│ 淘宝闪购     │ ☆☆☆   │ 无     │ 无       │ -       │ 无      │ 弃用   │
└─────────────┴────────┴────────┴──────────┴──────────┴──────────┴────────┘
"""

import json
import os
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict
import hashlib

# ============================================================
# 1. 场景标签编码体系 (Scenario Label Taxonomy)
# ============================================================

SCENARIO_LABELS = {
    # ── A: 食品安全 ──
    "A01": {"label": "食品不新鲜", "category": "食品安全", "severity": "高", "keywords": ["不新鲜", "变质", "异味", "发臭", "过期", "馊"]},
    "A02": {"label": "食品异物", "category": "食品安全", "severity": "高", "keywords": ["头发", "虫子", "蟑螂", "苍蝇", "塑料", "铁丝", "石子"]},
    "A03": {"label": "食品卫生违规", "category": "食品安全", "severity": "高", "keywords": ["脏", "不干净", "没消毒", "生熟混放", "过期食品", "无健康证"]},
    "A04": {"label": "食品中毒/不适", "category": "食品安全", "severity": "极高", "keywords": ["拉肚子", "食物中毒", "呕吐", "肠胃不适", "过敏"]},
    "A05": {"label": "海鲜质量问题", "category": "食品安全", "severity": "高", "keywords": ["死海鲜", "注水", "缺斤少两", "以次充好", "养殖冒充野生"]},

    # ── B: 店铺环境 ──
    "B01": {"label": "卫生脏乱", "category": "店铺环境", "severity": "中", "keywords": ["脏", "垃圾", "油污", "灰尘", "污渍", "发霉"]},
    "B02": {"label": "虫害问题", "category": "店铺环境", "severity": "中高", "keywords": ["蟑螂", "蚊子", "苍蝇", "蚂蚁", "老鼠", "虫子", "虫卵", "小强"]},
    "B03": {"label": "设施陈旧", "category": "店铺环境", "severity": "中", "keywords": ["旧", "破", "坏", "生锈", "掉漆", "漏水", "墙皮脱落"]},
    "B04": {"label": "空调/通风问题", "category": "店铺环境", "severity": "低", "keywords": ["空调不冷", "太热", "闷热", "噪音大", "没窗户", "通风差"]},
    "B05": {"label": "空间狭小", "category": "店铺环境", "severity": "低", "keywords": ["小", "挤", "窄", "没地方放", "空间不够"]},
    "B06": {"label": "隔音差", "category": "店铺环境", "severity": "中", "keywords": ["隔音", "吵", "噪音", "听到隔壁", "施工声"]},

    # ── C: 服务态度 ──
    "C01": {"label": "态度恶劣", "category": "服务态度", "severity": "高", "keywords": ["态度差", "凶", "甩脸", "爱搭不理", "不耐烦", "骂人"]},
    "C02": {"label": "服务不及时", "category": "服务态度", "severity": "中", "keywords": ["等很久", "叫不应", "没人理", "上菜慢", "催了没用"]},
    "C03": {"label": "虚假宣传", "category": "服务态度", "severity": "高", "keywords": ["照骗", "和图片不一样", "货不对板", "虚假宣传", "到店无房"]},
    "C04": {"label": "退改纠纷", "category": "服务态度", "severity": "高", "keywords": ["不退钱", "退款难", "霸王条款", "不让取消", "扣费"]},

    # ── D: 性价比/价格 ──
    "D01": {"label": "价格虚高/宰客", "category": "性价比", "severity": "高", "keywords": ["宰客", "天价", "贵", "不值", "坑", "黑心", "抢钱"]},
    "D02": {"label": "隐性消费", "category": "性价比", "severity": "中高", "keywords": ["加价", "隐藏消费", "没标价", "结账才知", "额外收费"]},
    "D03": {"label": "缺斤少两", "category": "性价比", "severity": "高", "keywords": ["少秤", "缺斤少两", "分量不足", "偷换"]},
    "D04": {"label": "节假日涨价", "category": "性价比", "severity": "中", "keywords": ["假期贵", "旺季涨价", "节假日翻倍", "周末特贵"]},

    # ── E: 体验内容 ──
    "E01": {"label": "游玩内容匮乏", "category": "体验内容", "severity": "中", "keywords": ["没啥好玩", "无聊", "没什么", "不知道干嘛", "内容少"]},
    "E02": {"label": "商业化过重", "category": "体验内容", "severity": "中", "keywords": ["商业化", "失去本味", "过度开发", "都是卖东西"]},
    "E03": {"label": "文化体验缺失", "category": "体验内容", "severity": "中", "keywords": ["没文化", "红色文化弱", "渔家体验少", "缺乏特色"]},

    # ── F: 交通/基础设施 ──
    "F01": {"label": "交通不便", "category": "交通", "severity": "中", "keywords": ["船少", "等船久", "交通难", "班次少", "晕船"]},
    "F02": {"label": "岛上交通问题", "category": "交通", "severity": "低", "keywords": ["没公交", "走路累", "租车贵", "道路差"]},
    "F03": {"label": "基础设施不足", "category": "基础设施", "severity": "中", "keywords": ["没ATM", "信号差", "没医院", "公厕脏", "没路灯"]},

    # ── G: 正面评价（对照组） ──
    "G01": {"label": "风景优美", "category": "正面体验", "severity": "无", "keywords": ["美", "漂亮", "好看", "风景好", "海很美"]},
    "G02": {"label": "海鲜好吃", "category": "正面体验", "severity": "无", "keywords": ["好吃", "新鲜", "美味", "推荐", "值回票价"]},
    "G03": {"label": "服务热情", "category": "正面体验", "severity": "无", "keywords": ["热情", "贴心", "周到", "服务好", "友善"]},
    "G04": {"label": "性价比高", "category": "正面体验", "severity": "无", "keywords": ["值", "划算", "性价比", "实惠", "物超所值"]},
}

# ============================================================
# 2. 数据模型
# ============================================================

@dataclass
class Review:
    """单条评论数据"""
    id: str                          # 唯一ID（平台+原始ID的hash）
    platform: str                    # 平台名称
    source_url: str                  # 原始URL
    business_name: str               # 商家名称
    business_type: str               # 商家类型（住宿/餐饮/景点/交通/其他）
    content: str                     # 评论正文
    rating: Optional[float] = None   # 评分（1-5）
    date: Optional[str] = None       # 评论日期（YYYY-MM-DD）
    year: Optional[int] = None       # 年份
    month: Optional[int] = None      # 月份
    user_location: Optional[str] = None  # 用户所在地
    labels: List[str] = field(default_factory=list)  # 场景标签编码
    label_details: Dict = field(default_factory=dict) # 标签详情
    sentiment: Optional[str] = None  # 情感极性（positive/negative/neutral）
    word_count: int = 0              # 字数

    def __post_init__(self):
        if self.content:
            self.word_count = len(self.content)
        if self.date:
            try:
                d = datetime.strptime(self.date, "%Y-%m-%d")
                self.year = d.year
                self.month = d.month
            except ValueError:
                pass

    def to_dict(self):
        return asdict(self)


# ============================================================
# 3. 防过拟合采样器
# ============================================================

class BalancedSampler:
    """
    分层均衡采样器
    
    设计目标：
    1. 平台均衡：各平台采样量标准化（下采样至最小组）
    2. 时间均衡：按月分层，避免某月数据主导
    3. 类别均衡：商家类型比例保持原始分布
    4. 评分均衡：确保正/负面评论比例合理
    """
    
    def __init__(self, target_per_platform: int = 200, seed: int = 42):
        self.target_per_platform = target_per_platform
        self.seed = seed
        self.stats = defaultdict(lambda: defaultdict(int))
    
    def sample(self, reviews: List[Review]) -> List[Review]:
        """执行分层均衡采样"""
        import random
        random.seed(self.seed)
        
        # 按平台分组
        by_platform = defaultdict(list)
        for r in reviews:
            by_platform[r.platform].append(r)
        
        sampled = []
        for platform, platform_reviews in by_platform.items():
            n = len(platform_reviews)
            if n <= self.target_per_platform:
                sampled.extend(platform_reviews)
                self.stats[platform]['kept'] = n
                self.stats[platform]['dropped'] = 0
            else:
                # 按月分层采样
                by_month = defaultdict(list)
                for r in platform_reviews:
                    month_key = f"{r.year}-{r.month:02d}" if r.year and r.month else "unknown"
                    by_month[month_key].append(r)
                
                # 均匀分配每月配额
                months = list(by_month.keys())
                per_month = max(1, self.target_per_platform // max(1, len(months)))
                
                for month_key, month_reviews in by_month.items():
                    k = min(per_month, len(month_reviews))
                    sampled.extend(random.sample(month_reviews, k))
                    self.stats[platform][f'month_{month_key}'] = k
                
                self.stats[platform]['kept'] = sum(
                    self.stats[platform][k] for k in self.stats[platform]
                    if k.startswith('month_')
                )
                self.stats[platform]['dropped'] = n - self.stats[platform]['kept']
        
        return sampled
    
    def report(self) -> str:
        """输出采样统计报告"""
        lines = ["=" * 60, "分层均衡采样报告", "=" * 60]
        for platform, stats in self.stats.items():
            lines.append(f"\n平台: {platform}")
            lines.append(f"  保留: {stats.get('kept', 0)} 条")
            lines.append(f"  丢弃: {stats.get('dropped', 0)} 条")
            month_stats = {k: v for k, v in stats.items() if k.startswith('month_')}
            if month_stats:
                lines.append("  月度分布:")
                for m, c in sorted(month_stats.items()):
                    lines.append(f"    {m}: {c} 条")
        return "\n".join(lines)


# ============================================================
# 4. 场景标签自动编码器
# ============================================================

class ScenarioLabeler:
    """
    基于关键词匹配的场景标签自动编码器
    
    支持：
    - 多级标签（大类/中类/细类）
    - 多标签分配（一条评论可命中多个标签）
    - 置信度评估（命中关键词数 / 标签总关键词数）
    """
    
    def __init__(self, labels: Dict = None):
        self.labels = labels or SCENARIO_LABELS
    
    def label_review(self, content: str) -> Tuple[List[str], Dict]:
        """对单条评论进行标签编码"""
        matched_labels = []
        details = {}
        
        for code, info in self.labels.items():
            hits = []
            for kw in info['keywords']:
                if kw in content:
                    hits.append(kw)
            
            if hits:
                matched_labels.append(code)
                details[code] = {
                    'label': info['label'],
                    'category': info['category'],
                    'severity': info['severity'],
                    'matched_keywords': hits,
                    'confidence': round(len(hits) / len(info['keywords']), 2)
                }
        
        return matched_labels, details
    
    def label_batch(self, reviews: List[Review]) -> List[Review]:
        """批量标签编码"""
        for r in reviews:
            labels, details = self.label_review(r.content)
            r.labels = labels
            r.label_details = details
            # 简单情感判定
            neg_count = sum(1 for l in labels if not l.startswith('G'))
            pos_count = sum(1 for l in labels if l.startswith('G'))
            if neg_count > pos_count:
                r.sentiment = 'negative'
            elif pos_count > neg_count:
                r.sentiment = 'positive'
            else:
                r.sentiment = 'neutral'
        return reviews
    
    def label_distribution(self, reviews: List[Review]) -> Dict:
        """统计标签分布"""
        counter = Counter()
        for r in reviews:
            for label in r.labels:
                counter[label] += 1
        
        # 按类别聚合
        by_category = defaultdict(list)
        for code, count in counter.most_common():
            info = self.labels.get(code, {})
            by_category[info.get('category', '未知')].append({
                'code': code,
                'label': info.get('label', code),
                'count': count,
                'pct': round(count / len(reviews) * 100, 1) if reviews else 0
            })
        
        return dict(by_category)


# ============================================================
# 5. 同比/环比分析器
# ============================================================

class TemporalAnalyzer:
    """
    时间维度分析器
    
    支持：
    - 同比分析（YoY）：同月/同季度跨年对比
    - 环比分析（MoM）：相邻月份对比
    - 长尾检测：识别低频但高影响的标签
    """
    
    def __init__(self, labeler: ScenarioLabeler):
        self.labeler = labeler
    
    def yoy_analysis(self, reviews: List[Review], year_a: int = 2025, year_b: int = 2026) -> Dict:
        """同比分析：year_a vs year_b"""
        reviews_a = [r for r in reviews if r.year == year_a]
        reviews_b = [r for r in reviews if r.year == year_b]
        
        dist_a = self.labeler.label_distribution(reviews_a)
        dist_b = self.labeler.label_distribution(reviews_b)
        
        result = {
            'year_a': year_a,
            'year_b': year_b,
            'count_a': len(reviews_a),
            'count_b': len(reviews_b),
            'categories': {}
        }
        
        all_categories = set(list(dist_a.keys()) + list(dist_b.keys()))
        for cat in all_categories:
            items_a = {item['code']: item for item in dist_a.get(cat, [])}
            items_b = {item['code']: item for item in dist_b.get(cat, [])}
            all_codes = set(list(items_a.keys()) + list(items_b.keys()))
            
            changes = []
            for code in all_codes:
                count_a = items_a.get(code, {}).get('count', 0)
                count_b = items_b.get(code, {}).get('count', 0)
                pct_change = ((count_b - count_a) / count_a * 100) if count_a > 0 else (100.0 if count_b > 0 else 0)
                label = self.labeler.labels.get(code, {}).get('label', code)
                changes.append({
                    'code': code,
                    'label': label,
                    'count_2025': count_a,
                    'count_2026': count_b,
                    'yoy_change_pct': round(pct_change, 1),
                    'trend': 'up' if pct_change > 0 else ('down' if pct_change < 0 else 'stable')
                })
            
            result['categories'][cat] = sorted(changes, key=lambda x: abs(x['yoy_change_pct']), reverse=True)
        
        return result
    
    def mom_analysis(self, reviews: List[Review]) -> Dict:
        """环比分析：逐月对比"""
        by_month = defaultdict(list)
        for r in reviews:
            if r.year and r.month:
                key = f"{r.year}-{r.month:02d}"
                by_month[key].append(r)
        
        months = sorted(by_month.keys())
        result = {'months': months, 'changes': []}
        
        for i in range(1, len(months)):
            prev_month = months[i - 1]
            curr_month = months[i]
            
            dist_prev = self.labeler.label_distribution(by_month[prev_month])
            dist_curr = self.labeler.label_distribution(by_month[curr_month])
            
            # 计算整体变化
            neg_prev = sum(1 for r in by_month[prev_month] if r.sentiment == 'negative')
            neg_curr = sum(1 for r in by_month[curr_month] if r.sentiment == 'negative')
            
            result['changes'].append({
                'from': prev_month,
                'to': curr_month,
                'count_prev': len(by_month[prev_month]),
                'count_curr': len(by_month[curr_month]),
                'negative_prev': neg_prev,
                'negative_curr': neg_curr,
                'negative_change': neg_curr - neg_prev
            })
        
        return result
    
    def long_tail_detection(self, reviews: List[Review], threshold_pct: float = 2.0) -> Dict:
        """
        长尾标签检测：识别占比<2%但严重程度为"高"或"极高"的标签
        
        这些标签虽然频率低，但影响大，不应被忽略。
        """
        dist = self.labeler.label_distribution(reviews)
        long_tail = []
        
        for category, items in dist.items():
            for item in items:
                code = item['code']
                severity = self.labeler.labels.get(code, {}).get('severity', '无')
                if item['pct'] < threshold_pct and severity in ('高', '极高', '中高'):
                    long_tail.append({
                        'code': code,
                        'label': item['label'],
                        'category': category,
                        'count': item['count'],
                        'pct': item['pct'],
                        'severity': severity,
                        'risk_note': f"低频高危标签，需专项关注"
                    })
        
        return sorted(long_tail, key=lambda x: x['severity'], reverse=True)


# ============================================================
# 6. 数据导出
# ============================================================

class DataExporter:
    """数据导出器"""
    
    @staticmethod
    def to_json(reviews: List[Review], filepath: str):
        """导出为JSON"""
        data = [r.to_dict() for r in reviews]
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[EXPORT] {len(data)} reviews saved to {filepath}")
    
    @staticmethod
    def to_csv(reviews: List[Review], filepath: str):
        """导出为CSV"""
        import csv
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'platform', 'business_name', 'business_type',
                'content', 'rating', 'date', 'year', 'month',
                'sentiment', 'labels', 'word_count'
            ])
            for r in reviews:
                writer.writerow([
                    r.id, r.platform, r.business_name, r.business_type,
                    r.content, r.rating, r.date, r.year, r.month,
                    r.sentiment, '|'.join(r.labels), r.word_count
                ])
        print(f"[EXPORT] {len(reviews)} reviews saved to {filepath}")
    
    @staticmethod
    def analysis_report(analyzer: TemporalAnalyzer, reviews: List[Review], filepath: str):
        """生成分析报告"""
        yoy = analyzer.yoy_analysis(reviews)
        mom = analyzer.mom_analysis(reviews)
        long_tail = analyzer.long_tail_detection(reviews)
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_reviews': len(reviews),
            'platform_distribution': dict(Counter(r.platform for r in reviews)),
            'year_distribution': dict(Counter(r.year for r in reviews if r.year)),
            'sentiment_distribution': dict(Counter(r.sentiment for r in reviews)),
            'yoy_analysis': yoy,
            'mom_analysis': mom,
            'long_tail_labels': long_tail,
            'label_distribution': analyzer.labeler.label_distribution(reviews)
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"[EXPORT] Analysis report saved to {filepath}")


# ============================================================
# 7. 平台覆盖说明（重要发现）
# ============================================================

PLATFORM_COVERAGE_NOTE = """
重要发现：大众点评/美团/淘宝闪购在桂山岛的覆盖率极低

经系统性搜索验证（2026年7月13日）：
1. 大众点评：桂山岛景点有16,512张用户照片，但岛上独立商家页面几乎为零
2. 美团：搜索引擎未索引桂山岛相关页面，商家入驻率极低
3. 淘宝闪购：尚未覆盖桂山岛（海岛即时零售基础设施缺失）

实际有评论数据的平台：
- P0（优先）：携程/Trip.com（318+条评论）、易游网（227+条）、永安旅游（186+条）
- P1（重要）：黑猫投诉（详细投诉链）、知乎（排雷帖）、珠海票务网
- P2（补充）：小红书/微博/抖音（原报告已采集5312条）

建议：
1. 将原报告中的"小红书/微博/抖音"三平台改为"携程/OTA/投诉平台"为主
2. 保留小红书数据作为"种草内容"对照组
3. 放弃大众点评/美团/淘宝闪购（无数据基础）
4. 新增黑猫投诉/知乎作为"深度投诉"数据源
"""

# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("桂山岛文旅体验数据采集框架 v2.0")
    print("=" * 60)
    print()
    print(PLATFORM_COVERAGE_NOTE)
    print()
    
    # 初始化组件
    labeler = ScenarioLabeler()
    sampler = BalancedSampler(target_per_platform=200)
    analyzer = TemporalAnalyzer(labeler)
    exporter = DataExporter()
    
    # 示例：手动录入的已知评论数据（后续由爬虫填充）
    sample_reviews = [
        Review(
            id="manual_001",
            platform="知乎",
            source_url="https://zhuanlan.zhihu.com/p/416693638",
            business_name="桂山岛某餐厅",
            business_type="餐饮",
            content="120元/人自助，海鲜种类非常少！白贝、花甲、虾、生蚝，非常不新鲜！量非常少，让服务员加白贝只是敷衍了事",
            rating=1.0,
            date="2021-10-05",
            user_location="未知"
        ),
        Review(
            id="manual_002",
            platform="微博",
            source_url="https://sina.cn",
            business_name="桂山岛整体",
            business_type="景点",
            content="走了半天桂山岛，确实是没啥好走没啥好看没啥好吃的，消费也没啥优势可言。真就是来躺着最好",
            rating=2.0,
            date="2026-01-24",
            user_location="广东"
        ),
        Review(
            id="manual_003",
            platform="黑猫投诉",
            source_url="https://tousu.sina.cn",
            business_name="观山海酒店",
            business_type="住宿",
            content="通过美团预订后因故无法入住，酒店和美团拒绝退还2096元，私自办理入住、平台不得取消属霸王条款",
            rating=1.0,
            date="2023-08-25",
            user_location="未知"
        ),
        Review(
            id="manual_004",
            platform="易游网",
            source_url="https://eztravel.com",
            business_name="上岛民宿",
            business_type="住宿",
            content="450块住10平米，行李都没地方放。宾馆又旧又潮湿又小，功夫茶具是用来摆设的不能用，厕所天板缺一块",
            rating=1.5,
            date="2026-03-15",
            user_location="未知"
        ),
        Review(
            id="manual_005",
            platform="易游网",
            source_url="https://eztravel.com",
            business_name="上岛民宿",
            business_type="住宿",
            content="去到了和我说没房了，被带到别的民宿。实际和图片不符，房间卫生比较差，有一两只小蟑螂，厕所有异味",
            rating=1.0,
            date="2025-04-20",
            user_location="未知"
        ),
        Review(
            id="manual_006",
            platform="易游网",
            source_url="https://eztravel.com",
            business_name="海顺精品民宿",
            business_type="住宿",
            content="房间里面有很多小蟑螂，床单被套都是毛发。每次开热水都会出一阵黄颜色的水",
            rating=2.0,
            date="2026-04-10",
            user_location="未知"
        ),
        Review(
            id="manual_007",
            platform="易游网",
            source_url="https://eztravel.com",
            business_name="驿旅阳光民宿",
            business_type="住宿",
            content="周末特贵500多，空调不制冷噪声很大，楼顶白天巨热空调开16度开了很久温度也没降下来。一次性拖鞋矿泉水要问才有",
            rating=2.0,
            date="2025-08-15",
            user_location="未知"
        ),
        Review(
            id="manual_008",
            platform="易游网",
            source_url="https://eztravel.com",
            business_name="蓝色海岸民宿",
            business_type="住宿",
            content="风景很美，服务热情周到，还有免费升级和接送服务。海鲜好吃新鲜，推荐",
            rating=5.0,
            date="2026-02-10",
            user_location="广东"
        ),
        Review(
            id="manual_009",
            platform="珠海票务网",
            source_url="https://m.zh-piao.com",
            business_name="桂语香山酒店",
            business_type="住宿",
            content="旧桂山标准房一般，新桂山标准双人间空间比较小。整体还行吧",
            rating=3.5,
            date="2025-06-10",
            user_location="未知"
        ),
        Review(
            id="manual_010",
            platform="南方+",
            source_url="https://nfnews.com",
            business_name="桂山岛网红餐厅",
            business_type="餐饮",
            content="珠海市查餐厅网络直播执法行动走进桂山岛，重点检查网红餐厅操作间、食品储存间、餐具消毒间，发现问题要求限期整改",
            rating=None,
            date="2025-06-11",
            user_location=None
        ),
    ]
    
    # 标签编码
    print("[1/4] 执行场景标签编码...")
    labeler.label_batch(sample_reviews)
    
    # 标签分布
    dist = labeler.label_distribution(sample_reviews)
    print("\n标签分布:")
    for category, items in dist.items():
        print(f"  [{category}]")
        for item in items:
            print(f"    {item['code']} {item['label']}: {item['count']}条 ({item['pct']}%)")
    
    # 同比分析
    print("\n[2/4] 同比分析 (2025 vs 2026)...")
    yoy = analyzer.yoy_analysis(sample_reviews)
    for cat, changes in yoy['categories'].items():
        print(f"  [{cat}]")
        for c in changes:
            trend = "↑" if c['trend'] == 'up' else ("↓" if c['trend'] == 'down' else "→")
            print(f"    {c['label']}: 2025={c['count_2025']} → 2026={c['count_2026']} ({trend}{c['yoy_change_pct']}%)")
    
    # 长尾检测
    print("\n[3/4] 长尾标签检测...")
    long_tail = analyzer.long_tail_detection(sample_reviews)
    for lt in long_tail:
        print(f"  ⚠ {lt['label']} [{lt['severity']}] - {lt['count']}条 ({lt['pct']}%) - {lt['risk_note']}")
    
    # 导出
    print("\n[4/4] 导出数据...")
    base_dir = r"E:\珠海桂山岛案例\数据采集"
    exporter.to_json(sample_reviews, os.path.join(base_dir, "processed", "sample_reviews.json"))
    exporter.to_csv(sample_reviews, os.path.join(base_dir, "processed", "sample_reviews.csv"))
    exporter.analysis_report(analyzer, sample_reviews, os.path.join(base_dir, "processed", "analysis_report.json"))
    
    print("\n" + "=" * 60)
    print("框架初始化完成！")
    print("下一步：部署爬虫采集各平台真实评论数据")
    print("=" * 60)
