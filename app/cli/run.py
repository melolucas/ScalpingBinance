"""Comandos CLI"""
import asyncio
import argparse
import sys
from datetime import datetime
from typing import Optional
from app.config import settings
from app.adapters.binance.rest import BinanceREST
from app.adapters.binance.symbols import SymbolCache
from app.adapters.binance.ws_public import BinanceWSPublic
from app.adapters.binance.ws_private import BinanceWSPrivate
from app.data.ranker import SymbolRanker
from app.data.store import TradeStore
from app.core.fsm import SymbolFSM, State
from app.core.risk import RiskManager
from app.core.executor import OrderExecutor
from app.core.context import MarketContext
from app.core.scheduler import Scheduler
from app.strategies.basic_pullback import BasicPullbackStrategy
from app.utils.json_logger import get_logger
from app.utils.time import now_utc

logger = get_logger()


class Bot:
    """Bot principal"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.rest = BinanceREST()
        self.symbol_cache = SymbolCache(self.rest)
        self.ranker = SymbolRanker(self.rest)
        self.store = TradeStore()
        self.risk = RiskManager()
        self.executor = OrderExecutor(self.rest, self.symbol_cache, self.risk, dry_run)
        self.strategy = BasicPullbackStrategy()
        self.scheduler = Scheduler()
        
        # Estado por símbolo
        self.symbol_fsms: dict[str, SymbolFSM] = {}
        self.symbol_contexts: dict[str, MarketContext] = {}
        self.active_symbols: list[str] = []
        
        # WebSockets
        self.ws_public: Optional[BinanceWSPublic] = None
        self.ws_private: Optional[BinanceWSPrivate] = None
        
        # Estado global
        self.running = False
        self.bankroll = settings.starting_bankroll
    
    async def initialize(self):
        """Inicializa bot"""
        logger.info("bot_initializing", dry_run=self.dry_run)
        
        # Atualizar cache de símbolos
        await self.symbol_cache._ensure_updated()
        
        # Buscar ranking inicial
        await self._refresh_ranking()
        
        # Inicializar WebSockets
        await self._setup_websockets()
        
        # Configurar scheduler
        self.scheduler.schedule_periodic(
            self._refresh_ranking,
            settings.rank_refresh_interval_min * 60,
            "rank_refresh"
        )
        
        self.scheduler.schedule_periodic(
            self._reconcile_all,
            300,  # 5 minutos
            "reconcile"
        )
        
        # Polling periódico para klines (fallback se WebSocket falhar)
        self.scheduler.schedule_periodic(
            self._poll_klines,
            60,  # 1 minuto
            "poll_klines"
        )
        
        self.scheduler.start()
        
        logger.info("bot_initialized")
    
    async def _refresh_ranking(self):
        """Atualiza ranking de símbolos"""
        try:
            eligible = await self.ranker.get_eligible_symbols()
            symbols = [s.symbol for s in eligible[:settings.top_n]]
            
            # Atualizar lista ativa
            self.active_symbols = symbols
            
            # Inicializar FSM e contextos para novos símbolos
            for symbol in symbols:
                if symbol not in self.symbol_fsms:
                    self.symbol_fsms[symbol] = SymbolFSM(symbol)
                    self.symbol_contexts[symbol] = MarketContext(symbol)
            
            logger.info("ranking_refreshed", symbols=symbols, count=len(symbols))
            
            # Reconectar WS público se símbolos mudaram
            if self.ws_public:
                await self.ws_public.disconnect()
                await self._setup_websockets()
        
        except Exception as e:
            logger.error("ranking_refresh_failed", error=str(e))
    
    async def _setup_websockets(self):
        """Configura WebSockets"""
        if not self.active_symbols:
            return
        
        # WS Público (pode falhar no testnet)
        try:
            self.ws_public = BinanceWSPublic(
                symbols=self.active_symbols,
                on_candle=self._on_candle,
                on_trade=self._on_trade
            )
            # Conectar WS público (em background)
            asyncio.create_task(self.ws_public.connect())
        except Exception as e:
            logger.warning("ws_public_setup_failed", error=str(e))
            logger.warning("bot_will_use_polling", 
                         note="Bot usará polling periódico para buscar dados de mercado")
        
        # WS Privado (opcional - pode falhar se API key não tiver permissões)
        try:
            self.ws_private = BinanceWSPrivate(
                on_order_update=self._on_order_update,
                on_account_update=self._on_account_update
            )
            # Conectar (em background)
            asyncio.create_task(self.ws_private.connect())
        except Exception as e:
            logger.warning("ws_private_setup_failed", error=str(e))
            logger.warning("bot_will_continue_without_private_ws", 
                         note="Bot continuará funcionando, mas não receberá atualizações de ordens em tempo real")
    
    async def _on_candle(self, candle: dict):
        """Handler de candle"""
        symbol = candle.get("symbol")
        if symbol not in self.symbol_contexts:
            return
        
        context = self.symbol_contexts[symbol]
        interval = "1m" if candle.get("close_time") - candle.get("open_time") < 120000 else "5m"
        context.update_candle(candle, interval)
        
        # Verificar entrada
        await self._check_entry(symbol, context)
        
        # Verificar saída
        await self._check_exit(symbol, context)
    
    async def _on_trade(self, trade: dict):
        """Handler de trade"""
        # Usar para atualizar spread se necessário
        pass
    
    async def _on_order_update(self, order_update: dict):
        """Handler de atualização de ordem"""
        symbol = order_update.get("symbol")
        status = order_update.get("status")
        client_order_id = order_update.get("client_order_id")
        
        if symbol not in self.symbol_fsms:
            return
        
        fsm = self.symbol_fsms[symbol]
        
        if status == "FILLED" and fsm.state == State.BUYING:
            # Entrada preenchida
            entry_price = order_update.get("price", 0)
            qty = order_update.get("executed_qty", 0)
            
            position = {
                "entry_price": entry_price,
                "qty": qty,
                "entry_time": now_utc().isoformat()
            }
            
            fsm.enter_position(position)
            self.risk.register_position(symbol)
        
        elif status in ["CANCELED", "REJECTED", "EXPIRED"]:
            # Ordem cancelada/rejeitada
            fsm.reset_to_idle()
    
    async def _on_account_update(self, data: dict):
        """Handler de atualização de conta"""
        # Atualizar bankroll se necessário
        pass
    
    async def _check_entry(self, symbol: str, context: MarketContext):
        """Verifica se deve entrar"""
        fsm = self.symbol_fsms.get(symbol)
        if not fsm or not fsm.can_enter():
            return
        
        # Verificar risco
        can_open, reason = self.risk.can_open_position(symbol)
        if not can_open:
            return
        
        # Verificar estratégia
        should_enter, signal_data = self.strategy.should_enter(context)
        if not should_enter:
            return
        
        # Calcular tamanho da posição
        entry_price = context.get_current_price()
        qty = self.risk.calculate_position_size(self.bankroll, entry_price)
        
        # Calcular TP/SL
        tp_price, sl_price = self.strategy.calculate_tp_sl(context, entry_price)
        
        # Criar ordem
        success, order, error = await self.executor.enter_long(
            symbol=symbol,
            entry_price=entry_price,
            qty=qty,
            tp_price=tp_price,
            sl_price=sl_price
        )
        
        if success:
            order_id = order.get("orderId") if order else signal_data.get("entry_price")
            fsm.start_buying(str(order_id))
            logger.info("entry_attempted", symbol=symbol, price=entry_price, qty=qty)
        else:
            logger.warning("entry_failed", symbol=symbol, error=error)
    
    async def _check_exit(self, symbol: str, context: MarketContext):
        """Verifica se deve sair"""
        fsm = self.symbol_fsms.get(symbol)
        if not fsm or not fsm.is_in_position():
            return
        
        position = fsm.position
        if not position:
            return
        
        entry_price = position.get("entry_price", 0)
        current_price = context.get_current_price()
        
        # Verificar estratégia
        should_exit, reason = self.strategy.should_exit(context, entry_price, current_price)
        
        if should_exit:
            # Sair
            success, order, error = await self.executor.exit_position(symbol, current_price, reason)
            
            if success:
                # Calcular PnL
                pnl_pct = ((current_price - entry_price) / entry_price) * 100.0
                
                # Registrar trade
                from app.data.schemas import TradeSchema
                trade = TradeSchema(
                    ts_open=position.get("entry_time", now_utc().isoformat()),
                    ts_close=now_utc().isoformat(),
                    symbol=symbol,
                    side="BUY",
                    qty=position.get("qty", 0),
                    entry_price=entry_price,
                    exit_price=current_price,
                    pnl_pct_net=pnl_pct,
                    spread_entry=context.spread_pct,
                    atr_pct_entry=context.get_atr_percent(),
                    signal_ctx={},
                    result="WIN" if pnl_pct > 0 else "LOSS" if pnl_pct < 0 else "BREAKEVEN"
                )
                
                self.store.save_trade(trade)
                
                # Atualizar risco
                self.risk.register_position_closed(symbol, pnl_pct)
                
                # Atualizar bankroll
                self.bankroll *= (1 + pnl_pct / 100.0)
                
                # Sair de posição
                fsm.exit_position()
                
                logger.info("position_exited", symbol=symbol, pnl_pct=pnl_pct, reason=reason)
    
    async def _reconcile_all(self):
        """Reconcilia todas as posições"""
        # Reconciliar apenas símbolos com posições ativas
        for symbol in list(self.symbol_fsms.keys()):
            if symbol in self.active_symbols:
                try:
                    await self.executor.reconcile(symbol)
                except Exception as e:
                    # Erro 400 é esperado para símbolos sem ordens
                    if "400" not in str(e):
                        logger.error("reconcile_failed", symbol=symbol, error=str(e))
    
    async def _poll_klines(self):
        """Polling periódico de klines (fallback se WebSocket falhar)"""
        # Verificar se WebSocket está conectado
        ws_connected = False
        if self.ws_public and hasattr(self.ws_public, 'ws') and self.ws_public.ws:
            try:
                ws_connected = not self.ws_public.ws.closed
            except:
                ws_connected = False
        
        if ws_connected:
            logger.debug("poll_klines_skipped", reason="WebSocket está conectado")
            return  # WebSocket está conectado, não precisa de polling
        
        logger.info("poll_klines_starting", symbols_count=len(self.active_symbols[:5]), symbols=self.active_symbols[:5])
        
        # Buscar klines para símbolos ativos
        for symbol in self.active_symbols[:5]:  # Limitar a 5 símbolos por vez
            try:
                # Buscar klines 1m (últimos 20)
                klines = await self.rest.get_klines(symbol, interval="1m", limit=20)
                
                if klines and symbol in self.symbol_contexts:
                    context = self.symbol_contexts[symbol]
                    
                    # Processar klines
                    processed = 0
                    for kline in klines[-5:]:  # Últimos 5 candles
                        candle = {
                            "symbol": symbol,
                            "open_time": int(kline[0]),
                            "close_time": int(kline[6]),
                            "open": float(kline[1]),
                            "high": float(kline[2]),
                            "low": float(kline[3]),
                            "close": float(kline[4]),
                            "volume": float(kline[5]),
                            "quote_volume": float(kline[7]),
                            "trades": int(kline[8]),
                            "is_closed": True
                        }
                        context.update_candle(candle, "1m")
                        processed += 1
                    
                    logger.info("poll_klines_processed", symbol=symbol, candles=processed)
                    
                    # Verificar entrada/saída
                    await self._check_entry(symbol, context)
                    await self._check_exit(symbol, context)
                else:
                    logger.debug("poll_klines_no_data", symbol=symbol, has_klines=bool(klines), has_context=symbol in self.symbol_contexts)
            
            except Exception as e:
                logger.debug("poll_klines_failed", symbol=symbol, error=str(e))
    
    async def run(self):
        """Roda bot"""
        self.running = True
        
        try:
            await self.initialize()
            
            logger.info("bot_running")
            
            # Manter rodando
            while self.running:
                await asyncio.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("bot_stopping")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Encerra bot"""
        self.running = False
        
        if self.ws_public:
            await self.ws_public.disconnect()
        
        if self.ws_private:
            await self.ws_private.disconnect()
        
        self.scheduler.stop()
        await self.rest.close()
        
        logger.info("bot_shutdown")


