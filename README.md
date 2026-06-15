# X-Gudao (股道) 📈

> **对标 Macrotrends 的中文金融数据分析平台**
> 
> 基于本地 Ollama (Qwen2) + Python 的智能金融分析系统

## ✨ 功能特性

- 📊 **多资产数据获取** — 股票、ETF、指数、加密货币（Yahoo Finance）
- 📈 **技术分析** — 移动平均线、RSI、MACD、布林带、波动率
- 💰 **基本面分析** — P/E、P/B、ROE、营收增长、利润率
- 🔍 **多资产对比** — 收益、风险、相关性分析（如 VOO/QQQ/SPY）
- 📉 **风险平价组合** — 滚动窗口风险平价 + 回测
- 🎨 **交互式可视化** — Plotly 交互式图表
- 📄 **自动报告生成** — Markdown/HTML 分析报告
- 🤖 **AI 智能分析** — 接入本地 Ollama Qwen2 模型生成洞察

## 🏗️ 项目结构

```
x-gudao/
├── README.md                 # 项目说明
├── requirements.txt          # Python 依赖
├── config.json               # 配置文件
├── src/
│   ├── __init__.py
│   ├── data_fetcher.py       # 数据获取模块
│   ├── analyzer.py           # 分析引擎（技术+基本面）
│   ├── visualizer.py         # 可视化模块
│   ├── comparator.py         # 多资产对比
│   ├── risk_parity.py        # 风险平价策略
│   ├── reporter.py           # 报告生成器
│   └── ai_insights.py        # AI 智能洞察（Ollama）
├── web/                      # Web 仪表盘（可选）
│   └── app.py
├── output/                   # 输出目录
│   ├── reports/
│   ├── charts/
│   └── data/
└── main.py                   # CLI 入口
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 Ollama（本地模型）

```bash
ollama serve
ollama pull qwen2:7b-64k
```

### 3. 运行分析

```bash
# 单只股票分析
python main.py --symbol AAPL --period 2y

# 多资产对比（对标 Macrotrends 风格）
python main.py --compare VOO QQQ SPY --period 5y --output ./output

# 风险平价回测
python main.py --risk-parity --portfolio portfolio.json --output ./output

# 完整报告（含 AI 洞察）
python main.py --symbol TSLA --period 3y --ai --output ./output
```

## 📊 对标 Macrotrends 功能矩阵

| 功能 | Macrotrends | X-Gudao |
|------|------------|---------|
| 股票历史价格图表 | ✅ | ✅ |
| 财务指标（P/E等） | ✅ | ✅ |
| 多指数对比 | ✅ | ✅ |
| 宏观经济数据 | ✅ | 🚧 开发中 |
| 交互式图表 | ✅ | ✅（Plotly） |
| 数据导出 CSV | ✅ | ✅ |
| AI 智能洞察 | ❌ | ✅（Ollama 本地） |
| 风险平价回测 | ❌ | ✅ |
| 中文支持 | ❌ | ✅ |

## ⚙️ 配置说明

编辑 `config.json`：

```json
{
  "ollama": {
    "base_url": "http://localhost:11434",
    "model": "qwen2:7b-64k"
  },
  "analysis": {
    "default_period": "2y",
    "risk_free_rate": 0.04,
    "ma_windows": [20, 50, 200]
  },
  "output": {
    "format": ["html", "markdown"],
    "chart_format": "png"
  }
}
```

## 🛠️ 技术栈

- **数据源**: yfinance (Yahoo Finance)
- **分析**: pandas, numpy, scipy
- **可视化**: matplotlib, seaborn, plotly
- **AI 引擎**: Ollama + Qwen2 (本地运行)
- **Web**: Flask/Streamlit (可选)

## 📝 License

MIT License
