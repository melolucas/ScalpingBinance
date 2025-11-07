"""Gerenciamento de risco"""
from typing import Dict, Optional, Set
from datetime import datetime, timedelta
from app.config import settings
from app.utils.json_logger import get_logger
from app.data.store import TradeStore

logger = get_logger()


class RiskManager:
    """Gerenciador de risco"""
    
    def __init__(self):
        self.store = TradeStore()
        self.active_positions: Set[str] = set()
        self.symbol_loss_streak: Dict[str, int] = {}
        self.symbol_last_loss: Dict[str, datetime] = {}
        self.max_loss_streak = 3  # Máximo de perdas consecutivas por símbolo
    
    def can_open_position(self, symbol: str) -> tuple[bool, Optional[str]]:
        """Verifica se pode abrir nova posição"""
        # Verificar máximo de posições
        if len(self.active_positions) >= settings.max_positions:
            return False, f"Max positions reached: {settings.max_positions}"
        
        # Verificar se símbolo já está em posição
        if symbol in self.active_positions:
            return False, f"Symbol {symbol} already in position"
        
        # Verificar loss streak
        streak = self.symbol_loss_streak.get(symbol, 0)
        if streak >= self.max_loss_streak:
            return False, f"Symbol {symbol} has loss streak {streak} >= {self.max_loss_streak}"
        
        return True, None
    
    def calculate_position_size(self, bankroll: float, entry_price: float) -> float:
        """Calcula tamanho da posição"""
        capital = bankroll * settings.capital_per_trade
        qty = capital / entry_price
        return qty
    
    def register_position(self, symbol: str):
        """Registra posição aberta"""
        self.active_positions.add(symbol)
        logger.debug("risk_position_opened", symbol=symbol, total=len(self.active_positions))
    
    def register_position_closed(self, symbol: str, pnl_pct: Optional[float] = None):
        """Registra posição fechada"""
        if symbol in self.active_positions:
            self.active_positions.remove(symbol)
        
        # Atualizar loss streak
        if pnl_pct is not None:
            if pnl_pct < 0:
                self.symbol_loss_streak[symbol] = self.symbol_loss_streak.get(symbol, 0) + 1
                self.symbol_last_loss[symbol] = datetime.utcnow()
            else:
                # Reset streak em caso de ganho
                self.symbol_loss_streak[symbol] = 0
        
        logger.debug("risk_position_closed", symbol=symbol, pnl_pct=pnl_pct, total=len(self.active_positions))
    
    def reset_loss_streak(self, symbol: str):
        """Reseta loss streak de símbolo"""
        self.symbol_loss_streak[symbol] = 0
        if symbol in self.symbol_last_loss:
            del self.symbol_last_loss[symbol]
    
    def get_active_count(self) -> int:
        """Retorna número de posições ativas"""
        return len(self.active_positions)
    
    def cleanup_old_streaks(self, days: int = 1):
        """Limpa streaks antigos"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        symbols_to_remove = []
        
        for symbol, last_loss in self.symbol_last_loss.items():
            if last_loss < cutoff:
                symbols_to_remove.append(symbol)
        
        for symbol in symbols_to_remove:
            self.reset_loss_streak(symbol)

