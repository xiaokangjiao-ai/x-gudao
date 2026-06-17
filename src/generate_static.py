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

# ── 研报内容（股道奇货 · 每季度~半年更新一次） ──
RESEARCH = {
    "SPY":  {"thesis": "SPY是全球资管规模最大的ETF，追踪标普500指数，覆盖美国经济中约80%的市值。作为美国大盘股的核心配置工具，其流动性极强（单日成交额常超300亿美元），费率仅0.09%。", "highlights": ["全球最大ETF，资管规模超5000亿美元", "追踪标普500，美国经济晴雨表", "费率0.09%，适合长期持有", "股息率约1.3%，兼具成长与收益"], "outlook": "在美国经济软着陆预期下，SPY作为大盘股代表，中期仍有配置价值。注意美联储利率路径的不确定性对估值端的压制。"},
    "QQQ":  {"thesis": "纳指100ETF（QQQ）追踪美国科技股含量最高的100只股票，权重包括苹果、微软、英伟达、谷歌等全球顶级科技企业。科技股的高增长特性使其长期大幅跑赢标普500，但波动性也显著更高。", "highlights": ["科技股权重超55%，AI赛道集中", "前10大成份股权重约60%，集中度高", "过去20年年化收益约18%，显著跑赢大盘", "费率0.20%，性价比突出"], "outlook": "AI浪潮持续，NVDA等头部科技股盈利超预期，短期继续看好。但高估值（PE约35倍）意味着一旦利率预期反转，波动将放大。"},
    "VOO":  {"thesis": "Vanguard标普500ETF以0.03%的超低管理费闻名，是长期投资者的首选工具。追踪误差极小，费率优势在20年+的时间维度上可节省数万美元费用复利，是'只买不卖'策略的完美载体。", "highlights": ["费率仅0.03%，行业最低梯队", "追踪误差极低，被动复制指数", "Vanguard自有指数团队管理，实力雄厚", "长期持有收益率与标普500指数几乎一致"], "outlook": "标普500企业盈利仍稳健，分析师普遍预期2025年EPS增长约10%。低费率+分散风险，VOO适合任何时点一次性买入。"},
    "VTI":  {"thesis": "VTI覆盖美国全市场股票（大型+中型+小型股），不只是大盘股。相比SPY/VOO多了约20%的中小盘敞口，在美国经济扩张期往往能获得超额收益。是最能完整代表'美国股市'的指数基金。", "highlights": ["覆盖美股全市场4000+只股票", "包含SPY/VOO所有标的 + 中小盘", "中小盘占比约20%，进攻性更强", "费率0.03%，比SPY更低"], "outlook": "美国经济若成功软着陆，小盘股（VTI中约20%）有望补涨。VTI是拥抱美国整体经济成长的最简单工具。"},
    "IWM":  {"thesis": "罗素2000小盘股ETF(IWM)追踪美国2000家小型上市公司，与大盘股（SPY/QQQ）相关性较低，是美股组合中重要的'卫星配置'。历史上小盘股在经济复苏初期往往大幅跑赢大盘。", "highlights": ["专注美国小盘股，差异化配置", "与标普500相关性约0.85，降低组合波动", "经济复苏期弹性极大", "费率0.19%，小盘ETF中较低"], "outlook": "美联储若进入降息周期，实际利率下行对小盘股最为受益。当前高利率环境令小盘股承压，但降息预期升温是关键转折点。"},
    "GLD":  {"thesis": "SPDR黄金ETF持有实物黄金，是对抗通胀和避险情绪的核心工具。金价与股市相关性低（通常为负），在美元走弱、央行购金、地缘风险升温时表现突出，是投资组合的'保险'资产。", "highlights": ["持有实物黄金，零信用风险", "与股市相关性低，降低组合风险", "金价受益于去美元化、央行购金", "股息率约1.5%，金价波动约15%/年"], "outlook": "全球央行持续增持黄金、美国财政赤字扩大、地缘风险频发，三重因素支撑金价。中期目标2500美元/盎司以上。"},
    "BND":  {"thesis": "Vanguard全美债券市场ETF追踪美国整体债券市场，是稳健型投资者的核心配置。相比股票波动小（年化波动约5%），在股票熊市中往往逆势正收益，提供组合的'压舱石'作用。", "highlights": ["美国债券市场全覆盖（国债+企业债+MBS）", "年化波动约5%，远低于股票", "与股票相关性低，组合平滑器", "当前收益率约4.5%，吸引力提升"], "outlook": "美联储降息预期下，债券价格有望上涨。BND当前处于历史较好配置区间，适合风险偏好较低的投资者。"},
    "TLT":  {"thesis": "iShares 20年期以上美国国债ETF专注长期国债，追踪20年+期限的美国政府债券。长久期特性使其对利率极为敏感：降息周期中涨幅最大，升值潜力突出；但加息周期中跌幅也最深。", "highlights": ["长久期，利率敏感度最高", "降息周期潜在涨幅领先所有债券ETF", "零信用风险，美国政府担保", "费率仅0.15%，纯利率工具"], "outlook": "美联储降息路径一旦确认，TLT将迎来显著上涨。当前债券市场已price in约2次降息，建议分批建仓以控制久期风险。"},
    "AAPL": {"thesis": "苹果是全球市值最高的消费电子公司，iPhone生态系统构成强大的用户粘性和定价权。服务业务（App Store、Apple TV+、iCloud）毛利率超70%，已超越iPhone成为利润增长的核心驱动力。", "highlights": ["市值约3万亿美元，全球第一", "服务业务毛利率70%+，护城河深厚", "iPhone全球活跃设备超20亿台", "强劲现金流，每年回购股票约800亿美元"], "outlook": "AI功能（Apple Intelligence）驱动换机周期，服务业务持续高增长。估值（PE约28倍）合理，中长期仍看好。"},
    "MSFT": {"thesis": "微软是全球企业级软件和云计算的绝对霸主。Azure云业务规模仅次于AWS，年增长率仍保持20%+。Copilot AI助手全面整合Office 365、Windows和Azure，推动ARR（年度经常性收入）持续创新高。", "highlights": ["Azure云全球第二，规模仅次于AWS", "Copilot AI全面集成到核心产品", "Office 365企业用户超4000万", "股息率约0.7%，持续回购增厚股东权益"], "outlook": "AI商业化元年，微软凭借企业级AI（Copilot）占据先机。Azure增长韧性强，股价中短期仍有望创新高。"},
    "GOOGL": {"thesis": "Alphabet是全球最大的搜索引擎和数字广告平台，同时布局云计算（Google Cloud全球第三）、AI（Gemini大模型）和自动驾驶（Waymo）。搜索引擎市场份额超90%，广告业务稳健，AI能力被低估。", "highlights": ["搜索市场份额超90%，护城河无可撼动", "Google Cloud增长超30%，亏损收窄", "Gemini大模型开源战略反击OpenAI", "PE约22倍，FAANG中估值最低"], "outlook": "AI搜索整合将提升货币化效率，Google Cloud扭亏为盈带来估值重估机会。当前价位具有中长期配置价值。"},
    "AMZN": {"thesis": "亚马逊是全球最大电商+云计算巨头。AWS是全球最大的云基础设施服务商（利润核心），电商业务通过Prime会员和高效率物流建立壁垒，同时积极布局AI（Bedrock）和自动驾驶（Zoox）。", "highlights": ["AWS全球最大云服务商，利润率超30%", "电商业务北美市场遥遥领先", "广告业务高速增长，被低估", "股息率约0%，但回购积极"], "outlook": "AWS需求复苏+广告业务爆发+电商利润率提升，三重催化剂共振。PE约35倍偏高，但成长性可消化。"},
    "NVDA": {"thesis": "英伟达是全球AI算力的核心供应商，数据中心GPU市场份额超80%。H100/H200供不应求，黄仁勋的定价权极强。CUDA生态是Nvidia最深的护城河，AMD和英特尔短期无法复制。", "highlights": ["AI GPU市场份额超80%，绝对垄断", "H100/H200芯片需求远超供给", "CUDA生态绑定200万开发者", "2025财年数据中心收入同比增长超400%"], "outlook": "AI算力需求井喷式增长，Blackwell架构进一步巩固优势。短期股价波动大，但长期赛道最清晰。"},
    "META": {"thesis": "Meta是全球最大社交网络公司（Facebook月活30亿+），旗下Instagram/Reels和WhatsApp构成强大社交矩阵。AI推荐引擎显著提升广告变现效率，Reels短视频已实现商业化，Threads挑战X平台初见成效。", "highlights": ["Facebook月活30.3亿，全球第一", "AI广告引擎提升变现效率约20%", "Reels短视频商业化加速", "回购+股息，股东回报大幅提升"], "outlook": "AI驱动广告收入超预期，Reels货币化空间大。估值（PE约22倍）合理偏低，分析师目标价普遍在550美元以上。"},
    "TSLA": {"thesis": "特斯拉是全球电动车绝对领导者，同时布局储能（Megapack）和自动驾驶（Full Self-Driving）。2025年Robotaxi商业化是最大看点，若成功将重构估值逻辑。中国市场竞争加剧是主要风险。", "highlights": ["全球电动车销量第一品牌", "Robotaxi FSD自动驾驶2025年商业化", "Megapack储能订单暴增，增速超汽车", "估值逻辑从汽车公司→AI/能源公司"], "outlook": "短期竞争压力令利润率承压，但Robotaxi和储能是长期催化剂。高风险高回报，适合有风险承受能力的投资者。"},
    "BRK.B": {"thesis": "伯克希尔·哈撒韦是巴菲特执掌的全球最大保险+投资集团。保险业务（GEICO等）提供浮存金用于投资，股票投资组合持有多只优质股票（苹果、美国银行、可口可乐等）。是长期价值投资的标杆。", "highlights": ["巴菲特60年投资传奇，年化收益约20%", "持有多只优质股票（苹果、美国银行等）", "保险浮存金超1600亿美元", "账面价值长期高于股价"], "outlook": "在当前高利率环境下，伯克希尔的保险+投资双轮驱动模式持续稳健。长期持有是'和时间做朋友'的最佳实践。"},
    # 2026-06-17 补全
    "IVV":   {"thesis": "IVV是贝莱德iShares系列中的旗舰标普500ETF，费率仅0.03%，与VOO并列全市场最低梯队。追踪美国500家最大上市公司，与SPY高度类似但费率更低，是长期低成本配置美国大盘股的首选工具。", "highlights": ["费率0.03%，行业最低梯队", "追踪标普500，持有503只大盘股", "日均成交量约300万股，流动性好", "贝莱德发行，全球前三大ETF之一"], "outlook": "在美国经济软着陆预期下，IVV作为低成本大盘股配置工具值得关注。0.03%的费率在20年维度上可节省约4%的费用复利。"},
    "VEA":   {"thesis": "VEA（Vanguard FTSE Developed Markets ETF）以0.05%的超低费率覆盖美国以外的全球发达市场（日本、英国、德国等）。是想要非美国资产分散化配置的投资者必备工具，与VWO（新兴市场）组合可覆盖全球股市。", "highlights": ["费率仅0.05%，发达市场最低之一", "覆盖约4000只非美发达市场股票", "日本、英国、欧洲分散布局", "与VWO组合可实现全球覆盖"], "outlook": "非美发达市场当前估值低于美国，欧元区和日本经济复苏预期下，VEA中期有估值修复机会。但汇率风险是主要不确定性。"},
    "IEFA":  {"thesis": "IEFA（iShares Core MSCI EAFE ETF）追踪MSCI EAFE指数，覆盖欧洲、澳大利亚和远东发达市场（不含美国和加拿大）。费率0.32%，是投资非美发达市场的核心工具，适合想要与美国股市形成互补配置的投资者。", "highlights": ["追踪MSCI EAFE，覆盖21个发达市场", "欧洲+日本+澳大利亚分散布局", "不含美国，与SPY/IVV形成互补", "贝莱德iShares品牌，品质可靠"], "outlook": "IEFA不含美国，与A股/港股低相关，是全球化分散配置的重要组成部分。当前非美市场估值折价明显，中期具备配置价值。"},
    "VWO":   {"thesis": "VWO（Vanguard FTSE Emerging Markets ETF）以0.08%的超低费率覆盖新兴市场（中国、印度、巴西、台湾、韩国等）。费率远低于同类主动基金，是新兴市场分散配置的成本效益最优选择。", "highlights": ["费率仅0.08%，新兴市场最低梯队", "覆盖约5500只新兴市场股票", "中国、印度、巴西、台湾、韩国", "Vanguard品牌，低成本指数投资标杆"], "outlook": "新兴市场估值处于历史低位，中国政策宽松、印度经济高增长是主要看点。但地缘政治风险和汇率波动需关注，适合长期配置而非短期炒作。"},
}

