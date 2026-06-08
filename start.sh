#!/bin/bash
set -e
echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Seeding database ==="
python manage.py seed || echo "Warning: seed failed, but continuing..."

echo "=== Starting Gunicorn ==="
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
