import random
import string
from django.db import models
from django.conf import settings


def generate_model_id():
    """Generate a unique 10-character alphanumeric ID"""
    chars = string.ascii_letters + string.digits
    while True:
        code = "".join(random.choices(chars, k=10))
        if not SketchModel.objects.filter(model_id=code).exists():
            return code


def cover_upload_path(instance, filename):
    """Upload to models/covers/{model_id}.{ext}"""
    ext = filename.split(".")[-1]
    return f"models/covers/{instance.model_id}.{ext}"


class SketchModel(models.Model):
    VIEW_CHOICES = [
        ("public", "Public"),
        ("private", "Private"),
    ]
    FORK_CHOICES = [
        ("public", "Public"),
        ("private", "Private"),
    ]

    # Identity
    model_id = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Graph data
    graph_data = models.JSONField(default=dict)

    # Cover image
    cover_image = models.ImageField(upload_to=cover_upload_path, blank=True, null=True)

    # Owner
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_models",
    )

    # Fork tracking
    forked_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="forks",
    )

    # Access
    view_access = models.CharField(
        max_length=10, choices=VIEW_CHOICES, default="public"
    )
    fork_access = models.CharField(
        max_length=10, choices=FORK_CHOICES, default="private"
    )

    # Users with special access
    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="ModelAccess",
        related_name="accessible_models",
    )

    # Stats
    views = models.PositiveIntegerField(default=0)
    downloads = models.PositiveIntegerField(default=0)
    forks_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Likes
    liked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_models",
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.model_id})"

    def save(self, *args, **kwargs):
        if not self.model_id:
            self.model_id = generate_model_id()
        super().save(*args, **kwargs)

    @property
    def likes_count(self):
        return self.liked_by.count()

    def can_view(self, user):
        if self.view_access == "public":
            return True
        if not user.is_authenticated:
            return False
        if user == self.owner:
            return True
        access = self.modelaccess_set.filter(user=user).first()
        return access and access.can_view

    def can_fork(self, user):
        if not user.is_authenticated:
            return False
        if user == self.owner:
            return True
        if self.fork_access == "public":
            return True
        access = self.modelaccess_set.filter(user=user).first()
        return access and access.can_fork

    def can_edit(self, user):
        return user == self.owner

    def can_delete(self, user):
        return user == self.owner


class ModelAccess(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    model = models.ForeignKey(SketchModel, on_delete=models.CASCADE)
    can_view = models.BooleanField(default=True)
    can_fork = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "model")

    def __str__(self):
        return f"{self.user.username} → {self.model.name}"
