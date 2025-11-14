# 📊 Estratégia de Scalping - EMA 9/21

Documentação completa da estratégia implementada no bot.

## 🎯 Visão Geral

A estratégia utiliza **médias móveis exponenciais (EMA)** combinadas com **análise de volume** e **ruptura de candles** para identificar oportunidades de entrada em operações de curto prazo.

## 📈 Indicadores Utilizados

### 1. EMA (Exponential Moving Average)

- **EMA 9**: Média móvel exponencial de 9 períodos (rápida)
- **EMA 21**: Média móvel exponencial de 21 períodos (lenta)

**Por que EMA?**
- Responde mais rápido a mudanças de preço que SMA
- Dá mais peso a preços recentes
- Ideal para scalping (operações rápidas)

### 2. Volume

- **Volume Médio**: Média dos últimos 20 candles
- **Volume Atual**: Volume do candle atual

**Filtro de Volume:**
- Só entra quando volume atual > volume médio
- Garante liquidez e confirmação do movimento

### 3. Análise de Candles

- **Candle Forte**: Close > High do candle anterior
- Indica força compradora e continuidade da tendência

## 🔍 Condições de Entrada

O bot entra em uma posição **LONG (compra)** quando **TODAS** as condições abaixo são atendidas:

### ✅ Condição 1: Tendência 5m Alinhada

```
EMA 9 (5m) > EMA 21 (5m)
E
EMA 9 (5m) está inclinada para cima (crescendo)
```

**Por quê?**
- Timeframe maior (5m) confirma a tendência macro
- Evita operar contra a tendência principal

### ✅ Condição 2: Tendência 1m Alinhada

```
EMA 9 (1m) > EMA 21 (1m)
E
EMA 9 (1m) está inclinada para cima (crescendo)
```

**Por quê?**
- Timeframe de entrada (1m) confirma o momento
- Garante que o movimento está ativo

### ✅ Condição 3: Candle Forte

```
Close do candle atual > High do candle anterior
```

**Por quê?**
- Indica força compradora
- Confirma continuidade do movimento
- Evita entrar em candles fracos

### ✅ Condição 4: Volume Acima da Média

```
Volume atual > Volume médio dos últimos 20 candles
```

**Por quê?**
- Confirma interesse real no movimento
- Garante liquidez para entrada/saída
- Evita movimentos "fantasma"

### ✅ Condição 5: Spread Aceitável

```
Spread < 0.1% (configurável)
```

**Por quê?**
- Evita custos excessivos de transação
- Garante melhor execução
- Filtra pares com baixa liquidez

## 🎯 Saída da Posição

### Take Profit (TP)

**Padrão:** +0.5% (configurável)

**Como funciona:**
- Quando o preço atinge `entry_price * (1 + TP%)`, a posição é fechada
- Objetivo: Lucro rápido e consistente

**Ajustes recomendados:**
- Mercado volátil: 0.6% - 0.8%
- Mercado calmo: 0.3% - 0.5%

### Stop Loss (SL)

**Padrão:** -0.4% (configurável)

**Como funciona:**
- Quando o preço atinge `entry_price * (1 - SL%)`, a posição é fechada
- Objetivo: Limitar perdas rapidamente

**Ajustes recomendados:**
- Mercado volátil: -0.5% a -0.7%
- Mercado calmo: -0.3% a -0.4%

### Razão TP/SL

**Padrão:** 1.25:1 (TP 0.5% / SL 0.4%)

**Por quê?**
- TP maior que SL compensa trades perdedores
- Win rate de ~55% já é lucrativo
- Ideal para scalping rápido

## 📊 Exemplo Prático

### Cenário de Entrada

```
Par: BTCUSDT
Preço atual: $50,000

EMA 9 (5m): $50,100 ✅ (acima de EMA 21)
EMA 21 (5m): $49,950 ✅
EMA 9 (1m): $50,050 ✅ (acima de EMA 21)
EMA 21 (1m): $49,980 ✅

Candle atual:
- Close: $50,100 ✅
- High anterior: $50,080 ✅ (Close > High anterior)

Volume atual: 1,500 BTC ✅
Volume médio: 1,200 BTC ✅ (Volume > Média)

Spread: 0.05% ✅ (< 0.1%)
```

