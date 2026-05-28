from django.db import models
from django.conf import settings


class UserSettings(models.Model):
    """Stores all user preferences. Created automatically on signup."""

    THEME_CHOICES = [
        ("system", "System"),
        ("light", "Light"),
        ("dark", "Dark"),
        ("rose", "Rose"),
        ("dark-rose", "Dark Rose"),
        ("forest", "Forest"),
        ("forest-dark", "Forest Dark"),
        ("honey", "Honey"),
        ("honey-dark", "Honey Dark"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="settings",
    )

    theme = models.CharField(
        max_length=max(len(value) for value, _ in THEME_CHOICES),
        choices=THEME_CHOICES,
        default="system",
        help_text="Select your preferred color theme",
    )

    collapse_left_sidebar = models.BooleanField(
        default=False,
        help_text="Collapse the left toolbar by default",
    )
    collapse_right_sidebar = models.BooleanField(
        default=False,
        help_text="Collapse the right sidebar by default",
    )

    # Future fields - just comments for now:
    # editor_font_size = models.IntegerField(default=14)
    # auto_save_interval = models.IntegerField(default=60)
    # email_notifications = models.BooleanField(default=True)
    # public_profile = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Settings"
        verbose_name_plural = "User Settings"

    def __str__(self):
        return f"Settings for {self.user.username}"
