"""Estratégia de pullback básica"""
from typing import Optional, Dict
from app.core.strategy import Strategy
from app.core.context import MarketContext
from app.config import settings
from app.utils.json_logger import get_logger

logger = get_logger()


class BasicPullbackStrategy(Strategy):
    """Estratégia de pullback com EMA/T3"""
    
    def __init__(self):
        super().__init__()
        self.name = "basic_pullback"
    
    def should_enter(self, context: MarketContext) -> tuple[bool, Optional[Dict]]:
        """Decide se deve entrar baseado em pullback"""
        # Verificar tendência
        trend = context.get_trend()
        if not trend or trend != "UP":
            return False, None  # Só opera em tendência de alta (long)
        
        # Verificar pullback
        pullback_pct = context.get_recent_pullback(candles=5)
        if not pullback_pct or pullback_pct < 1.2:  # Pullback mínimo de 1.2%
            return False, None
        
        # Verificar ATR%
        atr_pct = context.get_atr_percent()
        if atr_pct < settings.min_volatility_percent:
            return False, None
        
        # Verificar spread
        if context.spread_pct > settings.max_spread_percent:
            return False, None
        
        # Verificar volume (último candle)
        if not context.candles_1m:
            return False, None
        
        last_candle = context.candles_1m[-1]
        volume = float(last_candle.get("volume", 0))
        
        # Verificar se volume é maior que média (simplificado)
        if len(context.candles_1m) >= 20:
            avg_volume = sum(float(c.get("volume", 0)) for c in list(context.candles_1m)[-20:]) / 20
            if volume < avg_volume * 0.8:  # Volume abaixo de 80% da média
                return False, None
        
        # Sinal de entrada
        signal_data = {
            "trend": trend,
            "pullback_pct": pullback_pct,
            "atr_pct": atr_pct,
            "spread_pct": context.spread_pct,
            "entry_price": context.get_current_price()
        }
        
        logger.info("signal_triggered", symbol=context.symbol, **signal_data)
        return True, signal_data
    
    def should_exit(self, context: MarketContext, entry_price: float, current_price: float) -> tuple[bool, Optional[str]]:
        """Decide se deve sair"""
        # Verificar reversão de tendência
        trend = context.get_trend()
        if trend == "DOWN":
            return True, "trend_reversal"
        
        # Verificar se TP foi atingido (deve ser verificado externamente)
        # Verificar se SL foi atingido (deve ser verificado externamente)
        
        return False, None

