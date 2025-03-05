FROM python:3.11-slim

# Instalar dependências do sistema para o psycopg2 e netcat para wait-for-it
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Definir o diretório de trabalho
WORKDIR /app

# Copiar os arquivos de dependências e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código para a imagem
COPY . /app

# Dar permissão de execução para o wait-for-it.sh
RUN chmod +x ./Scripts/wait-for-it.sh

# Comando de inicialização usando wait-for-it para aguardar o PostgreSQL
CMD ["./Scripts/wait-for-it.sh", "db:5432", "--", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
