from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()


class AccountTemplateRenderingTests(TestCase):
    """Test that all account templates render correctly"""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        EmailAddress.objects.create(
            user=self.user, email="test@example.com", verified=True, primary=True
        )

    def _login(self):
        """Log in the test user."""
        self.client.login(username="testuser", password="testpass123")

    # ---- Login ----
    def test_login_page_renders(self):
        """Verify login page renders."""
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/login.html")
        self.assertContains(response, "Sign in")

    # ---- Signup ----
    def test_signup_page_renders(self):
        """Verify signup page renders."""
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/signup.html")
        self.assertContains(response, "Create Account")

    # ---- Logout ----
    def test_logout_page_renders(self):
        """Verify logout page renders."""
        self._login()
        response = self.client.get(reverse("account_logout"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/logout.html")
        self.assertContains(response, "Are you sure")

    # ---- Password Change ----
    def test_password_change_page_renders(self):
        """Verify password change page renders."""
        self._login()
        response = self.client.get(reverse("account_change_password"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/password_change.html")
        self.assertContains(response, "Current Password")

    # ---- Password Reset ----
    def test_password_reset_page_renders(self):
        """Verify password reset page renders."""
        response = self.client.get(reverse("account_reset_password"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/password_reset.html")
        self.assertContains(response, "Reset Password")

    def test_password_reset_done_page_renders(self):
        """Verify password reset done page renders."""
        response = self.client.get(reverse("account_reset_password_done"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Check Your Email")

    def test_password_reset_from_key_done_page_renders(self):
        """Verify password reset from key done page renders."""
        response = self.client.get(reverse("account_reset_password_from_key_done"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Password Changed")

    # ---- Email Management ----
    def test_email_management_page_renders(self):
        """Verify email management page renders."""
        self._login()
        response = self.client.get(reverse("account_email"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/email.html")
        self.assertContains(response, "Email Addresses")

    def test_verification_sent_page_renders(self):
        """Verify verification sent page renders."""
        response = self.client.get(reverse("account_email_verification_sent"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verify Your Email")

    # ---- Account Inactive ----
    def test_account_inactive_page_renders(self):
        """Verify account inactive page renders."""
        response = self.client.get(reverse("account_inactive"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Account Inactive")

    # ---- Reauthenticate ----
    def test_reauthenticate_page_renders(self):
        """Verify reauthenticate page renders."""
        self._login()
        response = self.client.get(reverse("account_reauthenticate"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/reauthenticate.html")
        self.assertContains(response, "Confirm Your Password")
