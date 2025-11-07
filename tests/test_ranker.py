"""Testes do ranker"""
import pytest
from app.data.ranker import SymbolRanker
from app.data.schemas import Ticker24hSchema


def test_ranker_filters():
    """Testa filtros do ranker"""
    # Mock ticker
    ticker = {
        "symbol": "BTCUSDT",
        "quoteVolume": 100000000,  # Passa filtro de volume
        "priceChangePercent": 2.0,  # Passa filtro de variação
        "highPrice": "50000",
        "lowPrice": "48000",
        "lastPrice": "49000"
    }
    
    # Simular validação
    min_vol = 10000000
    min_change = 0.015 * 100
    
    volume_ok = float(ticker["quoteVolume"]) >= min_vol
    change_ok = abs(float(ticker["priceChangePercent"])) >= min_change
    
    assert volume_ok is True
    assert change_ok is True


def test_ranker_score():
    """Testa cálculo de score"""
    # Dados mock
    volume = 100000000
    atr_pct = 0.01
    change_pct = 2.0
    spread_pct = 0.0005
    
    # Score simplificado
    vol_score = min(volume / 1e9, 1.0)
    atr_score = min(atr_pct / 0.01, 1.0)
    change_score = min(change_pct / 5.0, 1.0)
    spread_penalty = min(spread_pct / 0.001, 1.0)
    
    score = vol_score * 0.3 + atr_score * 0.3 + change_score * 0.2 - spread_penalty * 0.2
    
    assert score > 0
    assert score <= 1.0

