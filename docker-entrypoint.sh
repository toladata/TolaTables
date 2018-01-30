#!/bin/bash

echo "Collect static files"
python manage.py collectstatic -v 0 --noinput

echo "Migrate"
python manage.py makemigrations
python manage.py migrate

echo "Starting celery worker"
celery_cmd="celery -A tola worker -l info"
$celery_cmd &

echo "Running the server"
nginx
PYTHONUNBUFFERED=1 python manage.py runserver --insecure 127.0.0.1:8888