from django.urls import path, include
from . import views

urlpatterns = [
    path("guest/", views.guest_login, name="guest_login"),
    path("guest/signup/", views.guest_to_signup, name="guest_to_signup"),
    path("", include("allauth.urls")),
    path("profile/", views.profile, name="profile"),
    path("u/<str:username>/", views.public_profile, name="public_profile"),
]
