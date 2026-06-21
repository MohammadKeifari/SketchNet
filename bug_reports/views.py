import json
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import BugReport


@staff_member_required
def admin_canvas(request, pk):
    """Load a bug report's graph into the canvas (admin only)."""
    report = get_object_or_404(BugReport, pk=pk)
    context = {
        "template_graph": json.dumps(report.graph_json) if report.graph_json else None,
        "report_id": pk,
        "report_title": report.title,
    }
    return render(request, "sketchmod/canvas.html", context)


@require_POST
@csrf_exempt
def submit_report(request):
    """API endpoint for submitting a bug report."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    report = BugReport.objects.create(
        user=request.user if request.user.is_authenticated else None,
        issue_type=data.get("issue_type", "other"),
        title=data.get("title", "Untitled Report"),
        description=data.get("description", ""),
        expected_behavior=data.get("expected_behavior", ""),
        graph_json=data.get("graph_json"),
        error_message=data.get("error_message", ""),
    )

    # Optional: send email notification
    from django.core.mail import mail_admins

    mail_admins(
        subject=f"SketchNet Bug Report: {report.title}",
        message=f"A new bug report has been submitted.\n\n"
        f"Type: {report.get_issue_type_display()}\n"
        f"User: {report.user or 'Anonymous'}\n"
        f"Status: {report.get_status_display()}\n\n"
        f"Description:\n{report.description}\n\n"
        f"View in admin: http://127.0.0.1:8000/admin/bug_reports/bugreport/{report.pk}/",
        fail_silently=True,
    )

    return JsonResponse({"success": True, "report_id": report.pk})
