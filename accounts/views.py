from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import Http404
from models_library.models import SketchModel
from data_manager.models import Dataset
from accounts.forms import ProfileForm

User = get_user_model()


@login_required
def profile(request):
    """Render and update the authenticated user's profile page."""
    if request.method == "POST":
        form = ProfileForm(
            request.POST, request.FILES, instance=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "account/profile.html", {"form": form})


def public_profile(request, username):
    """Public profile page listing a user's public models and datasets."""
    profile_user = get_object_or_404(User, username=username)
    settings = profile_user.settings
    is_owner = request.user.is_authenticated and request.user == profile_user
    if not settings.public_profile and not is_owner:
        raise Http404("This profile is private.")

    public_models = SketchModel.objects.filter(
        owner=profile_user, view_access="public"
    )
    public_datasets = Dataset.objects.filter(
        owner=profile_user, is_private=False
    )

    return render(
        request,
        "account/public_profile.html",
        {
            "profile_user": profile_user,
            "public_models": public_models,
            "public_datasets": public_datasets,
            "is_owner": is_owner,
            "profile_is_public": settings.public_profile,
        },
    )
