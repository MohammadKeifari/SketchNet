from django.http import HttpResponse
from django.urls import reverse


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
