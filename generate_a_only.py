#!/usr/bin/env python3
"""
A股数据单独生成脚本
"""
import sys
import os
import json
from pathlib import Path

# 设置路径
ROOT = Path(__file__).parent.resolve()
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from ashare_fetcher import get_ashare_data

# A股列表
a_tickers = ["300750","603259","002475","000858","600519","000333","300760","000661","002007","601398","601288","601318","600887","000651","601888","002594","603501","688981"]

# 名称映射
names = {
    "300750": "宁德时代", "603259": "药明康德", "002475": "立讯精密",
    "000858": "五粮液", "600519": "贵州茅台", "000333": "美的集团",
    "300760": "迈瑞医疗", "000661": "长春高新", "002007": "华兰生物",
    "601398": "工商银行", "601288": "农业银行", "601318": "中国平安",
    "600887": "伊利股份", "000651": "格力电器", "601888": "中国中免",
    "002594": "比亚迪", "603501": "韦尔股份", "688981": "中芯国际",
}

categories = {
    "300750": "A股科技", "002475": "A股科技", "300760": "A股科技",
    "603501": "A股科技", "688981": "A股科技",
    "603259": "A股医药", "000661": "A股医药", "002007": "A股医药",
    "000858": "A股消费", "600519": "A股消费", "000333": "A股消费",
    "600887": "A股消费", "000651": "A股消费", "601888": "A股消费",
    "601398": "A股金融", "601288": "A股金融", "601318": "A股金融",
    "002594": "A股新能源",
}

print(f"获取 {len(a_tickers)} 个 A股数据...\n")

all_data = []
for ticker in a_tickers:
    print(f"[{ticker}] {names.get(ticker, ticker)}")
    data = get_ashare_data(ticker, 7)  # 获取7天数据
    if data:
        # 构建统一格式的数据
        history = data['history']
        closes = [d['close'] for d in history]
        
        result = {
            "ticker": ticker,
            "name": names.get(ticker, data['name']),
            "category": categories.get(ticker, "A股"),
            "data": history,
            "latest_close": data['price'],
            "day_change": data['change_pct'],
            "annual_return": data['change_pct'],  # 用日涨跌代替
            "annual_return_1y": data['change_pct'],
            "volatility": data.get('volatility', 0),
            "max_drawdown": 0,
            "sharpe": 0,
            "high": data['high_7d'],
            "low": data['low_7d'],
            "ma20": 0,
            "ma50": 0,
            "ma200": 0,
            "data_points": len(history),
            "date_range": f"{history[0]['date']} ~ {history[-1]['date']}",
            "price_history": history,
        }
        all_data.append(result)
        print(f"  OK 价格: {data['price']}, 涨跌: {data['change_pct']}%")
    else:
        print(f"  FAIL 获取失败")

print(f"\n✅ 成功获取 {len(all_data)} 个 A股数据")

# 保存为 JSON
output_file = ROOT / "a_shares_data.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)

print(f"\n数据已保存到: {output_file}")
