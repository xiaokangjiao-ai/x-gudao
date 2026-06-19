# -*- coding: utf-8 -*-
"""
X-Gudao 数据获取模块
支持股票、ETF、指数、加密货币数据获取（Yahoo Finance）
带重试机制和限流保护
"""

import yfinance as yf
import pandas as pd
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class DataFetcher:
    """金融数据获取器"""
    
    def __init__(self):
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 最小请求间隔（秒）
    
    def _rate_limit_wait(self):
        """限流等待"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed
            logger.debug(f"限流等待 {wait_time:.1f}s")
            time.sleep(wait_time)
        self.last_request_time = time.time()
    
    def get_stock_data(
        self,
        symbol: str,
        period: str = "2y",
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
        max_retries: int = 3,
    ) -> pd.DataFrame:
        """
        获取股票/ETF 历史数据
        
        Args:
            symbol: 股票代码 (如 VOO, QQQ, SPY, AAPL)
            period: 数据周期 (1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,max)
            interval: 数据间隔 (1d,1wk,1mo)
            start: 开始日期 (YYYY-MM-DD)
            end: 结束日期 (YYYY-MM-DD)
        
        Returns:
            DataFrame with OHLCV data
        """
        for attempt in range(max_retries + 1):
            try:
                self._rate_limit_wait()
                
                ticker = yf.Ticker(symbol)
                
                if start and end:
                    df = ticker.history(start=start, end=end, interval=interval)
                else:
                    df = ticker.history(period=period, interval=interval)
                
                if df.empty:
                    logger.warning(f"No data for {symbol}")
                    return pd.DataFrame()
                
                # 标准化 DataFrame
                df = df.reset_index()
                df.columns = [str(c).lower().replace(' ', '_') for c in df.columns]
                
                # 确保必要列存在
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                missing_cols = [c for c in required_cols if c not in df.columns]
                if missing_cols:
                    logger.warning(f"{symbol} 缺少列: {missing_cols}")
                    return pd.DataFrame()
                
                # 处理日期列
                date_col = None
                for col in ['date', 'datetime']:
                    if col in df.columns:
                        date_col = col
                        break
                
                if date_col is None:
                    df['date'] = df.index
                    date_col = 'date'
                
                df[date_col] = pd.to_datetime(df[date_col])
                df['date'] = df[date_col].dt.strftime('%Y-%m-%d')
                
                # 计算收益率
                df['daily_return'] = df['close'].pct_change()
                
                # 选择输出列
                output_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'daily_return']
                df = df[[c for c in output_cols if c in df.columns]]
                
                logger.info(f"Fetched {symbol}: {len(df)} rows ({period})")
                return df
            
            except Exception as e:
                error_msg = str(e).lower()
                if 'rate' in error_msg or 'too many' in error_msg or '429' in error_msg:
                    wait = (attempt + 1) * 10  # 递增等待：10s, 20s, 30s
                    logger.warning(f"Rate limited for {symbol}, retry {attempt+1}/{max_retries} after {wait}s")
                    time.sleep(wait)
                elif attempt < max_retries:
                    logger.warning(f"Error fetching {symbol} (attempt {attempt+1}): {e}")
                    time.sleep(2)
                else:
                    logger.error(f"Error fetching {symbol}: {e}")
                    return pd.DataFrame()
        
        return pd.DataFrame()
    
    def get_multiple_stocks(
        self,
        symbols: List[str],
        period: str = "2y",
        interval: str = "1d",
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取多只股票数据
        
        Args:
            symbols: 股票代码列表
            period: 数据周期
            interval: 数据间隔
        
        Returns:
            {symbol: DataFrame} 字典
        """
        results = {}
        
        for i, symbol in enumerate(symbols):
            logger.info(f"Fetching {symbol} data ({i+1}/{len(symbols)})")
            
            df = self.get_stock_data(symbol, period=period, interval=interval)
            
            if not df.empty:
                results[symbol] = df
            else:
                logger.error(f"Failed to get data for {symbol}")
            
            # 每个请求之间额外等待
            if i < len(symbols) - 1:
                time.sleep(1)
        
        return results
    
    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取股票基本信息
        
        Returns:
            包含 P/E、市值等信息的字典
        """
        try:
            self._rate_limit_wait()
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # 提取关键字段
            key_fields = {
                'symbol': symbol,
                'shortName': info.get('shortName'),
                'longName': info.get('longName'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'marketCap': info.get('marketCap'),
                'trailingPE': info.get('trailingPE'),
                'forwardPE': info.get('forwardPE'),
                'priceToBook': info.get('priceToBook'),
                'dividendYield': info.get('dividendYield'),
                'beta': info.get('beta'),
                'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh'),
                'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow'),
                'returnOnEquity': info.get('returnOnEquity'),
                'grossMargins': info.get('grossMargins'),
                'operatingMargins': info.get('operatingMargins'),
                'profitMargins': info.get('profitMargins'),
                'revenueGrowth': info.get('revenueGrowth'),
                'earningsGrowth': info.get('earningsGrowth'),
                'totalRevenue': info.get('totalRevenue'),
                'debtToEquity': info.get('debtToEquity'),
                'currentRatio': info.get('currentRatio'),
                'description': info.get('longBusinessSummary')[:500] if info.get('longBusinessSummary') else None,
            }
            
            return {k: v for k, v in key_fields.items() if v is not None}
        
        except Exception as e:
            logger.error(f"Error getting info for {symbol}: {e}")
            return {'symbol': symbol}
    
    def save_to_csv(
        self,
        df: pd.DataFrame,
        filepath: str,
    ) -> bool:
        """保存数据到 CSV"""
        try:
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            logger.info(f"Saved CSV: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving CSV: {e}")
            return False
    
    def save_to_json(
        self,
        data: Any,
        filepath: str,
    ) -> bool:
        """保存数据到 JSON"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"Saved JSON: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving JSON: {e}")
            return False


if __name__ == "__main__":
    # 测试
    fetcher = DataFetcher()
    
    print("=== 单只股票测试 ===")
    df = fetcher.get_stock_data("AAPL", period="6mo")
    print(df.head())
    
    print("\n=== 多股票测试 ===")
    data = fetcher.get_multiple_stocks(["VOO", "QQQ"], period="1y")
    for sym, d in data.items():
        print(f"{sym}: {len(d)} rows")
