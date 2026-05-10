from django.urls import path
from . import views

app_name = "setting"

urlpatterns = [
    path("", views.settings_view, name="settings"),
]
