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
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)

    # Files
    file = models.FileField(upload_to="datasets/")
    cover_image = models.ImageField(upload_to="datasets/covers/", blank=True, null=True)

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
        return f"{self.name} ({self.dataset_id})"

    def save(self, *args, **kwargs):
        if not self.dataset_id:
            self.dataset_id = generate_dataset_id()
        super().save(*args, **kwargs)

    @property
    def likes_count(self):
        return self.liked_by.count()

    @property
    def popularity(self):
        return self.downloads * 2 + self.views + self.likes_count * 3

    def is_visible_to(self, user):
        """Check if a user can see this dataset"""
        if not self.is_private:
            return True
        if not user.is_authenticated:
            return False
        return user == self.owner or user in self.allowed_users.all()

    def can_edit(self, user):
        return user == self.owner

    def can_delete(self, user):
        return user == self.owner
