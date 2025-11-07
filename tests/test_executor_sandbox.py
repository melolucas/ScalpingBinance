"""Testes sandbox do executor"""
import pytest
from app.core.executor import OrderExecutor
from app.adapters.binance.symbols import SymbolInfo


def test_symbol_info_validation():
    """Testa validação de símbolo"""
    # Mock filters
    filters = [
        {
            "filterType": "PRICE_FILTER",
            "minPrice": "0.0001",
            "maxPrice": "100000",
            "tickSize": "0.0001"
        },
        {
            "filterType": "LOT_SIZE",
            "minQty": "0.001",
            "maxQty": "1000",
            "stepSize": "0.001"
        },
        {
            "filterType": "MIN_NOTIONAL",
            "minNotional": "10"
        }
    ]
    
    symbol_info = SymbolInfo("BTCUSDT", filters)
    
    # Validar preço
    valid, error = symbol_info.validate_price(50000)
    assert valid is True
    
    # Validar quantidade
    valid, error, qty = symbol_info.validate_quantity(0.1)
    assert valid is True
    
    # Validar notional
    valid, error = symbol_info.validate_notional(50000, 0.1)
    assert valid is True  # 5000 > 10


def test_order_id_generation():
    """Testa geração de order ID"""
    from app.core.executor import OrderExecutor
    
    # Mock executor
    executor = OrderExecutor(None, None, None, dry_run=True)
    
    order_id = executor._generate_order_id("BTCUSDT")
    
    assert "BTCUSDT" in order_id
    assert len(order_id) > 10

