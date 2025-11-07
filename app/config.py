"""Configuração centralizada via Pydantic"""
import os
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações do bot carregadas do .env"""
    
    # Autenticação
    binance_api_key: str = Field(alias="BINANCE_API_KEY", default="")
    binance_api_secret: str = Field(alias="BINANCE_API_SECRET", default="")
    mode: Literal["SPOT", "FUTURES"] = Field(alias="MODE", default="SPOT")
    use_testnet: bool = Field(alias="USE_TESTNET", default=True)
    
    # Endpoints (preenchidos automaticamente)
    binance_base_url: str = Field(alias="BINANCE_BASE_URL", default="")
    binance_ws_url: str = Field(alias="BINANCE_WS_URL", default="")
    binance_fapi_url: str = Field(alias="BINANCE_FAPI_URL", default="")
    binance_fws_url: str = Field(alias="BINANCE_FWS_URL", default="")
    
    # Risco & Concorrência
    top_n: int = Field(alias="TOP_N", default=15)
    max_positions: int = Field(alias="MAX_POSITIONS", default=5)
    capital_per_trade: float = Field(alias="CAPITAL_PER_TRADE", default=0.10)
    leverage: int = Field(alias="LEVERAGE", default=1)
    cooldown_minutes: int = Field(alias="COOLDOWN_MINUTES", default=10)
    
    # Filtros de Elegibilidade
    min_volume_usdt: float = Field(alias="MIN_VOLUME_USDT", default=10000000.0)
    min_futures_volume_usdt: float = Field(alias="MIN_FUTURES_VOLUME_USDT", default=200000000.0)
    max_spread_percent: float = Field(alias="MAX_SPREAD_PERCENT", default=0.001)
    min_volatility_percent: float = Field(alias="MIN_VOLATILITY_PERCENT", default=0.002)
    min_daily_change_percent: float = Field(alias="MIN_DAILY_CHANGE_PERCENT", default=0.015)
    
    # Estratégia
    take_profit_percent: float = Field(alias="TAKE_PROFIT_PERCENT", default=0.03)
    stop_loss_percent: float = Field(alias="STOP_LOSS_PERCENT", default=0.015)
    trailing_start_percent: float = Field(alias="TRAILING_START_PERCENT", default=0.015)
    trailing_step_percent: float = Field(alias="TRAILING_STEP_PERCENT", default=0.005)
    
    # Streams / Rede
    rank_refresh_interval_min: int = Field(alias="RANK_REFRESH_INTERVAL_MIN", default=15)
    ping_interval: int = Field(alias="PING_INTERVAL", default=1800)
    recv_window: int = Field(alias="RECV_WINDOW", default=5000)
    
    # Logs
    log_path: str = Field(alias="LOG_PATH", default="./logs")
    trade_history_file: str = Field(alias="TRADE_HISTORY_FILE", default="./logs/trades.json")
    daily_stats_file: str = Field(alias="DAILY_STATS_FILE", default="./logs/daily_stats.json")
    
    # Banca
    base_asset: str = Field(alias="BASE_ASSET", default="USDT")
    starting_bankroll: float = Field(alias="STARTING_BANKROLL", default=100.0)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup_endpoints()
    
    def _setup_endpoints(self):
        """Preenche endpoints automaticamente baseado em MODE e USE_TESTNET"""
        if self.mode == "SPOT":
            if self.use_testnet:
                self.binance_base_url = self.binance_base_url or "https://testnet.binance.vision/api/v3"
                self.binance_ws_url = self.binance_ws_url or "wss://testnet.binance.vision/ws"
            else:
                self.binance_base_url = self.binance_base_url or "https://api.binance.com/api/v3"
                self.binance_ws_url = self.binance_ws_url or "wss://stream.binance.com:9443/ws"
        else:  # FUTURES
            if self.use_testnet:
                self.binance_base_url = self.binance_base_url or "https://testnet.binancefuture.com/fapi/v1"
                self.binance_fapi_url = self.binance_fapi_url or "https://testnet.binancefuture.com/fapi/v1"
                self.binance_fws_url = self.binance_fws_url or "wss://stream.binancefuture.com/ws"
            else:
                self.binance_base_url = self.binance_base_url or "https://fapi.binance.com/fapi/v1"
                self.binance_fapi_url = self.binance_fapi_url or "https://fapi.binance.com/fapi/v1"
                self.binance_fws_url = self.binance_fws_url or "wss://fstream.binance.com/ws"
    
    @property
    def is_spot(self) -> bool:
        """Retorna True se modo é SPOT"""
        return self.mode == "SPOT"
    
    @property
    def is_futures(self) -> bool:
        """Retorna True se modo é FUTURES"""
        return self.mode == "FUTURES"
    
    @property
    def rest_url(self) -> str:
        """Retorna URL REST apropriada"""
        if self.is_spot:
            return self.binance_base_url
        return self.binance_fapi_url
    
    @property
    def ws_public_url(self) -> str:
        """Retorna URL WebSocket público apropriada"""
        if self.is_spot:
            return self.binance_ws_url
        return self.binance_fws_url
    
    @property
    def min_volume(self) -> float:
        """Retorna volume mínimo baseado no modo"""
        if self.is_spot:
            return self.min_volume_usdt
        return self.min_futures_volume_usdt


# Instância global
settings = Settings()

