from django.urls import path
from . import views

app_name = "bug_reports"

urlpatterns = [
    path("api/submit/", views.submit_report, name="submit_report"),
    path("canvas/<int:pk>/", views.admin_canvas, name="admin_canvas"),
]
