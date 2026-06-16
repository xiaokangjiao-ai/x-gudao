# -*- coding: utf-8 -*-
"""
X-Gudao FastAPI Web 服务
对标 Macrotrends 的实时金融数据 API
"""

import sys
import os
import logging
from typing import Optional, List

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

# 路径配置
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data_fetcher import DataFetcher
from src.db_fetcher import fetch_from_db, get_latest_date, get_db_stats
from src.models import StockDataResponse, StockPriceRow, StockInfo, CompareResponse, CompareItem, ErrorResponse

# 日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="X-Gudao 股道奇货 API",
    description="对标 Macrotrends 的中文金融数据分析平台",
    version="1.0.0"
)

# 全局数据获取器
fetcher = DataFetcher()

# 静态文件服务
static_dir = os.path.join(os.path.dirname(__file__), 'static')
output_dir = os.path.join(os.path.dirname(__file__), 'output')

if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
if os.path.isdir(output_dir):
    app.mount("/output", StaticFiles(directory=output_dir, html=True), name="output")

# CSS 服务（从 output/css）
css_dir = os.path.join(output_dir, 'css')
if os.path.isdir(css_dir):
    app.mount("/css", StaticFiles(directory=css_dir), name="css")

# 股票详情页服务（从 output/stocks）
stocks_dir = os.path.join(output_dir, 'stocks')
if os.path.isdir(stocks_dir):
    app.mount("/stocks", StaticFiles(directory=stocks_dir, html=True), name="stocks")

# 对比页服务
compare_dir = os.path.join(output_dir, 'compare')
if os.path.isdir(compare_dir):
    app.mount("/compare", StaticFiles(directory=compare_dir, html=True), name="compare")


@app.get("/", response_class=HTMLResponse)
async def root():
    """首页 - 优先 static/index.html（交互式），fallback 到 output/index.html（静态）"""
    interactive = os.path.join(static_dir, 'index.html')
    static_index = os.path.join(output_dir, 'index.html')
    if os.path.exists(interactive):
        return FileResponse(interactive)
    elif os.path.exists(static_index):
        return FileResponse(static_index)
    return HTMLResponse("<h1>欢迎使用 X-Gudao 股道奇货</h1><p>API 文档: <a href='/docs'>/docs</a></p>")


@app.get("/docs")
@app.get("/redoc")
async def api_docs():
    """Swagger 文档由 FastAPI 自动提供"""


