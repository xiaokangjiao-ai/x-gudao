#!/usr/bin/env python3
"""
x-gudao SSG: 静态网站预生成脚本
每次运行生成所有HTML页面，包括每个ETF的独立详情页
"""
import sys
import json
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# ── 依赖检查 ──────────────────────────────────────────────
try:
    import jinja2
    import yfinance as yf
    import numpy as np
except ImportError as e:
    print(f"[ERROR] 缺少依赖: {e.name}，请运行: pip install jinja2 yfinance numpy")
    sys.exit(1)

# ── 路径设置 ──────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.resolve()
TEMPLATES = ROOT / "templates"
OUTPUT = ROOT / "_site"
WATCHLIST = ROOT / "watchlist.json"
DB_PATH = ROOT / "data" / "market_data.db"

OUTPUT.mkdir(exist_ok=True)


# ── 数据获取 ──────────────────────────────────────────────
def fetch_from_yf(ticker: str, period: str = "5y") -> list:
    """从Yahoo Finance获取历史数据"""
    try:
        df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        if df.empty:
            print(f"  [WARN] {ticker} 无数据")
            return []
        records = []
        for date, row in df.iterrows():
            records.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })
        return records
    except Exception as e:
        print(f"  [ERROR] {ticker}: {e}")
        return []


