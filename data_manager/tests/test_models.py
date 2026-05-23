from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from data_manager.models import Dataset, generate_dataset_id

User = get_user_model()


class DatasetModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.file = SimpleUploadedFile("test.csv", b"col1,col2\n1,2\n3,4")

    def test_create_dataset(self):
        """Dataset is created with correct fields"""
        dataset = Dataset.objects.create(
            name="Test Dataset",
            description="A test dataset",
            format="csv",
            file=self.file,
            owner=self.user,
        )
        self.assertEqual(dataset.name, "Test Dataset")
        self.assertEqual(dataset.format, "csv")
        self.assertEqual(dataset.owner, self.user)
        self.assertFalse(dataset.is_private)

    def test_dataset_id_generated(self):
        """Dataset ID is auto-generated and 8 characters"""
        dataset = Dataset.objects.create(
            name="Test",
            format="csv",
            file=self.file,
            owner=self.user,
        )
        self.assertIsNotNone(dataset.dataset_id)
        self.assertEqual(len(dataset.dataset_id), 8)
        self.assertTrue(dataset.dataset_id.isalnum())

    def test_dataset_id_unique(self):
        """Each dataset gets a unique ID"""
        file2 = SimpleUploadedFile("test2.csv", b"data")
        d1 = Dataset.objects.create(
            name="Test 1",
            format="csv",
            file=self.file,
            owner=self.user,
        )
        d2 = Dataset.objects.create(
            name="Test 2",
            format="csv",
            file=file2,
            owner=self.user,
        )
        self.assertNotEqual(d1.dataset_id, d2.dataset_id)

    def test_str_method(self):
        """String representation includes name and ID"""
        dataset = Dataset.objects.create(
            name="My Dataset",
            format="csv",
            file=self.file,
            owner=self.user,
        )
        self.assertIn("My Dataset", str(dataset))
        self.assertIn(dataset.dataset_id, str(dataset))

    def test_default_not_private(self):
        """New datasets are public by default"""
        dataset = Dataset.objects.create(
            name="Public",
            format="csv",
            file=self.file,
            owner=self.user,
        )
        self.assertFalse(dataset.is_private)

    def test_private_dataset(self):
        """Dataset can be set to private"""
        dataset = Dataset.objects.create(
            name="Private",
            format="csv",
            file=self.file,
            owner=self.user,
            is_private=True,
        )
        self.assertTrue(dataset.is_private)

    def test_likes_count(self):
        """Likes count returns correct number"""
        dataset = Dataset.objects.create(
            name="Liked",
            format="csv",
            file=self.file,
            owner=self.user,
        )
        user2 = User.objects.create_user(
            username="fan",
            email="fan@example.com",
            password="pass123",
        )
        user3 = User.objects.create_user(
            username="fan2",
            email="fan2@example.com",
            password="pass123",
        )
        dataset.liked_by.add(user2, user3)
        self.assertEqual(dataset.likes_count, 2)

    def test_popularity_score(self):
        """Popularity is calculated correctly"""
        dataset = Dataset.objects.create(
            name="Popular",
            format="csv",
            file=self.file,
            owner=self.user,
        )
        dataset.downloads = 5
        dataset.views = 10
        dataset.save()
        user2 = User.objects.create_user(
            username="liker",
            email="liker@example.com",
            password="pass123",
        )
        dataset.liked_by.add(user2)
        # popularity = downloads*2 + views + likes*3 = 10 + 10 + 3 = 23
        self.assertEqual(dataset.popularity, 23)

    def test_is_visible_to_owner(self):
        """Owner can always see their dataset"""
        dataset = Dataset.objects.create(
            name="Secret",
            format="csv",
            file=self.file,
            owner=self.user,
            is_private=True,
        )
        self.assertTrue(dataset.is_visible_to(self.user))

    def test_is_visible_to_allowed_user(self):
        """Allowed users can see private datasets"""
        dataset = Dataset.objects.create(
            name="Shared",
            format="csv",
            file=self.file,
            owner=self.user,
            is_private=True,
        )
        other = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="pass123",
        )
        dataset.allowed_users.add(other)
        self.assertTrue(dataset.is_visible_to(other))

    def test_is_not_visible_to_random_user(self):
        """Random users cannot see private datasets"""
        dataset = Dataset.objects.create(
            name="Hidden",
            format="csv",
            file=self.file,
            owner=self.user,
            is_private=True,
        )
        stranger = User.objects.create_user(
            username="stranger",
            email="stranger@example.com",
            password="pass123",
        )
        self.assertFalse(dataset.is_visible_to(stranger))

    def test_is_visible_public_to_anonymous(self):
        """Public datasets are visible to everyone"""
        dataset = Dataset.objects.create(
            name="Open",
            format="csv",
            file=self.file,
            owner=self.user,
            is_private=False,
        )
        from django.contrib.auth.models import AnonymousUser

        anon = AnonymousUser()
        self.assertTrue(dataset.is_visible_to(anon))

    def test_can_edit(self):
        """Only owner can edit"""
        dataset = Dataset.objects.create(
            name="Mine",
            format="csv",
            file=self.file,
            owner=self.user,
        )
        other = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="pass123",
        )
        self.assertTrue(dataset.can_edit(self.user))
        self.assertFalse(dataset.can_edit(other))

    def test_can_delete(self):
        """Only owner can delete"""
        dataset = Dataset.objects.create(
            name="Mine",
            format="csv",
            file=self.file,
            owner=self.user,
        )
        other = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="pass123",
        )
        self.assertTrue(dataset.can_delete(self.user))
        self.assertFalse(dataset.can_delete(other))

    def test_ordering_newest_first(self):
        """Datasets are ordered by created_at descending"""
        file2 = SimpleUploadedFile("test2.csv", b"data")
        d1 = Dataset.objects.create(
            name="Old",
            format="csv",
            file=self.file,
            owner=self.user,
        )
        d2 = Dataset.objects.create(
            name="New",
            format="csv",
            file=file2,
            owner=self.user,
        )
        datasets = Dataset.objects.all()
        self.assertEqual(datasets[0], d2)
        self.assertEqual(datasets[1], d1)

    def test_downloads_default_zero(self):
        """New dataset starts with 0 downloads"""
        dataset = Dataset.objects.create(
            name="Fresh",
            format="csv",
            file=self.file,
            owner=self.user,
        )
        self.assertEqual(dataset.downloads, 0)

    def test_views_default_zero(self):
        """New dataset starts with 0 views"""
        dataset = Dataset.objects.create(
            name="Fresh",
            format="csv",
            file=self.file,
            owner=self.user,
        )
        self.assertEqual(dataset.views, 0)
