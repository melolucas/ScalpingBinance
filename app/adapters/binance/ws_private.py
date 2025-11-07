"""WebSocket privado Binance (user data stream)"""
import asyncio
import json
from typing import Callable, Optional
import websockets
from app.config import settings
from app.adapters.binance.rest import BinanceREST
from app.utils.json_logger import get_logger

logger = get_logger()


class BinanceWSPrivate:
    """WebSocket privado para user data stream"""
    
    def __init__(self, on_order_update: Optional[Callable] = None, on_account_update: Optional[Callable] = None):
        self.rest = BinanceREST()
        self.on_order_update = on_order_update
        self.on_account_update = on_account_update
        self.ws: Optional[websockets.WebSocketServerProtocol] = None
        self.listen_key: Optional[str] = None
        self.running = False
        self.reconnect_delay = 5
        self.ping_interval = settings.ping_interval
    
    async def connect(self):
        """Conecta ao WebSocket privado"""
        # Criar listen key
        try:
            await self._create_listen_key()
        except Exception as e:
            # Se falhar, logar mas não bloquear
            logger.error("listen_key_create_failed", error=str(e))
            logger.warning("ws_private_will_not_connect", 
                         note="WebSocket privado não conectará. Bot continuará sem atualizações de ordens em tempo real.")
            return
        
        if not self.listen_key:
            logger.warning("listen_key_empty", note="Listen key vazio. WebSocket privado não conectará.")
            return
        
        # URL do stream
        if settings.is_spot:
            url = f"{settings.ws_public_url}/{self.listen_key}"
        else:
            url = f"{settings.ws_public_url}/{self.listen_key}"
        
        self.running = True
        
        # Task para ping periódico
        ping_task = asyncio.create_task(self._ping_loop())
        
        try:
            while self.running:
                try:
                    async with websockets.connect(url) as ws:
                        self.ws = ws
                        logger.info("ws_private_connected", url=url)
                        
                        async for message in ws:
                            if not self.running:
                                break
                            
                            try:
                                data = json.loads(message)
                                
                                event_type = data.get("e")
                                
                                if event_type == "executionReport":  # Spot
                                    await self._handle_execution_report(data)
                                elif event_type == "ORDER_TRADE_UPDATE":  # Futures
                                    await self._handle_order_trade_update(data)
                                elif event_type == "outboundAccountPosition":  # Spot account update
                                    await self._handle_account_update(data)
                                elif event_type == "ACCOUNT_UPDATE":  # Futures account update
                                    await self._handle_account_update(data)
                            
                            except json.JSONDecodeError:
                                logger.warning("ws_private_invalid_json", message=message[:100])
                            except Exception as e:
                                logger.error("ws_private_handler_error", error=str(e))
                
                except websockets.exceptions.ConnectionClosed:
                    if self.running:
                        logger.warning("ws_private_closed", delay=self.reconnect_delay)
                        await asyncio.sleep(self.reconnect_delay)
                        await self._refresh_listen_key()
                except Exception as e:
                    if self.running:
                        logger.error("ws_private_error", error=str(e))
                        await asyncio.sleep(self.reconnect_delay)
        
        finally:
            ping_task.cancel()
            await self._delete_listen_key()
    
    async def _create_listen_key(self):
        """Cria listen key"""
        try:
            if settings.is_spot:
                endpoint = "/userDataStream"
            else:
                endpoint = "/listenKey"
            
            url = f"{self.rest.base_url}/{endpoint.lstrip('/')}"
            session = await self.rest._get_session()
            async with session.post(url, headers=self.rest._get_headers()) as resp:
                resp.raise_for_status()
                result = await resp.json()
            self.listen_key = result.get("listenKey")
            logger.info("listen_key_created")
        except Exception as e:
            logger.error("listen_key_create_failed", error=str(e))
            raise
    
    async def _refresh_listen_key(self):
        """Atualiza listen key"""
        if not self.listen_key:
            await self._create_listen_key()
            return
        
        try:
            if settings.is_spot:
                endpoint = "/userDataStream"
            else:
                endpoint = "/listenKey"
            
            url = f"{self.rest.base_url}/{endpoint.lstrip('/')}"
            params = {"listenKey": self.listen_key}
            session = await self.rest._get_session()
            async with session.put(url, params=params, headers=self.rest._get_headers()) as resp:
                resp.raise_for_status()
            logger.debug("listen_key_refreshed")
        except Exception as e:
            logger.warning("listen_key_refresh_failed", error=str(e))
            await self._create_listen_key()
    
    async def _delete_listen_key(self):
        """Deleta listen key"""
        if not self.listen_key:
            return
        
        try:
            if settings.is_spot:
                endpoint = "/userDataStream"
            else:
                endpoint = "/listenKey"
            
            url = f"{self.rest.base_url}/{endpoint.lstrip('/')}"
            params = {"listenKey": self.listen_key}
            session = await self.rest._get_session()
            async with session.delete(url, params=params, headers=self.rest._get_headers()) as resp:
                resp.raise_for_status()
            logger.info("listen_key_deleted")
        except Exception as e:
            logger.warning("listen_key_delete_failed", error=str(e))
    
    async def _ping_loop(self):
        """Loop de ping periódico"""
        while self.running:
            await asyncio.sleep(self.ping_interval)
            if self.running:
                await self._refresh_listen_key()
    
    async def _handle_execution_report(self, data: dict):
        """Processa executionReport (Spot)"""
        if self.on_order_update:
            order_update = {
                "symbol": data.get("s"),
                "client_order_id": data.get("c"),
                "order_id": int(data.get("i", 0)),
                "side": data.get("S"),
                "order_type": data.get("o"),
                "status": data.get("X"),
                "executed_qty": float(data.get("z", 0)),
                "price": float(data.get("p", 0)),
                "time": int(data.get("E", 0))
            }
            await self.on_order_update(order_update)
    
    async def _handle_order_trade_update(self, data: dict):
        """Processa ORDER_TRADE_UPDATE (Futures)"""
        if self.on_order_update:
            order_data = data.get("o", {})
            order_update = {
                "symbol": order_data.get("s"),
                "client_order_id": order_data.get("c"),
                "order_id": int(order_data.get("i", 0)),
                "side": order_data.get("S"),
                "order_type": order_data.get("o"),
                "status": order_data.get("X"),
                "executed_qty": float(order_data.get("z", 0)),
                "price": float(order_data.get("p", 0)),
                "time": int(data.get("E", 0))
            }
            await self.on_order_update(order_update)
    
    async def _handle_account_update(self, data: dict):
        """Processa account update"""
        if self.on_account_update:
            await self.on_account_update(data)
    
    async def disconnect(self):
        """Desconecta WebSocket"""
        self.running = False
        if self.ws:
            await self.ws.close()
        await self._delete_listen_key()
        await self.rest.close()
        logger.info("ws_private_disconnected")

