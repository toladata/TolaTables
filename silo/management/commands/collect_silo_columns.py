from django.core.management.base import BaseCommand, CommandError
from silo.models import Silo

from pymongo import MongoClient
from django.conf import settings

from collections import deque

import json

class Command(BaseCommand):
    """
    Usage: python manage.py collect_silo_columns
    """
    help = 'Adds every column that exists in mongodb to the list of columns in the mysql database per silo'

    def handle(self, *args, **options):
        #get every column for each silo
        db = MongoClient(settings.MONGODB_HOST).tola
        silos = Silo.objects.all()

        for silo in silos:
            keys = set()
            keys_collect = db.label_value_store.map_reduce(
                    "function() {for (var key in this) { emit(key, null); }}",\
                    "function(key, value) {return null;}",\
                    "keys", \
                    query = {"silo_id" : silo.id}, \
                    )
            for key in keys_collect.find():
                keys.add(key['_id'])
            keys = keys.difference(['id', 'silo_id', 'read_id', 'create_date', 'edit_date', 'editted_date', '_id'])
            keys = list(keys)
            keys.sort()
            silo.columns = json.dumps(keys)
            silo.save()
