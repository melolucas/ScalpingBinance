"""
Configurações do bot de scalping
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Binance API
    API_KEY = os.getenv('BINANCE_API_KEY', '')
    API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    
    # Trading Mode
    TRADING_MODE = os.getenv('TRADING_MODE', 'SPOT')  # SPOT ou FUTURES
    BASE_CURRENCY = os.getenv('BASE_CURRENCY', 'USDT')
    
    # Market Scanner
    MIN_VOLUME_24H = float(os.getenv('MIN_VOLUME_24H', '30000000'))
    MIN_PRICE = float(os.getenv('MIN_PRICE', '0.01'))
    MIN_VOLATILITY = float(os.getenv('MIN_VOLATILITY', '0.3'))  # Volatilidade mínima em %
    MAX_PAIRS = int(os.getenv('MAX_PAIRS', '3'))
    
    # Stablecoins para excluir (não servem para scalping)
    EXCLUDED_SYMBOLS = ['USDCUSDT', 'BUSDUSDT', 'TUSDUSDT', 'USDPUSDT', 'FDUSDUSDT']
    
    # Strategy
    TIMEFRAME_ENTRY = os.getenv('TIMEFRAME_ENTRY', '1m')
    TIMEFRAME_TREND = os.getenv('TIMEFRAME_TREND', '5m')
    EMA_FAST = int(os.getenv('EMA_FAST', '9'))
    EMA_SLOW = int(os.getenv('EMA_SLOW', '21'))
    VOLUME_PERIOD = int(os.getenv('VOLUME_PERIOD', '20'))
    
    # Risk Management
    TAKE_PROFIT_PCT = float(os.getenv('TAKE_PROFIT_PCT', '0.5'))
    STOP_LOSS_PCT = float(os.getenv('STOP_LOSS_PCT', '0.4'))
    MAX_SPREAD_PCT = float(os.getenv('MAX_SPREAD_PCT', '0.1'))
    MAX_SLIPPAGE_PCT = float(os.getenv('MAX_SLIPPAGE_PCT', '0.05'))
    
    # Position Management
    MAX_POSITIONS_PER_PAIR = int(os.getenv('MAX_POSITIONS_PER_PAIR', '1'))
    MAX_TOTAL_POSITIONS = int(os.getenv('MAX_TOTAL_POSITIONS', '3'))
    
    # Logging
    LOG_TO_CSV = os.getenv('LOG_TO_CSV', 'true').lower() == 'true'
    LOG_TO_DB = os.getenv('LOG_TO_DB', 'true').lower() == 'true'
    LOG_FILE = os.getenv('LOG_FILE', 'trades_log.csv')
    DB_FILE = os.getenv('DB_FILE', 'trades.db')
    
    # Proxy e Firewall
    USE_PROXY = os.getenv('USE_PROXY', 'false').lower() == 'true'
    PROXY_HOST = os.getenv('PROXY_HOST', '')
    PROXY_PORT = os.getenv('PROXY_PORT', '')
    PROXY_USER = os.getenv('PROXY_USER', '')
    PROXY_PASS = os.getenv('PROXY_PASS', '')
    
    # Fallback: usar polling se WebSocket falhar
    USE_WEBSOCKET = os.getenv('USE_WEBSOCKET', 'true').lower() == 'true'
    POLLING_INTERVAL = int(os.getenv('POLLING_INTERVAL', '5'))  # Segundos entre polls

