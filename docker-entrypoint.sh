#!/bin/bash

echo "Collect static files"
python manage.py collectstatic -v 0 --noinput

echo "Migrate"
python manage.py migrate

echo "Starting celery worker"
celery_cmd="celery -A tola worker -l info"
$celery_cmd &

echo "Running the server"
service nginx restart
gunicorn -b 0.0.0.0:8888 tola.wsgi