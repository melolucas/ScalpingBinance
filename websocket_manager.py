"""
Gerenciador de WebSocket para candles em tempo real
Usa websocket-client diretamente para maior compatibilidade
Suporta proxy e fallback para polling
"""
from binance.client import Client
import websocket
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Callable
import threading
import time
from config import Config
from status_logger import status_logger

class WebSocketManager:
    def __init__(self, client: Client):
        self.client = client
        self.ws_connections = []
        self.connected_symbols = set()  # Rastreia símbolos já conectados
        self.candles_1m: Dict[str, pd.DataFrame] = {}
        self.candles_5m: Dict[str, pd.DataFrame] = {}
        self.callbacks: Dict[str, Callable] = {}
        self.lock = threading.Lock()
        self.running = False
        self.use_polling = False  # Fallback para polling se WebSocket falhar
        self.polling_threads = []
        
    def initialize_candles(self, symbols: list):
        """Inicializa candles históricos para cada símbolo"""
        status_logger.print("📈 Carregando candles históricos...")
        
        total = len(symbols)
        for idx, symbol in enumerate(symbols, 1):
            try:
                status_logger.update(f"Carregando {symbol}... ({idx}/{total})")
                
                # Carrega candles 1m
                klines_1m = self.client.get_klines(
                    symbol=symbol,
                    interval='1m',
                    limit=100
                )
                
                df_1m = pd.DataFrame(klines_1m, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                df_1m['close'] = df_1m['close'].astype(float)
                df_1m['volume'] = df_1m['volume'].astype(float)
                df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'], unit='ms')
                
                # Carrega candles 5m
                klines_5m = self.client.get_klines(
                    symbol=symbol,
                    interval='5m',
                    limit=100
                )
                
                df_5m = pd.DataFrame(klines_5m, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                df_5m['close'] = df_5m['close'].astype(float)
                df_5m['volume'] = df_5m['volume'].astype(float)
                df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'], unit='ms')
                
                with self.lock:
                    self.candles_1m[symbol] = df_1m
                    self.candles_5m[symbol] = df_5m
                
                status_logger.print(f"  ✓ {symbol} - {len(df_1m)} candles 1m, {len(df_5m)} candles 5m")
                
            except Exception as e:
                status_logger.print(f"  ✗ Erro ao carregar {symbol}: {e}")
    
    def process_candle_update(self, symbol: str, interval: str, kline_data: dict):
        """Processa atualização de candle via WebSocket"""
        try:
            if not kline_data.get('x', False):  # Candle ainda não fechou
                return
            
            candle_data = {
                'timestamp': pd.to_datetime(kline_data['t'], unit='ms'),
                'open': float(kline_data['o']),
                'high': float(kline_data['h']),
                'low': float(kline_data['l']),
                'close': float(kline_data['c']),
                'volume': float(kline_data['v'])
            }
            
            with self.lock:
                if interval == '1m':
                    df = self.candles_1m.get(symbol)
                    if df is not None:
                        # Remove último candle (pode estar incompleto) e adiciona novo
                        df = df.iloc[:-1] if len(df) > 0 else df
                        new_row = pd.DataFrame([candle_data])
                        df = pd.concat([df, new_row], ignore_index=True)
                        # Mantém apenas últimos 100 candles
                        df = df.tail(100).reset_index(drop=True)
                        self.candles_1m[symbol] = df
                        
                elif interval == '5m':
                    df = self.candles_5m.get(symbol)
                    if df is not None:
                        df = df.iloc[:-1] if len(df) > 0 else df
                        new_row = pd.DataFrame([candle_data])
                        df = pd.concat([df, new_row], ignore_index=True)
                        df = df.tail(100).reset_index(drop=True)
                        self.candles_5m[symbol] = df
            
            # Chama callback se existir
            if symbol in self.callbacks:
                self.callbacks[symbol](symbol, interval)
                
        except Exception as e:
            print(f"Erro ao processar candle de {symbol}: {e}")
    
    def _create_message_handler(self, symbol: str, interval: str):
        """Cria handler de mensagens para um símbolo e intervalo específicos"""
        def handler(ws, message):
            try:
                data = json.loads(message)
                if 'k' in data:
                    self.process_candle_update(symbol, interval, data['k'])
            except Exception as e:
                print(f"Erro ao processar mensagem WebSocket: {e}")
        return handler
    
    def _on_error(self, ws, error, symbol: str = None):
        """Handler de erros WebSocket"""
        # Se for erro de conexão (firewall/proxy), ativa fallback
        error_str = str(error)
        if symbol and ('10060' in error_str or 'timed out' in error_str.lower() or 'connection' in error_str.lower()):
            if not self.use_polling:
                status_logger.print(f"🔄 Firewall bloqueando WebSocket. Ativando modo polling para {symbol}...")
                self.use_polling = True
                if symbol in self.callbacks:
                    self._start_polling_fallback([symbol], self.callbacks[symbol])
        elif symbol:
            # Outros erros: tenta reconectar após 5 segundos
            threading.Timer(5.0, lambda: self._reconnect_symbol(symbol)).start()
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handler de fechamento WebSocket"""
        print("🔌 WebSocket fechado")
    
    def _on_open(self, ws):
        """Handler de abertura WebSocket"""
        pass
    
    def start_streams(self, symbols: list, callback: Callable):
        """Inicia streams WebSocket para todos os símbolos"""
        # Filtra símbolos já conectados
        new_symbols = [s for s in symbols if s not in self.connected_symbols]
        
        if not new_symbols:
            return  # Todos já estão conectados
        
        status_logger.print("🔌 Conectando WebSockets...")
        
        self.running = True
        
        total = len(new_symbols)
        for idx, symbol in enumerate(new_symbols, 1):
            status_logger.update(f"Conectando WebSocket {symbol}... ({idx}/{total})")
            
            # Marca como conectado antes de tentar (evita duplicatas)
            self.connected_symbols.add(symbol)
            self.callbacks[symbol] = callback
            
            try:
                # Configura proxy se necessário
                http_proxy = None
                if Config.USE_PROXY and Config.PROXY_HOST:
                    if Config.PROXY_USER:
                        http_proxy = f"http://{Config.PROXY_USER}:{Config.PROXY_PASS}@{Config.PROXY_HOST}:{Config.PROXY_PORT}"
                    else:
                        http_proxy = f"http://{Config.PROXY_HOST}:{Config.PROXY_PORT}"
                
                # Stream 1m
                stream_url_1m = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@kline_1m"
                ws_1m = websocket.WebSocketApp(
                    stream_url_1m,
                    on_message=self._create_message_handler(symbol, '1m'),
                    on_error=lambda ws, err: self._on_error(ws, err, symbol),
                    on_close=self._on_close,
                    on_open=self._on_open,
                    http_proxy_host=Config.PROXY_HOST if Config.USE_PROXY else None,
                    http_proxy_port=int(Config.PROXY_PORT) if Config.USE_PROXY and Config.PROXY_PORT else None,
                    http_proxy_auth=(Config.PROXY_USER, Config.PROXY_PASS) if Config.USE_PROXY and Config.PROXY_USER else None
                )
                
                # Stream 5m
                stream_url_5m = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@kline_5m"
                ws_5m = websocket.WebSocketApp(
                    stream_url_5m,
                    on_message=self._create_message_handler(symbol, '5m'),
                    on_error=lambda ws, err: self._on_error(ws, err, symbol),
                    on_close=self._on_close,
                    on_open=self._on_open,
                    http_proxy_host=Config.PROXY_HOST if Config.USE_PROXY else None,
                    http_proxy_port=int(Config.PROXY_PORT) if Config.USE_PROXY and Config.PROXY_PORT else None,
                    http_proxy_auth=(Config.PROXY_USER, Config.PROXY_PASS) if Config.USE_PROXY and Config.PROXY_USER else None
                )
                
                # Inicia WebSockets em threads separadas
                thread_1m = threading.Thread(target=ws_1m.run_forever, daemon=True)
                thread_5m = threading.Thread(target=ws_5m.run_forever, daemon=True)
                
                thread_1m.start()
                thread_5m.start()
                
                self.ws_connections.append((ws_1m, thread_1m, symbol))
                self.ws_connections.append((ws_5m, thread_5m, symbol))
            except Exception as e:
                status_logger.print(f"⚠️ Erro ao conectar WebSocket para {symbol}: {e}")
                self.connected_symbols.discard(symbol)  # Remove se falhou
                
                # Se WebSocket falhar e não estiver usando polling, tenta ativar fallback
                if not self.use_polling and Config.USE_WEBSOCKET:
                    status_logger.print(f"🔄 Tentando modo fallback (polling) para {symbol}...")
                    self._start_polling_fallback([symbol], callback)
        
        status_logger.clear()
        status_logger.print(f"✅ WebSockets conectados para {len(new_symbols)} par(es)")
    
    def get_candles(self, symbol: str, interval: str) -> pd.DataFrame:
        """Retorna candles do símbolo e intervalo especificados"""
        with self.lock:
            if interval == '1m':
                return self.candles_1m.get(symbol, pd.DataFrame())
            elif interval == '5m':
                return self.candles_5m.get(symbol, pd.DataFrame())
            return pd.DataFrame()
    
    def _reconnect_symbol(self, symbol: str):
        """Reconecta WebSocket de um símbolo específico"""
        if symbol not in self.callbacks:
            return
        
        try:
            # Remove das conexões antigas e marca como desconectado
            self.ws_connections = [(ws, t, s) for ws, t, s in self.ws_connections if s != symbol]
            self.connected_symbols.discard(symbol)
            
            # Reconecta após um pequeno delay
            callback = self.callbacks[symbol]
            threading.Timer(2.0, lambda: self.start_streams([symbol], callback)).start()
        except:
            pass
    
    def _start_polling_fallback(self, symbols: list, callback: Callable):
        """Modo fallback: usa polling via API REST quando WebSocket falha"""
        status_logger.print("📡 Modo Polling ativado (WebSocket bloqueado pelo firewall)")
        
        def poll_candles(symbol: str, interval: str):
            """Poll candles via API REST"""
            last_update = {}
            while self.running:
                try:
                    klines = self.client.get_klines(
                        symbol=symbol,
                        interval=interval,
                        limit=1
                    )
                    
                    if klines:
                        kline = klines[0]
                        kline_id = f"{kline[0]}_{interval}"  # timestamp + interval como ID
                        
                        # Só processa se for novo
                        if kline_id != last_update.get(symbol + interval):
                            last_update[symbol + interval] = kline_id
                            
                            # Simula formato WebSocket
                            kline_data = {
                                't': int(kline[0]),  # timestamp
                                'o': kline[1],  # open
                                'h': kline[2],  # high
                                'l': kline[3],  # low
                                'c': kline[4],  # close
                                'v': kline[5],  # volume
                                'x': True  # candle fechado
                            }
                            
                            self.process_candle_update(symbol, interval, kline_data)
                    
                    time.sleep(Config.POLLING_INTERVAL)
                except Exception as e:
                    status_logger.print(f"⚠️ Erro no polling de {symbol}: {e}")
                    time.sleep(Config.POLLING_INTERVAL * 2)
        
        # Inicia threads de polling para cada símbolo e intervalo
        for symbol in symbols:
            thread_1m = threading.Thread(target=poll_candles, args=(symbol, '1m'), daemon=True)
            thread_5m = threading.Thread(target=poll_candles, args=(symbol, '5m'), daemon=True)
            thread_1m.start()
            thread_5m.start()
            self.polling_threads.append((thread_1m, thread_5m, symbol))
    
    def stop(self):
        """Para os streams WebSocket e polling"""
        self.running = False
        for ws, thread, symbol in self.ws_connections:
            try:
                ws.close()
            except:
                pass
        self.ws_connections.clear()
        self.connected_symbols.clear()
        self.polling_threads.clear()
        status_logger.print("🔌 Conexões desconectadas")

