"""Executor de ordens"""
import asyncio
import uuid
from typing import Optional, Dict, Tuple
from app.config import settings
from app.adapters.binance.rest import BinanceREST
from app.adapters.binance.symbols import SymbolCache
from app.core.risk import RiskManager
from app.utils.json_logger import get_logger
from app.utils.time import timestamp_ms

logger = get_logger()


class OrderExecutor:
    """Executor de ordens"""
    
    def __init__(self, rest_client: BinanceREST, symbol_cache: SymbolCache, risk_manager: RiskManager, dry_run: bool = False):
        self.rest = rest_client
        self.symbol_cache = symbol_cache
        self.risk = risk_manager
        self.dry_run = dry_run
        self.active_orders: Dict[str, dict] = {}  # symbol -> order info
    
    def _generate_order_id(self, symbol: str) -> str:
        """Gera ID único de ordem"""
        return f"{symbol}_{uuid.uuid4().hex[:8]}_{timestamp_ms()}"
    
    async def enter_long(
        self,
        symbol: str,
        entry_price: float,
        qty: float,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Entra em posição long"""
        try:
            # Validar símbolo
            symbol_info = await self.symbol_cache.get_symbol_info(symbol)
            if not symbol_info:
                return False, None, f"Symbol {symbol} not found"
            
            # Validar preço
            valid, error = symbol_info.validate_price(entry_price)
            if not valid:
                return False, None, error
            
            # Validar quantidade
            valid, error, qty = symbol_info.validate_quantity(qty)
            if not valid:
                return False, None, error
            
            # Validar notional
            valid, error = symbol_info.validate_notional(entry_price, qty)
            if not valid:
                return False, None, error
            
            # Gerar order ID
            order_id = self._generate_order_id(symbol)
            
            if self.dry_run:
                logger.info("dry_run_order", symbol=symbol, side="BUY", price=entry_price, qty=qty)
                return True, {"orderId": order_id, "status": "FILLED"}, None
            
            # Criar ordem
            if settings.is_spot:
                # Spot: LIMIT order
                order = await self.rest.create_order(
                    symbol=symbol,
                    side="BUY",
                    order_type="LIMIT",
                    quantity=qty,
                    price=entry_price,
                    time_in_force="IOC",  # Immediate or Cancel
                    new_client_order_id=order_id
                )
            else:
                # Futures: MARKET order (simplificado)
                order = await self.rest.create_order(
                    symbol=symbol,
                    side="BUY",
                    order_type="MARKET",
                    quantity=qty,
                    new_client_order_id=order_id
                )
                
                # Criar TP e SL
                if tp_price:
                    await self.rest.create_take_profit_market(
                        symbol=symbol,
                        side="BUY",
                        stop_price=tp_price,
                        close_position=True
                    )
                
                if sl_price:
                    await self.rest.create_stop_market(
                        symbol=symbol,
                        side="BUY",
                        stop_price=sl_price,
                        close_position=True
                    )
            
            self.active_orders[symbol] = {
                "order_id": order.get("orderId"),
                "client_order_id": order_id,
                "symbol": symbol,
                "side": "BUY",
                "price": entry_price,
                "qty": qty,
                "tp_price": tp_price,
                "sl_price": sl_price
            }
            
            logger.info("order_created", symbol=symbol, order_id=order_id, side="BUY")
            return True, order, None
        
        except Exception as e:
            logger.error("order_create_failed", symbol=symbol, error=str(e))
            return False, None, str(e)
    
    async def exit_position(
        self,
        symbol: str,
        exit_price: Optional[float] = None,
        reason: Optional[str] = None
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Sai de posição"""
        try:
            order_info = self.active_orders.get(symbol)
            if not order_info:
                return False, None, f"No active order for {symbol}"
            
            if self.dry_run:
                logger.info("dry_run_exit", symbol=symbol, price=exit_price, reason=reason)
                return True, {"status": "FILLED"}, None
            
            # Spot: criar ordem de venda
            if settings.is_spot:
                if exit_price:
                    # LIMIT order
                    order = await self.rest.create_order(
                        symbol=symbol,
                        side="SELL",
                        order_type="LIMIT",
                        quantity=order_info["qty"],
                        price=exit_price,
                        time_in_force="IOC",
                        new_client_order_id=self._generate_order_id(symbol)
                    )
                else:
                    # MARKET order
                    order = await self.rest.create_order(
                        symbol=symbol,
                        side="SELL",
                        order_type="MARKET",
                        quantity=order_info["qty"],
                        new_client_order_id=self._generate_order_id(symbol)
                    )
            else:
                # Futures: TP/SL já estão configurados, ou cancelar e criar MARKET
                # Simplificado: assumir que TP/SL já foram acionados
                pass
            
            # Remover da lista de ordens ativas
            if symbol in self.active_orders:
                del self.active_orders[symbol]
            
            logger.info("position_exited", symbol=symbol, reason=reason)
            return True, order if 'order' in locals() else {}, None
        
        except Exception as e:
            logger.error("exit_failed", symbol=symbol, error=str(e))
            return False, None, str(e)
    
    async def cancel_order(self, symbol: str) -> bool:
        """Cancela ordem"""
        try:
            order_info = self.active_orders.get(symbol)
            if not order_info:
                return False
            
            await self.rest.cancel_order(
                symbol=symbol,
                order_id=order_info.get("order_id"),
                orig_client_order_id=order_info.get("client_order_id")
            )
            
            if symbol in self.active_orders:
                del self.active_orders[symbol]
            
            logger.info("order_cancelled", symbol=symbol)
            return True
        
        except Exception as e:
            logger.error("cancel_failed", symbol=symbol, error=str(e))
            return False
    
    async def reconcile(self, symbol: str) -> Dict:
        """Reconcilia status de ordem/posição"""
        try:
            # Buscar ordens abertas
            # Ignorar erro 400 (símbolo pode não existir no testnet ou não ter ordens)
            try:
                open_orders = await self.rest.get_open_orders(symbol)
            except Exception as e:
                # Erro 400 geralmente significa que não há ordens ou símbolo inválido
                # Não é crítico, apenas logar em debug
                logger.debug("reconcile_no_orders", symbol=symbol, error=str(e))
                open_orders = []
            
            # Buscar posições (Futures)
            positions = []
            if settings.is_futures:
                try:
                    positions = await self.rest.get_position(symbol)
                except Exception as e:
                    logger.debug("reconcile_no_positions", symbol=symbol, error=str(e))
                    positions = []
            
            return {
                "open_orders": open_orders,
                "positions": positions
            }
        
        except Exception as e:
            # Erro crítico apenas se não for 400
            if "400" not in str(e):
                logger.error("reconcile_failed", symbol=symbol, error=str(e))
            return {}

