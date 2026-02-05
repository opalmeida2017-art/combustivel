# Usa uma imagem estável do Python (Debian Bookworm) para evitar erros de pacote
FROM python:3.9-slim-bookworm

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema operacional necessárias
# Removemos 'software-properties-common' que estava dando erro
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requisitos e instala as bibliotecas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o resto do seu código para dentro do container
COPY . .

# Cria a pasta de fotos (caso não exista) para evitar erros de permissão
RUN mkdir -p fotos_abastecimento

# Expõe a porta padrão do Streamlit
EXPOSE 8501

# Comando de verificação de saúde (Healthcheck)
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Comando para iniciar o aplicativo
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]