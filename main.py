"""
Bot de Scalping Automático - Main Runner
"""
from binance.client import Client
from market_scanner import MarketScanner
from websocket_manager import WebSocketManager
from strategy import ScalpingStrategy
from trade_executor import TradeExecutor
from logger import TradeLogger
from config import Config
from status_logger import status_logger
import time
import signal
import sys
import threading

class ScalpingBot:
    def __init__(self):
        # Inicializa cliente Binance
        self.client = Client(
            api_key=Config.API_KEY,
            api_secret=Config.API_SECRET,
            testnet=True  # Mude para True em testes
        )
        
        # Módulos
        self.scanner = MarketScanner(self.client)
        self.ws_manager = WebSocketManager(self.client)
        self.strategy = ScalpingStrategy()
        self.executor = TradeExecutor(self.client)
        self.logger = TradeLogger()
        
        # Estado
        self.running = False
        self.selected_symbols = []
        
        # Setup signal handler para shutdown graceful
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Handler para shutdown graceful"""
        print("\n🛑 Parando bot...")
        self.running = False
        self.ws_manager.stop()
        sys.exit(0)
    
    def on_candle_update(self, symbol: str, interval: str):
        """Callback quando candle é atualizado"""
        if interval != Config.TIMEFRAME_ENTRY:  # Só processa candles de entrada
            return
        
        if self.executor.has_active_position(symbol):
            # Já tem posição, só monitora TP/SL
            return
        
        if not self.executor.can_open_position():
            return
        
        # Busca candles
        candles_1m = self.ws_manager.get_candles(symbol, '1m')
        candles_5m = self.ws_manager.get_candles(symbol, '5m')
        
        if candles_1m.empty or candles_5m.empty:
            return
        
        # Verifica sinal de entrada
        signal_info = self.strategy.check_entry_signal(candles_1m, candles_5m)
        
        if signal_info and signal_info['signal'] == 'BUY':
            entry_price = signal_info['price']
            take_profit = self.strategy.calculate_take_profit(entry_price)
            stop_loss = self.strategy.calculate_stop_loss(entry_price)
            
            print(f"\n📊 SINAL DE COMPRA: {symbol}")
            print(f"   Preço: ${entry_price:.8f}")
            print(f"   TP: ${take_profit:.8f} (+{Config.TAKE_PROFIT_PCT}%)")
            print(f"   SL: ${stop_loss:.8f} (-{Config.STOP_LOSS_PCT}%)")
            print(f"   Volume: {signal_info['volume']:.2f} (média: {signal_info['volume_avg']:.2f})")
            
            # Salva sinal no banco (para aprendizado)
            if self.logger.db:
                try:
                    signal_id = self.logger.db.insert_signal({
                        'symbol': symbol,
                        'signal_type': 'BUY',
                        'price': entry_price,
                        'ema_fast': signal_info.get('ema_fast'),
                        'ema_slow': signal_info.get('ema_slow'),
                        'volume': signal_info.get('volume'),
                        'volume_avg': signal_info.get('volume_avg')
                    })
                except Exception as e:
                    print(f"⚠️ Erro ao salvar sinal: {e}")
                    signal_id = None
            else:
                signal_id = None
            
            # Abre posição
            success = self.executor.open_position(
                symbol=symbol,
                entry_price=entry_price,
                take_profit=take_profit,
                stop_loss=stop_loss
            )
            
            if success:
                print(f"✅ Posição aberta em {symbol}")
                
                # Marca sinal como executado
                if self.logger.db and signal_id:
                    try:
                        # Busca o trade_id mais recente deste símbolo
                        recent_trades = self.logger.db.get_trades(limit=1, symbol=symbol)
                        if recent_trades:
                            self.logger.db.mark_signal_executed(signal_id, recent_trades[0]['id'])
                    except Exception as e:
                        print(f"⚠️ Erro ao marcar sinal como executado: {e}")
    
    def monitor_positions(self):
        """Monitora posições abertas e verifica TP/SL"""
        # Busca preços atuais
        current_prices = {}
        
        for symbol in self.selected_symbols:
            try:
                ticker = self.client.get_ticker(symbol=symbol)
                current_prices[symbol] = float(ticker['lastPrice'])
            except:
                continue
        
        # Verifica posições
        closed_trades = self.executor.check_positions(current_prices)
        
        # Registra trades fechados
        for trade in closed_trades:
            self.logger.log_trade(trade)
    
    def print_statistics(self):
        """Imprime estatísticas dos trades"""
        stats = self.logger.get_statistics()
        
        if stats:
            print("\n" + "="*50)
            print("📊 ESTATÍSTICAS")
            print("="*50)
            print(f"Total de trades: {stats['total_trades']}")
            print(f"Trades vencedores: {stats['winning_trades']}")
            print(f"Trades perdedores: {stats['losing_trades']}")
            print(f"Win Rate: {stats['win_rate']:.2f}%")
            print(f"PnL Total: ${stats['total_pnl_usdt']:.2f}")
            print(f"PnL Médio: {stats['avg_pnl_pct']:.2f}%")
            print("="*50 + "\n")
    
    def run(self):
        """Loop principal do bot"""
        print("="*50)
        print("🤖 BOT DE SCALPING INICIADO")
        print("="*50)
        print(f"Modo: {Config.TRADING_MODE}")
        print(f"TP: +{Config.TAKE_PROFIT_PCT}% | SL: -{Config.STOP_LOSS_PCT}%")
        print(f"Timeframes: {Config.TIMEFRAME_ENTRY} (entrada) / {Config.TIMEFRAME_TREND} (tendência)")
        print("="*50 + "\n")
        
        # 1. Escaneia mercado e seleciona top pares (paralelo)
        self.selected_symbols = []
        self.scanning_complete = False
        
        def on_pair_found(symbol: str, pair_info: dict):
            """Callback quando encontra um par válido"""
            if symbol not in self.selected_symbols:
                self.selected_symbols.append(symbol)
                
                # Se é o primeiro par, já inicia a operação
                if len(self.selected_symbols) == 1:
                    status_logger.print(f"🚀 Primeiro par encontrado: {symbol} - Iniciando operação...")
                    self._start_trading_for_symbol(symbol)
                elif len(self.selected_symbols) <= Config.MAX_PAIRS:
                    status_logger.print(f"✅ Par {len(self.selected_symbols)}/{Config.MAX_PAIRS}: {symbol}")
                    self._start_trading_for_symbol(symbol)
        
        # Inicia scan em thread separada
        scan_thread = threading.Thread(
            target=lambda: self.scanner.scan_top_pairs(callback=on_pair_found),
            daemon=True
        )
        scan_thread.start()
        
        # Aguarda pelo menos 1 par ser encontrado
        timeout = 60  # 60 segundos de timeout
        start_time = time.time()
        while len(self.selected_symbols) == 0 and (time.time() - start_time) < timeout:
            time.sleep(0.5)
        
        if not self.selected_symbols:
            status_logger.print("❌ Nenhum par encontrado. Encerrando...")
            return
        
        # Aguarda scan completar (opcional - pode continuar operando enquanto escaneia)
        status_logger.print("⏳ Aguardando conclusão do scan...")
        scan_thread.join(timeout=120)  # Timeout de 2 minutos
        self.scanning_complete = True
        
        # Garante que temos os pares necessários
        if len(self.selected_symbols) < Config.MAX_PAIRS:
            status_logger.print(f"⚠️ Apenas {len(self.selected_symbols)} par(es) encontrado(s) de {Config.MAX_PAIRS} desejados")
        
        # 4. Loop principal
        self.running = True
        last_stats_time = time.time()
        last_status_update = time.time()
        
        status_logger.print("\n🟢 Bot rodando... Aguardando sinais...\n")
        
        try:
            while self.running:
                # Monitora posições a cada 1 segundo
                self.monitor_positions()
                
                # Atualiza status a cada 5 segundos
                if time.time() - last_status_update > 5:
                    active_positions = len(self.executor.active_positions)
                    if active_positions > 0:
                        positions_str = ", ".join(self.executor.active_positions.keys())
                        status_logger.update(f"🟢 Bot ativo | {active_positions} posição(ões) aberta(s): {positions_str} | Aguardando sinais...")
                    else:
                        status_logger.update(f"🟢 Bot ativo | Nenhuma posição aberta | Monitorando {len(self.selected_symbols)} par(es)...")
                    last_status_update = time.time()
                
                # Imprime estatísticas a cada 5 minutos
                if time.time() - last_stats_time > 300:
                    status_logger.clear()
                    self.print_statistics()
                    last_stats_time = time.time()
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            status_logger.clear()
            status_logger.print("\n🛑 Interrompido pelo usuário")
        except Exception as e:
            status_logger.clear()
            status_logger.print(f"\n❌ Erro no loop principal: {e}")
        finally:
            # Fecha todas as posições abertas (opcional - descomente se quiser)
            # for symbol in list(self.executor.active_positions.keys()):
            #     self.executor.close_position(symbol, reason='BOT_STOPPED')
            
            self.ws_manager.stop()
            status_logger.clear()
            self.print_statistics()
            status_logger.print("\n👋 Bot encerrado")
    
    def _start_trading_for_symbol(self, symbol: str):
        """Inicia trading para um símbolo específico"""
        try:
            # Inicializa candles para este símbolo
            self.ws_manager.initialize_candles([symbol])
            
            # Inicia WebSocket para este símbolo
            self.ws_manager.start_streams(
                symbols=[symbol],
                callback=self.on_candle_update
            )
        except Exception as e:
            status_logger.print(f"❌ Erro ao iniciar trading para {symbol}: {e}")

if __name__ == '__main__':
    # Verifica se API keys estão configuradas
    if not Config.API_KEY or not Config.API_SECRET:
        print("❌ ERRO: Configure BINANCE_API_KEY e BINANCE_API_SECRET no arquivo .env")
        sys.exit(1)
    
    bot = ScalpingBot()
    bot.run()