**Resultado:** ✅ SINAL DE COMPRA

### Execução

```
Entry Price: $50,100
Take Profit: $50,350 (+0.5%)
Stop Loss: $49,900 (-0.4%)
```

### Cenários de Saída

**Cenário 1: Take Profit**
```
Preço sobe para $50,350
→ Posição fechada com lucro de +0.5%
```

**Cenário 2: Stop Loss**
```
Preço cai para $49,900
→ Posição fechada com perda de -0.4%
```

## ⚙️ Parâmetros Configuráveis

### No arquivo `.env`:

```env
# Períodos das EMAs
EMA_FAST=9              # EMA rápida
EMA_SLOW=21             # EMA lenta

# Timeframes
TIMEFRAME_ENTRY=1m      # Timeframe de entrada
TIMEFRAME_TREND=5m      # Timeframe de tendência

# Volume
VOLUME_PERIOD=20        # Período para volume médio

# Risk Management
TAKE_PROFIT_PCT=0.5     # Take Profit em %
STOP_LOSS_PCT=0.4       # Stop Loss em %

# Filtros
MAX_SPREAD_PCT=0.1      # Spread máximo
```

## 🎓 Ajustes e Otimização

### 1. Ajustar Períodos das EMAs

**EMA mais rápida (menor período):**
- ✅ Mais sensível a mudanças
- ❌ Mais sinais falsos

**EMA mais lenta (maior período):**
- ✅ Menos sinais falsos
- ❌ Sinais mais tardios

**Teste:**
- EMA 7/21 (mais rápida)
- EMA 9/21 (padrão)
- EMA 12/26 (mais lenta)

### 2. Ajustar TP/SL

**TP maior:**
- ✅ Mais lucro por trade
- ❌ Menos trades fecham em TP

**SL menor:**
- ✅ Menos perdas por trade
- ❌ Mais trades fecham em SL

**Teste diferentes razões:**
- 1:1 (TP 0.5% / SL 0.5%)
- 1.25:1 (TP 0.5% / SL 0.4%) ← Padrão
- 1.5:1 (TP 0.6% / SL 0.4%)

### 3. Ajustar Filtro de Volume

**Volume médio maior:**
- ✅ Apenas movimentos fortes
- ❌ Menos oportunidades

**Volume médio menor:**
- ✅ Mais oportunidades
- ❌ Mais sinais falsos

## 📈 Performance Esperada

### Métricas Típicas

- **Win Rate:** 50% - 60%
- **Trades por dia:** 20 - 50 (depende da volatilidade)
- **PnL médio por trade:** +0.1% a +0.3% (após custos)
- **Duração média:** 2 - 10 minutos

### Fatores que Afetam Performance

1. **Volatilidade do mercado**
   - Alta volatilidade = mais oportunidades
   - Baixa volatilidade = menos oportunidades

2. **Liquidez dos pares**
   - Alta liquidez = melhor execução
   - Baixa liquidez = mais slippage

3. **Horário de operação**
   - Horários de maior volume = melhor performance
   - Horários de baixo volume = pior performance

## ⚠️ Limitações da Estratégia

1. **Mercados laterais (ranging)**
   - EMA pode gerar muitos sinais falsos
   - Considere adicionar filtro de ADX

2. **Notícias/Eventos**
   - Movimentos bruscos podem quebrar TP/SL
   - Considere pausar o bot em eventos importantes

3. **Baixa liquidez**
   - Slippage pode afetar resultados
   - Filtre pares com volume adequado

## 🔄 Melhorias Futuras

- [ ] Trailing stop opcional
- [ ] Filtro de ADX (força da tendência)
- [ ] Suporte a múltiplas estratégias
- [ ] Filtro de horários (evitar baixa liquidez)
- [ ] Análise de RSI para evitar sobrecompra

---

**Lembre-se:** A estratégia é uma ferramenta. O sucesso depende de ajustes, monitoramento e disciplina! 📊🚀

