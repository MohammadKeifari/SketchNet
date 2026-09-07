import shutil
import tempfile
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class PublicProfileTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.mkdtemp()
        media_override = override_settings(MEDIA_ROOT=self.media_dir)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.media_dir, ignore_errors=True))
        self.user = User.objects.create_user(
            username="publicuser",
            email="public@example.com",
            password="pass",
        )
        self.user.settings.public_profile = True
        self.user.settings.save()

    def test_public_profile_visible(self):
        response = self.client.get(
            reverse("public_profile", args=["publicuser"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "publicuser")

    def test_private_profile_hidden(self):
        self.user.settings.public_profile = False
        self.user.settings.save()
        response = self.client.get(
            reverse("public_profile", args=["publicuser"])
        )
        self.assertEqual(response.status_code, 404)

    def test_owner_sees_private_profile(self):
        self.user.settings.public_profile = False
        self.user.settings.save()
        self.client.login(username="publicuser", password="pass")
        response = self.client.get(
            reverse("public_profile", args=["publicuser"])
        )
        self.assertEqual(response.status_code, 200)

    def test_public_profile_shows_bio(self):
        self.user.bio = "I share public models."
        self.user.save()
        response = self.client.get(
            reverse("public_profile", args=["publicuser"])
        )
        self.assertContains(response, "I share public models.")

    def test_public_profile_shows_avatar(self):
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (8, 8), "green").save(buf, format="PNG")
        self.user.avatar.save(
            "face.png",
            SimpleUploadedFile("face.png", buf.getvalue(), content_type="image/png"),
            save=True,
        )
        response = self.client.get(
            reverse("public_profile", args=["publicuser"])
        )
        self.assertContains(response, "user-avatar-img")

    def test_sketchnet_profile_uses_themed_logo(self):
        catalog = User.objects.create_user(
            username="SketchNet",
            email="sketchnet@example.com",
            password="unused-pass-123",
        )
        catalog.settings.public_profile = True
        catalog.settings.save()
        response = self.client.get(
            reverse("public_profile", args=["SketchNet"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "logo.svg")
        self.assertContains(response, "user-avatar-logo")
        self.assertNotContains(response, "user-avatar-img")
