#!/bin/bash

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting FastAPI..."
exec "$@"
