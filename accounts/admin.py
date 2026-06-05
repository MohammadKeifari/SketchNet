from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser


class UserSettingsInline(admin.StackedInline):
    """Show settings directly on the user page"""

    from setting.models import UserSettings

    model = UserSettings
    can_delete = False
    readonly_fields = ["theme", "created_at", "updated_at"]
    fieldsets = (
        (
            None,
            {
                "fields": ("theme",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = [
        "username",
        "email",
        "theme_badge",
        "is_active",
        "is_staff",
        "date_joined",
    ]
    list_filter = [
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
    ]
    search_fields = ["username", "email"]
    ordering = ["-date_joined"]
    inlines = [UserSettingsInline]

    fieldsets = (
        (
            None,
            {
                "fields": ("username", "email", "password"),
            },
        ),
        (
            "Personal Info",
            {
                "fields": ("first_name", "last_name"),
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Important Dates",
            {
                "fields": ("last_login", "date_joined"),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )

    actions = ["activate_users", "deactivate_users"]

    def theme_badge(self, obj):
        """Show the user's theme with a colored badge"""
        if hasattr(obj, "settings"):
            theme = obj.settings.theme
            colors = {
                "system": "#6b7280",
                "light": "#f8f9fc",
                "dark": "#1a1d27",
                "rose": "#e8536c",
                "dark-rose": "#f0627a",
                "forest": "#3a8a3a",
                "forest-dark": "#4caf50",
                "honey": "#d4a800",
                "honey-dark": "#f0c040",
            }
            bg = colors.get(theme, "#6b7280")
            text_color = (
                "#ffffff" if theme not in ["light", "honey", "forest"] else "#1a1d2e"
            )

            return format_html(
                '<span style="background: {}; color: {}; padding: 3px 10px; '
                'border-radius: 12px; font-size: 0.8rem; font-weight: 600;">{}</span>',
                bg,
                text_color,
                theme.replace("-", " ").title(),
            )
        return "-"

    theme_badge.short_description = "Theme"

    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        """Mark all selected users as active."""
        queryset.update(is_active=True)

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        """Mark all selected users as inactive."""
        queryset.update(is_active=False)
