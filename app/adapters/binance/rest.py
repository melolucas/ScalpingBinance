"""Cliente REST Binance (Spot/Futures)"""
import hmac
import hashlib
import time
from typing import Dict, List, Optional, Any
import aiohttp
from urllib.parse import urlencode
from app.config import settings
from app.utils.json_logger import get_logger

logger = get_logger()


class BinanceREST:
    """Cliente REST para Binance Spot/Futures"""
    
    def __init__(self):
        self.api_key = settings.binance_api_key
        self.api_secret = settings.binance_api_secret
        self.base_url = settings.rest_url
        self.recv_window = settings.recv_window
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Retorna ou cria sessão HTTP"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Fecha sessão HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _sign(self, params: dict) -> str:
        """Gera assinatura HMAC-SHA256"""
        query_string = urlencode(sorted(params.items()))
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_headers(self) -> dict:
        """Retorna headers de autenticação"""
        return {
            "X-MBX-APIKEY": self.api_key
        }
    
    async def _request(self, method: str, endpoint: str, params: Optional[dict] = None, signed: bool = False) -> dict:
        """Faz requisição HTTP"""
        if params is None:
            params = {}
        
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = self.recv_window
            params["signature"] = self._sign(params)
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers() if signed or self.api_key else {}
        
        session = await self._get_session()
        
        try:
            async with session.request(method, url, params=params, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as e:
            logger.error("rest_request_failed", endpoint=endpoint, error=str(e))
            raise
    
    # --- Public Endpoints ---
    
    async def get_exchange_info(self) -> dict:
        """GET /exchangeInfo"""
        if settings.is_spot:
            return await self._request("GET", "/exchangeInfo")
        else:
            return await self._request("GET", "/exchangeInfo")
    
    async def get_ticker_24h(self, symbol: Optional[str] = None) -> List[dict]:
        """GET /ticker/24hr"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        endpoint = "/ticker/24hr"
        result = await self._request("GET", endpoint, params=params)
        if isinstance(result, list):
            return result
        return [result]
    
    async def get_order_book(self, symbol: str, limit: int = 100) -> dict:
        """GET /depth"""
        params = {"symbol": symbol, "limit": limit}
        
        endpoint = "/depth"
        return await self._request("GET", endpoint, params=params)
    
    async def get_klines(self, symbol: str, interval: str = "1m", limit: int = 500) -> List[List]:
        """GET /klines"""
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        endpoint = "/klines"
        return await self._request("GET", endpoint, params=params)
    
    async def get_price(self, symbol: str) -> dict:
        """GET /ticker/price"""
        params = {"symbol": symbol}
        
        endpoint = "/ticker/price"
        return await self._request("GET", endpoint, params=params)
    
    # --- Account Endpoints ---
    
    async def get_account(self) -> dict:
        """GET /account (Spot) ou /fapi/v2/account (Futures)"""
        if settings.is_spot:
            return await self._request("GET", "/account", signed=True)
        else:
            # Futures usa /fapi/v2/account, mas base_url tem /fapi/v1
            # Precisamos usar URL completa
            url = f"{self.base_url.replace('/fapi/v1', '/fapi/v2')}/account"
            params = {
                "timestamp": int(time.time() * 1000),
                "recvWindow": self.recv_window
            }
            params["signature"] = self._sign(params)
            session = await self._get_session()
            async with session.get(url, params=params, headers=self._get_headers()) as resp:
                resp.raise_for_status()
                return await resp.json()
    
    async def get_balance(self) -> dict:
        """Retorna saldo da conta"""
        account = await self.get_account()
        if settings.is_spot:
            return {b["asset"]: float(b["free"]) for b in account.get("balances", [])}
        else:
            return {b["asset"]: float(b["availableBalance"]) for b in account.get("assets", [])}
    
    # --- Order Endpoints ---
    
    async def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        time_in_force: str = "GTC",
        new_client_order_id: Optional[str] = None
    ) -> dict:
        """Cria ordem (Spot ou Futures)"""
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type
        }
        
        if quantity:
            params["quantity"] = quantity
        if price:
            params["price"] = price
        if time_in_force:
            params["timeInForce"] = time_in_force
        if new_client_order_id:
            params["newClientOrderId"] = new_client_order_id
        
        # Futures: adicionar positionSide se necessário
        if not settings.is_spot:
            params["positionSide"] = "BOTH"  # Simplificado
        
        endpoint = "/order"
        return await self._request("POST", endpoint, params=params, signed=True)
    
    async def cancel_order(self, symbol: str, order_id: Optional[int] = None, orig_client_order_id: Optional[str] = None) -> dict:
        """Cancela ordem"""
        params = {"symbol": symbol}
        
        if order_id:
            params["orderId"] = order_id
        if orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id
        
        endpoint = "/order"
        return await self._request("DELETE", endpoint, params=params, signed=True)
    
    async def get_order(self, symbol: str, order_id: Optional[int] = None, orig_client_order_id: Optional[str] = None) -> dict:
        """Consulta ordem"""
        params = {"symbol": symbol}
        
        if order_id:
            params["orderId"] = order_id
        if orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id
        
        endpoint = "/order"
        return await self._request("GET", endpoint, params=params, signed=True)
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[dict]:
        """Lista ordens abertas"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        endpoint = "/openOrders"
        return await self._request("GET", endpoint, params=params, signed=True)
    
    # --- Futures Specific ---
    
    async def set_leverage(self, symbol: str, leverage: int) -> dict:
        """Define leverage (Futures)"""
        if not settings.is_futures:
            raise ValueError("set_leverage only available for Futures")
        
        params = {
            "symbol": symbol,
            "leverage": leverage
        }
        
        return await self._request("POST", "/leverage", params=params, signed=True)
    
    async def get_position(self, symbol: Optional[str] = None) -> List[dict]:
        """Retorna posições (Futures)"""
        if not settings.is_futures:
            raise ValueError("get_position only available for Futures")
        
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        # Futures usa /fapi/v2/positionRisk
        url = f"{self.base_url.replace('/fapi/v1', '/fapi/v2')}/positionRisk"
        params = params or {}
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = self.recv_window
        params["signature"] = self._sign(params)
        session = await self._get_session()
        async with session.get(url, params=params, headers=self._get_headers()) as resp:
            resp.raise_for_status()
            return await resp.json()
    
    async def create_take_profit_market(self, symbol: str, side: str, stop_price: float, close_position: bool = True) -> dict:
        """Cria ordem TAKE_PROFIT_MARKET (Futures)"""
        if not settings.is_futures:
            raise ValueError("TAKE_PROFIT_MARKET only available for Futures")
        
        params = {
            "symbol": symbol,
            "side": "SELL" if side == "BUY" else "BUY",
            "type": "TAKE_PROFIT_MARKET",
            "stopPrice": stop_price,
            "closePosition": close_position
        }
        
        return await self._request("POST", "/order", params=params, signed=True)
    
    async def create_stop_market(self, symbol: str, side: str, stop_price: float, close_position: bool = True) -> dict:
        """Cria ordem STOP_MARKET (Futures)"""
        if not settings.is_futures:
            raise ValueError("STOP_MARKET only available for Futures")
        
        params = {
            "symbol": symbol,
            "side": "SELL" if side == "BUY" else "BUY",
            "type": "STOP_MARKET",
            "stopPrice": stop_price,
            "closePosition": close_position
        }
        
        return await self._request("POST", "/order", params=params, signed=True)

