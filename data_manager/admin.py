from django.contrib import admin
from .models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "dataset_id",
        "format",
        "owner",
        "is_private",
        "shape_display",
        "downloads",
        "views",
        "created_at",
    ]
    list_filter = ["format", "is_private", "created_at"]
    search_fields = ["name", "dataset_id", "owner__username", "owner__email"]
    readonly_fields = [
        "dataset_id",
        "downloads",
        "views",
        "created_at",
        "updated_at",
        "resolved_shape",
        "inferred_shape",
        "shape_known",
    ]
    ordering = ["-created_at"]

    fieldsets = (
        (
            None,
            {
                "fields": ("dataset_id", "name", "description", "format", "owner"),
            },
        ),
        (
            "Files",
            {
                "fields": ("file", "cover_image"),
            },
        ),
        (
            "Shape",
            {
                "fields": (
                    ("user_shape", "inferred_shape"),
                    ("resolved_shape", "shape_known"),
                ),
            },
        ),
        (
            "Visibility",
            {
                "fields": ("is_private", "allowed_users"),
            },
        ),
        (
            "Stats",
            {
                "fields": ("downloads", "views"),
            },
        ),
        (
            "Likes",
            {
                "fields": ("liked_by",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def shape_display(self, obj):
        """Show resolved shape or 'Unknown'"""
        if obj.resolved_shape:
            return obj.resolved_shape
        return "—"

    shape_display.short_description = "Shape"
