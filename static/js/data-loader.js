/**
 * 数据加载模块 - 从本地 JSON 文件加载数据
 * 替代原来的 API 调用
 */

const DATA_BASE_PATH = '../data';

/**
 * 加载单个标的的数据
 * @param {string} ticker - 股票/ETF代码
 * @returns {Promise<Object>} - 数据对象，包含 info 和 prices
 */
export async function loadTickerData(ticker) {
  try {
    const response = await fetch(`${DATA_BASE_PATH}/${ticker.toUpperCase()}.json`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} - 无法加载 ${ticker}.json`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`加载 ${ticker} 数据失败:`, error);
    throw error;
  }
}

/**
 * 加载概览数据（标的列表）
 * @returns {Promise<Array>} - 概览数据数组
 */
export async function loadOverview() {
  try {
    const response = await fetch(`${DATA_BASE_PATH}/overview.json`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} - 无法加载 overview.json`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('加载概览数据失败:', error);
    // 返回 mock 数据作为 fallback
    return getMockOverviewData();
  }
}

/**
 * 加载对比数据
 * @param {string|Array} symbols - 逗号分隔的代码字符串或数组
 * @returns {Promise<Object>} - 对比结果
 */
export async function loadCompareData(symbols) {
  if (typeof symbols === 'string') {
    symbols = symbols.split(/[,，\s]+/).filter(Boolean);
  }

  const results = [];
  const errors = [];

  for (const symbol of symbols) {
    try {
      const data = await loadTickerData(symbol);
      const prices = data.prices || [];

      if (prices.length === 0) {
        errors.push(`⚠️ ${symbol}: 无价格数据`);
        continue;
      }

      // 计算对比指标
      const metrics = calculateMetrics(prices);
      results.push({
        symbol: symbol.toUpperCase(),
        ...metrics
      });
    } catch (error) {
      errors.push(`❌ ${symbol}: ${error.message}`);
    }
  }

  return {
    results,
    errors: errors.length > 0 ? errors : null
  };
}

/**
 * 计算价格数据的对比指标
 * @param {Array} prices - 价格数组
 * @returns {Object} - 指标对象
 */
function calculateMetrics(prices) {
  if (!prices || prices.length < 2) {
    return {
      totalReturn: null,
      annualizedReturn: null,
      volatility: null,
      maxDrawdown: null,
      sharpeRatio: null
    };
  }

  const firstPrice = prices[0].close;
  const lastPrice = prices[prices.length - 1].close;

  // 总收益率
  const totalReturn = (lastPrice - firstPrice) / firstPrice;

  // 年化收益率
  const years = prices.length / 252; // 假设252个交易日/年
  const annualizedReturn = Math.pow(1 + totalReturn, 1 / years) - 1;

  // 波动率（日收益率的标准差 * sqrt(252)）
  const dailyReturns = [];
  for (let i = 1; i < prices.length; i++) {
    const ret = (prices[i].close - prices[i - 1].close) / prices[i - 1].close;
    dailyReturns.push(ret);
  }
  const avgReturn = dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length;
  const variance = dailyReturns.reduce((sum, ret) => sum + Math.pow(ret - avgReturn, 2), 0) / dailyReturns.length;
  const volatility = Math.sqrt(variance) * Math.sqrt(252);

  // 最大回撤
  let maxDrawdown = 0;
  let peak = prices[0].close;
  for (const price of prices) {
    if (price.close > peak) {
      peak = price.close;
    }
    const drawdown = (peak - price.close) / peak;
    if (drawdown > maxDrawdown) {
      maxDrawdown = drawdown;
    }
  }

  // 夏普比率（假设无风险利率为 2%）
  const riskFreeRate = 0.02;
  const sharpeRatio = volatility > 0 ? (annualizedReturn - riskFreeRate) / volatility : null;

  return {
    totalReturn,
    annualizedReturn,
    volatility,
    maxDrawdown,
    sharpeRatio
  };
}

/**
 * Mock 数据 - 当 JSON 文件不存在时作为 fallback
 */
function getMockOverviewData() {
  return [
    {
      symbol: 'VOO',
      name: 'Vanguard S&P 500 ETF',
      price: 450.23,
      change: 1.2,
      changePct: 0.27
    },
    {
      symbol: 'QQQ',
      name: 'Invesco QQQ Trust',
      price: 389.45,
      change: -2.1,
      changePct: -0.54
    },
    {
      symbol: 'SPY',
      name: 'SPDR S&P 500 ETF',
      price: 445.67,
      change: 1.1,
      changePct: 0.25
    }
  ];
}

/**
 * 显示加载状态
 * @param {string} containerId - 容器元素 ID
 * @param {string} message - 加载消息
 */
export function showLoading(containerId, message = '正在加载数据...') {
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = `<div class="loading">${message}</div>`;
  }
}

/**
 * 显示错误信息
 * @param {string} containerId - 容器元素 ID
 * @param {string} message - 错误消息
 */
export function showError(containerId, message) {
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = `<div class="error-msg">❌ ${message}</div>`;
  }
}

/**
 * 清除加载/错误状态
 * @param {string} containerId - 容器元素 ID
 */
export function clearStatus(containerId) {
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = '';
  }
}
