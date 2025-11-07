"""Utilitários matemáticos"""
from typing import List
try:
    import numpy as np
except ImportError:
    # Fallback se numpy não estiver disponível
    np = None


def z_score(value: float, mean: float, std: float) -> float:
    """Calcula z-score"""
    if std == 0:
        return 0.0
    return (value - mean) / std


def normalize(values: List[float]) -> List[float]:
    """Normaliza lista de valores (z-score)"""
    if not values:
        return []
    if np is None:
        # Fallback sem numpy
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = variance ** 0.5
        if std == 0:
            return [0.0] * len(values)
        return [(x - mean) / std for x in values]
    arr = np.array(values)
    mean = arr.mean()
    std = arr.std()
    if std == 0:
        return [0.0] * len(values)
    return ((arr - mean) / std).tolist()


def percent_change(old: float, new: float) -> float:
    """Calcula mudança percentual"""
    if old == 0:
        return 0.0
    return ((new - old) / old) * 100.0


def round_to_precision(value: float, precision: int) -> float:
    """Arredonda para precisão de casas decimais"""
    return round(value, precision)


def round_to_step(value: float, step: float) -> float:
    """Arredonda para múltiplo de step"""
    return round(value / step) * step

