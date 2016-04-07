import requests, json
from requests.auth import HTTPDigestAuth

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.models import User

from silo.models import *
from tola.util import siloToDict, combineColumns
from silo.google_views import *


class Command(BaseCommand):
    """
    Usage: python manage.py push_to_gsheet --f weekly
    """
    help = 'Pushes all reads that have autopush checked and belong to a silo'

    def add_arguments(self, parser):
        parser.add_argument("-f", "--frequency", type=str, required=True)

    def handle(self, *args, **options):
        frequency = options['frequency']
        if frequency != "daily" and frequency != "weekly":
            return self.stdout.write("Frequency argument can either be 'daily' or 'weekly'")

        # Get all silos that have a unique field setup, have autopush frequency selected and autopush frequency is the same as specified in this command line argument.
        silos = Silo.objects.filter(unique_fields__isnull=False, reads__autopush_frequency__isnull=False, reads__autopush_frequency = frequency).distinct()
        read_types = ReadType.objects.filter(Q(read_type="GSheet Import")|Q(read_type='Google Spreadsheet'))
        for silo in silos:
            reads = silo.reads.filter(reduce(or_, [Q(type=read.id) for read in readtypes])).filter(autopush_frequency__isnull=False, autopush_frequency = frequency)
            for read in reads:
                storage = Storage(GoogleCredentialsModel, 'id', silo.owner, 'credential')
                credential = storage.get()
                credential_json = json.loads(credential.to_json())

                #self.stdout.write("%s" % credential_json)
                if credential is None or credential.invalid == True:
                    self.stdout.write("There was a Google credential problem with user: %s for gsheet %s" % (silo.owner, read.pk))
                    continue

                suc = export_to_google_spreadsheet(credential_json, silo, read.resource_id)
                if suc == False:
                    self.stdout.write("The Google sheet export failed for user: %s  with ghseet: %s" % (silo.owner, read.pk))
                self.stdout.write('Successfully pushed the READ_ID, "%s", to Gsheet for %s' % (read.pk, silo.owner))
        self.stdout.write("done executing gsheet export command job")