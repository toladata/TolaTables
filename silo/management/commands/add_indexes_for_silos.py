from django.core.management.base import BaseCommand, CommandError
from silo.models import Silo, UniqueFields

from pymongo import MongoClient
from django.conf import settings

import json

class Command(BaseCommand):
    """
    Usage: python manage.py add_indexes_for_silos.py
    """
    help = 'Adds every column that exists in mongodb to the list of columns in the mysql database per silo'

    def handle(self, *args, **options):
        #get every column for each silo
        db = MongoClient(settings.MONGODB_HOST).tola
        silos = Silo.objects.all()
        db.label_value_store.create_index('silo_id')
        for silo in silos:
            for column in UniqueFields.objects.filter(silo_id=silo.pk):
                db.label_value_store.create_index(column.name, partialFilterExpression = {'silo_id' : silo.id})
