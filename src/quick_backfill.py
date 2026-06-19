#!/usr/bin/env python3
"""快速补全16个标的的5年历史数据（yfinance → SQLite）"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import sqlite3, time
from pathlib import Path
from datetime import datetime, timedelta

try:
    import yfinance as yf
    import numpy as np
except ImportError as e:
    print(f"[ERROR] 缺少依赖: {e.name}")
    sys.exit(1)

ROOT = Path(__file__).parent.parent.resolve()
DB_PATH = ROOT / "data" / "market_data.db"
DATA_DIR = ROOT / "data"

# 16个标的：8 ETF + 8 股票
TICKERS = [
    "SPY", "IVV", "VOO", "QQQ", "VTI", "BND", "GLD", "IWM",
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSM", "BRK.B",
]

def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume INTEGER,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (ticker, date)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ticker_date ON market_data(ticker, date)")
    conn.commit()
    return conn

def get_last_date(conn, ticker):
    row = conn.execute("SELECT MAX(date) FROM market_data WHERE ticker=?", (ticker,)).fetchone()
    return row[0] if row and row[0] else None

def fetch_and_store(conn, ticker, period="5y"):
    last_date = get_last_date(conn, ticker)
    if last_date:
        # 计算需要拉取的起始日期（last_date 的前一天开始）
        last_dt = datetime.strptime(last_date, "%Y-%m-%d")
        start = (last_dt - timedelta(days=7)).strftime("%Y-%m-%d")  # 多拉几天避免缺失
        print(f"  {ticker}: 已有数据到 {last_date}, 从 {start} 增量拉取...")
    else:
        start = (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d")
        print(f"  {ticker}: 无历史数据, 全量拉取5年...")

    try:
        df = yf.Ticker(ticker).history(start=start, auto_adjust=True)
        if df.empty:
            print(f"  {ticker}: ⚠️ 无数据")
            return 0

        count = 0
        now = datetime.now().isoformat()
        for date, row in df.iterrows():
            d = date.strftime("%Y-%m-%d")
            conn.execute("""
                INSERT OR REPLACE INTO market_data (ticker, date, open, high, low, close, volume, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ticker, d, round(float(row["Open"]),4), round(float(row["High"]),4),
                  round(float(row["Low"]),4), round(float(row["Close"]),4),
                  int(row["Volume"]), now))
            count += 1

        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM market_data WHERE ticker=?", (ticker,)).fetchone()[0]
        print(f"  {ticker}: ✅ 写入 {count} 条 (总计 {total} 条)")
        return count
    except Exception as e:
        print(f"  {ticker}: ❌ {e}")
        return 0

def main():
    print(f"\n{'='*50}")
    print(f"x-gudao 数据补全 - 16个标的 × 5年")
    print(f"数据库: {DB_PATH}")
    print(f"{'='*50}\n")

    conn = init_db()
    total_new = 0
    total_existing = 0

    for i, ticker in enumerate(TICKERS):
        print(f"[{i+1}/{len(TICKERS)}] {ticker}")
        existing = conn.execute("SELECT COUNT(*) FROM market_data WHERE ticker=?", (ticker,)).fetchone()[0]
        total_existing += existing
        new = fetch_and_store(conn, ticker)
        total_new += new
        time.sleep(0.3)  # 礼貌性延迟

    conn.close()
    print(f"\n{'='*50}")
    print(f"✅ 补全完成！")
    print(f"   本次新增/更新: {total_new} 条")
    print(f"   数据库总记录: {total_existing + total_new} 条")
    print(f"   标的数量: {len(TICKERS)}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
