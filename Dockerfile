FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Criar usuário não-root
RUN useradd -m -u 1000 botuser && \
    mkdir -p /app/logs && \
    chown -R botuser:botuser /app

# Copiar código da aplicação
COPY app/ ./app/
COPY *.py ./

# Mudar para usuário não-root
USER botuser

# Criar diretório de logs
RUN mkdir -p /app/logs

CMD ["python", "-m", "app.main", "run"]

