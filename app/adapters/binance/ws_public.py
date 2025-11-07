"""WebSocket público Binance (klines/trades)"""
import asyncio
import json
from typing import Callable, Dict, List, Optional, Set
import websockets
from app.config import settings
from app.utils.json_logger import get_logger

logger = get_logger()


class BinanceWSPublic:
    """WebSocket público para streams de mercado"""
    
    def __init__(self, symbols: List[str], on_candle: Optional[Callable] = None, on_trade: Optional[Callable] = None):
        self.symbols = symbols
        self.on_candle = on_candle
        self.on_trade = on_trade
        self.ws: Optional[websockets.WebSocketServerProtocol] = None
        self.running = False
        self.reconnect_delay = 5
    
    async def connect(self):
        """Conecta ao WebSocket"""
        streams = []
        
        # Construir streams
        for symbol in self.symbols:
            symbol_lower = symbol.lower()
            streams.append(f"{symbol_lower}@kline_1m")
            streams.append(f"{symbol_lower}@kline_5m")
            streams.append(f"{symbol_lower}@trade")
        
        # URL do stream
        stream_names = "/".join(streams)
        
        if settings.is_spot:
            url = f"{settings.ws_public_url}/stream?streams={stream_names}"
        else:
            url = f"{settings.ws_public_url}/stream?streams={stream_names}"
        
        self.running = True
        
        while self.running:
            try:
                async with websockets.connect(url, ping_interval=None) as ws:
                    self.ws = ws
                    logger.info("ws_public_connected", url=url)
                    
                    async for message in ws:
                        if not self.running:
                            break
                        
                        try:
                            data = json.loads(message)
                            
                            # Multiplex stream
                            if "stream" in data and "data" in data:
                                stream = data["stream"]
                                payload = data["data"]
                                
                                if "@kline" in stream:
                                    await self._handle_kline(payload)
                                elif "@trade" in stream:
                                    await self._handle_trade(payload)
                        
                        except json.JSONDecodeError:
                            logger.warning("ws_public_invalid_json", message=message[:100])
                        except Exception as e:
                            logger.error("ws_public_handler_error", error=str(e))
            
            except websockets.exceptions.ConnectionClosed:
                if self.running:
                    logger.warning("ws_public_closed", delay=self.reconnect_delay)
                    await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                if self.running:
                    # 404 pode ser limitação do testnet - logar como warning
                    if "404" in str(e):
                        logger.warning("ws_public_404", error=str(e), 
                                     note="Testnet pode ter limitações no WebSocket. Bot continuará sem dados em tempo real.")
                        # Aguardar mais tempo antes de tentar novamente
                        await asyncio.sleep(60)  # 1 minuto
                    else:
                        logger.error("ws_public_error", error=str(e))
                        await asyncio.sleep(self.reconnect_delay)
    
    async def _handle_kline(self, data: dict):
        """Processa evento de kline"""
        if self.on_candle:
            k = data.get("k", {})
            candle = {
                "symbol": k.get("s"),
                "open_time": int(k.get("t", 0)),
                "close_time": int(k.get("T", 0)),
                "open": float(k.get("o", 0)),
                "high": float(k.get("h", 0)),
                "low": float(k.get("l", 0)),
                "close": float(k.get("c", 0)),
                "volume": float(k.get("v", 0)),
                "quote_volume": float(k.get("q", 0)),
                "trades": int(k.get("n", 0)),
                "is_closed": k.get("x", False)
            }
            await self.on_candle(candle)
    
    async def _handle_trade(self, data: dict):
        """Processa evento de trade"""
        if self.on_trade:
            trade = {
                "symbol": data.get("s"),
                "price": float(data.get("p", 0)),
                "qty": float(data.get("q", 0)),
                "time": int(data.get("T", 0)),
                "is_buyer_maker": data.get("m", False)
            }
            await self.on_trade(trade)
    
    async def disconnect(self):
        """Desconecta WebSocket"""
        self.running = False
        if self.ws:
            await self.ws.close()
        logger.info("ws_public_disconnected")

