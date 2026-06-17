# x-gudao 首页优化任务清单

## 项目路径
- 项目根目录: `C:\Users\Administrator\x-gudao`
- SSG生成器: `src/generate_static.py`
- 输出目录: `output/`
- 模板目录: `templates/index.html`
- 数据库: `data/market_data.db` (440条记录, 22个标的)
- overview.json: `output/overview.json` (22个标的, 含完整价格数据)
- 数据库有数据的标的: VOO, QQQ, SPY, VTI, IWM, GLD, TLT, BND, AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, BRK.B, JPM, V, MA, SI, CL, HG (22个)
- 数据库无数据的标的: IVV, VEA, IEFA, VWO (这4个ETF在overview.json和数据库中均无数据)

## 当前首页渲染逻辑
`generate_static.py` 的 `render_index()` 函数:
- 从 overview.json 获取价格数据
- 从 ETF_META / STOCK_META 获取元数据
- 通过 Jinja2 模板 `templates/index.html` 渲染
- 将数据序列化为 JSON 嵌入页面 (ETF_DATA, STOCK_DATA)
- 包含 ECharts 迷你走势图

## 用户需求（按优先级）

### P0: 修复零值数据
- IVV, VEA, IEFA, VWO 没有数据库数据
- 方案: 对于无数据的标的, 使用 TICKER_METADATA 中的硬编码数据作为回退（来自 merge_pages.py）
- 或者: 只展示有数据的标的, 从首页中移除这4个, 替换为 SI, CL, HG, MA 中的ETF (如果 IWM/TLT 已在ETF列表中)

### P1: 数据修正
- GLD 年化收益 +80.11% 看起来偏高 (overview.json 中数据如此, 可能是商品ETF的正常值, 确认一下)
- MSFT 年化收益 -12.85% (overview.json 中 change_pct 字段, 需确认计算逻辑是全部时间范围还是1年)

### P2: UI优化
1. **涨跌幅视觉强化**:
   - 放大涨跌幅数字字号
   - 提升红绿颜色在深色背景下的饱和度/明度
   - 涨跌颜色切换: 国内习惯"红涨绿跌", 当前是美股"绿涨红跌"

2. **迷你走势图颜色**:
   - 当前所有线条都是蓝色/绿色
   - 应根据涨跌状态: 上涨用红(红涨) / 绿(绿涨), 下跌用绿(红跌) / 红(绿跌)
   - 需要与中国用户习惯一致

3. **统一卡片高度**:
   - 描述文字限制2行, 超出显示省略号
   - 确保 grid 对齐

4. **布局改为左右双栏**:
   - 左侧: ETF板块 (10个卡片)
   - 右侧: 股票板块 (10个卡片)
   - 一屏展示完毕, 无需下拉

5. **市场状态提示**:
   - 页面顶部显示 "数据更新时间: YYYY-MM-DD"
   - 显示 "美股已收盘" / "交易中" 状态

## 技术约束
- 模板使用 Jinja2 (`templates/index.html`)
- 数据嵌入为 JSON (ETF_DATA, STOCK_DATA)
- ECharts 用于迷你走势图
- 纯静态HTML, 无后端
- 使用 `_deploy_ghpages.py` 部署 (通过 gh api)
- 中文界面

## 注意事项
- 不要破坏现有详情页 (`merge_pages.py` 生成的)
- 首页是 `generate_static.py` 生成的, 与详情页生成逻辑分离
- watchlist.json 定义了 ETF 和股票分组
- merge_pages.py 的 TICKER_METADATA 有 IVV/VEA/IEFA/VWO 的硬编码元数据, 可以复用
- 如果用 Python, 注意 GBK 编码问题, print 用 reconfigure(encoding='utf-8')
