"""Utilitários de tempo"""
from datetime import datetime, timezone
from typing import Optional


def now_utc() -> datetime:
    """Retorna datetime UTC atual"""
    return datetime.now(timezone.utc)


def timestamp_ms() -> int:
    """Retorna timestamp em milissegundos"""
    return int(now_utc().timestamp() * 1000)


def timestamp_s() -> int:
    """Retorna timestamp em segundos"""
    return int(now_utc().timestamp())


def from_timestamp_ms(ts: int) -> datetime:
    """Converte timestamp ms para datetime"""
    return datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)


def format_iso(dt: Optional[datetime] = None) -> str:
    """Formata datetime como ISO string"""
    if dt is None:
        dt = now_utc()
    return dt.isoformat()

