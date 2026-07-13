# -*- coding: utf-8 -*-
"""
桂山岛文旅数据合并 + 标签编码 + 同比环比分析
=============================================
合并所有平台采集数据，执行场景标签编码、均衡采样、时间维度分析，导出最终数据集。
"""
import json, os, sys, glob, hashlib
from datetime import datetime
from collections import Counter, defaultdict

# ── 导入采集框架 ──
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guishan_collector import (
    Review, SCENARIO_LABELS, ScenarioLabeler,
    BalancedSampler, TemporalAnalyzer, DataExporter
)

BASE_DIR = r"E:\珠海桂山岛案例\数据采集"
RAW_DIR = os.path.join(BASE_DIR, "raw")
OUT_DIR = os.path.join(BASE_DIR, "processed")

def load_json_files():
    """加载所有 raw/*.json 文件"""
    all_reviews = []
    for fpath in glob.glob(os.path.join(RAW_DIR, "*.json")):
        fname = os.path.basename(fpath)
        print(f"[LOAD] {fname}")
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            all_reviews.extend(data)
            print(f"       -> {len(data)} records")
        elif isinstance(data, dict):
            # Try multiple nested keys
            for key in ['reviews', 'records', 'data', 'items']:
                if key in data and isinstance(data[key], list):
                    all_reviews.extend(data[key])
                    print(f"       -> {len(data[key])} records (nested in '{key}')")
                    break
            else:
                print(f"       -> skipped (unknown dict format)")
        else:
            print(f"       -> skipped (unknown format)")
    return all_reviews

def raw_to_reviews(raw_list):
    """将原始JSON转换为Review对象列表"""
    reviews = []
    for i, item in enumerate(raw_list):
        # 标准化字段
        rid = str(item.get('id', f'auto_{i:04d}'))
        # 确保id唯一
        if not rid or rid.startswith('auto_'):
            platform = item.get('platform', 'unknown')
            rid = f"{platform}_{i:04d}"
        
        content = item.get('content', '')
        if not content or len(content.strip()) < 5:
            continue  # 跳过空内容
        
        rating = item.get('rating')
        if rating is not None:
            try:
                rating = float(rating)
            except (ValueError, TypeError):
                rating = None
        
        date_str = item.get('date')
        # 尝试多种日期格式
        parsed_date = None
        if date_str:
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%Y年%m月%d日', '%Y-%m']:
                try:
                    d = datetime.strptime(str(date_str).strip(), fmt)
                    parsed_date = d.strftime('%Y-%m-%d')
                    break
                except ValueError:
                    continue
        
        r = Review(
            id=rid,
            platform=item.get('platform', '未知'),
            source_url=item.get('source_url', ''),
            business_name=item.get('business_name', '桂山岛'),
            business_type=item.get('business_type', '综合'),
            content=content.strip(),
            rating=rating,
            date=parsed_date,
            user_location=item.get('user_location', '') or ''
        )
        reviews.append(r)
    
    return reviews

