from __future__ import absolute_import, unicode_literals
from celery import shared_task

from silo.custom_csv_dict_reader import CustomDictReader
from tola.util import save_data_to_silo
from .models import Silo, Read, CeleryTask

from django.contrib.contenttypes.models import ContentType

import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, retry=False)
def process_silo(self, silo_id, read_id):
    silo = Silo.objects.get(id=silo_id)
    read_obj = Read.objects.get(pk=read_id)

    ctype = ContentType.objects.get_for_model(Read)
    task = CeleryTask.objects.get(content_type=ctype, object_id=read_obj.id)
    task.task_status = CeleryTask.TASK_IN_PROGRESS
    task.save()

    try:
        reader = CustomDictReader(read_obj.file_data)
        save_data_to_silo(silo, reader, read_obj)
        task.task_status = CeleryTask.TASK_FINISHED
    except TypeError, e:
        logger.error(e)
        task.task_status = CeleryTask.TASK_FAILED

    task.save()
    # Todo add notification when done
    return True
