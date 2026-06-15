# -*- coding: utf-8 -*-
"""
X-Gudao 多资产对比分析模块
对标 Macrotrends 的多指数/ETF 对比功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from scipy import stats


class Comparator:
    """多资产对比分析"""
    
    def __init__(self, risk_free_rate: float = 0.04):
        self.risk_free_rate = risk_free_rate
    
    def compare_assets(
        self,
        data_dict: Dict[str, pd.DataFrame],
        period_days: int = 252,
    ) -> Dict[str, Any]:
        """
        综合对比多只资产
        
        Args:
            data_dict: {symbol: DataFrame} 数据字典
            period_days: 用于计算指标的周期（默认1年=252交易日）
        
        Returns:
            对比分析报告字典
        """
        results = {
            'symbols': list(data_dict.keys()),
            'period_days': period_days,
            'price_stats': self._calculate_price_stats(data_dict, period_days),
            'return_stats': self._calculate_return_stats(data_dict, period_days),
            'risk_stats': self._calculate_risk_stats(data_dict, period_days),
            'dividend_stats': self._calculate_dividend_stats(data_dict),
            'correlation_matrix': self._calculate_correlations(data_dict),
            'rankings': self._rank_assets(data_dict),
            'summary': {},
        }
        
        # 生成摘要
        results['summary'] = self._generate_summary(results)
        
        return results
    
    def _calculate_price_stats(
        self,
        data_dict: Dict[str, pd.DataFrame],
        period_days: int,
    ) -> Dict[str, Dict]:
        """价格统计"""
        stats_dict = {}
        
        for sym, df in data_dict.items():
            latest_price = df['close'].iloc[-1]
            prev_price = df['close'].iloc[-period_days] if len(df) >= period_days else df['close'].iloc[0]
            high_52w = df['high'].rolling(window=252).max().iloc[-1]
            low_52w = df['low'].rolling(window=252).min().iloc[-1]
            
            # 距 52 周高低点的距离
            dist_from_high = (latest_price - high_52w) / high_52w * 100
            dist_from_low = (latest_price - low_52w) / low_52w * 100
            
            stats_dict[sym] = {
                'current_price': latest_price,
                'price_1y_ago': prev_price,
                'high_52w': high_52w,
                'low_52w': low_52w,
                'dist_from_high_pct': dist_from_high,
                'dist_from_low_pct': dist_from_low,
                'currency': 'USD',
            }
        
        return stats_dict
    
    def _calculate_return_stats(
        self,
        data_dict: Dict[str, pd.DataFrame],
        period_days: int,
    ) -> Dict[str, Dict]:
        """收益率统计"""
        stats_dict = {}
        
        for sym, df in data_dict.items():
            returns = df['daily_return'].dropna()
            
            # 不同周期的收益率
            total_return = (df['close'].iloc[-1] / df['close'].iloc[0]) - 1
            
            if len(df) >= period_days:
                period_return = (df['close'].iloc[-1] / df['close'].iloc[-period_days]) - 1
            else:
                period_return = total_return
            
            # 年化收益率
            years = len(df) / 252
            annualized = ((1 + total_return) ** (1 / years) - 1) if years > 0 else 0
            
            # 月收益率
            monthly = df.set_index('date')['close'].resample('M').last().pct_change().dropna()
            
            stats_dict[sym] = {
                'total_return': total_return,
                'return_1y': period_return if period_days == 252 else None,
                'annualized_return': annualized,
                'mean_daily_return': returns.mean(),
                'median_monthly_return': monthly.median() if len(monthly) > 0 else 0,
                'best_month': monthly.max() if len(monthly) > 0 else 0,
                'worst_month': monthly.min() if len(monthly) > 0 else 0,
            }
        
        return stats_dict
    
    def _calculate_risk_stats(
        self,
        data_dict: Dict[str, pd.DataFrame],
        period_days: int,
    ) -> Dict[str, Dict]:
        """风险统计"""
        stats_dict = {}
        
        for sym, df in data_dict.items():
            returns = df['daily_return'].dropna()
            
            # 年化波动率
            volatility = returns.std() * np.sqrt(252)
            
            # 下行波动率（只考虑负收益）
            negative_returns = returns[returns < 0]
            downside_vol = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0
            
            # 最大回撤
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min()
            
            # VaR (95%)
            var_95 = returns.quantile(0.05)
            
            # CVaR / Expected Shortfall
            cvar_95 = returns[returns <= var_95].mean()
            
            # 夏普比率
            excess_return = returns.mean() - self.risk_free_rate / 252
            sharpe = (excess_return / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
            
            # 索提诺比率（只用下行波动率）
            sortino = (excess_return / downside_vol * np.sqrt(252)) if downside_vol > 0 else 0
            
            # Calmar 比率
            calmar = annualized / abs(max_drawdown) if max_drawdown != 0 else 0
            
            stats_dict[sym] = {
                'volatility': volatility,
                'downside_volatility': downside_vol,
                'max_drawdown': max_drawdown,
                'var_95': var_95,
                'cvar_95': cvar_95,
                'sharpe_ratio': sharpe,
                'sortino_ratio': sortino,
                'calmar_ratio': calmar,
                'beta': 1.0,  # 相对于组合的 beta，后面会更新
            }
        
        return stats_dict
    
    def _calculate_dividend_stats(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
        """股息统计（简化版，假设固定股息率）"""
        # 实际应该从 info 获取
        stats_dict = {}
        for sym in data_dict.keys():
            stats_dict[sym] = {
                'dividend_yield': 0.0,
                'annual_dividend': 0.0,
            }
        return stats_dict
    
    def _calculate_correlations(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """计算相关系数矩阵"""
        symbols = list(data_dict.keys())
        returns_dict = {}
        
        for sym, df in data_dict.items():
            returns_dict[sym] = df['daily_return'].dropna()
        
        # 找到共同的时间范围
        min_len = min(len(r) for r in returns_dict.values())
        for sym in returns_dict:
            returns_dict[sym] = returns_dict[sym].iloc[-min_len:]
        
        corr_df = pd.DataFrame(returns_dict).corr()
        return corr_df
    
    def _rank_assets(
        self,
        data_dict: Dict[str, pd.DataFrame],
    ) -> Dict[str, int]:
        """综合排名"""
        return_stats = self._calculate_return_stats(data_dict, 252)
        risk_stats = self._calculate_risk_stats(data_dict, 252)
        
        rankings = {}
        
        # 按收益率排名
        returns_sorted = sorted(
            return_stats.keys(),
            key=lambda x: return_stats[x]['annualized_return'],
            reverse=True
        )
        
        # 按夏普比率排名
        sharpe_sorted = sorted(
            risk_stats.keys(),
            key=lambda x: risk_stats[x]['sharpe_ratio'],
            reverse=True
        )
        
        # 按最大回撤排名（回撤越小越好）
        dd_sorted = sorted(
            risk_stats.keys(),
            key=lambda x: risk_stats[x]['max_drawdown'],
            reverse=True
        )
        
        for sym in data_dict.keys():
            rank_ret = returns_sorted.index(sym) + 1
            rank_sharpe = sharpe_sorted.index(sym) + 1
            rank_dd = dd_sorted.index(sym) + 1
            rankings[sym] = {
                'return_rank': rank_ret,
                'sharpe_rank': rank_sharpe,
                'drawdown_rank': rank_dd,
                'avg_rank': (rank_ret + rank_sharpe + rank_dd) / 3,
            }
        
        return rankings
    
    def _generate_summary(self, results: Dict) -> Dict[str, Any]:
        """生成对比摘要"""
        symbols = results['symbols']
        
        # 找出各项最优
        best_return = max(symbols, key=lambda s: results['return_stats'][s]['annualized_return'])
        best_sharpe = max(symbols, key=lambda s: results['risk_stats'][s]['sharpe_ratio'])
        lowest_vol = min(symbols, key=lambda s: results['risk_stats'][s]['volatility'])
        smallest_dd = min(symbols, key=lambda s: results['risk_stats'][s]['max_drawdown'])
        
        # 找出相关性最低的配对
        corr = results['correlation_matrix']
        pairs = []
        for i, s1 in enumerate(symbols):
            for j, s2 in enumerate(symbols):
                if i < j:
                    pairs.append((s1, s2, corr.loc[s1, s2]))
        lowest_corr_pair = min(pairs, key=lambda x: x[2]) if pairs else (None, None, 0)
        
        return {
            'best_return': {'symbol': best_return, 'value': results['return_stats'][best_return]['annualized_return']},
            'best_sharpe': {'symbol': best_sharpe, 'value': results['risk_stats'][best_sharpe]['sharpe_ratio']},
            'lowest_volatility': {'symbol': lowest_vol, 'value': results['risk_stats'][lowest_vol]['volatility']},
            'smallest_drawdown': {'symbol': smallest_dd, 'value': results['risk_stats'][smallest_dd]['max_drawdown']},
            'lowest_correlation_pair': {'symbols': [lowest_corr_pair[0], lowest_corr_pair[1]], 'corr': lowest_corr_pair[2]},
            'winner': max(symbols, key=lambda s: results['rankings'][s]['avg_rank']),
        }


def format_pct(value: float) -> str:
    """格式化百分比"""
    return f"{value * 100:.2f}%"


def format_number(value: float, decimals: int = 2) -> str:
    """格式化数字"""
    return f"{value:,.{decimals}f}"


if __name__ == "__main__":
    from data_fetcher import DataFetcher
    
    fetcher = DataFetcher()
    data = fetcher.get_multiple_stocks(['VOO', 'QQQ', 'SPY'], period='3y')
    
    comparator = Comparator()
    report = comparator.compare_assets(data)
    
    print("=== 对比分析摘要 ===")
    for k, v in report['summary'].items():
        print(f"  {k}: {v}")
