# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('silo', '0006_auto_20151222_1252'),
    ]

    operations = [
        migrations.CreateModel(
            name='UniqueFields',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=254)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AlterField(
            model_name='googlecredentialsmodel',
            name='id',
            field=models.OneToOneField(related_name='google_credentials', primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='silo',
            name='unique_fields',
            field=models.ManyToManyField(related_name='silos', to='silo.UniqueFields', blank=True),
        ),
    ]
