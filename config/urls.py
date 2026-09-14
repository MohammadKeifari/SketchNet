from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from .views import robots_txt, sitemap_xml, serve_media

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("learn/", TemplateView.as_view(template_name="learn.html"), name="learn"),
    path("robots.txt", robots_txt, name="robots"),
    path("sitemap.xml", sitemap_xml, name="sitemap"),
    path("accounts/", include("accounts.urls")),
    path("settings/", include("setting.urls")),
    path("data/", include("data_manager.urls")),
    path("sketchmod/", include("sketchmod.urls")),
    path("models/", include("models_library.urls")),
    path("bug-reports/", include("bug_reports.urls")),
    # Django's static() helper is a no-op when DEBUG=False, so gunicorn +
    # Cloudflare Tunnel never served /media/ (covers, avatars, datasets).
    re_path(r"^media/(?P<path>.*)$", serve_media, name="serve_media"),
]
