# Generated by Django 5.0.7 on 2024-08-20 06:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MonitoraggioImpianti', '0003_alter_impianto_potenza_business_plan'),
    ]

    operations = [
        migrations.CreateModel(
            name='linkportale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('portale', models.CharField(default='-', max_length=200, verbose_name='Nome portale')),
                ('link', models.CharField(default='-', max_length=250, verbose_name='link-portale')),
            ],
            options={
                'verbose_name': 'Link Portale',
                'verbose_name_plural': 'Link Portali',
            },
        ),
    ]
