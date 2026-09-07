from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("setting", "0003_usersettings_collapse_left_sidebar_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersettings",
            name="default_export_format",
            field=models.CharField(
                choices=[("pytorch-py", "PyTorch (.py)"), ("pytorch-zip", "PyTorch (.zip)")],
                default="pytorch-py",
                help_text="Preferred export format from SketchMod",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="usersettings",
            name="highlight_phase_on_open",
            field=models.CharField(
                choices=[
                    ("none", "None"),
                    ("preprocessing", "Preprocessing"),
                    ("training", "Training"),
                    ("evaluation", "Evaluation"),
                ],
                default="none",
                help_text="Automatically highlight a phase path when opening the canvas",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="usersettings",
            name="public_profile",
            field=models.BooleanField(
                default=False,
                help_text="Show your public models and datasets on a profile page",
            ),
        ),
    ]
