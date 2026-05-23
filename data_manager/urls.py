from django.urls import path
from . import views

app_name = "data"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    # fixed
    path("upload/", views.upload_dataset, name="upload"),
    path("my/", views.my_datasets, name="my"),
    path("liked/", views.liked_datasets, name="liked"),
    path("all/", views.all_datasets, name="all"),
    path("search-users-global/", views.search_users_global, name="search_users_global"),
    # dynamic
    path("<str:dataset_id>/", views.dataset_detail, name="detail"),
    path("<str:dataset_id>/edit/", views.edit_dataset, name="edit"),
    path("<str:dataset_id>/delete/", views.delete_dataset, name="delete"),
    path("<str:dataset_id>/download/", views.download_dataset, name="download"),
    path("<str:dataset_id>/like/", views.toggle_like, name="like"),
    # Private access
    path("<str:dataset_id>/search-users/", views.search_users, name="search_users"),
    path(
        "<str:dataset_id>/add-user/<int:user_id>/",
        views.add_allowed_user,
        name="add_user",
    ),
    path(
        "<str:dataset_id>/remove-user/<int:user_id>/",
        views.remove_allowed_user,
        name="remove_user",
    ),
]
