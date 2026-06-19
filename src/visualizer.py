# -*- coding: utf-8 -*-
"""
X-Gudao 可视化模块
使用 Plotly 生成交互式图表
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
import os


class ChartGenerator:
    """交互式图表生成器"""
    
    def __init__(self, output_dir: str = "./output/charts"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def plot_stock_with_indicators(
        self,
        df: pd.DataFrame,
        symbol: str,
        show_ma: bool = True,
        show_rsi: bool = True,
        show_macd: bool = True,
        show_bb: bool = True,
        save_html: bool = True,
        save_png: bool = False,
    ) -> go.Figure:
        """
        绘制股票技术分析图（多面板）
        
        Args:
            df: 包含 OHLCV 和技术指标的数据
            symbol: 股票代码
            show_ma/rsi/macd/bb: 是否显示各指标
            save_html/png: 是否保存
        """
        n_subplots = 2  # 价格面板 + 成交量
        names = ["Price & Volume"]
        
        if show_rsi:
            n_subplots += 1
            names.append("RSI")
        if show_macd:
            n_subplots += 1
            names.append("MACD")
        
        fig = make_subplots(
            rows=n_subplots, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=names,
            row_heights=[0.5, 0.2] + [0.15] * (n_subplots - 2),
        )
        
        row = 1
        
        # === 1. 价格面板 + 移动平均线 + 布林带 ===
        fig.add_trace(
            go.Candlestick(
                x=df['date'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name=symbol,
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350',
            ),
            row=row, col=1
        )
        
        # 成交量（彩色）
        colors = ['#26a69a' if df['close'].iloc[i] >= df['open'].iloc[i] else '#ef5350' for i in range(len(df))]
        fig.add_trace(
            go.Bar(x=df['date'], y=df['volume'], name='Volume', marker_color=colors, opacity=0.5),
            row=row, col=1
        )
        
        if show_ma:
            for window in [20, 50, 200]:
                if f'ma_{window}' in df.columns:
                    fig.add_trace(
                        go.Scatter(x=df['date'], y=df[f'ma_{window}'], name=f'MA{window}',
                                   line=dict(width=1.5), opacity=0.8),
                        row=row, col=1
                    )
        
        if show_bb and 'bb_upper' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['date'], y=df['bb_upper'], name='BB Upper',
                           line=dict(width=1, dash='dash'), line_color='gray', opacity=0.5),
                row=row, col=1
            )
            fig.add_trace(
                go.Scatter(x=df['date'], y=df['bb_middle'], name='BB Middle',
                           line=dict(width=1, dash='dot'), line_color='gray', opacity=0.5),
                row=row, col=1
            )
            fig.add_trace(
                go.Scatter(x=df['date'], y=df['bb_lower'], name='BB Lower',
                           line=dict(width=1, dash='dash'), line_color='gray', opacity=0.5,
                           fill='tonexty', fillcolor='rgba(200,200,200,0.1)'),
                row=row, col=1
            )
        
        row += 1
        
        # === 2. RSI 面板 ===
        if show_rsi and 'rsi_14' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['date'], y=df['rsi_14'], name='RSI(14)',
                           line=dict(color='purple', width=1.5)),
                row=row, col=1
            )
            # 超买超卖线
            fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=row, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=row, col=1)
            fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.3, row=row, col=1)
            row += 1
        
        # === 3. MACD 面板 ===
        if show_macd and 'macd' in df.columns:
            colors_macd = ['#26a69a' if v >= 0 else '#ef5350' for v in df['macd_hist'].fillna(0)]
            fig.add_trace(
                go.Bar(x=df['date'], y=df['macd_hist'], name='MACD Hist',
                       marker_color=colors_macd, opacity=0.7),
                row=row, col=1
            )
            fig.add_trace(
                go.Scatter(x=df['date'], y=df['macd'], name='MACD',
                           line=dict(color='blue', width=1.5)),
                row=row, col=1
            )
            fig.add_trace(
                go.Scatter(x=df['date'], y=df['macd_signal'], name='Signal',
                           line=dict(color='orange', width=1.5)),
                row=row, col=1
            )
        
        # 布局设置
        fig.update_layout(
            title=f'{symbol} - 技术分析图表',
            xaxis_rangeslider_visible=False,
            template='plotly_white',
            height=800,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
        )
        
        fig.update_xaxes(title_text="Date", row=n_subplots, col=1)
        
        if save_html:
            filepath = os.path.join(self.output_dir, f"{symbol}_technical.html")
            fig.write_html(filepath)
        
        if save_png:
            filepath_png = os.path.join(self.output_dir, f"{symbol}_technical.png")
            fig.write_image(filepath_png, width=1200, height=800, scale=2)
        
        return fig
    
    def plot_comparison(
        self,
        data_dict: Dict[str, pd.DataFrame],
        normalize: bool = True,
        save_html: bool = True,
    ) -> go.Figure:
        """
        多资产收益对比图
        """
        fig = go.Figure()
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        
        for i, (symbol, df) in enumerate(data_dict.items()):
            if normalize:
                # 归一化到起始值 = 100
                normalized = df['close'] / df['close'].iloc[0] * 100
                label = f'{symbol} (起始=100)'
            else:
                normalized = df['close']
                label = symbol
            
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=normalized,
                mode='lines',
                name=label,
                line=dict(width=2, color=colors[i % len(colors)]),
            ))
        
        fig.update_layout(
            title='多资产收益对比' if normalize else '多资产价格对比',
            xaxis_title='Date',
            yaxis_title='相对收益 (起始=100)' if normalize else '价格',
            template='plotly_white',
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        
        if save_html:
            filepath = os.path.join(self.output_dir, "comparison.html")
            fig.write_html(filepath)
        
        return fig
    
    def plot_correlation_heatmap(
        self,
        returns_dict: Dict[str, pd.Series],
        save_html: bool = True,
    ) -> go.Figure:
        """相关性热力图"""
        symbols = list(returns_dict.keys())
        n = len(symbols)
        
        # 构建相关系数矩阵
        corr_matrix = np.zeros((n, n))
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                corr_matrix[i, j] = returns_dict[sym1].corr(returns_dict[sym2])
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix,
            x=symbols,
            y=symbols,
            colorscale='RdBu',
            zmid=0,
            text=np.round(corr_matrix, 2),
            texttemplate='%{text}',
            textfont={"size": 12},
            hovertemplate='%{x} vs %{y}<br>相关性: %{z:.3f}<extra></extra>',
        ))
        
        fig.update_layout(
            title='资产相关性矩阵',
            template='plotly_white',
        )
        
        if save_html:
            filepath = os.path.join(self.output_dir, "correlation.html")
            fig.write_html(filepath)
        
        return fig
    
    def plot_risk_return(
        self,
        stats_dict: Dict[str, Dict],
        save_html: bool = True,
    ) -> go.Figure:
        """风险收益散点图"""
        symbols = list(stats_dict.keys())
        returns = [stats_dict[s]['annualized_return'] * 100 for s in symbols]
        volatilities = [stats_dict[s]['volatility'] * 100 for s in symbols]
        
        fig = go.Figure()
        
        for i, sym in enumerate(symbols):
            fig.add_trace(go.Scatter(
                x=[volatilities[i]],
                y=[returns[i]],
                mode='markers+text',
                marker=dict(size=20, color='steelblue'),
                text=[sym],
                textposition="top center",
                name=sym,
            ))
        
        fig.update_layout(
            title='风险-收益分布',
            xaxis_title='波动率 (年化, %)',
            yaxis_title='收益率 (年化, %)',
            template='plotly_white',
        )
        
        # 添加对角参考线（夏普比率 = 1）
        max_vol = max(volatilities) * 1.1
        fig.add_trace(go.Scatter(
            x=[0, max_vol],
            y=[0, max_vol],
            mode='lines',
            line=dict(dash='dash', color='gray'),
            name='Sharpe=1',
            opacity=0.5,
        ))
        
        if save_html:
            filepath = os.path.join(self.output_dir, "risk_return.html")
            fig.write_html(filepath)
        
        return fig


if __name__ == "__main__":
    from data_fetcher import DataFetcher
    from analyzer import TechnicalAnalyzer
    
    fetcher = DataFetcher()
    analyzer = TechnicalAnalyzer()
    chart_gen = ChartGenerator()
    
    symbols = ['VOO', 'QQQ', 'SPY']
    data = fetcher.get_multiple_stocks(symbols, period='2y')
    
    for sym, df in data.items():
        df = analyzer.add_all_indicators(df)
        chart_gen.plot_stock_with_indicators(df, sym)
    
    # 对比图
    chart_gen.plot_comparison(data)
    
    print("Charts generated!")
