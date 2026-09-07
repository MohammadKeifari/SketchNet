from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages


@login_required
def settings_view(request):
    """Display and update the current user's theme and sidebar preferences."""
    user_settings = request.user.settings
    saved = False

    if request.method == "POST":
        theme = request.POST.get("theme")
        if theme in [
            "light",
            "dark",
            "rose",
            "dark-rose",
            "forest",
            "forest-dark",
            "honey",
            "honey-dark",
            "system",
        ]:
            user_settings.theme = theme

        user_settings.collapse_left_sidebar = (
            request.POST.get("collapse_left_sidebar") == "on"
        )
        user_settings.collapse_right_sidebar = (
            request.POST.get("collapse_right_sidebar") == "on"
        )

        export_format = request.POST.get("default_export_format")
        if export_format in ("pytorch-py", "pytorch-zip"):
            user_settings.default_export_format = export_format

        highlight_phase = request.POST.get("highlight_phase_on_open")
        if highlight_phase in ("none", "preprocessing", "training", "evaluation"):
            user_settings.highlight_phase_on_open = highlight_phase

        user_settings.public_profile = request.POST.get("public_profile") == "on"

        user_settings.save()
        saved = True

    return render(
        request,
        "setting/settings.html",
        {
            "settings": user_settings,
            "saved": saved,
        },
    )
