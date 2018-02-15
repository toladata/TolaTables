import logging
import sys

from django.core.management import call_command
from django.test import TestCase

from silo.models import Country, ReadType, TolaSites


class DevNull(object):
    def write(self, data):
        pass


class LoadInitialDataTest(TestCase):
    def setUp(self):
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = DevNull()
        sys.stderr = DevNull()
        logging.disable(logging.ERROR)

    def tearDown(self):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        logging.disable(logging.NOTSET)

    def test_load_basic_data(self):
        args = []
        opts = {}
        call_command('loadinitialdata', *args, **opts)

        ReadType.objects.get(read_type="ONA")
        Country.objects.get(code="AF")
        TolaSites.objects.get(name="Track")

    def test_load_basic_data_two_times_no_crash(self):
        args = []
        opts = {}
        call_command('loadinitialdata', *args, **opts)
        call_command('loadinitialdata', *args, **opts)

        # We make sure it only returns one unique object of each model
        ReadType.objects.get(read_type="ONA")
        Country.objects.get(code="AF")
        TolaSites.objects.get(name="Track")
