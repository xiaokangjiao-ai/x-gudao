# -*- coding: utf-8 -*-
"""X-Gudao 快速测试"""
import sys
sys.path.insert(0, '.')

from src.data_fetcher import DataFetcher
from src.analyzer import TechnicalAnalyzer
from src.comparator import Comparator

print("=== X-Gudao 核心测试 ===")
print()

# 1. 测试数据获取
print("1. 测试数据获取...")
fetcher = DataFetcher()
data = fetcher.get_multiple_stocks(['VOO', 'QQQ', 'SPY'], period='6mo')
print(f"   OK: 获取了 {list(data.keys())}")
for sym, df in data.items():
    print(f"   - {sym}: {len(df)} 行")

print()

# 2. 测试对比分析
print("2. 测试对比分析...")
comparator = Comparator()
results = comparator.compare_assets(data)
print("   OK: 分析完成")
print(f"   最佳收益: {results['summary']['best_return']['symbol']}")
print(f"   最优夏普: {results['summary']['best_sharpe']['symbol']}")
print(f"   最低波动: {results['summary']['lowest_volatility']['symbol']}")

print()
print("=== 测试全部通过 ===")
