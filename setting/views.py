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
