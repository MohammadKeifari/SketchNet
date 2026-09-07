from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress
import shutil
import tempfile
from django.test import override_settings

User = get_user_model()


class ProfileViewTests(TestCase):

    def setUp(self):
        """Set up test fixtures."""
        self.media_dir = tempfile.mkdtemp()
        media_override = override_settings(MEDIA_ROOT=self.media_dir)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.media_dir, ignore_errors=True))
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        EmailAddress.objects.create(
            user=self.user, email="test@example.com", verified=True, primary=True
        )
        self.profile_url = "/accounts/profile/"

    def test_profile_requires_login(self):
        """Unauthenticated users are redirected"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)

    def test_profile_loads_when_logged_in(self):
        """Authenticated users see profile page"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose photo")
        self.assertContains(response, "No file chosen")

    def test_profile_shows_username(self):
        """Profile displays the user's username"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.profile_url)
        self.assertContains(response, "testuser")

    def test_profile_shows_email(self):
        """Profile displays the user's email"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.profile_url)
        self.assertContains(response, "test@example.com")

    def test_profile_has_change_password_link(self):
        """Profile has link to change password"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.profile_url)
        self.assertContains(response, reverse("account_change_password"))

    def test_profile_has_manage_email_link(self):
        """Profile has link to manage email"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.profile_url)
        self.assertContains(response, reverse("account_email"))

    def test_profile_has_signout_link(self):
        """Profile has sign out link"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.profile_url)
        self.assertContains(response, reverse("account_logout"))

    def test_profile_uses_correct_template(self):
        """Profile uses the right template"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.profile_url)
        self.assertTemplateUsed(response, "account/profile.html")

    def test_profile_updates_bio(self):
        """POST saves a bio and redirects back to profile."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            self.profile_url,
            {"bio": "Builds models on a canvas."},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, "Builds models on a canvas.")
        self.assertContains(response, "Profile updated.")

    def test_profile_uploads_avatar(self):
        """POST stores a PNG avatar and shows it on the profile."""
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (8, 8), "red").save(buf, format="PNG")
        upload = SimpleUploadedFile(
            "photo.png", buf.getvalue(), content_type="image/png"
        )
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            self.profile_url,
            {"bio": "", "avatar": upload},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar)
        self.assertContains(response, "user-avatar-img")

    def test_profile_rejects_oversize_avatar(self):
        """POST rejects photos larger than 2 MB."""
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (8, 8), "red").save(buf, format="PNG")
        payload = buf.getvalue() + b"\x00" * (2 * 1024 * 1024 + 1)
        upload = SimpleUploadedFile(
            "huge.png", payload, content_type="image/png"
        )
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            self.profile_url, {"bio": "", "avatar": upload}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "under 2MB")
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)

    def test_profile_rejects_non_image_avatar(self):
        """POST rejects a text file uploaded as the avatar."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        upload = SimpleUploadedFile(
            "notes.txt", b"not an image", content_type="text/plain"
        )
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            self.profile_url, {"bio": "", "avatar": upload}
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)

    def test_profile_removes_avatar(self):
        """POST with remove_avatar clears the stored photo."""
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (8, 8), "blue").save(buf, format="PNG")
        self.user.avatar.save(
            "photo.png",
            SimpleUploadedFile("photo.png", buf.getvalue(), content_type="image/png"),
            save=True,
        )
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            self.profile_url,
            {"bio": "ok", "remove_avatar": "on"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)

    def test_navbar_letter_fallback_without_avatar(self):
        """Navbar shows the username initial when there is no photo."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("home"))
        html = response.content.decode()
        self.assertIn('class="user-avatar"', html)
        self.assertRegex(html, r"user-avatar[^>]*>\s*T\s*<")
        self.assertNotIn("user-avatar-img", html)

