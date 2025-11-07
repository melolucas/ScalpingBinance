"""Retry com backoff e jitter"""
import asyncio
import random
from typing import Callable, TypeVar, Optional
from functools import wraps

T = TypeVar("T")


def exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True
):
    """Decorator para retry com backoff exponencial"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries - 1:
                        raise
                    
                    # Calcular delay
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    
                    # Adicionar jitter
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    *args,
    **kwargs
) -> T:
    """Executa função com retry e backoff"""
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            if attempt == max_retries - 1:
                raise
            
            # Calcular delay
            delay = min(base_delay * (2 ** attempt), max_delay)
            
            # Adicionar jitter
            if jitter:
                delay = delay * (0.5 + random.random() * 0.5)
            
            await asyncio.sleep(delay)
    
    raise last_exception

