from django.urls import path, include
from . import views

urlpatterns = [
    path("", include("allauth.urls")),
    path("profile/", views.profile, name="profile"),
    path("u/<str:username>/", views.public_profile, name="public_profile"),
]
