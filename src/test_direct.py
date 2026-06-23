#!/usr/bin/env python3
import os
import sys

# 清除代理
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    if key in os.environ:
        del os.environ[key]

print("环境变量已清除")

# 测试 requests 直接访问
import requests

print("\n测试直接访问 East Money API...")
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
    # 禁用代理
    r = requests.get(url, params=params, timeout=10, proxies={'http': None, 'https': None})
    print(f"  状态码: {r.status_code}")
    print(f"  内容: {r.text[:300]}")
except Exception as e:
    print(f"  错误: {type(e).__name__}: {e}")
