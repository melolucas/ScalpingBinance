"""Contexto de mercado (indicadores)"""
from typing import List, Optional, Dict
from collections import deque
from app.data.schemas import CandleSchema
from app.utils.json_logger import get_logger

logger = get_logger()


class MarketContext:
    """Contexto de mercado com indicadores"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.candles_1m: deque = deque(maxlen=100)
        self.candles_5m: deque = deque(maxlen=100)
        self.ema9: Optional[float] = None
        self.ema21: Optional[float] = None
        self.t3: Optional[float] = None
        self.atr_1m: Optional[float] = None
        self.atr_5m: Optional[float] = None
        self.spread_pct: float = 0.0
    
    def update_candle(self, candle: dict, interval: str = "1m"):
        """Atualiza candle e recalcula indicadores"""
        if interval == "1m":
            self.candles_1m.append(candle)
        elif interval == "5m":
            self.candles_5m.append(candle)
        
        self._recalculate_indicators()
    
    def _recalculate_indicators(self):
        """Recalcula todos os indicadores"""
        if len(self.candles_1m) >= 21:
            self._calculate_ema()
            self._calculate_t3()
            self._calculate_atr()
    
    def _calculate_ema(self):
        """Calcula EMA(9) e EMA(21)"""
        if len(self.candles_1m) < 21:
            return
        
        closes = [float(c.get("close", 0)) for c in self.candles_1m]
        
        # EMA(9)
        ema9 = self._ema(closes, 9)
        self.ema9 = ema9[-1] if ema9 else None
        
        # EMA(21)
        ema21 = self._ema(closes, 21)
        self.ema21 = ema21[-1] if ema21 else None
    
    def _ema(self, prices: List[float], period: int) -> List[float]:
        """Calcula EMA"""
        if len(prices) < period:
            return []
        
        multiplier = 2.0 / (period + 1)
        ema = [prices[0]]
        
        for price in prices[1:]:
            ema.append((price - ema[-1]) * multiplier + ema[-1])
        
        return ema
    
    def _calculate_t3(self):
        """Calcula Tilson T3"""
        if len(self.candles_1m) < 21:
            return
        
        closes = [float(c.get("close", 0)) for c in self.candles_1m]
        
        # T3 simplificado (usando EMA com período 8 e 21)
        ema8 = self._ema(closes, 8)
        if not ema8:
            return
        
        # T3 = EMA(EMA(EMA(close, 8), 8), 8) - simplificado
        ema8_2 = self._ema(ema8, 8)
        if not ema8_2:
            return
        
        ema8_3 = self._ema(ema8_2, 8)
        if not ema8_3:
            return
        
        self.t3 = ema8_3[-1]
    
    def _calculate_atr(self):
        """Calcula ATR(14)"""
        if len(self.candles_1m) < 14:
            return
        
        highs = [float(c.get("high", 0)) for c in self.candles_1m]
        lows = [float(c.get("low", 0)) for c in self.candles_1m]
        closes = [float(c.get("close", 0)) for c in self.candles_1m]
        
        trs = []
        for i in range(1, len(self.candles_1m)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            trs.append(tr)
        
        if len(trs) >= 14:
            atr = sum(trs[-14:]) / 14
            self.atr_1m = atr
        
        # ATR 5m
        if len(self.candles_5m) >= 14:
            highs_5m = [float(c.get("high", 0)) for c in self.candles_5m]
            lows_5m = [float(c.get("low", 0)) for c in self.candles_5m]
            closes_5m = [float(c.get("close", 0)) for c in self.candles_5m]
            
            trs_5m = []
            for i in range(1, len(self.candles_5m)):
                tr = max(
                    highs_5m[i] - lows_5m[i],
                    abs(highs_5m[i] - closes_5m[i-1]),
                    abs(lows_5m[i] - closes_5m[i-1])
                )
                trs_5m.append(tr)
            
            if len(trs_5m) >= 14:
                atr_5m = sum(trs_5m[-14:]) / 14
                self.atr_5m = atr_5m
    
    def get_atr_percent(self) -> float:
        """Retorna ATR%"""
        if not self.candles_1m:
            return 0.0
        
        current_price = float(self.candles_1m[-1].get("close", 0))
        if current_price == 0 or not self.atr_1m:
            return 0.0
        
        return (self.atr_1m / current_price)
    
    def get_trend(self) -> Optional[str]:
        """Retorna tendência: 'UP', 'DOWN', None"""
        if not self.ema9 or not self.ema21:
            return None
        
        if self.ema9 > self.ema21:
            return "UP"
        elif self.ema9 < self.ema21:
            return "DOWN"
        
        return None
    
    def get_current_price(self) -> float:
        """Retorna preço atual"""
        if not self.candles_1m:
            return 0.0
        return float(self.candles_1m[-1].get("close", 0))
    
    def get_recent_pullback(self, candles: int = 5) -> Optional[float]:
        """Detecta pullback recente (retorna % de queda)"""
        if len(self.candles_1m) < candles:
            return None
        
        recent = list(self.candles_1m)[-candles:]
        highs = [float(c.get("high", 0)) for c in recent]
        current = float(recent[-1].get("close", 0))
        
        if not highs or current == 0:
            return None
        
        max_high = max(highs)
        pullback_pct = ((max_high - current) / max_high) * 100.0
        
        return pullback_pct if pullback_pct > 0 else None

