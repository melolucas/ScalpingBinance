"""Ranking de pares elegíveis"""
import asyncio
from typing import List, Dict, Optional
from app.config import settings
from app.adapters.binance.rest import BinanceREST
from app.data.schemas import Ticker24hSchema
from app.utils.math import z_score, normalize
from app.utils.files import write_json
from app.utils.time import now_utc
from app.utils.json_logger import get_logger

logger = get_logger()


class SymbolRanker:
    """Rankeia símbolos por elegibilidade"""
    
    def __init__(self, rest_client: BinanceREST):
        self.rest = rest_client
        self.last_rank: List[Ticker24hSchema] = []
    
    async def get_eligible_symbols(self) -> List[Ticker24hSchema]:
        """Retorna lista ordenada de símbolos elegíveis"""
        try:
            # Buscar tickers 24h
            tickers = await self.rest.get_ticker_24h()
            
            # Enriquecer com spread e ATR%
            enriched = []
            for ticker in tickers:
                symbol = ticker["symbol"]
                
                # Verificar filtros básicos
                if not self._passes_filters(ticker):
                    continue
                
                # Buscar spread (best bid/ask)
                spread_pct = await self._get_spread(symbol)
                
                # Buscar ATR%
                atr_pct = await self._get_atr_percent(symbol)
                
                # Calcular score
                score = self._calculate_score(ticker, spread_pct, atr_pct)
                
                enriched.append(Ticker24hSchema(
                    symbol=symbol,
                    price_change_percent=float(ticker.get("priceChangePercent", 0)),
                    volume=float(ticker.get("volume", 0)),
                    quote_volume=float(ticker.get("quoteVolume", 0)),
                    high=float(ticker.get("highPrice", 0)),
                    low=float(ticker.get("lowPrice", 0)),
                    last_price=float(ticker.get("lastPrice", 0)),
                    bid_price=0.0,  # Preenchido depois
                    ask_price=0.0,  # Preenchido depois
                    spread_percent=spread_pct,
                    atr_percent=atr_pct,
                    score=score
                ))
            
            # Ordenar por score
            enriched.sort(key=lambda x: x.score, reverse=True)
            
            # Persistir snapshot
            self._save_snapshot(enriched)
            
            self.last_rank = enriched
            return enriched[:settings.top_n]
        
        except Exception as e:
            logger.error("rank_error", error=str(e))
            return self.last_rank[:settings.top_n] if self.last_rank else []
    
    def _passes_filters(self, ticker: dict) -> bool:
        """Verifica se ticker passa nos filtros básicos"""
        volume = float(ticker.get("quoteVolume", 0))
        min_vol = settings.min_volume
        
        if volume < min_vol:
            return False
        
        change_pct = abs(float(ticker.get("priceChangePercent", 0)))
        if change_pct < settings.min_daily_change_percent * 100:
            return False
        
        return True
    
    async def _get_spread(self, symbol: str) -> float:
        """Busca spread percentual (best bid/ask)"""
        try:
            book = await self.rest.get_order_book(symbol, limit=5)
            if not book or "bids" not in book or "asks" not in book:
                return 0.001  # Default conservador
            
            bids = book["bids"]
            asks = book["asks"]
            
            if not bids or not asks:
                return 0.001
            
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            
            if best_bid == 0:
                return 0.001
            
            spread_pct = ((best_ask - best_bid) / best_bid)
            return spread_pct
        
        except Exception:
            return 0.001
    
    async def _get_atr_percent(self, symbol: str) -> float:
        """Calcula ATR% a partir de klines"""
        try:
            klines = await self.rest.get_klines(symbol, interval="5m", limit=50)
            if len(klines) < 14:
                return 0.0
            
            # Calcular ATR simples
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            closes = [float(k[4]) for k in klines]
            
            trs = []
            for i in range(1, len(klines)):
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i-1]),
                    abs(lows[i] - closes[i-1])
                )
                trs.append(tr)
            
            # ATR(14)
            atr = sum(trs[-14:]) / 14 if len(trs) >= 14 else sum(trs) / len(trs) if trs else 0.0
            
            current_price = closes[-1]
            if current_price == 0:
                return 0.0
            
            atr_pct = (atr / current_price)
            return atr_pct
        
        except Exception:
            return 0.0
    
    def _calculate_score(self, ticker: dict, spread_pct: float, atr_pct: float) -> float:
        """Calcula score de elegibilidade"""
        # Coletar métricas
        volume = float(ticker.get("quoteVolume", 0))
        change_pct = abs(float(ticker.get("priceChangePercent", 0)))
        
        # Normalizar (z-score aproximado)
        # Para simplificar, usar valores relativos
        volumes = [t.get("quoteVolume", 0) for t in [ticker]]  # Simplificado
        atrs = [atr_pct]
        changes = [change_pct]
        spreads = [spread_pct]
        
        # Score = z(volume) + z(atr) + z(change) - z(spread)
        # Simplificado: usar valores relativos
        vol_score = min(volume / 1e9, 1.0)  # Normalizado
        atr_score = min(atr_pct / 0.01, 1.0)  # Normalizado
        change_score = min(change_pct / 5.0, 1.0)  # Normalizado
        spread_penalty = min(spread_pct / 0.001, 1.0)  # Penalidade
        
        score = vol_score * 0.3 + atr_score * 0.3 + change_score * 0.2 - spread_penalty * 0.2
        
        # Winrate histórico (placeholder - implementar depois)
        winrate_hist = 0.5
        score += winrate_hist * 0.1
        
        return score
    
    def _save_snapshot(self, ranked: List[Ticker24hSchema]):
        """Salva snapshot do ranking"""
        try:
            date_str = now_utc().strftime("%Y%m%d_%H%M%S")
            snapshot_path = f"{settings.log_path}/rank_{date_str}.json"
            data = [t.model_dump() for t in ranked]
            write_json(snapshot_path, data)
        except Exception as e:
            logger.warning("snapshot_save_failed", error=str(e))

