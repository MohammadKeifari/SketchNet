from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_customuser_bio_avatar"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="is_guest",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
