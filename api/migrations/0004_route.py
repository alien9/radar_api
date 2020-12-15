# Generated by Django 3.1.4 on 2020-12-11 02:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_contagem_trajeto_viagem'),
    ]

    operations = [
        migrations.CreateModel(
            name='Route',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('origem', models.IntegerField()),
                ('destino', models.IntegerField()),
                ('dist', models.FloatField()),
            ],
            options={
                'verbose_name': 'Rotas',
                'db_table': 'route',
            },
        ),
    ]
