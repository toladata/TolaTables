#!/bin/bash

echo "Migrate"
python manage.py migrate

echo "Creating admin user"
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@humanitec.com', 'admin') if not User.objects.filter(email='admin@humanitec.com').count() else 'Do nothing'"

echo "Loading config fixtures"
python manage.py loaddata fixtures/*.json

echo "Starting celery worker"
sh start-celery.sh

echo "Running the server"
PYTHONUNBUFFERED=1 python manage.py runserver 0.0.0.0:8000
