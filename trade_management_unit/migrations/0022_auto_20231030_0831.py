# Generated by Django 3.2 on 2023-10-30 08:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('trade_management_unit', '0021_alter_instrument_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='algosltotrackrecord',
            old_name='recorded_at',
            new_name='zone_change_time',
        ),
        migrations.RemoveField(
            model_name='algosltotrackrecord',
            name='existing_price_zone_time',
        ),
        migrations.RemoveField(
            model_name='algosltotrackrecord',
            name='trade',
        ),
        migrations.AddField(
            model_name='algosltotrackrecord',
            name='trade_session',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='trade_management_unit.tradesession'),
            preserve_default=False,
        ),
    ]