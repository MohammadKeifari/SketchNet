from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from setting.models import UserSettings

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

    def test_default_collapse_left_sidebar(self):
        """New users default to left sidebar visible"""
        user = User.objects.create_user(
            username="leftuser",
            email="left@example.com",
            password="testpass123",
        )
        self.assertEqual(user.settings.collapse_left_sidebar, False)

    def test_default_collapse_right_sidebar(self):
        """New users default to right sidebar visible"""
        user = User.objects.create_user(
            username="rightuser",
            email="right@example.com",
            password="testpass123",
        )
        self.assertEqual(user.settings.collapse_right_sidebar, False)

    def test_settings_updated_at_changes_on_save(self):
        """updated_at should change when settings are modified"""
        user = User.objects.create_user(
            username="timeuser",
            email="time@example.com",
            password="testpass123",
        )
        original_updated = user.settings.updated_at
        # Ensure time passes between saves
        import time

        time.sleep(0.01)
        user.settings.theme = "dark"
        user.settings.save()
        self.assertGreater(user.settings.updated_at, original_updated)

    def test_signal_does_not_create_duplicate(self):
        """Saving user again should not create duplicate settings"""
        user = User.objects.create_user(
            username="dupuser",
            email="dup@example.com",
            password="testpass123",
        )
        count_before = UserSettings.objects.filter(user=user).count()
        user.save()
        count_after = UserSettings.objects.filter(user=user).count()
        self.assertEqual(count_before, count_after)
        self.assertEqual(count_before, 1)

    def test_all_theme_choices_valid(self):
        """All themes in THEME_CHOICES should be assignable"""
        user = User.objects.create_user(
            username="themeuser",
            email="theme@example.com",
            password="testpass123",
        )
        valid_themes = [
            "system",
            "light",
            "dark",
            "rose",
            "dark-rose",
            "forest",
            "forest-dark",
            "honey",
            "honey-dark",
        ]
        for theme in valid_themes:
            user.settings.theme = theme
            user.settings.full_clean()

    def test_verbose_name(self):
        """Meta verbose_name should be correct"""
        self.assertEqual(
            str(UserSettings._meta.verbose_name),
            "User Settings",
        )


