"""Agendador de tarefas periódicas"""
import asyncio
from typing import Callable, Optional
from app.config import settings
from app.utils.json_logger import get_logger

logger = get_logger()


class Scheduler:
    """Agendador de tarefas"""
    
    def __init__(self):
        self.tasks: list[asyncio.Task] = []
        self.running = False
    
    def schedule_periodic(
        self,
        func: Callable,
        interval_seconds: int,
        name: Optional[str] = None
    ):
        """Agenda tarefa periódica"""
        async def periodic_task():
            while self.running:
                try:
                    await func()
                except Exception as e:
                    logger.error("scheduled_task_error", task=name, error=str(e))
                
                await asyncio.sleep(interval_seconds)
        
        task = asyncio.create_task(periodic_task())
        self.tasks.append(task)
        logger.info("task_scheduled", name=name, interval=interval_seconds)
    
    def start(self):
        """Inicia scheduler"""
        self.running = True
        logger.info("scheduler_started")
    
    def stop(self):
        """Para scheduler"""
        self.running = False
        for task in self.tasks:
            task.cancel()
        logger.info("scheduler_stopped")
    
    async def wait_all(self):
        """Aguarda todas as tarefas"""
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

