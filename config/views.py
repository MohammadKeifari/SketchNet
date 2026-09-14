import mimetypes
import posixpath

from django.conf import settings
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.views.static import serve

# Windows uploads sometimes store JPEG covers as .jfif; browsers need image/jpeg.
mimetypes.add_type("image/jpeg", ".jfif")
mimetypes.add_type("image/jpeg", ".jpe")


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /sketchmod/api/",
        "Disallow: /accounts/",
        "Disallow: /settings/",
        f"Sitemap: {request.build_absolute_uri(reverse('sitemap'))}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def sitemap_xml(request):
    pages = [
        ("", "daily", "1.0"),
        ("learn/", "weekly", "0.9"),
        ("data/all/", "daily", "0.7"),
        ("models/all/", "daily", "0.7"),
    ]
    base = request.build_absolute_uri("/")
    urls = []
    for path, changefreq, priority in pages:
        loc = base if not path else f"{base}{path}"
        urls.append(
            "  <url>"
            f"<loc>{loc}</loc>"
            f"<changefreq>{changefreq}</changefreq>"
            f"<priority>{priority}</priority>"
            "</url>"
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(urls)
        + "</urlset>"
    )
    return HttpResponse(body, content_type="application/xml")


def _media_file_stem(path):
    """Return the filename without directory or extension."""
    name = path.rsplit("/", 1)[-1]
    if "." in name:
        return name.rsplit(".", 1)[0]
    return name


def _user_may_read_media(request, path):
    """Whether this user may fetch a file under MEDIA_ROOT."""
    if path.startswith("avatars/"):
        return True
    if path.startswith("models/covers/"):
        from models_library.models import SketchModel

        model = SketchModel.objects.filter(model_id=_media_file_stem(path)).first()
        return bool(model and model.can_view(request.user))
    if path.startswith("datasets/covers/"):
        from data_manager.models import Dataset

        dataset = Dataset.objects.filter(dataset_id=_media_file_stem(path)).first()
        return bool(dataset and dataset.is_visible_to(request.user))
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "datasets":
        from data_manager.models import Dataset

        dataset = Dataset.objects.filter(dataset_id=parts[1]).first()
        return bool(dataset and dataset.is_visible_to(request.user))
    return False


def serve_media(request, path):
    """Serve user uploads in production (gunicorn / Cloudflare Tunnel).

    Django's ``static()`` helper installs no routes when ``DEBUG=False``, so
    ``runserver`` shows covers and avatars while the public site 404s them.
    Dataset payloads still follow ``Dataset.is_visible_to``.
    """
    normalized = posixpath.normpath(path or "").lstrip("/")
    if not normalized or normalized.startswith(".."):
        raise Http404()
    if not _user_may_read_media(request, normalized):
        raise Http404()
    return serve(request, normalized, document_root=str(settings.MEDIA_ROOT))
