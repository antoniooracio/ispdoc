#!/bin/bash
# entrypoint.sh

# Esperar o banco de dados estar disponível
echo "Aguardando o banco de dados..."
while ! nc -z mariadb 3306; do
  sleep 1
done
echo "Banco de dados disponível!"

# Aplicar as migrations
python manage.py migrate

# Iniciar o servidor
exec "$@"
