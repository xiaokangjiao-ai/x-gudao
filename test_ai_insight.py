# -*- coding: utf-8 -*-
"""
测试 Ollama AI 金融分析能力
基于知识库而非实时数据
"""

import requests
import json
import sys

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2:7b-64k"

def get_ai_insight(prompt, system_prompt=None):
    """调用本地 Ollama 模型"""
    
    full_prompt = f"""{system_prompt or ''}

用户问题：{prompt}

请用中文回答，数据精确到小数点后2位，必须包含免责声明。"""
    
    payload = {
        "model": MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.3,
            "num_predict": 4000
        }
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result.get('response', '无响应')
    except Exception as e:
        return f"错误: {e}"


SYSTEM_PROMPT = """你是一位资深金融数据分析师，精通美股ETF分析。

## 分析原则
1. 数据驱动：所有结论基于历史数据和公认指标
2. 风险优先：先谈风险，再谈收益
3. 长期视角：强调复利效应
4. 费用意识：关注费率对长期收益的侵蚀

## 必须包含的免责声明
> ⚠️ 本分析基于历史数据和公开信息，仅供参考，不构成投资建议。
> 过往表现不代表未来收益。市场有风险，投资需谨慎。

## 回答规范
- 用中文回答，专业术语保留英文
- 数据精确到小数点后2位
- 百分比统一用%表示
- 价格统一用$表示
"""

# 测试问题：VOO vs QQQ vs SPY 对比分析
PROMPT = """请对以下三只美股ETF进行深度对比分析：

## 分析标的
1. VOO (Vanguard S&P 500 ETF) - 费率0.03%
2. QQQ (Invesco QQQ Trust) - 费率0.20%，跟踪纳斯达克100
3. SPY (SPDR S&P 500 ETF) - 费率0.09%，最早的标普500ETF

## 分析要求

### 1. 基础信息对比
- 成立时间、管理资产规模(AUM)
- 费率结构对比
- 跟踪指数差异

### 2. 历史表现分析（基于公开历史数据）
- 近5年/10年年化收益率
- 波动率对比
- 最大回撤

### 3. 风险收益特征
- 夏普比率估算
- 贝塔系数
- 行业集中度风险（QQQ科技权重过高）

### 4. 适用场景建议
- 保守型投资者适合哪个？
- 成长型投资者适合哪个？
- 定投策略建议？

### 5. 综合评分排名
请给出1-10分的综合评分并说明理由。

请用表格展示关键对比数据。
"""

if __name__ == "__main__":
    import sys
    # 设置 UTF-8 编码
    sys.stdout.reconfigure(encoding='utf-8')
    
    print("=" * 60)
    print("X-Gudao AI 金融分析测试")
    print("模型:", MODEL)
    print("=" * 60)
    print()
    
    print("正在调用 Ollama...")
    print("-" * 60)
    
    result = get_ai_insight(PROMPT, SYSTEM_PROMPT)
    
    print(result)
    print()
    print("=" * 60)
    print("分析完成!")
