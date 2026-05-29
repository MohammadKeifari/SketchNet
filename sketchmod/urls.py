from django.urls import path
from . import views

app_name = "sketchmod"

urlpatterns = [
    path("", views.canvas, name="canvas"),
    path("api/export/", views.export_api, name="export_api"),
    path(
        "api/<str:dataset_id>/columns/",
        views.api_dataset_columns,
        name="api_dataset_columns",
    ),
]
