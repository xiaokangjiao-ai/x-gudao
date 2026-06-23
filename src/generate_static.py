#!/usr/bin/env python3
"""
x-gudao SSG: 静态网站预生成脚本
每次运行生成所有HTML页面，包括每个ETF的独立详情页
"""
import sys
import json
import sqlite3
import argparse
import time
import os
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

# ── A股数据模块 ──────────────────────────────────────────────
# 动态导入ashare_fetcher（如果存在）
ASHARE_AVAILABLE = False
try:
    sys.path.insert(0, str(Path(__file__).parent))
    import ashare_fetcher
    ASHARE_AVAILABLE = True
    print("[INFO] A股数据模块已加载")
except ImportError as e:
    print(f"[WARN] A股数据模块加载失败: {e}")

# ── 路径设置 ──────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.resolve()
TEMPLATES = ROOT / "templates"
OUTPUT = ROOT / "_site"
WATCHLIST = ROOT / "watchlist.json"
DB_PATH = ROOT / "data" / "market_data.db"

OUTPUT.mkdir(exist_ok=True)


# ── 数据获取 ──────────────────────────────────────────────
def fetch_from_yf(ticker: str, period: str = "1y", max_retries: int = 3) -> list:
    """
    从Yahoo Finance获取历史数据
    支持代理（https_proxy环境变量）+ 自动重试
    BRK.B特殊处理：yfinance依赖 '-' 代替 '.', 故自动替换后重试
    """
    def _do_fetch(symbol: str) -> list:
        try:
            df = yf.Ticker(symbol).history(period=period, auto_adjust=True)
            if df.empty:
                return None
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
            return None

    # 重试循环
    last_err = None
    for attempt in range(1, max_retries + 1):
        result = _do_fetch(ticker)
        if result is not None and len(result) > 0:
            return result
        # BRK.B特殊处理：使用BRK-B
        if "." in ticker:
            alt = ticker.replace(".", "-")
            result = _do_fetch(alt)
            if result is not None and len(result) > 0:
                return result
        # 非最后一次重试则等待
        if attempt < max_retries:
            wait = 2 ** attempt  # 指数退避：2s, 4s
            print(f"  [RETRY] {ticker} 第{attempt}次失败，{wait}s后重试...")
            time.sleep(wait)

    print(f"  [ERROR] {ticker}: 获取失败，已重试{max_retries}次")
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


def is_ashare_code(ticker: str) -> bool:
    """检查是否为A股代码（6位数字）"""
    return len(ticker) == 6 and ticker.isdigit()


