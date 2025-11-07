"""Cache de exchangeInfo e validação de filtros"""
import asyncio
from typing import Dict, List, Optional, Tuple
from app.adapters.binance.rest import BinanceREST
from app.utils.json_logger import get_logger

logger = get_logger()


class SymbolInfo:
    """Informações e filtros de símbolo"""
    
    def __init__(self, symbol: str, filters: dict):
        self.symbol = symbol
        self.filters = {f["filterType"]: f for f in filters}
    
    def get_price_filter(self) -> Optional[dict]:
        """Retorna filtro de preço"""
        return self.filters.get("PRICE_FILTER")
    
    def get_lot_size(self) -> Optional[dict]:
        """Retorna filtro de tamanho de lote"""
        return self.filters.get("LOT_SIZE")
    
    def get_min_notional(self) -> Optional[dict]:
        """Retorna filtro de notional mínimo"""
        return self.filters.get("MIN_NOTIONAL")
    
    def validate_price(self, price: float) -> Tuple[bool, Optional[str]]:
        """Valida preço contra filtros"""
        price_filter = self.get_price_filter()
        if not price_filter:
            return True, None
        
        min_price = float(price_filter.get("minPrice", 0))
        max_price = float(price_filter.get("maxPrice", float("inf")))
        tick_size = float(price_filter.get("tickSize", 0))
        
        if price < min_price:
            return False, f"Price {price} below min {min_price}"
        if price > max_price:
            return False, f"Price {price} above max {max_price}"
        
        # Arredondar para tick size
        if tick_size > 0:
            price = round(price / tick_size) * tick_size
        
        return True, None
    
    def validate_quantity(self, qty: float) -> Tuple[bool, Optional[str], float]:
        """Valida quantidade contra filtros, retorna qty ajustada"""
        lot_size = self.get_lot_size()
        if not lot_size:
            return True, None, qty
        
        min_qty = float(lot_size.get("minQty", 0))
        max_qty = float(lot_size.get("maxQty", float("inf")))
        step_size = float(lot_size.get("stepSize", 0))
        
        if qty < min_qty:
            return False, f"Quantity {qty} below min {min_qty}", qty
        if qty > max_qty:
            return False, f"Quantity {qty} above max {max_qty}", qty
        
        # Arredondar para step size
        if step_size > 0:
            qty = round(qty / step_size) * step_size
        
        return True, None, qty
    
    def validate_notional(self, price: float, qty: float) -> Tuple[bool, Optional[str]]:
        """Valida notional mínimo"""
        min_notional = self.get_min_notional()
        if not min_notional:
            return True, None
        
        min_notional_value = float(min_notional.get("minNotional", 0))
        notional = price * qty
        
        if notional < min_notional_value:
            return False, f"Notional {notional} below min {min_notional_value}"
        
        return True, None


class SymbolCache:
    """Cache de informações de símbolos"""
    
    def __init__(self, rest_client: BinanceREST):
        self.rest = rest_client
        self.symbols: Dict[str, SymbolInfo] = {}
        self.last_update: Optional[float] = None
        self.update_interval = 3600  # 1 hora
    
    async def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """Retorna informações do símbolo"""
        await self._ensure_updated()
        return self.symbols.get(symbol)
    
    async def _ensure_updated(self):
        """Garante que cache está atualizado"""
        import time
        now = time.time()
        
        if self.last_update is None or (now - self.last_update) > self.update_interval:
            await self._update()
    
    async def _update(self):
        """Atualiza cache de símbolos"""
        try:
            exchange_info = await self.rest.get_exchange_info()
            symbols_data = exchange_info.get("symbols", [])
            
            self.symbols = {}
            for sym_data in symbols_data:
                symbol = sym_data["symbol"]
                filters = sym_data.get("filters", [])
                self.symbols[symbol] = SymbolInfo(symbol, filters)
            
            import time
            self.last_update = time.time()
            
            logger.info("symbol_cache_updated", count=len(self.symbols))
        
        except Exception as e:
            logger.error("symbol_cache_update_failed", error=str(e))

