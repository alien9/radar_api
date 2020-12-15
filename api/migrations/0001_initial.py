# Generated by Django 3.1.4 on 2020-12-06 02:23

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Radar',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lote', models.IntegerField()),
                ('codigo', models.TextField(max_length=50)),
                ('endereco', models.TextField(max_length=400)),
                ('sentido', models.TextField(max_length=200)),
                ('referencia', models.TextField(max_length=100)),
                ('tipo_equip', models.TextField(max_length=50)),
                ('enquadrame', models.TextField(max_length=20)),
                ('qtde_fxs_f', models.IntegerField()),
                ('data_publi', models.TextField(max_length=50)),
                ('velocidade', models.TextField(max_length=30)),
                ('geom', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('bairro', models.TextField(max_length=300)),
                ('velocidade_cam_oni', models.IntegerField()),
                ('velocidade_carro_moto', models.IntegerField()),
            ],
            options={
                'verbose_name': 'Sensor',
                'db_table': 'base_radares',
            },
        ),
    ]
