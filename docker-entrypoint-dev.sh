#!/bin/bash

echo "Migrate"
python manage.py migrate

echo "Creating admin user"
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@humanitec.com', 'admin') if not User.objects.filter(email='admin@humanitec.com').count() else 'Do nothing'"

echo "Loading basic initial data"
python manage.py loadinitialdata

echo "Starting celery worker"
celery_cmd="celery -A tola worker -l info -f celery.log"
$celery_cmd &

echo "Running the server"
if [ "$nginx" == "true" ]; then
    PYTHONUNBUFFERED=1 gunicorn -b 0.0.0.0:8080 tola.wsgi --reload
else
    PYTHONUNBUFFERED=1 python manage.py runserver 0.0.0.0:8080
fi
