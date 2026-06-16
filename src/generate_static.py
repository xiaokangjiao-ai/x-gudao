#!/usr/bin/env python3
"""
x-gudao SSG: 静态网站预生成脚本
- 10个ETF + 10个股票的独立详情页
- 首页两大板块展示
"""
import sys, json, sqlite3, argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    import jinja2, yfinance as yf, numpy as np
except ImportError as e:
    print(f"[ERROR] 缺少依赖: {e.name}")
    sys.exit(1)

ROOT = Path(__file__).parent.parent.resolve()
TEMPLATES = ROOT / "templates"
OUTPUT = ROOT / "_site"
WATCHLIST = ROOT / "watchlist.json"
DB_PATH = ROOT / "data" / "market_data.db"
OUTPUT.mkdir(exist_ok=True)

# ── 基金/股票元数据 ──────────────────────────────
ETF_META = {
    "SPY":  {"name": "SPDR S&P 500 ETF Trust", "desc": "全球规模最大的ETF，追踪标普500指数，涵盖美国500家大型上市公司，是全球股市的基准。管理费用仅0.09%。"},
    "IVV":  {"name": "iShares Core S&P 500 ETF", "desc": "贝莱德发行的标普500指数基金，管理费低至0.03%，与SPY并列为美国核心资产的代表。"},
    "VOO":  {"name": "Vanguard S&P 500 ETF", "desc": "先锋集团旗舰ETF，追踪标普500指数，0.03%的超低管理费使其成为长期持有的首选。"},
    "QQQ":  {"name": "Invesco QQQ Trust", "desc": "追踪纳斯达克100指数，集中持有苹果、微软、英伟达等全球顶尖科技公司，科技股风向标。"},
    "VTI":  {"name": "Vanguard Total Stock Market ETF", "desc": "覆盖美国整个股市（大中小盘），持有约4000只股票，是真正意义上的美国全市场指数。"},
    "VEA":  {"name": "Vanguard FTSE Developed Markets ETF", "desc": "投资美国以外发达市场（日本、英国、欧洲等），是全球化配置的核心工具之一。"},
    "IEFA": {"name": "iShares Core MSCI EAFE ETF", "desc": "追踪MSCI EAFE指数，覆盖欧洲、澳大利亚和远东发达市场的国际化分散ETF。"},
    "BND":  {"name": "Vanguard Total Bond Market ETF", "desc": "美国全债市ETF，覆盖国债、企业债、抵押贷款债券等，是固定收益配置的核心。"},
    "VWO":  {"name": "Vanguard FTSE Emerging Markets ETF", "desc": "追踪新兴市场指数（中国、印度、巴西等），是全球成长型投资者不可忽视的选择。"},
    "GLD":  {"name": "SPDR Gold Shares", "desc": "全球最大的黄金ETF，以实物黄金为支撑，是对冲通胀和地缘风险的经典工具。"},
}

STOCK_META = {
    "AAPL":  {"name": "Apple Inc.", "desc": "全球市值最高的公司，iPhone、Mac、iPad等硬件生态与App Store服务业务共同驱动增长。"},
    "MSFT":  {"name": "Microsoft Corp.", "desc": "全球最大软件公司，Azure云服务、Office 365、Windows系统三大支柱，AI领域的核心玩家。"},
    "GOOGL": {"name": "Alphabet Inc.", "desc": "谷歌母公司，搜索广告+YouTube+云计算三足鼎立，AI大模型Gemini引领技术前沿。"},
    "AMZN":  {"name": "Amazon.com Inc.", "desc": "全球最大电商和云计算平台（AWS），物流网络与云服务构成强大的护城河。"},
    "NVDA":  {"name": "NVIDIA Corp.", "desc": "全球AI芯片霸主，GPU在数据中心、自动驾驶、游戏领域占据绝对领先地位。"},
    "META":  {"name": "Meta Platforms Inc.", "desc": "Facebook、Instagram、WhatsApp母公司，社交媒体帝国在AI推荐和元宇宙领域持续布局。"},
    "TSLA":  {"name": "Tesla Inc.", "desc": "全球领先的电动汽车制造商，同时在储能、自动驾驶和人形机器人领域引领创新。"},
    "BRK.B": {"name": "Berkshire Hathaway Inc.", "desc": "沃伦·巴菲特的投资旗舰，持有保险、铁路、能源等多元业务，是价值投资的标杆。"},
    "JPM":   {"name": "JPMorgan Chase & Co.", "desc": "美国最大银行，投行、财富管理、商业银行业务遍布全球，金融业的晴雨表。"},
    "V":     {"name": "Visa Inc.", "desc": "全球最大的支付网络运营商，覆盖200多个国家和地区，是数字支付时代的核心基础设施。"},
}


