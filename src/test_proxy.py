#!/usr/bin/env python3
import os
import sys

# 先设置代理
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7897'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7897'

print("环境变量:")
print(f"  HTTP_PROXY: {os.environ.get('HTTP_PROXY')}")
print(f"  HTTPS_PROXY: {os.environ.get('HTTPS_PROXY')}")

# 测试 requests 是否能用代理
import requests

print("\n测试 requests 通过代理访问...")
try:
    # 先用 httpbin 测试代理
    r = requests.get('http://httpbin.org/ip', timeout=10)
    print(f"  httpbin IP: {r.text}")
except Exception as e:
    print(f"  错误: {e}")

# 测试 East Money API
print("\n测试 East Money API...")
try:
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": "0.300750",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "1",
        "end": "20500101",
        "lmt": 7,
    }
    r = requests.get(url, params=params, timeout=10)
    print(f"  状态码: {r.status_code}")
    print(f"  内容: {r.text[:200]}")
except Exception as e:
    print(f"  错误: {e}")
