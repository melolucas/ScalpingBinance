"""Script para validar .env"""
import os
from pathlib import Path

# Valores esperados
REQUIRED_VARS = [
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "MODE",
    "USE_TESTNET",
]

OPTIONAL_VARS = {
    "TOP_N": "15",
    "MAX_POSITIONS": "5",
    "CAPITAL_PER_TRADE": "0.10",
    "LEVERAGE": "1",
    "COOLDOWN_MINUTES": "10",
    "MIN_VOLUME_USDT": "10000000",
    "MIN_FUTURES_VOLUME_USDT": "200000000",
    "MAX_SPREAD_PERCENT": "0.001",
    "MIN_VOLATILITY_PERCENT": "0.002",
    "MIN_DAILY_CHANGE_PERCENT": "0.015",
    "TAKE_PROFIT_PERCENT": "0.03",
    "STOP_LOSS_PERCENT": "0.015",
    "TRAILING_START_PERCENT": "0.015",
    "TRAILING_STEP_PERCENT": "0.005",
    "RANK_REFRESH_INTERVAL_MIN": "15",
    "PING_INTERVAL": "1800",
    "RECV_WINDOW": "5000",
    "LOG_PATH": "./logs",
    "TRADE_HISTORY_FILE": "./logs/trades.json",
    "DAILY_STATS_FILE": "./logs/daily_stats.json",
    "BASE_ASSET": "USDT",
    "STARTING_BANKROLL": "100",
}

def validate_env():
    """Valida arquivo .env"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("[ERRO] Arquivo .env não encontrado!")
        print("   Crie um arquivo .env baseado em .env.example")
        return False
    
    # Carregar variáveis do .env
    env_vars = {}
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                # Separar chave e valor
                key, value = line.split("=", 1)
                # Remover comentários inline (tudo após #)
                if "#" in value:
                    value = value.split("#")[0]
                env_vars[key.strip()] = value.strip()
    
    errors = []
    warnings = []
    
    # Verificar variáveis obrigatórias
    for var in REQUIRED_VARS:
        if var not in env_vars or not env_vars[var]:
            errors.append(f"[ERRO] {var} está vazio ou não definido")
        else:
            print(f"[OK] {var} definido")
    
    # Verificar MODE
    if "MODE" in env_vars:
        mode = env_vars["MODE"].upper()
        if mode not in ["SPOT", "FUTURES"]:
            errors.append(f"[ERRO] MODE deve ser 'SPOT' ou 'FUTURES', encontrado: {mode}")
        else:
            print(f"[OK] MODE={mode}")
    
    # Verificar USE_TESTNET
    if "USE_TESTNET" in env_vars:
        testnet = env_vars["USE_TESTNET"].lower()
        if testnet not in ["true", "false"]:
            errors.append(f"[ERRO] USE_TESTNET deve ser 'true' ou 'false', encontrado: {testnet}")
        else:
            print(f"[OK] USE_TESTNET={testnet}")
    
    # Verificar variáveis opcionais
    for var, default in OPTIONAL_VARS.items():
        if var not in env_vars:
            warnings.append(f"[AVISO] {var} não definido (usará default: {default})")
    
    # Verificar valores numéricos
    numeric_vars = [
        "TOP_N", "MAX_POSITIONS", "CAPITAL_PER_TRADE", "LEVERAGE", "COOLDOWN_MINUTES",
        "MIN_VOLUME_USDT", "MIN_FUTURES_VOLUME_USDT", "MAX_SPREAD_PERCENT",
        "MIN_VOLATILITY_PERCENT", "MIN_DAILY_CHANGE_PERCENT", "TAKE_PROFIT_PERCENT",
        "STOP_LOSS_PERCENT", "TRAILING_START_PERCENT", "TRAILING_STEP_PERCENT",
        "RANK_REFRESH_INTERVAL_MIN", "PING_INTERVAL", "RECV_WINDOW", "STARTING_BANKROLL"
    ]
    
    for var in numeric_vars:
        if var in env_vars:
            try:
                float(env_vars[var])
            except ValueError:
                errors.append(f"[ERRO] {var} deve ser numérico, encontrado: {env_vars[var]}")
    
    # Resultado
    print("\n" + "="*50)
    if errors:
        print("\n[ERRO] ERROS ENCONTRADOS:")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("\n[OK] .env válido!")
    
    if warnings:
        print("\n[AVISO] AVISOS:")
        for warning in warnings:
            print(f"  {warning}")
    
    print("\n" + "="*50)
    return True

if __name__ == "__main__":
    validate_env()

