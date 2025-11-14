"""
Módulo de gerenciamento do banco de dados SQLite
Sistema completo para aprendizado e análise de trades
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from config import Config
import os

class Database:
    """Gerenciador do banco de dados SQLite"""
    
    def __init__(self, db_file: str = None):
        self.db_file = db_file or Config.DB_FILE
        self._init_database()
    
    def _get_connection(self):
        """Cria conexão com o banco"""
        return sqlite3.connect(self.db_file)
    
    def _init_database(self):
        """Inicializa todas as tabelas do banco"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Tabela de trades (já existente, mas melhorada)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                quantity REAL NOT NULL,
                pnl_pct REAL NOT NULL,
                pnl_usdt REAL NOT NULL,
                entry_time TEXT NOT NULL,
                exit_time TEXT NOT NULL,
                duration_seconds REAL,
                reason TEXT NOT NULL,
                strategy TEXT DEFAULT 'EMA_9_21',
                volume REAL,
                stop_loss_pct REAL,
                take_profit_pct REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de sinais (sinais detectados, mesmo que não tenham virado trade)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                price REAL NOT NULL,
                ema_fast REAL,
                ema_slow REAL,
                volume REAL,
                volume_avg REAL,
                executed BOOLEAN DEFAULT 0,
                trade_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trade_id) REFERENCES trades(id)
            )
        ''')
        
        # Tabela de performance diária
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                total_pnl_usdt REAL DEFAULT 0,
                total_pnl_pct REAL DEFAULT 0,
                avg_pnl_pct REAL DEFAULT 0,
                best_trade_pct REAL,
                worst_trade_pct REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de configurações do bot (histórico de mudanças)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                take_profit_pct REAL,
                stop_loss_pct REAL,
                max_pairs INTEGER,
                ema_fast INTEGER,
                ema_slow INTEGER,
                trading_mode TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Índices para melhor performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_pnl ON trades(pnl_pct)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_performance_date ON daily_performance(date)')
        
        conn.commit()
        conn.close()
        print(f"✅ Banco de dados inicializado: {self.db_file}")
    
    # ==================== TRADES ====================
    
    def insert_trade(self, trade_data: Dict) -> int:
        """Insere um trade e retorna o ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO trades (
                    timestamp, symbol, entry_price, exit_price, quantity,
                    pnl_pct, pnl_usdt, entry_time, exit_time, duration_seconds,
                    reason, strategy, volume, stop_loss_pct, take_profit_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data.get('timestamp', datetime.now().isoformat()),
                trade_data['symbol'],
                trade_data['entry_price'],
                trade_data['exit_price'],
                trade_data['quantity'],
                trade_data['pnl_pct'],
                trade_data['pnl_usdt'],
                trade_data['entry_time'],
                trade_data['exit_time'],
                trade_data.get('duration_seconds'),
                trade_data['reason'],
                trade_data.get('strategy', 'EMA_9_21'),
                trade_data.get('volume', 0),
                trade_data.get('stop_loss_pct', Config.STOP_LOSS_PCT),
                trade_data.get('take_profit_pct', Config.TAKE_PROFIT_PCT)
            ))
            
            trade_id = cursor.lastrowid
            conn.commit()
            
            # Atualiza performance diária
            self._update_daily_performance(trade_data)
            
            return trade_id
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_trades(self, limit: int = 100, symbol: str = None, 
                   start_date: str = None, end_date: str = None) -> List[Dict]:
        """Busca trades com filtros opcionais"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ==================== SIGNALS ====================
    
    def insert_signal(self, signal_data: Dict) -> int:
        """Insere um sinal detectado"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO signals (
                    timestamp, symbol, signal_type, price,
                    ema_fast, ema_slow, volume, volume_avg
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_data.get('timestamp', datetime.now().isoformat()),
                signal_data['symbol'],
                signal_data.get('signal_type', 'BUY'),
                signal_data['price'],
                signal_data.get('ema_fast'),
                signal_data.get('ema_slow'),
                signal_data.get('volume'),
                signal_data.get('volume_avg')
            ))
            
            signal_id = cursor.lastrowid
            conn.commit()
            return signal_id
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def mark_signal_executed(self, signal_id: int, trade_id: int):
        """Marca sinal como executado e associa ao trade"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE signals 
            SET executed = 1, trade_id = ?
            WHERE id = ?
        ''', (trade_id, signal_id))
        
        conn.commit()
        conn.close()
    
    def get_signals(self, symbol: str = None, executed: bool = None, 
                    limit: int = 100) -> List[Dict]:
        """Busca sinais com filtros"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM signals WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if executed is not None:
            query += " AND executed = ?"
            params.append(1 if executed else 0)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ==================== STATISTICS ====================
    
    def get_statistics(self, days: int = None) -> Dict:
        """Retorna estatísticas gerais"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        
        if days:
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        # Total de trades
        cursor.execute(f"SELECT COUNT(*) FROM ({query})", params)
        total_trades = cursor.fetchone()[0]
        
        if total_trades == 0:
            conn.close()
            return {}
        
        # Trades vencedores
        cursor.execute(f"{query} AND pnl_pct > 0", params)
        winning_trades = len(cursor.fetchall())
        
        # Trades perdedores
        cursor.execute(f"{query} AND pnl_pct < 0", params)
        losing_trades = len(cursor.fetchall())
        
        # Win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # PnL total
        cursor.execute(f"SELECT SUM(pnl_usdt) FROM ({query})", params)
        total_pnl = cursor.fetchone()[0] or 0
        
        # PnL médio
        cursor.execute(f"SELECT AVG(pnl_pct) FROM ({query})", params)
        avg_pnl_pct = cursor.fetchone()[0] or 0
        
        # Melhor trade
        cursor.execute(f"{query} ORDER BY pnl_pct DESC LIMIT 1", params)
        best_trade = cursor.fetchone()
        best_pnl = best_trade[6] if best_trade else 0
        
        # Pior trade
        cursor.execute(f"{query} ORDER BY pnl_pct ASC LIMIT 1", params)
        worst_trade = cursor.fetchone()
        worst_pnl = worst_trade[6] if worst_trade else 0
        
        # Por símbolo
        cursor.execute(f"""
            SELECT symbol, COUNT(*), SUM(pnl_usdt), AVG(pnl_pct)
            FROM ({query})
            GROUP BY symbol
            ORDER BY SUM(pnl_usdt) DESC
        """, params)
        by_symbol = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl_usdt': total_pnl,
            'avg_pnl_pct': avg_pnl_pct,
            'best_trade_pct': best_pnl,
            'worst_trade_pct': worst_pnl,
            'by_symbol': [
                {'symbol': s[0], 'trades': s[1], 'pnl_usdt': s[2] or 0, 'avg_pnl_pct': s[3] or 0}
                for s in by_symbol
            ]
        }
    
    def get_daily_performance(self, days: int = 30) -> List[Dict]:
        """Retorna performance diária"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).date().isoformat()
        
        cursor.execute('''
            SELECT * FROM daily_performance
            WHERE date >= ?
            ORDER BY date DESC
        ''', (start_date,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def _update_daily_performance(self, trade_data: Dict):
        """Atualiza performance diária após um trade"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Extrai data do trade
        trade_date = datetime.fromisoformat(trade_data['timestamp']).date().isoformat()
        
        # Verifica se já existe registro do dia
        cursor.execute('SELECT * FROM daily_performance WHERE date = ?', (trade_date,))
        existing = cursor.fetchone()
        
        if existing:
            # Atualiza existente
            cursor.execute('''
                UPDATE daily_performance
                SET 
                    total_trades = total_trades + 1,
                    winning_trades = winning_trades + ?,
                    losing_trades = losing_trades + ?,
                    total_pnl_usdt = total_pnl_usdt + ?,
                    total_pnl_pct = total_pnl_pct + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE date = ?
            ''', (
                1 if trade_data['pnl_pct'] > 0 else 0,
                1 if trade_data['pnl_pct'] < 0 else 0,
                trade_data['pnl_usdt'],
                trade_data['pnl_pct'],
                trade_date
            ))
        else:
            # Cria novo registro
            cursor.execute('''
                INSERT INTO daily_performance (
                    date, total_trades, winning_trades, losing_trades,
                    total_pnl_usdt, total_pnl_pct, best_trade_pct, worst_trade_pct
                ) VALUES (?, 1, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_date,
                1 if trade_data['pnl_pct'] > 0 else 0,
                1 if trade_data['pnl_pct'] < 0 else 0,
                trade_data['pnl_usdt'],
                trade_data['pnl_pct'],
                trade_data['pnl_pct'] if trade_data['pnl_pct'] > 0 else None,
                trade_data['pnl_pct'] if trade_data['pnl_pct'] < 0 else None
            ))
        
        # Recalcula win_rate e avg_pnl
        cursor.execute('''
            UPDATE daily_performance
            SET 
                win_rate = CASE 
                    WHEN total_trades > 0 THEN (winning_trades * 100.0 / total_trades)
                    ELSE 0
                END,
                avg_pnl_pct = CASE
                    WHEN total_trades > 0 THEN (total_pnl_pct / total_trades)
                    ELSE 0
                END
            WHERE date = ?
        ''', (trade_date,))
        
        conn.commit()
        conn.close()
    
    # ==================== CONFIG HISTORY ====================
    
    def save_config(self, config_data: Dict):
        """Salva configuração atual do bot"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bot_configs (
                timestamp, take_profit_pct, stop_loss_pct, max_pairs,
                ema_fast, ema_slow, trading_mode, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            config_data.get('take_profit_pct', Config.TAKE_PROFIT_PCT),
            config_data.get('stop_loss_pct', Config.STOP_LOSS_PCT),
            config_data.get('max_pairs', Config.MAX_PAIRS),
            config_data.get('ema_fast', Config.EMA_FAST),
            config_data.get('ema_slow', Config.EMA_SLOW),
            config_data.get('trading_mode', Config.TRADING_MODE),
            config_data.get('notes', '')
        ))
        
        conn.commit()
        conn.close()
    
    def get_config_history(self, limit: int = 10) -> List[Dict]:
        """Busca histórico de configurações"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM bot_configs
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ==================== UTILITY ====================
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Executa query customizada (útil para análises)"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_table_info(self, table_name: str) -> List[Dict]:
        """Retorna informações sobre uma tabela"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(f"PRAGMA table_info({table_name})")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

