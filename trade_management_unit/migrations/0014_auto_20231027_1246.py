# Generated by Django 3.2 on 2023-10-27 12:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade_management_unit', '0013_auto_20231027_1237'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userconfiguration',
            name='risk_reward_ratio',
        ),
        migrations.AddField(
            model_name='userconfiguration',
            name='reward_risk_ratio',
            field=models.FloatField(default=2),
        ),
    ]