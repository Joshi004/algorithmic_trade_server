# Generated manually to create scanner_instances table

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('trade_management_unit', '0001_create_scanning_algorithm'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScannerInstance',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('frequency', models.CharField(max_length=10)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('algorithm', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='scanner_instances',
                    to='trade_management_unit.scanningalgorithm'
                )),
            ],
            options={
                'db_table': 'scanner_instances',
                'indexes': [
                    models.Index(fields=['algorithm', 'frequency', 'is_active'], name='idx_scanner_algo_freq_active'),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='scannerinstance',
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True),
                fields=['algorithm', 'frequency'],
                name='unique_active_scanner_per_algo_freq'
            ),
        ),
    ] 