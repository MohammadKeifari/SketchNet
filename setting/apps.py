from django.apps import AppConfig


class SettingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "setting"

    def ready(self):
        """Register signal handlers when the app is loaded."""
        import setting.signals  # noqa
