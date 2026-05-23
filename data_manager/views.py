from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, JsonResponse
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from .models import Dataset
from .forms import DatasetForm, DatasetEditForm

User = get_user_model()


def get_visible_datasets(user):
    """Base queryset of datasets visible to a user"""
    if user.is_authenticated:
        return Dataset.objects.filter(
            Q(is_private=False) | Q(owner=user) | Q(allowed_users=user)
        ).distinct()
    return Dataset.objects.filter(is_private=False)


# ===== DASHBOARD =====
def dashboard(request):
    """Main data page with all sections"""
    datasets = get_visible_datasets(request.user)

    # My datasets (owned + accessible)
    if request.user.is_authenticated:
        my_datasets = datasets.filter(
            Q(owner=request.user) | Q(allowed_users=request.user)
        ).distinct()[:3]
    else:
        my_datasets = Dataset.objects.none()

    # Liked datasets
    if request.user.is_authenticated:
        liked_datasets = datasets.filter(liked_by=request.user)[:3]
    else:
        liked_datasets = Dataset.objects.none()

    # All datasets (for bottom section)
    all_datasets = (
        datasets.select_related("owner")
        .annotate(like_count=Count("liked_by"))
        .order_by("-created_at")[:20]
    )

    return render(
        request,
        "data_manager/dashboard.html",
        {
            "my_datasets": my_datasets,
            "liked_datasets": liked_datasets,
            "all_datasets": all_datasets,
        },
    )


# ===== UPLOAD =====
@login_required
def upload_dataset(request):
    if request.method == "POST":
        form = DatasetForm(request.POST, request.FILES)
        if form.is_valid():
            dataset = form.save(commit=False)
            dataset.owner = request.user
            dataset.save()

            if dataset.is_private:
                messages.success(
                    request,
                    f"Dataset '{dataset.name}' uploaded. You can now add users who can access it.",
                )
                return redirect("data:edit", dataset_id=dataset.dataset_id)

            messages.success(
                request, f"Dataset '{dataset.name}' uploaded successfully."
            )
            return redirect("data:detail", dataset_id=dataset.dataset_id)
        else:
            # Form invalid - return to dashboard with errors shown in modal
            messages.error(request, "Please fix the errors below.")
            return redirect("data:dashboard")

    return redirect("data:dashboard")


# ===== EDIT =====
@login_required
def edit_dataset(request, dataset_id):
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)

    if not dataset.can_edit(request.user):
        messages.error(request, "You don't have permission to edit this dataset.")
        return redirect("data:dashboard")

    if request.method == "POST":
        form = DatasetEditForm(request.POST, request.FILES, instance=dataset)
        if form.is_valid():
            form.save()
            messages.success(request, "Dataset updated.")
            return redirect("data:detail", dataset_id=dataset.dataset_id)
    else:
        form = DatasetEditForm(instance=dataset)

    return render(
        request,
        "data_manager/edit.html",
        {
            "form": form,
            "dataset": dataset,
        },
    )


# ===== DELETE =====
@login_required
def delete_dataset(request, dataset_id):
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)

    if not dataset.can_delete(request.user):
        messages.error(request, "You don't have permission to delete this dataset.")
        return redirect("data:dashboard")

    if request.method == "POST":
        name = dataset.name
        dataset.file.delete(save=False)
        if dataset.cover_image:
            dataset.cover_image.delete(save=False)
        dataset.delete()
        messages.success(request, f"Dataset '{name}' deleted.")
        return redirect("data:dashboard")

    return render(request, "data_manager/delete_confirm.html", {"dataset": dataset})


# ===== DOWNLOAD =====
@login_required
def download_dataset(request, dataset_id):
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)

    if not dataset.is_visible_to(request.user):
        messages.error(request, "You don't have access to this dataset.")
        return redirect("data:dashboard")

    dataset.downloads += 1
    dataset.save(update_fields=["downloads"])

    return FileResponse(
        dataset.file.open("rb"),
        as_attachment=True,
        filename=dataset.file.name.split("/")[-1],
    )