def get_ticker_data(ticker: str, skip_fetch: bool = False) -> dict:
    """
    获取单个标的完整数据
    非skip-fetch模式：始终通过yfinance获取最新1年数据
    skip-fetch模式：仅使用DB数据
    A股代码特殊处理：使用ashare_fetcher获取数据
    """
    data = []
    
    # ═══ A股特殊处理 ═══
    if is_ashare_code(ticker):
        print(f"  [FETCH] {ticker} ← A股数据源")
        if ASHARE_AVAILABLE:
            # 使用ashare_fetcher获取A股完整数据
            ashare_result = ashare_fetcher.get_ashare_data(ticker, days=7)  # 获取7天数据（用户要求一周）
            if ashare_result and ashare_result.get('history'):
                # 转换历史数据为标准格式
                data = []
                for item in ashare_result['history']:
                    data.append({
                        "date": item.get("date", ""),
                        "open": round(float(item.get("open", 0)), 2),
                        "high": round(float(item.get("high", 0)), 2),
                        "low": round(float(item.get("low", 0)), 2),
                        "close": round(float(item.get("close", 0)), 2),
                        "volume": int(item.get("volume", 0)),
                    })
                print(f"  [A股] {ticker} 获取到 {len(data)} 条K线数据")
            else:
                print(f"  [WARN] {ticker} A股数据获取失败")
        else:
            print(f"  [WARN] {ticker} A股模块不可用，尝试SQLite...")
            data = fetch_from_db(ticker)
            if data:
                print(f"  [DB] {ticker} ({len(data)}条)")
        
        if not data:
            return {}
    else:
        # ═══ 美股/ETF处理 ═══
        if skip_fetch:
            data = fetch_from_db(ticker)
            if data:
                print(f"  [SKIP-FETCH] {ticker} ← SQLite ({len(data)}条)")
            else:
                print(f"  [SKIP-FETCH] {ticker} DB无数据，跳过")
        else:
            print(f"  [FETCH] {ticker} ← Yahoo Finance (1y)")
            data = fetch_from_yf(ticker, "1y")
            if not data:
                print(f"  [FALLBACK] {ticker} ← SQLite")
                data = fetch_from_db(ticker)
                if data:
                    print(f"  [DB] {ticker} ({len(data)}条)")

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

    # 构建带评分的 overview 数据
    overview = []
    for d in tickers_data:
        latest = d["latest_close"]
        ma20, ma50, ma200 = d["ma20"], d["ma50"], d["ma200"]

        # ═══ 均线状态判定（改进版：数据不足时用ma20乖离率补充）═══
        ma20_bias = (latest - ma20) / ma20 if ma20 > 0 else 0
        if ma20 > 0 and ma50 > 0 and ma200 > 0:
            if latest > ma20 > ma50 > ma200:
                ma_status = "多头"
            elif latest > ma20 and latest > ma50:
                ma_status = "偏多"
            elif latest < ma20 and latest < ma50 < ma200:
                ma_status = "偏空"
            elif latest < ma200:
                ma_status = "空头"
            elif latest > ma20:
                ma_status = "偏多"
            else:
                ma_status = "中性"
        elif ma20 > 0:
            # 缺少ma50/ma200时，基于ma20乖离率判断
            if ma20_bias > 0.03:
                ma_status = "偏多"
            elif ma20_bias < -0.03:
                ma_status = "偏空"
            else:
                ma_status = "中性"
        else:
            ma_status = "中性"

        # ═══ 四维评分 (0-100) 改进版 ═══
        score_components = {}

        # 1. 趋势分 (40分): 基于均线排列 + 乖离率
        if ma_status == "多头":
            score_components["trend"] = 40 if ma20_bias < 0.08 else 32  # 超买扣分
        elif ma_status == "偏多":
            score_components["trend"] = 28
        elif ma_status == "偏空":
            score_components["trend"] = 14
        elif ma_status == "空头":
            score_components["trend"] = 6
        else:
            score_components["trend"] = 20

        # 2. 波动率分 (20分): 低波动高分，用实际百分位
        vol = d["volatility"] or 0
        if vol <= 5:
            score_components["volatility"] = 20
        elif vol <= 15:
            score_components["volatility"] = 18
        elif vol <= 25:
            score_components["volatility"] = 15
        elif vol <= 35:
            score_components["volatility"] = 10
        elif vol <= 45:
            score_components["volatility"] = 6
        else:
            score_components["volatility"] = 3

        # 3. 收益分 (25分): 优先用1年年化，否则用总年化
        ann_ret = d.get("annual_return_1y", 0) or d.get("annual_return", 0) or 0
        ann_ret_pct = ann_ret / 100  # 转小数
        if ann_ret_pct >= 0.30:
            score_components["return"] = 25
        elif ann_ret_pct >= 0.20:
            score_components["return"] = 22
        elif ann_ret_pct >= 0.10:
            score_components["return"] = 18
        elif ann_ret_pct >= 0.05:
            score_components["return"] = 15
        elif ann_ret_pct >= 0:
            score_components["return"] = 12
        elif ann_ret_pct >= -0.10:
            score_components["return"] = 8
        elif ann_ret_pct >= -0.25:
            score_components["return"] = 4
        else:
            score_components["return"] = 1

        # 4. 动量分 (15分): 基于近5日涨跌幅均值
        closes = [p["close"] for p in d["price_history"]]
        if len(closes) >= 6:
            recent_returns = [(closes[-i] - closes[-i-1]) / closes[-i-1] for i in range(1, 6)]
            avg_momentum = sum(recent_returns) / len(recent_returns) * 100
        else:
            avg_momentum = d.get("day_change", 0) or 0

        if avg_momentum >= 2:
            score_components["momentum"] = 15
        elif avg_momentum >= 1:
            score_components["momentum"] = 13
        elif avg_momentum >= 0:
            score_components["momentum"] = 11
        elif avg_momentum >= -1:
            score_components["momentum"] = 8
        elif avg_momentum >= -2:
            score_components["momentum"] = 5
        else:
            score_components["momentum"] = 2

        total_score = sum(score_components.values())
        stars = max(1, min(5, round(total_score / 17.5)))  # 1-5星 (更细粒度)

        # ═══ 风险等级分类（基于金融常识 + 波动率）═══
        # 手动定义风险等级，因为算法无法准确捕捉金融常识
        risk_manual = {
            # 低风险：债券、防御型、低波动红利ETF
            "BND": "低风险",
            "BRK.B": "低风险",
            "SCHD": "低风险",
            # 中等风险：大盘ETF、优质蓝筹
            "VOO": "中等",
            "QQQ": "中等",
            "AAPL": "中等",
            "MSFT": "中等",
            "GOOGL": "中等",
            "AMZN": "中等",
            "META": "中等",
            # 高风险：高波动科技股、小盘、商品、医药
            "NVDA": "高风险",
            "SMH": "高风险",
            "IWM": "高风险",
            "GLD": "高风险",
            "LLY": "高风险",
            "VXUS": "高风险",
        }
        risk_level = risk_manual.get(d["ticker"], "中等")

        # ═══ 趋势细分（基于均线乖离率）═══
        ma20_bias = (latest - ma20) / ma20 if ma20 > 0 else 0
        if ma_status == "多头":
            if ma20_bias > 0.08:
                trend_category = "超买多头"
            elif ma20_bias < 0.02:
                trend_category = "初始多头"
            else:
                trend_category = "稳健多头"
        elif ma_status == "偏多":
            trend_category = "震荡偏多"
        elif ma_status == "偏空":
            trend_category = "震荡偏空"
        elif ma_status == "空头":
            trend_category = "空头趋势"
        else:
            trend_category = "震荡"

        overview.append({
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
            "ma20": ma20,
            "ma50": ma50,
            "ma200": ma200,
            "ma_status": ma_status,
            "risk_level": risk_level,
            "trend_category": trend_category,
            "score": round(total_score, 1),
            "stars": stars,
        })

    # Top3: 按评分排序取前3
    top3 = sorted(overview, key=lambda x: x["score"], reverse=True)[:3]

    return tmpl.render(
        overview_data=json.dumps(overview, ensure_ascii=False),
        top3_data=json.dumps(top3, ensure_ascii=False),
    )


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
        a_tickers = wl.get("a_tickers", [])
        tickers = tickers + a_tickers  # 合并美股和A股
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
