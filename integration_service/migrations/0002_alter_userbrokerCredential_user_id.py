from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('integration_service', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userbrokerCredential',
            name='user_id',
            field=models.UUIDField(help_text='References User.public_id'),
        ),
    ] 