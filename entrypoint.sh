#!/bin/sh
set -e

cd /app

.venv/bin/alembic upgrade head

exec .venv/bin/python /app/main.py
