# Generated by Django 3.1.4 on 2020-12-23 02:08

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_auto_20201221_2154'),
    ]

    operations = [
        migrations.AlterField(
            model_name='route',
            name='dist',
            field=models.FloatField(null=True),
        ),
        migrations.AlterField(
            model_name='route',
            name='geom',
            field=django.contrib.gis.db.models.fields.LineStringField(null=True, srid=4326),
        ),
    ]