def fetch_from_db(ticker: str) -> list:
    """从本地SQLite获取数据"""
    if not DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(str(DB_PATH))
        df = conn.execute(
            "SELECT date, open, high, low, close, volume FROM market_data WHERE ticker=? ORDER BY date ASC",
            (ticker,)
        ).fetchall()
        conn.close()
        if not df:
            return []
        return [{"date": r[0], "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]} for r in df]
    except Exception as e:
        print(f"  [DB ERROR] {ticker}: {e}")
        return []


def get_ticker_data(ticker: str, skip_fetch: bool = False) -> dict:
    """
    获取单个标的完整数据（DB优先，YF兜底）
    自动补全：MA20/50/200，年化收益，波动率等
    """
    data = fetch_from_db(ticker)
    source = "db" if data else "yf"
    if not data and not skip_fetch:
        print(f"  [FETCH] {ticker} ← Yahoo Finance (fallback)")
        data = fetch_from_yf(ticker)
    elif data:
        print(f"  [FETCH] {ticker} ← SQLite ({len(data)}条)")
    elif skip_fetch:
        print(f"  [SKIP-FETCH] {ticker} 跳过网络获取")

    if not data:
        return {}

    closes = [d["close"] for d in data]
    latest = data[-1]["close"]
    prev = data[-2]["close"] if len(data) > 1 else latest

    # 年化收益（基于5年或全部数据）
    year_range = (datetime.strptime(data[-1]["date"], "%Y-%m-%d") -
                  datetime.strptime(data[0]["date"], "%Y-%m-%d")).days / 365.25
    if year_range < 0.5:
        year_range = 0.5
    ann_return = round(((latest / data[0]["close"]) ** (1 / year_range) - 1) * 100, 2)

    # 波动率（年化）
    returns = [((closes[i] - closes[i - 1]) / closes[i - 1]) for i in range(1, len(closes))]
    volatility = round(np.std(returns) * np.sqrt(252) * 100, 2) if len(returns) > 1 else 0

    # 最大回撤
    peak = closes[0]
    max_dd = 0
    for price in closes:
        if price > peak:
            peak = price
        dd = (price - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd

    # MA
    def ma_calc(data_list, period):
        result = []
        for i in range(len(data_list)):
            if i < period - 1:
                result.append(None)
            else:
                result.append(round(sum(d["close"] for d in data_list[i - period + 1:i + 1]) / period, 2))
        return result

    ma20_vals = ma_calc(data, 20)
    ma50_vals = ma_calc(data, 50)
    ma200_vals = ma_calc(data, 200)

    closes_1y = closes[-252:] if len(closes) >= 252 else closes
    ann_return_1y = round(((closes[-1] / closes_1y[0]) ** (252 / len(closes_1y)) - 1) * 100, 2) if len(closes_1y) > 1 else 0

    # 52周高低价
    recent = data[-252:] if len(data) >= 252 else data
    high_52w = max(d["high"] for d in recent)
    low_52w = min(d["low"] for d in recent)

    return {
        "ticker": ticker,
        "name": get_ticker_name(ticker),
        "category": get_ticker_category(ticker),
        "data": data,
        "latest_close": round(latest, 2),
        "day_change": round((latest - prev) / prev * 100, 2),
        "annual_return": ann_return,
        "annual_return_1y": ann_return_1y,
        "volatility": volatility,
        "max_drawdown": round(max_dd, 2),
        "sharpe": round(ann_return / volatility, 2) if volatility > 0 else 0,
        "high": round(high_52w, 2),
        "low": round(low_52w, 2),
        "ma20": ma20_vals[-1] if ma20_vals and ma20_vals[-1] else 0,
        "ma50": ma50_vals[-1] if ma50_vals and ma50_vals[-1] else 0,
        "ma200": ma200_vals[-1] if ma200_vals and ma200_vals[-1] else 0,
        "data_points": len(data),
        "date_range": f"{data[0]['date']} ~ {data[-1]['date']}",
        "price_history": data[-252:] if len(data) >= 252 else data,  # 用于首页迷你图
    }


def get_ticker_name(ticker: str) -> str:
    names = {
        "SPY": "SPDR S&P 500 ETF Trust", "IVV": "iShares Core S&P 500 ETF",
        "VOO": "Vanguard S&P 500 ETF", "QQQ": "Invesco QQQ Trust (纳指100)",
        "VTI": "Vanguard Total Stock Market ETF", "VEA": "Vanguard FTSE Developed Markets ETF",
        "VWO": "Vanguard FTSE Emerging Markets ETF", "AGG": "iShares Core US Aggregate Bond ETF",
        "IEFA": "iShares Core MSCI EAFE ETF", "GLD": "SPDR Gold Shares",
    }
    return names.get(ticker, ticker)


def get_ticker_category(ticker: str) -> str:
    cats = {
        "SPY": "美国核心", "IVV": "美国核心", "VOO": "美国核心",
        "QQQ": "美国科技", "VTI": "美国全市场",
        "VEA": "发达市场", "VWO": "新兴市场", "IEFA": "发达市场",
        "AGG": "债券", "GLD": "黄金",
    }
    return cats.get(ticker, "ETF")


def calc_stats(data: list) -> dict:
    closes = [d["close"] for d in data]
    latest = closes[-1]
    prev = closes[-2] if len(closes) > 1 else latest
    recent = data[-252:] if len(data) >= 252 else data
    high = max(d["high"] for d in recent)
    low = min(d["low"] for d in recent)

    year_range = max((datetime.strptime(data[-1]["date"], "%Y-%m-%d") -
                       datetime.strptime(data[0]["date"], "%Y-%m-%d")).days / 365.25, 0.5)
    ann_ret = round(((latest / data[0]["close"]) ** (1 / year_range) - 1) * 100, 2)
    returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
    vol = round(np.std(returns) * np.sqrt(252) * 100, 2) if len(returns) > 1 else 0

    closes_1y = closes[-252:] if len(closes) >= 252 else closes
    ret_1y = round(((closes[-1] / closes_1y[0]) ** (252 / len(closes_1y)) - 1) * 100, 2) if len(closes_1y) > 1 else 0

    def ma(d, p):
        r = []
        for i in range(len(d)):
            r.append(round(sum(d[j]["close"] for j in range(max(0, i - p + 1), i + 1)) / min(p, i + 1), 2)) if i >= p - 1 else r.append(None)
        return r

    ma20 = ma(data, 20)
    ma50 = ma(data, 50)
    ma200 = ma(data, 200)

    return {
        "high": round(high, 2),
        "low": round(low, 2),
        "annual_return": ann_ret,
        "annual_return_1y": ret_1y,
        "day_change": round((latest - prev) / prev * 100, 2),
        "volatility": vol,
        "ma20": ma20[-1] if ma20[-1] else 0,
        "ma50": ma50[-1] if ma50[-1] else 0,
        "ma200": ma200[-1] if ma200[-1] else 0,
        "data_points": len(data),
        "date_range": f"{data[0]['date']} ~ {data[-1]['date']}",
    }


# ── 页面生成 ──────────────────────────────────────────────
def build_index_page(tickers_data: list) -> str:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATES)))
    tmpl = env.get_template("index.html")
    overview = [{
        "ticker": d["ticker"],
        "name": d["name"],
        "category": d["category"],
        "latest_close": d["latest_close"],
        "change_pct": d["day_change"],
        "annual_return": d["annual_return"],
        "volatility": d["volatility"],
        "high": d["high"],
        "low": d["low"],
        "data_points": d["data_points"],
        "price_history": d["price_history"],
    } for d in tickers_data]
    return tmpl.render(overview_data=json.dumps(overview, ensure_ascii=False))


