import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from data_manager.models import Dataset

User = get_user_model()


class DataViewTests(TestCase):

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
        self.file = SimpleUploadedFile("test.csv", b"col1,col2\n1,2\n3,4")
        self.dataset = Dataset.objects.create(
            name="Public Dataset",
            description="A public test dataset",
            format="csv",
            file=self.file,
            owner=self.user,
        )

    def _login(self):
        self.client.login(username="testuser", password="testpass123")

    # ===== DASHBOARD =====
    def test_dashboard_loads(self):
        """Dashboard page loads for everyone"""
        response = self.client.get(reverse("data:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "data_manager/dashboard.html")

    def test_dashboard_shows_public_datasets(self):
        """Public datasets appear on dashboard"""
        response = self.client.get(reverse("data:dashboard"))
        self.assertContains(response, "Public Dataset")

    def test_dashboard_does_not_show_private_to_anonymous(self):
        """Private datasets hidden from anonymous users"""
        self.dataset.is_private = True
        self.dataset.save()
        response = self.client.get(reverse("data:dashboard"))
        self.assertNotContains(response, "Public Dataset")

    # ===== UPLOAD =====
    def test_upload_requires_login(self):
        """Upload redirects unauthenticated users"""
        response = self.client.get(reverse("data:upload"))
        self.assertEqual(response.status_code, 302)

    def test_upload_get_redirects(self):
        """GET to upload redirects to dashboard"""
        self._login()
        response = self.client.get(reverse("data:upload"))
        self.assertRedirects(response, reverse("data:dashboard"))

    def test_upload_creates_dataset(self):
        """POST upload creates a new dataset"""
        self._login()
        file = SimpleUploadedFile("new.csv", b"a,b\n1,2")
        response = self.client.post(
            reverse("data:upload"),
            {
                "name": "New Dataset",
                "description": "Fresh data",
                "format": "csv",
                "file": file,
            },
        )
        self.assertEqual(Dataset.objects.count(), 2)
        new_dataset = Dataset.objects.get(name="New Dataset")
        self.assertRedirects(
            response,
            reverse("data:detail", kwargs={"dataset_id": new_dataset.dataset_id}),
        )

    def test_upload_private_redirects_to_edit(self):
        """Uploading private dataset redirects to edit page"""
        self._login()
        file = SimpleUploadedFile("private.csv", b"a,b\n1,2")
        response = self.client.post(
            reverse("data:upload"),
            {
                "name": "Private Data",
                "format": "csv",
                "file": file,
                "is_private": "on",
            },
        )
        dataset = Dataset.objects.get(name="Private Data")
        self.assertRedirects(
            response, reverse("data:edit", kwargs={"dataset_id": dataset.dataset_id})
        )

    # ===== DETAIL =====
    def test_detail_loads(self):
        """Detail page loads for public dataset"""
        response = self.client.get(
            reverse("data:detail", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "data_manager/detail.html")

    def test_detail_increments_views(self):
        """Visiting detail page increments views"""
        self._login()
        self.client.get(
            reverse("data:detail", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.dataset.refresh_from_db()
        self.assertEqual(self.dataset.views, 1)

    def test_detail_private_requires_access(self):
        """Private dataset detail page is restricted"""
        self.dataset.is_private = True
        self.dataset.save()
        self.client.login(username="otheruser", password="testpass123")
        response = self.client.get(
            reverse("data:detail", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.assertRedirects(response, reverse("data:dashboard"))

    # ===== EDIT =====
    def test_edit_requires_login(self):
        """Edit page requires login"""
        response = self.client.get(
            reverse("data:edit", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.assertEqual(response.status_code, 302)

    def test_edit_requires_owner(self):
        """Only owner can edit"""
        self.client.login(username="otheruser", password="testpass123")
        response = self.client.get(
            reverse("data:edit", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.assertRedirects(response, reverse("data:dashboard"))

    def test_edit_loads_for_owner(self):
        """Owner can access edit page"""
        self._login()
        response = self.client.get(
            reverse("data:edit", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.assertEqual(response.status_code, 200)

    def test_edit_updates_dataset(self):
        """POST to edit updates the dataset"""
        self._login()
        response = self.client.post(
            reverse("data:edit", kwargs={"dataset_id": self.dataset.dataset_id}),
            {"name": "Updated Name", "format": "csv"},
        )
        self.dataset.refresh_from_db()
        self.assertEqual(self.dataset.name, "Updated Name")
        self.assertRedirects(
            response,
            reverse("data:detail", kwargs={"dataset_id": self.dataset.dataset_id}),
        )

    # ===== DELETE =====
    def test_delete_requires_login(self):
        """Delete page requires login"""
        response = self.client.get(
            reverse("data:delete", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.assertEqual(response.status_code, 302)

    def test_delete_requires_owner(self):
        """Only owner can delete"""
        self.client.login(username="otheruser", password="testpass123")
        response = self.client.get(
            reverse("data:delete", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.assertRedirects(response, reverse("data:dashboard"))

    def test_delete_page_loads_for_owner(self):
        """Owner sees delete confirmation page"""
        self._login()
        response = self.client.get(
            reverse("data:delete", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.assertEqual(response.status_code, 200)

    def test_delete_post_removes_dataset(self):
        """POST to delete removes the dataset"""
        self._login()
        response = self.client.post(
            reverse("data:delete", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.assertEqual(Dataset.objects.count(), 0)
        self.assertRedirects(response, reverse("data:dashboard"))

    # ===== DOWNLOAD =====
    def test_download_requires_login(self):
        """Download requires login"""
        response = self.client.get(
            reverse("data:download", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.assertEqual(response.status_code, 302)

    def test_download_increments_count(self):
        """Download increments download counter"""
        self._login()
        self.client.get(
            reverse("data:download", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.dataset.refresh_from_db()
        self.assertEqual(self.dataset.downloads, 1)

    def test_download_private_requires_access(self):
        """Cannot download private datasets without access"""
        self.dataset.is_private = True
        self.dataset.save()
        self.client.login(username="otheruser", password="testpass123")
        response = self.client.get(
            reverse("data:download", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.assertRedirects(response, reverse("data:dashboard"))

    # ===== LIKE =====
    def test_like_requires_login(self):
        """Like requires login"""
        response = self.client.post(
            reverse("data:like", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.assertEqual(response.status_code, 302)

    def test_like_toggles_on(self):
        """Liking a dataset adds user to liked_by"""
        self._login()
        response = self.client.post(
            reverse("data:like", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"liked": True, "likes_count": 1})

    def test_like_toggles_off(self):
        """Unliking removes user from liked_by"""
        self._login()
        self.dataset.liked_by.add(self.user)
        response = self.client.post(
            reverse("data:like", kwargs={"dataset_id": self.dataset.dataset_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"liked": False, "likes_count": 0})

    # ===== MY DATASETS =====
    def test_my_datasets_requires_login(self):
        """My datasets requires login"""
        response = self.client.get(reverse("data:my"))
        self.assertEqual(response.status_code, 302)

    def test_my_datasets_shows_owned(self):
        """Shows datasets owned by user"""
        self._login()
        response = self.client.get(reverse("data:my"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Dataset")

    def test_my_datasets_shows_accessible(self):
        """Shows private datasets user has access to"""
        private = Dataset.objects.create(
            name="Shared With Me",
            format="csv",
            file=self.file,
            owner=self.other,
            is_private=True,
        )
        private.allowed_users.add(self.user)
        self._login()
        response = self.client.get(reverse("data:my"))
        self.assertContains(response, "Shared With Me")

    # ===== LIKED DATASETS =====
    def test_liked_datasets_requires_login(self):
        """Liked datasets requires login"""
        response = self.client.get(reverse("data:liked"))
        self.assertEqual(response.status_code, 302)

    def test_liked_datasets_shows_liked(self):
        """Shows datasets user has liked"""
        self._login()
        self.dataset.liked_by.add(self.user)
        response = self.client.get(reverse("data:liked"))
        self.assertContains(response, "Public Dataset")

    # ===== ALL DATASETS =====
    def test_all_datasets_loads(self):
        """All datasets page loads"""
        response = self.client.get(reverse("data:all"))
        self.assertEqual(response.status_code, 200)

    def test_all_datasets_search(self):
        """Search filters datasets by name"""
        Dataset.objects.create(
            name="Unique Name XYZ",
            format="csv",
            file=self.file,
            owner=self.user,
        )
        response = self.client.get(reverse("data:all") + "?search=XYZ")
        self.assertContains(response, "Unique Name XYZ")
        self.assertNotContains(response, "Public Dataset")

    def test_all_datasets_search_by_id(self):
        """Search filters datasets by ID"""
        response = self.client.get(
            reverse("data:all") + f"?search={self.dataset.dataset_id}"
        )
        self.assertContains(response, "Public Dataset")

    def test_all_datasets_search_by_username(self):
        """Search filters datasets by owner username"""
        response = self.client.get(reverse("data:all") + "?search=testuser")
        self.assertContains(response, "Public Dataset")

    def test_all_datasets_sort_newest(self):
        """Sort by newest"""
        response = self.client.get(reverse("data:all") + "?sort=newest")
        self.assertEqual(response.status_code, 200)

    def test_all_datasets_sort_downloads(self):
        """Sort by downloads"""
        response = self.client.get(reverse("data:all") + "?sort=downloads")
        self.assertEqual(response.status_code, 200)

    def test_all_datasets_hides_private(self):
        """Private datasets not shown to strangers"""
        self.dataset.is_private = True
        self.dataset.save()
        self.client.login(username="otheruser", password="testpass123")
        response = self.client.get(reverse("data:all"))
        self.assertNotContains(response, "Public Dataset")

    # ===== PRIVATE ACCESS =====
    def test_search_users_requires_login(self):
        """Search users requires login"""
        response = self.client.get(reverse("data:search_users_global") + "?q=test")
        self.assertEqual(response.status_code, 302)

    def test_search_users_finds_users(self):
        """Search returns matching users"""
        self._login()
        response = self.client.get(reverse("data:search_users_global") + "?q=other")
        data = response.json()
        self.assertEqual(len(data["users"]), 1)
        self.assertEqual(data["users"][0]["username"], "otheruser")

    def test_search_users_excludes_self(self):
        """Search does not return the requesting user"""
        self._login()
        response = self.client.get(reverse("data:search_users_global") + "?q=testuser")
        data = response.json()
        self.assertEqual(len(data["users"]), 0)

    def test_add_allowed_user(self):
        """Owner can add user to private dataset"""
        self._login()
        self.dataset.is_private = True
        self.dataset.save()
        response = self.client.get(
            reverse(
                "data:add_user",
                kwargs={
                    "dataset_id": self.dataset.dataset_id,
                    "user_id": self.other.id,
                },
            )
        )
        self.assertJSONEqual(
            response.content, {"success": True, "username": "otheruser"}
        )
        self.assertTrue(self.dataset.allowed_users.filter(id=self.other.id).exists())

    def test_remove_allowed_user(self):
        """Owner can remove user from private dataset"""
        self._login()
        self.dataset.is_private = True
        self.dataset.save()
        self.dataset.allowed_users.add(self.other)
        response = self.client.get(
            reverse(
                "data:remove_user",
                kwargs={
                    "dataset_id": self.dataset.dataset_id,
                    "user_id": self.other.id,
                },
            )
        )
        self.assertJSONEqual(response.content, {"success": True})
        self.assertFalse(self.dataset.allowed_users.filter(id=self.other.id).exists())

    # ===== NEW: Shape API =====
    def test_dataset_shape_api_returns_shape(self):
        """Shape endpoint returns the resolved shape"""
        url = reverse("data:api_shape", args=[self.dataset.dataset_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("shape", data)
        self.assertNotEqual(data["shape"], "")

    def test_dataset_shape_api_requires_visibility(self):
        """Shape endpoint respects visibility"""
        self.dataset.is_private = True
        self.dataset.save()
        self.client.login(username="otheruser", password="testpass123")
        url = reverse("data:api_shape", args=[self.dataset.dataset_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    # ===== NEW: Info API =====
    def test_dataset_info_api(self):
        """Info endpoint returns filename and format"""
        url = reverse("data:api_info", args=[self.dataset.dataset_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("filename", data)
        self.assertIn("format", data)
        self.assertEqual(data["format"], "csv")

    # ===== NEW: Generate Dataset =====
    def test_generate_dataset_classification(self):
        """Generate a synthetic classification dataset"""
        self._login()
        url = reverse("data:generate")
        response = self.client.post(
            url,
            {
                "type": "classification",
                "name": "Synthetic Test",
                "n_samples": 20,
                "n_features": 2,
                "n_classes": 2,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIsNotNone(data["dataset_id"])
        self.assertIn("shape", data)
        dataset = Dataset.objects.get(dataset_id=data["dataset_id"])
        self.assertTrue(dataset.file.name.endswith(".csv"))

    def test_generate_dataset_invalid_type(self):
        """Generate fails with unknown type"""
        self._login()
        url = reverse("data:generate")
        response = self.client.post(url, {"type": "unknown"})
        self.assertEqual(response.status_code, 400)

    def test_generate_dataset_unauthenticated(self):
        """Generate requires login"""
        url = reverse("data:generate")
        response = self.client.post(url, {"type": "classification"})
        self.assertEqual(response.status_code, 302)

    # ===== NEW: Dataset List API (canvas picker) =====
    def test_dataset_list_api(self):
        """List API returns datasets for picker"""
        url = reverse("data:api_dataset_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("datasets", data)
        self.assertTrue(len(data["datasets"]) >= 1)
