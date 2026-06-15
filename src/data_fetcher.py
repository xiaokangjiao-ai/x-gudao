# -*- coding: utf-8 -*-
"""
X-Gudao 数据获取模块
支持股票、ETF、指数、加密货币数据获取（Yahoo Finance）
"""

import yfinance as yf
import pandas as pd
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class DataFetcher:
    """金融数据获取器"""
    
    def __init__(self):
        self.session = None
    
    def get_stock_data(
        self,
        symbol: str,
        period: str = "2y",
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        获取股票/ETF历史数据
        
        Args:
            symbol: 股票代码 (如 AAPL, VOO, QQQ, SPY)
            period: 时间范围 (1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max)
            interval: 数据间隔 (1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo)
            start: 开始日期 (YYYY-MM-DD)，优先于 period
            end: 结束日期 (YYYY-MM-DD)
        
        Returns:
            包含 OHLCV 数据的 DataFrame
        """
        logger.info(f"Fetching {symbol} data, period={period}, interval={interval}")
        
        ticker = yf.Ticker(symbol)
        
        if start and end:
            df = ticker.history(start=start, end=end, interval=interval)
        else:
            df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return pd.DataFrame()
        
        # 标准化列名
        df.columns = [col.lower() for col in df.columns]
        df.index.name = 'date'
        df = df.reset_index()
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        
        logger.info(f"Fetched {len(df)} rows for {symbol}")
        return df
    
    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """获取股票基本信息"""
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            'symbol': symbol,
            'shortName': info.get('shortName', 'N/A'),
            'longName': info.get('longName', 'N/A'),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'marketCap': info.get('marketCap', 0),
            'currency': info.get('currency', 'USD'),
            'exchange': info.get('exchange', 'N/A'),
            'description': info.get('longBusinessSummary', 'N/A')[:500],
            # 基本面指标
            'trailingPE': info.get('trailingPE', None),
            'forwardPE': info.get('forwardPE', None),
            'priceToBook': info.get('priceToBook', None),
            'priceToSalesTrailing12Months': info.get('priceToSalesTrailing12Months', None),
            'returnOnEquity': info.get('returnOnEquity', None),
            'revenueGrowth': info.get('revenueGrowth', None),
            'earningsGrowth': info.get('earningsGrowth', None),
            'grossMargins': info.get('grossMargins', None),
            'operatingMargins': info.get('operatingMargins', None),
            'profitMargins': info.get('profitMargins', None),
            'dividendYield': info.get('dividendYield', 0),
            'beta': info.get('beta', 1.0),
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh', 0),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow', 0),
            'currentPrice': info.get('currentPrice', info.get('regularMarketPrice', 0)),
        }
    
    def get_multiple_stocks(
        self,
        symbols: List[str],
        period: str = "2y",
        interval: str = "1d",
    ) -> Dict[str, pd.DataFrame]:
        """批量获取多只股票数据"""
        results = {}
        for sym in symbols:
            try:
                df = self.get_stock_data(sym, period=period, interval=interval)
                if not df.empty:
                    results[sym] = df
                else:
                    logger.warning(f"No data for {sym}, skipping")
            except Exception as e:
                logger.error(f"Error fetching {sym}: {e}")
        return results
    
    def get_financials(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """获取财务报表数据"""
        ticker = yf.Ticker(symbol)
        return {
            'income_statement': ticker.income_stmt,
            'quarterly_income': ticker.quarterly_income_stmt,
            'balance_sheet': ticker.balance_sheet,
            'quarterly_balance': ticker.quarterly_balance_sheet,
            'cashflow': ticker.cashflow,
            'quarterly_cashflow': ticker.quarterly_cashflow,
        }
    
    def save_to_csv(self, df: pd.DataFrame, filepath: str) -> None:
        """保存数据到 CSV"""
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        logger.info(f"Saved data to {filepath}")
    
    def save_to_json(self, data: Dict, filepath: str) -> None:
        """保存数据到 JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"Saved data to {filepath}")


def get_index_data(symbols: List[str], period: str = "5y") -> Dict[str, pd.DataFrame]:
    """便捷函数：获取指数/ETF 对比数据"""
    fetcher = DataFetcher()
    return fetcher.get_multiple_stocks(symbols, period=period)


if __name__ == "__main__":
    # 测试
    fetcher = DataFetcher()
    
    # 测试单只股票
    print("=== 测试: VOO ===")
    df = fetcher.get_stock_data("VOO", period="6mo")
    print(df.tail())
    print(f"\nShape: {df.shape}")
    
    # 测试信息
    print("\n=== VOO 基本信息 ===")
    info = fetcher.get_stock_info("VOO")
    for k, v in list(info.items())[:10]:
        print(f"  {k}: {v}")
