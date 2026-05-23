from django.test import TestCase
from django.urls import reverse


class DataURLTests(TestCase):

    def test_dashboard_url(self):
        self.assertEqual(reverse("data:dashboard"), "/data/")

    def test_upload_url(self):
        self.assertEqual(reverse("data:upload"), "/data/upload/")

    def test_detail_url(self):
        url = reverse("data:detail", kwargs={"dataset_id": "abcd1234"})
        self.assertEqual(url, "/data/abcd1234/")

    def test_edit_url(self):
        url = reverse("data:edit", kwargs={"dataset_id": "abcd1234"})
        self.assertEqual(url, "/data/abcd1234/edit/")

    def test_delete_url(self):
        url = reverse("data:delete", kwargs={"dataset_id": "abcd1234"})
        self.assertEqual(url, "/data/abcd1234/delete/")

    def test_download_url(self):
        url = reverse("data:download", kwargs={"dataset_id": "abcd1234"})
        self.assertEqual(url, "/data/abcd1234/download/")

    def test_like_url(self):
        url = reverse("data:like", kwargs={"dataset_id": "abcd1234"})
        self.assertEqual(url, "/data/abcd1234/like/")

    def test_my_datasets_url(self):
        self.assertEqual(reverse("data:my"), "/data/my/")

    def test_liked_datasets_url(self):
        self.assertEqual(reverse("data:liked"), "/data/liked/")

    def test_all_datasets_url(self):
        self.assertEqual(reverse("data:all"), "/data/all/")

    def test_search_users_url(self):
        url = reverse("data:search_users", kwargs={"dataset_id": "abcd1234"})
        self.assertEqual(url, "/data/abcd1234/search-users/")

    def test_add_user_url(self):
        url = reverse("data:add_user", kwargs={"dataset_id": "abcd1234", "user_id": 1})
        self.assertEqual(url, "/data/abcd1234/add-user/1/")

    def test_remove_user_url(self):
        url = reverse(
            "data:remove_user", kwargs={"dataset_id": "abcd1234", "user_id": 1}
        )
        self.assertEqual(url, "/data/abcd1234/remove-user/1/")

    def test_fixed_urls_not_matched_as_dataset_id(self):
        """Fixed paths like 'my', 'liked', 'all' don't conflict with dataset IDs"""
        self.assertEqual(reverse("data:my"), "/data/my/")
        self.assertEqual(reverse("data:liked"), "/data/liked/")
        self.assertEqual(reverse("data:all"), "/data/all/")
        self.assertEqual(reverse("data:upload"), "/data/upload/")
