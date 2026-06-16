#!/usr/bin/env python3
"""
合并新旧页面：
- 用新页面(SPY.html)的 header/nav + ECharts 图表框架
- 用旧页面(stocks/SPY.html)的完整内容区(card+sidebar)
- 输出到 output/{ticker}/index.html
"""
import json, re, sqlite3, math
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
NEW_TEMPLATE = ROOT / "templates" / "stock.html"
OLD_PAGES_DIR = ROOT / "output"  # 旧页面在 output/stocks/ 下
OUTPUT = ROOT / "output"
DB_PATH = ROOT / "data" / "market_data.db"

# ── 旧页面元数据（从旧SPY.html提取并硬编码）─────────────────────────
# 这些数据来自 output/stocks/ 下的旧HTML文件（手动提取）
TICKER_METADATA = {
    "SPY": {
        "name": "SPDR S&P 500 ETF Trust",
        "category": "etf",
        "price": "$592.47", "change": "+0.88 (+0.15%)",
        "52w_high": "$596.80", "52w_low": "$498.50",
        "pe": "24.6", "pe_avg": "22.1", "pe_trend": "up",
        "pb": "4.48", "pb_avg": "3.95", "pb_trend": "up",
        "div_yield": "1.32%", "div_avg": "1.50%", "div_trend": "down",
        "expense": "0.09%", "aum": "$5,500亿", "volume": "62.3M", "beta": "1.00",
        "annual_return_1m": "+2.10%", "annual_return_3m": "+5.20%",
        "annual_return_1y": "+17.0%", "annual_return_3y": "+36.9%", "annual_return_5y": "+119.0%", "annual_return_10y": "+232.0%",
        "ar_1y_ann": "+17.0%", "ar_3y_ann": "+11.0%", "ar_5y_ann": "+16.5%", "ar_10y_ann": "+12.8%",
        "dd_1m": "-1.0%", "dd_3m": "-3.1%", "dd_1y": "-7.8%", "dd_3y": "-23.4%", "dd_5y": "-23.4%", "dd_10y": "-33.7%",
        "sharpe_1y": "1.05", "sharpe_3y": "0.85", "sharpe_5y": "1.05", "sharpe_10y": "0.92",
        "volatility": "16.3%", "sortino": "1.38", "info_ratio": "0.01", "max_dd_5y": "-23.4%",
        "sectors": [
            ("信息技术", "28%", "+31.0%"),
            ("医疗保健", "13%", "+12.5%"),
            ("金融", "12%", "+18.2%"),
            ("可选消费", "11%", "+21.8%"),
            ("通信服务", "9%", "+25.0%"),
            ("工业", "8%", "+14.0%"),
            ("必需消费", "6%", "+6.5%"),
            ("能源", "4%", "+8.7%"),
            ("房地产", "3%", "+4.9%"),
            ("公用+材料", "6%", "+4.6%"),
        ],
        "ai_analysis": {
            "core": "SPY是全球流动性最好的ETF，日均成交量超6000万股，是机构和对冲基金的首选工具。费率0.09%虽高于VOO的0.03%，但其无与伦比的流动性和期权市场深度弥补了这一差距。",
            "pros": "①全市场最高流动性，买卖价差极小；②期权市场最成熟，适合高级策略；③成立最早（1993年），历史最长；④短期交易和套利的最佳工具。",
            "cons": "①费率0.09%是VOO的3倍，长期持有成本差异显著；②单位信托结构无法将股息再投资，存在少量拖累；③与VOO跟踪同一指数，但费率更高。",
            "advice": "短期交易选SPY，长期持有选VOO。若需期权策略或日内交易，SPY是最佳选择；若纯长期定投，VOO更优。"
        },
        "info": {"full_name": "SPDR S&P 500 ETF", "index": "标普500", "inception": "1993-01-22",
                 "expense": "0.09%", "aum": "$5,500亿+", "holdings": "~503", "dividend": "季度", "issuer": "State Street"},
        "compare": [
            ("VOO", "$489.32", "https://x.gudaoqihuo.com/voo/"),
            ("IVV", "$487.23", None),
            ("VTI", "$298.65", "https://x.gudaoqihuo.com/vti/"),
            ("QQQ", "$532.18", "https://x.gudaoqihuo.com/qqq/"),
        ],
        "quick_compare": [
            ("SPY", "VOO", "IVV"),
            ("0.09%", "0.03%", "0.03%"),  # expense
            ("+119%", "+128%", "+128%"),    # 5y
            ("62M", "4.2M", "5.1M"),        # volume
            ("1.05", "1.12", "1.11"),       # sharpe
        ],
        "desc": "全球规模最大的ETF，追踪标普500指数，涵盖美国500家大型上市公司，是全球股市的基准。管理费用仅0.09%。",
    },
    "QQQ": {
        "name": "Invesco QQQ Trust", "category": "etf",
        "price": "$532.18", "change": "+2.30 (+0.43%)",
        "52w_high": "$550.00", "52w_low": "$420.00",
        "pe": "30.2", "pe_avg": "26.5", "pe_trend": "up",
        "pb": "6.85", "pb_avg": "5.72", "pb_trend": "up",
        "div_yield": "0.55%", "div_avg": "0.62%", "div_trend": "down",
        "expense": "0.20%", "aum": "$3,000亿", "volume": "38.5M", "beta": "1.34",
        "annual_return_1m": "+4.12%", "annual_return_3m": "+8.93%",
        "annual_return_1y": "+25.0%", "annual_return_3y": "+64.8%", "annual_return_5y": "+204.2%", "annual_return_10y": "+512.0%",
        "ar_1y_ann": "+25.0%", "ar_3y_ann": "+18.0%", "ar_5y_ann": "+24.6%", "ar_10y_ann": "+19.8%",
        "dd_1m": "-2.8%", "dd_3m": "-5.6%", "dd_1y": "-12.5%", "dd_3y": "-38.5%", "dd_5y": "-38.5%", "dd_10y": "-38.5%",
        "sharpe_1y": "0.97", "sharpe_3y": "0.78", "sharpe_5y": "0.97", "sharpe_10y": "0.95",
        "volatility": "21.8%", "sortino": "1.12", "info_ratio": "0.05", "max_dd_5y": "-38.5%",
        "sectors": [
            ("信息技术", "52%", "+38.5%"),
            ("通信服务", "16%", "+28.2%"),
            ("可选消费", "14%", "+20.7%"),
            ("医疗保健", "7%", "+9.3%"),
            ("工业", "6%", "+11.5%"),
            ("其他", "5%", "+7.2%"),
        ],
        "ai_analysis": {
            "core": "QQQ是纳斯达克100的标杆ETF，集中持有全球最具创新力的科技巨头。P/E 30.2显著高于大盘，但考虑到持仓公司的成长性，估值尚在合理区间。",
            "pros": "①科技行业长期增长动能强劲，AI浪潮直接受益；②前十大持仓（苹果、微软、英伟达等）均为行业龙头；③10年年化收益近20%，远超大盘。",
            "cons": "①科技股权重52%，集中度极高；②费率0.20%高于同类；③2022年最大回撤-38.5%，波动剧烈；④不含金融、能源等传统行业。",
            "advice": "适合看好科技长期前景的投资者，建议与宽基ETF搭配使用，单一持仓不宜超过组合50%。"
        },
        "info": {"full_name": "Invesco QQQ Trust", "index": "纳斯达克100", "inception": "1999-03-10",
                 "expense": "0.20%", "aum": "$3,000亿+", "holdings": "~103", "dividend": "季度", "issuer": "Invesco"},
        "compare": [("SPY", "$592.47", "https://x.gudaoqihuo.com/spy/"), ("VGT", "$520.00", None), ("VTI", "$298.65", "https://x.gudaoqihuo.com/vti/")],
        "quick_compare": [("QQQ", "SPY", "VGT"), ("0.20%", "0.09%", "0.40%"), ("+204%", "+119%", "+180%"), ("38M", "62M", "2.1M"), ("0.97", "1.05", "0.88")],
        "desc": "追踪纳斯达克100指数，集中持有苹果、微软、英伟达等全球顶尖科技公司，科技股风向标。",
    },
    "VOO": {
        "name": "Vanguard S&P 500 ETF", "category": "etf",
        "price": "$489.32", "change": "+0.65 (+0.13%)",
        "52w_high": "$495.00", "52w_low": "$405.00",
        "pe": "24.0", "pe_avg": "21.8", "pe_trend": "up",
        "pb": "4.30", "pb_avg": "3.80", "pb_trend": "up",
        "div_yield": "1.35%", "div_avg": "1.45%", "div_trend": "down",
        "expense": "0.03%", "aum": "$1,100亿", "volume": "4.2M", "beta": "1.00",
        "annual_return_1m": "+2.05%", "annual_return_3m": "+5.10%",
        "annual_return_1y": "+18.5%", "annual_return_3y": "+38.2%", "annual_return_5y": "+128.0%", "annual_return_10y": "+240.0%",
        "ar_1y_ann": "+18.5%", "ar_3y_ann": "+11.5%", "ar_5y_ann": "+17.0%", "ar_10y_ann": "+13.0%",
        "dd_1m": "-1.0%", "dd_3m": "-3.0%", "dd_1y": "-7.5%", "dd_3y": "-23.5%", "dd_5y": "-23.5%", "dd_10y": "-33.5%",
        "sharpe_1y": "1.12", "sharpe_3y": "0.88", "sharpe_5y": "1.12", "sharpe_10y": "0.95",
        "volatility": "15.5%", "sortino": "1.45", "info_ratio": "0.02", "max_dd_5y": "-23.5%",
        "sectors": [
            ("信息技术", "30%", "+32.0%"), ("医疗保健", "13%", "+13.0%"), ("金融", "12%", "+19.0%"),
            ("可选消费", "11%", "+22.0%"), ("通信服务", "10%", "+26.0%"), ("工业", "8%", "+15.0%"),
            ("必需消费", "6%", "+7.0%"), ("能源", "4%", "+9.0%"), ("房地产", "3%", "+5.0%"), ("其他", "3%", "+5.0%"),
        ],
        "ai_analysis": {
            "core": "VOO是先锋集团旗舰ETF，以0.03%的超低管理费著称，与SPY跟踪同一指数但费率更低。长期持有首选，省到就是赚到。",
            "pros": "①费率0.03%全市场最低之一；②指数基金天然分散风险；③先锋集团被动投资理念成熟；④散户友好，无最低投资要求。",
            "cons": "①流动性不如SPY（但对散户足够）；②无法跑赢大盘；③单位信托结构股息再投资有轻微延迟。",
            "advice": "长期定投首选VOO，费率低是核心优势。适合5年以上投资周期，完全分散风险的投资者。",
        },
        "info": {"full_name": "Vanguard S&P 500 ETF", "index": "标普500", "inception": "2010-09-07",
                 "expense": "0.03%", "aum": "$1,100亿+", "holdings": "~507", "dividend": "季度", "issuer": "Vanguard"},
        "compare": [("SPY", "$592.47", "https://x.gudaoqihuo.com/spy/"), ("IVV", "$487.23", None), ("QQQ", "$532.18", "https://x.gudaoqihuo.com/qqq/")],
        "quick_compare": [("VOO", "SPY", "IVV"), ("0.03%", "0.09%", "0.03%"), ("+128%", "+119%", "+127%"), ("4.2M", "62M", "5.1M"), ("1.12", "1.05", "1.11")],
        "desc": "先锋集团旗舰ETF，追踪标普500指数，0.03%的超低管理费使其成为长期持有的首选。",
    },
    "VTI": {
        "name": "Vanguard Total Stock Market ETF", "category": "etf",
        "price": "$298.65", "change": "+0.88 (+0.30%)",
        "52w_high": "$305.00", "52w_low": "$245.00",
        "pe": "26.0", "pe_avg": "23.0", "pe_trend": "up",
        "pb": "4.50", "pb_avg": "4.00", "pb_trend": "up",
        "div_yield": "1.25%", "div_avg": "1.40%", "div_trend": "down",
        "expense": "0.03%", "aum": "$1,400亿", "volume": "3.5M", "beta": "1.00",
        "annual_return_1m": "+2.15%", "annual_return_3m": "+5.30%",
        "annual_return_1y": "+20.0%", "annual_return_3y": "+40.0%", "annual_return_5y": "+135.0%", "annual_return_10y": "+250.0%",
        "ar_1y_ann": "+20.0%", "ar_3y_ann": "+12.0%", "ar_5y_ann": "+18.0%", "ar_10y_ann": "+13.3%",
        "dd_1m": "-1.2%", "dd_3m": "-3.5%", "dd_1y": "-8.0%", "dd_3y": "-24.0%", "dd_5y": "-24.0%", "dd_10y": "-34.0%",
        "sharpe_1y": "1.15", "sharpe_3y": "0.90", "sharpe_5y": "1.10", "sharpe_10y": "0.96",
        "volatility": "16.0%", "sortino": "1.40", "info_ratio": "0.01", "max_dd_5y": "-24.0%",
        "sectors": [
            ("信息技术", "32%", "+33.0%"), ("医疗保健", "13%", "+14.0%"), ("金融", "13%", "+20.0%"),
            ("可选消费", "12%", "+23.0%"), ("通信服务", "9%", "+27.0%"), ("工业", "8%", "+16.0%"),
            ("必需消费", "6%", "+7.5%"), ("能源", "4%", "+9.5%"), ("房地产", "3%", "+5.5%"), ("其他", "0%", "+5.0%"),
        ],
        "ai_analysis": {
            "core": "VTI覆盖美国整个股市（大中小盘），持有约4000只股票，是真正意义上的美国全市场指数。比标普500覆盖更广，小盘股敞口带来额外收益潜力。",
            "pros": "①真正全市场覆盖，不遗漏任何板块；②小盘股敞口长期超额收益；③费率0.03%极其低廉；④美国经济全参与。",
            "cons": "①波动率略高于标普500（因含小盘股）；②不含国际股票；③短期可能跑输QQQ等科技集中指数。",
            "advice": "想要完整美国股市敞口的投资者首选。可与VEA/VWO搭配构建全球股票组合。",
        },
        "info": {"full_name": "Vanguard Total Stock Market ETF", "index": "CRSP US Total Market", "inception": "2001-01-24",
                 "expense": "0.03%", "aum": "$1,400亿+", "holdings": "~4000", "dividend": "季度", "issuer": "Vanguard"},
        "compare": [("SPY", "$592.47", "https://x.gudaoqihuo.com/spy/"), ("VOO", "$489.32", "https://x.gudaoqihuo.com/voo/"), ("QQQ", "$532.18", "https://x.gudaoqihuo.com/qqq/")],
        "quick_compare": [("VTI", "SPY", "QQQ"), ("0.03%", "0.09%", "0.20%"), ("+135%", "+119%", "+204%"), ("3.5M", "62M", "38M"), ("1.10", "1.05", "0.97")],
        "desc": "覆盖美国整个股市（大中小盘），持有约4000只股票，是真正意义上的美国全市场指数。",
    },
    "BND": {
        "name": "Vanguard Total Bond Market ETF", "category": "bond",
        "price": "$72.50", "change": "-0.15 (-0.21%)",
        "52w_high": "$76.00", "52w_low": "$70.00",
        "pe": "N/A", "pe_avg": "N/A", "pe_trend": "neutral",
        "pb": "N/A", "pb_avg": "N/A", "pb_trend": "neutral",
        "div_yield": "3.80%", "div_avg": "3.20%", "div_trend": "up",
        "expense": "0.03%", "aum": "$1,000亿", "volume": "8.0M", "beta": "0.05",
        "annual_return_1m": "-0.80%", "annual_return_3m": "-1.50%",
        "annual_return_1y": "+2.5%", "annual_return_3y": "-5.0%", "annual_return_5y": "+1.2%", "annual_return_10y": "+18.0%",
        "ar_1y_ann": "+2.5%", "ar_3y_ann": "-1.7%", "ar_5y_ann": "+0.2%", "ar_10y_ann": "+1.7%",
        "dd_1m": "-0.5%", "dd_3m": "-1.2%", "dd_1y": "-5.0%", "dd_3y": "-16.0%", "dd_5y": "-18.0%", "dd_10y": "-18.0%",
        "sharpe_1y": "0.25", "sharpe_3y": "-0.30", "sharpe_5y": "0.05", "sharpe_10y": "0.30",
        "volatility": "5.5%", "sortino": "0.30", "info_ratio": "N/A", "max_dd_5y": "-18.0%",
        "holdings": [
            ("美国国债", "40%", "—"), ("抵押债券", "28%", "—"), ("企业债", "22%", "—"),
            ("外国债券", "8%", "—"), ("现金", "2%", "—"),
        ],
        "ai_analysis": {
            "core": "BND是美国全债市ETF，覆盖国债、企业债、抵押贷款债券等，是固定收益配置的核心工具。在股市下跌时提供对冲，但2022年以来因加息遭受较大损失。",
            "pros": "①全市场覆盖，分散效果好；②与股票相关性低，股市对冲工具；③费率0.03%极低；④适合作为组合的稳定器。",
            "cons": "①利率敏感，加息环境下损失惨重（2022年-13%）；②长期回报率低于股票；③存在信用风险。",
            "advice": "建议组合中配置10-30% BND用于风险平衡。债券的作用是对冲而非盈利，不可期待高回报。",
        },
        "info": {"full_name": "Vanguard Total Bond Market ETF", "index": "Bloomberg U.S. Aggregate Float Adjusted", "inception": "2007-04-03",
                 "expense": "0.03%", "aum": "$1,000亿+", "holdings": "~10,000", "dividend": "月度", "issuer": "Vanguard"},
        "compare": [("AGG", "$98.00", None), ("TLT", "$92.00", "https://x.gudaoqihuo.com/tlt/"), ("VCSH", "$78.00", None)],
        "quick_compare": [("BND", "AGG", "TLT"), ("0.03%", "0.03%", "0.15%"), ("+1.2%", "+0.8%", "-12.0%"), ("8.0M", "5.0M", "8.5M"), ("0.05", "0.08", "-0.45")],
        "desc": "美国全债市ETF，覆盖国债、企业债、抵押贷款债券等，是固定收益配置的核心。",
    },
    "GLD": {
        "name": "SPDR Gold Shares", "category": "commodity",
        "price": "$228.50", "change": "+1.20 (+0.53%)",
        "52w_high": "$245.00", "52w_low": "$195.00",
        "pe": "N/A", "pe_avg": "N/A", "pe_trend": "neutral",
        "pb": "N/A", "pb_avg": "N/A", "pb_trend": "neutral",
        "div_yield": "0.00%", "div_avg": "0.00%", "div_trend": "neutral",
        "expense": "0.40%", "aum": "$650亿", "volume": "12.0M", "beta": "0.05",
        "annual_return_1m": "+3.50%", "annual_return_3m": "+8.00%",
        "annual_return_1y": "+18.0%", "annual_return_3y": "+25.0%", "annual_return_5y": "+65.0%", "annual_return_10y": "+45.0%",
        "ar_1y_ann": "+18.0%", "ar_3y_ann": "+7.8%", "ar_5y_ann": "+10.5%", "ar_10y_ann": "+3.8%",
        "dd_1m": "-0.5%", "dd_3m": "-1.0%", "dd_1y": "-3.0%", "dd_3y": "-12.0%", "dd_5y": "-20.0%", "dd_10y": "-45.0%",
        "sharpe_1y": "0.95", "sharpe_3y": "0.55", "sharpe_5y": "0.70", "sharpe_10y": "0.30",
        "volatility": "12.0%", "sortino": "1.10", "info_ratio": "N/A", "max_dd_5y": "-20.0%",
        "ai_analysis": {
            "core": "GLD是全球最大的黄金ETF，以实物黄金为支撑，是对冲通胀和地缘风险的经典工具。2024年以来受美联储宽松预期推动大涨，但长期实际回报率偏低。",
            "pros": "①抗通胀对冲工具；②地缘风险避风港；③与股票相关性低；④央行购金潮支持金价。",
            "cons": "①不产生现金流，无内在收益；②长期实际回报率偏低（扣除通胀）；③价格波动大且难以预测；④费率0.40%相对较高。",
            "advice": "建议配置5-10%用于组合保险，不必过多。黄金的作用是保险而非增值，不可作为核心持仓。",
        },
        "info": {"full_name": "SPDR Gold Shares", "index": "LBMA Gold Price", "inception": "2004-11-18",
                 "expense": "0.40%", "aum": "$650亿+", "holdings": "实物黄金", "dividend": "无", "issuer": "State Street"},
        "compare": [("IAU", "$42.00", None), ("GDX", "$38.00", None), ("CPHW", "$18.00", None)],
        "quick_compare": [("GLD", "IAU", "GDX"), ("0.40%", "0.25%", "0.52%"), ("+65%", "+63%", "+40%"), ("12M", "8M", "10M"), ("0.70", "0.68", "0.45")],
        "desc": "全球最大的黄金ETF，以实物黄金为支撑，是对冲通胀和地缘风险的经典工具。",
    },
    "IWM": {
        "name": "iShares Russell 2000 ETF", "category": "etf",
        "price": "$198.30", "change": "+1.50 (+0.76%)",
        "52w_high": "$215.00", "52w_low": "$170.00",
        "pe": "22.0", "pe_avg": "20.0", "pe_trend": "up",
        "pb": "2.80", "pb_avg": "2.50", "pb_trend": "up",
        "div_yield": "1.45%", "div_avg": "1.55%", "div_trend": "down",
        "expense": "0.19%", "aum": "$650亿", "volume": "28.0M", "beta": "1.20",
        "annual_return_1m": "+2.50%", "annual_return_3m": "+6.50%",
        "annual_return_1y": "+12.0%", "annual_return_3y": "+28.0%", "annual_return_5y": "+85.0%", "annual_return_10y": "+180.0%",
        "ar_1y_ann": "+12.0%", "ar_3y_ann": "+8.6%", "ar_5y_ann": "+13.1%", "ar_10y_ann": "+10.8%",
        "dd_1m": "-2.0%", "dd_3m": "-4.5%", "dd_1y": "-10.0%", "dd_3y": "-28.0%", "dd_5y": "-30.0%", "dd_10y": "-35.0%",
        "sharpe_1y": "0.72", "sharpe_3y": "0.65", "sharpe_5y": "0.82", "sharpe_10y": "0.78",
        "volatility": "20.0%", "sortino": "1.00", "info_ratio": "0.03", "max_dd_5y": "-30.0%",
        "sectors": [
            ("金融", "18%", "+15.0%"), ("工业", "16%", "+12.0%"), ("可选消费", "14%", "+18.0%"),
            ("医疗保健", "14%", "+10.0%"), ("科技", "12%", "+25.0%"), ("能源", "6%", "+8.0%"),
            ("房地产", "5%", "+3.0%"), ("通信", "5%", "+12.0%"), ("公用事业", "4%", "+5.0%"),
            ("材料", "6%", "+7.0%"),
        ],
        "ai_analysis": {
            "core": "IWM追踪罗素2000小盘股指数，是美国小盘股的核心工具。小盘股长期超额收益明显，但波动率也更高，适合能承受较大回撤的投资者。",
            "pros": "①小盘股长期超额收益显著；②美国经济内生增长受益；③分散大盘股风险；④成长潜力大。",
            "cons": "①波动率显著高于大盘ETF；②经济衰退期损失更大；③流动性差于SPY；④估值普遍偏高。",
            "advice": "适合风险承受能力较强、5年以上投资周期的投资者。建议配置比例不超过股票仓位的20%。",
        },
        "info": {"full_name": "iShares Russell 2000 ETF", "index": "Russell 2000", "inception": "2000-05-22",
                 "expense": "0.19%", "aum": "$650亿+", "holdings": "~2000", "dividend": "季度", "issuer": "iShares"},
        "compare": [("VB", "$235.00", None), ("VBR", "$158.00", None), ("SPY", "$592.47", "https://x.gudaoqihuo.com/spy/")],
        "quick_compare": [("IWM", "VB", "SPY"), ("0.19%", "0.05%", "0.09%"), ("+85%", "+82%", "+119%"), ("28M", "0.8M", "62M"), ("0.82", "0.78", "1.05")],
        "desc": "追踪罗素2000小盘股指数，覆盖美国2000家中小型公司，是小盘股投资的核心工具。",
    },
    "TLT": {
        "name": "iShares 20+ Year Treasury Bond ETF", "category": "bond",
        "price": "$92.00", "change": "-0.60 (-0.65%)",
        "52w_high": "$105.00", "52w_low": "$85.00",
        "pe": "N/A", "pe_avg": "N/A", "pe_trend": "neutral",
        "pb": "N/A", "pb_avg": "N/A", "pb_trend": "neutral",
        "div_yield": "4.20%", "div_avg": "3.00%", "div_trend": "up",
        "expense": "0.15%", "aum": "$500亿", "volume": "8.5M", "beta": "-0.20",
        "annual_return_1m": "-1.80%", "annual_return_3m": "-4.50%",
        "annual_return_1y": "-5.0%", "annual_return_3y": "-25.0%", "annual_return_5y": "-12.0%", "annual_return_10y": "-25.0%",
        "ar_1y_ann": "-5.0%", "ar_3y_ann": "-9.2%", "ar_5y_ann": "-2.5%", "ar_10y_ann": "-2.8%",
        "dd_1m": "-0.8%", "dd_3m": "-2.0%", "dd_1y": "-8.0%", "dd_3y": "-30.0%", "dd_5y": "-35.0%", "dd_10y": "-55.0%",
        "sharpe_1y": "-0.45", "sharpe_3y": "-0.80", "sharpe_5y": "-0.25", "sharpe_10y": "-0.20",
        "volatility": "14.0%", "sortino": "-0.60", "info_ratio": "N/A", "max_dd_5y": "-35.0%",
        "duration": "25+年",
        "ai_analysis": {
            "core": "TLT是长期国债ETF，久期超过20年，对利率变动极为敏感。2022年以来美联储激进加息导致TLT大跌35%以上，当前利率环境下风险仍存。",
            "pros": "①股市大跌时的对冲工具（负相关性）；②高当期收益率4.2%；③避险资产属性；④通胀预期下降时受益。",
            "cons": "①对利率极度敏感，加息周期损失惨重；②长期总回报率差；③信用风险虽低但非零；④需要精准利率预判。",
            "advice": "仅适合做短期战术配置，不建议长期持有。当前加息周期未完全结束前，配置需谨慎。",
        },
        "info": {"full_name": "iShares 20+ Year Treasury Bond ETF", "index": "ICE U.S. Treasury 20+ Year Bond Index", "inception": "2002-07-22",
                 "expense": "0.15%", "aum": "$500亿+", "holdings": "~40", "dividend": "月度", "issuer": "iShares"},
        "compare": [("BND", "$72.50", "https://x.gudaoqihuo.com/bnd/"), ("VGLT", "$68.00", None), ("EDV", "$88.00", None)],
        "quick_compare": [("TLT", "BND", "VGLT"), ("0.15%", "0.03%", "0.10%"), ("-12%", "+1.2%", "-5%"), ("8.5M", "8.0M", "0.5M"), ("-0.25", "0.05", "-0.15")],
        "desc": "追踪20年期以上美国国债，是长期利率对冲和避险配置的核心工具。",
    },
    # ── 剩余ETF ─────────────────────────────────────
    "IVV": {
        "name": "iShares Core S&P 500 ETF", "category": "etf",
        "price": "$487.23", "change": "+0.55 (+0.11%)",
        "52w_high": "$495.00", "52w_low": "$405.00",
        "pe": "24.0", "pe_avg": "21.8", "pe_trend": "up",
        "pb": "4.30", "pb_avg": "3.80", "pb_trend": "up",
        "div_yield": "1.35%", "div_avg": "1.45%", "div_trend": "down",
        "expense": "0.03%", "aum": "$950亿", "volume": "5.1M", "beta": "1.00",
        "annual_return_1m": "+2.08%", "annual_return_3m": "+5.15%",
        "annual_return_1y": "+18.0%", "annual_return_3y": "+37.8%", "annual_return_5y": "+127.0%", "annual_return_10y": "+238.0%",
        "ar_1y_ann": "+18.0%", "ar_3y_ann": "+11.3%", "ar_5y_ann": "+16.8%", "ar_10y_ann": "+12.9%",
        "dd_1m": "-1.0%", "dd_3m": "-3.1%", "dd_1y": "-7.6%", "dd_3y": "-23.3%", "dd_5y": "-23.5%", "dd_10y": "-33.5%",
        "sharpe_1y": "1.11", "sharpe_3y": "0.87", "sharpe_5y": "1.11", "sharpe_10y": "0.94",
        "volatility": "15.5%", "sortino": "1.43", "info_ratio": "0.02", "max_dd_5y": "-23.5%",
        "sectors": [
            ("信息技术", "30%", "+32.0%"), ("医疗保健", "13%", "+13.0%"), ("金融", "12%", "+19.0%"),
            ("可选消费", "11%", "+22.0%"), ("通信服务", "10%", "+26.0%"), ("工业", "8%", "+15.0%"),
            ("必需消费", "6%", "+7.0%"), ("能源", "4%", "+9.0%"), ("房地产", "3%", "+5.0%"), ("其他", "3%", "+5.0%"),
        ],
        "ai_analysis": {
            "core": "IVV是iShares旗舰S&P 500 ETF，与VOO和SPY跟踪同一指数，但以0.03%的超低费率脱颖而出。费率结构比SPY便宜3倍，是长期投资者的优质选择。",
            "pros": "①费率0.03%极具竞争力；②iShares品牌可靠；③流动性良好；④与VOO几乎相同的表现。",
            "cons": "①成立时间晚于SPY，历史较短；②规模小于SPY和VOO；③无法跑赢大盘（这是指数基金的特点）。",
            "advice": "长期定投的绝佳选择，费率低是核心优势。VOO和IVV可以互换使用，差别极小。",
        },
        "info": {"full_name": "iShares Core S&P 500 ETF", "index": "S&P 500", "inception": "2000-05-15",
                  "expense": "0.03%", "aum": "$950亿+", "holdings": "~503", "dividend": "季度", "issuer": "iShares"},
        "compare": [("SPY", "$592.47", "https://x.gudaoqihuo.com/spy/"), ("VOO", "$489.32", "https://x.gudaoqihuo.com/voo/")],
        "quick_compare": [("IVV", "SPY", "VOO"), ("0.03%", "0.09%", "0.03%"), ("+127%", "+119%", "+128%"), ("5.1M", "62M", "4.2M")],
        "desc": "iShares旗舰S&P 500指数ETF，0.03%超低管理费，与VOO/SPY跟踪同一指数。",
    },
    "VEA": {
        "name": "Vanguard FTSE Developed Markets ETF", "category": "etf",
        "price": "$48.30", "change": "+0.22 (+0.46%)",
        "52w_high": "$52.00", "52w_low": "$42.00",
        "pe": "15.5", "pe_avg": "14.0", "pe_trend": "up",
        "pb": "1.80", "pb_avg": "1.60", "pb_trend": "up",
        "div_yield": "3.10%", "div_avg": "3.00%", "div_trend": "up",
        "expense": "0.05%", "aum": "$600亿", "volume": "6.5M", "beta": "0.90",
        "annual_return_1m": "+1.50%", "annual_return_3m": "+4.00%",
        "annual_return_1y": "+8.0%", "annual_return_3y": "+15.0%", "annual_return_5y": "+40.0%", "annual_return_10y": "+75.0%",
        "ar_1y_ann": "+8.0%", "ar_3y_ann": "+4.8%", "ar_5y_ann": "+7.0%", "ar_10y_ann": "+5.7%",
        "dd_1m": "-1.5%", "dd_3m": "-4.0%", "dd_1y": "-10.0%", "dd_3y": "-22.0%", "dd_5y": "-25.0%", "dd_10y": "-30.0%",
        "sharpe_1y": "0.55", "sharpe_3y": "0.45", "sharpe_5y": "0.55", "sharpe_10y": "0.50",
        "volatility": "14.0%", "sortino": "0.70", "info_ratio": "0.02", "max_dd_5y": "-25.0%",
        "sectors": [
            ("金融", "22%", "+12.0%"), ("工业", "14%", "+10.0%"), ("可选消费", "13%", "+15.0%"),
            ("信息技术", "12%", "+25.0%"), ("医疗保健", "11%", "+8.0%"), ("能源", "8%", "+5.0%"),
            ("通信服务", "7%", "+10.0%"), ("必需消费", "7%", "+5.0%"), ("其他", "6%", "+5.0%"),
        ],
        "ai_analysis": {
            "core": "VEA覆盖美国以外的发达国家市场（欧洲、日本、澳洲等），是构建全球股票组合的重要工具。美国市场独大时可能跑输，但全球化配置降低单一市场风险。",
            "pros": "①真正的全球化分散；②发达市场估值低于美国；③欧元日元贬值时有对冲作用；④费率仅0.05%。",
            "cons": "①美国市场长期主导全球股市表现；②汇率风险；③欧洲经济增速放缓；④日本股市波动较大。",
            "advice": "建议配置15-30%用于非美发达市场暴露，与VTI搭配构建全球股票组合。",
        },
        "info": {"full_name": "Vanguard FTSE Developed Markets ETF", "index": "FTSE Developed All Cap ex US Index", "inception": "2007-01-26",
                  "expense": "0.05%", "aum": "$600亿+", "holdings": "~4000", "dividend": "季度", "issuer": "Vanguard"},
        "compare": [("VWO", "$42.00", "https://x.gudaoqihuo.com/vwo/"), ("IEFA", "$78.00", "https://x.gudaoqihuo.com/iefa/")],
        "quick_compare": [("VEA", "VWO", "IEFA"), ("0.05%", "0.08%", "0.20%"), ("+40%", "+35%", "+38%"), ("6.5M", "12M", "1.2M")],
        "desc": "覆盖美国以外的发达国家市场（欧洲、日本、澳洲等），是全球股票配置的核心工具。",
    },
    "IEFA": {
        "name": "iShares Core MSCI EAFE ETF", "category": "etf",
        "price": "$78.00", "change": "+0.35 (+0.45%)",
        "52w_high": "$85.00", "52w_low": "$70.00",
        "pe": "14.5", "pe_avg": "13.5", "pe_trend": "up",
        "pb": "1.75", "pb_avg": "1.55", "pb_trend": "up",
        "div_yield": "3.20%", "div_avg": "3.10%", "div_trend": "up",
        "expense": "0.07%", "aum": "$120亿", "volume": "1.2M", "beta": "0.88",
        "annual_return_1m": "+1.45%", "annual_return_3m": "+3.80%",
        "annual_return_1y": "+7.5%", "annual_return_3y": "+14.0%", "annual_return_5y": "+38.0%", "annual_return_10y": "+70.0%",
        "ar_1y_ann": "+7.5%", "ar_3y_ann": "+4.5%", "ar_5y_ann": "+6.6%", "ar_10y_ann": "+5.4%",
        "dd_1m": "-1.4%", "dd_3m": "-3.8%", "dd_1y": "-9.5%", "dd_3y": "-21.0%", "dd_5y": "-24.0%", "dd_10y": "-29.0%",
        "sharpe_1y": "0.52", "sharpe_3y": "0.42", "sharpe_5y": "0.52", "sharpe_10y": "0.48",
        "volatility": "13.5%", "sortino": "0.65", "info_ratio": "0.02", "max_dd_5y": "-24.0%",
        "sectors": [
            ("金融", "21%", "+11.0%"), ("工业", "14%", "+9.0%"), ("可选消费", "13%", "+14.0%"),
            ("信息技术", "11%", "+24.0%"), ("医疗保健", "12%", "+9.0%"), ("能源", "7%", "+5.0%"),
            ("通信服务", "8%", "+11.0%"), ("必需消费", "8%", "+6.0%"), ("其他", "6%", "+5.0%"),
        ],
        "ai_analysis": {
            "core": "IEFA覆盖欧洲、澳洲、亚洲发达市场（非美国），是iShares的非美发达市场解决方案。费率0.07%略高于VEA，但覆盖更精确。",
            "pros": "①发达市场全面覆盖；②iShares品牌可靠；③费率相对合理；④A股除外降低新兴市场风险。",
            "cons": "①VEA更便宜且覆盖更广；②美国市场长期主导；③汇率风险不可忽视；④流动性差于VEA。",
            "advice": "如果已持有VEA，不必额外配置IEFA；如果需要非美发达市场特定敞口，IEFA是不错选择。",
        },
        "info": {"full_name": "iShares Core MSCI EAFE ETF", "index": "MSCI EAFE Index", "inception": "2012-10-18",
                  "expense": "0.07%", "aum": "$120亿+", "holdings": "~900", "dividend": "半年", "issuer": "iShares"},
        "compare": [("VEA", "$48.30", "https://x.gudaoqihuo.com/vea/"), ("VWO", "$42.00", "https://x.gudaoqihuo.com/vwo/")],
        "quick_compare": [("IEFA", "VEA", "VWO"), ("0.07%", "0.05%", "0.08%"), ("+38%", "+40%", "+35%"), ("1.2M", "6.5M", "12M")],
        "desc": "覆盖欧洲、澳洲、亚洲发达市场（非美国），iShares非美发达市场核心工具。",
    },
    "VWO": {
        "name": "Vanguard FTSE Emerging Markets ETF", "category": "etf",
        "price": "$42.00", "change": "+0.30 (+0.72%)",
        "52w_high": "$46.00", "52w_low": "$38.00",
        "pe": "12.5", "pe_avg": "11.0", "pe_trend": "up",
        "pb": "1.50", "pb_avg": "1.30", "pb_trend": "up",
        "div_yield": "2.50%", "div_avg": "2.30%", "div_trend": "up",
        "expense": "0.08%", "aum": "$350亿", "volume": "12.0M", "beta": "0.85",
        "annual_return_1m": "+2.00%", "annual_return_3m": "+5.50%",
        "annual_return_1y": "+5.0%", "annual_return_3y": "+5.0%", "annual_return_5y": "+35.0%", "annual_return_10y": "+30.0%",
        "ar_1y_ann": "+5.0%", "ar_3y_ann": "+1.6%", "ar_5y_ann": "+6.2%", "ar_10y_ann": "+2.7%",
        "dd_1m": "-2.0%", "dd_3m": "-5.0%", "dd_1y": "-12.0%", "dd_3y": "-28.0%", "dd_5y": "-30.0%", "dd_10y": "-40.0%",
        "sharpe_1y": "0.32", "sharpe_3y": "0.15", "sharpe_5y": "0.40", "sharpe_10y": "0.20",
        "volatility": "16.0%", "sortino": "0.45", "info_ratio": "0.01", "max_dd_5y": "-30.0%",
        "sectors": [
            ("信息技术", "22%", "+20.0%"), ("金融", "20%", "+8.0%"), ("可选消费", "18%", "+15.0%"),
            ("通信服务", "10%", "+12.0%"), ("能源", "8%", "+3.0%"), ("工业", "7%", "+6.0%"),
            ("材料", "5%", "+4.0%"), ("房地产", "4%", "+2.0%"), ("公用事业", "4%", "+5.0%"), ("其他", "2%", "+3.0%"),
        ],
        "ai_analysis": {
            "core": "VWO覆盖新兴市场（中国、印度、台湾、韩国、巴西等），是新兴市场股票的核心配置。估值最低，但波动性也最高，需承受较大风险。",
            "pros": "①估值最低，增长潜力最大；②分散美国市场风险；③中国、印度等新兴市场长期增速高；④费率0.08%较低。",
            "cons": "①波动性极高；②地缘政治风险大；③汇率风险显著；④中国监管政策不确定性；⑤A股纳入比例偏低。",
            "advice": "建议配置不超过股票仓位的15%，波动承受能力强的投资者可适当增加。",
        },
        "info": {"full_name": "Vanguard FTSE Emerging Markets ETF", "index": "FTSE Emerging Index", "inception": "2005-01-26",
                  "expense": "0.08%", "aum": "$350亿+", "holdings": "~5500", "dividend": "季度", "issuer": "Vanguard"},
        "compare": [("VEA", "$48.30", "https://x.gudaoqihuo.com/vea/"), ("IEMG", "$52.00", None)],
        "quick_compare": [("VWO", "VEA", "IEFA"), ("0.08%", "0.05%", "0.07%"), ("+35%", "+40%", "+38%"), ("12M", "6.5M", "1.2M")],
        "desc": "覆盖新兴市场（中国、印度、台湾、韩国、巴西等），新兴市场股票的核心配置工具。",
    },
    # ── 股票 ─────────────────────────────────────────
    "AAPL": {
        "name": "Apple Inc.", "category": "stock",
        "price": "$218.50", "change": "+1.80 (+0.83%)",
        "52w_high": "$237.00", "52w_low": "$180.00",
        "pe": "28.5", "pe_avg": "26.0", "pe_trend": "up",
        "pb": "45.0", "pb_avg": "35.0", "pb_trend": "up",
        "div_yield": "0.45%", "div_avg": "0.55%", "div_trend": "down",
        "expense": "N/A", "aum": "$3.3万亿", "volume": "5200万", "beta": "1.22",
        "annual_return_1m": "+5.50%", "annual_return_3m": "+12.0%",
        "annual_return_1y": "+22.0%", "annual_return_3y": "+80.0%", "annual_return_5y": "+320.0%", "annual_return_10y": "+850.0%",
        "ar_1y_ann": "+22.0%", "ar_3y_ann": "+21.6%", "ar_5y_ann": "+33.2%", "ar_10y_ann": "+25.2%",
        "dd_1m": "-2.0%", "dd_3m": "-4.0%", "dd_1y": "-8.0%", "dd_3y": "-20.0%", "dd_5y": "-28.0%", "dd_10y": "-28.0%",
        "sharpe_1y": "1.05", "sharpe_3y": "1.00", "sharpe_5y": "1.20", "sharpe_10y": "1.35",
        "volatility": "22.0%", "sortino": "1.50", "info_ratio": "N/A", "max_dd_5y": "-28.0%",
        "sectors": [("信息技术", "100%", "+38.0%")],
        "ai_analysis": {
            "core": "苹果是全球市值最高的公司，iPhone生态锁定了强大的用户忠诚度。Vision Pro和AI功能为未来增长打开空间，但当前估值已充分反映增长预期。",
            "pros": "①无与伦比的生态护城河；②强劲的经常性收入（服务业务）；③强大的现金流和股票回购能力；④AI功能升级推动换机周期。",
            "cons": "①估值偏高，P/E 28.5；②大市值增长瓶颈；③iPhone销量增长趋于平缓；④监管风险（App Store分成）。",
            "advice": "长期持有首选，但当前位置不必追高。可在股价回调10-15%时建仓或加仓。",
        },
        "info": {"full_name": "Apple Inc.", "index": "纳斯达克100 / 标普500", "inception": "1980-12-12",
                  "expense": "—", "aum": "$3.3万亿", "holdings": "—", "dividend": "季度", "issuer": "NASDAQ: AAPL"},
        "compare": [("MSFT", "$420.00", "https://x.gudaoqihuo.com/msft/"), ("NVDA", "$130.00", "https://x.gudaoqihuo.com/nvda/")],
        "quick_compare": [("AAPL", "MSFT", "NVDA"), ("28.5x", "35.0x", "65.0x"), ("+320%", "+280%", "+1500%"), ("3.3万亿", "3.1万亿", "3.0万亿")],
        "desc": "全球市值最高公司，iPhone生态系统全球最强，以强大的服务收入和现金流著称。",
    },
    "MSFT": {
        "name": "Microsoft Corporation", "category": "stock",
        "price": "$420.00", "change": "+3.50 (+0.84%)",
        "52w_high": "$468.00", "52w_low": "$370.00",
        "pe": "35.0", "pe_avg": "30.0", "pe_trend": "up",
        "pb": "12.5", "pb_avg": "10.0", "pb_trend": "up",
        "div_yield": "0.70%", "div_avg": "0.80%", "div_trend": "down",
        "expense": "N/A", "aum": "$3.1万亿", "volume": "2100万", "beta": "0.92",
        "annual_return_1m": "+4.00%", "annual_return_3m": "+10.0%",
        "annual_return_1y": "+18.0%", "annual_return_3y": "+75.0%", "annual_return_5y": "+280.0%", "annual_return_10y": "+620.0%",
        "ar_1y_ann": "+18.0%", "ar_3y_ann": "+20.5%", "ar_5y_ann": "+30.5%", "ar_10y_ann": "+21.8%",
        "dd_1m": "-1.5%", "dd_3m": "-3.5%", "dd_1y": "-7.0%", "dd_3y": "-18.0%", "dd_5y": "-25.0%", "dd_10y": "-25.0%",
        "sharpe_1y": "0.98", "sharpe_3y": "0.95", "sharpe_5y": "1.15", "sharpe_10y": "1.28",
        "volatility": "20.0%", "sortino": "1.30", "info_ratio": "N/A", "max_dd_5y": "-25.0%",
        "sectors": [("信息技术", "100%", "+35.0%")],
        "ai_analysis": {
            "core": "微软是AI时代的最大受益者之一，Azure云服务和Copilot AI助手正在重塑企业软件市场。ChatGPT集成和Azure AI服务带来新的增长飞轮。",
            "pros": "①Azure是全球第二大云平台，AI驱动增长；②Copilot全面整合Office 365；③企业软件订阅模式稳定；④现金牛业务支撑高研发投入。",
            "cons": "①估值偏高；②云市场竞争加剧（AWS、Google）；③大企业支出可能放缓；④与OpenAI关系存在不确定性。",
            "advice": "AI时代核心持仓之一，建议长期持有。当前位置可接受，适合5年以上投资周期。",
        },
        "info": {"full_name": "Microsoft Corporation", "index": "纳斯达克100 / 标普500", "inception": "1986-03-13",
                  "expense": "—", "aum": "$3.1万亿", "holdings": "—", "dividend": "季度", "issuer": "NASDAQ: MSFT"},
        "compare": [("AAPL", "$218.50", "https://x.gudaoqihuo.com/aapl/"), ("GOOGL", "$180.00", "https://x.gudaoqihuo.com/googl/")],
        "quick_compare": [("MSFT", "AAPL", "GOOGL"), ("35.0x", "28.5x", "24.0x"), ("+280%", "+320%", "+180%"), ("3.1万亿", "3.3万亿", "2.2万亿")],
        "desc": "全球市值第二，Azure云+Office 365+AI是核心增长引擎，AI时代最大受益者之一。",
    },
    "NVDA": {
        "name": "NVIDIA Corporation", "category": "stock",
        "price": "$130.00", "change": "+5.50 (+4.42%)",
        "52w_high": "$153.00", "52w_low": "$85.00",
        "pe": "65.0", "pe_avg": "45.0", "pe_trend": "up",
        "pb": "55.0", "pb_avg": "35.0", "pb_trend": "up",
        "div_yield": "0.03%", "div_avg": "0.25%", "div_trend": "down",
        "expense": "N/A", "aum": "$3.0万亿", "volume": "4200万", "beta": "1.75",
        "annual_return_1m": "+8.00%", "annual_return_3m": "+25.0%",
        "annual_return_1y": "+55.0%", "annual_return_3y": "+1500.0%", "annual_return_5y": "+1500.0%", "annual_return_10y": "+3500.0%",
        "ar_1y_ann": "+55.0%", "ar_3y_ann": "+155%", "ar_5y_ann": "+65%", "ar_10y_ann": "+43%",
        "dd_1m": "-3.0%", "dd_3m": "-6.0%", "dd_1y": "-15.0%", "dd_3y": "-35.0%", "dd_5y": "-35.0%", "dd_10y": "-35.0%",
        "sharpe_1y": "1.50", "sharpe_3y": "2.50", "sharpe_5y": "2.20", "sharpe_10y": "2.80",
        "volatility": "45.0%", "sortino": "3.00", "info_ratio": "N/A", "max_dd_5y": "-35.0%",
        "sectors": [("信息技术", "100%", "+80.0%")],
        "ai_analysis": {
            "core": "英伟达是AI算力的核心供应商，H100/H200 GPU垄断了全球AI训练市场。数据中心业务爆发式增长，CUDA生态护城河极深。",
            "pros": "①GPU市场绝对主导（市占率80%+）；②CUDA生态无可替代；③AI训练需求井喷；④数据中心业务爆发式增长。",
            "cons": "①估值极高，P/E 65；②竞争对手AMD/Google正在追赶；③中国出口限制影响收入；④股价波动极大。",
            "advice": "AI核心持仓，但波动极大。仓位不宜超过组合10%，追高风险大，建议回调时分批建仓。",
        },
        "info": {"full_name": "NVIDIA Corporation", "index": "纳斯达克100", "inception": "1999-01-22",
                  "expense": "—", "aum": "$3.0万亿", "holdings": "—", "dividend": "季度", "issuer": "NASDAQ: NVDA"},
        "compare": [("AMD", "$165.00", None), ("INTC", "$30.00", None)],
        "quick_compare": [("NVDA", "AMD", "INTC"), ("65.0x", "30.0x", "N/A"), ("+1500%", "+300%", "-20%"), ("3.0万亿", "2500亿", "1000亿")],
        "desc": "AI算力垄断者，H100/H200 GPU主导全球AI训练市场，CUDA生态护城河极深。",
    },
    "GOOGL": {
        "name": "Alphabet Inc. (Google)", "category": "stock",
        "price": "$180.00", "change": "+1.20 (+0.67%)",
        "52w_high": "$200.00", "52w_low": "$155.00",
        "pe": "24.0", "pe_avg": "25.0", "pe_trend": "down",
        "pb": "6.50", "pb_avg": "6.00", "pb_trend": "up",
        "div_yield": "0.50%", "div_avg": "—", "div_trend": "up",
        "expense": "N/A", "aum": "$2.2万亿", "volume": "2500万", "beta": "1.05",
        "annual_return_1m": "+3.50%", "annual_return_3m": "+8.00%",
        "annual_return_1y": "+15.0%", "annual_return_3y": "+60.0%", "annual_return_5y": "+180.0%", "annual_return_10y": "+300.0%",
        "ar_1y_ann": "+15.0%", "ar_3y_ann": "+17.0%", "ar_5y_ann": "+22.8%", "ar_10y_ann": "+14.8%",
        "dd_1m": "-2.0%", "dd_3m": "-4.0%", "dd_1y": "-9.0%", "dd_3y": "-25.0%", "dd_5y": "-30.0%", "dd_10y": "-30.0%",
        "sharpe_1y": "0.88", "sharpe_3y": "0.82", "sharpe_5y": "1.00", "sharpe_10y": "0.95",
        "volatility": "22.0%", "sortino": "1.10", "info_ratio": "N/A", "max_dd_5y": "-30.0%",
        "sectors": [("通信服务", "100%", "+22.0%")],
        "ai_analysis": {
            "core": "Google搜索仍是全球互联网入口，YouTube和云业务持续增长。Gemini AI正在追赶ChatGPT，AI投入巨大但商业化路径尚不清晰。",
            "pros": "①搜索市场份额80%+；②YouTube广告增长强劲；③Google Cloud高速增长；④AI投入巨大（Gemini、TPU）。",
            "cons": "①AI竞争落后于微软/OpenAI；②数字广告市场整体增速放缓；③监管风险（反垄断）；④自动驾驶商业化进度慢。",
            "advice": "核心互联网持仓，但估值修复需等待AI商业化突破。长期投资者可持有。",
        },
        "info": {"full_name": "Alphabet Inc.", "index": "纳斯达克100 / 标普500", "inception": "2004-08-19",
                  "expense": "—", "aum": "$2.2万亿", "holdings": "—", "dividend": "—", "issuer": "NASDAQ: GOOGL"},
        "compare": [("MSFT", "$420.00", "https://x.gudaoqihuo.com/msft/"), ("META", "$520.00", "https://x.gudaoqihuo.com/meta/")],
        "quick_compare": [("GOOGL", "MSFT", "META"), ("24.0x", "35.0x", "25.0x"), ("+180%", "+280%", "+350%"), ("2.2万亿", "3.1万亿", "1.3万亿")],
        "desc": "全球搜索霸主，YouTube+云业务+AI，Alphabet核心资产。",
    },
    "AMZN": {
        "name": "Amazon.com Inc.", "category": "stock",
        "price": "$195.00", "change": "+2.80 (+1.46%)",
        "52w_high": "$210.00", "52w_low": "$160.00",
        "pe": "42.0", "pe_avg": "55.0", "pe_trend": "down",
        "pb": "8.50", "pb_avg": "10.0", "pb_trend": "down",
        "div_yield": "N/A", "div_avg": "N/A", "div_trend": "neutral",
        "expense": "N/A", "aum": "$2.0万亿", "volume": "4000万", "beta": "1.18",
        "annual_return_1m": "+5.00%", "annual_return_3m": "+12.0%",
        "annual_return_1y": "+25.0%", "annual_return_3y": "+50.0%", "annual_return_5y": "+200.0%", "annual_return_10y": "+450.0%",
        "ar_1y_ann": "+25.0%", "ar_3y_ann": "+14.5%", "ar_5y_ann": "+24.5%", "ar_10y_ann": "+18.5%",
        "dd_1m": "-2.5%", "dd_3m": "-5.0%", "dd_1y": "-10.0%", "dd_3y": "-35.0%", "dd_5y": "-35.0%", "dd_10y": "-35.0%",
        "sharpe_1y": "1.20", "sharpe_3y": "0.72", "sharpe_5y": "1.05", "sharpe_10y": "1.20",
        "volatility": "28.0%", "sortino": "1.45", "info_ratio": "N/A", "max_dd_5y": "-35.0%",
        "sectors": [("可选消费", "100%", "+28.0%")],
        "ai_analysis": {
            "core": "亚马逊电商+AWS双轮驱动，AWS是全球第三大云平台且AI需求爆发。电商利润率持续改善，广告业务快速增长成为新利润引擎。",
            "pros": "①AWS受益AI算力需求爆发；②电商市场份额持续扩大；③广告业务高增长高利润率；④Prime会员粘性极强。",
            "cons": "①电商竞争激烈（Shopify、Temu）；②AWS面临Azure/GCP强力竞争；③监管风险（反垄断）；④投资周期长，盈利不稳定。",
            "advice": "AWS是AI时代核心资产，电商+云双驱动。长期看好，短期可逢低配置。",
        },
        "info": {"full_name": "Amazon.com Inc.", "index": "纳斯达克100 / 标普500", "inception": "1997-05-15",
                  "expense": "—", "aum": "$2.0万亿", "holdings": "—", "dividend": "无", "issuer": "NASDAQ: AMZN"},
        "compare": [("MSFT", "$420.00", "https://x.gudaoqihuo.com/msft/"), ("GOOGL", "$180.00", "https://x.gudaoqihuo.com/googl/")],
        "quick_compare": [("AMZN", "MSFT", "GOOGL"), ("42.0x", "35.0x", "24.0x"), ("+200%", "+280%", "+180%"), ("2.0万亿", "3.1万亿", "2.2万亿")],
        "desc": "全球电商巨头+AWS云服务，电商+云双驱动，广告业务成新利润引擎。",
    },
    "META": {
        "name": "Meta Platforms Inc.", "category": "stock",
        "price": "$520.00", "change": "+6.00 (+1.17%)",
        "52w_high": "$580.00", "52w_low": "$400.00",
        "pe": "25.0", "pe_avg": "24.0", "pe_trend": "up",
        "pb": "8.00", "pb_avg": "7.00", "pb_trend": "up",
        "div_yield": "0.35%", "div_avg": "—", "div_trend": "up",
        "expense": "N/A", "aum": "$1.3万亿", "volume": "1500万", "beta": "1.25",
        "annual_return_1m": "+6.00%", "annual_return_3m": "+15.0%",
        "annual_return_1y": "+30.0%", "annual_return_3y": "+180.0%", "annual_return_5y": "+350.0%", "annual_return_10y": "+550.0%",
        "ar_1y_ann": "+30.0%", "ar_3y_ann": "+40.5%", "ar_5y_ann": "+35.2%", "ar_10y_ann": "+20.5%",
        "dd_1m": "-2.5%", "dd_3m": "-5.0%", "dd_1y": "-12.0%", "dd_3y": "-30.0%", "dd_5y": "-30.0%", "dd_10y": "-30.0%",
        "sharpe_1y": "1.30", "sharpe_3y": "1.50", "sharpe_5y": "1.40", "sharpe_10y": "1.20",
        "volatility": "32.0%", "sortino": "1.60", "info_ratio": "N/A", "max_dd_5y": "-30.0%",
        "sectors": [("通信服务", "100%", "+35.0%")],
        "ai_analysis": {
            "core": "Meta是全球社交霸主，Facebook月活30亿，Instagram和WhatsApp持续增长。AI推荐算法和Reels短视频推动广告效率提升。",
            "pros": "①社交网络绝对主导（FB+IG+WhatsApp）；②AI提升广告精准度和变现效率；③Threads进军文字社交；④元宇宙长期布局。",
            "cons": "①监管风险（隐私政策限制）；②TikTok强力竞争；③用户增长趋于饱和；④元宇宙投入巨大且商业化不确定。",
            "advice": "高效率的广告平台，AI驱动利润率提升。长期投资者可持有，注意监管风险。",
        },
        "info": {"full_name": "Meta Platforms Inc.", "index": "纳斯达克100 / 标普500", "inception": "2012-05-18",
                  "expense": "—", "aum": "$1.3万亿", "holdings": "—", "dividend": "季度", "issuer": "NASDAQ: META"},
        "compare": [("GOOGL", "$180.00", "https://x.gudaoqihuo.com/googl/"), ("SNAP", "$12.00", None)],
        "quick_compare": [("META", "GOOGL", "SNAP"), ("25.0x", "24.0x", "N/A"), ("+350%", "+180%", "-50%"), ("1.3万亿", "2.2万亿", "200亿")],
        "desc": "全球社交网络霸主（Facebook+Instagram+WhatsApp），AI广告效率提升驱动利润高增长。",
    },
    "TSLA": {
        "name": "Tesla Inc.", "category": "stock",
        "price": "$175.00", "change": "-2.50 (-1.41%)",
        "52w_high": "$250.00", "52w_low": "$140.00",
        "pe": "55.0", "pe_avg": "60.0", "pe_trend": "down",
        "pb": "9.50", "pb_avg": "15.0", "pb_trend": "down",
        "div_yield": "N/A", "div_avg": "N/A", "div_trend": "neutral",
        "expense": "N/A", "aum": "$5600亿", "volume": "8000万", "beta": "2.30",
        "annual_return_1m": "+3.00%", "annual_return_3m": "-5.00%",
        "annual_return_1y": "-10.0%", "annual_return_3y": "+20.0%", "annual_return_5y": "+250.0%", "annual_return_10y": "+1500.0%",
        "ar_1y_ann": "-10.0%", "ar_3y_ann": "+6.3%", "ar_5y_ann": "+28.5%", "ar_10y_ann": "+32.0%",
        "dd_1m": "-5.0%", "dd_3m": "-12.0%", "dd_1y": "-35.0%", "dd_3y": "-50.0%", "dd_5y": "-50.0%", "dd_10y": "-50.0%",
        "sharpe_1y": "-0.30", "sharpe_3y": "0.25", "sharpe_5y": "1.10", "sharpe_10y": "1.80",
        "volatility": "55.0%", "sortino": "1.20", "info_ratio": "N/A", "max_dd_5y": "-50.0%",
        "sectors": [("可选消费", "100%", "-5.0%")],
        "ai_analysis": {
            "core": "特斯拉是全球电动车龙头，但当前估值更多反映了对自动驾驶（Robotaxi/FSD）和能源业务的乐观预期。销量增长放缓，竞争加剧。",
            "pros": "①全球电动车龙头，品牌号召力强；②FSD自动驾驶领先；③能源存储业务快速增长；④一体化制造优势。",
            "cons": "①估值极高，含大量梦想溢价；②全球电动车竞争激烈；③ Musk个人风险；④销量增长已放缓；⑤ Robotaxi商业化不确定。",
            "advice": "高风险高回报标的。长期逻辑存在但短期估值承压，适合能承受极大波动的投资者，仓位不超过5%。",
        },
        "info": {"full_name": "Tesla Inc.", "index": "纳斯达克100 / 标普500", "inception": "2010-06-29",
                  "expense": "—", "aum": "$5600亿", "holdings": "—", "dividend": "无", "issuer": "NASDAQ: TSLA"},
        "compare": [("RIVN", "$15.00", None), ("F", "$12.00", None)],
        "quick_compare": [("TSLA", "RIVN", "F"), ("55.0x", "N/A", "6.0x"), ("+250%", "-70%", "+20%"), ("5600亿", "150亿", "400亿")],
        "desc": "全球电动车龙头，FSD自动驾驶+能源存储，长期高增长但波动极大。",
    },
    "BRK.B": {
        "name": "Berkshire Hathaway Inc. Class B", "category": "stock",
        "price": "$385.00", "change": "+1.50 (+0.39%)",
        "52w_high": "$410.00", "52w_low": "$350.00",
        "pe": "8.5", "pe_avg": "9.0", "pe_trend": "down",
        "pb": "1.50", "pb_avg": "1.40", "pb_trend": "up",
        "div_yield": "N/A", "div_avg": "N/A", "div_trend": "neutral",
        "expense": "N/A", "aum": "$8500亿", "volume": "400万", "beta": "0.88",
        "annual_return_1m": "+1.50%", "annual_return_3m": "+4.00%",
        "annual_return_1y": "+12.0%", "annual_return_3y": "+45.0%", "annual_return_5y": "+80.0%", "annual_return_10y": "+180.0%",
        "ar_1y_ann": "+12.0%", "ar_3y_ann": "+13.2%", "ar_5y_ann": "+12.5%", "ar_10y_ann": "+10.8%",
        "dd_1m": "-1.0%", "dd_3m": "-2.5%", "dd_1y": "-5.0%", "dd_3y": "-15.0%", "dd_5y": "-20.0%", "dd_10y": "-20.0%",
        "sharpe_1y": "0.85", "sharpe_3y": "0.90", "sharpe_5y": "0.88", "sharpe_10y": "0.82",
        "volatility": "14.0%", "sortino": "1.10", "info_ratio": "N/A", "max_dd_5y": "-20.0%",
        "sectors": [("金融", "100%", "+12.0%")],
        "ai_analysis": {
            "core": "巴菲特执掌的伯克希尔，全球最成功的投资集团。持仓包括苹果、美国银行、可口可乐等优质公司。估值极低，安全边际高。",
            "pros": "①P/E仅8.5，估值极低；②巴菲特投资理念成熟稳健；③保险浮存金提供低成本资金；④多元化配置降低风险。",
            "cons": "①体量巨大难以实现高增长；②苹果持仓占比过高；③接班人风险；④巴菲特终将退休。",
            "advice": "价值投资首选，安全边际高。适合追求稳健收益的长期投资者，可作为组合压舱石。",
        },
        "info": {"full_name": "Berkshire Hathaway Inc. Class B", "index": "标普500", "inception": "1996-01-19",
                  "expense": "—", "aum": "$8500亿", "holdings": "—", "dividend": "无", "issuer": "NYSE: BRK.B"},
        "compare": [("SPY", "$592.47", "https://x.gudaoqihuo.com/spy/"), ("VTI", "$298.65", "https://x.gudaoqihuo.com/vti/")],
        "quick_compare": [("BRK.B", "SPY", "VTI"), ("8.5x", "24.6x", "26.0x"), ("+80%", "+119%", "+135%"), ("8500亿", "5.5万亿", "1.4万亿")],
        "desc": "巴菲特执掌的全球最成功投资集团，估值极低（PE 8.5），组合包含苹果、美国银行等优质资产。",
    },
    "JPM": {
        "name": "JPMorgan Chase & Co.", "category": "stock",
        "price": "$215.00", "change": "+1.80 (+0.84%)",
        "52w_high": "$240.00", "52w_low": "$185.00",
        "pe": "12.0", "pe_avg": "11.5", "pe_trend": "up",
        "pb": "1.80", "pb_avg": "1.50", "pb_trend": "up",
        "div_yield": "2.20%", "div_avg": "2.50%", "div_trend": "down",
        "expense": "N/A", "aum": "$6200亿", "volume": "1000万", "beta": "1.10",
        "annual_return_1m": "+2.50%", "annual_return_3m": "+6.00%",
        "annual_return_1y": "+18.0%", "annual_return_3y": "+50.0%", "annual_return_5y": "+110.0%", "annual_return_10y": "+200.0%",
        "ar_1y_ann": "+18.0%", "ar_3y_ann": "+14.5%", "ar_5y_ann": "+16.0%", "ar_10y_ann": "+11.6%",
        "dd_1m": "-1.0%", "dd_3m": "-2.5%", "dd_1y": "-8.0%", "dd_3y": "-20.0%", "dd_5y": "-25.0%", "dd_10y": "-25.0%",
        "sharpe_1y": "1.05", "sharpe_3y": "0.85", "sharpe_5y": "0.95", "sharpe_10y": "0.88",
        "volatility": "20.0%", "sortino": "1.20", "info_ratio": "N/A", "max_dd_5y": "-25.0%",
        "sectors": [("金融", "100%", "+15.0%")],
        "ai_analysis": {
            "core": "摩根大通是全球最大银行，Jamie Dimon执掌下风控优秀。利息收入受益高利率环境，科技创新投入领先同业。",
            "pros": "①全球系统重要性银行，品牌最强；②利息收入受益高利率；③金融科技投入大（Chase app评价最高）；④风险管理领先。",
            "cons": "①经济衰退时坏账风险上升；②监管要求日趋严格；③投行业务受市场周期影响大；④估值已反映乐观预期。",
            "advice": "美国银行股首选，稳健收益+股息。适合追求稳定现金流的投资者，组合配置5-10%。",
        },
        "info": {"full_name": "JPMorgan Chase & Co.", "index": "标普500 / 道琼斯", "inception": "1969-12-02",
                  "expense": "—", "aum": "$6200亿", "holdings": "—", "dividend": "季度", "issuer": "NYSE: JPM"},
        "compare": [("BAC", "$38.00", None), ("WFC", "$55.00", None)],
        "quick_compare": [("JPM", "BAC", "WFC"), ("12.0x", "10.0x", "10.5x"), ("+110%", "+80%", "+60%"), ("6200亿", "2800亿", "1800亿")],
        "desc": "全球最大银行，巴菲特投资标的之一，Jamie Dimon执掌，高利率环境受益者。",
    },
    "V": {
        "name": "Visa Inc.", "category": "stock",
        "price": "$275.00", "change": "+1.50 (+0.55%)",
        "52w_high": "$295.00", "52w_low": "$245.00",
        "pe": "30.0", "pe_avg": "28.0", "pe_trend": "up",
        "pb": "16.0", "pb_avg": "14.0", "pb_trend": "up",
        "div_yield": "0.75%", "div_avg": "0.70%", "div_trend": "up",
        "expense": "N/A", "aum": "$5500亿", "volume": "600万", "beta": "0.95",
        "annual_return_1m": "+2.00%", "annual_return_3m": "+5.00%",
        "annual_return_1y": "+12.0%", "annual_return_3y": "+45.0%", "annual_return_5y": "+105.0%", "annual_return_10y": "+380.0%",
        "ar_1y_ann": "+12.0%", "ar_3y_ann": "+13.2%", "ar_5y_ann": "+15.4%", "ar_10y_ann": "+17.3%",
        "dd_1m": "-1.5%", "dd_3m": "-3.0%", "dd_1y": "-7.0%", "dd_3y": "-18.0%", "dd_5y": "-20.0%", "dd_10y": "-20.0%",
        "sharpe_1y": "0.82", "sharpe_3y": "0.85", "sharpe_5y": "0.95", "sharpe_10y": "1.20",
        "volatility": "18.0%", "sortino": "1.10", "info_ratio": "N/A", "max_dd_5y": "-20.0%",
        "sectors": [("金融", "100%", "+12.0%")],
        "ai_analysis": {
            "core": "Visa是全球支付网络核心，VisaNet连接超过40亿张卡。跨境支付垄断地位极强，经济波动时依然保持韧性。",
            "pros": "①全球支付网络绝对垄断；②跨境支付手续费率高且稳定；③用户增长+消费升级双驱动；④轻资产高利润率商业模式。",
            "cons": "①估值偏高，P/E 30；② fintech竞争（Stripe、Square）；③监管机构可能限制手续费；④经济衰退时消费减少影响收入。",
            "advice": "长期优质资产，商业模式极强。适合作为组合中的消费金融配置，长期持有。",
        },
        "info": {"full_name": "Visa Inc.", "index": "标普500 / 道琼斯", "inception": "2008-03-19",
                  "expense": "—", "aum": "$5500亿", "holdings": "—", "dividend": "季度", "issuer": "NYSE: V"},
        "compare": [("MA", "$480.00", None), ("PYPL", "$65.00", None)],
        "quick_compare": [("V", "MA", "PYPL"), ("30.0x", "35.0x", "15.0x"), ("+105%", "+95%", "-30%"), ("5500亿", "4200亿", "700亿")],
        "desc": "全球支付网络核心，覆盖40亿+卡，跨境支付垄断，利润率高且稳定。",
    },
}