# ===== LIKE =====
@login_required
def toggle_like(request, dataset_id):
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)

    if not dataset.is_visible_to(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)

    if dataset.liked_by.filter(id=request.user.id).exists():
        dataset.liked_by.remove(request.user)
        liked = False
    else:
        dataset.liked_by.add(request.user)
        liked = True

    return JsonResponse({"liked": liked, "likes_count": dataset.likes_count})


# ===== DETAIL =====
def dataset_detail(request, dataset_id):
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)

    if not dataset.is_visible_to(request.user):
        messages.error(request, "You don't have access to this dataset.")
        return redirect("data:dashboard")

    dataset.views += 1
    dataset.save(update_fields=["views"])

    return render(request, "data_manager/detail.html", {"dataset": dataset})


# ===== MY DATASETS (EXPANDED) =====
@login_required
def my_datasets(request):
    datasets = (
        Dataset.objects.filter(Q(owner=request.user) | Q(allowed_users=request.user))
        .distinct()
        .order_by("-created_at")
    )

    return render(request, "data_manager/my_datasets.html", {"datasets": datasets})


# ===== LIKED DATASETS (EXPANDED) =====
@login_required
def liked_datasets(request):
    datasets = (
        Dataset.objects.filter(liked_by=request.user)
        .filter(
            Q(is_private=False) | Q(owner=request.user) | Q(allowed_users=request.user)
        )
        .distinct()
        .order_by("-created_at")
    )

    return render(request, "data_manager/liked_datasets.html", {"datasets": datasets})


# ===== ALL DATASETS =====
def all_datasets(request):
    datasets = get_visible_datasets(request.user).select_related("owner")
    datasets = datasets.annotate(like_count=Count("liked_by"))

    # Search
    search = request.GET.get("search", "")
    if search:
        datasets = datasets.filter(
            Q(name__icontains=search)
            | Q(dataset_id__icontains=search)
            | Q(owner__username__icontains=search)
        )

    # Sort
    sort = request.GET.get("sort", "newest")
    if sort == "downloads":
        datasets = datasets.order_by("-downloads")
    elif sort == "popular":
        datasets = datasets.order_by("-downloads", "-views")
    else:
        datasets = datasets.order_by("-created_at")

    return render(
        request,
        "data_manager/all_datasets.html",
        {
            "datasets": datasets,
            "search": search,
            "sort": sort,
        },
    )


# ===== PRIVATE ACCESS =====
@login_required
def search_users(request, dataset_id):
    """Search users to add to private dataset (JSON response)"""
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)

    if not dataset.can_edit(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)

    query = request.GET.get("q", "")
    if len(query) < 2:
        return JsonResponse({"users": []})

    # Exclude owner and already allowed users
    existing_ids = list(dataset.allowed_users.values_list("id", flat=True)) + [
        dataset.owner.id
    ]

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


@login_required
def add_allowed_user(request, dataset_id, user_id):
    """Add a user to private dataset"""
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)

    if not dataset.can_edit(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)

    user = get_object_or_404(User, id=user_id)
    dataset.allowed_users.add(user)

    return JsonResponse({"success": True, "username": user.username})


@login_required
def remove_allowed_user(request, dataset_id, user_id):
    """Remove a user from private dataset"""
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)

    if not dataset.can_edit(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)

    user = get_object_or_404(User, id=user_id)
    dataset.allowed_users.remove(user)

    return JsonResponse({"success": True})


@login_required
def search_users_global(request):
    """Search all users (for upload phase when no dataset ID exists)"""
    query = request.GET.get("q", "")
    if len(query) < 2:
        return JsonResponse({"users": []})

    users = User.objects.filter(
        Q(username__icontains=query) | Q(email__icontains=query)
    ).exclude(id=request.user.id)[:10]

    return JsonResponse(
        {
            "users": [
                {"id": u.id, "username": u.username, "email": u.email} for u in users
            ]
        }
    )
