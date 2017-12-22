import requests, json, logging
from requests.auth import HTTPDigestAuth
from requests.exceptions import Timeout

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import MultipleObjectsReturned

from silo.models import LabelValueStore, Read, ReadType, Silo, ThirdPartyTokens
from tola.util import  saveDataToSilo

class Command(BaseCommand):
    """
    Usage: python manage.py get_all_ona_forms --f weekly
    """
    help = 'Fetches all reads that have autopull_frequency checked and belong to a silo'

    logger = logging.getLogger("silo")

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
                try:
                    ona_token = ThirdPartyTokens.objects.get(user=silo.owner.pk, name="ONA")
                except MultipleObjectsReturned as e:
                    self.logger.error("get_all_ona_forms token error: silo_id=%s, read_id=%s" % (silo.pk, read.pk))
                    self.logger.error(e)
                    continue
                try:
                    response = requests.get(read.read_url, headers={'Authorization': 'Token %s' % ona_token.token}, timeout=10)
                except Timeout:
                    self.logger.error("get_all_ona_forms timeout error: silo_id=%s, read_id=%s" % (silo.pk, read.pk))
                    continue

                data = json.loads(response.content)

                try:
                    saveDataToSilo(silo, data, read, silo.owner.pk)
                    self.stdout.write('Successfully fetched the READ_ID, "%s", from ONA' % read.pk)
                except TypeError as e:
                    self.logger.error("get_all_ona_forms type error: silo_id=%s, read_id=%s" % (silo.pk, read.pk))
                    self.logger.error(e)
                except UnicodeEncodeError as e:
                    self.logger.error("get_all_ona_forms unicode error: silo_id=%s, read_id=%s" % (silo.pk, read.pk))
                    self.logger.error(e)
