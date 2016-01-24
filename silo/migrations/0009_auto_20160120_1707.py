# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silo', '0008_mergedsilosfieldmapping'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mergedsilosfieldmapping',
            name='merged_silo',
            field=models.OneToOneField(related_name='merged_silo_mappings', to='silo.Silo'),
        ),
    ]
