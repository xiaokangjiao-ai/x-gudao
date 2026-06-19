# -*- coding: utf-8 -*-
"""
X-Gudao 分析引擎
技术分析 + 基本面分析
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from scipy import stats


class TechnicalAnalyzer:
    """技术分析引擎"""
    
    def __init__(self, risk_free_rate: float = 0.04):
        self.risk_free_rate = risk_free_rate  # 年化无风险利率
    
    def add_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加所有技术指标"""
        df = df.copy()
        close = df['close']
        
        # 移动平均线
        for window in [20, 50, 200]:
            df[f'ma_{window}'] = close.rolling(window=window).mean()
            df[f'ma_{window}_signal'] = close > df[f'ma_{window}']
        
        # EMA
        for window in [12, 26]:
            df[f'ema_{window}'] = close.ewm(span=window, adjust=False).mean()
        
        # RSI
        df['rsi_14'] = self._calculate_rsi(close, 14)
        
        # MACD
        macd, signal, hist = self._calculate_macd(close)
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_hist'] = hist
        
        # 布林带
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = self._calculate_bollinger_bands(close)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (close - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # 波动率
        df['volatility_20'] = close.pct_change().rolling(window=20).std() * np.sqrt(252)
        df['volatility_60'] = close.pct_change().rolling(window=60).std() * np.sqrt(252)
        
        # 收益率
        df['daily_return'] = close.pct_change()
        df['cumulative_return'] = (1 + df['daily_return']).cumprod() - 1
        df['log_return'] = np.log(close / close.shift(1))
        
        # 年化收益率
        df['annualized_return'] = df['daily_return'].rolling(window=252).mean() * 252
        
        # 价格动量
        df['momentum_20'] = close / close.shift(20) - 1
        df['momentum_60'] = close / close.shift(60) - 1
        
        # ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - close.shift())
        low_close = np.abs(df['low'] - close.shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_14'] = tr.rolling(window=14).mean()
        
        return df
    
    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        """计算 RSI"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(
        self,
        close: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算 MACD"""
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist
    
    def _calculate_bollinger_bands(
        self,
        close: pd.Series,
        window: int = 20,
        num_std: float = 2.0,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算布林带"""
        middle = close.rolling(window=window).mean()
        std = close.rolling(window=window).std()
        upper = middle + (std * num_std)
        lower = middle - (std * num_std)
        return upper, middle, lower
    
    def get_latest_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """获取最新技术信号"""
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        signals = {
            'trend': 'NEUTRAL',
            'rsi': latest.get('rsi_14', 50),
            'macd': 'NEUTRAL',
            'ma_signal': 'NEUTRAL',
            'strength': 0,
        }
        
        # 趋势判断
        if latest.get('ma_20_signal', False) and latest.get('ma_50_signal', False):
            signals['trend'] = 'BULLISH'
        elif not latest.get('ma_20_signal', True) and not latest.get('ma_50_signal', True):
            signals['trend'] = 'BEARISH'
        
        # RSI 信号
        rsi = signals['rsi']
        if rsi > 70:
            signals['rsi_signal'] = 'OVERBOUGHT'
        elif rsi < 30:
            signals['rsi_signal'] = 'OVERSOLD'
        else:
            signals['rsi_signal'] = 'NEUTRAL'
        
        # MACD 信号
        if latest.get('macd', 0) > latest.get('macd_signal', 0):
            signals['macd'] = 'BULLISH'
        elif latest.get('macd', 0) < latest.get('macd_signal', 0):
            signals['macd'] = 'BEARISH'
        
        # 综合评分 (-100 到 100)
        score = 0
        if latest.get('ma_20_signal', False):
            score += 20
        if latest.get('ma_50_signal', False):
            score += 20
        if latest.get('ma_200_signal', False):
            score += 20
        if 40 < rsi < 60:
            score += 10  # 健康区间
        if latest.get('macd', 0) > latest.get('macd_signal', 0):
            score += 15
        if latest.get('momentum_20', 0) > 0:
            score += 15
        
        signals['strength'] = score
        return signals
    
    def calculate_sharpe_ratio(
        self,
        returns: pd.Series,
        risk_free_rate: Optional[float] = None,
    ) -> float:
        """计算夏普比率"""
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate
        
        excess_returns = returns - risk_free_rate / 252
        if excess_returns.std() == 0:
            return 0.0
        
        sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
        return sharpe
    
    def calculate_max_drawdown(self, returns: pd.Series) -> Tuple[float, str, str]:
        """计算最大回撤"""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()
        
        # 找到最大回撤的起止日期
        peak_idx = drawdown[:drawdown.idxmin()].idxmax()
        trough_idx = drawdown.idxmin()
        
        return max_dd, str(peak_idx.date()), str(trough_idx.date())


class FundamentalAnalyzer:
    """基本面分析引擎"""
    
    def analyze(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """分析基本面数据"""
        analysis = {
            'valuation': self._analyze_valuation(info),
            'profitability': self._analyze_profitability(info),
            'growth': self._analyze_growth(info),
            'dividend': self._analyze_dividend(info),
            'risk': self._analyze_risk(info),
            'overall_score': 0,
        }
        
        # 综合评分
        scores = []
        if analysis['valuation']['score'] != 'N/A':
            scores.append(analysis['valuation']['score'])
        if analysis['profitability']['score'] != 'N/A':
            scores.append(analysis['profitability']['score'])
        if analysis['growth']['score'] != 'N/A':
            scores.append(analysis['growth']['score'])
        
        if scores:
            avg = sum(scores) / len(scores)
            if avg >= 80:
                analysis['overall_score'] = 'EXCELLENT'
            elif avg >= 60:
                analysis['overall_score'] = 'GOOD'
            elif avg >= 40:
                analysis['overall_score'] = 'FAIR'
            else:
                analysis['overall_score'] = 'WEAK'
        
        return analysis
    
    def _analyze_valuation(self, info: Dict) -> Dict[str, Any]:
        pe = info.get('trailingPE')
        fwd_pe = info.get('forwardPE')
        ptb = info.get('priceToBook')
        
        result = {'pe': pe, 'forward_pe': fwd_pe, 'price_to_book': ptb, 'verdict': 'N/A', 'score': 'N/A'}
        
        if pe:
            if pe < 15:
                result['verdict'] = '低估'
                result['score'] = 80
            elif pe < 25:
                result['verdict'] = '合理'
                result['score'] = 60
            elif pe < 40:
                result['verdict'] = '偏高'
                result['score'] = 40
            else:
                result['verdict'] = '高估'
                result['score'] = 20
        
        return result
    
    def _analyze_profitability(self, info: Dict) -> Dict[str, Any]:
        roe = info.get('returnOnEquity')
        gross = info.get('grossMargins')
        op = info.get('operatingMargins')
        profit = info.get('profitMargins')
        
        result = {'roe': roe, 'gross_margin': gross, 'operating_margin': op, 'profit_margin': profit, 'verdict': 'N/A', 'score': 'N/A'}
        
        scores = []
        if roe and roe > 0.15:
            scores.append(80)
        elif roe and roe > 0.10:
            scores.append(60)
        elif roe and roe > 0:
            scores.append(40)
        
        if profit and profit > 0.20:
            scores.append(80)
        elif profit and profit > 0.10:
            scores.append(60)
        
        if scores:
            result['score'] = sum(scores) / len(scores)
            if result['score'] >= 70:
                result['verdict'] = '优秀'
            elif result['score'] >= 50:
                result['verdict'] = '良好'
            else:
                result['verdict'] = '一般'
        
        return result
    
    def _analyze_growth(self, info: Dict) -> Dict[str, Any]:
        rev_growth = info.get('revenueGrowth')
        earn_growth = info.get('earningsGrowth')
        
        result = {'revenue_growth': rev_growth, 'earnings_growth': earn_growth, 'verdict': 'N/A', 'score': 'N/A'}
        
        if rev_growth and earn_growth:
            if rev_growth > 0.15 and earn_growth > 0.15:
                result['verdict'] = '高增长'
                result['score'] = 80
            elif rev_growth > 0.05:
                result['verdict'] = '稳定增长'
                result['score'] = 60
            elif rev_growth > 0:
                result['verdict'] = '低速增长'
                result['score'] = 40
            else:
                result['verdict'] = '负增长'
                result['score'] = 20
        
        return result
    
    def _analyze_dividend(self, info: Dict) -> Dict[str, Any]:
        yield_ = info.get('dividendYield', 0)
        result = {'yield': yield_, 'verdict': 'N/A', 'score': 'N/A'}
        
        if yield_:
            if yield_ > 0.03:
                result['verdict'] = '高息'
                result['score'] = 80
            elif yield_ > 0.015:
                result['verdict'] = '中等'
                result['score'] = 60
            elif yield_ > 0:
                result['verdict'] = '低息'
                result['score'] = 40
        
        return result
    
    def _analyze_risk(self, info: Dict) -> Dict[str, Any]:
        beta = info.get('beta', 1.0)
        result = {'beta': beta, 'verdict': 'N/A', 'score': 'N/A'}
        
        if beta:
            if beta < 0.8:
                result['verdict'] = '防御型'
                result['score'] = 80
            elif beta < 1.2:
                result['verdict'] = '平衡型'
                result['score'] = 60
            elif beta < 1.5:
                result['verdict'] = '进攻型'
                result['score'] = 40
            else:
                result['verdict'] = '高波动'
                result['score'] = 20
        
        return result


if __name__ == "__main__":
    # 测试技术分析
    from data_fetcher import DataFetcher
    
    fetcher = DataFetcher()
    df = fetcher.get_stock_data("AAPL", period="1y")
    
    analyzer = TechnicalAnalyzer()
    df = analyzer.add_all_indicators(df)
    signals = analyzer.get_latest_signals(df)
    
    print("=== 技术信号 ===")
    for k, v in signals.items():
        print(f"  {k}: {v}")
