import requests, json
from requests.auth import HTTPDigestAuth

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth.models import User

from silo.models import *
from tola.util import siloToDict, combineColumns
from silo.google_views import *


class Command(BaseCommand):
    """
    Usage: python manage.py get_gsheet_data --f weekly
    """
    help = 'Fetches all reads that have autopull checked and belong to a silo'

    def add_arguments(self, parser):
        parser.add_argument("-f", "--frequency", type=str, required=True)

    def handle(self, *args, **options):
        frequency = options['frequency']
        if frequency != "daily" and frequency != "weekly":
            return self.stdout.write("Frequency argument can either be 'daily' or 'weekly'")

        # get all silos that have a unique field setup, autopull checked, and the frequency is the same as specified in the command promp
        silos = Silo.objects.filter(unique_fields__isnull=False, reads__autopull=True, reads__autopull_frequency__isnull=False, reads__autopull_frequency = frequency).distinct()
        read_type = ReadType.objects.get(read_type="GSheet Import")
        for silo in silos:
            reads = silo.reads.filter(type=read_type.pk)
            for read in reads:
                # get gsheet authorized client and the gsheet id to fetch its data into the silo
                storage = Storage(GoogleCredentialsModel, 'id', silo.owner, 'credential')
                credential = storage.get()
                credential_json = json.loads(credential.to_json())
                #self.stdout.write("%s" % credential_json)
                if credential is None or credential.invalid == True:
                    self.stdout.write("There was a Google credential problem with user: %s for gsheet %s" % (silo.owner, read.pk))
                    continue

                suc = import_from_google_spreadsheet(credential_json, silo, read.resource_id)
                if suc == False:
                    self.stdout.write("The Google sheet import failed for user: %s  with ghseet: %s" % (silo.owner, read.pk))
                self.stdout.write('Successfully fetched the READ_ID, "%s", from Gsheet for %s' % (read.pk, silo.owner))
        self.stdout.write("done executing gsheet import command job")