async def cmd_run(dry_run: bool = False):
    """Comando: run"""
    bot = Bot(dry_run=dry_run)
    await bot.run()


async def cmd_stats():
    """Comando: stats"""
    from app.data.store import TradeStore
    from datetime import datetime
    
    store = TradeStore()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    stats = store.compute_daily_stats(today)
    
    print(f"\n=== Estatísticas do Dia ({today}) ===")
    print(f"Operações: {stats.ops}")
    print(f"Winrate: {stats.winrate:.2f}%")
    print(f"PnL Bruto: {stats.gross_pnl:.2f}%")
    print(f"PnL Líquido: {stats.net_pnl:.2f}%")
    print(f"Max Drawdown: {stats.max_dd:.2f}%")
    print(f"Melhores símbolos: {', '.join(stats.best_symbols)}")
    print(f"Piores símbolos: {', '.join(stats.worst_symbols)}")
    print()


async def cmd_rank():
    """Comando: rank"""
    rest = BinanceREST()
    ranker = SymbolRanker(rest)
    
    eligible = await ranker.get_eligible_symbols()
    
    print(f"\n=== Top {settings.top_n} Símbolos Elegíveis ===\n")
    for i, symbol_data in enumerate(eligible[:settings.top_n], 1):
        print(f"{i}. {symbol_data.symbol}")
        print(f"   Score: {symbol_data.score:.4f}")
        print(f"   Volume 24h: ${symbol_data.quote_volume:,.0f}")
        print(f"   ATR%: {symbol_data.atr_percent*100:.3f}%")
        print(f"   Spread: {symbol_data.spread_percent*100:.3f}%")
        print(f"   Variação 24h: {symbol_data.price_change_percent:.2f}%")
        print()
    
    await rest.close()


