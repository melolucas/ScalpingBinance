# 🤖 Bot de Scalping Automático

Bot de scalping/micro-swing para criptomoedas na Binance, focado em operações rápidas com targets curtos.

## 📋 Características

- **Múltiplas operações por dia** (20-50+ trades)
- **Targets curtos**: +0.4% a +0.8%
- **Stop Loss apertado**: -0.3% a -0.7%
- **Estratégia**: EMA 9/21 + volume + candle breakout
- **Timeframes**: 1m (entrada) e 5m (tendência)
- **Top 3 pares mais voláteis** selecionados automaticamente
- **Modo SPOT** (preparado para migração para FUTURES)

## 🚀 Instalação

### 1. Clone o repositório

```bash
cd Scalping
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente

Copie o arquivo `.env.example` para `.env`:

```bash
copy .env.example .env
```

Edite o `.env` e adicione suas credenciais da Binance:

```env
BINANCE_API_KEY=sua_api_key_aqui
BINANCE_API_SECRET=sua_api_secret_aqui
```

**⚠️ IMPORTANTE**: 
- Use API keys com permissões apenas de **SPOT trading**
- NUNCA compartilhe suas keys
- Para testes, considere usar a testnet da Binance primeiro

### 4. Ajuste as configurações (opcional)

Edite o `.env` para personalizar:

- `TAKE_PROFIT_PCT`: Percentual de lucro (padrão: 0.5%)
- `STOP_LOSS_PCT`: Percentual de stop loss (padrão: 0.4%)
- `MAX_PAIRS`: Quantidade de pares para operar (padrão: 3)
- `MIN_VOLUME_24H`: Volume mínimo em 24h (padrão: 30M USDT)

## ▶️ Como Usar

### Executar o bot

```bash
python main.py
```

O bot irá:

1. Escanear o mercado e selecionar os top 3 pares mais voláteis
2. Conectar aos WebSockets para candles em tempo real
3. Monitorar sinais de entrada baseados na estratégia
4. Executar compras/vendas automaticamente
5. Registrar todos os trades em CSV e SQLite

### Parar o bot

Pressione `Ctrl+C` para parar o bot de forma segura.

## 📊 Estratégia

### Sinais de Entrada

O bot entra em uma posição quando:

1. ✅ **Tendência 5m alinhada**: EMA 9 > EMA 21 e inclinada para cima
2. ✅ **Tendência 1m alinhada**: EMA 9 > EMA 21 e inclinada para cima
3. ✅ **Candle forte**: Close > High do candle anterior
4. ✅ **Volume acima da média**: Volume atual > média dos últimos 20 candles
5. ✅ **Spread aceitável**: Spread < 0.1%

### Saída

- **Take Profit**: +0.5% (configurável)
- **Stop Loss**: -0.4% (configurável)
- **1 trade por vez por par**: Evita sobreposição

## 📝 Logs e Banco de Dados SQLite

Todos os trades são registrados em:

- **CSV**: `trades_log.csv` (padrão)
- **SQLite**: `trades.db` (padrão) - **Sistema completo para aprendizado!**

### O que é salvo no SQLite:

1. **Trades** - Todos os trades executados (compra + venda)
2. **Sinais** - Todos os sinais detectados (mesmo que não executados)
3. **Performance Diária** - Resumo automático por dia
4. **Histórico de Configurações** - Mudanças nos parâmetros do bot

### Como Analisar os Dados:

```bash
# Script interativo de análise
python analyze_db.py
```

O script oferece:
- 📊 Estatísticas gerais de trades
- 🔔 Análise de sinais (executados vs não executados)
- 📅 Performance diária
- 🔍 Queries SQL customizadas
- 🗄️ Estrutura do banco de dados

**📚 Veja o guia completo:** [`doc/sqlite/README.md`](doc/sqlite/README.md)

### Campos Registrados:
- Timestamp, símbolo, preços de entrada/saída
- Quantidade, PnL (%), PnL (USDT)
- Duração, motivo da saída (TP/SL)
- Volume, estratégia usada
- EMAs, volume médio (nos sinais)

## 🔧 Estrutura do Projeto

```
Scalping/
├── main.py                 # Runner principal
├── config.py               # Configurações
├── market_scanner.py       # Scanner de volatilidade
├── websocket_manager.py    # Gerenciador WebSocket
├── strategy.py             # Estratégia EMA 9/21
├── trade_executor.py       # Executor de trades
├── logger.py               # Sistema de logs
├── database.py             # Gerenciador SQLite completo
├── analyze_db.py           # Script de análise do banco
├── requirements.txt        # Dependências
├── env_template.txt        # Template de configuração
├── doc/                    # Documentação completa
│   ├── README.md          # Índice da documentação
│   ├── setup/             # Guias de instalação
│   ├── strategy/          # Documentação da estratégia
│   └── sqlite/            # Guia do SQLite
└── README.md               # Este arquivo
```

## ⚠️ Avisos Importantes

1. **Comece com valores pequenos** para testar
2. **Use SPOT primeiro** antes de migrar para FUTURES
3. **Monitore os logs** regularmente
4. **Ajuste TP/SL** conforme a volatilidade do mercado
5. **Não deixe o bot rodando sem supervisão** nas primeiras semanas

## 🔄 Migração para FUTURES

Quando estiver 100% calibrado em SPOT:

1. Altere `TRADING_MODE=FUTURES` no `.env`
2. Ajuste `TAKE_PROFIT_PCT` e `STOP_LOSS_PCT` (menores, devido à alavancagem)
3. Configure alavancagem na Binance (comece com x2, x3)
4. Teste com valores mínimos primeiro

## 📈 Próximos Passos

- [ ] Trailing stop opcional
- [ ] Filtro de horários (evitar baixa liquidez)
- [ ] Dashboard web para monitoramento
- [ ] Backtesting da estratégia
- [ ] Suporte a múltiplas estratégias

## 🐛 Troubleshooting

### Erro: "API keys inválidas"
- Verifique se as keys estão corretas no `.env`
- Confirme que as keys têm permissão de trading

### Erro: "Saldo insuficiente"
- Mínimo necessário: $10 USDT
- Verifique seu saldo na Binance

### Bot não encontra pares
- Reduza `MIN_VOLUME_24H` no `.env`
- Verifique sua conexão com a internet

## 📄 Licença

Este projeto é para uso educacional. Use por sua conta e risco.

---

**Desenvolvido para operações rápidas e repetitivas. Scalping bom é feio: take pequeno, stop pequeno, muitas tentativas por dia.** 🚀

