#!/usr/bin/env python3
"""
x-gudao SSG: 静态网站预生成脚本
- 10个ETF + 10个股票的独立详情页
- 首页两大板块展示
- 使用 ticker_metadata.json 融合旧版丰富数据
"""
import sys, json, sqlite3, argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    import jinja2, numpy as np
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e.name}")
    sys.exit(1)

ROOT = Path(__file__).parent.parent.resolve()
TEMPLATES = ROOT / "templates"
OUTPUT = ROOT / "output"
WATCHLIST = ROOT / "watchlist.json"
DB_PATH = ROOT / "data" / "market_data.db"
META_PATH = ROOT / "data" / "ticker_metadata.json"
OUTPUT.mkdir(exist_ok=True)

# ── 基金/股票元数据（用于 watchlist 中有但 metadata.json 中无的标的） ──
ETF_META = {
    "SPY":  {"name": "SPDR S&P 500 ETF Trust", "name_cn": "标普500ETF", "full_name": "SPDR S&P 500 ETF", "desc": "全球规模最大的ETF，追踪标普500指数，涵盖美国500家大型上市公司，是全球股市的基准。管理费用仅0.09%。"},
    "IVV":  {"name": "iShares Core S&P 500 ETF", "name_cn": "iShares标普500ETF", "full_name": "iShares Core S&P 500 ETF", "desc": "贝莱德发行的标普500指数基金，管理费低至0.03%，与SPY并列为美国核心资产的代表。"},
    "VOO":  {"name": "Vanguard S&P 500 ETF", "name_cn": "先锋标普500ETF", "full_name": "Vanguard S&P 500", "desc": "先锋集团旗舰ETF，追踪标普500指数，0.03%的超低管理费使其成为长期持有的首选。"},
    "QQQ":  {"name": "Invesco QQQ Trust", "name_cn": "纳斯达克100ETF", "full_name": "Invesco QQQ Trust", "desc": "追踪纳斯达克100指数，集中持有苹果、微软、英伟达等全球顶尖科技公司，科技股风向标。"},
    "VTI":  {"name": "Vanguard Total Stock Market ETF", "name_cn": "先锋全市场ETF", "full_name": "Vanguard Total Stock Market", "desc": "覆盖美国整个股市（大中小盘），持有约4000只股票，是真正意义上的美国全市场指数。"},
    "VEA":  {"name": "Vanguard FTSE Developed Markets ETF", "name_cn": "发达市场ETF", "full_name": "Vanguard FTSE Developed Markets", "desc": "投资美国以外发达市场（日本、英国、欧洲等），是全球化配置的核心工具之一。"},
    "IEFA": {"name": "iShares Core MSCI EAFE ETF", "name_cn": "EAFE发达市场ETF", "full_name": "iShares Core MSCI EAFE ETF", "desc": "追踪MSCI EAFE指数，覆盖欧洲、澳大利亚和远东发达市场的国际化分散ETF。"},
    "BND":  {"name": "Vanguard Total Bond Market ETF", "name_cn": "先锋全债市ETF", "full_name": "Vanguard Total Bond Market", "desc": "美国全债市ETF，覆盖国债、企业债、抵押贷款债券等，是固定收益配置的核心。"},
    "VWO":  {"name": "Vanguard FTSE Emerging Markets ETF", "name_cn": "新兴市场ETF", "full_name": "Vanguard FTSE Emerging Markets ETF", "desc": "追踪新兴市场指数（中国、印度、巴西等），是全球成长型投资者不可忽视的选择。"},
    "GLD":  {"name": "SPDR Gold Shares", "name_cn": "SPDR黄金ETF", "full_name": "SPDR Gold Shares", "desc": "全球最大的黄金ETF，以实物黄金为支撑，是对冲通胀和地缘风险的经典工具。"},
}

