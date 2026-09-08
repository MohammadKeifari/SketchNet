from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from models_library.models import SketchModel, ModelAccess

User = get_user_model()


class ModelViewTests(TestCase):

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username="owner", email="o@t.com", password="pass"
        )
        self.other = User.objects.create_user(
            username="other", email="x@t.com", password="pass"
        )
        self.model = SketchModel.objects.create(
            name="Test Model",
            description="A test model",
            graph_data={"nodes": [], "links": [], "ports": [], "nodeCounter": 0},
            owner=self.user,
        )

        # Verify setup
        self.assertEqual(User.objects.count(), 2)
        self.assertTrue(self.client.login(username="other", password="pass"))
        self.client.logout()

    def _login(self, user=None):
        """Log in the test user."""
        u = user or self.user
        logged_in = self.client.login(username=u.username, password="pass")
        self.assertTrue(logged_in, f"Login failed for {u.username}")

    # ===== DASHBOARD =====
    def test_dashboard_loads(self):
        """Verify dashboard loads."""
        response = self.client.get(reverse("models:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_public_models(self):
        """Verify dashboard shows public models."""
        response = self.client.get(reverse("models:dashboard"))
        self.assertContains(response, "Test Model")

    def test_dashboard_hides_private_from_anonymous(self):
        """Verify dashboard hides private from anonymous."""
        self.model.view_access = "private"
        self.model.save()
        response = self.client.get(reverse("models:dashboard"))
        self.assertNotContains(response, "Test Model")

    # ===== SAVE =====
    def test_save_requires_login(self):
        """Verify save requires login."""
        response = self.client.post(reverse("models:save"), {"name": "New"})
        self.assertEqual(response.status_code, 302)

    def test_save_creates_model(self):
        """Verify save creates model."""
        self._login()
        response = self.client.post(
            reverse("models:save"),
            {
                "name": "New Model",
                "description": "Desc",
                "view_access": "public",
                "fork_access": "private",
                "graph_data": '{"nodes":[],"links":[]}',
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("model_id", data)
        self.assertEqual(SketchModel.objects.count(), 2)

    def test_save_requires_name(self):
        """Verify save requires name."""
        self._login()
        response = self.client.post(
            reverse("models:save"),
            {
                "name": "",
                "graph_data": "{}",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_save_with_invalid_json(self):
        """Verify save with invalid json."""
        self._login()
        response = self.client.post(
            reverse("models:save"),
            {
                "name": "Bad JSON",
                "graph_data": "not json",
            },
        )
        self.assertEqual(response.status_code, 400)

    # ===== UPDATE =====
    def test_update_requires_login(self):
        """Verify update requires login."""
        response = self.client.post(
            reverse("models:update", kwargs={"model_id": self.model.model_id}),
            {"graph_data": "{}"},
        )
        self.assertEqual(response.status_code, 302)

    def test_update_requires_owner(self):
        """Verify update requires owner."""
        self._login(self.other)
        response = self.client.post(
            reverse("models:update", kwargs={"model_id": self.model.model_id}),
            {"graph_data": "{}"},
        )
        self.assertEqual(response.status_code, 403)

    def test_update_success(self):
        """Verify update success."""
        self._login()
        new_data = '{"nodes":[{"id":"n1","type":"neuron","x":100,"y":200}],"links":[]}'
        response = self.client.post(
            reverse("models:update", kwargs={"model_id": self.model.model_id}),
            {"graph_data": new_data},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.model.refresh_from_db()
        self.assertEqual(len(self.model.graph_data["nodes"]), 1)

    # ===== VIEW =====
    def test_view_loads(self):
        """Verify view loads."""
        response = self.client.get(
            reverse("models:view", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(response.status_code, 200)

    def test_view_increments_views(self):
        """Verify view increments views."""
        self._login()
        self.client.get(
            reverse("models:view", kwargs={"model_id": self.model.model_id})
        )
        self.model.refresh_from_db()
        self.assertEqual(self.model.views, 1)

    def test_view_private_denied(self):
        """Verify view private denied."""
        self.model.view_access = "private"
        self.model.save()
        self._login(self.other)
        response = self.client.get(
            reverse("models:view", kwargs={"model_id": self.model.model_id})
        )
        self.assertRedirects(response, reverse("models:dashboard"))

    # ===== EDIT =====
    def test_edit_requires_login(self):
        """Verify edit requires login."""
        response = self.client.get(
            reverse("models:edit", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(response.status_code, 302)

    def test_edit_requires_owner(self):
        """Verify edit requires owner."""
        self._login(self.other)
        response = self.client.get(
            reverse("models:edit", kwargs={"model_id": self.model.model_id})
        )
        self.assertRedirects(
            response, reverse("models:view", kwargs={"model_id": self.model.model_id})
        )

    def test_edit_loads_for_owner(self):
        """Verify edit loads for owner."""
        self._login()
        response = self.client.get(
            reverse("models:edit", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(response.status_code, 200)

    def test_edit_updates_model(self):
        """Verify edit updates model."""
        self._login()
        response = self.client.post(
            reverse("models:edit", kwargs={"model_id": self.model.model_id}),
            {
                "name": "Updated Name",
                "description": "New desc",
                "view_access": "private",
                "fork_access": "public",
            },
        )
        self.assertRedirects(
            response, reverse("models:view", kwargs={"model_id": self.model.model_id})
        )
        self.model.refresh_from_db()
        self.assertEqual(self.model.name, "Updated Name")
        self.assertEqual(self.model.view_access, "private")
        self.assertEqual(self.model.fork_access, "public")

    # ===== FORK =====
    def test_fork_requires_login(self):
        """Verify fork requires login."""
        response = self.client.post(
            reverse("models:fork", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(response.status_code, 302)

    def test_fork_creates_copy(self):
        """Verify fork creates copy."""
        logged_in = self.client.login(username="other", password="pass")
        self.assertTrue(logged_in, "Login failed")

        self.model.fork_access = "public"
        self.model.save()

        self.assertEqual(SketchModel.objects.count(), 1)  # Only original exists

        response = self.client.post(
            reverse("models:fork", kwargs={"model_id": self.model.model_id})
        )

        self.assertEqual(SketchModel.objects.count(), 2)  # Now 2 models

        # Get the forked model by finding the one NOT owned by self.user
        forked = SketchModel.objects.exclude(owner=self.user).first()

        self.assertIsNotNone(forked, "Forked model should exist")
        self.assertEqual(forked.owner, self.other)
        self.assertEqual(forked.forked_from, self.model)
        self.assertIn("(fork)", forked.name)
        self.assertRedirects(
            response, reverse("models:view", kwargs={"model_id": forked.model_id})
        )

    def test_fork_private_denied(self):
        """Verify fork private denied."""
        self._login(self.other)
        self.model.fork_access = "private"
        self.model.save()
        response = self.client.post(
            reverse("models:fork", kwargs={"model_id": self.model.model_id})
        )
        self.assertRedirects(
            response, reverse("models:view", kwargs={"model_id": self.model.model_id})
        )

    # ===== DELETE =====
    def test_delete_requires_login(self):
        """Verify delete requires login."""
        response = self.client.get(
            reverse("models:delete", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(response.status_code, 302)

    def test_delete_requires_owner(self):
        """Verify delete requires owner."""
        self._login(self.other)
        response = self.client.get(
            reverse("models:delete", kwargs={"model_id": self.model.model_id})
        )
        self.assertRedirects(response, reverse("models:dashboard"))

    def test_delete_page_loads(self):
        """Verify delete page loads."""
        self._login()
        response = self.client.get(
            reverse("models:delete", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(response.status_code, 200)

    def test_delete_removes_model(self):
        """Verify delete removes model."""
        self._login()
        response = self.client.post(
            reverse("models:delete", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(SketchModel.objects.count(), 0)
        self.assertRedirects(response, reverse("models:dashboard"))

    # ===== DELETE CONFIRMATION PAGE CONTAINS SESSION CLEAR SCRIPT =====
    def test_delete_confirmation_page_contains_session_clear_script(self):
        """The delete confirmation template should include code that clears
        sessionStorage if the deleted model matches the active canvas model."""
        self._login()
        response = self.client.get(
            reverse("models:delete", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "sketchmod-active-model-id")
        self.assertContains(response, "sessionStorage.removeItem")
        self.assertContains(response, "sketchmod-graph")

    # ===== DOWNLOAD =====
    def test_download_returns_json(self):
        """Verify download returns json."""
        response = self.client.get(
            reverse("models:download", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_download_private_denied(self):
        """Verify download private denied."""
        self.model.view_access = "private"
        self.model.save()
        self._login(self.other)
        response = self.client.get(
            reverse("models:download", kwargs={"model_id": self.model.model_id})
        )
        self.assertRedirects(response, reverse("models:dashboard"))

    # ===== LIKE =====
    def test_like_requires_login(self):
        """Verify like requires login."""
        response = self.client.post(
            reverse("models:like", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(response.status_code, 302)

    def test_like_rejects_get(self):
        """Like cannot be toggled with a GET request."""
        self._login()
        response = self.client.get(
            reverse("models:like", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(response.status_code, 405)

    def test_like_toggles_on(self):
        """Verify like toggles on."""
        self._login()
        response = self.client.post(
            reverse("models:like", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["liked"])
        self.assertEqual(response.json()["likes_count"], 1)

    def test_like_toggles_off(self):
        """Verify like toggles off."""
        self._login()
        self.model.liked_by.add(self.user)
        response = self.client.post(
            reverse("models:like", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["liked"])
        self.assertEqual(response.json()["likes_count"], 0)

    # ===== API DATA =====
    def test_api_data_returns_graph(self):
        """Verify api data returns graph."""
        response = self.client.get(
            reverse("models:api_data", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("nodes", data)
        self.assertIn("links", data)
        self.assertEqual(data["name"], "Test Model")

    def test_api_data_private_denied(self):
        """Verify api data private denied."""
        self.model.view_access = "private"
        self.model.save()
        self._login(self.other)
        response = self.client.get(
            reverse("models:api_data", kwargs={"model_id": self.model.model_id})
        )
        self.assertEqual(response.status_code, 403)

    # ===== API LIST =====
    def test_api_list_returns_public(self):
        """Verify api list returns public."""
        response = self.client.get(reverse("models:api_list"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)

    def test_api_list_search(self):
        """Verify api list search."""
        SketchModel.objects.create(name="UniqueXYZ", graph_data={}, owner=self.user)
        response = self.client.get(reverse("models:api_list") + "?search=UniqueXYZ")
        data = response.json()
        self.assertEqual(data["count"], 1)

    def test_api_list_section_mine(self):
        """Verify api list section mine."""
        self._login()
        response = self.client.get(reverse("models:api_list") + "?section=mine")
        data = response.json()
        self.assertEqual(data["count"], 1)

    # ===== EXPANDED VIEWS =====
    def test_my_models_requires_login(self):
        """Verify my models requires login."""
        response = self.client.get(reverse("models:my"))
        self.assertEqual(response.status_code, 302)

    def test_my_models_loads(self):
        """Verify my models loads."""
        self._login()
        response = self.client.get(reverse("models:my"))
        self.assertEqual(response.status_code, 200)

    def test_liked_models_requires_login(self):
        """Verify liked models requires login."""
        response = self.client.get(reverse("models:liked"))
        self.assertEqual(response.status_code, 302)

    def test_liked_models_loads(self):
        """Verify liked models loads."""
        self._login()
        response = self.client.get(reverse("models:liked"))
        self.assertEqual(response.status_code, 200)

    def test_all_models_loads(self):
        """Verify all models loads."""
        response = self.client.get(reverse("models:all"))
        self.assertEqual(response.status_code, 200)

    def test_all_models_search(self):
        """Verify all models search."""
        response = self.client.get(reverse("models:all") + "?search=nonexistent")
        self.assertContains(response, "No models found")

    def test_view_page_shows_view_graph_for_anonymous(self):
        """Public model detail shows read-only View graph link."""
        response = self.client.get(
            reverse("models:view", args=[self.model.model_id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "View graph")
        self.assertContains(response, f"load={self.model.model_id}&readonly=1")

    def test_remove_access_rejects_get(self):
        """GET must not revoke access (CSRF-safe mutating routes are POST-only)."""
        self._login()
        ModelAccess.objects.create(user=self.other, model=self.model, can_view=True)
        url = reverse(
            "models:remove_access",
            kwargs={"model_id": self.model.model_id, "user_id": self.other.id},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)
        self.assertTrue(
            ModelAccess.objects.filter(model=self.model, user=self.other).exists()
        )

    def test_remove_access_post(self):
        """Owner can revoke access with POST."""
        self._login()
        ModelAccess.objects.create(user=self.other, model=self.model, can_view=True)
        url = reverse(
            "models:remove_access",
            kwargs={"model_id": self.model.model_id, "user_id": self.other.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"success": True})
        self.assertFalse(
            ModelAccess.objects.filter(model=self.model, user=self.other).exists()
        )

    def test_remove_access_requires_owner(self):
        """Non-owners cannot revoke access."""
        self._login(self.other)
        url = reverse(
            "models:remove_access",
            kwargs={"model_id": self.model.model_id, "user_id": self.user.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
