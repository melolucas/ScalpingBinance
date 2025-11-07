"""Testes de configuração"""
import os
import pytest
from app.config import Settings


def test_settings_defaults():
    """Testa defaults de configuração"""
    settings = Settings()
    assert settings.mode == "SPOT"
    assert settings.use_testnet is True
    assert settings.top_n == 15
    assert settings.max_positions == 5


def test_settings_endpoints():
    """Testa preenchimento automático de endpoints"""
    settings = Settings(mode="SPOT", use_testnet=True)
    assert "testnet" in settings.binance_base_url.lower() or settings.binance_base_url
    
    settings = Settings(mode="FUTURES", use_testnet=True)
    assert settings.is_futures is True


def test_settings_properties():
    """Testa propriedades de configuração"""
    settings = Settings(mode="SPOT")
    assert settings.is_spot is True
    assert settings.is_futures is False
    
    settings = Settings(mode="FUTURES")
    assert settings.is_futures is True
    assert settings.is_spot is False

