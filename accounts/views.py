from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, logout
from django.contrib import messages
from django.http import Http404
from django.views.decorators.http import require_POST
from models_library.models import SketchModel
from data_manager.models import Dataset
from accounts.forms import ProfileForm
from accounts.guest import create_guest_user, login_guest

User = get_user_model()


@require_POST
def guest_login(request):
    """Create a temporary test user and send them to SketchMod."""
    if request.user.is_authenticated:
        if request.user.is_guest:
            return redirect("sketchmod:canvas")
        messages.info(request, "You're already signed in.")
        return redirect("home")

    user = create_guest_user()
    login_guest(request, user)
    messages.info(
        request,
        "You're using a test account. You can sketch and export, but nothing is saved.",
    )
    return redirect("sketchmod:canvas")


def guest_to_signup(request):
    """Drop a test session so the visitor can create a real account."""
    if request.user.is_authenticated and getattr(request.user, "is_guest", False):
        logout(request)
    elif request.user.is_authenticated:
        return redirect("home")
    return redirect("account_signup")


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