def print_stats(reviews, title="统计"):
    """打印统计摘要"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")
    print(f"  总评论数: {len(reviews)}")
    
    # 平台分布
    plat = Counter(r.platform for r in reviews)
    print(f"\n  平台分布:")
    for p, c in plat.most_common():
        print(f"    {p}: {c}条")
    
    # 商家类型
    btype = Counter(r.business_type for r in reviews)
    print(f"\n  商家类型:")
    for t, c in btype.most_common():
        print(f"    {t}: {c}条")
    
    # 年份分布
    years = Counter(r.year for r in reviews if r.year)
    print(f"\n  年份分布:")
    for y, c in sorted(years.items()):
        print(f"    {y}: {c}条")
    
    # 评分分布
    ratings = [r.rating for r in reviews if r.rating is not None]
    if ratings:
        print(f"\n  评分: 均值={sum(ratings)/len(ratings):.2f}, "
              f"最低={min(ratings):.1f}, 最高={max(ratings):.1f}")
    
    # 情感分布
    sent = Counter(r.sentiment for r in reviews if r.sentiment)
    print(f"\n  情感分布:")
    for s, c in sent.most_common():
        pct = c / len(reviews) * 100
        print(f"    {s}: {c}条 ({pct:.1f}%)")

def main():
    print("=" * 60)
    print(" 桂山岛文旅数据采集 - 数据合并与分析流水线")
    print("=" * 60)
    
    # ── 1. 加载原始数据 ──
    print("\n[1/6] 加载原始数据文件...")
    raw_list = load_json_files()
    print(f"  原始记录总数: {len(raw_list)}")
    
    # ── 2. 转换为Review对象 ──
    print("\n[2/6] 数据标准化...")
    reviews = raw_to_reviews(raw_list)
    print(f"  有效记录: {len(reviews)} (过滤了{len(raw_list)-len(reviews)}条空/无效)")
    
    # 去重（按内容hash）
    seen = set()
    unique = []
    for r in reviews:
        h = hashlib.md5(r.content.encode()).hexdigest()[:12]
        if h not in seen:
            seen.add(h)
            unique.append(r)
    dupes = len(reviews) - len(unique)
    reviews = unique
    print(f"  去重后: {len(reviews)} (去除{dupes}条重复)")
    
    print_stats(reviews, "合并后原始数据")
    
    # ── 3. 场景标签编码 ──
    print("\n[3/6] 执行场景标签编码...")
    labeler = ScenarioLabeler()
    reviews = labeler.label_batch(reviews)
    
    dist = labeler.label_distribution(reviews)
    print(f"\n  标签分布 (共{len(SCENARIO_LABELS)}个标签):")
    total_labeled = 0
    for category, items in sorted(dist.items()):
        print(f"  [{category}]")
        for item in sorted(items, key=lambda x: -x['count']):
            marker = " [!]" if item['pct'] < 5 and any(
                SCENARIO_LABELS.get(it['code'], {}).get('severity', '') in ('高', '极高')
                for it in items
            ) else ""
            print(f"    {item['code']} {item['label']}: {item['count']}条 ({item['pct']}%){marker}")
            total_labeled += item['count']
    
    unlabeled = sum(1 for r in reviews if not r.labels)
    print(f"\n  未命中任何标签: {unlabeled}条 ({unlabeled/len(reviews)*100:.1f}%)")
    
    # ── 4. 均衡采样 ──
    print("\n[4/6] 执行分层均衡采样...")
    sampler = BalancedSampler(target_per_platform=50, seed=42)
    sampled = sampler.sample(reviews)
    print_stats(sampled, f"采样后数据 (从{len(reviews)}条→{len(sampled)}条)")
    
    # ── 5. 同比/环比分析 ──
    print("\n[5/6] 执行时间维度分析...")
    analyzer = TemporalAnalyzer(labeler)
    
    # 同比 (2025 vs 2026)
    yoy = analyzer.yoy_analysis(reviews)
    print(f"\n  同比分析 (2025 vs 2026):")
    print(f"    2025年: {yoy['count_a']}条")
    print(f"    2026年: {yoy['count_b']}条")
    
    for cat, changes in yoy['categories'].items():
        significant = [c for c in changes if abs(c['yoy_change_pct']) > 20]
        if significant:
            print(f"\n  [{cat}] 显著变化:")
            for c in significant:
                trend = "↑" if c['trend'] == 'up' else "↓"
                print(f"    {trend} {c['label']}: "
                      f"2025={c['count_2025']}→2026={c['count_2026']} "
                      f"({c['yoy_change_pct']:+.1f}%)")
    
    # 环比
    mom = analyzer.mom_analysis(reviews)
    print(f"\n  环比分析 ({len(mom['months'])}个月份):")
    for change in mom['changes'][-6:]:  # 最近6个月
        print(f"    {change['from']}→{change['to']}: "
              f"评论{change['count_prev']}→{change['count_curr']}, "
              f"负面{change['negative_prev']}→{change['negative_curr']}")
    
    # 长尾检测
    long_tail = analyzer.long_tail_detection(reviews)
    if long_tail:
        print(f"\n  长尾高危标签 ({len(long_tail)}个):")
        for lt in long_tail:
            print(f"    [!] {lt['label']} [{lt['severity']}] "
                  f"- {lt['count']}条 ({lt['pct']}%)")
    else:
        print(f"\n  长尾高危标签: 无（所有高危标签占比≥2%）")
    
    # ── 6. 导出 ──
    print("\n[6/6] 导出数据...")
    exporter = DataExporter()
    
    # 全量数据
    exporter.to_json(reviews, os.path.join(OUT_DIR, "all_reviews.json"))
    exporter.to_csv(reviews, os.path.join(OUT_DIR, "all_reviews.csv"))
    
    # 采样数据
    exporter.to_json(sampled, os.path.join(OUT_DIR, "sampled_reviews.json"))
    exporter.to_csv(sampled, os.path.join(OUT_DIR, "sampled_reviews.csv"))
    
    # 分析报告
    exporter.analysis_report(analyzer, reviews, os.path.join(OUT_DIR, "full_analysis.json"))
    
    # 单独导出标签编码详情
    label_details = []
    for r in reviews:
        if r.labels:
            label_details.append({
                'id': r.id,
                'platform': r.platform,
                'business_name': r.business_name,
                'date': r.date,
                'content_preview': r.content[:100] + ('...' if len(r.content) > 100 else ''),
                'labels': r.labels,
                'label_details': r.label_details,
                'sentiment': r.sentiment,
                'rating': r.rating
            })
    with open(os.path.join(OUT_DIR, "label_details.json"), 'w', encoding='utf-8') as f:
        json.dump(label_details, f, ensure_ascii=False, indent=2)
    print(f"  [EXPORT] {len(label_details)} labeled records → label_details.json")
    
    # 导出同比环比详细
    temporal_data = {
        'yoy_analysis': yoy,
        'mom_analysis': mom,
        'long_tail_labels': long_tail,
        'generated_at': datetime.now().isoformat()
    }
    with open(os.path.join(OUT_DIR, "temporal_analysis.json"), 'w', encoding='utf-8') as f:
        json.dump(temporal_data, f, ensure_ascii=False, indent=2)
    print(f"  [EXPORT] temporal_analysis.json")
    
    # 最终汇总
    print(f"\n{'='*60}")
    print(f" 采集完成汇总")
    print(f"{'='*60}")
    print(f"  全量数据:   {len(reviews)}条")
    print(f"  采样数据:   {len(sampled)}条")
    print(f"  有标签:     {len(reviews)-unlabeled}条 ({(len(reviews)-unlabeled)/len(reviews)*100:.1f}%)")
    print(f"  负面评论:   {sum(1 for r in reviews if r.sentiment=='negative')}条")
    print(f"  正面评论:   {sum(1 for r in reviews if r.sentiment=='positive')}条")
    print(f"  中性评论:   {sum(1 for r in reviews if r.sentiment=='neutral')}条")
    print(f"  长尾高危:   {len(long_tail)}个标签")
    print(f"\n  输出目录: {OUT_DIR}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
