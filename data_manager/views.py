from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, JsonResponse
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from .models import Dataset
from .forms import DatasetForm, DatasetEditForm
from django.core.files import File

import tempfile
import os
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


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
    """Handle dataset upload from the dashboard modal."""
    if request.method == "POST":
        form = DatasetForm(request.POST, request.FILES)
        if form.is_valid():
            dataset = form.save(commit=False)
            dataset.owner = request.user
            dataset.save()  # Save first so file is on disk

            from .services import infer_dataset_shape

            shape, _ = infer_dataset_shape(dataset)
            if shape:
                dataset.inferred_shape = shape
            dataset.save()  # Triggers resolve_shape()

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
    """Display and process the dataset edit form."""
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)

    if not dataset.can_edit(request.user):
        messages.error(request, "You don't have permission to edit this dataset.")
        return redirect("data:dashboard")

    if request.method == "POST":
        form = DatasetEditForm(request.POST, request.FILES, instance=dataset)
        if form.is_valid():
            form.save()
            # Process allowed_users only if the dataset is private
            if dataset.is_private:
                # Get list of user IDs from the hidden inputs
                user_ids = request.POST.getlist("allowed_users")
                # Convert to integers and get User objects
                users = User.objects.filter(id__in=user_ids)
                dataset.allowed_users.set(users)  # replaces current set
            else:
                # If public, remove all allowed users (they can't be assigned)
                dataset.allowed_users.clear()
            from .services import infer_dataset_shape

            # Re-infer if file was changed or no inferred shape exists
            shape, _ = infer_dataset_shape(dataset)
            if shape:
                dataset.inferred_shape = shape
            dataset.save()  # Triggers resolve_shape()
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
    """Confirm and perform dataset deletion."""
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
    """Stream the dataset file and increment the download counter."""
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
@require_POST
def toggle_like(request, dataset_id):
    """Toggle the current user's like on a dataset."""
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
    """Show dataset details and increment the view counter."""
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
    """List datasets owned by or shared with the current user."""
    datasets = (
        Dataset.objects.filter(Q(owner=request.user) | Q(allowed_users=request.user))
        .distinct()
        .order_by("-created_at")
    )

    return render(request, "data_manager/my_datasets.html", {"datasets": datasets})


# ===== LIKED DATASETS (EXPANDED) =====
@login_required
def liked_datasets(request):
    """List datasets the current user has liked."""
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
    """Browse all visible datasets with search and sort options."""
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


def _parse_is_private(value):
    """Interpret form/JSON flags for the private checkbox."""
    if value is None:
        return None
    return str(value).strip().lower() in ("1", "true", "on", "yes", "private")


@login_required
@require_POST
def share_dataset(request, dataset_id):
    """Update dataset visibility without the full edit form."""
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)
    if not dataset.can_edit(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)

    parsed = _parse_is_private(request.POST.get("is_private"))
    if parsed is None:
        return JsonResponse({"error": "is_private is required"}, status=400)
    dataset.is_private = parsed
    dataset.save(update_fields=["is_private", "updated_at"])
    return JsonResponse({"success": True, "is_private": dataset.is_private})


@login_required
def list_allowed_users(request, dataset_id):
    """Return users explicitly allowed on a private dataset."""
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)
    if not dataset.can_edit(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)
    users = [
        {"id": u.id, "username": u.username, "email": u.email}
        for u in dataset.allowed_users.all()
    ]
    return JsonResponse({"users": users, "is_private": dataset.is_private})


@login_required
@require_POST
def add_allowed_user(request, dataset_id, user_id):
    """Add a user to private dataset"""
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)

    if not dataset.can_edit(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)

    user = get_object_or_404(User, id=user_id)
    dataset.allowed_users.add(user)

    return JsonResponse({"success": True, "username": user.username})


@login_required
@require_POST
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


# ===== API for choosing dataset =====
def api_dataset_list(request):
    """Return datasets for the SketchMod data input selector"""
    datasets = Dataset.objects.filter(is_private=False).select_related("owner")

    # If user is authenticated, also show their private datasets
    if request.user.is_authenticated:
        datasets = datasets | Dataset.objects.filter(
            Q(owner=request.user) | Q(allowed_users=request.user)
        )
    datasets = datasets.distinct()

    # Search
    search = request.GET.get("search", "")
    if search:
        datasets = datasets.filter(
            Q(name__icontains=search)
            | Q(dataset_id__icontains=search)
            | Q(owner__username__icontains=search)
        )

    # Filter by section
    section = request.GET.get("section", "all")
    if section == "mine" and request.user.is_authenticated:
        datasets = datasets.filter(
            Q(owner=request.user) | Q(allowed_users=request.user)
        )
    elif section == "liked" and request.user.is_authenticated:
        datasets = datasets.filter(liked_by=request.user)

    datasets = datasets.annotate(like_count=Count("liked_by")).order_by("-created_at")[
        :50
    ]

    data = []
    for d in datasets:
        data.append(
            {
                "id": d.dataset_id,
                "name": d.name,
                "format": d.get_format_display(),
                "owner": d.owner.username,
                "created_at": d.created_at.strftime("%b %d, %Y"),
                "downloads": d.downloads,
                "likes": d.likes_count,
                "is_private": d.is_private,
                "is_owner": (
                    request.user == d.owner if request.user.is_authenticated else False
                ),
                "data_shape": d.resolved_shape,
                "data_shape_known": d.shape_known,
            }
        )

    return JsonResponse({"datasets": data, "count": len(data)})


