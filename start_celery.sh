#!/bin/bash

echo "Starting celery worker"
celery_cmd="celery -A tola worker -l info"
$celery_cmd &
