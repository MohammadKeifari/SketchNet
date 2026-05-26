from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from models_library.models import SketchModel, ModelAccess, generate_model_id
from django.urls import reverse

User = get_user_model()


class SketchModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.other = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="testpass123",
        )

    def test_create_model(self):
        """Model is created with correct defaults"""
        model = SketchModel.objects.create(
            name="Test Model",
            description="A test model",
            graph_data={"nodes": [], "links": []},
            owner=self.user,
        )
        self.assertEqual(model.name, "Test Model")
        self.assertEqual(model.owner, self.user)
        self.assertEqual(model.view_access, "public")
        self.assertEqual(model.fork_access, "private")
        self.assertFalse(model.cover_image)
        self.assertEqual(model.views, 0)
        self.assertEqual(model.downloads, 0)
        self.assertEqual(model.forks_count, 0)

    def test_model_id_generated(self):
        """Model ID is auto-generated and 10 characters"""
        model = SketchModel.objects.create(
            name="Test",
            graph_data={},
            owner=self.user,
        )
        self.assertIsNotNone(model.model_id)
        self.assertEqual(len(model.model_id), 10)
        self.assertTrue(model.model_id.isalnum())

    def test_model_id_unique(self):
        """Each model gets a unique ID"""
        m1 = SketchModel.objects.create(name="M1", graph_data={}, owner=self.user)
        m2 = SketchModel.objects.create(name="M2", graph_data={}, owner=self.user)
        self.assertNotEqual(m1.model_id, m2.model_id)

    def test_str_method(self):
        """String representation includes name and ID"""
        model = SketchModel.objects.create(
            name="My Model",
            graph_data={},
            owner=self.user,
        )
        self.assertIn("My Model", str(model))
        self.assertIn(model.model_id, str(model))

    def test_likes_count(self):
        """Likes count returns correct number"""
        model = SketchModel.objects.create(
            name="Liked",
            graph_data={},
            owner=self.user,
        )
        user2 = User.objects.create_user(
            username="fan", email="fan@test.com", password="pass"
        )
        user3 = User.objects.create_user(
            username="fan2", email="fan2@test.com", password="pass"
        )
        model.liked_by.add(user2, user3)
        self.assertEqual(model.likes_count, 2)

    def test_can_view_public(self):
        """Anyone can view a public model"""
        model = SketchModel.objects.create(
            name="Public",
            graph_data={},
            owner=self.user,
            view_access="public",
        )
        self.assertTrue(model.can_view(self.other))
        self.assertTrue(model.can_view(self.user))

    def test_can_view_private(self):
        """Only owner and allowed users can view private model"""
        model = SketchModel.objects.create(
            name="Private",
            graph_data={},
            owner=self.user,
            view_access="private",
        )
        self.assertTrue(model.can_view(self.user))
        self.assertFalse(model.can_view(self.other))

    def test_can_view_private_with_access(self):
        """User with ModelAccess can view private model"""
        model = SketchModel.objects.create(
            name="Private Shared",
            graph_data={},
            owner=self.user,
            view_access="private",
        )
        ModelAccess.objects.create(user=self.other, model=model, can_view=True)
        self.assertTrue(model.can_view(self.other))

    def test_can_fork_public(self):
        """Anyone can fork a public-fork model"""
        model = SketchModel.objects.create(
            name="Forkable",
            graph_data={},
            owner=self.user,
            fork_access="public",
        )
        self.assertTrue(model.can_fork(self.other))

    def test_can_fork_private(self):
        """Only owner can fork private-fork model"""
        model = SketchModel.objects.create(
            name="NoFork",
            graph_data={},
            owner=self.user,
            fork_access="private",
        )
        self.assertTrue(model.can_fork(self.user))
        self.assertFalse(model.can_fork(self.other))

    def test_can_fork_private_with_access(self):
        """User with can_fork access can fork"""
        model = SketchModel.objects.create(
            name="SharedFork",
            graph_data={},
            owner=self.user,
            fork_access="private",
        )
        ModelAccess.objects.create(user=self.other, model=model, can_fork=True)
        self.assertTrue(model.can_fork(self.other))

    def test_can_edit(self):
        """Only owner can edit"""
        model = SketchModel.objects.create(
            name="Mine",
            graph_data={},
            owner=self.user,
        )
        self.assertTrue(model.can_edit(self.user))
        self.assertFalse(model.can_edit(self.other))

    def test_can_delete(self):
        """Only owner can delete"""
        model = SketchModel.objects.create(
            name="Mine",
            graph_data={},
            owner=self.user,
        )
        self.assertTrue(model.can_delete(self.user))
        self.assertFalse(model.can_delete(self.other))

    def test_fork_increments_counter(self):
        original = SketchModel.objects.create(
            name="Original",
            graph_data={},
            owner=self.user,
            fork_access="public",
        )

        logged_in = self.client.login(username="otheruser", password="testpass123")
        self.assertTrue(logged_in, "Login failed")

        url = reverse("models:fork", kwargs={"model_id": original.model_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        original.refresh_from_db()
        self.assertEqual(original.forks_count, 1)

    def test_ordering_newest_first(self):
        """Models are ordered by created_at descending"""
        m1 = SketchModel.objects.create(name="Old", graph_data={}, owner=self.user)
        import time

        time.sleep(0.01)
        m2 = SketchModel.objects.create(name="New", graph_data={}, owner=self.user)
        models = SketchModel.objects.all()
        self.assertEqual(models[0].name, "New")
        self.assertEqual(models[1].name, "Old")

    def test_model_with_cover_image(self):
        """Model can have a cover image"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        image = SimpleUploadedFile(
            "cover.jpg", b"fake-image-data", content_type="image/jpeg"
        )
        model = SketchModel.objects.create(
            name="With Cover",
            graph_data={},
            owner=self.user,
            cover_image=image,
        )
        self.assertTrue(model.cover_image)
        self.assertIn("cover", model.cover_image.name)


class ModelAccessTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="owner", email="o@t.com", password="pass"
        )
        self.other = User.objects.create_user(
            username="viewer", email="v@t.com", password="pass"
        )
        self.model = SketchModel.objects.create(
            name="Test",
            graph_data={},
            owner=self.user,
            view_access="private",
            fork_access="private",
        )

    def test_create_access(self):
        """ModelAccess grants specific permissions"""
        access = ModelAccess.objects.create(
            user=self.other, model=self.model, can_view=True, can_fork=False
        )
        self.assertTrue(access.can_view)
        self.assertFalse(access.can_fork)

    def test_unique_together(self):
        """Cannot create duplicate access for same user and model"""
        ModelAccess.objects.create(user=self.other, model=self.model, can_view=True)
        with self.assertRaises(IntegrityError):
            ModelAccess.objects.create(
                user=self.other, model=self.model, can_view=False
            )

    def test_str_method(self):
        """String representation shows user and model"""
        access = ModelAccess.objects.create(
            user=self.other, model=self.model, can_view=True
        )
        self.assertIn("viewer", str(access))
        self.assertIn("Test", str(access))

    def test_access_controls_view(self):
        """Access controls what user can do"""
        ModelAccess.objects.create(
            user=self.other, model=self.model, can_view=True, can_fork=False
        )
        self.assertTrue(self.model.can_view(self.other))
        self.assertFalse(self.model.can_fork(self.other))

    def test_access_controls_fork(self):
        """Access controls forking"""
        ModelAccess.objects.create(
            user=self.other, model=self.model, can_view=False, can_fork=True
        )
        self.assertFalse(self.model.can_view(self.other))
        self.assertTrue(self.model.can_fork(self.other))


class GenerateModelIdTests(TestCase):

    def test_id_length(self):
        """Generated ID is 10 characters"""
        id = generate_model_id()
        self.assertEqual(len(id), 10)

    def test_id_alphanumeric(self):
        """Generated ID contains only letters and digits"""
        import re

        id = generate_model_id()
        self.assertTrue(re.match(r"^[a-zA-Z0-9]+$", id))
