import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.seed.catalog import (
    EXPECTED_DATASET_COUNT,
    EXPECTED_MODEL_COUNT,
    STARTER_USERNAME,
)
from data_manager.models import Dataset
from models_library.models import SketchModel

User = get_user_model()


class SeedStarterCommandTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.mkdtemp()
        media_override = override_settings(MEDIA_ROOT=self.media_dir)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.media_dir, ignore_errors=True))

        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
        )
        self.other = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="alicepass123",
        )
        leftover = Dataset(
            name="junk",
            format="csv",
            owner=self.other,
            is_private=False,
        )
        leftover.save()
        leftover.file.save("junk.csv", ContentFile(b"a,b\n1,2\n"), save=True)
        SketchModel.objects.create(
            name="junk-model",
            owner=self.other,
            graph_data={"nodes": [], "links": []},
        )

    def test_refuses_without_wipe(self):
        with self.assertRaises(CommandError):
            call_command("seed_starter")
        self.assertTrue(User.objects.filter(username="alice").exists())
        self.assertEqual(Dataset.objects.filter(name="junk").count(), 1)

    def test_wipe_and_seed(self):
        call_command("seed_starter", "--wipe")

        self.assertTrue(
            User.objects.filter(pk=self.admin.pk, is_superuser=True).exists()
        )
        self.assertFalse(User.objects.filter(username="alice").exists())

        catalog = User.objects.get(username=STARTER_USERNAME)
        self.assertFalse(catalog.is_staff)
        self.assertFalse(catalog.is_superuser)
        self.assertFalse(catalog.has_usable_password())
        self.assertTrue(catalog.settings.public_profile)
        self.assertTrue(catalog.bio)
        self.assertFalse(catalog.avatar)

        response = self.client.get(
            reverse("public_profile", args=[STARTER_USERNAME])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "logo.svg")
        self.assertContains(response, "user-avatar-logo")

        self.assertEqual(Dataset.objects.count(), EXPECTED_DATASET_COUNT)
        self.assertEqual(SketchModel.objects.count(), EXPECTED_MODEL_COUNT)
        self.assertFalse(Dataset.objects.filter(name="junk").exists())

        by_name = {ds.name: ds for ds in Dataset.objects.filter(owner=catalog)}
        ids = {ds.dataset_id for ds in by_name.values()}
        for model in SketchModel.objects.filter(owner=catalog):
            self.assertEqual(model.view_access, "public")
            self.assertEqual(model.fork_access, "public")
            node = next(
                n
                for n in model.graph_data["nodes"]
                if n.get("type") == "input-data"
            )
            self.assertIn(node["datasetId"], ids)
            self.assertEqual(node["datasetName"], by_name[node["datasetName"]].name)
