import requests, json
from requests.auth import HTTPDigestAuth

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth.models import User

from silo.models import LabelValueStore, Read, ReadType, Silo, ThirdPartyTokens
from tola.util import siloToDict, combineColumns

class Command(BaseCommand):
    """
    Usage: python manage.py get_all_ona_forms --f weekly
    """
    help = 'Fetches all reads that have autopull_frequency checked and belong to a silo'

    def add_arguments(self, parser):
        parser.add_argument("-f", "--frequency", type=str, required=True)

    def handle(self, *args, **options):
        frequency = options['frequency']
        if frequency != "daily" and frequency != "weekly":
            return self.stdout.write("Frequency argument can either be 'daily' or 'weekly'")

        silos = Silo.objects.filter(unique_fields__isnull=False, reads__autopull_frequency__isnull=False, reads__autopull_frequency = frequency).distinct()
        read_type = ReadType.objects.get(read_type="JSON")
        for silo in silos:
            reads = silo.reads.filter(type=read_type.pk)
            for read in reads:
                ona_token = ThirdPartyTokens.objects.get(user=silo.owner.pk, name="ONA")
                response = requests.get(read.read_url, headers={'Authorization': 'Token %s' % ona_token.token})
                data = json.loads(response.content)

                # import data into this silo
                num_rows = len(data)
                if num_rows == 0:
                    continue

                counter = None
                #loop over data and insert create and edit dates and append to dict
                for counter, row in enumerate(data):
                    skip_row = False
                    unique_fields_criteria = {}
                    #if the value of unique column is already in existing_silo_data then skip the row
                    for unique_field in silo.unique_fields.all():
                        unique_fields_criteria[unique_field.name] = row[unique_field.name]
                    filter_criteria = {'silo_id': silo.pk}
                    filter_criteria.update(unique_fields_criteria)
                    if LabelValueStore.objects.filter(**filter_criteria).count() > 0:
                        continue
                    # at this point, the unique column value is not in existing data so append it.
                    lvs = LabelValueStore()
                    lvs.silo_id = silo.pk
                    for new_label, new_value in row.iteritems():
                        if new_label is not "" and new_label is not None and new_label is not "edit_date" and new_label is not "create_date":
                            setattr(lvs, new_label, new_value)
                    lvs.create_date = timezone.now()
                    result = lvs.save()

                if num_rows == (counter+1):
                    combineColumns(silo.pk)

                self.stdout.write('Successfully fetched the READ_ID, "%s", from ONA' % read.pk)