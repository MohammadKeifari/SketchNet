from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def profile(request):
    """Render the authenticated user's profile page."""
    return render(request, "account/profile.html")
