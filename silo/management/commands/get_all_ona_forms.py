import requests, json
from requests.auth import HTTPDigestAuth

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth.models import User

from silo.models import LabelValueStore, Read, ReadType, Silo, ThirdPartyTokens
from tola.util import  saveDataToSilo

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
        read_type = ReadType.objects.get(read_type="ONA")
        for silo in silos:
            reads = silo.reads.filter(type=read_type.pk)
            for read in reads:
                ona_token = ThirdPartyTokens.objects.get(user=silo.owner.pk, name="ONA")
                response = requests.get(read.read_url, headers={'Authorization': 'Token %s' % ona_token.token})
                data = json.loads(response.content)
                saveDataToSilo(silo, data, read, silo.owner.pk)
                self.stdout.write('Successfully fetched the READ_ID, "%s", from ONA' % read.pk)
