#!/bin/bash

echo "Migrate"
python manage.py migrate

echo "Creating admin user"
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@humanitec.com', 'admin') if not User.objects.filter(email='admin@humanitec.com').count() else 'Do nothing'"

echo "Loading config fixtures"
python manage.py loaddata fixtures/*.json

echo "Starting celery worker"
celery_cmd="celery -A tola worker -l info"
$celery_cmd &

echo "Running the server"
PYTHONUNBUFFERED=1 python manage.py runserver --insecure 127.0.0.1:8000