# -*- coding: utf-8 -*-
"""X-Gudao 数据模型 (Pydantic)"""

from pydantic import BaseModel
from typing import Optional, List, Dict

class StockPriceRow(BaseModel):
    date: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    daily_return: Optional[float] = None
    ma_20: Optional[float] = None
    ma_50: Optional[float] = None

class StockInfo(BaseModel):
    symbol: str
    shortName: Optional[str] = None
    longName: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    marketCap: Optional[float] = None
    trailingPE: Optional[float] = None
    forwardPE: Optional[float] = None
    priceToBook: Optional[float] = None
    dividendYield: Optional[float] = None
    beta: Optional[float] = None
    fiftyTwoWeekHigh: Optional[float] = None
    fiftyTwoWeekLow: Optional[float] = None
    returnOnEquity: Optional[float] = None
    profitMargins: Optional[float] = None
    revenueGrowth: Optional[float] = None
    description: Optional[str] = None

class StockDataResponse(BaseModel):
    symbol: str
    info: Optional[StockInfo] = None
    prices: List[StockPriceRow]
    total_rows: int
    period: str

class CompareItem(BaseModel):
    symbol: str
    annualized_return: Optional[float] = None
    volatility: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    current_price: Optional[float] = None
    total_rows: int

class CompareResponse(BaseModel):
    items: List[CompareItem]
    symbols: List[str]
    period: str

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None