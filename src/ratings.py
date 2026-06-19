# -*- coding: utf-8 -*-
"""
x-gudao 评级系统
基于量化指标计算综合评分（1-5星）+ 推荐标签
数据来源：SQLite market_data.db（表 market_data）
"""
import sqlite3
import math
from pathlib import Path
from typing import Optional

# ── 路径 ──────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.resolve()
DB_PATH = ROOT / "data" / "market_data.db"

# ── 一句话投资理由（后续可由 AI 每周更新）──────────────────
INVESTMENT_RATIONALE = {
    "NVDA":  "数据中心GPU垄断地位，Blackwell架构需求井喷，AI算力核心受益",
    "LLY":   "GLP-1双雄（替尔泊肽+Zepbound）全球垄断，肥胖症市场持续爆发，估值虽有溢价但增长确定性极强",
    "MSFT":  "Azure云增速重回加速通道，Copilot全面绑定Office与企业客户",
    "AAPL":  "iPhone出货量边际改善，服务收入持续高增，生态壁垒稳固",
    "GOOGL": "搜索+云+AI三位一体，Gemini追赶ChatGPT，估值仍处历史低位",
    "AMZN":  "AWS毛利率拐点已现，电商履约效率提升，AI+零售协同加速",
    "META":  "Llama开源生态崛起，广告受益AI优化，Reels货币化空间广阔",
    "BRK.B": "穿越周期的价值旗舰，浮存金模式提供安全垫，抗跌性突出",
    "VOO":   "Vanguard旗舰指数基金，低成本高效率，长期胜率极高",
    "QQQ":   "科技七巨头集中持仓，降息周期弹性最大，成长属性突出",
    "IWM":   "美国小盘股代表，降息受益显著，经济复苏期弹性最大",
    "BND":   "美国全债市场覆盖，降息预期直接受益，组合抗跌必备",
    "GLD":   "实际利率下行+地缘风险驱动黄金走强，对冲尾部风险首选",
    "SCHD":  "美国高股息蓝筹ETF，股息率4%+，熊市避风港，长期复利机器",
    "VXUS":  "除美国外全球市场覆盖，分散单一国家风险，配置多元化必备",
    "SMH":   "半导体行业ETF，AI算力需求核心受益，比单押NVDA更具行业代表性",
}

# ── 标的分类（用于波动率基准）──────────────────────────────
VOLATILITY_BENCHMARKS = {
    "NVDA":  45, "LLY":   28, "MSFT": 25, "AAPL": 22, "GOOGL": 25,
    "AMZN":  28, "META":  35, "BRK.B": 18,
    "VOO":   16, "QQQ":   20, "IWM":   22, "BND":    6, "GLD":   15,
    "SCHD":  12, "VXUS":  18, "SMH":   40,
}


def get_db_connection():
    """建立 SQLite 连接"""
    return sqlite3.connect(str(DB_PATH))


def fetch_ticker_data(ticker: str) -> list:
    """从 DB 读取标的收盘价序列（按日期升序）"""
    try:
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT date, close FROM market_data WHERE ticker=? ORDER BY date ASC",
            (ticker,)
        ).fetchall()
        conn.close()
        if not rows:
            return []
        return [{"date": r[0], "close": r[1]} for r in rows]
    except Exception:
        return []


def calc_ma(values: list, period: int):
    """计算简单移动平均，返回最后一个有效值"""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def calc_max_drawdown(closes: list) -> float:
    """计算最大回撤（%，负数表示回撤）"""
    if not closes:
        return 0.0
    peak = closes[0]
    max_dd = 0.0
    for price in closes:
        if price > peak:
            peak = price
        dd = (price - peak) / peak
        if dd < max_dd:
            max_dd = dd
    return max_dd * 100


