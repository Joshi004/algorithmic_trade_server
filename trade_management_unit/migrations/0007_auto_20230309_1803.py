# Generated by Django 3.0 on 2023-03-09 18:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade_management_unit', '0006_auto_20230309_1758'),
    ]

    operations = [
        migrations.AddField(
            model_name='tradesession',
            name='scanning_alogo_id',
            field=models.IntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='tradesession',
            name='closed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='tradesession',
            name='net_profit',
            field=models.FloatField(blank=True, null=True),
        ),
    ]