#!/bin/bash
set -e
python manage.py migrate --noinput
python manage.py seed
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
