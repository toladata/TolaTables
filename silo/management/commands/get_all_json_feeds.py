import logging
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from silo.models import  Read, ReadType, Silo
from tola.util import importJSON
logger = logging.getLogger("silo")

class Command(BaseCommand):
    """
    Usage: python manage.py get_all_json_feeds --f weekly
    """
    help = 'Fetches all json reads that have autopull_frequency checked and belong to a silo'

    def add_arguments(self, parser):
        parser.add_argument("-f", "--frequency", type=str, required=True)

    def handle(self, *args, **options):
        frequency = options['frequency']
        if frequency != "daily" and frequency != "weekly":
            return self.stdout.write("Frequency argument can either be 'daily' or 'weekly'")

        silos = Silo.objects.filter(unique_fields__isnull=False, reads__autopull_frequency=frequency).distinct()
        read_type = ReadType.objects.get(read_type="JSON")
        #self.stdout.write("silos: %s" % silos.count())
        for silo in silos:
            reads = silo.reads.filter(type=read_type.pk)
            for read in reads:
                result = importJSON(read, silo.owner, None, None, silo.pk, None)
                print(result)
                if result[0] == "error" or result[0] == 40:
                    logger.error("Silo_ID: %s %s" % (result[2], result[1]))
                    send_mail("Tola-Tables Auto-Pull Failed", "table_id: %s, source_id: %s, %s %s" % (silo.pk, read.pk, result[2], result[1]), "tolatables@mercycorps.org", [silo.owner.email], fail_silently=False)