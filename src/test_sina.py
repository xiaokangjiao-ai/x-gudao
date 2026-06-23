#!/usr/bin/env python3
import os
import sys
import requests

# 清除代理
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    if key in os.environ:
        del os.environ[key]

print("测试新浪财经 API...")

# 新浪财经实时行情 API
# 格式: sh+6位代码 (上海) 或 sz+6位代码 (深圳)
codes = ['sz300750', 'sh603259', 'sz002475']
url = f"https://hq.sinajs.cn/list={','.join(codes)}"
headers = {
    'Referer': 'https://finance.sina.com.cn',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

try:
    r = requests.get(url, headers=headers, timeout=10, proxies={'http': None, 'https': None})
    r.encoding = 'gb2312'
    print(f"状态码: {r.status_code}")
    print(f"内容:\n{r.text}")
except Exception as e:
    print(f"错误: {type(e).__name__}: {e}")
