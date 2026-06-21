from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class BugReport(models.Model):
    ISSUE_TYPES = [
        ("code_error", "Code Error (crash / traceback)"),
        ("unexpected_behavior", "Unexpected Behavior"),
        ("feature_request", "Feature Request"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("new", "New"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    issue_type = models.CharField(max_length=30, choices=ISSUE_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    expected_behavior = models.TextField(blank=True)
    graph_json = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"[{self.get_status_display()}] {self.title} — {self.user or 'Anonymous'}"
        )
