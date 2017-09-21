# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-25 09:28
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('silo', '0022_merge_20170728_0600'),
    ]

    operations = [
        migrations.AddField(
            model_name='tolauser',
            name='workflowlevel1',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='silo.WorkflowLevel1'),
        ),
        migrations.AlterField(
            model_name='workflowlevel2',
            name='workflowlevel1',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='silo.WorkflowLevel1'),
        ),
    ]
