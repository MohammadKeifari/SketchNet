from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import BugReport


@admin.register(BugReport)
class BugReportAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "issue_type",
        "status",
        "created_at",
        "open_in_canvas_link",
    )
    list_filter = ("status", "issue_type", "created_at")
    search_fields = ("title", "description", "user__username")
    readonly_fields = ("created_at", "updated_at", "open_in_canvas_button")
    fieldsets = (
        (None, {"fields": ("user", "issue_type", "status", "title")}),
        ("Details", {"fields": ("description", "expected_behavior", "error_message")}),
        ("Graph Data", {"fields": ("graph_json", "open_in_canvas_button")}),
        ("Admin", {"fields": ("admin_notes", "created_at", "updated_at")}),
    )

    def open_in_canvas_link(self, obj):
        if obj.graph_json:
            url = reverse("bug_reports:admin_canvas", args=[obj.pk])
            return format_html(
                '<a href="{}" target="_blank">🔗 Open in Canvas</a>', url
            )
        return "—"

    def open_in_canvas_button(self, obj):
        if obj.graph_json:
            url = reverse("bug_reports:admin_canvas", args=[obj.pk])
            return format_html(
                '<a href="{}" target="_blank" style="display:inline-block;padding:8px 16px;background:#6c5ce7;color:#ffffff !important;border-radius:6px;text-decoration:none;font-weight:500;">Open Graph in SketchMod</a>',
                url,
            )
        return "No graph data attached."

    open_in_canvas_button.short_description = "View Graph"
