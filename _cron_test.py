import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')
from massive_fetcher import fetch_daily, log_sync, init_db, SYMBOLS, MIN_INTERVAL
import sqlite3, time

conn = init_db()
total = 0
errors = []
for i, ticker in enumerate(SYMBOLS):
    print(f"[{i+1}/{len(SYMBOLS)}] {ticker}", flush=True)
    try:
        saved, started = fetch_daily(ticker)
        if saved > 0:
            total += saved
            log_sync(conn, ticker, 'daily', saved, started)
            print(f"  +{saved} 条", flush=True)
        else:
            print(f"  无新数据", flush=True)
    except Exception as e:
        errors.append(f"{ticker}: {e}")
        print(f"  错误: {e}", flush=True)
    if i < len(SYMBOLS) - 1:
        print(f"  等待 {MIN_INTERVAL}s...", flush=True)
        time.sleep(MIN_INTERVAL)

conn.close()
print(f"\n完成! 共获取 {total} 条新记录", flush=True)
if errors:
    print(f"出错: {errors}", flush=True)
