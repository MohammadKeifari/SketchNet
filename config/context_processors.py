from django.conf import settings


def google_oauth(request):
    return {
        "google_oauth_configured": bool(
            getattr(settings, "GOOGLE_CLIENT_ID", "")
            and getattr(settings, "GOOGLE_CLIENT_SECRET", "")
        )
    }
