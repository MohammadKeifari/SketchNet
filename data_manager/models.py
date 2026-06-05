import random
import string
from django.db import models
from django.conf import settings


def generate_dataset_id():
    """Generate a unique 8-character alphanumeric ID"""
    chars = string.ascii_letters + string.digits
    while True:
        code = "".join(random.choices(chars, k=8))
        if not Dataset.objects.filter(dataset_id=code).exists():
            return code


def default_cover_svg():
    """Return a simple SVG placeholder as default cover"""
    return (
        '<svg viewBox="0 0 200 150" xmlns="http://www.w3.org/2000/svg">'
        '<rect width="200" height="150" fill="#f0f0f0"/>'
        '<text x="100" y="80" text-anchor="middle" fill="#999" font-size="14" font-family="sans-serif">'
        "No Cover"
        "</text></svg>"
    )


def dataset_upload_path(instance, filename):
    """Upload to datasets/{dataset_id}/{filename}"""
    ext = filename.split(".")[-1]
    return f"datasets/{instance.dataset_id}/{instance.dataset_id}.{ext}"


def cover_upload_path(instance, filename):
    """Upload to datasets/covers/{dataset_id}.{ext}"""
    ext = filename.split(".")[-1]
    return f"datasets/covers/{instance.dataset_id}.{ext}"


class Dataset(models.Model):
    FORMAT_CHOICES = [
        ("csv", "CSV"),
        ("json", "JSON"),
        ("xlsx", "Excel"),
        ("parquet", "Parquet"),
        ("rar", "Image Set (RAR)"),
        ("zip", "Image Set (ZIP)"),
        ("other", "Other"),
    ]

    # Identity
    dataset_id = models.CharField(max_length=8, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Shape fields
    user_shape = models.CharField(
        max_length=255, blank=True, null=True, help_text="User-provided shape"
    )
    inferred_shape = models.CharField(
        max_length=255, blank=True, null=True, help_text="Auto-detected shape from file"
    )
    resolved_shape = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Final shape: user > inferred > none",
    )
    shape_known = models.BooleanField(
        default=False, help_text="True if resolved_shape is confirmed"
    )

    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)

    # Files
    file = models.FileField(upload_to=dataset_upload_path)
    cover_image = models.ImageField(upload_to=cover_upload_path, blank=True, null=True)

    # Ownership & Visibility
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="datasets",
    )
    is_private = models.BooleanField(default=False)
    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="accessible_datasets",
        blank=True,
    )

    # Stats
    downloads = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Likes
    liked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_datasets",
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        """Return the dataset name and short ID."""
        return f"{self.name} ({self.dataset_id})"

    def resolve_shape(self):
        """Apply priority: user_shape > inferred_shape > None"""
        if self.user_shape:
            self.resolved_shape = self.user_shape
            self.shape_known = True
        elif self.inferred_shape:
            self.resolved_shape = self.inferred_shape
            self.shape_known = True
        else:
            self.resolved_shape = None
            self.shape_known = False

    def save(self, *args, **kwargs):
        """Assign an ID, resolve shape, then persist the dataset."""
        if not self.dataset_id:
            self.dataset_id = generate_dataset_id()
        self.resolve_shape()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Remove stored files before deleting the database record."""
        # Delete the actual files
        if self.file:
            self.file.delete(save=False)
        if self.cover_image:
            self.cover_image.delete(save=False)
        super().delete(*args, **kwargs)

    @property
    def likes_count(self):
        """Return the number of users who liked this dataset."""
        return self.liked_by.count()

    @property
    def popularity(self):
        """Return a weighted popularity score from downloads, views, and likes."""
        return self.downloads * 2 + self.views + self.likes_count * 3

    def is_visible_to(self, user):
        """Check if a user can see this dataset"""
        if not self.is_private:
            return True
        if not user.is_authenticated:
            return False
        return user == self.owner or user in self.allowed_users.all()

    def can_edit(self, user):
        """Return whether the user is the dataset owner."""
        return user == self.owner

    def can_delete(self, user):
        """Return whether the user is allowed to delete this dataset."""
        return user == self.owner
