"""Armazenamento de trades e estatísticas"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from app.config import settings
from app.data.schemas import TradeSchema, DailyStatsSchema
from app.utils.files import read_json, write_json, append_json, ensure_dir


class TradeStore:
    """Armazena e recupera trades"""
    
    def __init__(self):
        self.trades_file = settings.trade_history_file
        self.stats_file = settings.daily_stats_file
        ensure_dir(Path(self.trades_file).parent)
        ensure_dir(Path(self.stats_file).parent)
    
    def save_trade(self, trade: TradeSchema):
        """Salva trade (append)"""
        trade_dict = trade.model_dump()
        append_json(self.trades_file, trade_dict)
    
    def get_trades(self, symbol: Optional[str] = None, date: Optional[str] = None) -> List[dict]:
        """Recupera trades, opcionalmente filtrados por símbolo/data"""
        trades = read_json(self.trades_file, default=[])
        
        if symbol:
            trades = [t for t in trades if t.get("symbol") == symbol]
        
        if date:
            trades = [t for t in trades if t.get("ts_open", "").startswith(date)]
        
        return trades
    
    def get_daily_stats(self, date: Optional[str] = None) -> List[dict]:
        """Recupera estatísticas diárias"""
        stats = read_json(self.stats_file, default=[])
        if date:
            stats = [s for s in stats if s.get("date") == date]
        return stats
    
    def update_daily_stats(self, date: str, stats: DailyStatsSchema):
        """Atualiza ou cria estatísticas diárias"""
        all_stats = read_json(self.stats_file, default=[])
        
        # Remove stats do dia se existir
        all_stats = [s for s in all_stats if s.get("date") != date]
        
        # Adiciona nova
        all_stats.append(stats.model_dump())
        
        # Ordena por data
        all_stats.sort(key=lambda x: x.get("date", ""))
        
        write_json(self.stats_file, all_stats)
    
    def compute_daily_stats(self, date: str) -> DailyStatsSchema:
        """Calcula estatísticas do dia a partir dos trades"""
        trades = self.get_trades(date=date)
        
        if not trades:
            return DailyStatsSchema(date=date)
        
        wins = 0
        losses = 0
        gross_pnl = 0.0
        net_pnl = 0.0
        max_dd = 0.0
        running_pnl = 0.0
        symbol_pnl: dict[str, float] = {}
        
        for trade in trades:
            if trade.get("result") == "WIN":
                wins += 1
            elif trade.get("result") == "LOSS":
                losses += 1
            
            pnl = trade.get("pnl_pct_net", 0.0) or 0.0
            gross_pnl += abs(pnl)
            net_pnl += pnl
            running_pnl += pnl
            max_dd = min(max_dd, running_pnl)
            
            symbol = trade.get("symbol", "")
            symbol_pnl[symbol] = symbol_pnl.get(symbol, 0.0) + pnl
        
        total = wins + losses
        winrate = (wins / total * 100.0) if total > 0 else 0.0
        
        # Top 3 melhores e piores símbolos
        sorted_symbols = sorted(symbol_pnl.items(), key=lambda x: x[1], reverse=True)
        best_symbols = [s[0] for s in sorted_symbols[:3]]
        worst_symbols = [s[0] for s in sorted_symbols[-3:]]
        
        return DailyStatsSchema(
            date=date,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            winrate=winrate,
            max_dd=abs(max_dd),
            ops=len(trades),
            best_symbols=best_symbols,
            worst_symbols=worst_symbols
        )

