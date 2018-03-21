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
        foundSilos = set()
        recordsUpdated = []
        multiMod = []

        # sampleRecords = db.label_value_store.find({"silo_id": {"$in": [175, 891, 996, 981, 1342, 1576]}})
        # print sampleRecords.count()
        # for r in sampleRecords:
        #     print 's=', r['silo_id']
        # import sys
        # print 'done'
        # sys.exit()

        autoPushEnabled = list(Silo.objects.filter(reads__autopush_frequency__isnull=False).values_list('pk', flat=True))
        problemSilos = {}
        diffSamples = []
        diffInclude = ['5731956873abe223358d3a74', '57a473d005e48c0fdd83cdb8']
        rCountBefore = db.label_value_store.count()

        for record in db.label_value_store.find({}):
            for key in record:
                try:
                    newVal = record[key].strip()
                except:
                    continue
                # print 'new', newVal
                # print '|val=%s newval=%s' % (record[key], newVal)
                if newVal != record[key]:
                    # print all diffs to console and save some samples for later
                    diff = 'silo %s: different new=|%s| old=|%s|, key=%s, _id=%s' % \
                        (record['silo_id'],
                        smart_str(newVal),
                        smart_str(record[key]),
                        smart_str(key),
                        record['_id'])
                    print diff
                    if (random.random() > .99 and len(diffSamples) <=15) \
                            or str(record['_id']) in diffInclude:
                        diffSamples.append(diff)

                    # There could be problems with the GSheet data if the auto-push
                    # has already taken place.  This lets us highlight potential problems
                    if record['silo_id'] in autoPushEnabled:
                        try:
                            problemSilos[record['silo_id']].append(key)
                        except KeyError:
                            problemSilos[record['silo_id']] = [key]
                    foundSilos.add(record['silo_id'])

                    # Only perform the update if the --write flag is thrown
                    if options['write']:
                        rid = ObjectId(record['_id'])
                        result = db.label_value_store.update_one(
                                        {'_id': rid},
                                        {'$set': {key : newVal}}
                                    )

                        # Hightlight any places where we updated more than one record
                        if result.matched_count > 1:
                            multiMod.append((rid, key))

                        recordsUpdated.append({
                            'mongo_id': record['_id']
                        })


            counter += 1
            # if counter >= 50000:
            #     break

        print '\n#########################################'
        print '#########################################'
        print ''
        print '\nDiff samples:'
        print '\n'.join(diffSamples)
        print ''
        print 'Records count before', rCountBefore
        print 'Records count after', db.label_value_store.count()
        print '\n%s records examined\n' % counter
        print '%s silos with extra whitespace:' % len(foundSilos)
        print ', '.join(sorted([str(i) for i in foundSilos]))
        print '\nMultimods (hopefully empty):', multiMod
        print ''
        print '%s records updated.  If value is 0 you may not have used the --write option.\n' % len(recordsUpdated)
        if len(problemSilos) > 0:
            print "These silos had extra whitespace and are on the auto-push list:"
            for silo in problemSilos:
                print 'silo_id %s: %s' % (silo, ', '.join(problemSilos[silo]))
        else:
            print "There were no silos that had extra whitespace and that were auto-push"