def api_dataset_shape(request, dataset_id):
    """Return the resolved shape of a dataset."""
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)
    if not dataset.is_visible_to(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)

    return JsonResponse({"shape": dataset.resolved_shape or ""})


@login_required
def generate_dataset(request):
    """Generate a synthetic sklearn dataset and save it as a new Dataset."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    ds_type = request.POST.get("type", "classification")
    name = request.POST.get("name", "").strip() or f"Synthetic {ds_type.capitalize()}"

    # Build kwargs from POST data
    kwargs = {}
    for key, value in request.POST.items():
        if key in ("csrfmiddlewaretoken", "type", "name"):
            continue
        if value == "" or value is None:
            continue
        try:
            kwargs[key] = int(value) if "." not in str(value) else float(value)
        except ValueError:
            kwargs[key] = value

    # Default parameters per type
    defaults = {
        "classification": {
            "n_samples": 100,
            "n_features": 2,
            "n_classes": 2,
            "n_informative": 2,
            "n_redundant": 0,
            "n_clusters_per_class": 1,
            "flip_y": 0.0,
            "random_state": None,
        },
        "regression": {
            "n_samples": 100,
            "n_features": 1,
            "n_informative": 1,
            "noise": 0.1,
            "bias": 0.0,
            "random_state": None,
        },
        "clustering": {
            "n_samples": 100,
            "n_features": 2,
            "centers": 3,
            "cluster_std": 1.0,
            "random_state": None,
        },
    }

    if ds_type not in defaults:
        return JsonResponse({"error": "Unknown dataset type."}, status=400)

    # Merge defaults with user kwargs (only known sklearn keys)
    allowed = set(defaults[ds_type].keys())
    user_kwargs = {k: v for k, v in kwargs.items() if k in allowed}
    final_kwargs = {**defaults[ds_type], **user_kwargs}
    # Remove None values that sklearn might not accept
    final_kwargs.pop("random_state", None)

    def _clamp(key, lo, hi, default):
        try:
            n = int(final_kwargs.get(key, default))
        except (TypeError, ValueError):
            n = default
        final_kwargs[key] = max(lo, min(hi, n))

    _clamp("n_samples", 10, 10_000, 100)
    _clamp("n_features", 1, 64, 2)
    if "n_informative" in final_kwargs:
        _clamp("n_informative", 1, int(final_kwargs["n_features"]), 1)
    if "n_classes" in final_kwargs:
        _clamp("n_classes", 2, 50, 2)
    if "centers" in final_kwargs:
        _clamp("centers", 1, 50, 3)

    try:
        import pandas as pd
        from sklearn.datasets import make_classification, make_regression, make_blobs
    except ImportError:
        logger.exception("sklearn is not installed")
        return JsonResponse(
            {"error": "Dataset generation is unavailable."},
            status=500,
        )

    try:
        if ds_type == "classification":
            X, y = make_classification(**final_kwargs)
        elif ds_type == "regression":
            X, y = make_regression(**final_kwargs)
        elif ds_type == "clustering":
            X, y = make_blobs(**final_kwargs)
        else:
            return JsonResponse({"error": "Unknown dataset type."}, status=400)

        # Create DataFrame
        df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])
        df["target"] = y

        # Write to temporary CSV
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        df.to_csv(tmp.name, index=False)
        tmp.close()

        # Create Dataset object
        dataset = Dataset(
            name=name,
            format="csv",
            owner=request.user,
            is_private=False,
        )
        # Save first so that dataset.dataset_id is generated
        dataset.save()

        # Save the file
        with open(tmp.name, "rb") as f:
            dataset.file.save(f"{dataset.dataset_id}.csv", File(f))

        # Explicitly infer the shape and save again
        from .services import infer_dataset_shape

        shape, known = infer_dataset_shape(dataset)
        if shape:
            dataset.inferred_shape = shape
            dataset.shape_known = known
        dataset.save()  # triggers resolve_shape() again

        return JsonResponse(
            {
                "success": True,
                "dataset_id": dataset.dataset_id,
                "name": dataset.name,
                "shape": dataset.resolved_shape or "",
            }
        )

    except Exception:
        logger.exception("Dataset generation failed")
        return JsonResponse({"error": "Generation failed."}, status=500)

    finally:
        if "tmp" in locals() and os.path.exists(tmp.name):
            os.unlink(tmp.name)


def api_dataset_info(request, dataset_id):
    """Return filename and format metadata for a dataset."""
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)
    if not dataset.is_visible_to(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)
    return JsonResponse(
        {
            "name": dataset.name,
            "filename": dataset.file.name.split("/")[-1],
            "format": dataset.format,
        }
    )
