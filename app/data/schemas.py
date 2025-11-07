"""Schemas Pydantic para DTOs"""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class TradeSchema(BaseModel):
    """Schema de trade"""
    ts_open: str
    ts_close: Optional[str] = None
    symbol: str
    side: Literal["BUY", "SELL", "LONG", "SHORT"]
    qty: float
    entry_price: float
    exit_price: Optional[float] = None
    pnl_pct_net: Optional[float] = None
    fees_usdt: Optional[float] = None
    spread_entry: float
    atr_pct_entry: float
    signal_ctx: dict = Field(default_factory=dict)
    latency_ms: Optional[int] = None
    result: Optional[Literal["WIN", "LOSS", "BREAKEVEN"]] = None


class DailyStatsSchema(BaseModel):
    """Schema de estatísticas diárias"""
    date: str
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    winrate: float = 0.0
    max_dd: float = 0.0
    ops: int = 0
    best_symbols: list[str] = Field(default_factory=list)
    worst_symbols: list[str] = Field(default_factory=list)


class CandleSchema(BaseModel):
    """Schema de candle"""
    symbol: str
    open_time: int
    close_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    trades: int = 0


class Ticker24hSchema(BaseModel):
    """Schema de ticker 24h"""
    symbol: str
    price_change_percent: float
    volume: float
    quote_volume: float
    high: float
    low: float
    last_price: float
    bid_price: float = 0.0
    ask_price: float = 0.0
    spread_percent: float = 0.0
    atr_percent: float = 0.0
    score: float = 0.0

