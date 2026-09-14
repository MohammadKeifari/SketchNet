"""Media URLs must work with DEBUG=False (gunicorn / Cloudflare)."""

import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from data_manager.models import Dataset
from models_library.models import SketchModel

User = get_user_model()


@override_settings(DEBUG=False)
class ProductionMediaTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.mkdtemp()
        media_override = override_settings(MEDIA_ROOT=self.media_dir)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.media_dir, ignore_errors=True))
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="pass12345"
        )
        self.other = User.objects.create_user(
            username="other", email="other@example.com", password="pass12345"
        )

    def test_public_dataset_file_is_served(self):
        dataset = Dataset.objects.create(
            name="Public CSV",
            format="csv",
            file=SimpleUploadedFile("test.csv", b"a,b\n1,2\n"),
            owner=self.owner,
        )
        response = self.client.get(dataset.file.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"a,b\n1,2\n")

    def test_private_dataset_file_is_hidden(self):
        dataset = Dataset.objects.create(
            name="Secret CSV",
            format="csv",
            file=SimpleUploadedFile("secret.csv", b"hidden\n"),
            owner=self.owner,
            is_private=True,
        )
        response = self.client.get(dataset.file.url)
        self.assertEqual(response.status_code, 404)
        self.client.login(username="owner", password="pass12345")
        response = self.client.get(dataset.file.url)
        self.assertEqual(response.status_code, 200)

    def test_public_dataset_cover_is_served(self):
        dataset = Dataset.objects.create(
            name="Covered",
            format="csv",
            file=SimpleUploadedFile("test.csv", b"a,b\n1,2\n"),
            owner=self.owner,
            cover_image=SimpleUploadedFile(
                "cover.jfif", b"fake-jpeg", content_type="image/jpeg"
            ),
        )
        response = self.client.get(dataset.cover_image.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_private_model_cover_is_hidden(self):
        model = SketchModel.objects.create(
            name="Private",
            graph_data={},
            owner=self.owner,
            view_access="private",
            cover_image=SimpleUploadedFile(
                "cover.jpg", b"fake-jpeg", content_type="image/jpeg"
            ),
        )
        response = self.client.get(model.cover_image.url)
        self.assertEqual(response.status_code, 404)
        self.client.login(username="owner", password="pass12345")
        response = self.client.get(model.cover_image.url)
        self.assertEqual(response.status_code, 200)

    def test_avatar_is_served(self):
        self.owner.avatar.save(
            "face.png",
            SimpleUploadedFile("face.png", b"png-bytes", content_type="image/png"),
            save=True,
        )
        response = self.client.get(self.owner.avatar.url)
        self.assertEqual(response.status_code, 200)

    def test_path_traversal_is_rejected(self):
        response = self.client.get("/media/../config/settings.py")
        self.assertEqual(response.status_code, 404)

    def test_unknown_media_prefix_is_rejected(self):
        response = self.client.get("/media/not-a-real-prefix/file.txt")
        self.assertEqual(response.status_code, 404)

    def test_media_url_is_registered(self):
        self.assertEqual(
            reverse("serve_media", kwargs={"path": "avatars/1.png"}),
            "/media/avatars/1.png",
        )
