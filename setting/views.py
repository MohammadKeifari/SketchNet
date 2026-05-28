from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse


@login_required
def settings_view(request):
    user_settings = request.user.settings

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
            user_settings.save()
            messages.success(request, "Settings saved.")
        return redirect("setting:settings")

    return render(
        request,
        "setting/settings.html",
        {
            "settings": user_settings,
        },
    )


@login_required
def update_sidebar_preference(request):
    """AJAX endpoint to update sidebar collapse preferences."""
    if request.method == "POST":
        import json

        data = json.loads(request.body)
        user_settings = request.user.settings

        if "collapse_left_sidebar" in data:
            user_settings.collapse_left_sidebar = data["collapse_left_sidebar"]
        if "collapse_right_sidebar" in data:
            user_settings.collapse_right_sidebar = data["collapse_right_sidebar"]

        user_settings.save()
        return JsonResponse({"success": True})

    return JsonResponse({"error": "Invalid request"}, status=400)
