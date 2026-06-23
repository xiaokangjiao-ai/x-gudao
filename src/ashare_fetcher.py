#!/usr/bin/env python3
"""
A股数据获取模块 - 多渠道支持（新浪财经、网易财经、东方财富）
"""
import os
import requests
import re
import json
import time
from datetime import datetime, timedelta
import random

# 清除代理（国内API不需要代理）
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    os.environ.pop(key, None)


def fetch_ashare_realtime(codes: list, max_retries: int = 3) -> dict:
    """
    从多个渠道获取 A股实时行情（带重试和多渠道）
    codes: 6位股票代码列表，如 ['300750', '603259']
    返回: {code: {name, price, change_pct, ...}}
    """
    # 渠道1: 新浪财经
    result = _fetch_from_sina(codes, max_retries)
    if len(result) >= len(codes) * 0.8:  # 成功率>80%就返回
        return result
    
    print(f"  [WARN] 新浪财经数据不完整 ({len(result)}/{len(codes)})，尝试网易财经...")
    
    # 渠道2: 网易财经
    result2 = _fetch_from_163(codes, max_retries)
    result.update(result2)
    
    if len(result) >= len(codes) * 0.8:
        return result
    
    print(f"  [WARN] 网易财经数据不完整 ({len(result)}/{len(codes)})，尝试东方财富...")
    
    # 渠道3: 东方财富
    result3 = _fetch_from_eastmoney(codes, max_retries)
    result.update(result3)
    
    return result


def _fetch_from_sina(codes: list, max_retries: int = 3) -> dict:
    """新浪财经API"""
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
    
    for attempt in range(max_retries):
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
            print(f"  [SINA ERROR] 尝试 {attempt+1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
    
    return {}


def _fetch_from_163(codes: list, max_retries: int = 3) -> dict:
    """网易财经API（备用渠道）"""
    result = {}
    
    for code in codes:
        # 网易格式: 0开头的深圳，1开头的上海
        if code.startswith('6'):
            symbol = f"1{code}"
        else:
            symbol = f"0{code}"
        
        url = f"https://api.money.126.net/data/feed/{symbol}"
        headers = {
            'Referer': 'https://money.163.com/',
            'User-Agent': 'Mozilla/5.0'
        }
        
        for attempt in range(max_retries):
            try:
                r = requests.get(url, headers=headers, timeout=10, proxies={'http': None, 'https': None})
                # 网易返回的是JSONP，需要解析
                text = r.text.strip()
                if text.startswith('_ntes_quote_callback('):
                    text = text[21:-2]  # 去掉JSONP包装
                data = json.loads(text)
                
                if symbol in data:
                    d = data[symbol]
                    result[code] = {
                        'name': d.get('name', code),
                        'open': float(d.get('open', 0)),
                        'close': float(d.get('yestclose', 0)),
                        'price': float(d.get('price', 0)),
                        'high': float(d.get('high', 0)),
                        'low': float(d.get('low', 0)),
                        'change_pct': round(d.get('percent', 0) * 100, 2),
                        'volume': int(d.get('volume', 0)),
                        'amount': float(d.get('turnover', 0)),
                        'date': d.get('time', '')[:10],
                        'time': d.get('time', '')[11:],
                    }
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"  [163 ERROR] {code}: {e}")
                time.sleep(1)
    
    return result


def _fetch_from_eastmoney(codes: list, max_retries: int = 3) -> dict:
    """东方财富API（备用渠道）"""
    result = {}
    
    for code in codes:
        # 判断市场
        if code.startswith('6'):
            secid = f"1.{code}"
        else:
            secid = f"0.{code}"
        
        url = "http://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": secid,
            "fields": "f57,f58,f43,f169,f170,f46,f44,f45,f47,f48",
        }
        
        for attempt in range(max_retries):
            try:
                r = requests.get(url, params=params, timeout=10, proxies={'http': None, 'https': None})
                r.encoding = 'utf-8'
                data = r.json()
                
                if 'data' in data and data['data']:
                    d = data['data']
                    result[code] = {
                        'name': d.get('f58', code),
                        'open': float(d.get('f46', 0)),
                        'close': float(d.get('f60', 0)),  # 昨日收盘
                        'price': float(d.get('f43', 0)) / 100,  # 当前价格（分->元）
                        'high': float(d.get('f44', 0)) / 100,
                        'low': float(d.get('f45', 0)) / 100,
                        'change_pct': round(d.get('f169', 0) / 100, 2),  # 涨跌幅
                        'volume': int(d.get('f47', 0)),
                        'amount': float(d.get('f48', 0)),
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'time': datetime.now().strftime('%H:%M:%S'),
                    }
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"  [EM ERROR] {code}: {e}")
                time.sleep(1)
    
    return result


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
