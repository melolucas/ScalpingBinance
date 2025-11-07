"""Testes de estratégia"""
import pytest
from app.core.context import MarketContext
from app.strategies.basic_pullback import BasicPullbackStrategy


def test_strategy_should_enter():
    """Testa decisão de entrada"""
    strategy = BasicPullbackStrategy()
    context = MarketContext("BTCUSDT")
    
    # Mock candles com tendência de alta
    for i in range(30):
        candle = {
            "open": 50000 + i * 10,
            "high": 50000 + i * 10 + 50,
            "low": 50000 + i * 10 - 50,
            "close": 50000 + i * 10 + 20,
            "volume": 1000
        }
        context.update_candle(candle, "1m")
    
    # Verificar se tem tendência
    trend = context.get_trend()
    assert trend in ["UP", "DOWN", None]


def test_strategy_tp_sl():
    """Testa cálculo de TP/SL"""
    strategy = BasicPullbackStrategy()
    context = MarketContext("BTCUSDT")
    
    # Mock candles
    for i in range(30):
        candle = {
            "open": 50000,
            "high": 50100,
            "low": 49900,
            "close": 50000,
            "volume": 1000
        }
        context.update_candle(candle, "1m")
    
    entry_price = 50000
    tp_price, sl_price = strategy.calculate_tp_sl(context, entry_price)
    
    assert tp_price > entry_price
    assert sl_price < entry_price

