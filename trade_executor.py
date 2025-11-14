"""
Executor de trades - compra/venda com TP/SL
"""
from binance.client import Client
from binance.exceptions import BinanceAPIException
from typing import Dict, Optional
from datetime import datetime
from config import Config
import time

class TradeExecutor:
    def __init__(self, client: Client):
        self.client = client
        self.trading_mode = Config.TRADING_MODE
        self.active_positions: Dict[str, Dict] = {}
        
    def get_account_balance(self, asset: str = 'USDT') -> float:
        """Retorna saldo disponível"""
        try:
            if self.trading_mode == 'SPOT':
                account = self.client.get_account()
                for balance in account['balances']:
                    if balance['asset'] == asset:
                        return float(balance['free'])
            else:
                # FUTURES
                account = self.client.futures_account()
                for asset_balance in account['assets']:
                    if asset_balance['asset'] == asset:
                        return float(asset_balance['availableBalance'])
            
            return 0.0
        except Exception as e:
            print(f"Erro ao buscar saldo: {e}")
            return 0.0
    
    def has_active_position(self, symbol: str) -> bool:
        """Verifica se já existe posição aberta no símbolo"""
        return symbol in self.active_positions
    
    def can_open_position(self) -> bool:
        """Verifica se pode abrir nova posição"""
        return len(self.active_positions) < Config.MAX_TOTAL_POSITIONS
    
    def buy_market(self, symbol: str, quantity: float) -> Optional[Dict]:
        """
        Executa compra market
        
        Retorna dict com info da ordem ou None em caso de erro
        """
        try:
            if self.trading_mode == 'SPOT':
                order = self.client.order_market_buy(
                    symbol=symbol,
                    quantity=quantity
                )
            else:
                # FUTURES
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side='BUY',
                    type='MARKET',
                    quantity=quantity
                )
            
            print(f"✅ COMPRA executada: {symbol} | Qty: {quantity} | Preço: {order.get('price', 'N/A')}")
            
            return {
                'order_id': order['orderId'],
                'symbol': symbol,
                'side': 'BUY',
                'quantity': float(order.get('executedQty', quantity)),
                'price': float(order.get('price', order.get('avgPrice', 0))),
                'timestamp': datetime.now()
            }
            
        except BinanceAPIException as e:
            print(f"❌ Erro na compra de {symbol}: {e.message}")
            return None
        except Exception as e:
            print(f"❌ Erro na compra de {symbol}: {e}")
            return None
    
    def sell_market(self, symbol: str, quantity: float) -> Optional[Dict]:
        """
        Executa venda market
        
        Retorna dict com info da ordem ou None em caso de erro
        """
        try:
            if self.trading_mode == 'SPOT':
                order = self.client.order_market_sell(
                    symbol=symbol,
                    quantity=quantity
                )
            else:
                # FUTURES
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side='SELL',
                    type='MARKET',
                    quantity=quantity
                )
            
            print(f"✅ VENDA executada: {symbol} | Qty: {quantity} | Preço: {order.get('price', 'N/A')}")
            
            return {
                'order_id': order['orderId'],
                'symbol': symbol,
                'side': 'SELL',
                'quantity': float(order.get('executedQty', quantity)),
                'price': float(order.get('price', order.get('avgPrice', 0))),
                'timestamp': datetime.now()
            }
            
        except BinanceAPIException as e:
            print(f"❌ Erro na venda de {symbol}: {e.message}")
            return None
        except Exception as e:
            print(f"❌ Erro na venda de {symbol}: {e}")
            return None
    
    def open_position(self, symbol: str, entry_price: float, take_profit: float, stop_loss: float) -> bool:
        """
        Abre nova posição
        
        Calcula quantidade baseada no saldo disponível e executa compra
        """
        if not self.can_open_position():
            print(f"⚠️ Limite de posições atingido ({len(self.active_positions)}/{Config.MAX_TOTAL_POSITIONS})")
            return False
        
        if self.has_active_position(symbol):
            print(f"⚠️ Já existe posição aberta em {symbol}")
            return False
        
        # Calcula quantidade (usa 95% do saldo disponível para segurança)
        balance = self.get_account_balance()
        if balance < 10:  # Mínimo de $10
            print(f"⚠️ Saldo insuficiente: ${balance:.2f}")
            return False
        
        # Quantidade em USDT (95% do saldo)
        usdt_amount = balance * 0.95
        
        # Quantidade do ativo
        quantity = usdt_amount / entry_price
        
        # Arredonda quantidade conforme precisão do símbolo
        try:
            exchange_info = self.client.get_exchange_info()
            symbol_info = next(s for s in exchange_info['symbols'] if s['symbol'] == symbol)
            step_size = None
            
            for filter_item in symbol_info['filters']:
                if filter_item['filterType'] == 'LOT_SIZE':
                    step_size = float(filter_item['stepSize'])
                    break
            
            if step_size:
                # Arredonda para o step size
                quantity = (quantity // step_size) * step_size
            
            # Executa compra
            buy_order = self.buy_market(symbol, quantity)
            
            if buy_order:
                # Registra posição
                self.active_positions[symbol] = {
                    'entry_price': buy_order['price'],
                    'quantity': buy_order['quantity'],
                    'take_profit': take_profit,
                    'stop_loss': stop_loss,
                    'entry_time': buy_order['timestamp'],
                    'buy_order': buy_order
                }
                return True
            
        except Exception as e:
            print(f"❌ Erro ao abrir posição em {symbol}: {e}")
        
        return False
    
    def close_position(self, symbol: str, reason: str = 'TP/SL') -> Optional[Dict]:
        """
        Fecha posição existente
        
        Retorna dict com info do trade completo ou None
        """
        if symbol not in self.active_positions:
            return None
        
        position = self.active_positions[symbol]
        quantity = position['quantity']
        
        # Executa venda
        sell_order = self.sell_market(symbol, quantity)
        
        if sell_order:
            # Calcula resultado
            entry_price = position['entry_price']
            exit_price = sell_order['price']
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            pnl_usdt = (exit_price - entry_price) * quantity
            
            trade_info = {
                'symbol': symbol,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'quantity': quantity,
                'pnl_pct': pnl_pct,
                'pnl_usdt': pnl_usdt,
                'entry_time': position['entry_time'],
                'exit_time': sell_order['timestamp'],
                'reason': reason,
                'buy_order': position['buy_order'],
                'sell_order': sell_order
            }
            
            # Remove posição
            del self.active_positions[symbol]
            
            return trade_info
        
        return None
    
    def check_positions(self, current_prices: Dict[str, float]) -> list:
        """
        Verifica posições abertas e fecha se atingir TP ou SL
        
        Retorna lista de trades fechados
        """
        closed_trades = []
        
        for symbol, position in list(self.active_positions.items()):
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            entry_price = position['entry_price']
            take_profit = position['take_profit']
            stop_loss = position['stop_loss']
            
            # Verifica TP
            if current_price >= take_profit:
                print(f"🎯 TP atingido: {symbol} | Entrada: ${entry_price:.8f} | Saída: ${current_price:.8f}")
                trade = self.close_position(symbol, reason='TAKE_PROFIT')
                if trade:
                    closed_trades.append(trade)
            
            # Verifica SL
            elif current_price <= stop_loss:
                print(f"🛑 SL atingido: {symbol} | Entrada: ${entry_price:.8f} | Saída: ${current_price:.8f}")
                trade = self.close_position(symbol, reason='STOP_LOSS')
                if trade:
                    closed_trades.append(trade)
        
        return closed_trades

