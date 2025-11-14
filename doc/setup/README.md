# 🚀 Guia de Instalação e Configuração

Guia completo para instalar e configurar o bot de scalping.

## 📋 Pré-requisitos

- Python 3.8 ou superior
- Conta na Binance com API keys configuradas
- Conexão estável com a internet

## 🔧 Instalação Passo a Passo

### 1. Clone ou Baixe o Projeto

```bash
cd Scalping
```

### 2. Crie um Ambiente Virtual (Recomendado)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instale as Dependências

```bash
pip install -r requirements.txt
```

**Dependências instaladas:**
- `python-binance` - Cliente oficial da Binance
- `websocket-client` - WebSockets para dados em tempo real
- `python-dotenv` - Gerenciamento de variáveis de ambiente
- `pandas` - Manipulação de dados
- `numpy` - Cálculos numéricos
- `ta` - Indicadores técnicos

### 4. Configure as Variáveis de Ambiente

#### 4.1. Crie o arquivo `.env`

Copie o template:

```bash
# Windows
copy env_template.txt .env

# Linux/Mac
cp env_template.txt .env
```

#### 4.2. Configure suas API Keys da Binance

Edite o arquivo `.env` e adicione suas credenciais:

```env
BINANCE_API_KEY=sua_api_key_aqui
BINANCE_API_SECRET=sua_api_secret_aqui
```

**⚠️ IMPORTANTE - Segurança:**
- Use API keys com permissões apenas de **SPOT trading**
- NUNCA compartilhe suas keys
- Não commite o arquivo `.env` no Git (já está no `.gitignore`)
- Para testes, use a testnet da Binance primeiro

#### 4.3. Como Obter API Keys na Binance

1. Acesse https://www.binance.com/
2. Faça login na sua conta
3. Vá em **Perfil** → **API Management**
4. Clique em **Create API**
5. Escolha **System generated** (mais seguro)
6. Complete a verificação de segurança
7. Copie a **API Key** e **Secret Key**
8. Configure as permissões:
   - ✅ Enable Reading
   - ✅ Enable Spot & Margin Trading
   - ❌ NÃO habilite Withdrawals (por segurança)

### 5. Ajuste as Configurações (Opcional)

Edite o `.env` para personalizar o bot:

```env
# Trading Configuration
TRADING_MODE=SPOT              # SPOT ou FUTURES
BASE_CURRENCY=USDT             # Moeda base

# Market Scanner
MIN_VOLUME_24H=30000000        # Volume mínimo em 24h
MIN_PRICE=0.01                 # Preço mínimo do ativo
MAX_PAIRS=3                    # Quantidade de pares para operar

# Strategy Parameters
TIMEFRAME_ENTRY=1m             # Timeframe para entrada
TIMEFRAME_TREND=5m             # Timeframe para tendência
EMA_FAST=9                     # Período EMA rápida
EMA_SLOW=21                    # Período EMA lenta
VOLUME_PERIOD=20               # Período para cálculo de volume médio

# Risk Management
TAKE_PROFIT_PCT=0.5            # Take Profit em %
STOP_LOSS_PCT=0.4              # Stop Loss em %
MAX_SPREAD_PCT=0.1             # Spread máximo aceitável
MAX_SLIPPAGE_PCT=0.05          # Slippage máximo aceitável

# Position Management
MAX_POSITIONS_PER_PAIR=1       # Máximo de posições por par
MAX_TOTAL_POSITIONS=3          # Máximo de posições totais

# Logging
LOG_TO_CSV=true                # Salvar em CSV
LOG_TO_DB=true                 # Salvar em SQLite
LOG_FILE=trades_log.csv        # Arquivo CSV
DB_FILE=trades.db              # Arquivo SQLite
```

## ✅ Verificação da Instalação

### Teste 1: Verificar Python

```bash
python --version
# Deve mostrar Python 3.8 ou superior
```

### Teste 2: Verificar Dependências

```bash
python -c "import binance; print('Binance OK')"
python -c "import pandas; print('Pandas OK')"
python -c "import sqlite3; print('SQLite OK')"
```

### Teste 3: Verificar Configuração

```bash
python -c "from config import Config; print(f'API Key configurada: {bool(Config.API_KEY)}')"
```

## 🧪 Testando com Testnet (Recomendado)

Antes de usar dinheiro real, teste na testnet:

1. Crie uma conta na testnet: https://testnet.binancefuture.com/
2. Obtenha API keys da testnet
3. No `main.py`, altere:

```python
self.client = Client(
    api_key=Config.API_KEY,
    api_secret=Config.API_SECRET,
    testnet=True  # ← Mude para True
)
```

4. Execute o bot e verifique se funciona corretamente

## 🚀 Primeira Execução

### 1. Execute o Bot

```bash
python main.py
```

### 2. O que Esperar

O bot irá:

1. ✅ Conectar à Binance
2. ✅ Escanear o mercado e selecionar top 3 pares
3. ✅ Carregar candles históricos
4. ✅ Conectar WebSockets
5. ✅ Começar a monitorar sinais

### 3. Verificar Logs

- Console: Verá mensagens em tempo real
- CSV: `trades_log.csv` (se habilitado)
- SQLite: `trades.db` (se habilitado)

## 🛑 Parar o Bot

Pressione `Ctrl+C` para parar o bot de forma segura.

## 🔍 Troubleshooting

### Erro: "API keys inválidas"

**Solução:**
- Verifique se as keys estão corretas no `.env`
- Confirme que as keys têm permissão de trading
- Verifique se não há espaços extras nas keys

### Erro: "Saldo insuficiente"

**Solução:**
- Mínimo necessário: $10 USDT
- Verifique seu saldo na Binance
- Para testnet, obtenha fundos de teste

### Erro: "ModuleNotFoundError"

**Solução:**
```bash
pip install -r requirements.txt
```

### Bot não encontra pares

**Solução:**
- Reduza `MIN_VOLUME_24H` no `.env`
- Verifique sua conexão com a internet
- Verifique se a Binance está acessível

### Erro de WebSocket

**Solução:**
- Verifique firewall/antivírus
- Teste conexão com a internet
- Tente novamente após alguns segundos

## 📊 Próximos Passos

Após a instalação:

1. ✅ Leia a [documentação da estratégia](../strategy/README.md)
2. ✅ Aprenda sobre o [sistema SQLite](../sqlite/README.md)
3. ✅ Configure parâmetros conservadores inicialmente
4. ✅ Monitore os primeiros trades de perto
5. ✅ Ajuste conforme necessário

## 🔐 Segurança

**Checklist de Segurança:**

- [ ] API keys com permissões mínimas necessárias
- [ ] `.env` não está no Git (verifique `.gitignore`)
- [ ] Não compartilhe suas keys
- [ ] Use testnet para testes iniciais
- [ ] Comece com valores pequenos
- [ ] Monitore regularmente

---

**Pronto para começar!** 🚀

