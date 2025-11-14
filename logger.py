"""
Sistema de logs - CSV e SQLite
Agora usando o módulo database.py para gerenciamento completo do SQLite
"""
import csv
from datetime import datetime
from typing import Dict, Optional
from config import Config
from database import Database
import os

class TradeLogger:
    def __init__(self):
        self.log_to_csv = Config.LOG_TO_CSV
        self.log_to_db = Config.LOG_TO_DB
        self.csv_file = Config.LOG_FILE
        
        # Inicializa banco de dados SQLite
        if self.log_to_db:
            self.db = Database()
        else:
            self.db = None
        
        # Inicializa CSV
        if self.log_to_csv:
            self._init_csv()
    
    def _init_csv(self):
        """Inicializa arquivo CSV com headers"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'symbol',
                    'entry_price',
                    'exit_price',
                    'quantity',
                    'pnl_pct',
                    'pnl_usdt',
                    'entry_time',
                    'exit_time',
                    'duration_seconds',
                    'reason',
                    'strategy',
                    'volume',
                    'stop_loss_pct',
                    'take_profit_pct'
                ])
    
    
    def log_trade(self, trade_info: Dict):
        """
        Registra trade completo
        
        trade_info deve conter:
        - symbol, entry_price, exit_price, quantity
        - pnl_pct, pnl_usdt
        - entry_time, exit_time, reason
        """
        try:
            # Calcula duração
            entry_time = trade_info['entry_time']
            exit_time = trade_info['exit_time']
            
            if isinstance(entry_time, datetime):
                entry_str = entry_time.isoformat()
            else:
                entry_str = str(entry_time)
            
            if isinstance(exit_time, datetime):
                exit_str = exit_time.isoformat()
            else:
                exit_str = str(exit_time)
            
            duration = None
            if isinstance(entry_time, datetime) and isinstance(exit_time, datetime):
                duration = (exit_time - entry_time).total_seconds()
            
            # Prepara dados
            row_data = {
                'timestamp': datetime.now().isoformat(),
                'symbol': trade_info['symbol'],
                'entry_price': trade_info['entry_price'],
                'exit_price': trade_info['exit_price'],
                'quantity': trade_info['quantity'],
                'pnl_pct': trade_info['pnl_pct'],
                'pnl_usdt': trade_info['pnl_usdt'],
                'entry_time': entry_str,
                'exit_time': exit_str,
                'duration_seconds': duration,
                'reason': trade_info['reason'],
                'strategy': trade_info.get('strategy', 'EMA_9_21'),
                'volume': trade_info.get('volume', 0),
                'stop_loss_pct': Config.STOP_LOSS_PCT,
                'take_profit_pct': Config.TAKE_PROFIT_PCT
            }
            
            # Salva em CSV
            if self.log_to_csv:
                with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        row_data['timestamp'],
                        row_data['symbol'],
                        row_data['entry_price'],
                        row_data['exit_price'],
                        row_data['quantity'],
                        row_data['pnl_pct'],
                        row_data['pnl_usdt'],
                        row_data['entry_time'],
                        row_data['exit_time'],
                        row_data['duration_seconds'],
                        row_data['reason'],
                        row_data['strategy'],
                        row_data['volume'],
                        row_data['stop_loss_pct'],
                        row_data['take_profit_pct']
                    ])
            
            # Salva em DB usando o módulo database
            if self.log_to_db and self.db:
                try:
                    self.db.insert_trade(row_data)
                except Exception as e:
                    print(f"❌ Erro ao salvar trade no banco: {e}")
            
            print(f"📝 Trade registrado: {trade_info['symbol']} | PnL: {trade_info['pnl_pct']:.2f}% (${trade_info['pnl_usdt']:.2f})")
            
        except Exception as e:
            print(f"❌ Erro ao registrar trade: {e}")
    
    def get_statistics(self, days: int = None) -> Dict:
        """Retorna estatísticas dos trades usando o módulo database"""
        try:
            if not self.log_to_db or not self.db:
                return {}
            
            return self.db.get_statistics(days=days)
            
        except Exception as e:
            print(f"Erro ao buscar estatísticas: {e}")
            return {}

