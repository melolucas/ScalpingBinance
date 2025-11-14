# 📚 Guia de Uso do SQLite no Bot de Scalping

Este guia explica como usar o sistema SQLite implementado para aprendizado e análise de dados.

## 🗄️ Estrutura do Banco de Dados

O banco de dados SQLite (`trades.db`) contém **4 tabelas principais**:

### 1. `trades` - Trades Executados
Armazena todos os trades completos (compra + venda).

**Campos principais:**
- `id`: ID único do trade
- `symbol`: Par negociado (ex: BTCUSDT)
- `entry_price`: Preço de entrada
- `exit_price`: Preço de saída
- `pnl_pct`: Lucro/Prejuízo em percentual
- `pnl_usdt`: Lucro/Prejuízo em USDT
- `reason`: Motivo da saída (TAKE_PROFIT, STOP_LOSS)
- `duration_seconds`: Duração do trade em segundos
- `timestamp`: Data/hora do registro

### 2. `signals` - Sinais Detectados
Armazena todos os sinais detectados pela estratégia, mesmo que não tenham virado trade.

**Campos principais:**
- `id`: ID único do sinal
- `symbol`: Par do sinal
- `signal_type`: Tipo (BUY/SELL)
- `price`: Preço no momento do sinal
- `executed`: Se o sinal foi executado (virou trade)
- `trade_id`: ID do trade relacionado (se executado)

**Por que é útil?**
- Analisa quantos sinais não foram executados
- Compara performance de sinais executados vs não executados
- Aprende quais condições geram melhores resultados

### 3. `daily_performance` - Performance Diária
Resumo automático da performance por dia.

**Campos principais:**
- `date`: Data (YYYY-MM-DD)
- `total_trades`: Total de trades no dia
- `winning_trades`: Trades vencedores
- `losing_trades`: Trades perdedores
- `win_rate`: Taxa de acerto (%)
- `total_pnl_usdt`: PnL total do dia
- `avg_pnl_pct`: PnL médio em %

**Atualização automática:** Atualizado a cada trade.

### 4. `bot_configs` - Histórico de Configurações
Registra mudanças nas configurações do bot.

**Útil para:**
- Comparar performance com diferentes configurações
- Entender qual setup funciona melhor

## 🔍 Como Analisar os Dados

### Opção 1: Script de Análise Interativo

Execute o script de análise:

```bash
python analyze_db.py
```

**Menu disponível:**
1. **Análise de Trades** - Estatísticas gerais e últimos trades
2. **Análise de Sinais** - Quantos sinais foram executados
3. **Performance Diária** - Evolução dia a dia
4. **Queries Customizadas** - Exemplos de SQL
5. **Estrutura do Banco** - Ver todas as tabelas
6. **Análise Completa** - Tudo de uma vez

### Opção 2: Usar o Módulo Database Diretamente

```python
from database import Database

# Conecta ao banco
db = Database()

# Busca últimos 10 trades
trades = db.get_trades(limit=10)

# Estatísticas gerais
stats = db.get_statistics()

# Performance dos últimos 30 dias
daily = db.get_daily_performance(days=30)

# Busca trades de um símbolo específico
btc_trades = db.get_trades(symbol='BTCUSDT')

# Queries customizadas
result = db.execute_query('''
    SELECT symbol, COUNT(*) as total
    FROM trades
    GROUP BY symbol
    ORDER BY total DESC
''')
```

## 📊 Exemplos de Queries SQL Úteis

### 1. Trades por Símbolo
```sql
SELECT 
    symbol,
    COUNT(*) as total_trades,
    SUM(pnl_usdt) as total_pnl,
    AVG(pnl_pct) as avg_pnl
FROM trades
GROUP BY symbol
ORDER BY total_pnl DESC;
```

### 2. Win Rate por Razão de Saída
```sql
SELECT 
    reason,
    COUNT(*) as total,
    SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
    AVG(pnl_pct) as avg_pnl
FROM trades
GROUP BY reason;
```

### 3. Melhor Horário para Operar
```sql
SELECT 
    strftime('%H', timestamp) as hour,
    COUNT(*) as trades,
    AVG(pnl_pct) as avg_pnl,
    SUM(pnl_usdt) as total_pnl
FROM trades
GROUP BY hour
ORDER BY avg_pnl DESC;
```

