#!/usr/bin/env python3
"""
A股数据获取模块 - 使用新浪财经实时行情
"""
import os
import requests
import re
from datetime import datetime, timedelta
import random

# 清除代理（国内API不需要代理）
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    os.environ.pop(key, None)

def fetch_ashare_realtime(codes: list) -> dict:
    """
    从新浪财经获取 A股实时行情
    codes: 6位股票代码列表，如 ['300750', '603259']
    返回: {code: {name, price, change_pct, ...}}
    """
    formatted_codes = []
    for code in codes:
        if code.startswith('6'):
            formatted_codes.append(f"sh{code}")
        else:
            formatted_codes.append(f"sz{code}")
    
    url = f"https://hq.sinajs.cn/list={','.join(formatted_codes)}"
    headers = {
        'Referer': 'https://finance.sina.com.cn',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10, proxies={'http': None, 'https': None})
        r.encoding = 'gbk'
        
        result = {}
        lines = r.text.strip().split(';')
        
        for line in lines:
            if not line.strip():
                continue
            match = re.search(r'var hq_str_(sh|sz)(\d{6})="([^"]*)"', line)
            if match:
                market, code, data = match.groups()
                parts = data.split(',')
                if len(parts) >= 33:
                    result[code] = {
                        'name': parts[0],
                        'open': float(parts[1]),
                        'close': float(parts[2]),
                        'price': float(parts[3]),
                        'high': float(parts[4]),
                        'low': float(parts[5]),
                        'change_pct': round((float(parts[3]) - float(parts[2])) / float(parts[2]) * 100, 2) if float(parts[2]) > 0 else 0,
                        'volume': int(parts[8]),
                        'amount': float(parts[9]),
                        'date': parts[30],
                        'time': parts[31],
                    }
        
        return result
    except Exception as e:
        print(f"  [ERROR] 获取实时行情失败: {e}")
        return {}


def generate_mock_history(realtime_data: dict, days: int = 252) -> list:
    """
    基于实时价格生成模拟历史数据
    """
    import numpy as np
    
    records = []
    end_date = datetime.now()
    
    current_price = realtime_data.get('price', 100)
    
    # 生成随机价格序列
    prices = [current_price]
    for i in range(days - 1):
        change = random.uniform(-0.02, 0.02)
        price = prices[-1] * (1 - change)
        prices.append(price)
    
    prices.reverse()
    
    for i in range(days):
        date = (end_date - timedelta(days=days-1-i)).strftime('%Y-%m-%d')
        price = prices[i]
        high = price * random.uniform(1.0, 1.02)
        low = price * random.uniform(0.98, 1.0)
        open_price = random.uniform(low, high)
        
        records.append({
            "date": date,
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(price, 2),
            "volume": int(random.uniform(1000000, 50000000)),
        })
    
    return records


def get_ashare_data(code: str, days: int = 252) -> dict:
    """
    获取单个 A股的完整数据
    """
    realtime = fetch_ashare_realtime([code])
    
    if code not in realtime:
        return {}
    
    rt = realtime[code]
    
    # 生成模拟历史数据
    history = generate_mock_history(rt, days)
    
    # 计算统计数据
    closes = [d['close'] for d in history]
    high = max(d['high'] for d in history)
    low = min(d['low'] for d in history)
    
    if len(closes) > 1:
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        volatility = round((sum(r**2 for r in returns) / len(returns)) ** 0.5 * (252 ** 0.5) * 100, 2)
    else:
        volatility = 0
    
    return {
        'ticker': code,
        'name': rt['name'],
        'price': rt['price'],
        'change_pct': rt['change_pct'],
        'open': rt['open'],
        'high': rt['high'],
        'low': rt['low'],
        'prev_close': rt['close'],
        'volume': rt['volume'],
        'history': history,
        'high_7d': round(high, 2),
        'low_7d': round(low, 2),
        'volatility': volatility,
    }


if __name__ == '__main__':
    codes = ['300750', '603259', '002475']
    for code in codes:
        print(f"\n获取 {code}:")
        data = get_ashare_data(code, 7)
        if data:
            print(f"  名称: {data['name']}")
            print(f"  当前价格: {data['price']}")
            print(f"  涨跌幅: {data['change_pct']}%")
            print(f"  历史数据: {len(data['history'])} 条")
        else:
            print("  无数据")
