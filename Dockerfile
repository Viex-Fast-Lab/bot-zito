# Usa uma imagem oficial do Python, leve e atualizada
FROM python:3.11-slim

# Evitar a geração de arquivos pyc e forçar output no console
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Instala dependências nativas (se necessário por algum pacote Python)
# RUN apt-get update && apt-get install -y gcc

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Força a invalidação do cache do Docker abaixo desta linha
ARG CACHEBUST=1

# Copia e instala as dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código-fonte (respeitando o .dockerignore)
COPY . .

# Comando padrão para rodar o bot na VPS
CMD ["python", "bot.py"]
