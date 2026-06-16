"""
x-gudao 数据同步模块
从 Massive API 获取市场数据，存入本地 SQLite
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import sqlite3
import time
import yaml
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ── 全局配置 ──────────────────────────────────────────────
API_KEY = "naRnrOfu3bs7fuhOdpczaUpkpNafsN3g"
BASE_URL = "https://api.polygon.io"
MIN_INTERVAL = 15  # 免费套餐：每分钟5次 → 每次间隔≥15秒

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "market_data.db"

# 30个标的（按优先级分组，控制请求顺序）
SYMBOLS = [
    # ETF（最重要，先拉）
    "VOO", "QQQ", "SPY", "VTI", "IWM", "GLD", "TLT", "BND",
    # 科技巨头
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "JPM", "V", "MA",
    # 大宗商品
    "GC", "SI", "CL", "HG",
    # 债券指数
    "^TNX", "^TYX", "^IRX",
]


# ── 数据库 ────────────────────────────────────────────────
def init_db():
    """初始化 SQLite 数据库"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            ticker      TEXT    NOT NULL,
            date        TEXT    NOT NULL,  -- YYYY-MM-DD
            open        REAL,
            high        REAL,
            low         REAL,
            close       REAL,
            volume      INTEGER,
            updated_at  TEXT    NOT NULL,
            PRIMARY KEY (ticker, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker     TEXT,
            sync_type  TEXT,   -- 'full' | 'daily'
            records    INTEGER,
            started_at TEXT,
            finished_at TEXT,
            error      TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ticker_date
        ON market_data(ticker, date)
    """)
    conn.commit()
    return conn


def get_last_date(conn: sqlite3.Connection, ticker: str) -> Optional[str]:
    """获取某标的最新的已存储日期"""
    cur = conn.execute(
        "SELECT MAX(date) FROM market_data WHERE ticker = ?", (ticker,)
    )
    row = cur.fetchone()
    return row[0] if row and row[0] else None


def upsert_rows(conn: sqlite3.Connection, ticker: str, rows: list):
    """批量插入/更新数据"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = [
        (ticker, r["date"], r.get("o"), r.get("h"), r.get("l"), r.get("c"), r.get("v"), now)
        for r in rows
    ]
    conn.executemany("""
        INSERT INTO market_data (ticker, date, open, high, low, close, volume, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ticker, date) DO UPDATE SET
            open=excluded.open, high=excluded.high, low=excluded.low,
            close=excluded.close, volume=excluded.volume, updated_at=excluded.updated_at
    """, data)
    conn.commit()