def get_all_tickers():
    """从watchlist读取所有标的"""
    wl = json.loads(WATCHLIST.read_text(encoding="utf-8"))
    return wl.get("etfs", []) + wl.get("stocks", [])


def get_groups():
    """获取ETF和股票分组"""
    wl = json.loads(WATCHLIST.read_text(encoding="utf-8"))
    return wl.get("etfs", []), wl.get("stocks", [])


def fetch_data(ticker):
    """DB优先，YF兜底"""
    data = fetch_from_db(ticker)
    if data:
        print(f"  [FETCH] {ticker} ← SQLite ({len(data)}条)")
    else:
        print(f"  [FETCH] {ticker} ← Yahoo Finance (fallback)")
        data = fetch_from_yf(ticker)
    return data


def fetch_from_db(ticker):
    if not DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute(
            "SELECT date, open, high, low, close, volume FROM market_data WHERE ticker=? ORDER BY date ASC",
            (ticker,)
        ).fetchall()
        conn.close()
        if not rows:
            return []
        return [{"date": r[0], "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]} for r in rows]
    except Exception as e:
        print(f"  [DB ERROR] {ticker}: {e}")
        return []


def fetch_from_yf(ticker):
    try:
        df = yf.Ticker(ticker).history(period="5y", auto_adjust=True)
        if df.empty:
            return []
        return [{
            "date": date.strftime("%Y-%m-%d"), "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2), "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2), "volume": int(float(row["Volume"])),
        } for date, row in df.iterrows()]
    except Exception as e:
        print(f"  [ERROR] {ticker}: {e}")
        return []


def get_meta(ticker, groups):
    etfs, stocks = groups
    if ticker in etfs:
        m = ETF_META.get(ticker, {})
        return m.get("name", ticker), m.get("desc", ""), "ETF"
    else:
        m = STOCK_META.get(ticker, {})
        return m.get("name", ticker), m.get("desc", ""), "股票"


def enrich(ticker, data, groups):
    """计算技术指标"""
    if not data:
        return None
    closes = [d["close"] for d in data]
    latest = closes[-1]
    prev = closes[-2] if len(closes) > 1 else latest
    name, desc, cat = get_meta(ticker, groups)

    yr = max((datetime.strptime(data[-1]["date"], "%Y-%m-%d") -
              datetime.strptime(data[0]["date"], "%Y-%m-%d")).days / 365.25, 0.5)
    ann_ret = round(((latest / data[0]["close"]) ** (1 / yr) - 1) * 100, 2)

    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    vol = round(np.std(returns) * np.sqrt(252) * 100, 2) if len(returns) > 1 else 0.0

    peak = closes[0]; max_dd = 0
    for p in closes:
        if p > peak: peak = p
        dd = (p - peak) / peak * 100
        if dd < max_dd: max_dd = dd

    def ma(p):
        r = []
        for i in range(len(data)):
            if i < p-1: r.append(None)
            else: r.append(round(sum(d["close"] for d in data[i-p+1:i+1]) / p, 2))
        return r

    ma20 = ma(20); ma50 = ma(50); ma200 = ma(200)

    recent = data[-252:] if len(data) >= 252 else data
    h52 = max(d["high"] for d in recent); l52 = min(d["low"] for d in recent)

    return {
        "ticker": ticker, "name": name, "desc": desc, "category": cat,
        "data": data,
        "latest_close": round(latest, 2),
        "day_change": round((latest - prev) / prev * 100, 2),
        "annual_return": ann_ret,
        "volatility": vol,
        "max_drawdown": round(max_dd, 2),
        "high": round(h52, 2), "low": round(l52, 2),
        "ma20": ma20[-1] if ma20[-1] else 0,
        "ma50": ma50[-1] if ma50[-1] else 0,
        "ma200": ma200[-1] if ma200[-1] else 0,
        "data_points": len(data),
        "date_range": f"{data[0]['date']} ~ {data[-1]['date']}",
        "price_history": data[-252:] if len(data) >= 252 else data,
    }


# ── 渲染 ──────────────────────────────────────────
def render_index(etf_data, stock_data):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATES)))
    tmpl = env.get_template("index.html")
    etf_overview = [{
        "ticker": d["ticker"], "name": d["name"], "desc": d.get("desc", ""),
        "latest_close": d["latest_close"], "change_pct": d["day_change"],
        "annual_return": d["annual_return"], "volatility": d["volatility"],
        "high": d["high"], "low": d["low"], "data_points": d["data_points"],
        "price_history": d["price_history"],
    } for d in etf_data]
    stock_overview = [{
        "ticker": d["ticker"], "name": d["name"], "desc": d.get("desc", ""),
        "latest_close": d["latest_close"], "change_pct": d["day_change"],
        "annual_return": d["annual_return"], "volatility": d["volatility"],
        "high": d["high"], "low": d["low"], "data_points": d["data_points"],
        "price_history": d["price_history"],
    } for d in stock_data]
    return tmpl.render(
        etf_data=json.dumps(etf_overview, ensure_ascii=False),
        stock_data=json.dumps(stock_overview, ensure_ascii=False),
    )


