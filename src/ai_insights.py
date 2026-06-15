# -*- coding: utf-8 -*-
"""
X-Gudao AI 洞察模块
使用本地 Ollama Qwen2 模型生成分析洞察
"""

import requests
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AIInsights:
    """AI 智能分析"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2:7b-64k",
        temperature: float = 0.1,
        max_tokens: int = 6000,
    ):
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_base = f"{base_url}/v1"
        self.chat_endpoint = f"{self.api_base}/chat/completions"
    
    def check_connection(self) -> bool:
        """检查 Ollama 连接"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama connection failed: {e}")
            return False
    
    def list_models(self) -> list:
        """列出可用模型"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m['name'] for m in data.get('models', [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
        return []
    
    def generate_insight(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        生成 AI 洞察
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
        
        Returns:
            AI 生成的文本
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        try:
            response = requests.post(
                self.chat_endpoint,
                json=payload,
                timeout=120,
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return f"Error: {response.status_code}"
        
        except requests.exceptions.Timeout:
            return "Error: Request timeout (模型响应时间过长)"
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return f"Error: {str(e)}"
    
    def analyze_comparison(
        self,
        comparison_results: Dict[str, Any],
    ) -> str:
        """AI 分析对比结果"""
        
        symbols = comparison_results['symbols']
        return_stats = comparison_results['return_stats']
        risk_stats = comparison_results['risk_stats']
        summary = comparison_results['summary']
        
        prompt = f"""请分析以下三只 ETF (VOO, QQQ, SPY) 的对比数据，并给出投资建议：

## 收益表现
{chr(10).join(f"- {s}: 年化收益率 {return_stats[s]['annualized_return']*100:.2f}%, 总收益 {return_stats[s]['total_return']*100:.2f}%" for s in symbols)}

## 风险指标
{chr(10).join(f"- {s}: 波动率 {risk_stats[s]['volatility']*100:.2f}%, 最大回撤 {risk_stats[s]['max_drawdown']*100:.2f}%, 夏普比率 {risk_stats[s]['sharpe_ratio']:.3f}" for s in symbols)}

## 综合排名
- 最佳收益: {summary['best_return']['symbol']}
- 最优夏普: {summary['best_sharpe']['symbol']}
- 最低波动: {summary['lowest_volatility']['symbol']}
- 最小回撤: {summary['smallest_drawdown']['symbol']}

请用中文回答，包含：
1. 三只 ETF 的主要区别
2. 各自的优势和风险
3. 适合什么样的投资者
4. 如果定投 5 年，你会选择哪一只或如何组合（VOO/QQQ/SPY 任意组合，权重自定）
"""
        
        system_prompt = """你是一位专业的金融分析师，擅长 ETF 和指数基金分析。请用专业但易懂的语言回答问题。
重点关注：风险调整后收益、长期复利效应、费率影响。
如果数据不足，请明确指出。"""
        
        return self.generate_insight(prompt, system_prompt)
    
    def analyze_technical(
        self,
        symbol: str,
        df,
        signals: Dict[str, Any],
    ) -> str:
        """AI 技术分析"""
        
        latest = df.iloc[-1]
        prompt = f"""请对 {symbol} 进行技术分析：

## 当前价格
最新收盘价: ${latest['close']:.2f}

## 技术信号
- 趋势: {signals.get('trend', 'N/A')}
- RSI(14): {signals.get('rsi', 50):.2f}
- MACD: {signals.get('macd', 'N/A')}
- 综合评分: {signals.get('strength', 0)}/100

## 移动平均线
- MA20: ${latest.get('ma_20', 0):.2f} ({'上方' if latest['close'] > latest.get('ma_20', 0) else '下方'})
- MA50: ${latest.get('ma_50', 0):.2f} ({'上方' if latest['close'] > latest.get('ma_50', 0) else '下方'})
- MA200: ${latest.get('ma_200', 0):.2f} ({'上方' if latest['close'] > latest.get('ma_200', 0) else '下方'})

## 波动率
- 20日波动率: {latest.get('volatility_20', 0)*100:.2f}%

请用中文分析：
1. 当前技术形态
2. 短期、中期、长期趋势判断
3. 关键支撑位和压力位
4. 风险提示
"""
        
        system_prompt = """你是一位技术分析专家，擅长蜡烛图形态、技术指标分析。请给出客观的技术分析，避免过度乐观或悲观。"""
        
        return self.generate_insight(prompt, system_prompt)


if __name__ == "__main__":
    # 测试
    ai = AIInsights()
    
    print("=== Ollama 连接状态 ===")
    if ai.check_connection():
        print("✅ Ollama 已连接")
        print(f"可用模型: {ai.list_models()}")
    else:
        print("❌ 无法连接 Ollama")