# ── 真实基金/股票基础数据（expense_ratio / AUM / 成交量等） ──
# 数据来源：ETF.com, Yahoo Finance, 各大资管公司官网（2025年数据）
FUNDAMENTAL = {
    "SPY":    {"expense_ratio": "0.09%", "aum": "571B", "avg_daily_volume": "82.3M", "inception_date": "1993-01-22", "issuer": "State Street", "holdings_count": "503", "dividend_freq": "季度", "tracked_index": "S&P 500"},
    "QQQ":    {"expense_ratio": "0.20%", "aum": "262B", "avg_daily_volume": "45.6M", "inception_date": "1999-03-10", "issuer": "Invesco", "holdings_count": "101", "dividend_freq": "季度", "tracked_index": "Nasdaq-100"},
    "VOO":    {"expense_ratio": "0.03%", "aum": "390B", "avg_daily_volume": "3.2M", "inception_date": "2010-09-07", "issuer": "Vanguard", "holdings_count": "508", "dividend_freq": "季度", "tracked_index": "S&P 500"},
    "VTI":    {"expense_ratio": "0.03%", "aum": "420B", "avg_daily_volume": "3.8M", "inception_date": "2001-01-10", "issuer": "Vanguard", "holdings_count": "~4000", "dividend_freq": "季度", "tracked_index": "CRSP US Total Market"},
    "IWM":    {"expense_ratio": "0.19%", "aum": "71B", "avg_daily_volume": "28.4M", "inception_date": "2000-05-22", "issuer": "iShares", "holdings_count": "~2000", "dividend_freq": "季度", "tracked_index": "Russell 2000"},
    "GLD":    {"expense_ratio": "0.40%", "aum": "65B", "avg_daily_volume": "15.2M", "inception_date": "2004-11-18", "issuer": "State Street", "holdings_count": "实物黄金", "dividend_freq": "无", "tracked_index": "LBMA Gold Price"},
    "BND":    {"expense_ratio": "0.03%", "aum": "95B", "avg_daily_volume": "7.1M", "inception_date": "2007-04-03", "issuer": "Vanguard", "holdings_count": "~10000", "dividend_freq": "月度", "tracked_index": "Bloomberg U.S. Aggregate"},
    "TLT":    {"expense_ratio": "0.15%", "aum": "42B", "avg_daily_volume": "12.8M", "inception_date": "2002-07-26", "issuer": "iShares", "holdings_count": "~40", "dividend_freq": "月度", "tracked_index": "ICE U.S. Treasury 20+"},
    "AAPL":   {"expense_ratio": "N/A",    "aum": "N/A",   "avg_daily_volume": "56M",   "inception_date": "1980-12-12", "issuer": "—", "holdings_count": "—", "dividend_freq": "季度", "tracked_index": "—"},
    "MSFT":   {"expense_ratio": "N/A",    "aum": "N/A",   "avg_daily_volume": "22M",   "inception_date": "1986-03-13", "issuer": "—", "holdings_count": "—", "dividend_freq": "季度", "tracked_index": "—"},
    "GOOGL":  {"expense_ratio": "N/A",    "aum": "N/A",   "avg_daily_volume": "26M",   "inception_date": "2004-08-19", "issuer": "—", "holdings_count": "—", "dividend_freq": "—", "tracked_index": "—"},
    "AMZN":   {"expense_ratio": "N/A",    "aum": "N/A",   "avg_daily_volume": "38M",   "inception_date": "1997-05-15",  "issuer": "—", "holdings_count": "—", "dividend_freq": "—", "tracked_index": "—"},
    "NVDA":   {"expense_ratio": "N/A",    "aum": "N/A",   "avg_daily_volume": "41M",   "inception_date": "1999-01-22",  "issuer": "—", "holdings_count": "—", "dividend_freq": "季度", "tracked_index": "—"},
    "META":   {"expense_ratio": "N/A",    "aum": "N/A",   "avg_daily_volume": "18M",   "inception_date": "2012-05-18",  "issuer": "—", "holdings_count": "—", "dividend_freq": "季度", "tracked_index": "—"},
    "TSLA":   {"expense_ratio": "N/A",    "aum": "N/A",   "avg_daily_volume": "95M",   "inception_date": "2010-06-29",  "issuer": "—", "holdings_count": "—", "dividend_freq": "—", "tracked_index": "—"},
    "BRK.B":  {"expense_ratio": "N/A",    "aum": "N/A",   "avg_daily_volume": "3.2M",  "inception_date": "1996-01-19",  "issuer": "—", "holdings_count": "—", "dividend_freq": "—", "tracked_index": "—"},
    # ── 2026-06-17 补全 ──
    "IVV":   {"expense_ratio": "0.03%", "aum": "500B",  "avg_daily_volume": "3.1M",  "inception_date": "2000-05-15", "issuer": "iShares", "holdings_count": "503",   "dividend_freq": "季度", "tracked_index": "S&P 500"},
    "VEA":   {"expense_ratio": "0.05%", "aum": "150B",  "avg_daily_volume": "5.3M",  "inception_date": "2007-07-02", "issuer": "Vanguard","holdings_count": "~4000", "dividend_freq": "半年", "tracked_index": "FTSE Developed All Cap ex USA"},
    "IEFA":  {"expense_ratio": "0.32%", "aum": "65B",   "avg_daily_volume": "10.2M", "inception_date": "2001-08-01", "issuer": "iShares", "holdings_count": "~900",  "dividend_freq": "半年", "tracked_index": "MSCI EAFE"},
    "VWO":   {"expense_ratio": "0.08%", "aum": "80B",   "avg_daily_volume": "15.6M", "inception_date": "2005-03-02", "issuer": "Vanguard","holdings_count": "~5500", "dividend_freq": "半年", "tracked_index": "FTSE Emerging"},
}


