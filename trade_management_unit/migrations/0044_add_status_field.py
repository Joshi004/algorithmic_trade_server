# Custom migration to add status field to TradeSession
from django.db import migrations
import django_mysql.models


class Migration(migrations.Migration):

    dependencies = [
        ('trade_management_unit', '0043_fix_tradesession_user_foreign_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='tradesession',
            name='status',
            field=django_mysql.models.EnumField(
                choices=[('started', 'Started'), ('paused', 'Paused'), ('stopped', 'Stopped')], 
                default='started'
            ),
        ),
    ] 