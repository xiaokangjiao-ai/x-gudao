# -*- coding: utf-8 -*-
"""生成16个占位行情图 SVG"""
import os

TICKERS = ["VOO","QQQ","IWM","BND","GLD","SCHD","VXUS","SMH",
           "NVDA","AAPL","MSFT","GOOGL","AMZN","META","LLY","BRK.B"]

SVG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120" viewBox="0 0 400 120">
  <rect width="400" height="120" fill="#0d1117" rx="8"/>
  <text x="200" y="55" text-anchor="middle" fill="#8b949e" font-family="Inter,sans-serif" font-size="14">📈 {ticker} 行情图</text>
  <text x="200" y="78" text-anchor="middle" fill="#30363d" font-family="Inter,sans-serif" font-size="11">点击查看 TradingView 实时图表</text>
</svg>"""

out_dir = os.path.join("C:\\Users\\Administrator\\x-gudao", "assets", "charts")
os.makedirs(out_dir, exist_ok=True)

for t in TICKERS:
    name = t.replace(".", "_")
    path = os.path.join(out_dir, f"{name}.svg")
    with open(path, "w", encoding="utf-8") as f:
        f.write(SVG_TEMPLATE.format(ticker=t))
    print(f"  OK {name}.svg")

print(f"Done: {len(TICKERS)} SVGs in {out_dir}")
