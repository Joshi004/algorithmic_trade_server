# Generated by Django 3.2 on 2023-10-28 15:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade_management_unit', '0017_algoudtsscanrecord_instrument_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='tradesession',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False),
        ),
    ]