def build_ticker_page(ticker_data: dict, all_tickers_data: list) -> str:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATES)))
    tmpl = env.get_template("stock.html")

    # 每个详情页显示与其他基金的对比（用年化收益对比）
    compare = [{
        "ticker": d["ticker"],
        "name": d["name"],
        "price": d["latest_close"],
        "return": d["annual_return"],
    } for d in all_tickers_data if d["ticker"] != ticker_data["ticker"]][:6]

    stats = {
        "high": ticker_data["high"],
        "low": ticker_data["low"],
        "annual_return": ticker_data["annual_return"],
        "day_change": ticker_data["day_change"],
        "volatility": ticker_data["volatility"],
        "ma20": ticker_data["ma20"],
        "ma50": ticker_data["ma50"],
        "ma200": ticker_data["ma200"],
        "data_points": ticker_data["data_points"],
        "date_range": ticker_data["date_range"],
    }

    return tmpl.render(
        ticker=ticker_data["ticker"],
        name=ticker_data["name"],
        category=ticker_data["category"],
        latest_close=ticker_data["latest_close"],
        stats=stats,
        chart_data=json.dumps(ticker_data["data"], ensure_ascii=False),
        latest_data=json.dumps({"close": ticker_data["latest_close"], "change": ticker_data["day_change"]}, ensure_ascii=False),
        compare_data=json.dumps(compare, ensure_ascii=False),
    )


def build_compare_page(all_tickers_data: list) -> str:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATES)))
    tmpl = env.get_template("compare.html")
    return tmpl.render(all_data=json.dumps([{
        "ticker": d["ticker"],
        "name": d["name"],
        "data": d["data"],
        "latest_close": d["latest_close"],
        "annual_return": d["annual_return"],
        "volatility": d["volatility"],
        "max_drawdown": d["max_drawdown"],
        "sharpe": d["sharpe"],
    } for d in all_tickers_data], ensure_ascii=False))


# ── 主流程 ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="x-gudao SSG 静态网站生成器")
    parser.add_argument("--tickers", nargs="*", help="指定标的列表（覆盖watchlist.json）")
    parser.add_argument("--skip-fetch", action="store_true", help="跳过数据获取，直接用DB现有数据")
    args = parser.parse_args()

    # 读取标的列表
    if args.tickers:
        tickers = args.tickers
    elif WATCHLIST.exists():
        wl = json.loads(WATCHLIST.read_text(encoding="utf-8"))
        tickers = wl.get("tickers", [])
    else:
        print("[ERROR] 找不到 watchlist.json")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"x-gudao SSG 静态网站生成器")
    print(f"标的数量: {len(tickers)}")
    print(f"输出目录: {OUTPUT}")
    print(f"{'='*50}\n")

    # 获取所有数据
    all_data = []
    for ticker in tickers:
        print(f"[{tickers.index(ticker) + 1}/{len(tickers)}] {ticker}")
        data = get_ticker_data(ticker, skip_fetch=args.skip_fetch)
        if data:
            all_data.append(data)
        else:
            print(f"  [SKIP] {ticker} 无数据，跳过")

    if not all_data:
        print("[ERROR] 没有获取到任何数据")
        sys.exit(1)

    print(f"\n✅ 成功获取 {len(all_data)} 个标的\n")

    # 生成各页面
    print("[1/4] 生成首页 index.html ...")
    index_html = build_index_page(all_data)
    (OUTPUT / "index.html").write_text(index_html, encoding="utf-8")

    print("[2/4] 生成对比页 compare.html ...")
    compare_html = build_compare_page(all_data)
    (OUTPUT / "compare.html").write_text(compare_html, encoding="utf-8")

    print("[3/4] 生成基金列表页 screener.html ...")
    # screener 和 index 一样，只是去掉迷你图
    (OUTPUT / "screener.html").write_text(index_html, encoding="utf-8")  # 复用

    print("[4/4] 生成各基金详情页 ...")
    for d in all_data:
        ticker_dir = OUTPUT / d["ticker"].lower()
        ticker_dir.mkdir(exist_ok=True)
        page_html = build_ticker_page(d, all_data)
        (ticker_dir / "index.html").write_text(page_html, encoding="utf-8")
        print(f"  ✓ {d['ticker']}/index.html")

    # 生成 overview.json（供其他用途）
    overview = [{
        "ticker": d["ticker"],
        "name": d["name"],
        "category": d["category"],
        "latest_close": d["latest_close"],
        "change_pct": d["day_change"],
        "annual_return": d["annual_return"],
        "annual_return_1y": d["annual_return_1y"],
        "volatility": d["volatility"],
        "high": d["high"],
        "low": d["low"],
        "data_points": d["data_points"],
        "date_range": d["date_range"],
        "ma20": d["ma20"],
        "ma50": d["ma50"],
        "ma200": d["ma200"],
    } for d in all_data]
    (OUTPUT / "overview.json").write_text(json.dumps(overview, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*50}")
    print(f"✅ 生成完成！共 {len(all_data)} 个页面")
    print(f"📁 输出: {OUTPUT}")
    print(f"   首页: {OUTPUT / 'index.html'}")
    print(f"   对比: {OUTPUT / 'compare.html'}")
    for d in all_data:
        print(f"   {d['ticker']}: {OUTPUT / d['ticker'].lower() / 'index.html'}")
    print(f"{'='*50}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
