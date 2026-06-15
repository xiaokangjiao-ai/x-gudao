# -*- coding: utf-8 -*-
"""
X-Gudao 风控拦截器
在数据分析和 AI 输出之间添加安全层
"""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RiskControl:
    """风控引擎"""
    
    # 禁止执行的操作关键词
    BLOCKED_ACTIONS = [
        'execute_order', 'place_order', 'buy_stock', 'sell_stock',
        'transfer_fund', 'withdraw', 'deposit', 'trade', '交易',
        '下单', '买入', '卖出', '转账',
    ]
    
    # 敏感信息正则
    SENSITIVE_PATTERNS = [
        r'password\s*[:=]\s*\S+',
        r'secret\s*[:=]\s*\S+',
        r'api_key\s*[:=]\s*\S+',
        r'token\s*[:=]\s*\S+',
        r'private_key\s*[:=]\s*\S+',
    ]
    
    # 强制免责声明
    DISCLAIMER = """
> ⚠️ **免责声明**
> 本报告由 X-Gudao 金融分析系统生成，仅供参考，不构成任何投资建议。
> 过往表现不代表未来收益。市场有风险，投资需谨慎。
> 数据来源：Yahoo Finance | AI 洞察：Ollama Qwen2
"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.request_count = 0
        self.request_timestamps: List[datetime] = []
        self.max_requests_per_minute = 30
    
    def check_action(self, action: str) -> Dict[str, Any]:
        """检查操作是否允许"""
        if not self.enabled:
            return {'allowed': True, 'reason': '风控已禁用'}
        
        action_lower = action.lower().strip()
        
        # 检查是否为禁止操作
        for blocked in self.BLOCKED_ACTIONS:
            if blocked in action_lower:
                return {
                    'allowed': False,
                    'reason': f'禁止操作: {action}',
                    'risk_level': 'HIGH',
                }
        
        return {'allowed': True, 'reason': 'OK', 'risk_level': 'LOW'}
    
    def sanitize_output(self, text: str) -> str:
        """清理输出中的敏感信息"""
        for pattern in self.SENSITIVE_PATTERNS:
            text = re.sub(pattern, '[REDACTED]', text, flags=re.IGNORECASE)
        return text
    
    def append_disclaimer(self, report: str) -> str:
        """追加免责声明"""
        if not report.endswith(self.DISCLAIMER.strip()[:10]):
            report += self.DISCLAIMER
        return report
    
    def check_rate_limit(self) -> Dict[str, Any]:
        """检查 API 限流"""
        now = datetime.now()
        
        # 清理 1 分钟前的记录
        self.request_timestamps = [
            t for t in self.request_timestamps 
            if (now - t).total_seconds() < 60
        ]
        
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            return {
                'allowed': False,
                'reason': 'API 限流：请求过于频繁，请稍后重试',
                'retry_after': 60,
            }
        
        self.request_timestamps.append(now)
        self.request_count += 1
        
        return {'allowed': True, 'request_count': self.request_count}
    
    def validate_analysis_input(
        self,
        symbols: List[str],
        period: str,
    ) -> Dict[str, Any]:
        """验证分析输入参数"""
        errors = []
        warnings = []
        
        # 验证股票代码格式
        valid_period = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'max']
        if period not in valid_period:
            warnings.append(f"非常规周期: {period}，可能数据不足")
        
        # 资产数量限制
        if len(symbols) > 20:
            errors.append("单次对比资产数量不能超过 20")
        
        # 特殊代码警告
        crypto_symbols = ['BTC-USD', 'ETH-USD', 'DOGE-USD']
        for sym in symbols:
            if sym in crypto_symbols:
                warnings.append(f"{sym} 为加密货币，波动性极高")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
        }


# 全局风控实例
_risk_control = RiskControl()


def get_risk_control() -> RiskControl:
    """获取全局风控实例"""
    return _risk_control


if __name__ == "__main__":
    rc = RiskControl()
    
    print("=== 风控测试 ===")
    
    # 测试操作检查
    result = rc.check_action("analyze VOO QQQ SPY")
    print(f"分析操作: {result}")
    
    result = rc.check_action("buy AAPL stock")
    print(f"买入操作: {result}")
    
    # 测试免责声明
    report = "## 分析结论\n\n推荐持有 VOO"
    report = rc.append_disclaimer(report)
    print(f"\n{report}")
