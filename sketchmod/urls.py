from django.urls import path
from . import views

app_name = "sketchmod"

urlpatterns = [
    path("", views.canvas, name="canvas"),
]
