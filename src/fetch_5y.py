#!/usr/bin/env python3
"""带指数退避的5年数据拉取"""
import sys, io, time, random
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

try:
    import yfinance as yf
except ImportError:
    print("[ERROR] 缺少 yfinance")
    sys.exit(1)

ROOT = Path(__file__).parent.parent.resolve()
DB_PATH = ROOT / "data" / "market_data.db"

TICKERS = [
    "SPY", "IVV", "VOO", "QQQ", "VTI", "BND", "GLD", "IWM",
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSM", "BRK.B",
]

def init_db():
    (DB_PATH.parent).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS market_data (
        ticker TEXT NOT NULL, date TEXT NOT NULL,
        open REAL, high REAL, low REAL, close REAL, volume INTEGER,
        updated_at TEXT NOT NULL, PRIMARY KEY (ticker, date))""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ticker_date ON market_data(ticker, date)")
    conn.commit()
    return conn

def fetch_with_retry(conn, ticker, max_retries=3):
    last_date = conn.execute("SELECT MAX(date) FROM market_data WHERE ticker=?", (ticker,)).fetchone()[0]
    if last_date:
        start_dt = datetime.strptime(last_date, "%Y-%m-%d") - timedelta(days=10)
        start = start_dt.strftime("%Y-%m-%d")
        mode = f"增量({last_date}后)"
    else:
        start = (datetime.now() - timedelta(days=365*5+10)).strftime("%Y-%m-%d")
        mode = "全量5年"

    for attempt in range(max_retries):
        try:
            df = yf.Ticker(ticker).history(start=start, auto_adjust=True)
            if df.empty:
                print(f"  {ticker}: ⚠️ 空数据")
                return 0
            count = 0
            now = datetime.now().isoformat()
            for date, row in df.iterrows():
                d = date.strftime("%Y-%m-%d")
                conn.execute("""INSERT OR REPLACE INTO market_data 
                    (ticker, date, open, high, low, close, volume, updated_at)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (ticker, d, round(float(row["Open"]),4), round(float(row["High"]),4),
                     round(float(row["Low"]),4), round(float(row["Close"]),4),
                     int(row["Volume"]), now))
                count += 1
            conn.commit()
            total = conn.execute("SELECT COUNT(*) FROM market_data WHERE ticker=?", (ticker,)).fetchone()[0]
            print(f"  {ticker}: ✅ {mode} 写入{count}条 (总计{total}条)")
            return count
        except Exception as e:
            wait = (attempt + 1) * 30 + random.randint(5, 15)
            print(f"  {ticker}: ❌ 尝试{attempt+1}/{max_retries} 失败: {e}, 等待{wait}秒...")
            time.sleep(wait)
    print(f"  {ticker}: ❌ 所有重试均失败")
    return 0

def main():
    print(f"\n{'='*50}")
    print(f"x-gudao 5年数据补全 (指数退避)")
    print(f"{'='*50}\n")
    conn = init_db()
    total_new = 0
    for i, t in enumerate(TICKERS):
        print(f"[{i+1}/{len(TICKERS)}] {t}")
        n = fetch_with_retry(conn, t)
        total_new += n
        if i < len(TICKERS) - 1:
            time.sleep(random.uniform(5, 10))  # 标的间间隔
    conn.close()
    print(f"\n✅ 完成！新增/更新: {total_new} 条")

if __name__ == "__main__":
    main()
