#!/bin/sh
set -e

if [ "$RUN_MIGRATIONS" != "false" ]; then
  echo "Aplicando migraciones..."
  python manage.py migrate --noinput
fi

if [ "$RUN_MIGRATIONS" != "false" ]; then
  echo "Verificando configuracion de produccion..."
  python manage.py check --deploy
fi

if [ "$COLLECT_STATIC" = "true" ]; then
  echo "Recolectando estaticos..."
  python manage.py collectstatic --noinput
fi

exec "$@"
