from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from models_library.models import SketchModel
from setting.models import UserSettings

User = get_user_model()


class GuestLoginTests(TestCase):

    def test_login_page_offers_guest_not_google(self):
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continue as test user")
        self.assertNotContains(response, "Continue with Google")

    def test_signup_page_offers_guest_not_google(self):
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continue as test user")
        self.assertNotContains(response, "Continue with Google")

    def test_guest_login_creates_user_and_opens_canvas(self):
        response = self.client.post(reverse("guest_login"))
        self.assertRedirects(response, reverse("sketchmod:canvas"))
        guests = User.objects.filter(is_guest=True)
        self.assertEqual(guests.count(), 1)
        guest = guests.get()
        self.assertTrue(guest.username.startswith("guest_"))
        self.assertFalse(guest.has_usable_password())

    def test_guest_login_when_already_guest_reuses_session(self):
        self.client.post(reverse("guest_login"))
        first_id = User.objects.get(is_guest=True).pk
        response = self.client.post(reverse("guest_login"))
        self.assertRedirects(response, reverse("sketchmod:canvas"))
        self.assertEqual(User.objects.filter(is_guest=True).count(), 1)
        self.assertEqual(User.objects.get(is_guest=True).pk, first_id)

    def test_guest_cannot_save_profile(self):
        self.client.post(reverse("guest_login"))
        guest = User.objects.get(is_guest=True)
        response = self.client.post(
            reverse("profile"),
            {"bio": "should not persist"},
            HTTP_ACCEPT="text/html",
        )
        guest.refresh_from_db()
        self.assertEqual(guest.bio, "")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("sketchmod:canvas"))

    def test_guest_can_save_settings_for_session(self):
        self.client.post(reverse("guest_login"))
        guest = User.objects.get(is_guest=True)
        response = self.client.post(
            reverse("setting:settings"),
            {
                "theme": "dark",
                "collapse_left_sidebar": "on",
                "default_export_format": "pytorch-zip",
                "highlight_phase_on_open": "training",
                "public_profile": "on",
            },
            HTTP_ACCEPT="text/html",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Settings saved.")
        settings = UserSettings.objects.get(user=guest)
        self.assertEqual(settings.theme, "dark")
        self.assertTrue(settings.collapse_left_sidebar)
        self.assertEqual(settings.default_export_format, "pytorch-zip")
        self.assertEqual(settings.highlight_phase_on_open, "training")
        self.assertFalse(settings.public_profile)

    def test_guest_settings_page_allows_save(self):
        self.client.post(reverse("guest_login"))
        response = self.client.get(reverse("setting:settings"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Save Settings")
        self.assertContains(response, "apply for this session")
        self.assertNotContains(response, "Public profile")

    def test_guest_cannot_save_model(self):
        self.client.post(reverse("guest_login"))
        response = self.client.post(
            reverse("models:save"),
            {
                "name": "Guest Model",
                "graph_data": '{"nodes":[],"links":[]}',
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["success"])
        self.assertEqual(SketchModel.objects.count(), 0)

    def test_guest_logout_deletes_user(self):
        self.client.post(reverse("guest_login"))
        guest_id = User.objects.get(is_guest=True).pk
        response = self.client.post(reverse("account_logout"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=guest_id).exists())

    def test_guest_create_account_opens_signup(self):
        self.client.post(reverse("guest_login"))
        guest_id = User.objects.get(is_guest=True).pk
        response = self.client.get(reverse("guest_to_signup"))
        self.assertRedirects(response, reverse("account_signup"))
        self.assertFalse(User.objects.filter(pk=guest_id).exists())
        follow = self.client.get(reverse("account_signup"))
        self.assertContains(follow, "Create Account")


class SignupWithoutVerificationTests(TestCase):

    def test_signup_logs_in_without_email_confirm(self):
        response = self.client.post(
            reverse("account_signup"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )
        self.assertRedirects(response, "/")
        self.assertTrue(User.objects.filter(username="newuser").exists())
        follow = self.client.get(reverse("profile"))
        self.assertEqual(follow.status_code, 200)
        self.assertContains(follow, "newuser")
