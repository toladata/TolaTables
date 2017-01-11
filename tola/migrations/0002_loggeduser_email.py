# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tola', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='loggeduser',
            name='email',
            field=models.CharField(default=b'user@mercycorps.org', max_length=100),
        ),
    ]
