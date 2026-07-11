#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成各持仓标的研究报告 Markdown"""
import json, os
from datetime import datetime

REPORTS_DIR = r"C:\Users\Administrator\x-gudao\gh-pages\src\data\reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

# 从 overview.json 读取最新数据
with open(r"C:\Users\Administrator\x-gudao\gh-pages\overview.json", encoding="utf-8") as f:
    stocks = json.load(f)

# 股票分析字典 (名称, 行业分析要点, 关键驱动因素)
ANALYSIS = {
    "NVDA": {
        "name": "英伟达 (NVIDIA)", "sec": "AI半导体", "pe": "~45x", "fwd": "强劲",
        "bull": "数据中心需求爆发，Blackwell架构放量，AI算力投资持续。",
        "bear": "估值高，增长放缓时波动大；中国出口限制持续影响。",
        "verdict": "持仓观望，250美元下方可加仓。"
    },
    "AAPL": {
        "name": "苹果 (Apple)", "sec": "科技消费", "pe": "~28x", "fwd": "稳健",
        "bull": "iPhone AI功能提振换机需求，服务收入持续增长，股票回购支撑股价。",
        "bear": "中国市场竞争加剧，监管风险，估值已较高。",
        "verdict": "核心持仓，300美元下方具吸引力。"
    },
    "MSFT": {
        "name": "微软 (Microsoft)", "sec": "科技软件", "pe": "~33x", "fwd": "稳健",
        "bull": "Azure AI云增长强劲，Copilot产品渗透率提升，企业端需求稳定。",
        "bear": "资本开支大幅增加压制短期利润率，技术整合周期风险。",
        "verdict": "长期看好，380美元下方可持有。"
    },
    "GOOGL": {
        "name": "谷歌 (Alphabet)", "sec": "科技广告/AI", "pe": "~22x", "fwd": "良好",
        "bull": "搜索+YouTube广告稳健，Gemini AI追赶中，Waymo商业化加速。",
        "bear": "AI搜索对广告模式冲击待观察，反垄断压力持续。",
        "verdict": "估值偏低，基本面改善，适合逢低布局。"
    },
    "AMZN": {
        "name": "亚马逊 (Amazon)", "sec": "电商/云", "pe": "~36x", "fwd": "良好",
        "bull": "AWS恢复增长，广告业务高增，Prime会员粘性极强。",
        "bear": "零售利润率承压，竞争加剧（TikTok Shop、Temu）。",
        "verdict": "持有，220美元强支撑。"
    },
    "META": {
        "name": "Meta Platforms", "sec": "社交广告", "pe": "~24x", "fwd": "良好",
        "bull": "AI推荐改善广告效率，Reels货币化加速，元宇宙减亏。",
        "bear": "监管趋严，用户增长放缓，iOS隐私政策持续影响。",
        "verdict": "高性价比AI标的，500美元下方值得持有。"
    },
    "LLY": {
        "name": "礼来 (Eli Lilly)", "sec": "制药/减肥药", "pe": "~55x", "fwd": "强劲",
        "bull": "替尔泊肽放量超预期，减肥药市场空间巨大，阿尔茨海默管线进展积极。",
        "bear": "估值极高，GLP-1竞争加剧（诺和诺德、安进）。",
        "verdict": "高确定性成长，可小仓位持有。"
    },
    "BRK.B": {
        "name": "伯克希尔B (Berkshire)", "sec": "综合性投资", "pe": "~21x", "fwd": "稳健",
        "bull": "保险+铁路+能源组合稳健，巴菲特持仓现金充裕，防御性强。",
        "bear": "超大市值限制弹性，子业务庞杂难以跟踪。",
        "verdict": "长期核心持仓，防卫首选。"
    },
    "VOO": {
        "name": "Vanguard 标普500 ETF", "sec": "美国大盘指数", "pe": "N/A", "fwd": "稳健",
        "bull": "分散投资、低费率（0.03%），美国经济韧性，长期复利稳定。",
        "bear": "短期受高利率/衰退预期压制，汇率风险（对冲基金投资者）。",
        "verdict": "长期定投标的，核心配置。"
    },
    "QQQ": {
        "name": "Invesco 纳指100 ETF", "sec": "美国科技指数", "pe": "N/A", "fwd": "良好",
        "bull": "AI驱动科技长期增长，纳斯达克长期超额收益明显。",
        "bear": "高波动，科技占比>55%集中风险。",
        "verdict": "成长型仓位，逢低定投。"
    },
    "IWM": {
        "name": "iShares 罗素2000 ETF", "sec": "美国小盘指数", "pe": "N/A", "fwd": "中性",
        "bull": "美国小盘股估值洼地，经济软着陆利好小盘。",
        "bear": "对小盘银行利率敏感，国内经济疲软时承压。",
        "verdict": "经济预期改善时可增配。"
    },
    "BND": {
        "name": "Vanguard 全债券市场 ETF", "sec": "债券", "pe": "N/A", "fwd": "稳定",
        "bull": "降息周期受益，美股对冲工具，现金流稳定。",
        "bear": "利率未如预期下降则亏损，通胀回升风险。",
        "verdict": "5%-10%配置用于风险对冲。"
    },
    "GLD": {
        "name": "SPDR 黄金 ETF", "sec": "黄金", "pe": "N/A", "fwd": "中性",
        "bull": "央行购金热，地缘风险避险，实际利率下行利好。",
        "bear": "美元强势压制金价，无现金流。",
        "verdict": "5%-10%配置，避险用途。"
    },
    "SCHD": {
        "name": "Schwab 道指优选股息 ETF", "sec": "美国高股息", "pe": "N/A", "fwd": "稳定",
        "bull": "高股息蓝筹，美国经济韧性，现金流好。",
        "bear": "高股息股在加息环境承压，部分持仓基本面恶化。",
        "verdict": "持有，关注股息可持续性。"
    },
    "VXUS": {
        "name": "Vanguard 全球除美 ETF", "sec": "全球股市", "pe": "N/A", "fwd": "中性",
        "bull": "非美市场估值低，欧洲/日本基本面改善。",
        "bear": "汇率风险，欧元区增长疲软。",
        "verdict": "分散配置用途，10%仓位。"
    },
    "SMH": {
        "name": "VanEck 半导体 ETF", "sec": "半导体", "pe": "N/A", "fwd": "良好",
        "bull": "AI驱动半导体长期需求，设备/材料龙头受益。",
        "bear": "周期性强，存储/逻辑价格波动大。",
        "verdict": "AI主题配置，半导体上行周期持有。"
    },
    "300750": {
        "name": "宁德时代", "sec": "新能源汽车电池", "pe": "~18x", "fwd": "良好",
        "bull": "全球动力电池龙头，储能业务爆发，麒麟电池/神行超充引领技术。",
        "bear": "竞争加剧（比亚迪弗迪），原材料价格波动，产能过剩风险。",
        "verdict": "持有，新能源汽车渗透率提升逻辑不变。"
    },
    "603259": {
        "name": "药明康德", "sec": "CXO医药外包", "pe": "~16x", "fwd": "改善",
        "bull": "全球CXO需求稳定，CGT/多肽等新业务拓展，在手订单充足。",
        "bear": "美国《生物安全法》风险，客户去风险化，汇率波动。",
        "verdict": "持有，等待地缘风险边际改善。"
    },
    "002475": {
        "name": "立讯精密", "sec": "消费电子精密制造", "pe": "~20x", "fwd": "中性",
        "bull": "苹果产业链核心供应商，汽车/通信业务拓展。",
        "bear": "苹果依赖度高，消费电子需求疲软，竞争激烈。",
        "verdict": "持有，关注汽车业务增速。"
    },
    "000858": {
        "name": "五粮液", "sec": "高端白酒", "pe": "~14x", "fwd": "中性",
        "bull": "浓香白酒龙头，品牌力强，批价企稳，渠道库存改善。",
        "bear": "商务消费承压，白酒行业库存周期未见拐点，竞争加剧。",
        "verdict": "观望，等待库存周期拐点和批价回升信号。"
    },
    "600519": {
        "name": "贵州茅台", "sec": "高端白酒", "pe": "~22x", "fwd": "稳健",
        "bull": "最强品牌护城河，直销占比持续提升，i茅台数字化推进。",
        "bear": "高端白酒批价松动，商务需求疲软，长期增速放缓。",
        "verdict": "长期核心持仓，控制仓位。"
    },
    "000333": {
        "name": "美的集团", "sec": "家电龙头", "pe": "~12x", "fwd": "稳健",
        "bull": "家电+机器人双主业，海外营收占比提升，盈利能力稳定。",
        "bear": "地产后周期需求疲软，家电内销承压。",
        "verdict": "低估值高分红的稳健标的。"
    },
    "300760": {
        "name": "迈瑞医疗", "sec": "医疗器械", "pe": "~28x", "fwd": "稳健",
        "bull": "国产医疗器械龙头，受益医疗新基建，海外高端突破。",
        "bear": "医疗反腐持续，招标降价压力，估值不低。",
        "verdict": "持有，医疗器械国产替代长逻辑。"
    },
    "000661": {
        "name": "长春高新", "sec": "生物制药/生长激素", "pe": "~12x", "fwd": "改善",
        "bull": "生长激素龙头长效水针占比提升，成人生长激素新蓝海。",
        "bear": "广东联盟集采降价，新患入组增速放缓，竞争加剧。",
        "verdict": "持有，关注成人生长激素市场拓展。"
    },
    "002007": {
        "name": "华兰生物", "sec": "血制品/疫苗", "pe": "~22x", "fwd": "中性",
        "bull": "血制品供需偏紧提价，流感疫苗旺季放量。",
        "bear": "血制品浆站拓展受限，疫苗竞争加剧。",
        "verdict": "小仓位持有，等待血制品涨价兑现。"
    },
    "601398": {
        "name": "工商银行", "sec": "国有银行", "pe": "~5x", "fwd": "稳定",
        "bull": "中国最稳定银行之一，股息率高（~5%+），防御性强。",
        "bear": "净息差收窄，资产质量压力，经济增长放缓。",
        "verdict": "高股息防御配置，适合低风险偏好。"
    },
    "601288": {
        "name": "农业银行", "sec": "国有银行", "pe": "~5x", "fwd": "稳定",
        "bull": "县域金融优势，股息率高（~5%+），拨备充足。",
        "bear": "净息差持续收窄，资产质量不确定性。",
        "verdict": "高股息防御配置，与工行配置逻辑相同。"
    },
    "601318": {
        "name": "中国平安", "sec": "综合金融/保险", "pe": "~8x", "fwd": "改善",
        "bull": "寿险改革成效显现，新业务价值增速转正，医疗生态协同。",
        "bear": "资本市场波动影响投资收益，代理人转型阵痛。",
        "verdict": "持有，保险行业复苏逻辑。"
    },
    "600887": {
        "name": "伊利股份", "sec": "乳制品龙头", "pe": "~14x", "fwd": "稳定",
        "bull": "乳制品绝对龙头，原奶价格低位利好成本，下沉市场渗透。",
        "bear": "消费需求疲软，竞争激烈（蒙牛），费用率居高不下。",
        "verdict": "持有，等待消费复苏带来弹性。"
    },
    "000651": {
        "name": "格力电器", "sec": "家电/空调", "pe": "~8x", "fwd": "稳定",
        "bull": "空调龙头定价权强，股息率高，渠道改革成效显现。",
        "bear": "地产后周期影响空调需求，多元化成效待验证。",
        "verdict": "低估值高分红，价值重估潜力。"
    },
    "601888": {
        "name": "中国中免", "sec": "免税零售", "pe": "~18x", "fwd": "改善",
        "bull": "免税牌照优势，三亚机场客流恢复，线上直邮拓展。",
        "bear": "消费降级压制高端消费，竞争加剧（王府井等）。",
        "verdict": "持有，免税行业长期空间大。"
    },
    "002594": {
        "name": "比亚迪", "sec": "新能源汽车", "pe": "~20x", "fwd": "良好",
        "bull": "新能源车全球销量冠军，规模化成本优势，智能驾驶技术追赶。",
        "bear": "价格战压制利润率，海外贸易壁垒增加。",
        "verdict": "核心持仓，新能源渗透率逻辑持续。"
    },
    "603501": {
        "name": "韦尔股份", "sec": "半导体图像传感器", "pe": "~30x", "fwd": "改善",
        "bull": "手机CIS龙头，车载CIS高速增长，库存去化接近尾声。",
        "bear": "手机需求未见明显复苏，竞争加剧（索尼/三星）。",
        "verdict": "持有，等待手机CIS需求复苏。"
    },
    "688981": {
        "name": "中芯国际", "sec": "半导体晶圆代工", "pe": "~35x", "fwd": "良好",
        "bull": "成熟制程国产替代主力，AIoT/汽车电子需求旺盛，政策支持。",
        "bear": "美国出口管制升级风险，资本开支大折旧压力。",
        "verdict": "持有，国产替代核心标的。"
    },
}

