# -*- coding: utf-8 -*-
"""
x-gudao SSG: 静态网站预生成脚本
集成了评级系统的完整版
每次运行生成所有HTML页面，包括每个标的的独立详情页
"""
import sys
import json
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

# ── 依赖检查 ──────────────────────────────────────────────
try:
    import jinja2
    import numpy as np
except ImportError as e:
    print(f"[ERROR] 缺少依赖: {e.name}，请运行: pip install jinja2 numpy")
    sys.exit(1)

# ── 导入评级模块 ──────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from ratings import (
    compute_all_ratings, INVESTMENT_RATIONALE, get_top3
)

# ── 路径设置 ──────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.resolve()
TEMPLATES = ROOT / "templates"
OUTPUT = ROOT / "_site"
WATCHLIST = ROOT / "watchlist.json"
DB_PATH = ROOT / "data" / "market_data.db"

OUTPUT.mkdir(exist_ok=True)


# ── 数据获取（从 SQLite）──────────────────────────────────
def fetch_from_db(ticker: str) -> list:
    """从本地SQLite获取数据（DB优先）"""
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


def get_ticker_data(ticker: str) -> dict:
    """
    获取单个标的完整数据
    自动补全：MA20/50/200，年化收益，波动率等
    """
    data = fetch_from_db(ticker)
    if not data:
        print(f"  [WARN] {ticker} 无数据")
        return {}

    closes = [d["close"] for d in data]
    latest = data[-1]["close"]
    prev = data[-2]["close"] if len(data) > 1 else latest

    # 年化收益
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

    # MA 计算（优雅降级）
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

    # Sharpe
    sharpe = round(ann_return / volatility, 2) if volatility > 0 else 0

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
        "sharpe": sharpe,
        "high": round(high_52w, 2),
        "low": round(low_52w, 2),
        "ma20": ma20_vals[-1] if ma20_vals and ma20_vals[-1] else 0,
        "ma50": ma50_vals[-1] if ma50_vals and ma50_vals[-1] else 0,
        "ma200": ma200_vals[-1] if ma200_vals and ma200_vals[-1] else 0,
        "data_points": len(data),
        "date_range": f"{data[0]['date']} ~ {data[-1]['date']}",
        "price_history": data[-252:] if len(data) >= 252 else data,  # 首页迷你图
    }


def get_ticker_name(ticker: str) -> str:
    names = {
        "VOO": "Vanguard S&P 500 ETF",
        "QQQ": "Invesco QQQ Trust (纳指100)",
        "IWM": "iShares Russell 2000 ETF",
        "BND": "Vanguard Total Bond Market ETF",
        "GLD": "SPDR Gold Shares",
        "SCHD": "Schwab U.S. Dividend Equity ETF",
        "VXUS": "Vanguard Total International Stock ETF",
        "SMH": "VanEck Semiconductor ETF",
        "NVDA": "NVIDIA Corporation",
        "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corporation",
        "GOOGL": "Alphabet Inc.",
        "AMZN": "Amazon.com Inc.",
        "META": "Meta Platforms Inc.",
        "LLY": "Eli Lilly and Company",
        "BRK.B": "Berkshire Hathaway Inc.",
    }
    return names.get(ticker, ticker)


def get_ticker_category(ticker: str) -> str:
    cats = {
        "VOO": "美国大盘", "QQQ": "美国科技", "IWM": "美国小盘",
        "BND": "债券", "GLD": "黄金",
        "SCHD": "高股息", "VXUS": "全球(除美)", "SMH": "半导体",
        "NVDA": "半导体", "AAPL": "消费电子", "MSFT": "软件",
        "GOOGL": "互联网", "AMZN": "电商云计算",
        "META": "社交媒体", "LLY": "医疗健康", "BRK.B": "综合控股",
    }
    return cats.get(ticker, "其他")


