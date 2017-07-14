import requests, json, logging
from requests.auth import HTTPDigestAuth

from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth.models import User

from silo.models import *
from silo.gviews_v4 import *
logger = logging.getLogger("silo")

class Command(BaseCommand):
    """
    Usage: python manage.py get_gsheet_data --f weekly
    """
    help = 'Fetches all reads that have autopull_frequency checked and belong to a silo'

    def add_arguments(self, parser):
        parser.add_argument("-f", "--frequency", type=str, required=True)

    def handle(self, *args, **options):
        frequency = options['frequency']
        if frequency != "daily" and frequency != "weekly":
            return self.stdout.write("Frequency argument can either be 'daily' or 'weekly'")

        # get all silos that have a unique field setup, autopull_frequency checked, and the frequency is the same as specified in the command promp
        silos = Silo.objects.filter(unique_fields__isnull=False, reads__autopull_frequency__isnull=False, reads__autopull_frequency = frequency).distinct()
        read_type = ReadType.objects.get(read_type="GSheet Import")
        for silo in silos:
            reads = silo.reads.filter(type=read_type.pk)
            for read in reads:
                msgs = import_from_gsheet_helper(silo.owner, silo.pk, None, read.resource_id, read.gsheet_id)
                for msg in msgs:
                    # if it is not a success message then I want to know
                    if msg.get("level") != 25:
                        # replace with logger
                        logger.error("silo_id=%s, read_id=%s, level: %s, msg: %s" % (silo.pk, read.pk, msg.get("level"), msg.get("msg")))
                        send_mail("Tola-Tables Auto-Pull Failed", "table_id: %s, source_id: %s, %s %s" % (silo.pk, read.pk, msg.get("level"), msg.get("msg")), "tolatables@mercycorps.org", [silo.owner.email], fail_silently=False)
        self.stdout.write("done executing gsheet import command job")