def render_ticker(d, all_data):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATES)))
    tmpl = env.get_template("stock.html")
    compare = [{
        "ticker": x["ticker"], "name": x["name"],
        "price": x["latest_close"], "return": x["annual_return"],
    } for x in all_data if x["ticker"] != d["ticker"]][:6]
    return tmpl.render(
        ticker=d["ticker"], name=d["name"], desc=d.get("desc", ""),
        category=d["category"], latest_close=d["latest_close"],
        stats={
            "high": d["high"], "low": d["low"],
            "annual_return": d["annual_return"],
            "day_change": d["day_change"],
            "volatility": d["volatility"],
            "ma20": d["ma20"], "ma50": d["ma50"], "ma200": d["ma200"],
            "data_points": d["data_points"], "date_range": d["date_range"],
            "max_drawdown": d["max_drawdown"],
            "sharpe": round(d["annual_return"] / d["volatility"], 2) if d["volatility"] > 0 else 0,
        },
        chart_data=json.dumps(d["data"], ensure_ascii=False),
        latest_data=json.dumps({"close": d["latest_close"], "change": d["day_change"]}, ensure_ascii=False),
        compare_data=json.dumps(compare, ensure_ascii=False),
        tickers_json=json.dumps([x["ticker"] for x in all_data], ensure_ascii=False),
    )


def main():
    print(f"\n{'='*55}")
    print(f"  股道奇货 SSG · 全球最具投资价值TOP 10")
    print(f"{'='*55}\n")

    etf_tickers, stock_tickers = get_groups()
    all_tickers = etf_tickers + stock_tickers
    print(f"  ETF: {len(etf_tickers)}只 | 股票: {len(stock_tickers)}只 | 总计: {len(all_tickers)}")
    print(f"  输出: {OUTPUT}\n")

    all_data = []
    for ticker in all_tickers:
        idx = all_tickers.index(ticker) + 1
        print(f"[{idx}/{len(all_tickers)}] {ticker}")
        raw = fetch_data(ticker)
        enriched = enrich(ticker, raw, (etf_tickers, stock_tickers))
        if enriched:
            all_data.append(enriched)
        else:
            print(f"  [SKIP] {ticker} 无数据")

    if not all_data:
        print("[ERROR] 无数据")
        sys.exit(1)

    etf_data = [d for d in all_data if d["ticker"] in etf_tickers]
    stock_data = [d for d in all_data if d["ticker"] in stock_tickers]

    print(f"\n✅ 获取完毕: ETF {len(etf_data)}只, 股票 {len(stock_data)}只\n")

    # 首页
    print("[1/3] 生成首页 index.html ...")
    (OUTPUT / "index.html").write_text(render_index(etf_data, stock_data), encoding="utf-8")

    # 详情页
    print("[2/3] 生成详情页 ...")
    for d in all_data:
        td = OUTPUT / d["ticker"].lower()
        td.mkdir(exist_ok=True)
        html = render_ticker(d, all_data)
        (td / "index.html").write_text(html, encoding="utf-8")
        print(f"  ✓ {d['ticker']}/index.html")

    # 兼容页
    print("[3/3] 兼容页面 ...")
    (OUTPUT / "screener.html").write_text((OUTPUT / "index.html").read_text(encoding="utf-8"), encoding="utf-8")

    print(f"\n{'='*55}")
    print(f"✅ 生成完成 | {len(all_data)} 个页面")
    print(f"   {OUTPUT / 'index.html'}")
    for d in all_data:
        print(f"   {d['ticker']}: {OUTPUT / d['ticker'].lower() / 'index.html'}")
    print(f"{'='*55}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
