import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model, login
from django.utils import timezone

GUEST_TTL = timedelta(hours=24)
GUEST_LOGIN_BACKEND = "django.contrib.auth.backends.ModelBackend"


def prune_expired_guests():
    """Delete guest accounts older than GUEST_TTL."""
    User = get_user_model()
    User.objects.filter(
        is_guest=True, date_joined__lt=timezone.now() - GUEST_TTL
    ).delete()


def create_guest_user():
    """Create a throwaway user that cannot persist profile or models."""
    User = get_user_model()
    prune_expired_guests()
    uid = uuid.uuid4().hex[:12]
    user = User(
        username=f"guest_{uid}",
        email=f"guest_{uid}@guest.sketchnet.invalid",
        is_guest=True,
    )
    user.set_unusable_password()
    user.save()
    return user


def login_guest(request, user):
    """Log the guest in with the default model backend."""
    login(request, user, backend=GUEST_LOGIN_BACKEND)
