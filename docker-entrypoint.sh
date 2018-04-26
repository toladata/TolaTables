#!/bin/bash

echo "Migrate"
python manage.py migrate

echo "Starting celery worker"
celery_cmd="celery -A tola worker -l info -f celery.log"
$celery_cmd &

RESULT=$?
if [ $RESULT -eq 0 ]; then
    echo $(date -u) " - Running the server in branch '$branch'"
    service nginx restart
    if [ "$branch" == "dev-v2" ]; then
        gunicorn -b 0.0.0.0:8080 tola.wsgi --reload
    else
        gunicorn -b 0.0.0.0:8080 tola.wsgi
    fi
fi
