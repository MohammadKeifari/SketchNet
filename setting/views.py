from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages


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
