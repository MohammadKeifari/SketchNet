import json
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.cache import cache
from .models import BugReport
from sketchmod.views import _canvas_context

RATE_LIMIT = 5
RATE_WINDOW_SECONDS = 3600


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


@staff_member_required
def admin_canvas(request, pk):
    """Load a bug report's graph into the canvas (admin only)."""
    report = get_object_or_404(BugReport, pk=pk)
    context = _canvas_context(request, readonly=False)
    context.update(
        {
            "template_graph": report.graph_json if report.graph_json else None,
            "report_id": pk,
            "report_title": report.title,
        }
    )
    return render(request, "sketchmod/canvas.html", context)


@require_POST
def submit_report(request):
    """API endpoint for submitting a bug report."""
    if len(request.body) > 2 * 1024 * 1024:
        return JsonResponse(
            {"success": False, "error": "Report too large."}, status=413
        )
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    if data.get("_contact_url"):
        return JsonResponse({"success": True, "report_id": None})

    ip = _client_ip(request)
    cache_key = f"bug-report:{ip}"
    count = cache.get(cache_key, 0)
    if count >= RATE_LIMIT:
        return JsonResponse(
            {"success": False, "error": "Too many reports. Try again later."},
            status=429,
        )
    cache.set(cache_key, count + 1, RATE_WINDOW_SECONDS)

    report = BugReport.objects.create(
        user=request.user if request.user.is_authenticated else None,
        issue_type=data.get("issue_type", "other"),
        title=data.get("title", "Untitled Report")[:200],
        description=data.get("description", "")[:5000],
        expected_behavior=data.get("expected_behavior", "")[:5000],
        graph_json=data.get("graph_json"),
        error_message=data.get("error_message", "")[:2000],
    )

    from django.core.mail import mail_admins

    mail_admins(
        subject=f"SketchNet Bug Report: {report.title}",
        message=f"A new bug report has been submitted.\n\n"
        f"Type: {report.get_issue_type_display()}\n"
        f"User: {report.user or 'Anonymous'}\n"
        f"Status: {report.get_status_display()}\n\n"
        f"Description:\n{report.description}\n\n"
        f"View in admin: /admin/bug_reports/bugreport/{report.pk}/",
        fail_silently=True,
    )

    return JsonResponse({"success": True, "report_id": report.pk})
