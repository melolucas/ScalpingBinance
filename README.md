# Binance Micro-Profit Bot

Bot de trading automatizado para Binance que opera micro-lucros em múltiplos pares, começando com **Spot** e suportando **Futures 1x** posteriormente.

## 🎯 Objetivo

Bot que:
- Monitora **todos os pares** mas **só opera os elegíveis** (liquidez, spread, ATR%, variação)
- Faz trades curtos de **~3% TP** com **~1.5% SL** (ajustáveis)
- Mantém **cooldown** por símbolo após saída
- Começa em **Spot**; depois permite **Futures 1x** sem mudar estratégia
- Mantém **logs detalhados** e gera **métricas diárias** (winrate, PnL líquido, horários bons/ruins)
- Ranking dinâmico de pares ("top N") atualizado a cada X min

## 📋 Requisitos

- Python 3.11+
- Conta Binance (testnet recomendado para testes)
- API Key e Secret da Binance

## 🚀 Instalação

1. Clone o repositório:
```bash
git clone <repo-url>
cd binance-microbot
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure o `.env`:
```bash
cp .env.example .env
```

Edite o `.env` e preencha:
```env
BINANCE_API_KEY=sua_api_key
BINANCE_API_SECRET=sua_api_secret
MODE=SPOT
USE_TESTNET=true
```

## ⚙️ Configuração

### Parâmetros Principais

- `MODE`: `SPOT` ou `FUTURES` (padrão: `SPOT`)
- `USE_TESTNET`: `true` ou `false` (padrão: `true`)
- `TOP_N`: Quantos pares do ranking operar (padrão: 15)
- `MAX_POSITIONS`: Posições simultâneas (padrão: 5)
- `CAPITAL_PER_TRADE`: Capital por trade em % (padrão: 0.10 = 10%)
- `TAKE_PROFIT_PERCENT`: TP em % (padrão: 0.03 = 3%)
- `STOP_LOSS_PERCENT`: SL em % (padrão: 0.015 = 1.5%)

### Filtros de Elegibilidade

- `MIN_VOLUME_USDT`: Volume mínimo 24h (Spot)
- `MIN_FUTURES_VOLUME_USDT`: Volume mínimo 24h (Futures)
- `MAX_SPREAD_PERCENT`: Spread máximo permitido
- `MIN_VOLATILITY_PERCENT`: ATR% mínimo
- `MIN_DAILY_CHANGE_PERCENT`: Variação 24h mínima

## 🏃 Como Rodar

### Modo Normal
```bash
make run
# ou
python -m app.main run
```

### Modo Dry-Run (Simulação)
```bash
make dry
# ou
python -m app.main run --dry-run
```

### Ver Estatísticas
```bash
make stats
# ou
python -m app.main stats
```

### Ver Ranking de Símbolos
```bash
make rank
# ou
python -m app.main rank
```

### Replay de Trades
```bash
python -m app.main replay --symbol BTCUSDT --date 2025-01-15
```

### Docker
```bash
make docker
# ou
docker compose up --build -d
```

## 🔄 Alternando para Futures 1x

1. Edite o `.env`:
```env
MODE=FUTURES
USE_TESTNET=true
```

2. Certifique-se de ter saldo na conta Futures testnet

3. Rode normalmente:
```bash
make run
```

O bot automaticamente usa os adapters corretos para Futures sem mudar a estratégia.

## 📊 Estratégia

### Basic Pullback

- **Contexto**: Tendência (EMA9 > EMA21 → só long)
- **Gatilho**: Pullback rápido (queda ≥ 1.2% nos últimos 3-5 candles 1m) + candle de confirmação
- **Alvos**:
  - TP = `TAKE_PROFIT_PERCENT` (ajustado +0.5% se ATR% alto)
  - SL = `STOP_LOSS_PERCENT` (ajustado +0.3% se ATR% alto)
  - Trailing: inicia em `TRAILING_START_PERCENT`, step `TRAILING_STEP_PERCENT`

## 📁 Estrutura do Projeto

```
binance-microbot/
├── app/
│   ├── main.py              # Entrypoint CLI
│   ├── config.py            # Configuração Pydantic
│   ├── utils/               # Utilitários (logger, time, math, files)
│   ├── data/                # Schemas, store, ranker
│   ├── adapters/binance/    # REST, WebSockets, symbols
│   ├── core/                # FSM, risk, executor, context, strategy, scheduler
│   ├── strategies/          # Estratégias (basic_pullback)
│   └── cli/                 # Comandos CLI
├── tests/                   # Testes
├── logs/                    # Logs e dados
├── .env.example             # Exemplo de configuração
├── requirements.txt         # Dependências
├── Dockerfile               # Docker
├── docker-compose.yml       # Docker Compose
└── Makefile                 # Comandos úteis
```

## 📝 Logs

Logs são salvos em `./logs/`:
- `bot.log`: Log geral (JSON estruturado)
- `<SYMBOL>.log`: Log por símbolo
- `trades.json`: Histórico de trades
- `daily_stats.json`: Estatísticas diárias agregadas
- `rank_<timestamp>.json`: Snapshots do ranking

## ⚠️ Avisos de Risco

- **Este bot opera com dinheiro real**. Use testnet para testes.
- **Taxas**: Binance cobra taxas de trading (0.1% maker/taker no Spot, variável no Futures).
- **Spread**: Spread pode impactar lucros em trades pequenos.
- **Funding**: Se usar Futures, há taxas de funding periódicas.
- **Limites**: Respeite os limites de rate da Binance.
- **Perdas**: Trading envolve risco de perda total do capital.

## 🧪 Testes

```bash
make test
# ou
pytest -q
```

## 🛣️ Roadmap

- [ ] Trailing stop aprimorado
- [ ] Múltiplas estratégias
- [ ] Pesos por símbolo com aprendizado dos logs
- [ ] Blacklist automática de símbolos ruins
- [ ] CSV export automático diário
- [ ] Ajuste dinâmico de TP/SL baseado em ATR%

## 📄 Licença

Este projeto é fornecido "como está", sem garantias. Use por sua conta e risco.

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor, abra uma issue ou PR.

---

**Desenvolvido com ❤️ para trading automatizado**