def build_page(ticker: str, meta: dict) -> str:
    """构建完整的详情页HTML"""
    # ── 从数据库获取K线数据 ───────────────────────────
    chart_data = []
    try:
        if DB_PATH.exists():
            conn = sqlite3.connect(str(DB_PATH))
            rows = conn.execute(
                "SELECT date, open, high, low, close, volume FROM market_data WHERE ticker=? ORDER BY date ASC LIMIT 500",
                (ticker,)
            ).fetchall()
            conn.close()
            if rows:
                chart_data = [{"date": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4], "v": r[5]} for r in rows]
    except Exception:
        pass

    # 如果DB没有，尝试读旧JSON
    if not chart_data:
        json_file = OUTPUT / f"{ticker}.json"
        if json_file.exists():
            try:
                raw = json.loads(json_file.read_text(encoding="utf-8"))
                if "data" in raw:
                    chart_data = raw["data"]
                elif isinstance(raw, list):
                    chart_data = raw
            except Exception:
                pass

    # ── 计算MA ──────────────────────────────────────────
    closes = [d["c"] if "c" in d else d.get("close", d.get("price", 0)) for d in chart_data]
    if not closes:
        closes = [0]

    def calc_ma(data_list, period):
        r = []
        for i in range(len(data_list)):
            if i < period - 1:
                r.append(None)
            else:
                r.append(round(sum(data_list[i-period+1:i+1]) / period, 2))
        return r

    ma20 = calc_ma(closes, 20)
    ma50 = calc_ma(closes, 50)
    latest = closes[-1] if closes else 0
    prev = closes[-2] if len(closes) > 1 else latest

    # ── 生成chart_data JSON ─────────────────────────────
    chart_json = json.dumps(chart_data, ensure_ascii=False)
    ma20_json = json.dumps(ma20, ensure_ascii=False)
    ma50_json = json.dumps(ma50, ensure_ascii=False)

    # ── sectors / holdings ──────────────────────────────
    sectors_html = ""
    if "sectors" in meta:
        sector_colors = ["#4fc3f7","#66bb6a","#ffa726","#ab47bc","#ef5350","#26a69a","#78909c","#8d6e63","#5c6bc0","#7e57c2"]
        bar_items = ""
        for i, (name, pct, _) in enumerate(meta["sectors"][:8]):
            color = sector_colors[i % len(sector_colors)]
            bar_items += f'<div class="sector-bar-item" style="flex:{pct[:-1]};background:{color}"><span>{name} {pct}</span></div>'
        table_rows = ""
        for name, pct, chg in meta["sectors"]:
            updown = "trend-up" if chg.startswith("+") else "trend-down"
            table_rows += f'<tr><td>{"🏭" if "信息" in name or "科技" in name else "🏦" if "金融" in name else "📡"} {name}</td><td class="num">{pct}</td><td class="num {updown}">{chg}</td></tr>'
        sectors_html = f'''
            <div class="section-card">
                <div class="section-header">🏭 行业分布</div>
                <div class="sector-bar" style="margin:14px 20px 0">{bar_items}</div>
                <table class="data-table" style="margin-top:12px">
                    <thead><tr><th>行业</th><th>权重</th><th>近1年涨跌</th></tr></thead>
                    <tbody>{table_rows}</tbody>
                </table>
            </div>'''
    elif "holdings" in meta:
        bar_items = ""
        for name, pct, _ in meta["holdings"]:
            bar_items += f'<div class="sector-bar-item" style="flex:{pct[:-1]};background:#4fc3f7"><span>{name} {pct}</span></div>'
        table_rows = ""
        for name, pct, chg in meta["holdings"]:
            table_rows += f'<tr><td>{name}</td><td class="num">{pct}</td><td class="num">{chg}</td></tr>'
        sectors_html = f'''
            <div class="section-card">
                <div class="section-header">🏦 持仓分布</div>
                <div class="sector-bar" style="margin:14px 20px 0">{bar_items}</div>
                <table class="data-table" style="margin-top:12px">
                    <thead><tr><th>持仓类型</th><th>权重</th><th>备注</th></tr></thead>
                    <tbody>{table_rows}</tbody>
                </table>
            </div>'''

    # ── AI analysis ──────────────────────────────────────
    ai = meta.get("ai_analysis", {})
    ai_html = ""
    if ai:
        ai_html = f'''
            <div class="section-card">
                <div class="section-header">🤖 AI 智能分析 — Qwen2 本地推理</div>
                <div class="ai-insight-body">
                    <strong>核心观点</strong>：{ai.get("core","")}<br><br>
                    <strong>优势</strong>：{ai.get("pros","")}<br><br>
                    <strong>风险</strong>：{ai.get("cons","")}<br><br>
                    <strong>建议</strong>：{ai.get("advice","")}
                </div>
            </div>'''

    # ── financial metrics table ───────────────────────────
    fin_rows = ""
    metrics = [
        ("市盈率 (P/E)", meta.get("pe","N/A"), meta.get("pe_avg","—"), meta.get("pe_trend","")),
        ("市净率 (P/B)", meta.get("pb","N/A"), meta.get("pb_avg","—"), meta.get("pb_trend","")),
        ("股息率", meta.get("div_yield","—"), meta.get("div_avg","—"), meta.get("div_trend","")),
        ("费率 (Expense Ratio)", meta.get("expense","—"), "—", "neutral"),
        ("净资产规模", meta.get("aum","—"), "—", ""),
        ("日均成交量", meta.get("volume","—"), "—", ""),
        ("Beta", meta.get("beta","—"), "—", ""),
    ]
    for name, cur, avg, trend in metrics:
        if trend == "up":
            trend_html = '<span class="trend-up">↑</span>'
        elif trend == "down":
            trend_html = '<span class="trend-down">↓</span>'
        else:
            trend_html = '<span>—</span>'
        fin_rows += f'<tr><td>{name}</td><td class="num">{cur}</td><td class="num">{avg}</td><td class="num">{trend_html}</td></tr>'

    financial_html = f'''
            <div class="section-card">
                <div class="section-header">📊 关键财务指标</div>
                <table class="data-table">
                    <thead><tr><th>指标</th><th class="num">当前值</th><th class="num">5年均值</th><th class="num">趋势</th></tr></thead>
                    <tbody>{fin_rows}</tbody>
                </table>
            </div>'''

    # ── historical returns ────────────────────────────────
    periods = [
        ("近1月", meta.get("annual_return_1m","—"), "—", meta.get("dd_1m","—"), "—"),
        ("近3月", meta.get("annual_return_3m","—"), "—", meta.get("dd_3m","—"), "—"),
        ("近1年", meta.get("annual_return_1y","—"), meta.get("ar_1y_ann","—"), meta.get("dd_1y","—"), meta.get("sharpe_1y","—")),
        ("近3年", meta.get("annual_return_3y","—"), meta.get("ar_3y_ann","—"), meta.get("dd_3y","—"), meta.get("sharpe_3y","—")),
        ("近5年", meta.get("annual_return_5y","—"), meta.get("ar_5y_ann","—"), meta.get("dd_5y","—"), meta.get("sharpe_5y","—")),
        ("近10年", meta.get("annual_return_10y","—"), meta.get("ar_10y_ann","—"), meta.get("dd_10y","—"), meta.get("sharpe_10y","—")),
    ]
    perf_rows = ""
    for period, ret, ann, dd, sharpe in periods:
        ret_class = "trend-up" if ret.startswith("+") else ("trend-down" if ret.startswith("-") else "")
        dd_class = "trend-down" if dd.startswith("-") else ""
        perf_rows += f'<tr><td>{period}</td><td class="num {ret_class}">{ret}</td><td class="num {ret_class}">{ann}</td><td class="num {dd_class}">{dd}</td><td class="num">{sharpe}</td></tr>'

    perf_html = f'''
            <div class="section-card">
                <div class="section-header">📈 历史收益表现</div>
                <table class="data-table">
                    <thead><tr><th>周期</th><th class="num">收益率</th><th class="num">年化</th><th class="num">最大回撤</th><th class="num">夏普比率</th></tr></thead>
                    <tbody>{perf_rows}</tbody>
                </table>
            </div>'''

    # ── sidebar ──────────────────────────────────────────
    info = meta.get("info", {})
    info_rows = ""
    for k, v in info.items():
        label_map = {"full_name":"全称","index":"跟踪指数","inception":"成立日期","expense":"费率","aum":"资产规模","holdings":"成分股","dividend":"派息频率","issuer":"发行商"}
        label = label_map.get(k, k)
        info_rows += f'<div class="indicator-row"><span class="indicator-name">{label}</span><span class="indicator-value">{v}</span></div>'

    risk_rows = ""
    risk_items = [
        ("年化波动率", meta.get("volatility","—"), ""),
        ("Beta", meta.get("beta","—"), ""),
        ("夏普比率", meta.get("sharpe_5y","—"), "up"),
        ("最大回撤", meta.get("max_dd_5y","—"), "down"),
        ("索提诺比率", meta.get("sortino","—"), "up"),
        ("信息比率", meta.get("info_ratio","—"), ""),
    ]
    for name, val, cls in risk_items:
        val_cls = f"class='indicator-value {cls}'" if cls else "class='indicator-value'"
        risk_rows += f'<div class="indicator-row"><span class="indicator-name">{name}</span><span {val_cls}>{val}</span></div>'

    compare_rows = ""
    for name, price, href in meta.get("compare", []):
        if href:
            compare_rows += f'<div class="indicator-row"><span class="indicator-name"><a href="{href}">{name}</a></span><span class="indicator-value">{price}</span></div>'
        else:
            compare_rows += f'<div class="indicator-row"><span class="indicator-name">{name}</span><span class="indicator-value">{price}</span></div>'

    # quick compare
    qc = meta.get("quick_compare", [])
    qc_tickers = qc[0] if qc else []
    qc_labels = ["", "费率", "近5年收益", "流动性", "夏普比率"]
    qc_fixed = ""
    for i, row in enumerate(qc[1:]):
        cells = ""
        # parse numeric for comparison
        def parse_num(v):
            try:
                return float(v.replace("%","").replace("M","").replace("k","").replace("x","").replace("+","").replace("-","-"))
            except:
                return 0.0
        num_vals = [parse_num(x) for x in row]
        max_val = max(num_vals) if num_vals else 0
        for j, val in enumerate(row):
            cls = ""
            if j > 0 and num_vals[j] == max_val and max_val != 0:
                cls = "compare-best"
            cells += f'<td class="{cls}">{val}</td>'
        label = qc_labels[i+1] if i+1 < len(qc_labels) else ""
        qc_fixed += f'<tr><td>{label}</td>{cells}</tr>'
    # old qc_rows loop (kept for compatibility)
    qc_rows = ""

    cat_class = meta.get("category", "etf")
    cat_label = "ETF" if cat_class in ("etf","") else ("债券" if cat_class == "bond" else "商品" if cat_class == "commodity" else "股票")

    # day change color
    day_chg = meta.get("change", "")
    chg_class = "up" if day_chg.startswith("+") else "down"

    # 52w range
    w52h = meta.get("52w_high", "—")
    w52l = meta.get("52w_low", "—")

    # volatility
    vol_val = meta.get("volatility", "—")

    # annual return (from 5y)
    ar_5y = meta.get("annual_return_5y", "—")
    ar_5y_val = ar_5y
    ar_5y_cls = "trend-up" if ar_5y.startswith("+") else ("trend-down" if ar_5y.startswith("-") else "")

    # price change in %
    chg_val = meta.get("change", "+0.00%")

    sidebar_html = f'''
        <div class="sidebar">
            <!-- Basic Info -->
            <div class="side-card">
                <div class="side-title">📋 基本信息</div>
                {info_rows}
            </div>

            <!-- Risk Metrics -->
            <div class="side-card">
                <div class="side-title">⚠️ 风险指标</div>
                {risk_rows}
            </div>

            <!-- Similar ETFs -->
            <div class="side-card">
                <div class="side-title">🔀 同类标的</div>
                {compare_rows}
            </div>

            <!-- Quick Compare -->
            <div class="side-card">
                <div class="side-title">⚔️ 快速对比</div>
                <table class="compare-table">
                    <thead><tr><th></th><th>{qc_tickers[0] if qc_tickers else ""}</th><th>{qc_tickers[1] if len(qc_tickers)>1 else ""}</th><th>{qc_tickers[2] if len(qc_tickers)>2 else ""}</th></tr></thead>
                    <tbody>{qc_fixed}</tbody>
                </table>
            </div>
        </div>'''

    # ── assemble full page ──────────────────────────────────
    cat_badge_class = {"etf":"etf","bond":"bond","commodity":"commodity","stock":"stock"}.get(cat_class,"etf")
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker} - {meta.get("name","")} | 股道奇货</title>
    <meta name="description" content="{meta.get('name','')}（{ticker}）历史价格、K线图、财务指标、AI分析 - 股道奇货">
    <meta name="keywords" content="{ticker}, {meta.get('name','')}, ETF, 股票, 历史数据, K线图">
    <link rel="canonical" href="https://x.gudaoqihuo.com/{ticker.lower()}/">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📈</text></svg>">
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
            --bg-primary: #0d1117; --bg-secondary: #161b22; --bg-card: #1c2128;
            --border: #30363d; --text-primary: #e6edf3; --text-secondary: #8b949e;
            --accent: #58a6ff; --green: #3fb950; --red: #f85149; --gold: #d4a843;
            --border-radius: 12px;
        }}
        body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg-primary); color: var(--text-primary); line-height: 1.6; }}
        a {{ color: var(--accent); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .up {{ color: var(--green) !important; }}
        .down {{ color: var(--red) !important; }}
        .trend-up {{ color: var(--green); font-weight: 700; }}
        .trend-down {{ color: var(--red); font-weight: 700; }}
        .label-positive {{ color: var(--green); }}
        .label-negative {{ color: var(--red); }}

        header {{ background: var(--bg-secondary); border-bottom: 1px solid var(--border); padding: 0 24px; position: sticky; top: 0; z-index: 100; }}
        .header-inner {{ max-width: 1400px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; height: 56px; }}
        .logo {{ font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 8px; }}
        .logo span {{ color: var(--gold); }}
        nav {{ display: flex; gap: 24px; }}
        nav a {{ color: var(--text-secondary); font-size: 14px; font-weight: 500; }}
        nav a:hover {{ color: var(--text-primary); text-decoration: none; }}

        .breadcrumb {{ max-width: 1400px; margin: 0 auto; padding: 16px 24px; font-size: 13px; color: var(--text-secondary); }}
        .breadcrumb a {{ color: var(--text-secondary); }}

        .hero {{ max-width: 1400px; margin: 0 auto; padding: 8px 24px 24px; }}
        .stock-header {{ display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 16px; }}
        .stock-left {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
        .ticker-badge {{ font-size: 32px; font-weight: 700; color: var(--gold); letter-spacing: 2px; }}
        .stock-name {{ font-size: 20px; font-weight: 600; }}
        .stock-category {{ display: inline-block; font-size: 11px; padding: 3px 10px; border-radius: 10px; }}
        .stock-category.etf {{ background: rgba(88,166,255,0.1); color: var(--accent); border: 1px solid rgba(88,166,255,0.3); }}
        .stock-category.bond {{ background: rgba(63,185,80,0.1); color: var(--green); border: 1px solid rgba(63,185,80,0.3); }}
        .stock-category.commodity {{ background: rgba(212,168,67,0.1); color: var(--gold); border: 1px solid rgba(212,168,67,0.3); }}
        .stock-category.stock {{ background: rgba(212,168,67,0.1); color: var(--gold); border: 1px solid rgba(212,168,67,0.3); }}
        .stock-right {{ text-align: right; }}
        .current-price {{ font-size: 36px; font-weight: 700; }}
        .price-change {{ font-size: 15px; margin-top: 4px; }}
        .stock-desc {{ font-size: 14px; color: var(--text-secondary); line-height: 1.7; margin-top: 10px; max-width: 700px; }}

        .stats-row {{ display: flex; gap: 12px; margin-top: 20px; flex-wrap: wrap; }}
        .stat-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 14px 18px; flex: 1; min-width: 130px; }}
        .stat-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary); margin-bottom: 4px; }}
        .stat-value {{ font-size: 17px; font-weight: 600; }}

        .content-wrap {{ max-width: 1400px; margin: 0 auto; padding: 0 24px 48px; display: grid; grid-template-columns: 1fr 340px; gap: 20px; align-items: start; }}
        @media (max-width: 900px) {{ .content-wrap {{ grid-template-columns: 1fr; }} }}

        .main-area {{ min-width: 0; }}

        .chart-section {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--border-radius); overflow: hidden; margin-bottom: 20px; }}
        .chart-header {{ display: flex; align-items: center; justify-content: space-between; padding: 14px 20px; border-bottom: 1px solid var(--border); }}
        .chart-title {{ font-size: 14px; font-weight: 600; }}
        .period-btn {{ background: transparent; border: 1px solid var(--border); color: var(--text-secondary); padding: 4px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; transition: all 0.2s; margin-left: 6px; }}
        .period-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
        .period-btn.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
        #main-chart {{ width: 100%; height: 380px; }}

        .section-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--border-radius); margin-bottom: 20px; overflow: hidden; }}
        .section-header {{ display: flex; align-items: center; gap: 8px; padding: 14px 20px; border-bottom: 1px solid var(--border); font-size: 14px; font-weight: 600; }}

        .data-table {{ width: 100%; border-collapse: collapse; }}
        .data-table th {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary); text-align: right; padding: 10px 16px; border-bottom: 1px solid var(--border); background: var(--bg-card); }}
        .data-table th:first-child {{ text-align: left; }}
        .data-table td {{ font-size: 13px; padding: 10px 16px; text-align: right; border-bottom: 1px solid rgba(48,54,61,0.5); }}
        .data-table td:first-child {{ text-align: left; color: var(--text-secondary); font-size: 13px; }}
        .data-table tr:last-child td {{ border-bottom: none; }}
        .data-table tr:hover td {{ background: rgba(255,255,255,0.02); }}

        .sector-bar {{ display: flex; height: 28px; border-radius: 6px; overflow: hidden; margin: 14px 20px 0; gap: 2px; }}
        .sector-bar-item {{ display: flex; align-items: center; justify-content: center; font-size: 11px; color: #fff; font-weight: 500; overflow: hidden; white-space: nowrap; min-width: 0; }}
        .sector-bar-item span {{ overflow: hidden; text-overflow: ellipsis; padding: 0 4px; }}

        .ai-insight-body {{ padding: 16px 20px; font-size: 14px; line-height: 1.8; color: var(--text-primary); }}
        .ai-insight-body strong {{ color: var(--gold); }}

        .sidebar {{ display: flex; flex-direction: column; gap: 16px; }}
        .side-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--border-radius); padding: 18px; }}
        .side-title {{ font-size: 13px; font-weight: 600; margin-bottom: 12px; color: var(--text-primary); }}
        .indicator-row {{ display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px solid rgba(48,54,61,0.5); font-size: 13px; }}
        .indicator-row:last-child {{ border-bottom: none; }}
        .indicator-name {{ color: var(--text-secondary); }}
        .indicator-value {{ font-weight: 600; }}
        .indicator-value.up {{ color: var(--green); }}
        .indicator-value.down {{ color: var(--red); }}

        .compare-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
        .compare-table th {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary); text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--border); }}
        .compare-table th:first-child {{ text-align: left; }}
        .compare-table td {{ font-size: 12px; padding: 6px 8px; text-align: right; }}
        .compare-table td:first-child {{ text-align: left; font-weight: 500; color: var(--text-secondary); }}
        .compare-table td.compare-best {{ color: var(--green); font-weight: 700; }}
        .compare-table tr:hover td {{ background: rgba(255,255,255,0.03); }}

        footer {{ background: var(--bg-secondary); border-top: 1px solid var(--border); padding: 24px; text-align: center; font-size: 13px; color: var(--text-secondary); }}
        footer a {{ color: var(--text-secondary); }}
    </style>
