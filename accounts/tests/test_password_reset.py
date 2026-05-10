from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail

User = get_user_model()


class PasswordResetTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.reset_url = reverse("account_reset_password")

    def test_reset_page_loads(self):
        """Password reset page loads"""
        response = self.client.get(self.reset_url)
        self.assertEqual(response.status_code, 200)

    def test_reset_with_valid_email(self):
        """Sends email for valid email address"""
        response = self.client.post(
            self.reset_url,
            {
                "email": "test@example.com",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    def test_reset_with_invalid_email(self):
        """Does not reveal if email exists or not"""
        response = self.client.post(
            self.reset_url,
            {
                "email": "nonexistent@example.com",
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_reset_page_has_back_link(self):
        """Reset page links back to login"""
        response = self.client.get(self.reset_url)
        self.assertContains(response, reverse("account_login"))
