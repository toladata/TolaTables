from django.core.management.base import BaseCommand, CommandError
from django.utils.encoding import smart_text, smart_str
from django.conf import settings
import pymongo
from bson.objectid import ObjectId
import json
import random
from silo.models import LabelValueStore, Silo


class Command(BaseCommand):
    """
    Usage: python manage.py update_to_0-9-2
    """
    def add_arguments(self, parser):
        parser.add_argument("--write", action='store_true', dest='write')

    def handle(self, *args, **options):

        client  = pymongo.MongoClient(settings.MONGODB_URI)
        db = client.get_database(settings.TOLATABLES_MONGODB_NAME)

        counter = 0
        found_silos = set()
        records_updated = []
        multi_mod = []

        auto_push_enabled = list(Silo.objects.filter(reads__autopush_frequency__isnull=False).values_list('pk', flat=True))
        problem_silos = {}
        diff_samples = []
        diff_include = ['5731956873abe223358d3a74', '57a473d005e48c0fdd83cdb8']
        row_count_before = db.label_value_store.count()

        for record in db.label_value_store.find({}):
            for key in record:
                try:
                    new_val = record[key].strip()
                except:
                    continue
                if new_val != record[key]:
                    diff = 'silo %s: different new=|%s| old=|%s|, key=%s, _id=%s' % \
                        (record['silo_id'],
                        smart_str(new_val),
                        smart_str(record[key]),
                        smart_str(key),
                        record['_id'])
                    print diff
                    if (random.random() > .99 and len(diff_samples) <=15) \
                            or str(record['_id']) in diff_include:
                        diff_samples.append(diff)

                    # There could be problems with the GSheet data if the auto-push
                    # has already taken place.  This lets us highlight potential problems
                    if record['silo_id'] in auto_push_enabled:
                        try:
                            problem_silos[record['silo_id']].append(key)
                        except KeyError:
                            problem_silos[record['silo_id']] = [key]
                    found_silos.add(record['silo_id'])

                    # Only perform the update if the --write flag is thrown
                    if options['write']:
                        rid = ObjectId(record['_id'])
                        result = db.label_value_store.update_one(
                                        {'_id': rid},
                                        {'$set': {key : new_val}}
                                    )

                        # Hightlight any places where we updated more than one record
                        if result.matched_count > 1:
                            multi_mod.append((rid, key))

                        records_updated.append({
                            'mongo_id': record['_id']
                        })


            counter += 1

        print '\n#########################################'
        print '#########################################'
        print ''
        print '\nDiff samples:'
        print '\n'.join(diff_samples)
        print ''
        print 'Records count before', row_count_before
        print 'Records count after', db.label_value_store.count()
        print '\n%s records examined\n' % counter
        print '%s silos with extra whitespace:' % len(found_silos)
        print ', '.join(sorted([str(i) for i in found_silos]))
        print '\nMultimods (hopefully empty):', multi_mod
        print ''
        print '%s records updated.  If value is 0 you may not have used the --write option.\n' % len(records_updated)
        if len(problem_silos) > 0:
            print "These silos had extra whitespace and are on the auto-push list:"
            for silo in problem_silos:
                print 'silo_id %s: %s' % (silo, ', '.join(problem_silos[silo]))
        else:
            print "There were no silos that had extra whitespace and that were auto-push"
