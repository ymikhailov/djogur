# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-06-06 01:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='money',
            field=models.IntegerField(default=0),
        ),
    ]
