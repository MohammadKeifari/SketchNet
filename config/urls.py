from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("learn/", TemplateView.as_view(template_name="learn.html"), name="learn"),
    path("accounts/", include("accounts.urls")),
    path("settings/", include("setting.urls")),
    path("data/", include("data_manager.urls")),
    path("sketchmod/", include("sketchmod.urls")),
    path("models/", include("models_library.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