# ── 页面生成 ──────────────────────────────────────────────
def build_index_page(tickers_data: list, ratings: list) -> str:
    """生成首页（三段式布局 + 评级）"""
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATES)))
    tmpl = env.get_template("index.html")

    # overview_data（保留迷你图数据）
    overview = [{
        "ticker": d["ticker"],
        "name": d["name"],
        "category": d["category"],
        "latest_close": d["latest_close"],
        "change_pct": d["day_change"],
        "annual_return": d["annual_return"],
        "volatility": d["volatility"],
        "max_drawdown": d["max_drawdown"],
        "sharpe": d["sharpe"],
        "high": d["high"],
        "low": d["low"],
        "data_points": d["data_points"],
        "price_history": d["price_history"],
        "ma20": d["ma20"],
        "ma50": d["ma50"],
        "ma200": d["ma200"],
    } for d in tickers_data]

    # 合并评级数据到 overview（包含 exchange 字段）
    rating_map = {r["ticker"]: r for r in ratings}
    for o in overview:
        rating = rating_map.get(o["ticker"], {})
        o.update(rating)
        # 确保 exchange 字段存在（用于外链生成）
        if "exchange" not in o:
            # 默认 exchange 映射
            exchange_map = {
                "VOO": "AMEX", "QQQ": "NASDAQ", "IWM": "AMEX",
                "BND": "AMEX", "GLD": "AMEX",
                "SCHD": "AMEX", "VXUS": "AMEX", "SMH": "AMEX",
                "NVDA": "NASDAQ", "AAPL": "NASDAQ", "MSFT": "NASDAQ",
                "GOOGL": "NASDAQ", "AMZN": "NASDAQ", "META": "NASDAQ",
                "LLY": "NYSE", "BRK.B": "NYSE",
            }
            o["exchange"] = exchange_map.get(o["ticker"], "NASDAQ")

    # 按评级分数降序
    overview.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Top3
    top3 = overview[:3]

    return tmpl.render(
        overview_data=json.dumps(overview, ensure_ascii=False),
        top3_data=json.dumps(top3, ensure_ascii=False),
        ratings_data=json.dumps(ratings, ensure_ascii=False),
    )


def build_ticker_page(ticker_data: dict, all_tickers_data: list, rating: dict) -> str:
    """生成标的详情页（集成评级 + 外链）"""
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATES)))
    tmpl = env.get_template("stock.html")

    # 与其他标的对比（按年化收益排序的前6个）
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
        "max_drawdown": ticker_data["max_drawdown"],
        "sharpe": ticker_data["sharpe"],
        "ma20": ticker_data["ma20"],
        "ma50": ticker_data["ma50"],
        "ma200": ticker_data["ma200"],
        "data_points": ticker_data["data_points"],
        "date_range": ticker_data["date_range"],
    }

    rationale = INVESTMENT_RATIONALE.get(ticker_data["ticker"], "")

    return tmpl.render(
        ticker=ticker_data["ticker"],
        name=ticker_data["name"],
        category=ticker_data["category"],
        latest_close=ticker_data["latest_close"],
        stats=stats,
        chart_data=json.dumps(ticker_data["data"], ensure_ascii=False),
        latest_data=json.dumps({"close": ticker_data["latest_close"], "change": ticker_data["day_change"]}, ensure_ascii=False),
        compare_data=json.dumps(compare, ensure_ascii=False),
        rating=rating,
        rationale=rationale,
    )


def build_compare_page(all_tickers_data: list, ratings: list) -> str:
    """生成对比页"""
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATES)))
    tmpl = env.get_template("compare.html")
    rating_map = {r["ticker"]: r for r in ratings}
    return tmpl.render(all_data=json.dumps([{
        "ticker": d["ticker"],
        "name": d["name"],
        "data": d["data"],
        "latest_close": d["latest_close"],
        "annual_return": d["annual_return"],
        "volatility": d["volatility"],
        "max_drawdown": d["max_drawdown"],
        "sharpe": d["sharpe"],
        **rating_map.get(d["ticker"], {}),
    } for d in all_tickers_data], ensure_ascii=False))


