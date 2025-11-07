"""Utilitários de arquivos"""
import json
from pathlib import Path
from typing import Any, List, Optional


def ensure_dir(path: str) -> Path:
    """Garante que diretório existe"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path: str, default: Any = None) -> Any:
    """Lê arquivo JSON"""
    p = Path(path)
    if not p.exists():
        return default if default is not None else []
    
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default if default is not None else []


def write_json(path: str, data: Any, append: bool = False):
    """Escreve arquivo JSON"""
    p = Path(path)
    ensure_dir(p.parent)
    
    if append and p.exists():
        existing = read_json(str(p), default=[])
        if isinstance(existing, list) and isinstance(data, list):
            data = existing + data
        elif isinstance(existing, list):
            data = existing + [data]
        else:
            data = [existing, data]
    
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_json(path: str, item: Any):
    """Append item a lista JSON"""
    write_json(path, item, append=True)

