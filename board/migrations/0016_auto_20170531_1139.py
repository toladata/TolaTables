# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-05-31 18:39
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('board', '0015_auto_20170530_1346'),
    ]

    operations = [
        migrations.AlterField(
            model_name='graphinput',
            name='graphmodel',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='graphinputs', to='board.Graphmodel'),
        ),
    ]
