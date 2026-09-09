from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect

GUEST_MESSAGE = (
    "Test users cannot save. Create an account to keep your graphs and profile."
)

GUEST_ALLOWED_WRITE_PREFIXES = (
    "/accounts/logout/",
    "/accounts/guest/",
    "/sketchmod/api/export/",
    "/sketchmod/api/validate/",
    "/sketchmod/api/highlight-path/",
    "/sketchmod/api/consume-template/",
)


def _is_guest(user):
    return bool(getattr(user, "is_authenticated", False) and getattr(user, "is_guest", False))


def _path_allowed(path):
    return any(path.startswith(prefix) for prefix in GUEST_ALLOWED_WRITE_PREFIXES)


def _wants_html(request):
    accept = request.headers.get("Accept", "")
    ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    content_type = request.content_type or ""
    if ajax or content_type.startswith("application/json") or "/api/" in request.path:
        return False
    return "text/html" in accept


def guest_blocked_response(request):
    if _wants_html(request):
        messages.error(request, GUEST_MESSAGE)
        return redirect("sketchmod:canvas")
    return JsonResponse({"success": False, "error": GUEST_MESSAGE}, status=403)


class GuestRestrictionMiddleware:
    """Block guest accounts from persisting profile, settings, data, or models."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and _is_guest(
            getattr(request, "user", None)
        ):
            if not _path_allowed(request.path):
                return guest_blocked_response(request)
        return self.get_response(request)
