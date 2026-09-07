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

    EXPORT_FORMAT_CHOICES = [
        ("pytorch-py", "PyTorch (.py)"),
        ("pytorch-zip", "PyTorch (.zip)"),
    ]
    PHASE_HIGHLIGHT_CHOICES = [
        ("none", "None"),
        ("preprocessing", "Preprocessing"),
        ("training", "Training"),
        ("evaluation", "Evaluation"),
    ]

    default_export_format = models.CharField(
        max_length=20,
        choices=EXPORT_FORMAT_CHOICES,
        default="pytorch-py",
        help_text="Preferred export format from SketchMod",
    )
    highlight_phase_on_open = models.CharField(
        max_length=20,
        choices=PHASE_HIGHLIGHT_CHOICES,
        default="none",
        help_text="Automatically highlight a phase path when opening the canvas",
    )
    public_profile = models.BooleanField(
        default=False,
        help_text="Show your public models and datasets on a profile page",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Settings"
        verbose_name_plural = "User Settings"

    def __str__(self):
        """Return a label identifying the owning user."""
        return f"Settings for {self.user.username}"
