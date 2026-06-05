from django.test import TestCase
from django.urls import reverse


class ModelURLTests(TestCase):

    def test_dashboard_url(self):
        """Verify dashboard url."""
        self.assertEqual(reverse("models:dashboard"), "/models/")

    def test_save_url(self):
        """Verify save url."""
        self.assertEqual(reverse("models:save"), "/models/save/")

    def test_view_url(self):
        """Verify view url."""
        url = reverse("models:view", kwargs={"model_id": "abc1234567"})
        self.assertEqual(url, "/models/abc1234567/")

    def test_update_url(self):
        """Verify update url."""
        url = reverse("models:update", kwargs={"model_id": "abc1234567"})
        self.assertEqual(url, "/models/abc1234567/update/")

    def test_edit_url(self):
        """Verify edit url."""
        url = reverse("models:edit", kwargs={"model_id": "abc1234567"})
        self.assertEqual(url, "/models/abc1234567/edit/")

    def test_fork_url(self):
        """Verify fork url."""
        url = reverse("models:fork", kwargs={"model_id": "abc1234567"})
        self.assertEqual(url, "/models/abc1234567/fork/")

    def test_delete_url(self):
        """Verify delete url."""
        url = reverse("models:delete", kwargs={"model_id": "abc1234567"})
        self.assertEqual(url, "/models/abc1234567/delete/")

    def test_download_url(self):
        """Verify download url."""
        url = reverse("models:download", kwargs={"model_id": "abc1234567"})
        self.assertEqual(url, "/models/abc1234567/download/")

    def test_like_url(self):
        """Verify like url."""
        url = reverse("models:like", kwargs={"model_id": "abc1234567"})
        self.assertEqual(url, "/models/abc1234567/like/")

    def test_api_data_url(self):
        """Verify api data url."""
        url = reverse("models:api_data", kwargs={"model_id": "abc1234567"})
        self.assertEqual(url, "/models/abc1234567/data/")

    def test_api_list_url(self):
        """Verify api list url."""
        self.assertEqual(reverse("models:api_list"), "/models/api/list/")

    def test_my_models_url(self):
        """Verify my models url."""
        self.assertEqual(reverse("models:my"), "/models/my/")

    def test_liked_models_url(self):
        """Verify liked models url."""
        self.assertEqual(reverse("models:liked"), "/models/liked/")

    def test_all_models_url(self):
        """Verify all models url."""
        self.assertEqual(reverse("models:all"), "/models/all/")

    def test_fixed_urls_not_matched_as_model_id(self):
        """Fixed paths like 'my', 'all', 'save' don't conflict with model IDs"""
        self.assertEqual(reverse("models:my"), "/models/my/")
        self.assertEqual(reverse("models:all"), "/models/all/")
        self.assertEqual(reverse("models:save"), "/models/save/")
        self.assertEqual(reverse("models:api_list"), "/models/api/list/")