# ── 基金/股票元数据（用于 watchlist 中有但 metadata.json 中无的标的） ──

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
    "IWM":  {"name": "iShares Russell 2000 ETF", "name_cn": "罗素2000小盘ETF", "full_name": "iShares Russell 2000 ETF", "desc": "追踪罗素2000指数，覆盖美国2000家小盘股，是投资美国中小企业成长的核心工具。"},
    "TLT":  {"name": "iShares 20+ Year Treasury Bond ETF", "name_cn": "长期国债ETF", "full_name": "iShares 20+ Year Treasury Bond ETF", "desc": "追踪美国长期国债指数，持有20年以上到期的国债，是利率敏感型资产配置的核心工具。"},
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
    """JSON 优先（499条历史数据）→ DB 兜底（实时价格）→ 无数据"""
    # 优先从 JSON 文件读取完整历史（2024-06-17 至今，~500条）
    old_json = OUTPUT / f"{ticker}.json"
    if old_json.exists():
        try:
            jdata = json.loads(old_json.read_text(encoding="utf-8"))
            prices = jdata.get("prices") or jdata.get("data") or []
            if prices:
                data = [{"date": p.get("date", p.get("Date", "")), "open": float(p.get("Open", p.get("open", 0))),
                         "high": float(p.get("High", p.get("high", 0))), "low": float(p.get("Low", p.get("low", 0))),
                         "close": float(p.get("Close", p.get("close", 0))), "volume": int(float(p.get("Volume", 0)))}
                        for p in prices]
                data = sorted(data, key=lambda x: x["date"])
                # DB 补充最新价格（若 DB 数据更新则覆盖）
                db_data = fetch_from_db(ticker)
                if db_data and db_data[-1]["date"] > data[-1]["date"]:
                    # 有更新的 DB 数据：追加并保持 JSON 的历史
                    last_json_date = data[-1]["date"]
                    for row in reversed(db_data):
                        if row["date"] > last_json_date:
                            data.append(row)
                    data.sort(key=lambda x: x["date"])
                    print(f"    [JSON+DB] {ticker} ← JSON({len(data)-len(db_data)} records) + DB({len(db_data)} new)")
                else:
                    print(f"    [JSON] {ticker} ← JSON ({len(data)} records)")
                return data
        except Exception as e:
            print(f"    [JSON ERR] {ticker}: {e}")

    # DB 兜底
    data = fetch_from_db(ticker)
    if data:
        print(f"    [DB] {ticker} ← SQLite ({len(data)} records)")
        return data

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


