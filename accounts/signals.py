from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver


@receiver(user_logged_out)
def delete_guest_on_logout(sender, request, user, **kwargs):
    """Throw away the temporary user when a guest signs out."""
    if user is not None and getattr(user, "is_guest", False):
        user.delete()