async def cmd_replay(symbol: str, date: str):
    """Comando: replay"""
    from app.data.store import TradeStore
    
    store = TradeStore()
    trades = store.get_trades(symbol=symbol, date=date)
    
    print(f"\n=== Replay: {symbol} - {date} ===\n")
    print(f"Total de trades: {len(trades)}\n")
    
    for i, trade in enumerate(trades, 1):
        print(f"Trade {i}:")
        print(f"  Entrada: {trade.get('entry_price')} @ {trade.get('ts_open')}")
        print(f"  Saída: {trade.get('exit_price')} @ {trade.get('ts_close')}")
        print(f"  PnL: {trade.get('pnl_pct_net', 0):.2f}%")
        print(f"  Resultado: {trade.get('result')}")
        print()


def main():
    """Entrypoint CLI"""
    parser = argparse.ArgumentParser(description="Binance Micro-Profit Bot")
    subparsers = parser.add_subparsers(dest="command", help="Comandos")
    
    # Comando: run
    run_parser = subparsers.add_parser("run", help="Roda o bot")
    run_parser.add_argument("--dry-run", action="store_true", help="Modo simulação")
    
    # Comando: stats
    subparsers.add_parser("stats", help="Mostra estatísticas")
    
    # Comando: rank
    subparsers.add_parser("rank", help="Mostra ranking de símbolos")
    
    # Comando: replay
    replay_parser = subparsers.add_parser("replay", help="Replay de trades")
    replay_parser.add_argument("--symbol", required=True, help="Símbolo")
    replay_parser.add_argument("--date", required=True, help="Data (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    if args.command == "run":
        asyncio.run(cmd_run(dry_run=args.dry_run))
    elif args.command == "stats":
        asyncio.run(cmd_stats())
    elif args.command == "rank":
        asyncio.run(cmd_rank())
    elif args.command == "replay":
        asyncio.run(cmd_replay(args.symbol, args.date))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