# ── 从价格数据计算各周期收益率 ───────────────
def calc_performance_rows(data):
    """基于历史价格数据计算 1M/3M/6M/YTD/1Y/3Y 各周期收益"""
    if not data or len(data) < 5:
        return []

    def ret(p_start, p_end):
        if not p_start or not p_end or p_start == 0:
            return None
        return (p_end - p_start) / p_start * 100

    rows = []
    latest = data[-1]["close"]
    prices = {d["date"]: d["close"] for d in data}

    # 按日期排序
    sorted_dates = sorted(prices.keys())
    if not sorted_dates:
        return []

    today_str = sorted_dates[-1]
    from datetime import datetime as dt
    try:
        today_dt = dt.strptime(today_str, "%Y-%m-%d")
    except:
        return []

    # Helper: find price on or before target date
    def price_on(target_str):
        if target_str in prices:
            return prices[target_str]
        # binary search
        for d in reversed(sorted_dates):
            if d <= target_str:
                return prices[d]
        return None

    # Helper: find price closest date in past N days
    def price_days_ago(n):
        try:
            past = (today_dt - timedelta(days=n)).strftime("%Y-%m-%d")
            return price_on(past)
        except:
            return None

    periods = [
        ("1个月",  21),
        ("3个月",  63),
        ("6个月", 126),
        ("YTD",   None),
        ("1年",  252),
    ]

    # YTD: find Jan 1 of this year
    ytd_start = f"{today_dt.year}-01-01"

    for label, days in periods:
        if label == "YTD":
            p_start = price_on(ytd_start)
        else:
            p_start = price_days_ago(days)

        if p_start and latest:
            r = (latest - p_start) / p_start * 100
            sign = "+" if r >= 0 else ""
            rows.append({
                "period": label,
                "return": f"{sign}{r:.2f}%",
                "annualized": None,   # 不足1年的不年化
                "max_drawdown": "—",
                "sharpe": "—",
            })

    return rows


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
        fund = FUNDAMENTAL.get(ticker, {})
        meta = {
            "ticker": ticker,
            "name": base.get("name", ticker),
            "name_cn": base.get("name_cn", base.get("name", ticker)),
            "full_name": base.get("full_name", base.get("name", ticker)),
            "description": base.get("desc", ""),
            "category": "ETF" if ticker in {**ETF_META} else "股票",
            "expense_ratio": fund.get("expense_ratio", "N/A"),
            "aum": fund.get("aum", "N/A"),
            "avg_daily_volume": fund.get("avg_daily_volume", "—"),
            "inception_date": fund.get("inception_date", "—"),
            "issuer": fund.get("issuer", "—"),
            "holdings_count": fund.get("holdings_count", "—"),
            "dividend_freq": fund.get("dividend_freq", "—"),
            "tracked_index": fund.get("tracked_index", "—"),
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
        if "price" not in meta:
            meta["price"] = 0.0
        if "day_change" not in meta:
            meta["day_change"] = 0.0
        if "day_change_pct" not in meta:
            meta["day_change_pct"] = 0.0

    # 计算历史收益（如果 price data 充足）
    if data and len(data) >= 10:
        meta["performance"] = calc_performance_rows(data)

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
        "research": RESEARCH.get(ticker),
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
    # 获取最新数据日期
    latest_date = ""
    all_overview = etf_overview + stock_overview
    for item in all_overview:
        if item.get("price_history"):
            latest_date = item["price_history"][-1]["date"]
            break
    return tmpl.render(
        etf_data=json.dumps(etf_overview, ensure_ascii=False),
        stock_data=json.dumps(stock_overview, ensure_ascii=False),
        latest_date=latest_date,
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
        research=d.get("research"),
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
