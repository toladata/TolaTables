# -*- coding: utf-8 -*-
import logging

from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from django.core.management.base import BaseCommand
from django.db import transaction

import factories

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    Loads initial factories data.

    By default, Read Types, Countries, a Site and TolaSite will be 
    created, if they do not exist yet.
    """

    def _create_site(self):
        Site.objects.get_or_create(name='Track API',
                                   domain='track.toladata.io')

        factories.TolaSites(name='Track', site=get_current_site(None))

    def _create_read_type(self):
        factories.ReadType(
            read_type="ONA",
        )

        factories.ReadType(
            read_type="CSV",
        )

        factories.ReadType(
            read_type="Google Spreadsheet",
        )

        factories.ReadType(
            read_type="GSheet Import",
        )

        factories.ReadType(
            read_type="JSON",
        )

        factories.ReadType(
            read_type="CommCare",
        )

        factories.ReadType(
            read_type="OneDrive",
        )

        factories.ReadType(
            read_type="CustomForm",
        )

    def _create_countries(self):
        factories.Country(
            country="Afghanistan",
            code="AF",
            latitude="34.5333",
            longitude="69.1333",
        )

        factories.Country(
            country="Pakistan",
            code="PK",
            latitude="33.6667",
            longitude="73.1667",
        )

        factories.Country(
            country="Jordan",
            code="JO",
            latitude="31.9500",
            longitude="35.9333",
        )

        factories.Country(
            country="Lebanon",
            code="LB",
            latitude="33.9000",
            longitude="35.5333",
        )

        factories.Country(
            country="Ethiopia",
            code="ET",
            latitude="9.0167",
            longitude="38.7500",
        )

        factories.Country(
            country="Timor-Leste",
            code="TL",
            latitude="-8.3",
            longitude="125.5667",
        )

        factories.Country(
            country="Kenya",
            code="KE",
            latitude="-1.2833",
            longitude="36.8167",
        )

        factories.Country(
            country="Iraq",
            code="IQ",
            latitude="33.3333",
            longitude="44.4333",
        )

        factories.Country(
            country="Nepal",
            code="NP",
            latitude="26.5333",
            longitude="86.7333",
        )

        factories.Country(
            country="Mali",
            code="ML",
            latitude="17.6500",
            longitude="0.0000",
        )

        factories.Country(
            country="United States",
            code="US",
            latitude="45",
            longitude="-120",
        )

        factories.Country(
            country="Turkey",
            code="TR",
            latitude="39.9167",
            longitude="32.8333",
        )

        factories.Country(
            country="Syrian Arab Republic",
            code="SY",
            latitude="33.5000",
            longitude="36.3000",
        )

        factories.Country(
            country="China",
            code="CN",
        )

        factories.Country(
            country="India",
            code="IN",
        )

        factories.Country(
            country="Indonesia",
            code="ID",
        )

        factories.Country(
            country="Mongolia",
            code="MN",
        )

        factories.Country(
            country="Myanmar",
            code="MY",
            latitude="21.9162",
            longitude="95.9560",
        )

        factories.Country(
            country="Palestine",
            code="PS",
            latitude="31.3547",
            longitude="34.3088",
        )

        factories.Country(
            country="South Sudan",
            code="SS",
            latitude="6.8770",
            longitude="31.3070",
        )

        factories.Country(
            country="Uganda",
            code="UG",
            latitude="1.3733",
            longitude="32.2903",
        )

        factories.Country(
            country="Germany",
            code="DE",
            latitude="51.1657",
            longitude="10.4515",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Creating basic data')
        self._create_site()
        self._create_countries()
        self._create_read_type()
