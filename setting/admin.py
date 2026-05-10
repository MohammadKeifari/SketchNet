from django.contrib import admin
from django.utils.html import format_html
from .models import UserSettings


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ["user_link", "theme_badge", "created_at", "updated_at"]
    list_filter = ["theme"]
    search_fields = ["user__username", "user__email"]
    readonly_fields = ["user", "theme", "created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        (
            None,
            {
                "fields": ("user", "theme"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def has_add_permission(self, request):
        """Settings are created automatically — no manual creation"""
        return False

    def user_link(self, obj):
        """Clickable link to the user's admin page"""
        from django.urls import reverse

        url = reverse("admin:accounts_customuser_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)

    user_link.short_description = "User"
    user_link.admin_order_field = "user__username"

    def theme_badge(self, obj):
        """Colored theme indicator"""
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
        bg = colors.get(obj.theme, "#6b7280")
        text_color = (
            "#ffffff" if obj.theme not in ["light", "honey", "forest"] else "#1a1d2e"
        )

        return format_html(
            '<span style="background: {}; color: {}; padding: 3px 10px; '
            'border-radius: 12px; font-size: 0.8rem; font-weight: 600;">{}</span>',
            bg,
            text_color,
            obj.theme.replace("-", " ").title(),
        )

    theme_badge.short_description = "Theme"
