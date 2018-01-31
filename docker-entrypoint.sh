#!/bin/bash

echo "Collect static files"
python manage.py collectstatic -v 0 --noinput

echo "Migrate"
python manage.py migrate

sh start-celery.sh

echo "Running the server"
nginx
PYTHONUNBUFFERED=1 python manage.py runserver --insecure 127.0.0.1:8888