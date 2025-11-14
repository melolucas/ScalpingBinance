"""
Scanner de mercado - seleciona os top pares mais voláteis
"""
from binance.client import Client
import pandas as pd
from config import Config
from status_logger import status_logger
import threading
from queue import Queue
from typing import List, Dict

class MarketScanner:
    def __init__(self, client: Client):
        self.client = client
        self.base_currency = Config.BASE_CURRENCY
        
    def get_all_symbols(self):
        """Busca todos os pares USDT disponíveis para SPOT trading"""
        exchange_info = self.client.get_exchange_info()
        symbols = []
        
        for symbol_info in exchange_info['symbols']:
            try:
                # Verifica se é par SPOT
                # Na API da Binance, alguns símbolos podem não ter o campo 'type'
                # Se não tiver, assumimos que é SPOT (comportamento padrão)
                symbol_type = symbol_info.get('type', 'SPOT')
                
                # Filtra apenas símbolos SPOT que estão trading
                if (symbol_info.get('quoteAsset') == self.base_currency and
                    symbol_info.get('status') == 'TRADING' and
                    symbol_type == 'SPOT'):
                    symbols.append(symbol_info['symbol'])
            except KeyError as e:
                # Se faltar algum campo obrigatório, pula este símbolo
                continue
        
        return symbols
    
    def calculate_volatility(self, symbol: str, period: int = 24) -> float:
        """Calcula volatilidade do par (desvio padrão dos retornos)"""
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval='1h',
                limit=period
            )
            
            if len(klines) < period:
                return 0.0
            
            closes = [float(k[4]) for k in klines]
            returns = pd.Series(closes).pct_change().dropna()
            
            if len(returns) == 0:
                return 0.0
            
            volatility = returns.std() * 100  # Em percentual
            return volatility
            
        except Exception as e:
            print(f"Erro ao calcular volatilidade de {symbol}: {e}")
            return 0.0
    
    def get_ticker_info(self, symbol: str) -> dict:
        """Busca informações do ticker (volume, preço, spread)"""
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            orderbook = self.client.get_order_book(symbol=symbol, limit=5)
            
            price = float(ticker['lastPrice'])
            volume_24h = float(ticker['quoteVolume'])
            
            # Calcula spread
            if len(orderbook['bids']) > 0 and len(orderbook['asks']) > 0:
                bid = float(orderbook['bids'][0][0])
                ask = float(orderbook['asks'][0][0])
                spread_pct = ((ask - bid) / bid) * 100
            else:
                spread_pct = 999.0
            
            return {
                'symbol': symbol,
                'price': price,
                'volume_24h': volume_24h,
                'spread_pct': spread_pct
            }
            
        except Exception as e:
            print(f"Erro ao buscar info de {symbol}: {e}")
            return None
    
    def _analyze_symbol(self, symbol: str, idx: int, total: int, results_queue: Queue):
        """Analisa um símbolo individual (para threading)"""
        try:
            status_logger.update(f"Analisando {symbol}... ({idx}/{total})")
            
            # Filtra stablecoins e símbolos excluídos
            if symbol in Config.EXCLUDED_SYMBOLS:
                return
            
            info = self.get_ticker_info(symbol)
            
            if not info:
                return
            
            # Filtros básicos
            if info['price'] < Config.MIN_PRICE:
                return
            
            if info['volume_24h'] < Config.MIN_VOLUME_24H:
                return
            
            if info['spread_pct'] > Config.MAX_SPREAD_PCT:
                return
            
            # Calcula volatilidade
            status_logger.update(f"Calculando volatilidade de {symbol}... ({idx}/{total})")
            volatility = self.calculate_volatility(symbol)
            
            # Filtro de volatilidade mínima (importante para scalping)
            if volatility < Config.MIN_VOLATILITY:
                return
            
            if volatility > 0:
                results_queue.put({
                    'symbol': symbol,
                    'price': info['price'],
                    'volume_24h': info['volume_24h'],
                    'spread_pct': info['spread_pct'],
                    'volatility': volatility
                })
        except Exception as e:
            # Ignora erros individuais
            pass
    
    def scan_top_pairs(self, callback=None) -> list:
        """
        Escaneia mercado e retorna top N pares mais voláteis
        que atendem aos critérios
        
        Args:
            callback: Função chamada quando encontra um par válido (symbol, pair_info)
        """
        status_logger.print("🔍 Escaneando mercado...")
        
        status_logger.update("Buscando símbolos disponíveis...")
        symbols = self.get_all_symbols()
        status_logger.print(f"📊 Encontrados {len(symbols)} pares {Config.BASE_CURRENCY}")
        
        valid_pairs = []
        total = len(symbols)
        results_queue = Queue()
        threads = []
        max_threads = 10  # Limite de threads simultâneas
        
        status_logger.update(f"Iniciando análise paralela de {total} pares...")
        
        # Cria threads para análise paralela
        for idx, symbol in enumerate(symbols, 1):
            # Limita número de threads simultâneas
            while threading.active_count() >= max_threads + 1:  # +1 para thread principal
                threading.Event().wait(0.1)
            
            thread = threading.Thread(
                target=self._analyze_symbol,
                args=(symbol, idx, total, results_queue),
                daemon=True
            )
            thread.start()
            threads.append(thread)
            
            # Processa resultados encontrados enquanto analisa
            while not results_queue.empty():
                pair = results_queue.get()
                valid_pairs.append(pair)
                
                # Chama callback se fornecido (para começar a operar imediatamente)
                if callback:
                    callback(pair['symbol'], pair)
        
        # Aguarda todas as threads terminarem
        status_logger.update("Aguardando conclusão da análise...")
        for thread in threads:
            thread.join()
        
        # Processa resultados finais
        while not results_queue.empty():
            pair = results_queue.get()
            valid_pairs.append(pair)
            if callback:
                callback(pair['symbol'], pair)
        
        # Ordena por volatilidade (maior primeiro)
        status_logger.update("Ordenando pares por volatilidade...")
        valid_pairs.sort(key=lambda x: x['volatility'], reverse=True)
        
        # Retorna top N
        top_pairs = valid_pairs[:Config.MAX_PAIRS]
        
        status_logger.clear()
        status_logger.print(f"✅ Top {len(top_pairs)} pares selecionados:")
        for pair in top_pairs:
            status_logger.print(f"  {pair['symbol']} | Vol: ${pair['volume_24h']:,.0f} | Volatilidade: {pair['volatility']:.2f}% | Spread: {pair['spread_pct']:.3f}%")
        
        return [p['symbol'] for p in top_pairs]

