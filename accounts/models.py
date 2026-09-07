from django.contrib.auth.models import AbstractUser
from django.db import models

from data_manager.models import _safe_ext


def avatar_upload_path(instance, filename):
    """Store avatars at avatars/{user_id}.{ext}."""
    ext = _safe_ext(filename, "png")
    ident = instance.pk or "pending"
    return f"avatars/{ident}.{ext}"


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True, blank=False)
    bio = models.TextField(blank=True, max_length=280)
    avatar = models.ImageField(
        upload_to=avatar_upload_path,
        blank=True,
        null=True,
    )

    def __str__(self):
        """Return the username as the string representation."""
        return self.username

    def delete(self, *args, **kwargs):
        """Remove the avatar file before deleting the user row."""
        if self.avatar:
            self.avatar.delete(save=False)
        super().delete(*args, **kwargs)
