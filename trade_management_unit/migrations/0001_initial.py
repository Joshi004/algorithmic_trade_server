# Generated by Django 3.2 on 2023-08-28 11:28

from django.db import migrations, models
import django.db.models.deletion
import django_mysql.models
from trade_management_unit.lib.common.Utils.Utils import *

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('name', models.CharField(max_length=225)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Instrument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instrument_token', models.BigIntegerField()),
                ('exchange_token', models.BigIntegerField()),
                ('trading_symbol', models.CharField(db_index=True, max_length=200)),
                ('name', models.CharField(db_index=True, max_length=200)),
                ('last_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('expiry', models.DateField(null=True)),
                ('strike', models.DecimalField(decimal_places=2, max_digits=10)),
                ('tick_size', models.DecimalField(decimal_places=4, max_digits=10)),
                ('lot_size', models.IntegerField()),
                ('instrument_type', models.CharField(max_length=50)),
                ('segment', models.CharField(max_length=50)),
                ('exchange', models.CharField(db_index=True, max_length=50)),
            ],
            options={
                'db_table': 'instruments',
            },
        ),
        migrations.CreateModel(
            name='TradeSession',
            fields=[
                ('id', models.CharField(auto_created=True, default='', max_length=64, primary_key=True, serialize=False)),
                ('started_at', models.DateTimeField()),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                ('net_profit', models.FloatField(blank=True, null=True)),
                ('is_closed', models.BooleanField(default=False)),
                ('scanning_alogo_id', models.CharField(default='', max_length=64)),
            ],
            options={
                'db_table': 'trade_sessions',
            },
        ),
        migrations.CreateModel(
            name='Trade',
            fields=[
                ('id', models.CharField(auto_created=True, default='', max_length=64, primary_key=True, serialize=False)),
                ('started_at', models.DateTimeField()),
                ('closed_at', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('trading_alog_id', models.CharField(default='', max_length=64)),
                ('net_profit', models.FloatField(blank=True, null=True)),
                ('instrument', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trade_management_unit.instrument', verbose_name='Ordered Instrument')),
                ('trade_session', models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='trade_management_unit.tradesession', verbose_name='Trade Session')),
            ],
            options={
                'db_table': 'trades',
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.CharField(auto_created=True, default='', max_length=64, primary_key=True, serialize=False)),
                ('status', django_mysql.models.EnumField(choices=[('pending', 'pending'), ('rejected', 'rejected'), ('exicuted', 'exicuted')], default='pending')),
                ('order_type', django_mysql.models.EnumField(choices=[('buy', 'buy'), ('sell', 'sell')])),
                ('started_at', models.DateTimeField(default=current_ist)),
                ('closed_at', models.DateTimeField(blank=True, default=current_ist)),
                ('instrument', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trade_management_unit.instrument', verbose_name='instrument_id')),
                ('trade', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trade_management_unit.trade', verbose_name='trade_id')),
            ],
            options={
                'db_table': 'orders',
            },
        ),
        migrations.AddIndex(
            model_name='instrument',
            index=models.Index(fields=['trading_symbol'], name='instruments_trading_107c4c_idx'),
        ),
        migrations.AddIndex(
            model_name='instrument',
            index=models.Index(fields=['name'], name='instruments_name_9d146b_idx'),
        ),
        migrations.AddIndex(
            model_name='instrument',
            index=models.Index(fields=['exchange'], name='instruments_exchang_ea4098_idx'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='groups',
            field=models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='user_permissions',
            field=models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions'),
        ),
    ]
