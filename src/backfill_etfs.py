#!/usr/bin/env python3
"""
补全缺失ETF的JSON数据文件
IEFA, IVV, VEA, VWO → Polygon.io → output/{ticker}.json
"""
import sys, json, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent))
import massive_fetcher as mf

ROOT = Path(__file__).parent.parent
OUTPUT = ROOT / "output"

TICKERS_INFO = {
    "IEFA": {
        "name": "iShares MSCI EAFE ETF",
        "category": "etf",
        "expense_ratio": "0.32%",
        "aum": "65B",
        "avg_daily_volume": "10.2M",
        "inception_date": "2001-08-01",
        "issuer": "iShares",
        "holdings_count": "~900",
        "dividend_freq": "半年",
        "tracked_index": "MSCI EAFE Index",
    },
    "IVV": {
        "name": "iShares Core S&P 500 ETF",
        "category": "etf",
        "expense_ratio": "0.03%",
        "aum": "500B",
        "avg_daily_volume": "3.1M",
        "inception_date": "2000-05-15",
        "issuer": "iShares",
        "holdings_count": "503",
        "dividend_freq": "季度",
        "tracked_index": "S&P 500",
    },
    "VEA": {
        "name": "Vanguard FTSE Developed Markets ETF",
        "category": "etf",
        "expense_ratio": "0.05%",
        "aum": "150B",
        "avg_daily_volume": "5.3M",
        "inception_date": "2007-07-02",
        "issuer": "Vanguard",
        "holdings_count": "~4000",
        "dividend_freq": "半年",
        "tracked_index": "FTSE Developed All Cap ex USA Index",
    },
    "VWO": {
        "name": "Vanguard FTSE Emerging Markets ETF",
        "category": "etf",
        "expense_ratio": "0.08%",
        "aum": "80B",
        "avg_daily_volume": "15.6M",
        "inception_date": "2005-03-02",
        "issuer": "Vanguard",
        "holdings_count": "~5500",
        "dividend_freq": "半年",
        "tracked_index": "FTSE Emerging Index",
    },
}

def build_json(ticker: str, info: dict, rows: list) -> dict:
    return {
        "ticker": ticker,
        "name": info["name"],
        "category": info["category"],
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+0800"),
        "data": [
            {
                "date": r["date"],
                "open": r["o"],
                "high": r["h"],
                "low": r["l"],
                "close": r["c"],
                "volume": r["v"],
            }
            for r in rows
        ],
    }

def main():
    print("=" * 50)
    print("补全缺失ETF数据")
    print("=" * 50)

    for i, ticker in enumerate(TICKERS_INFO):
        info = TICKERS_INFO[ticker]
        print(f"\n[{i+1}/4] {ticker} ({info['name']})")
        print(f"  从 Polygon.io 获取历史数据...")

        rows, status = mf.fetch_ohlcv(ticker, "2024-01-01", "2026-06-16")
        print(f"  状态: {status} | 条数: {len(rows)}")

        if status != "OK" or not rows:
            print(f"  [SKIP] 无法获取数据，跳过")
            if i < 3:
                print(f"  等待 {mf.MIN_INTERVAL}s...")
                time.sleep(mf.MIN_INTERVAL)
            continue

        d = build_json(ticker, info, rows)
        out_path = OUTPUT / f"{ticker}.json"
        out_path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✅ 已写入: {out_path.name} ({len(rows)}条, {out_path.stat().st_size//1024}KB)")

        # 最后一批不等间隔
        if i < 3:
            print(f"  等待 {mf.MIN_INTERVAL}s（限流）...")
            time.sleep(mf.MIN_INTERVAL)

    print("\n" + "=" * 50)
    print("全部完成！运行 generate_static.py 重新生成详情页。")
    print("=" * 50)

if __name__ == "__main__":
    main()
