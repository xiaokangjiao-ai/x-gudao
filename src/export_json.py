"""
静态 JSON 生成器 - 为 x-gudao 站点生成每个标的的独立数据文件。
不依赖 app.py，可独立运行。
"""
import sqlite3
import json
import yaml
from pathlib import Path
from datetime import datetime, timezone

# ── 路径配置 ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH      = PROJECT_ROOT / "data" / "market_data.db"
CONFIG_PATH  = PROJECT_ROOT / "config" / "api_config.yaml"
OUTPUT_DIR   = PROJECT_ROOT / "output"

TZ = timezone(datetime.now().astimezone().utcoffset())  # Asia/Shanghai


def load_symbols():
    """从 api_config.yaml 读取标的清单。"""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return {s["ticker"]: s for s in config["symbols"]}


def export_ticker_json(conn, ticker: str, symbol_info: dict) -> dict | None:
    """为单个标的生成 JSON 文件，返回该标的的统计摘要。"""
    cur = conn.cursor()
    cur.execute(
        "SELECT date, open, high, low, close, volume "
        "FROM market_data "
        "WHERE ticker = ? "
        "ORDER BY date ASC",
        (ticker,),
    )
    rows = cur.fetchall()
    if not rows:
        return None

    data = [
        {
            "date":   r[0],
            "open":   round(float(r[1]), 2),
            "high":   round(float(r[2]), 2),
            "low":    round(float(r[3]), 2),
            "close":  round(float(r[4]), 2),
            "volume": int(float(r[5])),
        }
        for r in rows
    ]

    generated_at = datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S%z")
    if not generated_at.endswith("+0800"):
        generated_at = generated_at[:-2] + "+0800"   # 标准化格式

    payload = {
        "ticker":      ticker,
        "name":        symbol_info.get("name", ""),
        "category":    symbol_info.get("category", ""),
        "data":        data,
        "generated_at": generated_at,
    }

    out_path = OUTPUT_DIR / f"{ticker}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # 统计摘要
    latest  = data[-1]
    first   = data[0]
    prices  = [d["close"] for d in data]
    summary = {
        "ticker":          ticker,
        "name":            symbol_info.get("name", ""),
        "category":        symbol_info.get("category", ""),
        "latest_date":     latest["date"],
        "latest_close":    latest["close"],
        "latest_volume":   latest["volume"],
        "change":          round(latest["close"] - first["close"], 2),
        "change_pct":      round((latest["close"] - first["close"]) / first["close"] * 100, 2),
        "52w_high":        round(max(prices), 2),
        "52w_low":         round(min(prices), 2),
        "data_points":     len(data),
    }
    return summary


def build_overview(conn, symbol_map: dict) -> dict:
    """生成所有标的的聚合概览 JSON。"""
    cur = conn.cursor()
    overviews = []

    for ticker, info in symbol_map.items():
        cur.execute(
            "SELECT date, open, high, low, close, volume "
            "FROM market_data WHERE ticker = ? ORDER BY date ASC",
            (ticker,),
        )
        rows = cur.fetchall()
        if not rows:
            continue

        prices = [float(r[4]) for r in rows]
        latest = rows[-1]
        first  = rows[0]

        overviews.append({
            "ticker":        ticker,
            "name":          info.get("name", ""),
            "category":      info.get("category", ""),
            "latest_date":   latest[0],
            "latest_close":  round(float(latest[4]), 2),
            "latest_volume": int(float(latest[5])),
            "change":        round(float(latest[4]) - float(first[4]), 2),
            "change_pct":    round((float(latest[4]) - float(first[4])) / float(first[4]) * 100, 2),
            "52w_high":      round(max(prices), 2),
            "52w_low":       round(min(prices), 2),
            "data_points":   len(rows),
        })

    generated_at = datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    return {
        "generated_at": generated_at,
        "total_tickers": len(overviews),
        "tickers":       overviews,
    }


def run():
    """主入口。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    symbol_map = load_symbols()
    print(f"Loaded {len(symbol_map)} symbols from api_config.yaml")

    conn = sqlite3.connect(DB_PATH)
    summaries = []
    skipped   = []

    for ticker, info in symbol_map.items():
        summary = export_ticker_json(conn, ticker, info)
        if summary:
            summaries.append(summary)
            print(f"  [OK] {ticker}: {summary['data_points']} rows, "
                  f"latest={summary['latest_close']}, "
                  f"52w [{summary['52w_low']}, {summary['52w_high']}]")
        else:
            skipped.append(ticker)
            print(f"  [SKIP] {ticker}: no data in DB")

    # overview
    overview = build_overview(conn, symbol_map)
    overview_path = OUTPUT_DIR / "overview.json"
    with open(overview_path, "w", encoding="utf-8") as f:
        json.dump(overview, f, ensure_ascii=False, indent=2)
    print(f"\nOverview: {overview_path} ({overview_path.stat().st_size} bytes)")

    conn.close()

    print(f"\nDone. {len(summaries)} files written, {len(skipped)} skipped.")
    if skipped:
        print(f"   Skipped (no DB data): {skipped}")

    return summaries, skipped


if __name__ == "__main__":
    run()