"""
Logger de status em tempo real - atualiza na mesma linha
"""
import sys
from datetime import datetime

class StatusLogger:
    """Logger que atualiza status na mesma linha"""
    
    def __init__(self):
        self.current_status = ""
        self.last_update = None
    
    def update(self, message: str, show_time: bool = True):
        """
        Atualiza o status na mesma linha
        
        Args:
            message: Mensagem a exibir
            show_time: Se True, mostra timestamp
        """
        timestamp = datetime.now().strftime("%H:%M:%S") if show_time else ""
        status = f"[{timestamp}] {message}" if timestamp else message
        
        # Limpa a linha anterior completamente (150 caracteres) e escreve a nova
        # Adiciona espaços para garantir que limpa tudo
        padding = " " * max(0, 150 - len(status))
        sys.stdout.write(f"\r{status}{padding}")
        sys.stdout.flush()
        
        self.current_status = status
        self.last_update = datetime.now()
    
    def print(self, message: str, show_time: bool = True):
        """
        Imprime mensagem em nova linha (não sobrescreve)
        
        Args:
            message: Mensagem a exibir
            show_time: Se True, mostra timestamp
        """
        # Quebra a linha atual primeiro
        sys.stdout.write("\n")
        sys.stdout.flush()
        
        timestamp = datetime.now().strftime("%H:%M:%S") if show_time else ""
        status = f"[{timestamp}] {message}" if timestamp else message
        
        print(status)
        self.current_status = ""
    
    def clear(self):
        """Limpa a linha atual"""
        sys.stdout.write("\r" + " " * 150 + "\r")
        sys.stdout.flush()
        self.current_status = ""

# Instância global
status_logger = StatusLogger()