def calc_annual_return(closes: list) -> float:
    """计算年化收益率（%）"""
    if len(closes) < 2:
        return 0.0
    start_price = closes[0]
    end_price = closes[-1]
    # 用实际天数估算年化
    # 这里用简单的一年252交易日假设（若数据不足一年则用实际天数）
    days = max(len(closes) - 1, 1)
    ann = ((end_price / start_price) ** (252 / days) - 1) * 100
    return round(ann, 2)


def calc_volatility(closes: list) -> float:
    """计算年化波动率（%）"""
    if len(closes) < 3:
        return 0.0
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    std = math.sqrt(sum(r*r for r in returns) / max(len(returns) - 1, 1))
    return round(std * math.sqrt(252) * 100, 2)


def calc_sharpe(returns: list, risk_free: float = 4.0) -> float:
    """计算 Sharpe Ratio（假设无风险利率 4%）"""
    if len(returns) < 2:
        return 0.0
    mean_ret = sum(returns) / len(returns) * 252
    std_ret = math.sqrt(sum(r*r for r in returns) / max(len(returns) - 1, 1)) * math.sqrt(252)
    if std_ret == 0:
        return 0.0
    return round((mean_ret - risk_free) / std_ret, 2)


# ── 核心评分函数 ───────────────────────────────────────────

def score_trend(ma20: float, ma50: float, ma200: float, latest: float) -> float:
    """
    趋势强度评分（满分 25 分）
    - 均线多头排列（MA20 > MA50 > MA200）: +15
    - 价格在 MA200 之上: +10
    - 贴近均线程度加分（最多+5）
    """
    score = 0.0
    # 多头排列
    if ma20 and ma50 and ma200:
        if ma20 > ma50 > ma200:
            score += 15
        elif ma20 > ma50:
            score += 8
        elif ma20 > ma200:
            score += 4
    elif ma20 and ma50:
        if ma20 > ma50:
            score += 10
    elif ma20:
        score += 5
    # 价格在 MA200 之上
    if ma200 and latest > ma200:
        score += 10
    elif ma200 and latest > ma200 * 0.95:
        score += 5
    # 贴近均线（近期是否在上升趋势）
    if ma20 and latest > ma20:
        score += 5
    elif ma20 and latest > ma20 * 0.95:
        score += 2
    return min(score, 25.0)


def score_risk_reward(annual_return: float, volatility: float, sharpe: float) -> float:
    """
    风险收益比评分（满分 25 分）
    - 正年化收益: +10
    - Sharpe > 1: +10（Sharpe > 2 再加5分）
    - 低波动率加成（<15% 加 5 分）
    """
    score = 0.0
    if annual_return > 0:
        score += 10
    elif annual_return < -10:
        score -= 5
    if sharpe >= 2:
        score += 15
    elif sharpe >= 1:
        score += 10
    elif sharpe >= 0:
        score += 3
    # 低波动率加成
    if 0 < volatility < 15:
        score += 5
    elif volatility < 10:
        score += 3
    return min(max(score, 0.0), 25.0)


def score_drawdown(max_drawdown: float, volatility: float) -> float:
    """
    回撤安全度评分（满分 25 分）
    - 最大回撤 < 5%: +25
    - 回撤 5-10%: +18
    - 回撤 10-20%: +10
    - 回撤 20-30%: +5
    - 回撤 > 30%: 0
    - 低波动标的额外加分
    """
    dd = abs(max_drawdown)
    if dd <= 5:
        score = 25.0
    elif dd <= 10:
        score = 18.0
    elif dd <= 20:
        score = 10.0
    elif dd <= 30:
        score = 5.0
    else:
        score = 0.0
    # 低波动标的额外 3 分（相对安全）
    if volatility < 15:
        score += 3
    return min(score, 25.0)


