# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silo', '0007_auto_20160115_1612'),
    ]

    operations = [
        migrations.CreateModel(
            name='MergedSilosFieldMapping',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('mapping', models.TextField()),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('from_silo', models.ForeignKey(related_name='from_mappings', to='silo.Silo')),
                ('merged_silo', models.ForeignKey(related_name='merged_silo_mappings', to='silo.Silo')),
                ('to_silo', models.ForeignKey(related_name='to_mappings', to='silo.Silo')),
            ],
        ),
    ]