STOCK_META = {
    "AAPL":  {"name": "Apple Inc.", "name_cn": "苹果公司", "full_name": "Apple Inc.", "desc": "全球市值最高的公司，iPhone、Mac、iPad等硬件生态与App Store服务业务共同驱动增长。"},
    "MSFT":  {"name": "Microsoft Corp.", "name_cn": "微软公司", "full_name": "Microsoft Corp.", "desc": "全球最大软件公司，Azure云服务、Office 365、Windows系统三大支柱，AI领域的核心玩家。"},
    "GOOGL": {"name": "Alphabet Inc.", "name_cn": "谷歌母公司", "full_name": "Alphabet Inc.", "desc": "谷歌母公司，搜索广告+YouTube+云计算三足鼎立，AI大模型Gemini引领技术前沿。"},
    "AMZN":  {"name": "Amazon.com Inc.", "name_cn": "亚马逊", "full_name": "Amazon.com Inc.", "desc": "全球最大电商和云计算平台（AWS），物流网络与云服务构成强大的护城河。"},
    "NVDA":  {"name": "NVIDIA Corp.", "name_cn": "英伟达", "full_name": "NVIDIA Corp.", "desc": "全球AI芯片霸主，GPU在数据中心、自动驾驶、游戏领域占据绝对领先地位。"},
    "META":  {"name": "Meta Platforms Inc.", "name_cn": "Meta", "full_name": "Meta Platforms Inc.", "desc": "Facebook、Instagram、WhatsApp母公司，社交媒体帝国在AI推荐和元宇宙领域持续布局。"},
    "TSLA":  {"name": "Tesla Inc.", "name_cn": "特斯拉", "full_name": "Tesla Inc.", "desc": "全球领先的电动汽车制造商，同时在储能、自动驾驶和人形机器人领域引领创新。"},
    "BRK.B": {"name": "Berkshire Hathaway Inc.", "name_cn": "伯克希尔哈撒韦", "full_name": "Berkshire Hathaway Inc.", "desc": "沃伦·巴菲特的投资旗舰，持有保险、铁路、能源等多元业务，是价值投资的标杆。"},
    "JPM":   {"name": "JPMorgan Chase & Co.", "name_cn": "摩根大通", "full_name": "JPMorgan Chase & Co.", "desc": "美国最大银行，投行、财富管理、商业银行业务遍布全球，金融业的晴雨表。"},
    "V":     {"name": "Visa Inc.", "name_cn": "Visa", "full_name": "Visa Inc.", "desc": "全球最大的支付网络运营商，覆盖200多个国家和地区，是数字支付时代的核心基础设施。"},
}


# ── 加载 ticker_metadata.json ───────────────────
def load_ticker_metadata():
    if not META_PATH.exists():
        print(f"  [WARN] {META_PATH} not found, using only ETF_META/STOCK_META")
        return {}
    try:
        with open(META_PATH, encoding="utf-8") as f:
            data = json.load(f)
        print(f"  [META] Loaded {len(data)} tickers from metadata")
        return data
    except Exception as e:
        print(f"  [ERROR] Failed to load metadata: {e}")
        return {}


# ── 分组 ─────────────────────────────────────────
def get_groups():
    wl = json.loads(WATCHLIST.read_text(encoding="utf-8"))
    return wl.get("etfs", []), wl.get("stocks", [])


def get_all_tickers():
    etfs, stocks = get_groups()
    return etfs + stocks


# ── 数据获取 ──────────────────────────────────────
def fetch_data(ticker):
    """DB优先 → output/{TICKER}.json 兜底"""
    data = fetch_from_db(ticker)
    if data:
        print(f"    [DB] {ticker} ← SQLite ({len(data)} records)")
        return data

    # 尝试旧 JSON 文件兜底
    old_json = OUTPUT / f"{ticker}.json"
    if old_json.exists():
        try:
            jdata = json.loads(old_json.read_text(encoding="utf-8"))
            # 尝试找到 prices 字段
            prices = jdata.get("prices") or jdata.get("data") or []
            if prices:
                data = [{"date": p.get("date", p.get("Date", "")), "open": float(p.get("Open", p.get("open", 0))),
                         "high": float(p.get("High", p.get("high", 0))), "low": float(p.get("Low", p.get("low", 0))),
                         "close": float(p.get("Close", p.get("close", 0))), "volume": int(float(p.get("Volume", 0)))}
                        for p in prices]
                data = sorted(data, key=lambda x: x["date"])
                print(f"    [JSON] {ticker} ← old JSON ({len(data)} records)")
                return data
        except Exception as e:
            print(f"    [JSON ERR] {ticker}: {e}")

    print(f"    [SKIP] {ticker} — no data found")
    return []


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
        return [{"date": r[0], "open": float(r[1]), "high": float(r[2]), "low": float(r[3]),
                 "close": float(r[4]), "volume": int(r[5])} for r in rows]
    except Exception as e:
        print(f"    [DB ERROR] {ticker}: {e}")
        return []


# ── 技术指标计算 ─────────────────────────────────
def compute_stats(data):
    if not data:
        return None
    closes = [d["close"] for d in data]
    latest = closes[-1]
    prev = closes[-2] if len(closes) > 1 else latest

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
    h52 = max(d["high"] for d in recent)
    l52 = min(d["low"] for d in recent)

    sharpe = round(ann_ret / vol, 2) if vol > 0 else 0

    return {
        "latest_close": round(latest, 2),
        "day_change": round(latest - prev, 2),
        "day_change_pct": round((latest - prev) / prev * 100, 2),
        "annual_return": ann_ret,
        "volatility": vol,
        "max_drawdown": round(max_dd, 2),
        "high": round(h52, 2),
        "low": round(l52, 2),
        "ma20": ma20[-1] if ma20[-1] else 0,
        "ma50": ma50[-1] if ma50[-1] else 0,
        "ma200": ma200[-1] if ma200[-1] else 0,
        "sharpe": sharpe,
        "data_points": len(data),
        "date_range": f"{data[0]['date']} ~ {data[-1]['date']}",
        "price_history": data[-252:] if len(data) >= 252 else data,
    }


