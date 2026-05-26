from django.contrib import admin
from .models import SketchModel, ModelAccess


class ModelAccessInline(admin.TabularInline):
    model = ModelAccess
    extra = 0
    fields = ("user", "can_view", "can_fork")


@admin.register(SketchModel)
class SketchModelAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "model_id",
        "owner",
        "view_access",
        "fork_access",
        "views",
        "downloads",
        "forks_count",
        "created_at",
    ]
    list_filter = ["view_access", "fork_access", "created_at"]
    search_fields = ["name", "model_id", "owner__username", "owner__email"]
    readonly_fields = [
        "model_id",
        "views",
        "downloads",
        "forks_count",
        "created_at",
        "updated_at",
    ]
    inlines = [ModelAccessInline]
    ordering = ["-created_at"]

    fieldsets = (
        (
            None,
            {
                "fields": ("model_id", "name", "description", "owner", "forked_from"),
            },
        ),
        (
            "Graph Data",
            {
                "fields": ("graph_data",),
                "classes": ("collapse",),
            },
        ),
        (
            "Access",
            {
                "fields": ("view_access", "fork_access"),
            },
        ),
        (
            "Stats",
            {
                "fields": ("views", "downloads", "forks_count"),
            },
        ),
        (
            "Cover",
            {
                "fields": ("cover_image",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )


@admin.register(ModelAccess)
class ModelAccessAdmin(admin.ModelAdmin):
    list_display = ["user", "model", "can_view", "can_fork"]
    list_filter = ["can_view", "can_fork"]
    search_fields = ["user__username", "model__name"]