def score_volatility_fit(volatility: float, ticker: str) -> float:
    """
    波动率适中度评分（满分 25 分）
    股票：波动率接近其基准则高分（不是越低越好，而是"符合预期"）
    债券/黄金：低波动明显高分
    """
    benchmark = VOLATILITY_BENCHMARKS.get(ticker, 20)
    ratio = volatility / benchmark if volatility > 0 and benchmark > 0 else 1.0
    if volatility < 1:  # 债券/稳定资产
        return 25.0
    # 波动率在基准的 0.6x ~ 1.3x 之间最为"适中"
    if 0.6 <= ratio <= 1.3:
        score = 25.0
    elif ratio < 0.6:  # 比预期更稳定
        score = 20.0
    elif ratio < 2.0:
        score = 15.0 - (ratio - 1.3) * 5
    else:
        score = max(0.0, 10.0 - (ratio - 2.0) * 3)
    return min(max(score, 0.0), 25.0)


def stars_from_score(score: float) -> int:
    """综合评分 → 1-5星"""
    pct = score / 100.0
    if pct >= 0.85: return 5
    elif pct >= 0.70: return 4
    elif pct >= 0.55: return 3
    elif pct >= 0.40: return 2
    else: return 1


def tag_from_score(score: float, ticker: str) -> tuple:
    """综合评分 → 推荐标签（emoji + 文字）"""
    pct = score / 100.0
    if pct >= 0.85:
        return "🔥", "强力推荐"
    elif pct >= 0.70:
        return "💎", "价值优选"
    elif pct >= 0.55:
        return "✅", "稳健配置"
    elif pct >= 0.40:
        return "⚠️", "高位观望"
    else:
        return "🔴", "高风险"


def ma_bullish_status(ma20: float, ma50: float, ma200: float, latest: float) -> str:
    """
    均线排列状态
    - 多头排列: "🟢 完美多头"
    - 偏多头: "🟡 偏多整理"
    - 偏空头: "🟠 偏空警惕"
    - 空头排列: "🔴 空头排列"
    """
    if not all([ma20, ma50, ma200]):
        # 数据不足，保守估计
        if ma20 and latest > ma20:
            return "🟡", "偏多整理", "偏多"
        elif ma20:
            return "🟠", "偏空警惕", "偏空"
        return "⚪", "数据不足", "中性"
    if ma20 > ma50 > ma200 and latest > ma20:
        return "🟢", "完美多头", "多头"
    elif ma20 > ma50 and latest > ma20:
        return "🟡", "偏多整理", "偏多"
    elif ma20 < ma50 < ma200 and latest < ma20:
        return "🔴", "空头排列", "空头"
    elif ma20 < ma50 or latest < ma20:
        return "🟠", "偏空警惕", "偏空"
    else:
        return "⚪", "中性整理", "中性"


# ── 主评级计算 ────────────────────────────────────────────

