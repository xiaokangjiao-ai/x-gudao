#!/usr/bin/env python3
import sys
import os

# 设置路径
sys.path.insert(0, 'C:\\Users\\Administrator\\x-gudao\\gh-pages\\src')

from ashare_fetcher import get_ashare_data

# 测试 9 个 A股
codes = ['300750', '603259', '002475', '000858', '600519', '000333', '300760', '000661', '002007']

print("测试获取 9 个 A股数据:\n")
for code in codes:
    print(f"[{code}]")
    data = get_ashare_data(code, 7)
    if data:
        print(f"  名称: {data['name']}")
        print(f"  价格: {data['price']}")
        print(f"  涨跌幅: {data['change_pct']}%")
        print(f"  历史数据: {len(data['history'])} 条")
        print(f"  7日最高: {data['high_7d']}")
        print(f"  7日最低: {data['low_7d']}")
    else:
        print("  获取失败")
    print()
