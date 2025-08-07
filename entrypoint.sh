#!/bin/bash

echo "Waiting for Postgres..."

while ! nc -z db 5432; do
  sleep 1
done

echo "Postgres started"

alembic upgrade head

exec "$@"
