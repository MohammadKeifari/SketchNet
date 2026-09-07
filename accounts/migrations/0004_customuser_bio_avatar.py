from django.db import migrations, models
import accounts.models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_remove_customuser_theme"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="avatar",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=accounts.models.avatar_upload_path,
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="bio",
            field=models.TextField(blank=True, max_length=280),
        ),
    ]