@app.get("/api/stock/{symbol}", response_model=StockDataResponse)
async def get_stock(symbol: str, period: str = "5y"):
    """获取股票/ETF 历史数据（含 MA20/MA50）
    优先从本地 SQLite 读取，无数据时 fallback 到 Yahoo Finance"""
    symbol = symbol.upper().strip()
    
    # 验证 period
    valid_periods = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"]
    if period not in valid_periods:
        raise HTTPException(status_code=400, detail=f"Invalid period: {period}. Must be one of {valid_periods}")
    
    try:
        # ── 优先：本地 SQLite ───────────────────────────
        df = fetch_from_db(symbol.upper(), period=period)
        
        if df is None:
            # ── Fallback：Yahoo Finance ────────────────
            logger.info(f"[{symbol}] 本地缓存未命中，尝试 Yahoo Finance...")
            df = fetcher.get_stock_data(symbol, period=period)
        
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for symbol: {symbol}")
        
        # 计算均线
        for window in [20, 50]:
            df[f'ma_{window}'] = df['close'].rolling(window=window).mean()
        
        # 转换 NaN 为 None
        df = df.where(pd.notna(df), None)
        
        # 构建 Pydantic 模型
        rows = []
        for _, row in df.iterrows():
            rows.append(StockPriceRow(
                date=str(row.get('date', '')),
                open=float(row['open']) if row.get('open') is not None else None,
                high=float(row['high']) if row.get('high') is not None else None,
                low=float(row['low']) if row.get('low') is not None else None,
                close=float(row['close']) if row.get('close') is not None else None,
                volume=int(row['volume']) if row.get('volume') is not None else None,
                daily_return=float(row['daily_return']) if row.get('daily_return') is not None else None,
                ma_20=float(row['ma_20']) if row.get('ma_20') is not None else None,
                ma_50=float(row['ma_50']) if row.get('ma_50') is not None else None,
            ))
        
        # 获取基本信息
        info_dict = fetcher.get_stock_info(symbol)
        stock_info = StockInfo(**{k: v for k, v in info_dict.items() if k in StockInfo.model_fields}) if info_dict else None
        
        return StockDataResponse(
            symbol=symbol,
            info=stock_info,
            prices=rows,
            total_rows=len(rows),
            period=period
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/compare")
async def compare_stocks(symbols: str = Query(..., description="逗号分隔的股票代码，如 VOO,QQQ,SPY"), period: str = "5y"):
    """多资产对比"""
    sym_list = [s.upper().strip() for s in symbols.split(',') if s.strip()]
    
    if len(sym_list) < 2:
        raise HTTPException(status_code=400, detail="Please provide at least 2 symbols")
    if len(sym_list) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 symbols allowed")
    
    try:
        # 优先从本地 SQLite 读取
        data = {}
        for sym in sym_list:
            df = fetch_from_db(sym, period=period)
            if df is not None and not df.empty:
                data[sym] = df
        
        # 缺失的标的 fallback 到 Yahoo Finance
        missing = [s for s in sym_list if s not in data]
        if missing:
            logger.info(f"对比接口缺失数据，尝试 Yahoo Finance: {missing}")
            yf_data = fetcher.get_multiple_stocks(missing, period=period)
            data.update({k: v for k, v in yf_data.items() if v is not None and not v.empty})
        
        items = []
        for sym in sym_list:
            if sym not in data or data[sym].empty:
                items.append(CompareItem(
                    symbol=sym, annualized_return=None, volatility=None,
                    sharpe_ratio=None, max_drawdown=None, current_price=None, total_rows=0
                ))
                continue
            
            df = data[sym]
            returns = df['daily_return'].dropna()
            annual_return = (1 + returns).prod() ** (252 / len(returns)) - 1 if len(returns) > 0 else 0
            volatility = returns.std() * (252 ** 0.5) if len(returns) > 0 else 0
            sharpe = (annual_return - 0.04) / volatility if volatility > 0 else 0
            
            cumret = (1 + returns).cumprod()
            peak = cumret.cummax()
            drawdown = ((cumret - peak) / peak).min()
            
            items.append(CompareItem(
                symbol=sym,
                annualized_return=round(annual_return * 100, 2),
                volatility=round(volatility * 100, 2),
                sharpe_ratio=round(sharpe, 3),
                max_drawdown=round(drawdown * 100, 2),
                current_price=round(float(df['close'].iloc[-1]), 2),
                total_rows=len(df)
            ))
        
        return CompareResponse(items=items, symbols=sym_list, period=period)
    
    except Exception as e:
        logger.error(f"Compare error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def db_status():
    """数据库同步状态"""
    stats = get_db_stats()
    return stats


@app.get("/api/sync/trigger")
async def sync_trigger(symbols: str = Query(None, description="可选：逗号分隔标的，不填则同步全部")):
    """手动触发数据同步（供 cron 任务调用）"""
    import subprocess, sys
    cmd = [sys.executable, "src/massive_fetcher.py", "--mode", "daily"]
    if symbols:
        cmd += ["--symbols", symbols]
    result = subprocess.run(cmd, capture_output=True, text=True,
                           cwd=os.path.dirname(__file__))
    return {
        "returncode": result.returncode,
        "stdout": result.stdout[-500:] if result.stdout else "",
        "stderr": result.stderr[-200:] if result.stderr else "",
    }



@app.get("/api/info/{symbol}")
async def get_info(symbol: str):
    """获取股票基本信息"""
    symbol = symbol.upper().strip()
    info = fetcher.get_stock_info(symbol)
    if not info or len(info) <= 1:
        raise HTTPException(status_code=404, detail=f"No info found for symbol: {symbol}")
    return info


@app.get("/about.html", response_class=HTMLResponse)
@app.get("/screener.html", response_class=HTMLResponse)
async def fallback_pages(request: Request):
    """缺失页面 fallback"""
    path = request.url.path
    filename = path.lstrip('/')
    static_file = os.path.join(static_dir, filename) if os.path.isdir(static_dir) else None
    output_file = os.path.join(output_dir, filename)
    
    if static_file and os.path.exists(static_file):
        return FileResponse(static_file)
    if os.path.exists(output_file):
        return FileResponse(output_file)
    
    raise HTTPException(status_code=404, detail="File not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=3000, reload=True)
