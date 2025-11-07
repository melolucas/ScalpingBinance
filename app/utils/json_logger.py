"""Logger JSON estruturado"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger


class JSONLogger:
    """Logger que escreve em JSON estruturado"""
    
    def __init__(self, log_path: str = "./logs", symbol: Optional[str] = None):
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
        
        # Logger geral
        general_log = self.log_path / "bot.log"
        logger.add(
            str(general_log),
            format="{message}",
            rotation="1 day",
            retention="30 days",
            serialize=True,
            level="DEBUG"  # Mudado para DEBUG para ver logs de polling
        )
        
        # Logger por símbolo (se especificado)
        self.symbol_logger = None
        if symbol:
            symbol_log = self.log_path / f"{symbol}.log"
            self.symbol_logger = logger.bind(symbol=symbol)
            logger.add(
                str(symbol_log),
                format="{message}",
                rotation="1 day",
                retention="7 days",
                serialize=True,
                level="INFO",
                filter=lambda record: record["extra"].get("symbol") == symbol
            )
    
    def _log(self, level: str, event: str, symbol: Optional[str] = None, **kwargs):
        """Log estruturado"""
        payload = {
            "ts": datetime.utcnow().isoformat(),
            "level": level,
            "event": event,
            **kwargs
        }
        if symbol:
            payload["symbol"] = symbol
        
        log_func = getattr(logger, level.lower())
        if self.symbol_logger and symbol:
            log_func = getattr(self.symbol_logger, level.lower())
        
        log_func(json.dumps(payload))
    
    def info(self, event: str, symbol: Optional[str] = None, **kwargs):
        """Log INFO"""
        self._log("INFO", event, symbol, **kwargs)
    
    def warning(self, event: str, symbol: Optional[str] = None, **kwargs):
        """Log WARNING"""
        self._log("WARNING", event, symbol, **kwargs)
    
    def error(self, event: str, symbol: Optional[str] = None, **kwargs):
        """Log ERROR"""
        self._log("ERROR", event, symbol, **kwargs)
    
    def debug(self, event: str, symbol: Optional[str] = None, **kwargs):
        """Log DEBUG"""
        self._log("DEBUG", event, symbol, **kwargs)


# Instância global
_json_logger = None


def get_logger(symbol: Optional[str] = None) -> JSONLogger:
    """Retorna instância do logger"""
    global _json_logger
    if _json_logger is None:
        from app.config import settings
        _json_logger = JSONLogger(settings.log_path, symbol)
    return _json_logger

