#!/usr/bin/env python3
"""批量拉取16标的5年数据 → SQLite（yfinance.download 批量模式）"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import sqlite3
from pathlib import Path
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    print("[ERROR] 缺少 yfinance"); sys.exit(1)

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

def main():
    print(f"\n{'='*50}")
    print(f"批量拉取 16标的 × 5年数据")
    print(f"{'='*50}\n")

    # Step 1: 批量下载
    print("[1/3] 正在从 Yahoo Finance 批量下载（可能需要1-2分钟）...")
    try:
        df = yf.download(TICKERS, period="5y", auto_adjust=True, group_by="ticker", threads=True)
        print(f"  ✅ 下载完成，shape: {df.shape}")
    except Exception as e:
        print(f"  ❌ 下载失败: {e}")
        # fallback: 逐个下载
        print("  尝试逐个下载...")
        dfs = {}
        for t in TICKERS:
            try:
                dfs[t] = yf.Ticker(t).history(period="5y", auto_adjust=True)
                print(f"  ✅ {t}: {len(dfs[t])} rows")
                time.sleep(2)
            except Exception as e2:
                print(f"  ❌ {t}: {e2}")
        if not dfs:
            print("[FATAL] 所有下载均失败"); sys.exit(1)
        # 合并
        import pandas as pd
        all_tickers = list(dfs.keys())
        df = pd.concat(dfs, axis=0)
        print(f"  ✅ 逐个下载完成，total shape: {df.shape}")

    # Step 2: 写入 SQLite
    print("\n[2/3] 写入 SQLite...")
    conn = init_db()
    now = datetime.now().isoformat()
    total = 0

    if isinstance(df.columns, pd.MultiIndex):
        # group_by='ticker' 格式
        for ticker in TICKERS:
            try:
                sub = df[ticker].dropna()
                if sub.empty:
                    print(f"  ⚠️ {ticker}: 无数据")
                    continue
                count = 0
                for date, row in sub.iterrows():
                    d = date.strftime("%Y-%m-%d")
                    conn.execute("""INSERT OR REPLACE INTO market_data
                        (ticker, date, open, high, low, close, volume, updated_at)
                        VALUES (?,?,?,?,?,?,?,?)""",
                        (ticker, d, round(float(row["Open"]),4), round(float(row["High"]),4),
                         round(float(row["Low"]),4), round(float(row["Close"]),4),
                         int(row["Volume"]), now))
                    count += 1
                conn.commit()
                total += count
                print(f"  ✅ {ticker}: {count} rows")
            except Exception as e:
                print(f"  ❌ {ticker}: {e}")
    else:
        print("  ⚠️ 意外的数据格式，跳过写入")

    conn.close()

    # Step 3: 验证
    print(f"\n[3/3] 验证数据...")
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT ticker, COUNT(*), MIN(date), MAX(date) FROM market_data GROUP BY ticker ORDER BY ticker").fetchall()
    print(f"\n{'Ticker':<8} {'Count':>6} {'From':>12} {'To':>12}")
    print('-'*42)
    grand = 0
    for r in rows:
        print(f'{r[0]:<8} {r[1]:>6} {r[2]:>12} {r[3]:>12}')
        grand += r[1]
    print('-'*42)
    print(f'Total: {grand} records')
    conn.close()

    print(f"\n✅ 完成！共写入 {total} 条记录")

if __name__ == "__main__":
    main()
