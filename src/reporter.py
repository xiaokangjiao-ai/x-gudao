# -*- coding: utf-8 -*-
"""
X-Gudao 报告生成器
生成 Markdown 和 HTML 分析报告
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd
from jinja2 import Template


class ReportGenerator:
    """分析报告生成器"""
    
    def __init__(self, output_dir: str = "./output/reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_comparison_report(
        self,
        comparison_results: Dict[str, Any],
        symbol_info: Optional[Dict[str, Dict]] = None,
    ) -> str:
        """
        生成多资产对比报告
        
        Args:
            comparison_results: Comparator.compare_assets() 返回的结果
            symbol_info: 各资产的基本信息
        
        Returns:
            Markdown 格式报告
        """
        symbols = comparison_results['symbols']
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 构建 Markdown
        md = f"""# 📊 X-Gudao 多资产对比分析报告

**生成时间**: {timestamp}  
**分析资产**: {', '.join(symbols)}  
**数据周期**: 近 {comparison_results['period_days']} 交易日 (约 {comparison_results['period_days']//252} 年)

---

## 📈 一、收益表现对比

| 指标 | {' | '.join(symbols)} |
|------| {' | '.join(['---' for _ in symbols])} |
"""
        
        return_stats = comparison_results['return_stats']
        for metric in ['total_return', 'annualized_return', 'mean_daily_return']:
            label = {
                'total_return': '总收益率',
                'annualized_return': '年化收益率',
                'mean_daily_return': '日均收益率',
            }[metric]
            values = [return_stats[s].get(metric, 0) for s in symbols]
            md += f"| {label} | {' | '.join([f'{v*100:.2f}%' if abs(v) < 10 else f'{v*100:.4f}%' for v in values])} |\n"
        
        md += f"""
### 最佳收益: **{comparison_results['summary']['best_return']['symbol']}** ({comparison_results['summary']['best_return']['value']*100:.2f}%)

---

## 📉 二、风险指标对比

| 指标 | {' | '.join(symbols)} |
|------| {' | '.join(['---' for _ in symbols])} |
"""
        
        risk_stats = comparison_results['risk_stats']
        for metric in ['volatility', 'max_drawdown', 'sharpe_ratio', 'sortino_ratio']:
            label = {
                'volatility': '年化波动率',
                'max_drawdown': '最大回撤',
                'sharpe_ratio': '夏普比率',
                'sortino_ratio': '索提诺比率',
            }[metric]
            values = [risk_stats[s].get(metric, 0) for s in symbols]
            if metric == 'max_drawdown':
                md += f"| {label} | {' | '.join([f'{v*100:.2f}%' for v in values])} |\n"
            else:
                md += f"| {label} | {' | '.join([f'{v:.3f}' for v in values])} |\n"
        
        md += f"""
### 最低波动: **{comparison_results['summary']['lowest_volatility']['symbol']}** ({comparison_results['summary']['lowest_volatility']['value']*100:.2f}%)
### 最小回撤: **{comparison_results['summary']['smallest_drawdown']['symbol']}** ({comparison_results['summary']['smallest_drawdown']['value']*100:.2f}%)

---

## 🔗 三、相关性分析

### 相关系数矩阵

|  | {' | '.join(symbols)} |
|---| {' | '.join(['---' for _ in symbols])} |
"""
        
        corr = comparison_results['correlation_matrix']
        for s1 in symbols:
            row = [f"{corr.loc[s1, s2]:.3f}" for s2 in symbols]
            md += f"| {s1} | {' | '.join(row)} |\n"
        
        low_corr = comparison_results['summary']['lowest_correlation_pair']
        md += f"""
### 最低相关配对: **{low_corr['symbols'][0]} / {low_corr['symbols'][1]}** (r = {low_corr['corr']:.3f})

> 💡 **组合建议**: 相关性低的资产组合可有效分散风险

---

## 🏆 四、综合排名

| 资产 | 收益排名 | 夏普排名 | 回撤排名 | 平均排名 |
|------|----------|----------|----------|----------|
"""
        
        rankings = comparison_results['rankings']
        for sym in symbols:
            r = rankings[sym]
            md += f"| {sym} | #{r['return_rank']} | #{r['sharpe_rank']} | #{r['drawdown_rank']} | {r['avg_rank']:.1f} |\n"
        
        winner = comparison_results['summary']['winner']
        md += f"""
### 🥇 综合冠军: **{winner}**

---

## 📋 五、综合摘要

| 分析维度 | 推荐资产 | 原因 |
|----------|----------|------|
| 最高收益 | {comparison_results['summary']['best_return']['symbol']} | 年化 {comparison_results['summary']['best_return']['value']*100:.2f}% |
| 最优风险收益比 | {comparison_results['summary']['best_sharpe']['symbol']} | 夏普比率 {comparison_results['summary']['best_sharpe']['value']:.3f} |
| 最低风险 | {comparison_results['summary']['lowest_volatility']['symbol']} | 波动率仅 {comparison_results['summary']['lowest_volatility']['value']*100:.2f}% |
| 回撤控制 | {comparison_results['summary']['smallest_drawdown']['symbol']} | 最大回撤 {comparison_results['summary']['smallest_drawdown']['value']*100:.2f}% |

---

## 💡 六、投资建议

"""
        
        # 根据分析结果生成建议
        best_sharpe_sym = comparison_results['summary']['best_sharpe']['symbol']
        best_return_sym = comparison_results['summary']['best_return']['symbol']
        lowest_vol_sym = comparison_results['summary']['lowest_volatility']['symbol']
        
        md += f"""1. **追求稳健收益**: 推荐 **{best_sharpe_sym}**，夏普比率最优
2. **追求高增长**: 考虑 **{best_return_sym}**，历史收益最高
3. **保守型投资者**: 优先 **{lowest_vol_sym}**，波动最小

### VOO / QQQ / SPY 对比说明

| 指数 | 特点 | 适合投资者 |
|------|------|-----------|
| **VOO** | 标普500低成本ETF，费率低 | 长期定投、被动投资 |
| **QQQ** | 纳斯达克100，科技权重高 | 成长型投资者 |
| **SPY** | 标普500最早的ETF，流动性好 | 需要期权等高级策略者 |
"""
        
        md += f"""
---

> ⚠️ **免责声明**: 本报告仅供参考，不构成投资建议。过往表现不代表未来收益。

*由 X-Gudao 金融分析系统生成 | 对标 Macrotrends*
"""
        
        return md
    
    def save_report(
        self,
        content: str,
        filename: str,
        formats: list = ['md', 'html'],
    ) -> Dict[str, str]:
        """保存报告到文件"""
        paths = {}
        
        if 'md' in formats:
            md_path = os.path.join(self.output_dir, f"{filename}.md")
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(content)
            paths['md'] = md_path
        
        if 'html' in formats:
            html_content = self._markdown_to_html(content)
            html_path = os.path.join(self.output_dir, f"{filename}.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            paths['html'] = html_path
        
        return paths
    
    def _markdown_to_html(self, md_content: str) -> str:
        """简单的 Markdown 转 HTML"""
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>X-Gudao 金融分析报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
               max-width: 1000px; margin: 0 auto; padding: 20px; line-height: 1.6;
               background: #f5f5f5; }}
        .container {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #1a73e8; border-bottom: 3px solid #1a73e8; padding-bottom: 10px; }}
        h2 {{ color: #333; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: center; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        tr:nth-child(even) {{ background: #fafafa; }}
        .highlight {{ background: #e8f0fe; font-weight: 600; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
        .disclaimer {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        {self._simple_md_to_html(md_content)}
    </div>
</body>
</html>"""
        return html
    
    def _simple_md_to_html(self, md: str) -> str:
        """简化的 Markdown 解析"""
        import re
        
        # 标题
        md = re.sub(r'^### (.+)$', r'<h3>\1</h3>', md, flags=re.MULTILINE)
        md = re.sub(r'^## (.+)$', r'<h2>\1</h2>', md, flags=re.MULTILINE)
        md = re.sub(r'^# (.+)$', r'<h1>\1</h1>', md, flags=re.MULTILINE)
        
        # 表格
        lines = md.split('\n')
        in_table = False
        new_lines = []
        for line in lines:
            if '|' in line and line.strip().startswith('|'):
                if not in_table:
                    new_lines.append('<table>')
                    in_table = True
                # 解析表格行
                cells = [c.strip() for c in line.split('|')[1:-1]]
                tag = 'th' if any('---' in c for c in cells) else 'td'
                if tag == 'td':
                    new_lines.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
                elif '---' not in line:
                    new_lines.append('<tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr>')
            else:
                if in_table:
                    new_lines.append('</table>')
                    in_table = False
                new_lines.append(line)
        if in_table:
            new_lines.append('</table>')
        md = '\n'.join(new_lines)
        
        # 列表
        md = re.sub(r'^- (.+)$', r'<li>\1</li>', md, flags=re.MULTILINE)
        md = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', md)
        
        # 引用
        md = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', md, flags=re.MULTILINE)
        
        # 换行
        md = md.replace('\n\n', '</p><p>')
        
        return f'<p>{md}</p>'


if __name__ == "__main__":
    from data_fetcher import DataFetcher
    from comparator import Comparator
    
    fetcher = DataFetcher()
    comparator = Comparator()
    
    data = fetcher.get_multiple_stocks(['VOO', 'QQQ', 'SPY'], period='3y')
    results = comparator.compare_assets(data)
    
    reporter = ReportGenerator()
    report = reporter.generate_comparison_report(results)
    
    paths = reporter.save_report(report, "VOO_QQQ_SPY_comparison")
    print(f"Report saved to: {paths}")
