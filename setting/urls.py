from django.urls import path
from . import views

app_name = "setting"

urlpatterns = [
    path("", views.settings_view, name="settings"),
    path("api/sidebar/", views.update_sidebar_preference, name="update_sidebar"),
]
