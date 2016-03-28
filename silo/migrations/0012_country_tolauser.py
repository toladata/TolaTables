# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('silo', '0011_tolasites_activity_url'),
    ]

    operations = [
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('country', models.CharField(max_length=255, verbose_name=b'Country Name', blank=True)),
                ('code', models.CharField(max_length=4, verbose_name=b'2 Letter Country Code', blank=True)),
                ('description', models.TextField(max_length=765, verbose_name=b'Description/Notes', blank=True)),
                ('latitude', models.CharField(max_length=255, null=True, verbose_name=b'Latitude', blank=True)),
                ('longitude', models.CharField(max_length=255, null=True, verbose_name=b'Longitude', blank=True)),
                ('create_date', models.DateTimeField(null=True, blank=True)),
                ('edit_date', models.DateTimeField(null=True, blank=True)),
            ],
            options={
                'ordering': ('country',),
                'verbose_name_plural': 'Countries',
            },
        ),
        migrations.CreateModel(
            name='TolaUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(blank=True, max_length=3, null=True, choices=[(b'mr', b'Mr.'), (b'mrs', b'Mrs.'), (b'ms', b'Ms.')])),
                ('name', models.CharField(max_length=100, null=True, verbose_name=b'Given Name', blank=True)),
                ('employee_number', models.IntegerField(null=True, verbose_name=b'Employee Number', blank=True)),
                ('activity_api_token', models.CharField(max_length=255, null=True, blank=True)),
                ('privacy_disclaimer_accepted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(null=True, blank=True)),
                ('updated', models.DateTimeField(null=True, blank=True)),
                ('country', models.ForeignKey(blank=True, to='silo.Country', null=True)),
                ('user', models.OneToOneField(related_name='tola_user', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
