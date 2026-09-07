"""
Models for SketchNet's model library Django app.

This module defines the database models for storing and managing sketch models:
- SketchModel: Represents a sketch neural network diagram and its metadata
- ModelAccess: Represents granular access permissions for specific users
- Helper functions for model ID generation and file upload paths
"""

import random
import string
from django.db import models
from django.conf import settings


def generate_model_id():
    """
    Generate a unique 10-character alphanumeric model identifier.
    
    Returns:
        str: A unique model ID that doesn't already exist in the database.
    """
    chars = string.ascii_letters + string.digits
    while True:
        code = "".join(random.choices(chars, k=10))
        if not SketchModel.objects.filter(model_id=code).exists():
            return code


def cover_upload_path(instance, filename):
    """
    Generate the upload path for a model's cover image.
    
    Uses the model ID to organize files: models/covers/{model_id}.{ext}
    
    Args:
        instance (SketchModel): The model instance being saved.
        filename (str): Original filename from the upload.
        
    Returns:
        str: The relative path where the file should be stored.
    """
    ext = "".join(
        c for c in (filename or "").rsplit(".", 1)[-1].lower() if c.isalnum()
    )[:8] or "png"
    return f"models/covers/{instance.model_id}.{ext}"


class SketchModel(models.Model):
    """
    Represents a sketch-based neural network model.
    
    A SketchModel stores the visual graph of a neural network, its metadata,
    and access control information. Each model has an owner and can be forked
    by other users or shared with specific users.
    
    Attributes:
        model_id (str): Unique 10-character identifier (auto-generated on save).
        name (str): Human-readable name of the model.
        description (str): Detailed description of what the model does.
        graph_data (dict): JSON representation of the computation graph.
        cover_image (ImageField): Optional visual thumbnail for the model.
        owner (ForeignKey): User who created this model.
        forked_from (ForeignKey): Parent model if this is a fork (nullable).
        view_access (str): "public" or "private" - who can view this model.
        fork_access (str): "public" or "private" - who can fork this model.
        allowed_users (ManyToMany): Users with special access (through ModelAccess).
        views (int): Number of times this model has been viewed.
        downloads (int): Number of times the model graph has been downloaded.
        forks_count (int): Number of forks of this model.
        liked_by (ManyToMany): Users who have liked this model.
        created_at (DateTimeField): Timestamp of creation.
        updated_at (DateTimeField): Timestamp of last update.
    """
    
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
        """Return a string representation of the model."""
        return f"{self.name} ({self.model_id})"

    def save(self, *args, **kwargs):
        """
        Override save to auto-generate model_id if not present.
        
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        if not self.model_id:
            self.model_id = generate_model_id()
        super().save(*args, **kwargs)

    @property
    def likes_count(self):
        """
        Get the number of users who have liked this model.
        
        Returns:
            int: The count of likes.
        """
        return self.liked_by.count()

    def can_view(self, user):
        """
        Check if a user can view this model.
        
        Viewing is allowed if:
        - Model is public, OR
        - User is authenticated AND is the owner, OR
        - User has explicit view access via ModelAccess
        
        Args:
            user (User): The user to check permissions for.
            
        Returns:
            bool: True if the user can view this model.
        """
        if self.view_access == "public":
            return True
        if not user.is_authenticated:
            return False
        if user == self.owner:
            return True
        access = self.modelaccess_set.filter(user=user).first()
        return access and access.can_view

    def can_fork(self, user):
        """
        Check if a user can fork this model.
        
        Forking is allowed if:
        - User is authenticated AND is the owner, OR
        - Model fork_access is public, OR
        - User has explicit fork access via ModelAccess
        
        Args:
            user (User): The user to check permissions for.
            
        Returns:
            bool: True if the user can fork this model.
        """
        if not user.is_authenticated:
            return False
        if user == self.owner:
            return True
        if self.fork_access == "public":
            return True
        access = self.modelaccess_set.filter(user=user).first()
        return access and access.can_fork

    def can_edit(self, user):
        """
        Check if a user can edit this model.
        
        Only the owner can edit a model.
        
        Args:
            user (User): The user to check permissions for.
            
        Returns:
            bool: True if the user can edit this model.
        """
        return user == self.owner

    def can_delete(self, user):
        """
        Check if a user can delete this model.
        
        Only the owner can delete a model.
        
        Args:
            user (User): The user to check permissions for.
            
        Returns:
            bool: True if the user can delete this model.
        """
        return user == self.owner


class ModelAccess(models.Model):
    """
    Represents granular access permissions for a specific user to a specific model.
    
    This model allows the owner of a private model to grant specific users
    the ability to view and/or fork the model, without making it public.
    
    Attributes:
        user (ForeignKey): The user being granted access.
        model (ForeignKey): The model that access is being granted to.
        can_view (bool): Whether the user can view the model. Defaults to True.
        can_fork (bool): Whether the user can fork the model. Defaults to False.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    model = models.ForeignKey(SketchModel, on_delete=models.CASCADE)
    can_view = models.BooleanField(default=True)
    can_fork = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "model")

    def __str__(self):
        """Return a string representation of the access relationship."""
        return f"{self.user.username} → {self.model.name}"

