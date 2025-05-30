from django.db import migrations, models
import django.utils.timezone
from django_mysql.models import EnumField


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='UserBrokerCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('user_id', models.CharField(max_length=64)),
                ('broker_name', EnumField(choices=[('zerodha', 'zerodha')], default='zerodha')),
                ('api_key', models.CharField(max_length=255)),
                ('api_secret', models.CharField(max_length=255)),
                ('access_token', models.CharField(blank=True, max_length=255, null=True)),
                ('refresh_token', models.CharField(blank=True, max_length=255, null=True)),
                ('token_expiry', models.DateTimeField(blank=True, null=True)),
                ('status', EnumField(choices=[('active', 'active'), ('revoked', 'revoked'), ('expired', 'expired')], default='active')),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'user_broker_credentials',
            },
        ),
        migrations.AddIndex(
            model_name='userbrokerCredential',
            index=models.Index(fields=['user_id'], name='user_broker__user_id_4b7c3a_idx'),
        ),
        migrations.AddIndex(
            model_name='userbrokerCredential',
            index=models.Index(fields=['broker_name'], name='user_broker__broker__6e9c2f_idx'),
        ),
        migrations.AddIndex(
            model_name='userbrokerCredential',
            index=models.Index(fields=['status'], name='user_broker__status_9d8e5e_idx'),
        ),
    ] 