# Generated by Django 3.2 on 2023-11-21 10:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('trade_management_unit', '0037_auto_20231111_1506'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='trade_session',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='trade_management_unit.tradesession', verbose_name='trade_session_id'),
            preserve_default=False,
        ),
    ]