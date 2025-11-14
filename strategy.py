"""
Estratégia de scalping: EMA 9/21 + volume + candle breakout
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict
from config import Config

class ScalpingStrategy:
    def __init__(self):
        self.ema_fast = Config.EMA_FAST
        self.ema_slow = Config.EMA_SLOW
        self.volume_period = Config.VOLUME_PERIOD
        
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calcula EMA"""
        return prices.ewm(span=period, adjust=False).mean()
    
    def calculate_volume_avg(self, volumes: pd.Series, period: int) -> float:
        """Calcula volume médio"""
        if len(volumes) < period:
            return volumes.mean()
        return volumes.tail(period).mean()
    
    def check_trend_alignment(self, candles_5m: pd.DataFrame) -> bool:
        """
        Verifica se a tendência no 5m está alinhada
        EMA 9 > EMA 21 no timeframe de tendência
        """
        if len(candles_5m) < self.ema_slow:
            return False
        
        closes = candles_5m['close']
        ema_fast_5m = self.calculate_ema(closes, self.ema_fast)
        ema_slow_5m = self.calculate_ema(closes, self.ema_slow)
        
        # EMA rápida acima da lenta e inclinada pra cima
        last_fast = ema_fast_5m.iloc[-1]
        last_slow = ema_slow_5m.iloc[-1]
        prev_fast = ema_fast_5m.iloc[-2] if len(ema_fast_5m) > 1 else last_fast
        
        return last_fast > last_slow and last_fast > prev_fast
    
    def check_entry_signal(self, candles_1m: pd.DataFrame, candles_5m: pd.DataFrame) -> Optional[Dict]:
        """
        Verifica se há sinal de entrada
        
        Retorna dict com informações do sinal ou None
        """
        if len(candles_1m) < self.ema_slow or len(candles_5m) < self.ema_slow:
            return None
        
        # 1. Verifica alinhamento de tendência no 5m
        if not self.check_trend_alignment(candles_5m):
            return None
        
        # 2. Calcula EMAs no 1m
        closes_1m = candles_1m['close']
        ema_fast_1m = self.calculate_ema(closes_1m, self.ema_fast)
        ema_slow_1m = self.calculate_ema(closes_1m, self.ema_slow)
        
        # 3. Verifica se EMA 9 > EMA 21 no 1m
        last_fast_1m = ema_fast_1m.iloc[-1]
        last_slow_1m = ema_slow_1m.iloc[-1]
        prev_fast_1m = ema_fast_1m.iloc[-2] if len(ema_fast_1m) > 1 else last_fast_1m
        
        if not (last_fast_1m > last_slow_1m and last_fast_1m > prev_fast_1m):
            return None
        
        # 4. Verifica candle forte (close > high anterior)
        if len(candles_1m) < 2:
            return None
        
        last_candle = candles_1m.iloc[-1]
        prev_candle = candles_1m.iloc[-2]
        
        if last_candle['close'] <= prev_candle['high']:
            return None
        
        # 5. Verifica volume acima da média
        volumes = candles_1m['volume']
        volume_avg = self.calculate_volume_avg(volumes, self.volume_period)
        last_volume = last_candle['volume']
        
        if last_volume <= volume_avg:
            return None
        
        # 6. Todos os critérios atendidos - SINAL DE COMPRA
        current_price = last_candle['close']
        
        return {
            'signal': 'BUY',
            'price': current_price,
            'ema_fast': last_fast_1m,
            'ema_slow': last_slow_1m,
            'volume': last_volume,
            'volume_avg': volume_avg,
            'timestamp': last_candle['timestamp']
        }
    
    def should_log_signal(self) -> bool:
        """Retorna True se deve logar sinais (para aprendizado)"""
        return True
    
    def calculate_take_profit(self, entry_price: float) -> float:
        """Calcula preço de take profit"""
        return entry_price * (1 + Config.TAKE_PROFIT_PCT / 100)
    
    def calculate_stop_loss(self, entry_price: float) -> float:
        """Calcula preço de stop loss"""
        return entry_price * (1 - Config.STOP_LOSS_PCT / 100)

