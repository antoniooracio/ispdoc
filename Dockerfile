FROM python:3.12
LABEL authors="julioNolasco"

WORKDIR /app

# Copia o arquivo de requisitos do projeto
COPY requirements.txt .
# Instalar netcat (openbsd version)
RUN apt-get update && apt-get install -y netcat-openbsd
RUN apt-get update && apt-get install -y iputils-ping
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libpq-dev \
    && apt-get clean
RUN apt update && apt install -y git-lfs
RUN git lfs install

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código do projeto para o contêiner
COPY . .

# Expõe a porta padrão do Django
EXPOSE 9000

# Comando padrão para iniciar o servidor de desenvolvimento do Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:9000"]