### 4. Duração Média dos Trades
```sql
SELECT 
    AVG(duration_seconds) / 60 as avg_minutes,
    MIN(duration_seconds) / 60 as min_minutes,
    MAX(duration_seconds) / 60 as max_minutes
FROM trades
WHERE duration_seconds IS NOT NULL;
```

### 5. Sequência de Wins/Losses
```sql
SELECT 
    symbol,
    pnl_pct > 0 as is_win,
    COUNT(*) as count
FROM trades
GROUP BY symbol, is_win
ORDER BY symbol, is_win;
```

### 6. Performance por Dia da Semana
```sql
SELECT 
    strftime('%w', date) as day_of_week,
    CASE strftime('%w', date)
        WHEN '0' THEN 'Domingo'
        WHEN '1' THEN 'Segunda'
        WHEN '2' THEN 'Terça'
        WHEN '3' THEN 'Quarta'
        WHEN '4' THEN 'Quinta'
        WHEN '5' THEN 'Sexta'
        WHEN '6' THEN 'Sábado'
    END as day_name,
    AVG(total_pnl_usdt) as avg_daily_pnl,
    AVG(win_rate) as avg_win_rate
FROM daily_performance
GROUP BY day_of_week
ORDER BY avg_daily_pnl DESC;
```

## 🎓 O Que Aprender com os Dados

### 1. **Eficiência da Estratégia**
- Quantos sinais viram trades?
- Qual a taxa de acerto?
- Qual o PnL médio por trade?

### 2. **Melhores Pares**
- Quais símbolos performam melhor?
- Quais têm maior win rate?
- Quais geram mais lucro?

### 3. **Timing**
- Qual horário é melhor para operar?
- Qual dia da semana é mais lucrativo?
- Duração média dos trades vencedores vs perdedores

### 4. **Ajustes de Parâmetros**
- TP/SL ideais
- Melhor configuração de EMA
- Volume mínimo necessário

## 🛠️ Ferramentas Recomendadas

### Para Visualizar o Banco:
1. **DB Browser for SQLite** (gratuito)
   - Download: https://sqlitebrowser.org/
   - Abre o arquivo `trades.db` e explora visualmente

2. **VS Code Extension**
   - Instale a extensão "SQLite Viewer"
   - Abra `trades.db` diretamente no VS Code

### Para Análises Avançadas:
1. **Python + Pandas**
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('trades.db')
df = pd.read_sql_query('SELECT * FROM trades', conn)

# Análises com pandas
print(df.describe())
print(df.groupby('symbol')['pnl_pct'].mean())
```

2. **Jupyter Notebook**
   - Crie análises interativas
   - Gráficos com matplotlib/plotly

## 📈 Exemplo de Análise Completa

```python
from database import Database
import pandas as pd

db = Database()

# 1. Carrega todos os trades
trades = db.get_trades(limit=1000)
df = pd.DataFrame(trades)

# 2. Análise básica
print("Estatísticas Gerais:")
print(f"Total de trades: {len(df)}")
print(f"Win Rate: {(df['pnl_pct'] > 0).sum() / len(df) * 100:.2f}%")
print(f"PnL Total: ${df['pnl_usdt'].sum():.2f}")

# 3. Por símbolo
print("\nPor Símbolo:")
symbol_stats = df.groupby('symbol').agg({
    'pnl_usdt': ['sum', 'mean', 'count'],
    'pnl_pct': 'mean'
})
print(symbol_stats)

# 4. Por razão de saída
print("\nPor Razão de Saída:")
reason_stats = df.groupby('reason').agg({
    'pnl_usdt': ['sum', 'mean', 'count'],
    'pnl_pct': 'mean'
})
print(reason_stats)
```

## 🔄 Backup do Banco

**Importante:** Faça backup regular do `trades.db`!

```bash
# Backup simples
copy trades.db trades_backup.db

# Backup com data
copy trades.db trades_backup_2024-01-15.db
```

## 💡 Dicas

1. **Execute análises regularmente** para entender o que está funcionando
2. **Compare períodos** diferentes (últimos 7 dias vs 30 dias)
3. **Identifique padrões** nos dados (horários, símbolos, condições)
4. **Use os dados para ajustar** a estratégia e parâmetros
5. **Mantenha histórico** - não delete trades antigos, eles são valiosos para aprendizado

---

**Lembre-se:** O SQLite é perfeito para aprendizado porque é simples, não precisa de servidor, e você pode fazer queries diretas para entender seus dados! 🚀

