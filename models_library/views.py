from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from .models import SketchModel, ModelAccess

import json

User = get_user_model()


def get_visible_models(user):
    """Base queryset of models visible to a user"""
    if user.is_authenticated:
        return SketchModel.objects.filter(
            Q(view_access="public") | Q(owner=user) | Q(allowed_users=user)
        ).distinct()
    return SketchModel.objects.filter(view_access="public")


# ===== DASHBOARD =====
def dashboard(request):
    models_qs = get_visible_models(request.user).select_related("owner")

    # My models
    if request.user.is_authenticated:
        my_models = models_qs.filter(owner=request.user)[:3]
    else:
        my_models = SketchModel.objects.none()

    # Liked models
    if request.user.is_authenticated:
        liked_models = models_qs.filter(liked_by=request.user)[:3]
    else:
        liked_models = SketchModel.objects.none()

    # All models
    all_models = models_qs.annotate(like_count=Count("liked_by")).order_by(
        "-created_at"
    )[:20]

    return render(
        request,
        "models_library/dashboard.html",
        {
            "my_models": my_models,
            "liked_models": liked_models,
            "all_models": all_models,
        },
    )


# ===== SAVE =====
@login_required
def save_model(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        graph_data = request.POST.get("graph_data", "{}")
        view_access = request.POST.get("view_access", "public")
        fork_access = request.POST.get("fork_access", "private")

        if not name:
            return JsonResponse({"error": "Name is required"}, status=400)

        try:
            graph_json = json.loads(graph_data)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid graph data"}, status=400)

        model = SketchModel.objects.create(
            name=name,
            description=description,
            graph_data=graph_json,
            view_access=view_access,
            fork_access=fork_access,
            owner=request.user,
        )

        if request.FILES.get("cover_image"):
            model.cover_image = request.FILES["cover_image"]
            model.save()

        return JsonResponse(
            {
                "success": True,
                "model_id": model.model_id,
                "name": model.name,
            }
        )

    return JsonResponse({"error": "POST required"}, status=405)


# ===== UPDATE (subsequent saves) =====
@login_required
def update_model(request, model_id):
    model = get_object_or_404(SketchModel, model_id=model_id)

    if not model.can_edit(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)

    if request.method == "POST":
        graph_data = request.POST.get("graph_data", "{}")
        try:
            graph_json = json.loads(graph_data)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid graph data"}, status=400)

        model.graph_data = graph_json
        model.save()
        return JsonResponse({"success": True})

    return JsonResponse({"error": "POST required"}, status=405)


# ===== VIEW (read-only canvas) =====
def view_model(request, model_id):
    model = get_object_or_404(SketchModel, model_id=model_id)

    if not model.can_view(request.user):
        messages.error(request, "You don't have access to this model.")
        return redirect("models:dashboard")

    model.views += 1
    model.save(update_fields=["views"])

    return render(
        request,
        "models_library/view.html",
        {
            "model": model,
            "readonly": not model.can_edit(request.user),
        },
    )


# ===== FORK =====
@login_required
def fork_model(request, model_id):
    original = get_object_or_404(SketchModel, model_id=model_id)

    if not original.can_fork(request.user):
        messages.error(request, "You don't have permission to fork this model.")
        return redirect("models:view", model_id=model_id)

    print(f"Forking by user: {request.user.username}")
    print(f"Request user id: {request.user.id}")

    forked = SketchModel.objects.create(
        name=f"{original.name} (fork)",
        description=original.description,
        graph_data=original.graph_data,
        owner=request.user,
        forked_from=original,
    )

    original.forks_count += 1
    original.save(update_fields=["forks_count"])

    messages.success(request, f"Model forked successfully as '{forked.name}'.")
    return redirect("models:view", model_id=forked.model_id)


# ===== DELETE =====
@login_required
def delete_model(request, model_id):
    model = get_object_or_404(SketchModel, model_id=model_id)

    if not model.can_delete(request.user):
        messages.error(request, "You don't have permission to delete this model.")
        return redirect("models:dashboard")

    if request.method == "POST":
        name = model.name
        if model.cover_image:
            model.cover_image.delete(save=False)
        model.delete()
        messages.success(request, f"Model '{name}' deleted.")
        return redirect("models:dashboard")

    return render(request, "models_library/delete_confirm.html", {"model": model})


# ===== DOWNLOAD =====
def download_model(request, model_id):
    model = get_object_or_404(SketchModel, model_id=model_id)

    if not model.can_view(request.user):
        messages.error(request, "You don't have access to this model.")
        return redirect("models:dashboard")

    model.downloads += 1
    model.save(update_fields=["downloads"])

    # Return graph as downloadable JSON
    response = JsonResponse(model.graph_data, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = f'attachment; filename="{model.name}.json"'
    return response


# ===== LIKE =====
@login_required
def toggle_like(request, model_id):
    model = get_object_or_404(SketchModel, model_id=model_id)

    if not model.can_view(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)

    if model.liked_by.filter(id=request.user.id).exists():
        model.liked_by.remove(request.user)
        liked = False
    else:
        model.liked_by.add(request.user)
        liked = True

    return JsonResponse({"liked": liked, "likes_count": model.likes_count})


# ===== API: LIST =====
def api_model_list(request):
    models_qs = get_visible_models(request.user).select_related("owner")
    models_qs = models_qs.annotate(like_count=Count("liked_by"))

    search = request.GET.get("search", "")
    if search:
        models_qs = models_qs.filter(
            Q(name__icontains=search)
            | Q(model_id__icontains=search)
            | Q(owner__username__icontains=search)
        )

    section = request.GET.get("section", "all")
    if section == "mine" and request.user.is_authenticated:
        models_qs = models_qs.filter(owner=request.user)
    elif section == "liked" and request.user.is_authenticated:
        models_qs = models_qs.filter(liked_by=request.user)

    sort = request.GET.get("sort", "newest")
    if sort == "downloads":
        models_qs = models_qs.order_by("-downloads")
    elif sort == "popular":
        models_qs = models_qs.order_by("-downloads", "-views")
    else:
        models_qs = models_qs.order_by("-created_at")

    data = []
    for m in models_qs[:50]:
        data.append(
            {
                "id": m.model_id,
                "name": m.name,
                "owner": m.owner.username,
                "views": m.views,
                "downloads": m.downloads,
                "likes": m.likes_count,
                "forks": m.forks_count,
                "view_access": m.view_access,
                "fork_access": m.fork_access,
                "is_owner": (
                    request.user == m.owner if request.user.is_authenticated else False
                ),
                "created_at": m.created_at.strftime("%b %d, %Y"),
            }
        )

    return JsonResponse({"models": data, "count": len(data)})


# ===== USER ACCESS MANAGEMENT =====
@login_required
def manage_access(request, model_id):
    model = get_object_or_404(SketchModel, model_id=model_id)

    if not model.can_edit(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        can_view = request.POST.get("can_view") == "true"
        can_fork = request.POST.get("can_fork") == "true"

        user = get_object_or_404(User, id=user_id)
        access, created = ModelAccess.objects.get_or_create(
            user=user,
            model=model,
            defaults={"can_view": can_view, "can_fork": can_fork},
        )
        if not created:
            access.can_view = can_view
            access.can_fork = can_fork
            access.save()

        return JsonResponse({"success": True})

    # GET: return current access list
    accesses = model.modelaccess_set.select_related("user")
    data = []
    for a in accesses:
        data.append(
            {
                "user_id": a.user.id,
                "username": a.user.username,
                "email": a.user.email,
                "can_view": a.can_view,
                "can_fork": a.can_fork,
            }
        )

    return JsonResponse({"users": data})


@login_required
def remove_access(request, model_id, user_id):
    model = get_object_or_404(SketchModel, model_id=model_id)

    if not model.can_edit(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)

    ModelAccess.objects.filter(model=model, user_id=user_id).delete()
    return JsonResponse({"success": True})


@login_required
def search_users(request, model_id):
    model = get_object_or_404(SketchModel, model_id=model_id)

    if not model.can_edit(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)

    query = request.GET.get("q", "")
    if len(query) < 2:
        return JsonResponse({"users": []})

    existing_ids = list(model.modelaccess_set.values_list("user_id", flat=True))
    existing_ids.append(model.owner.id)

    users = User.objects.filter(
        Q(username__icontains=query) | Q(email__icontains=query)
    ).exclude(id__in=existing_ids)[:10]

    return JsonResponse(
        {
            "users": [
                {"id": u.id, "username": u.username, "email": u.email} for u in users
            ]
        }
    )


# ===== MY MODELS (EXPANDED) =====
@login_required
def my_models(request):
    models_qs = SketchModel.objects.filter(owner=request.user).order_by("-created_at")
    return render(request, "models_library/my_models.html", {"models": models_qs})


# ===== LIKED MODELS (EXPANDED) =====
@login_required
def liked_models(request):
    models_qs = (
        get_visible_models(request.user)
        .filter(liked_by=request.user)
        .order_by("-created_at")
    )
    return render(request, "models_library/liked_models.html", {"models": models_qs})


# ===== ALL MODELS (EXPANDED) =====
def all_models(request):
    models_qs = get_visible_models(request.user).select_related("owner")
    models_qs = models_qs.annotate(like_count=Count("liked_by"))

    search = request.GET.get("search", "")
    if search:
        models_qs = models_qs.filter(
            Q(name__icontains=search)
            | Q(model_id__icontains=search)
            | Q(owner__username__icontains=search)
        )

    sort = request.GET.get("sort", "newest")
    if sort == "downloads":
        models_qs = models_qs.order_by("-downloads")
    elif sort == "popular":
        models_qs = models_qs.order_by("-downloads", "-views")
    else:
        models_qs = models_qs.order_by("-created_at")

    return render(
        request,
        "models_library/all_models.html",
        {
            "models": models_qs,
            "search": search,
            "sort": sort,
        },
    )


# ============== edit ==================
@login_required
def edit_model(request, model_id):
    model = get_object_or_404(SketchModel, model_id=model_id)

    if not model.can_edit(request.user):
        messages.error(request, "You don't have permission to edit this model.")
        return redirect("models:view", model_id=model_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        view_access = request.POST.get("view_access", "public")
        fork_access = request.POST.get("fork_access", "private")

        if name:
            model.name = name
        model.description = description
        model.view_access = view_access
        model.fork_access = fork_access

        if request.FILES.get("cover_image"):
            if model.cover_image:
                model.cover_image.delete(save=False)
            model.cover_image = request.FILES["cover_image"]

        model.save()
        messages.success(request, "Model updated.")
        return redirect("models:view", model_id=model.model_id)

    return render(request, "models_library/edit.html", {"model": model})


def download_model(request, model_id):
    model = get_object_or_404(SketchModel, model_id=model_id)

    if not model.can_view(request.user):
        messages.error(request, "You don't have access to this model.")
        return redirect("models:dashboard")

    model.downloads += 1
    model.save(update_fields=["downloads"])

    response_data = model.graph_data
    response_data["name"] = model.name  # ADD THIS

    response = JsonResponse(response_data, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = f'attachment; filename="{model.name}.json"'
    return response


def api_model_data(request, model_id):
    """Return model graph data as JSON for the canvas to load"""
    model = get_object_or_404(SketchModel, model_id=model_id)

    if not model.can_view(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)

    data = model.graph_data
    data["name"] = model.name
    data["model_id"] = model.model_id

    return JsonResponse(data)