today = datetime.now().strftime("%Y-%m-%d")

for stock in stocks:
    ticker = stock["ticker"]
    info = ANALYSIS.get(ticker, {
        "name": ticker, "sec": "ETF/股票", "pe": "N/A", "fwd": "N/A",
        "bull": "数据分析中...", "bear": "请关注风险。",
        "verdict": "建议持续关注。"
    })
    
    # 涨跌标识
    chg = stock.get("change_pct", 0)
    emoji = "📈" if chg >= 0 else "📉"
    chg_str = f"+{chg:.2f}%" if chg >= 0 else f"{chg:.2f}%"
    
    # 年化收益
    ann_ret = stock.get("annual_return", 0)
    ret_emoji = "💹" if ann_ret >= 0 else "⚠️"
    
    # 格式化辅助函数
    def fmt(val, decimals=2):
        if val is None or val == 0:
            return 'N/A'
        try:
            return f'{float(val):.{decimals}f}'
        except:
            return str(val)
    
    def fmt_price(val):
        if val is None or val == 0:
            return 'N/A'
        try:
            return f'¥{float(val):.2f}'
        except:
            return str(val)
    
    ma20_val = stock.get('ma20', 0) or 0
    ma50_val = stock.get('ma50', 0) or 0
    ma200_val = stock.get('ma200', 0) or 0
    latest_close = stock.get('latest_close', 0) or 0
    
    def ma_relation(ma_val):
        if not ma_val:
            return '数据不足'
        return '高于现价' if ma_val > latest_close else '低于现价'
    
    md = f"""# {info['name']} ({ticker}) 分析报告

> **更新时间**: {today} | **最新价**: {fmt_price(latest_close)} {emoji} {chg_str}  
> **数据类型**: {stock.get('date_range', 'N/A')}

---

## 一、基本信息

| 项目 | 内容 |
|------|------|
| 证券代码 | {ticker} |
| 证券名称 | {info['name']} |
| 所属行业 | {info['sec']} |
| 最新收盘 | {fmt_price(latest_close)} |
| 日涨跌 | {chg_str} |
| 52周最高 | {fmt_price(stock.get('high', 0))} |
| 52周最低 | {fmt_price(stock.get('low', 0))} |
| 年化收益率 | {ret_emoji} {fmt(ann_ret)}% |
| 年化波动率 | {fmt(stock.get('volatility', 0))}% |

---

## 二、技术面分析

### 均线状态

| 指标 | 数值 | 与现价关系 |
|------|------|-----------|
| MA20 | {fmt_price(ma20_val)} | {ma_relation(ma20_val)} |
| MA50 | {fmt_price(ma50_val)} | {ma_relation(ma50_val)} |
| MA200 | {fmt_price(ma200_val)} | {ma_relation(ma200_val)} |

> 📊 数据来源: {stock.get('data_points', 'N/A')} 个交易日 ({stock.get('date_range', 'N/A')})

---

## 三、基本面要点

### 利好因素 🚀
{info['bull']}

### 风险因素 ⚠️
{info['bear']}

---

## 四、综合研判

**估值参考**: PE约 {info['pe']} | **前瞻**: {info['fwd']}

### 📌 调仓建议
{info['verdict']}

---

## 五、近期重要事件（2026年7月）

- **宏观**: 7月美联储暂无FOMC会议，9月降息预期升温；A股中报季（7-8月）密集披露
- **行业**: {info['sec']}行业最新动态请参考相关研报
- **政策**: 中国稳增长政策持续，关注财政/货币宽松信号

---

> ⚠️ **免责声明**: 本报告由系统自动生成，基于历史数据与公开信息，仅供参考，不构成投资建议。过往表现不代表未来收益。投资有风险，决策需谨慎。
>
> *x-gudao 量化分析系统 | {today}*
"""
    
    path = os.path.join(REPORTS_DIR, f"{ticker}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[OK] {ticker}.md")

print(f"\n[DONE] 共生成 {len(stocks)} 份研究报告 -> {REPORTS_DIR}")
