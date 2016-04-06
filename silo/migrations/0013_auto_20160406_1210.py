# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('silo', '0012_country_tolauser'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tolasites',
            name='activity_url',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='tolasites',
            name='agency_name',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='tolasites',
            name='agency_url',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='tolasites',
            name='name',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
