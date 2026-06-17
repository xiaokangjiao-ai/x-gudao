#!/usr/bin/env python3
import json
from pathlib import Path

output = Path('output')
results = []

for f in sorted(output.glob('*.json')):
    if f.stem in ('overview', 'CNAME', 'watchlist'): continue
    try:
        d = json.loads(f.read_text(encoding='utf-8'))
        data = d.get('data', [])
        dates = [x['date'] for x in data] if data else []
        results.append({
            'ticker': d.get('ticker', f.stem).upper(),
            'name': d.get('name', ''),
            'count': len(dates),
            'latest': dates[-1] if dates else '?',
            'earliest': dates[0] if dates else '?',
            'has_name': bool(d.get('name')),
            'category': d.get('category', '?'),
        })
    except Exception as e:
        results.append({'ticker': f.stem.upper(), 'error': str(e)})

print('=== JSON数据完整性 ===')
good = mid = bad = 0
for t in sorted(results, key=lambda x: x.get('count', 0), reverse=True):
    if 'error' in t:
        print(f"  [XX] {t['ticker']:8s}  解析错误: {t['error']}")
        bad += 1
    elif t.get('count', 0) > 100:
        print(f"  [OK] {t['ticker']:8s} {t['count']:4d}条  {t['earliest']} ~ {t['latest']}  [{t['category']}]  name={t['has_name']}")
        good += 1
    elif t.get('count', 0) > 20:
        print(f"  [--] {t['ticker']:8s} {t['count']:4d}条  {t['earliest']} ~ {t['latest']}  [{t['category']}]  name={t['has_name']}")
        mid += 1
    else:
        print(f"  [NG] {t['ticker']:8s} {t['count']:4d}条  {t['earliest']} ~ {t['latest']}  [{t['category']}]  name={t['has_name']}")
        bad += 1

print(f"\n汇总: [OK]完整={good}  [--]不足={mid}  [NG]缺失={bad}")

print("\n=== 详情页文件大小 ===")
for d in sorted(output.glob('*/index.html')):
    t = d.parent.name.upper()
    size = d.stat().st_size
    marker = '[BIG]' if size > 50000 else '[MED]' if size > 20000 else '[SML]'
    print(f"  {marker} {t:8s}  {size//1024:5d}KB")
