# Generated by Django 3.2 on 2023-10-26 19:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade_management_unit', '0010_alter_trade_closed_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trade',
            name='id',
            field=models.BigAutoField(auto_created=True, default='', max_length=64, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='tradesession',
            name='id',
            field=models.BigAutoField(auto_created=True, max_length=64, primary_key=True, serialize=False),
        ),
    ]