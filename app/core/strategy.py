"""Estratégia base"""
from typing import Optional, Dict
from app.core.context import MarketContext
from app.config import settings
from app.utils.json_logger import get_logger

logger = get_logger()


class Strategy:
    """Estratégia base"""
    
    def __init__(self):
        self.name = "base"
    
    def should_enter(self, context: MarketContext) -> tuple[bool, Optional[Dict]]:
        """Decide se deve entrar (retorna (should_enter, signal_data))"""
        return False, None
    
    def calculate_tp_sl(self, context: MarketContext, entry_price: float) -> tuple[float, float]:
        """Calcula TP e SL"""
        atr_pct = context.get_atr_percent()
        
        # TP base
        tp_pct = settings.take_profit_percent
        if atr_pct > 0.01:  # ATR% alto, ajustar TP
            tp_pct += 0.005
        
        # SL base
        sl_pct = settings.stop_loss_percent
        if atr_pct > 0.01:  # ATR% alto, ajustar SL
            sl_pct += 0.003
        
        tp_price = entry_price * (1 + tp_pct)
        sl_price = entry_price * (1 - sl_pct)
        
        return tp_price, sl_price
    
    def should_exit(self, context: MarketContext, entry_price: float, current_price: float) -> tuple[bool, Optional[str]]:
        """Decide se deve sair (retorna (should_exit, reason))"""
        # Verificar se contexto mudou (tendência reversa)
        trend = context.get_trend()
        if trend == "DOWN":  # Se estava comprado e tendência virou para baixo
            return True, "trend_reversal"
        
        return False, None