def log_sync(conn: sqlite3.Connection, ticker: str, sync_type: str,
            records: int, started_at: str, error: Optional[str] = None):
    conn.execute("""
        INSERT INTO sync_log (ticker, sync_type, records, started_at, finished_at, error)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ticker, sync_type, records, started_at, datetime.now().isoformat(), error))
    conn.commit()


# ── Massive API ────────────────────────────────────────────
def fetch_ohlcv(ticker: str, from_date: str, to_date: str,
                adjusted: bool = True) -> tuple[list, str]:
    """
    获取指定日期范围的日K数据
    返回: (rows, status)
    rows = [{'date':'YYYY-MM-DD', 'o':float, 'h':float, 'l':float, 'c':float, 'v':int}, ...]
    status = 'OK' | 'DELAYED' | 'NEXT_PAGE' | 'ERROR'
    """
    url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}"
    params = {
        "adjusted": "true" if adjusted else "false",
        "sort": "asc",
        "limit": 50000,
        "apiKey": API_KEY,
    }
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code == 429:
        return [], "RATE_LIMITED"
    if resp.status_code != 200:
        return [], f"HTTP_{resp.status_code}"

    data = resp.json()
    if data.get("status") in ("ERROR", "NOT_FOUND"):
        return [], f"ERROR:{data.get('error', 'unknown')}"

    rows = []
    for bar in data.get("results", []):
        # timestamp 是毫秒UTC，转 YYYY-MM-DD（北京时间）
        ts_sec = bar["t"] / 1000
        dt_utc = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
        # 转北京时间（UTC+8）
        dt_cst = dt_utc + timedelta(hours=8)
        rows.append({
            "date": dt_cst.strftime("%Y-%m-%d"),
            "o": round(bar.get("o", 0), 4),
            "h": round(bar.get("h", 0), 4),
            "l": round(bar.get("l", 0), 4),
            "c": round(bar.get("c", 0), 4),
            "v": bar.get("v", 0),
        })

    status = data.get("status", "OK")
    return rows, status


def fetch_full_history(ticker: str, years: int = 5) -> tuple[int, str]:
    """
    获取单个标的全量历史数据（5年，分段请求）
    返回: (records_saved, status_msg)
    """
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=365 * years)).strftime("%Y-%m-%d")

    started = datetime.now().isoformat()
    total_saved = 0

    # 拆分请求窗口（每段约500条 ≈ 2年交易日）
    segments = [
        # (from, to)
        (from_date, "2022-01-01"),
        ("2022-01-01", "2024-01-01"),
        ("2024-01-01", to_date),
    ]

    for seg_from, seg_to in segments:
        rows, status = fetch_ohlcv(ticker, seg_from, seg_to)
        if status == "RATE_LIMITED":
            # 等待一分钟后重试
            print(f"  ⏳ 限流等待60秒...")
            time.sleep(60)
            rows, status = fetch_ohlcv(ticker, seg_from, seg_to)
        if status.startswith("ERROR") or status == "RATE_LIMITED":
            print(f"  ⚠️  [{ticker}] {seg_from}~{seg_to}: {status}")
            continue

        if rows:
            conn = init_db()
            upsert_rows(conn, ticker, rows)
            conn.close()
            total_saved += len(rows)
            print(f"  ✅ [{ticker}] {seg_from}~{seg_to}: +{len(rows)} 条")

        # 限流保护：每次请求间隔
        time.sleep(MIN_INTERVAL)

    return total_saved, started


def fetch_daily(ticker: str) -> tuple[int, str]:
    """
    获取最近一个交易日的数据（增量更新）
    返回: (records_saved, status_msg)
    """
    conn = init_db()
    last_date = get_last_date(conn, ticker)
    conn.close()

    # 从上次最后日期的下一天开始取
    if last_date:
        from_date = (datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        # 没数据则取近30天
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    to_date = datetime.now().strftime("%Y-%m-%d")
    started = datetime.now().isoformat()

    rows, status = fetch_ohlcv(ticker, from_date, to_date)
    if status == "RATE_LIMITED":
        return 0, "RATE_LIMITED"
    if not rows or status.startswith("ERROR"):
        return 0, status

    conn = init_db()
    upsert_rows(conn, ticker, rows)
    conn.close()

    return len(rows), started


# ── CLI 入口 ───────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="x-gudao 数据同步")
    parser.add_argument("--mode", choices=["full", "daily", "test"], default="daily",
                        help="full=5年全量, daily=增量更新, test=测试单标的")
    parser.add_argument("--ticker", default=None, help="指定单个标的（test模式用）")
    parser.add_argument("--symbols", default=None, help="逗号分隔标的列表")
    args = parser.parse_args()

    # 选择标的范围
    if args.ticker:
        tickers = [args.ticker]
    elif args.symbols:
        tickers = [s.strip() for s in args.symbols.split(",")]
    else:
        tickers = SYMBOLS

    print(f"[x-gudao sync] 模式: {args.mode} | 标的: {len(tickers)} 个")
    print(f"[x-gudao sync] 数据库: {DB_PATH}")
    print("─" * 50)

    conn = init_db()

    if args.mode == "test":
        ticker = args.ticker or "VOO"
        print(f"\n🧪 测试: {ticker}")
        rows, status = fetch_ohlcv(ticker, "2026-01-01", "2026-06-16")
        print(f"状态: {status} | 条数: {len(rows)}")
        if rows:
            print(f"最新: {rows[-1]}")
        return

    total_records = 0
    errors = []

    for i, ticker in enumerate(tickers):
        print(f"\n[{i+1}/{len(tickers)}] 📈 {ticker}")
        try:
            if args.mode == "full":
                saved, started = fetch_full_history(ticker, years=5)
            else:
                saved, started = fetch_daily(ticker)

            if saved > 0:
                total_records += saved
                log_sync(conn, ticker, args.mode, saved, started)
                print(f"  📊 累计: +{saved} 条")
            else:
                print(f"  ℹ️  无新数据（或出错: {saved}）")
        except Exception as e:
            errors.append(f"{ticker}: {e}")
            print(f"  ❌ 错误: {e}")
            log_sync(conn, ticker, args.mode, 0, started or "", error=str(e))

        # 每请求间隔（最后一轮不必等）
        if i < len(tickers) - 1:
            print(f"  ⏳ 等待 {MIN_INTERVAL}s（限流保护）...")
            time.sleep(MIN_INTERVAL)

    conn.close()
    print(f"\n✅ 完成！共获取 {total_records} 条新记录")
    if errors:
        print(f"❌ 出错: {errors}")


if __name__ == "__main__":
    main()