"""
x-gudao SQLite 本地缓存读取器
优先从本地 SQLite 读取，缺失时返回 None 由调用方 fallback 到网络
"""
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

DB_PATH = Path(__file__).parent.parent / "data" / "market_data.db"

# period → 日期边界
PERIOD_BOUNDS = {
    "1mo":  30,
    "3mo":  90,
    "6mo":  180,
    "1y":   365,
    "2y":   730,
    "5y":   1825,
    "10y":  3650,
    "max":  99999,
}


def get_db_conn():
    if not DB_PATH.exists():
        return None
    return sqlite3.connect(DB_PATH)


def fetch_from_db(symbol: str, period: str = "5y") -> Optional[pd.DataFrame]:
    """
    从 SQLite 读取指定标的的历史数据
    返回 DataFrame 或 None（库为空/不存在）
    """
    conn = get_db_conn()
    if conn is None:
        return None

    try:
        days = PERIOD_BOUNDS.get(period, 1825)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        df = pd.read_sql("""
            SELECT date, open, high, low, close, volume
            FROM market_data
            WHERE ticker = ?
              AND date >= ?
            ORDER BY date ASC
        """, conn, params=(symbol, cutoff))

        if df.empty:
            return None

        # 类型转换
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        # 日收益率
        df["daily_return"] = df["close"].pct_change().fillna(0)

        return df

    finally:
        conn.close()


def get_latest_date(symbol: str) -> Optional[str]:
    """获取某标的最新的已存储日期"""
    conn = get_db_conn()
    if conn is None:
        return None
    try:
        cur = conn.execute(
            "SELECT MAX(date) FROM market_data WHERE ticker = ?", (symbol,)
        )
        row = cur.fetchone()
        return row[0] if row and row[0] else None
    finally:
        conn.close()


def get_db_stats() -> dict:
    """数据库统计信息"""
    conn = get_db_conn()
    if conn is None:
        return {"status": "empty", "tickers": 0, "records": 0}

    try:
        cur = conn.execute("SELECT COUNT(DISTINCT ticker), COUNT(*) FROM market_data")
        row = cur.fetchone()
        tickers, records = row[0] or 0, row[1] or 0

        cur = conn.execute("SELECT MAX(date), MIN(date) FROM market_data")
        row = cur.fetchone()

        return {
            "status": "ok",
            "tickers": tickers,
            "records": records,
            "latest_date": row[0],
            "earliest_date": row[1],
            "db_path": str(DB_PATH),
        }
    finally:
        conn.close()