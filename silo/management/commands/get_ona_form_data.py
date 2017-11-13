import requests, json
from requests.auth import HTTPDigestAuth

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth.models import User

from silo.models import LabelValueStore, Read, Silo, ThirdPartyTokens
from tola.util import  saveDataToSilo

class Command(BaseCommand):
    """
    Usage: python manage.py get_ona_form_data --username mkhan --read_ids 2 9 --silo_id 1
    """
    help = 'Fetches a specific form data from ONA'

    def add_arguments(self, parser):
        parser.add_argument("-u", "--username", type=str, required=True)
        parser.add_argument('--read_ids', nargs='*', type=int)
        parser.add_argument('--silo_id', nargs='?', type=int)

    def handle(self, *args, **options):
        silo = None
        read = None
        silo_id = options['silo_id']
        username = options['username']
        user = User.objects.get(username__exact=username)
        reads = Read.objects.filter(owner=user)

        try:
            silo = Silo.objects.get(pk=silo_id)
        except Silo.DoesNotExist:
            raise CommandError('Silo "%s" does not exist' % silo_id)

        for read_id in options['read_ids']:
            try:
                read = reads.filter(pk=read_id)[0]
            except Read.DoesNotExist:
                raise CommandError('Read "%s" does not exist for user, %s' % (read_id, user.username))

            # Fetch the data from ONA
            ona_token = ThirdPartyTokens.objects.get(user=user.pk, name="ONA")
            response = requests.get(read.read_url, headers={'Authorization': 'Token %s' % ona_token.token})
            data = json.loads(response.content)
            saveDataToSilo(silo, data, read, user)
            self.stdout.write('Successfully fetched the READ_ID, "%s", from database' % read_id)
