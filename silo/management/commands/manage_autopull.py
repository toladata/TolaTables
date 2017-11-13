from django.core.management.base import BaseCommand, CommandError
from silo.models import Silo, UniqueFields, Read

from django.db.models import Q

from pymongo import MongoClient
from django.conf import settings

from datetime import timedelta
from datetime import datetime

from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site

from django.core.urlresolvers import reverse
from django.conf import settings

import requests

import json

class Command(BaseCommand):
    """
    Usage: python manage.py manage_autopull
    """

    def handle(self, *args, **options):
        #not using a timezone here is fine since the timing doesn't have to be fine tuned

        #autopull
        #send the email for 10 days
        reads = Read.objects.filter((Q(autopull_frequency="weekly") | Q(autopull_frequency="daily")) & Q(autopull_expiration__gte=timedelta(days=10) + datetime.today()))
        for read in reads:
            try:
                url = reverse('renewsAutoJobs', kwargs={'read_pk' : read.pk, 'operation' : 'pull'})
                url = 'https://%s/%s' % (get_current_site(None).domain, 'renew_auto/%i/pull/' % read.id)
                subject = "Renew autopull for Tola Tables"
                message = "Your autopull for your import %s is about to expire. Go to this url to renew it %s." % (read.read_name, url)
                send_mail(subject,
                            message,
                            settings.EMAIL_HOST_USER,
                            [read.owner.email])
            except BadHeaderError:
                return HttpResponse('Invalid header found.')

        # remove autopull that has expired
        reads = Read.objects.filter((Q(autopull_frequency="weekly") | Q(autopull_frequency="daily")) & Q(autopull_expiration__lte= datetime.today()))
        for read in reads:
            read.autopull_frequency = "DISABLED"
            read.autopull_expiration = None
            read.save()


        #autopush
        #send the email for 10 days
        reads = Read.objects.filter((Q(autopush_frequency="weekly") | Q(autopush_frequency="daily")) & Q(autopush_expiration__gte=timedelta(days=10) + datetime.today()))
        for read in reads:
            try:
                url = reverse('renewsAutoJobs', kwargs={'read_pk' : read.pk, 'operation' : 'push'})
                url = 'https://%s/%s' % (get_current_site(None).domain, 'renew_auto/%i/push/' % read.id)
                subject = "Renew autopush for Tola Tables"
                message = "Your autopush for your import %s is about to expire. Go to this url to renew it %s." % (read.read_name, url)
                send_mail(subject,
                            message,
                            'systems@mercycorps.org',
                            [read.owner.email])
            except BadHeaderError:
                return HttpResponse('Invalid header found.')

        # remove autopush that has expired
        reads = Read.objects.filter((Q(autopush_frequency="weekly") | Q(autopush_frequency="daily")) & Q(autopush_expiration__lte= datetime.today()))
        for read in reads:
            read.autopush_frequency = "DISABLED"
            read.autopush_expiration = None
            read.save()
