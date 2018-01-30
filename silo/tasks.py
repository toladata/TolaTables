# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task
from celery.result import AsyncResult
from tola.celery import app

from random import randint
from silo.custom_csv_dict_reader import CustomDictReader
from tola.util import importJSON, saveDataToSilo
from .models import Silo, Read

import logging

logger = logging.getLogger("tola")


@shared_task(bind=True, retry=False)
def process_silo(self, silo_id, read_id):
    silo = Silo.objects.get(id=silo_id)
    read_obj = Read.objects.get(pk=read_id)

    try:
        reader = CustomDictReader(read_obj.file_data)
        saveDataToSilo(silo, reader, read_obj)

        # Todo add notification when done
        read_obj.task_id = None
        read_obj.save()
    except Exception, e:
        logger.error(e)
        read_obj.task_id = "FAILED"
        read_obj.save()

    return True


@app.task()
def process_silo_error(uuid, read_id):
    result = AsyncResult(uuid)
    exc = result.get(propagate=False)

    logger.error(exc)

    read_obj = Read.objects.get(pk=read_id)
    read_obj.task_id = "FAILED"
    read_obj.save()

