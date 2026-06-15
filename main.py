# -*- coding: utf-8 -*-
"""
X-Gudao 主入口
命令行工具，对标 Macrotrends 的多资产对比分析
"""

import argparse
import logging
import sys
import os
import json
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data_fetcher import DataFetcher
from src.analyzer import TechnicalAnalyzer, FundamentalAnalyzer
from src.visualizer import ChartGenerator
from src.comparator import Comparator
from src.reporter import ReportGenerator
from src.ai_insights import AIInsights

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def main():
    parser = argparse.ArgumentParser(
        description='X-Gudao 金融分析工具 (对标 Macrotrends)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 多资产对比（VOO/QQQ/SPY）
  python main.py --compare VOO QQQ SPY --period 5y

  # 单只股票分析
  python main.py --symbol AAPL --period 2y

  # 带 AI 洞察的对比分析
  python main.py --compare VOO QQQ SPY --period 5y --ai --output ./output

  # 风险平价组合
  python main.py --risk-parity --symbols VOO QQQ SPY --period 3y
        """
    )
    
    # 基本参数
    parser.add_argument('--period', default='2y', help='数据周期 (1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,max)')
    parser.add_argument('--output', default='./output', help='输出目录')
    parser.add_argument('--format', nargs='+', default=['html', 'md'], help='输出格式 (html, md, png)')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    # 分析模式
    parser.add_argument('--symbol', help='单只股票代码')
    parser.add_argument('--compare', nargs='+', help='多资产对比 (如 VOO QQQ SPY)')
    parser.add_argument('--risk-parity', action='store_true', help='风险平价分析模式')
    
    # AI 相关
    parser.add_argument('--ai', action='store_true', help='启用 AI 洞察 (需 Ollama)')
    parser.add_argument('--ollama-url', default='http://localhost:11434', help='Ollama 地址')
    parser.add_argument('--ollama-model', default='qwen2:7b-64k', help='Ollama 模型')
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    os.makedirs(os.path.join(args.output, 'charts'), exist_ok=True)
    os.makedirs(os.path.join(args.output, 'reports'), exist_ok=True)
    os.makedirs(os.path.join(args.output, 'data'), exist_ok=True)
    
    # 初始化组件
    fetcher = DataFetcher()
    tech_analyzer = TechnicalAnalyzer()
    chart_gen = ChartGenerator(os.path.join(args.output, 'charts'))
    reporter = ReportGenerator(os.path.join(args.output, 'reports'))
    
    if args.verbose:
        logger.info(f"分析模式: {'对比' if args.compare else '单资产'}")
        logger.info(f"数据周期: {args.period}")
    
    # === 模式 1: 多资产对比 ===
    if args.compare:
        symbols = args.compare
        logger.info(f"开始对比分析: {symbols}")
        
        # 获取数据
        data = fetcher.get_multiple_stocks(symbols, period=args.period)
        
        if len(data) == 0:
            logger.error("未能获取任何数据，退出")
            return
        
        # 对比分析
        comparator = Comparator()
        results = comparator.compare_assets(data)
        
        # 保存原始数据
        for sym, df in data.items():
            fetcher.save_to_csv(df, os.path.join(args.output, 'data', f'{sym}_data.csv'))
        
        # 生成图表
        logger.info("生成对比图表...")
        chart_gen.plot_comparison(data)
        
        # 相关性热力图
        returns_dict = {sym: df['daily_return'].dropna() for sym, df in data.items()}
        chart_gen.plot_correlation_heatmap(returns_dict)
        
        # 风险收益散点图
        stats_dict = {}
        for sym in symbols:
            stats_dict[sym] = {
                'annualized_return': results['return_stats'][sym]['annualized_return'],
                'volatility': results['risk_stats'][sym]['volatility'],
            }
        chart_gen.plot_risk_return(stats_dict)
        
        # 生成报告
        logger.info("生成分析报告...")
        report = reporter.generate_comparison_report(results)
        reporter.save_report(report, f"{'_'.join(symbols)}_comparison", formats=['md', 'html'] if 'html' in args.format else ['md'])
        
        # AI 洞察
        if args.ai:
            logger.info("生成 AI 洞察...")
            ai = AIInsights(base_url=args.ollama_url, model=args.ollama_model)
            
            if ai.check_connection():
                insights = ai.analyze_comparison(results)
                
                # 保存 AI 洞察
                ai_report_path = os.path.join(args.output, 'reports', f"{'_'.join(symbols)}_ai_insights.md")
                with open(ai_report_path, 'w', encoding='utf-8') as f:
                    f.write(f"# 🤖 AI 智能分析洞察\n\n{insights}\n\n---\n*由 Ollama {args.ollama_model} 生成*\n")
                
                print("\n" + "="*60)
                print("🤖 AI 洞察结果:")
                print("="*60)
                print(insights)
                print("="*60 + "\n")
            else:
                logger.warning("Ollama 未连接，跳过 AI 洞察")
        
        # 打印摘要
        print("\n" + "="*60)
        print("📊 对比分析摘要")
        print("="*60)
        for sym in symbols:
            ret = results['return_stats'][sym]['annualized_return']
            vol = results['risk_stats'][sym]['volatility']
            sharpe = results['risk_stats'][sym]['sharpe_ratio']
            print(f"  {sym}: 收益率 {ret*100:.2f}% | 波动率 {vol*100:.2f}% | 夏普 {sharpe:.3f}")
        
        winner = results['summary']['winner']
        print(f"\n🏆 综合冠军: {winner}")
        print(f"\n📁 报告已保存到: {args.output}/reports/")
    
    # === 模式 2: 单只股票分析 ===
    elif args.symbol:
        symbol = args.symbol
        logger.info(f"分析股票: {symbol}")
        
        # 获取数据
        df = fetcher.get_stock_data(symbol, period=args.period)
        
        if df.empty:
            logger.error(f"未能获取 {symbol} 的数据")
            return
        
        # 技术分析
        df = tech_analyzer.add_all_indicators(df)
        signals = tech_analyzer.get_latest_signals(df)
        
        # 基本面分析
        info = fetcher.get_stock_info(symbol)
        fund_analyzer = FundamentalAnalyzer()
        fund_analysis = fund_analyzer.analyze(info)
        
        # 生成图表
        logger.info("生成技术分析图表...")
        chart_gen.plot_stock_with_indicators(df, symbol)
        
        # 保存数据
        fetcher.save_to_csv(df, os.path.join(args.output, 'data', f'{symbol}_data.csv'))
        fetcher.save_to_json(info, os.path.join(args.output, 'data', f'{symbol}_info.json'))
        
        # AI 洞察
        if args.ai:
            logger.info("生成 AI 洞察...")
            ai = AIInsights(base_url=args.ollama_url, model=args.ollama_model)
            
            if ai.check_connection():
                insights = ai.analyze_technical(symbol, df, signals)
                print("\n" + "="*60)
                print(f"🤖 AI 技术分析: {symbol}")
                print("="*60)
                print(insights)
                print("="*60 + "\n")
            else:
                logger.warning("Ollama 未连接")
        
        # 打印摘要
        print("\n" + "="*60)
        print(f"📈 {symbol} 技术分析摘要")
        print("="*60)
        print(f"  当前价格: ${df['close'].iloc[-1]:.2f}")
        print(f"  趋势: {signals.get('trend', 'N/A')}")
        print(f"  RSI(14): {signals.get('rsi', 0):.2f}")
        print(f"  MACD: {signals.get('macd', 'N/A')}")
        print(f"  综合评分: {signals.get('strength', 0)}/100")
    
    else:
        parser.print_help()
    
    logger.info("分析完成!")


if __name__ == "__main__":
    main()
