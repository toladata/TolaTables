import requests, json
from requests.auth import HTTPDigestAuth

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth.models import User

from silo.models import LabelValueStore, Read, Silo, ThirdPartyTokens, ColumnOrderMapping, siloHideFilter, ReadType
from tola.util import getNewestDataDate

from commcare.tasks import fetchCommCareData, addExtraFields

class Command(BaseCommand):
    """
    python manage.py get_commcare_case_data --f weekly
    """
    help = 'Fetches a specific form data from ONA'

    def add_arguments(self, parser):
        parser.add_argument("-f", "--frequency", type=str, required=True)

    def handle(self, *args, **options):

        frequency = options['frequency']
        if frequency != "daily" and frequency != "weekly":
            return self.stdout.write("Frequency argument can either be 'daily' or 'weekly'")

        silos = Silo.objects.filter(reads__autopull_frequency__isnull=False, reads__autopull_frequency = frequency).distinct()
        read_type = ReadType.objects.get(read_type="CommCare")

        for silo in silos:
            reads = silo.reads.filter(type=read_type.pk)
            for read in reads:
                commcare_token = None
                try:
                    commcare_token = ThirdPartyTokens.objects.get(user=silo.owner.pk, name="CommCare")
                except Exception as e:
                    self.stdout.write('No commcare api key for read, "%s"' % read.pk)
                last_data_retrieved = str(getNewestDataDate(silo.id))[:10]
                url = "/".join(read.read_url.split("/")[:8]) + "?date_modified_start=" + last_data_retrieved + "&" + "limit="
                response = requests.get(url+ str(1), headers={'Authorization': 'ApiKey %(u)s:%(a)s' % {'u' : commcare_token.username, 'a' : commcare_token.token}})
                if response.status_code == 401:
                    commcare_token.delete()
                    self.stdout.write('Incorrect commcare api key READ_ID, "%s"' % read.pk)
                elif response.status_code != 200:
                    self.stdout.write('Falurie retrieving commcare data for READ_ID, "%s"' % read.pk)
                metadata = json.loads(response.content)
                if metadata['meta']['total_count'] == 0:
                    self.stdout.write('No new commcare data for READ_ID, "%s"' % read.pk)

                #Now call the update data function in commcare tasks
                auth = {'Authorization': 'ApiKey %(u)s:%(a)s' % {'u' : commcare_token.username, 'a' : commcare_token.token}}
                url += "50"
                data_raw = fetchCommCareData(url, auth, True, 0, metadata['meta']['total_count'], 50, silo.id, read.id, True)
                data_collects = data_raw.apply_async()
                data_retrieval = [v.get() for v in data_collects]
                columns = set()
                for data in data_retrieval:
                    columns = columns.union(data)
                #correct the columns
                try: columns.remove("")
                except KeyError as e: pass
                try: columns.remove("silo_id")
                except KeyError as e: pass
                try: columns.remove("read_id")
                except KeyError as e: pass
                for column in columns:
                    if "." in column:
                        columns.remove(column)
                        columns.add(column.replace(".", "_"))
                    if "$" in column:
                        columns.remove(column)
                        columns.add(column.replace("$", "USD"))
                try:
                    columns.remove("id")
                    columns.add("user_assigned_id")
                except KeyError as e: pass
                try:
                    columns.remove("_id")
                    columns.add("user_assigned_id")
                except KeyError as e: pass
                try:
                    columns.remove("edit_date")
                    columns.add("editted_date")
                except KeyError as e: pass
                try:
                    columns.remove("create_date")
                    columns.add("created_date")
                except KeyError as e: pass
                #now mass update all the data in the database

                addExtraFields.delay(list(columns), silo.id)
                try:
                    column_order_mapping = ColumnOrderMapping.objects.get(silo_id=silo.id)
                    columns = columns.union(json.loads(column_order_mapping.ordering))
                    column_order_mapping.ordering = json.dumps(list(columns))
                    column_order_mapping.save()
                except ColumnOrderMapping.DoesNotExist as e:
                    ColumnOrderMapping.objects.create(silo_id=silo.id,ordering = json.dumps(list(columns)))
                try:
                    silo_hide_filter = siloHideFilter.objects.get(silo_id=silo.id)
                    hidden_cols = set(json.loads(silo_hide_filter.hiddenColumns))
                    hidden_cols.add("case_id")
                    silo_hide_filter.hiddenColumns = json.dumps(list(hidden_cols))
                    silo_hide_filter.save()
                except siloHideFilter.DoesNotExist as e:
                    siloHideFilter.objects.create(silo_id=silo.id, hiddenColumns=json.dumps(["case_id"]), hiddenRows="[]")
                self.stdout.write('Successfully fetched the READ_ID, "%s", from CommCare' % read.pk)