# ── 合并 metadata + 计算数据 ─────────────────────
def build_enriched(ticker, data, meta_dict, ticker_metadata):
    stats = compute_stats(data) if data else {}

    # 优先用旧页面元数据
    old_meta = ticker_metadata.get(ticker, {})

    # 合并：用 old_meta 的值覆盖 ETF_META 的默认值
    meta = {}
    if ticker in ticker_metadata:
        meta = dict(ticker_metadata[ticker])
    else:
        # 用 ETF_META / STOCK_META 填充基础字段
        base = meta_dict.get(ticker, {})
        meta = {
            "ticker": ticker,
            "name": base.get("name", ticker),
            "name_cn": base.get("name_cn", base.get("name", ticker)),
            "full_name": base.get("full_name", base.get("name", ticker)),
            "description": base.get("desc", ""),
            "category": "ETF" if ticker in {**ETF_META} else "股票",
            "expense_ratio": "N/A",
            "aum": "N/A",
            "annual_volatility": f"{stats.get('volatility', 0):.1f}%" if stats else "N/A",
            "sharpe_ratio": stats.get("sharpe", 0) if stats else 0,
            "max_drawdown": f"{stats.get('max_drawdown', 0):.1f}%" if stats else "N/A",
            "performance": [],
            "sector_distribution": [],
            "ai_insight": None,
            "similar_etfs": [],
            "compare_data": None,
        }

    # 覆盖 price / day_change / week52_high/low（用最新计算值）
    if stats:
        meta["price"] = stats["latest_close"]
        meta["day_change"] = stats["day_change"]
        meta["day_change_pct"] = stats["day_change_pct"]
        meta["week52_high"] = stats["high"]
        meta["week52_low"] = stats["low"]
        meta["annual_volatility"] = f"{stats['volatility']:.1f}%"
        meta["sharpe_ratio"] = stats["sharpe"]
        meta["max_drawdown"] = f"{stats['max_drawdown']:.1f}%"
        if "similar_etfs" not in meta or not meta["similar_etfs"]:
            meta["similar_etfs"] = []
    else:
        # 无行情数据时用静态数据
        if "price" not in meta:
            meta["price"] = 0.0
        if "day_change" not in meta:
            meta["day_change"] = 0.0
        if "day_change_pct" not in meta:
            meta["day_change_pct"] = 0.0

    # 确定 category
    if meta.get("asset_type") == "bond":
        meta["category"] = "债券ETF"
    elif meta.get("asset_type") == "commodity":
        meta["category"] = "商品ETF"
    elif ticker in ETF_META:
        meta["category"] = "ETF"
    else:
        meta["category"] = "股票"

    return {
        "ticker": ticker,
        "meta": meta,
        "stats": stats or {
            "annual_return": 0, "volatility": 0, "max_drawdown": 0,
            "sharpe": 0, "ma20": 0, "ma50": 0, "ma200": 0,
        },
        "data": data,
        "chart_data": json.dumps(data, ensure_ascii=False) if data else "[]",
    }


# ── 渲染 ──────────────────────────────────────────
def make_jinja_env():
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATES)))
    # 注册 enumerate filter（模板中用到）
    env.filters["enumerate"] = lambda seq: enumerate(seq)
    return env


def render_index(etf_data, stock_data):
    env = make_jinja_env()
    tmpl = env.get_template("index.html")
    etf_overview = [{
        "ticker": d["ticker"], "name": d["meta"].get("name", d["ticker"]),
        "desc": d["meta"].get("description", ""),
        "latest_close": d["meta"].get("price", d["stats"].get("latest_close", 0)),
        "change_pct": d["meta"].get("day_change_pct", d["stats"].get("day_change_pct", 0)),
        "annual_return": d["stats"].get("annual_return", 0),
        "volatility": d["stats"].get("volatility", 0),
        "high": d["meta"].get("week52_high", d["stats"].get("high", 0)),
        "low": d["meta"].get("week52_low", d["stats"].get("low", 0)),
        "price_history": d["stats"].get("price_history", []),
    } for d in etf_data]
    stock_overview = [{
        "ticker": d["ticker"], "name": d["meta"].get("name", d["ticker"]),
        "desc": d["meta"].get("description", ""),
        "latest_close": d["meta"].get("price", d["stats"].get("latest_close", 0)),
        "change_pct": d["meta"].get("day_change_pct", d["stats"].get("day_change_pct", 0)),
        "annual_return": d["stats"].get("annual_return", 0),
        "volatility": d["stats"].get("volatility", 0),
        "high": d["meta"].get("week52_high", d["stats"].get("high", 0)),
        "low": d["meta"].get("week52_low", d["stats"].get("low", 0)),
        "price_history": d["stats"].get("price_history", []),
    } for d in stock_data]
    return tmpl.render(
        etf_data=json.dumps(etf_overview, ensure_ascii=False),
        stock_data=json.dumps(stock_overview, ensure_ascii=False),
    )


