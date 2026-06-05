from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()


class ProfileViewTests(TestCase):

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        EmailAddress.objects.create(
            user=self.user, email="test@example.com", verified=True, primary=True
        )
        self.profile_url = "/accounts/profile/"

    def test_profile_requires_login(self):
        """Unauthenticated users are redirected"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)

    def test_profile_loads_when_logged_in(self):
        """Authenticated users see profile page"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)

    def test_profile_shows_username(self):
        """Profile displays the user's username"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.profile_url)
        self.assertContains(response, "testuser")

    def test_profile_shows_email(self):
        """Profile displays the user's email"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.profile_url)
        self.assertContains(response, "test@example.com")

    def test_profile_has_change_password_link(self):
        """Profile has link to change password"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.profile_url)
        self.assertContains(response, reverse("account_change_password"))

    def test_profile_has_manage_email_link(self):
        """Profile has link to manage email"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.profile_url)
        self.assertContains(response, reverse("account_email"))

    def test_profile_has_signout_link(self):
        """Profile has sign out link"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.profile_url)
        self.assertContains(response, reverse("account_logout"))

    def test_profile_uses_correct_template(self):
        """Profile uses the right template"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.profile_url)
        self.assertTemplateUsed(response, "account/profile.html")