def compute_rating(ticker: str) -> Optional[dict]:
    """
    计算单个标的的完整评级信息
    返回 dict，包含评分、星级、标签、外链等
    """
    data = fetch_ticker_data(ticker)
    if not data or len(data) < 5:
        return None

    closes = [d["close"] for d in data]
    latest = closes[-1]

    # 计算基础指标
    ma20_val = calc_ma(closes, 20)
    ma50_val = calc_ma(closes, 50)
    ma200_val = calc_ma(closes, 200)
    annual_return = calc_annual_return(closes)
    volatility = calc_volatility(closes)
    max_dd = calc_max_drawdown(closes)

    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    sharpe = calc_sharpe(returns)

    # 四维度评分
    s_trend = score_trend(ma20_val, ma50_val, ma200_val, latest)
    s_rr = score_risk_reward(annual_return, volatility, sharpe)
    s_dd = score_drawdown(max_dd, volatility)
    s_vol = score_volatility_fit(volatility, ticker)

    total_score = round(s_trend + s_rr + s_dd + s_vol, 1)

    # 星级 + 标签
    stars = stars_from_score(total_score)
    emoji, tag_text = tag_from_score(total_score, ticker)

    # 均线状态
    ma_emoji, ma_text, ma_status = ma_bullish_status(ma20_val, ma50_val, ma200_val, latest)

    # 外链
    exchange_map = {
        "VOO": "AMEX", "QQQ": "NASDAQ", "IWM": "AMEX",
        "BND": "AMEX", "GLD": "AMEX",
        "SCHD": "AMEX", "VXUS": "AMEX", "SMH": "AMEX",
        "NVDA": "NASDAQ", "AAPL": "NASDAQ", "MSFT": "NASDAQ",
        "GOOGL": "NASDAQ", "AMZN": "NASDAQ", "META": "NASDAQ",
        "LLY": "NYSE", "BRK.B": "NYSE",
    }
    exchange = exchange_map.get(ticker, "NASDAQ")

    return {
        "ticker": ticker,
        "name": INVESTMENT_RATIONALE.get(ticker, ""),
        "rationale": INVESTMENT_RATIONALE.get(ticker, "暂无投资逻辑描述"),
        "score": total_score,
        "stars": stars,
        "star_emoji": "⭐" * stars,
        "tag_emoji": emoji,
        "tag": tag_text,
        "trend_score": round(s_trend, 1),
        "rr_score": round(s_rr, 1),
        "dd_score": round(s_dd, 1),
        "vol_score": round(s_vol, 1),
        "annual_return": annual_return,
        "volatility": volatility,
        "max_drawdown": round(max_dd, 2),
        "sharpe": sharpe,
        "ma20": round(ma20_val, 2) if ma20_val else None,
        "ma50": round(ma50_val, 2) if ma50_val else None,
        "ma200": round(ma200_val, 2) if ma200_val else None,
        "latest_close": round(latest, 2),
        "ma_emoji": ma_emoji,
        "ma_text": ma_text,
        "ma_status": ma_status,
        "links": {
            "yahoo": f"https://finance.yahoo.com/quote/{ticker}/",
            "tradingview": f"https://www.tradingview.com/symbols/{exchange}-{ticker}/",
            "seekingalpha": f"https://seekingalpha.com/symbol/{ticker}",
        },
    }


def compute_all_ratings(tickers: list) -> list:
    """
    计算所有标的的评级，按综合评分降序排列
    """
    results = []
    for ticker in tickers:
        rating = compute_rating(ticker)
        if rating:
            results.append(rating)
        else:
            print(f"  [WARN] {ticker} 数据不足，跳过评级")
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


# ── 工具函数 ───────────────────────────────────────────────

def get_top3(ratings: list) -> list:
    """获取本周最具价值 Top 3"""
    return ratings[:3]


if __name__ == "__main__":
    import json, sys
    sys.stdout.reconfigure(encoding='utf-8')
    tickers = ["VOO", "QQQ", "IWM", "BND", "GLD", "SCHD", "VXUS", "SMH",
               "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "LLY", "BRK.B"]
    ratings = compute_all_ratings(tickers)
    print(f"\n{'='*60}")
    print(f"\u8bc4\u7ea7\u7ed3\u679c\uff08\u5171 {len(ratings)} \u4e2a\u6807\u7684\uff09")
    print(f"{'='*60}")
    for r in ratings:
        print(f"{r['star_emoji']} {r['ticker']:6s} [{r['tag_emoji']}{r['tag']}] "
              f"\u7efc\u5408={r['score']:.1f} \u8d8b\u52bf={r['trend_score']:.0f} "
              f"\u98ce\u9669\u6536\u76ca={r['rr_score']:.0f} \u56de\u649e={r['dd_score']:.0f} "
              f"\u6ce2\u52a8\u7387={r['vol_score']:.0f}")
    print(f"\nTop3: {[r['ticker'] for r in get_top3(ratings)]}")
    # \u8f93\u51fa JSON \u4fdd\u5b58
    with open(ROOT / "ratings_output.json", "w", encoding="utf-8") as f:
        json.dump(ratings, f, ensure_ascii=False, indent=2)
    print(f"\u5df2\u4fdd\u5b58\u5230 ratings_output.json")