</head>
<body>
    <header>
        <div class="header-inner">
            <div class="logo">📈 <span>股道奇货</span></div>
            <nav>
                <a href="/">首页</a>
                <a href="/screener.html">全部列表</a>
                <a href="/privacy-policy.html">隐私政策</a>
                <a href="/disclaimer.html">免责声明</a>
            </nav>
        </div>
    </header>

    <div class="breadcrumb"><a href="/">首页</a> › {meta.get("name","")}（{ticker}）</div>

    <div class="hero">
        <div class="stock-header">
            <div class="stock-left">
                <span class="ticker-badge">{ticker}</span>
                <div>
                    <div class="stock-name">{meta.get("name","")}</div>
                    <span class="stock-category {cat_badge_class}">{cat_label}</span>
                </div>
            </div>
            <div class="stock-right">
                <div class="current-price">{meta.get("price","—")}</div>
                <div class="price-change {'up' if chg_class=='up' else 'down'}">{meta.get("change","")}</div>
            </div>
        </div>
        {"<div class='stock-desc'>" + meta.get("desc","") + "</div>" if meta.get("desc") else ""}
        <div class="stats-row">
            <div class="stat-card"><div class="stat-label">52周最高</div><div class="stat-value">{w52h}</div></div>
            <div class="stat-card"><div class="stat-label">52周最低</div><div class="stat-value">{w52l}</div></div>
            <div class="stat-card"><div class="stat-label">年化收益(5Y)</div><div class="stat-value {ar_5y_cls}">{ar_5y_val}</div></div>
            <div class="stat-card"><div class="stat-label">波动率</div><div class="stat-value">{vol_val}</div></div>
        </div>
    </div>

    <div class="content-wrap">
        <div class="main-area">
            <div class="chart-section">
                <div class="chart-header">
                    <div class="chart-title">📊 价格走势（K线 + 均线）</div>
                    <div>
                        <button class="period-btn" data-period="1y">1年</button>
                        <button class="period-btn active" data-period="5y">5年</button>
                        <button class="period-btn" data-period="all">全部</button>
                    </div>
                </div>
                <div id="main-chart"></div>
            </div>

            {financial_html}
            {perf_html}
            {sectors_html}
            {ai_html}
        </div>

        {sidebar_html}
    </div>

    <footer>
        <p>数据来源：Yahoo Finance · 仅供参考，不构成投资建议</p>
        <p style="margin-top: 8px;">
            <a href="/privacy-policy.html">隐私政策</a> ·
            <a href="/terms-of-service.html">服务条款</a> ·
            <a href="/disclaimer.html">免责声明</a>
        </p>
        <p style="margin-top: 8px;">© 2026 <strong>股道奇货</strong> · x.gudaoqihuo.com</p>
    </footer>

    <script>
    const CHART_DATA = {chart_json};
    const MA20_DATA = {ma20_json};
    const MA50_DATA = {ma50_json};
    const LATEST_PRICE = {latest};
    let currentPeriod = '5y';

    function calcMA(data, period) {{
        const r = [];
        for (let i = 0; i < data.length; i++) {{
            if (i < period - 1) {{ r.push(null); continue; }}
            let s = 0;
            for (let j = 0; j < period; j++) s += data[i - j];
            r.push(Math.round(s / period * 100) / 100);
        }}
        return r;
    }}

    function filterByPeriod(data, period) {{
        if (period === 'all') return data;
        const now = new Date(data[data.length - 1].date);
        const cutoff = new Date(now);
        if (period === '1y') cutoff.setFullYear(now.getFullYear() - 1);
        return data.filter(d => new Date(d.date) >= cutoff);
    }}

    let chart;
    function initChart() {{
        chart = echarts.init(document.getElementById('main-chart'));
        drawChart();
        window.addEventListener('resize', () => chart.resize());
    }}

    function drawChart() {{
        const data = filterByPeriod(CHART_DATA, currentPeriod);
        const closes = data.map(d => d.c || d.close);
        const ma20 = calcMA(closes, 20);
        const ma50 = calcMA(closes, 50);
        const dates = data.map(d => d.date);

        chart.setOption({{
            backgroundColor: 'transparent',
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'cross' }} }},
            legend: {{ top: 8, textStyle: {{ color: '#8b949e', fontSize: 12 }} }},
            grid: {{ left: '1%', right: '1%', top: '15%', bottom: '15%', containLabel: true }},
            xAxis: {{ type: 'category', data: dates, axisLine: {{ lineStyle: {{ color: '#30363d' }} }}, axisLabel: {{ color: '#8b949e', fontSize: 11, formatter: '月标签' }}, splitLine: {{ show: false }} }},
            yAxis: {{ type: 'value', scale: true, position: 'right', splitLine: {{ lineStyle: {{ color: '#21262d' }} }}, axisLabel: {{ color: '#8b949e', fontSize: 11, formatter: v => '$' + v.toFixed(0) }} }},
            dataZoom: [
                {{ type: 'inside', xAxisIndex: [0], start: 0, end: 100 }},
                {{ type: 'slider', xAxisIndex: [0], start: 0, end: 100, height: 20, bottom: 10, borderColor: '#30363d', backgroundColor: '#161b22', fillerColor: 'rgba(88,166,255,0.2)', handleStyle: {{ color: '#58a6ff' }}, textStyle: {{ color: '#8b949e' }} }}
            ],
            series: [
                {{ name: '收盘价', type: 'line', data: closes, smooth: false, symbol: 'none', lineStyle: {{ width: 1.5, color: '#58a6ff' }}, areaStyle: {{ color: {{ type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{{ offset: 0, color: 'rgba(88,166,255,0.2)' }}, {{ offset: 1, color: 'rgba(88,166,255,0)' }}] }} }} }},
                {{ name: 'MA20', type: 'line', data: ma20, smooth: true, symbol: 'none', lineStyle: {{ width: 1, color: '#f0883e', type: 'dashed' }}, connectNulls: true }},
                {{ name: 'MA50', type: 'line', data: ma50, smooth: true, symbol: 'none', lineStyle: {{ width: 1, color: '#a371f7', type: 'dashed' }}, connectNulls: true }}
            ]
        }}, true);
    }}

    document.querySelectorAll('.period-btn').forEach(btn => {{
        btn.addEventListener('click', () => {{
            document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentPeriod = btn.dataset.period;
            drawChart();
        }});
    }});

    initChart();
    </script>
</body>
</html>'''
    return html


def main():
    print("=" * 50)
    print("  股道奇货 · 生成详情页")
    print("=" * 50)

    for ticker, meta in TICKER_METADATA.items():
        print(f"  生成 {ticker} ...", end=" ", flush=True)
        out_dir = OUTPUT / ticker.lower()
        out_dir.mkdir(exist_ok=True)
        html = build_page(ticker, meta)
        out_file = out_dir / "index.html"
        out_file.write_text(html, encoding="utf-8")
        size_kb = len(html) // 1024
        print(f"✓ ({size_kb}KB)")

    print(f"\n✅ 完成！共 {len(TICKER_METADATA)} 个详情页")
    print(f"   输出目录: {OUTPUT}")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    main()
