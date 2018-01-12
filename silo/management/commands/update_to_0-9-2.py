from django.core.management.base import BaseCommand, CommandError
from silo.models import Silo, UniqueFields, Read

from django.db.models import Q

import pymongo
from django.conf import settings

from datetime import timedelta
from datetime import datetime
import pytz

from collections import deque

import json

class Command(BaseCommand):
    """
    Usage: python manage.py update_to_0-9-2
    """

    def handle(self, *args, **options):

        client = MongoClient(settings.MONGO_URI)
        db = client.get_database(settings.MONGODB_DATABASES['default']['name'])
        #get every column for each silo
        #index by silo
        db.label_value_store.create_index('silo_id')

        silos = Silo.objects.all()
        siloCount = silos.count()
        siloCounter = 0
        errors = []

        for silo in silos:
            siloCounter += 1
            print 'Processing silo %s of %s: %s (%s)' % (siloCounter, siloCount, silo, silo.id)

            keys = set()
            keys_collect = db.label_value_store.map_reduce(
                    "function() {for (var key in this) { emit(key, null); }}",\
                    "function(key, value) {return null;}",\
                    {'inline': 1 }, \
                    query = {"silo_id" : silo.id}, \
                    )
            for key in keys_collect['results']:
                    keys.add(key['_id'])
            keys = keys.difference(['id', 'silo_id', 'read_id', 'create_date', 'edit_date', 'editted_date', '_id'])
            keys = list(keys)
            keys.sort()
            silo.columns = json.dumps(keys)
            silo.save()
            for key in keys:
                results = db.label_value_store.find({'silo_id': silo.id, key : {"$regex" : '^\s+|\s+$'}})
                for result in results:
                    db.label_value_store.update_many(
                        result,
                        {"$set" : {key: result[key].strip()}}
                    )
            #add indexes to unique columns
            #Note that the partialFilterExperession parameter isn't available until MongoDB 3.2
            for column in UniqueFields.objects.filter(silo_id=silo.pk):
                try:
                    db.label_value_store.create_index(column.name, partialFilterExpression = {'silo_id' : silo.id})
                except pymongo.errors.OperationFailure as e:
                    if 'Index with name' in str(e) or 'map file memory' in str(e):
                        errors.append('Silo %s (%s): %s' % (silo, silo.id, e))
                except:
                    raise

            #Now turn that list stored in the database into a dictionary of the proper format
            #this is done seperately since the above script has been run in isolation before
            cols_with_metadata = []
            for col in json.loads(silo.columns):
                cols_with_metadata.append({'name' : col, 'type': 'string'})
            silo.columns = json.dumps(cols_with_metadata)
            silo.save()

        if len(errors):
            print '\nIndexing Errors'
            print '\n'.join(errors)

        #delete all reads that are no longer associated with a silo
        reads = Read.objects.all()
        for read in reads:
            if Silo.objects.filter(reads__pk=read.id).count() == 0:
                read.delete()

        #set expiration dates for current autopulls
        reads = Read.objects.filter(Q(autopull_frequency="weekly") | Q(autopull_frequency="daily"))
        for read in reads:
            read.autopull_expiration = datetime.now(pytz.utc) + timedelta(days=150)
            read.save()

        #set expiration dates for current autopush
        reads = Read.objects.filter(Q(autopush_frequency="weekly") | Q(autopush_frequency="daily"))
        for read in reads:
            read.autopush_expiration = datetime.now(pytz.utc) + timedelta(days=150)
            read.save()