class SettingsViewTests(TestCase):

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.settings_url = reverse("setting:settings")

    def test_settings_requires_login(self):
        """Verify settings requires login."""
        response = self.client.get(self.settings_url)
        self.assertEqual(response.status_code, 302)

    def test_settings_page_loads(self):
        """Verify settings page loads."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.settings_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "setting/settings.html")

    def test_settings_shows_all_themes(self):
        """Verify settings shows all themes."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.settings_url)
        self.assertContains(response, "System")
        self.assertContains(response, "Light")
        self.assertContains(response, "Dark")
        self.assertContains(response, "Rose")

    def test_change_theme_to_dark(self):
        """Verify change theme to dark."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(self.settings_url, {"theme": "dark"})
        self.assertRedirects(response, self.settings_url)
        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.theme, "dark")

    def test_change_theme_to_rose(self):
        """Verify change theme to rose."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(self.settings_url, {"theme": "rose"})
        self.assertRedirects(response, self.settings_url)
        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.theme, "rose")

    def test_invalid_theme_not_saved(self):
        """Verify invalid theme not saved."""
        self.client.login(username="testuser", password="testpass123")
        self.client.post(self.settings_url, {"theme": "invalid"})
        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.theme, "system")

    def test_settings_shows_current_theme(self):
        """Verify settings shows current theme."""
        self.user.settings.theme = "rose"
        self.user.settings.save()
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.settings_url)
        # Use DOTALL flag so . matches newlines
        self.assertRegex(
            response.content.decode(),
            r'value="rose"[^>]*checked',
        )

    def test_change_theme_to_forest(self):
        """Verify change theme to forest."""
        self.client.login(username="testuser", password="testpass123")
        self.client.post(self.settings_url, {"theme": "forest"})
        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.theme, "forest")

    def test_change_theme_to_honey_dark(self):
        """Verify change theme to honey dark."""
        self.client.login(username="testuser", password="testpass123")
        self.client.post(self.settings_url, {"theme": "honey-dark"})
        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.theme, "honey-dark")

    # === Sidebar collapse tests ===
    def test_collapse_left_sidebar_on(self):
        """Checkbox 'on' should set collapse_left_sidebar to True"""
        self.client.login(username="testuser", password="testpass123")
        self.client.post(
            self.settings_url,
            {
                "theme": self.user.settings.theme,
                "collapse_left_sidebar": "on",
            },
        )
        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.collapse_left_sidebar, True)

    def test_collapse_left_sidebar_off_when_not_sent(self):
        """collapse_left_sidebar should be False when checkbox absent"""
        self.user.settings.collapse_left_sidebar = True
        self.user.settings.save()
        self.client.login(username="testuser", password="testpass123")
        self.client.post(self.settings_url, {"theme": "light"})
        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.collapse_left_sidebar, False)

    def test_collapse_right_sidebar_on(self):
        """Checkbox 'on' should set collapse_right_sidebar to True"""
        self.client.login(username="testuser", password="testpass123")
        self.client.post(
            self.settings_url,
            {
                "theme": self.user.settings.theme,
                "collapse_right_sidebar": "on",
            },
        )
        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.collapse_right_sidebar, True)

    def test_collapse_right_sidebar_off_when_not_sent(self):
        """collapse_right_sidebar should be False when checkbox absent"""
        self.user.settings.collapse_right_sidebar = True
        self.user.settings.save()
        self.client.login(username="testuser", password="testpass123")
        self.client.post(self.settings_url, {"theme": "dark"})
        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.collapse_right_sidebar, False)

    def test_collapse_both_sidebars_on(self):
        """Both collapse settings can be set simultaneously"""
        self.client.login(username="testuser", password="testpass123")
        self.client.post(
            self.settings_url,
            {
                "theme": "rose",
                "collapse_left_sidebar": "on",
                "collapse_right_sidebar": "on",
            },
        )
        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.collapse_left_sidebar, True)
        self.assertEqual(self.user.settings.collapse_right_sidebar, True)

    def test_collapse_sidebar_preserves_theme(self):
        """Setting sidebar collapse should not change theme"""
        self.user.settings.theme = "forest"
        self.user.settings.save()
        self.client.login(username="testuser", password="testpass123")
        self.client.post(
            self.settings_url,
            {
                "theme": "forest",
                "collapse_left_sidebar": "on",
            },
        )
        self.user.settings.refresh_from_db()
        self.assertEqual(self.user.settings.theme, "forest")
        self.assertEqual(self.user.settings.collapse_left_sidebar, True)

    def test_collapse_settings_shown_in_page(self):
        """Settings page should contain the collapse toggle labels"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.settings_url)
        self.assertContains(response, "Collapse Left Toolbar")
        self.assertContains(response, "Collapse Right Sidebar")

    def _assert_checkbox_checked(self, content, checkbox_name, should_be_checked):
        """Helper to check if a checkbox is checked, handling multiline HTML."""
        # Pattern matches input with the given name, optionally followed by
        # any characters (including newlines) and then 'checked'
        pattern = rf'<input[^>]*name="{checkbox_name}"[^>]*checked'
        if should_be_checked:
            self.assertRegex(content, pattern, f"{checkbox_name} should be checked")
        else:
            self.assertNotRegex(
                content, pattern, f"{checkbox_name} should NOT be checked"
            )

    def test_collapse_left_checked_when_true(self):
        """Checkbox should be checked when collapse_left_sidebar is True"""
        self.user.settings.collapse_left_sidebar = True
        self.user.settings.save()
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.settings_url)
        self._assert_checkbox_checked(
            response.content.decode(), "collapse_left_sidebar", True
        )

    def test_collapse_right_checked_when_true(self):
        """Checkbox should be checked when collapse_right_sidebar is True"""
        self.user.settings.collapse_right_sidebar = True
        self.user.settings.save()
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.settings_url)
        self._assert_checkbox_checked(
            response.content.decode(), "collapse_right_sidebar", True
        )

    def test_collapse_left_unchecked_when_false(self):
        """Checkbox should NOT be checked when collapse_left_sidebar is False"""
        self.user.settings.collapse_left_sidebar = False
        self.user.settings.save()
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.settings_url)
        self._assert_checkbox_checked(
            response.content.decode(), "collapse_left_sidebar", False
        )

    def test_collapse_settings_persist_across_requests(self):
        """Collapse settings should persist after page reload"""
        self.client.login(username="testuser", password="testpass123")
        self.client.post(
            self.settings_url,
            {
                "theme": "dark",
                "collapse_left_sidebar": "on",
                "collapse_right_sidebar": "on",
            },
        )
        response = self.client.get(self.settings_url)
        content = response.content.decode()
        self._assert_checkbox_checked(content, "collapse_left_sidebar", True)
        self._assert_checkbox_checked(content, "collapse_right_sidebar", True)
