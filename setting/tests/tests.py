from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

import re

User = get_user_model()


class UserSettingsModelTests(TestCase):

    def test_settings_created_automatically(self):
        """UserSettings is created when user is created"""
        user = User.objects.create_user(
            username="newuser",
            email="new@example.com",
            password="testpass123",
        )
        self.assertTrue(hasattr(user, "settings"))
        self.assertEqual(user.settings.theme, "system")

    def test_settings_str(self):
        """String representation is correct"""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.assertEqual(str(user.settings), "Settings for testuser")

    def test_default_theme_is_system(self):
        """New users default to system theme"""
        user = User.objects.create_user(
            username="defaultuser",
            email="default@example.com",
            password="testpass123",
        )
        self.assertEqual(user.settings.theme, "system")


class SettingsViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.settings_url = reverse("setting:settings")

    def test_settings_requires_login(self):
        response = self.client.get(self.settings_url)
        self.assertEqual(response.status_code, 302)

    def test_settings_page_loads(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.settings_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "setting/settings.html")

    def test_settings_shows_all_themes(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.settings_url)
        self.assertContains(response, "System")
        self.assertContains(response, "Light")
        self.assertContains(response, "Dark")
        self.assertContains(response, "Rose")

    def test_change_theme_to_dark(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(self.settings_url, {"theme": "dark"})
        self.assertRedirects(response, self.settings_url)

        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.theme, "dark")

    def test_change_theme_to_rose(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(self.settings_url, {"theme": "rose"})
        self.assertRedirects(response, self.settings_url)

        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.theme, "rose")

    def test_invalid_theme_not_saved(self):
        self.client.login(username="testuser", password="testpass123")
        self.client.post(self.settings_url, {"theme": "invalid"})

        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.theme, "system")

    def test_settings_shows_current_theme(self):
        self.user.settings.theme = "rose"
        self.user.settings.save()

        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.settings_url)
        self.assertRegex(response.content.decode(), r'value="rose"[^>]*checked')

    def test_change_theme_to_forest(self):
        self.client.login(username="testuser", password="testpass123")
        self.client.post(self.settings_url, {"theme": "forest"})
        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.theme, "forest")

    def test_change_theme_to_honey_dark(self):
        self.client.login(username="testuser", password="testpass123")
        self.client.post(self.settings_url, {"theme": "honey-dark"})
        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.theme, "honey-dark")