# ── 主流程 ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="x-gudao SSG 静态网站生成器（含评级）")
    parser.add_argument("--tickers", nargs="*", help="指定标的列表")
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
    print(f"x-gudao SSG 静态网站生成器（含评级系统）")
    print(f"标的数量: {len(tickers)}")
    print(f"输出目录: {OUTPUT}")
    print(f"{'='*50}\n")

    # ── 步骤1: 计算评级（不需要完整数据，只用收盘价）───────────
    print("[STEP 1] 计算评级 ...")
    ratings = compute_all_ratings(tickers)
    print(f"  ✓ 完成 {len(ratings)} 个评级，Top3: {[r['ticker'] for r in get_top3(ratings)]}\n")

    # ── 步骤2: 获取完整数据 ───────────────────────────────────
    print("[STEP 2] 获取完整数据 ...")
    all_data = []
    for ticker in tickers:
        print(f"  [{tickers.index(ticker) + 1}/{len(tickers)}] {ticker}")
        data = get_ticker_data(ticker)
        if data:
            all_data.append(data)
        else:
            print(f"    [SKIP] 无数据")

    if not all_data:
        print("[ERROR] 没有获取到任何数据")
        sys.exit(1)

    print(f"\n  ✅ 成功处理 {len(all_data)} 个标的\n")

    # ── 步骤3: 生成页面 ───────────────────────────────────────
    print("[STEP 3] 生成页面 ...")
    print("  [3.1] 生成首页 index.html ...")
    index_html = build_index_page(all_data, ratings)
    (OUTPUT / "index.html").write_text(index_html, encoding="utf-8")

    print("  [3.2] 生成对比页 compare.html ...")
    compare_html = build_compare_page(all_data, ratings)
    (OUTPUT / "compare.html").write_text(compare_html, encoding="utf-8")

    print("  [3.3] 生成基金列表页 screener.html ...")
    (OUTPUT / "screener.html").write_text(index_html, encoding="utf-8")

    print("  [3.4] 生成各标的详情页 ...")
    rating_map = {r["ticker"]: r for r in ratings}
    for d in all_data:
        ticker_dir = OUTPUT / d["ticker"].lower()
        ticker_dir.mkdir(exist_ok=True)
        rating = rating_map.get(d["ticker"], {})
        page_html = build_ticker_page(d, all_data, rating)
        (ticker_dir / "index.html").write_text(page_html, encoding="utf-8")
        print(f"    ✓ {d['ticker']}/index.html")

    # ── 步骤4: 生成 overview.json（含评级）──────────────────────
    rating_map2 = {r["ticker"]: r for r in ratings}
    overview = [{
        "ticker": d["ticker"],
        "name": d["name"],
        "category": d["category"],
        "latest_close": d["latest_close"],
        "change_pct": d["day_change"],
        "annual_return": d["annual_return"],
        "annual_return_1y": d["annual_return_1y"],
        "volatility": d["volatility"],
        "max_drawdown": d["max_drawdown"],
        "sharpe": d["sharpe"],
        "high": d["high"],
        "low": d["low"],
        "data_points": d["data_points"],
        "date_range": d["date_range"],
        "ma20": d["ma20"],
        "ma50": d["ma50"],
        "ma200": d["ma200"],
        **rating_map2.get(d["ticker"], {}),
    } for d in all_data]
    overview.sort(key=lambda x: x.get("score", 0), reverse=True)
    (OUTPUT / "overview.json").write_text(json.dumps(overview, ensure_ascii=False, indent=2), encoding="utf-8")

    # 导出评级 JSON（方便后续使用）
    (OUTPUT / "ratings.json").write_text(json.dumps(ratings, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*50}")
    print(f"✅ 生成完成！共 {len(all_data)} 个页面 + 评级系统")
    print(f"📁 输出: {OUTPUT}")
    print(f"   首页: {OUTPUT / 'index.html'}")
    print(f"   对比: {OUTPUT / 'compare.html'}")
    print(f"   评级: {OUTPUT / 'ratings.json'}")
    for d in all_data:
        print(f"   {d['ticker']}: {OUTPUT / d['ticker'].lower() / 'index.html'}")
    print(f"{'='*50}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
