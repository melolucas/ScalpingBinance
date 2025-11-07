"""Máquina de estados finita por símbolo"""
import asyncio
from enum import Enum
from typing import Optional, Dict, Callable
from datetime import datetime, timedelta
from app.config import settings
from app.utils.time import now_utc, timestamp_ms
from app.utils.json_logger import get_logger

logger = get_logger()


class State(Enum):
    """Estados do FSM"""
    IDLE = "IDLE"
    BUYING = "BUYING"
    POSITION = "POSITION"
    EXITING = "EXITING"
    COOLDOWN = "COOLDOWN"


class SymbolFSM:
    """FSM por símbolo"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.state = State.IDLE
        self.state_changed_at = now_utc()
        self.cooldown_until: Optional[datetime] = None
        self.position: Optional[dict] = None
        self.order_id: Optional[str] = None
        self.on_state_change: Optional[Callable] = None
    
    def set_state(self, new_state: State):
        """Muda estado"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            self.state_changed_at = now_utc()
            
            logger.info(
                "fsm_state_change",
                symbol=self.symbol,
                old_state=old_state.value,
                new_state=new_state.value
            )
            
            if self.on_state_change:
                self.on_state_change(self.symbol, old_state, new_state)
    
    def can_enter(self) -> bool:
        """Verifica se pode entrar em nova posição"""
        if self.state != State.IDLE:
            return False
        
        if self.cooldown_until and now_utc() < self.cooldown_until:
            return False
        
        return True
    
    def start_buying(self, order_id: str):
        """Inicia processo de compra"""
        if self.state != State.IDLE:
            logger.warning("fsm_invalid_transition", symbol=self.symbol, state=self.state.value)
            return
        
        self.order_id = order_id
        self.set_state(State.BUYING)
    
    def enter_position(self, position: dict):
        """Entra em posição"""
        if self.state != State.BUYING:
            logger.warning("fsm_invalid_transition", symbol=self.symbol, state=self.state.value)
            return
        
        self.position = position
        self.set_state(State.POSITION)
    
    def start_exiting(self):
        """Inicia processo de saída"""
        if self.state != State.POSITION:
            logger.warning("fsm_invalid_transition", symbol=self.symbol, state=self.state.value)
            return
        
        self.set_state(State.EXITING)
    
    def exit_position(self):
        """Sai de posição e entra em cooldown"""
        if self.state not in [State.POSITION, State.EXITING]:
            logger.warning("fsm_invalid_transition", symbol=self.symbol, state=self.state.value)
            return
        
        self.position = None
        self.order_id = None
        self.set_state(State.COOLDOWN)
        
        # Definir cooldown
        cooldown_duration = timedelta(minutes=settings.cooldown_minutes)
        self.cooldown_until = now_utc() + cooldown_duration
    
    def reset_to_idle(self):
        """Reseta para IDLE (força)"""
        self.position = None
        self.order_id = None
        self.cooldown_until = None
        self.set_state(State.IDLE)
    
    def is_in_position(self) -> bool:
        """Verifica se está em posição"""
        return self.state == State.POSITION
    
    def is_in_cooldown(self) -> bool:
        """Verifica se está em cooldown"""
        if self.state != State.COOLDOWN:
            return False
        
        if self.cooldown_until and now_utc() >= self.cooldown_until:
            self.set_state(State.IDLE)
            self.cooldown_until = None
            return False
        
        return True

