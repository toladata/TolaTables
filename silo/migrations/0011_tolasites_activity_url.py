# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('silo', '0010_tolasites'),
    ]

    operations = [
        migrations.AddField(
            model_name='tolasites',
            name='activity_url',
            field=models.CharField(max_length=b'255', null=True, blank=True),
        ),
    ]
