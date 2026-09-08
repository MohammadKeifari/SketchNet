from django.urls import path
from . import views

app_name = "models"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    # CRUD
    path("save/", views.save_model, name="save"),
    # API
    path("api/list/", views.api_model_list, name="api_list"),
    path("my/", views.my_models, name="my"),
    path("liked/", views.liked_models, name="liked"),
    path("all/", views.all_models, name="all"),
    # dynamic urls:
    path("<str:model_id>/update/", views.update_model, name="update"),
    path("<str:model_id>/", views.view_model, name="view"),
    path("<str:model_id>/fork/", views.fork_model, name="fork"),
    path("<str:model_id>/delete/", views.delete_model, name="delete"),
    path("<str:model_id>/download/", views.download_model, name="download"),
    path("<str:model_id>/like/", views.toggle_like, name="like"),
    path("<str:model_id>/share/", views.share_model, name="share"),
    # Access management
    path("<str:model_id>/access/", views.manage_access, name="manage_access"),
    path(
        "<str:model_id>/access/<int:user_id>/remove/",
        views.remove_access,
        name="remove_access",
    ),
    path("<str:model_id>/search-users/", views.search_users, name="search_users"),
    # Expanded views
    path("<str:model_id>/edit/", views.edit_model, name="edit"),
    path("<str:model_id>/data/", views.api_model_data, name="api_data"),
]