def render_ticker(d, all_data):
    env = make_jinja_env()
    tmpl = env.get_template("stock_detail.html")

    meta = d["meta"]
    stats = d["stats"]

    # 构建 compare（同类对比数据）
    compare_tickers = [x["ticker"] for x in all_data
                       if x["ticker"] != d["ticker"] and x["meta"].get("category") == meta.get("category")]
    compare_list = [{
        "ticker": x["ticker"],
        "name": x["meta"].get("name", x["ticker"]),
        "price": x["meta"].get("price", x["stats"].get("latest_close", 0)),
        "return": x["stats"].get("annual_return", 0),
    } for x in all_data if x["ticker"] in compare_tickers][:6]

    # 动态更新 similar_etfs 的价格
    sim_etfs = meta.get("similar_etfs", [])
    for sim in sim_etfs:
        ticker_key = sim["ticker"].upper().replace(".", "-")
        match = next((x for x in all_data if x["ticker"].upper() == ticker_key), None)
        if match:
            sim["price"] = match["meta"].get("price", match["stats"].get("latest_close", sim["price"]))
        # 构造 URL
        if not sim.get("url"):
            sim["url"] = f"/{sim['ticker'].lower()}/"

    return tmpl.render(
        ticker=d["ticker"],
        name=meta.get("name", d["ticker"]),
        meta=meta,
        stats={
            "annual_return": stats.get("annual_return", 0),
            "volatility": stats.get("volatility", 0),
            "max_drawdown": stats.get("max_drawdown", 0),
            "sharpe": stats.get("sharpe", 0),
            "ma20": stats.get("ma20", 0),
            "ma50": stats.get("ma50", 0),
            "ma200": stats.get("ma200", 0),
            "date_range": stats.get("date_range", ""),
        },
        chart_data=d["chart_data"],
    )


# ── 主入口 ─────────────────────────────────────────
def main():
    print(f"\n{'='*58}")
    print(f"  股道奇货 SSG · 全球最具投资价值 TOP 20")
    print(f"{'='*58}\n")

    ticker_metadata = load_ticker_metadata()
    etf_tickers, stock_tickers = get_groups()
    all_tickers = etf_tickers + stock_tickers
    print(f"  ETF: {len(etf_tickers)}只 | 股票: {len(stock_tickers)}只 | 总计: {len(all_tickers)}")
    print(f"  Output: {OUTPUT}\n")

    all_data = []
    for ticker in all_tickers:
        idx = all_tickers.index(ticker) + 1
        print(f"[{idx}/{len(all_tickers)}] {ticker}")
        raw = fetch_data(ticker)
        meta_dict = {**ETF_META, **STOCK_META}
        enriched = build_enriched(ticker, raw, meta_dict, ticker_metadata)
        all_data.append(enriched)

    etf_data = [d for d in all_data if d["ticker"] in etf_tickers]
    stock_data = [d for d in all_data if d["ticker"] in stock_tickers]

    print(f"\n✅ Done: ETF {len(etf_data)}, 股票 {len(stock_data)}\n")

    # [1/3] 首页
    print("[1/3] Generating index.html ...")
    (OUTPUT / "index.html").write_text(render_index(etf_data, stock_data), encoding="utf-8")
    print("  ✓ index.html")

    # [2/3] 详情页（子目录结构）
    print("[2/3] Generating detail pages ...")
    for d in all_data:
        td = OUTPUT / d["ticker"].lower()
        td.mkdir(exist_ok=True)
        html = render_ticker(d, all_data)
        (td / "index.html").write_text(html, encoding="utf-8")
        ticker_short = d["ticker"]
        print(f"  ✓ {ticker_short}/index.html")

    # [3/3] 兼容页面（静态文件）
    print("[3/3] Compatibility pages ...")
    (OUTPUT / "screener.html").write_text((OUTPUT / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
    print("  ✓ screener.html")

    print(f"\n{'='*58}")
    print(f"✅ 生成完成 | {len(all_data)} 个详情页 + 1 首页")
    print(f"   首页: {OUTPUT / 'index.html'}")
    print(f"   详情页目录: {OUTPUT / 'spy' / 'index.html'} 等")
    print(f"{'='*58}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
