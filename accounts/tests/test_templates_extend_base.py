from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()


class TemplateExtendsBaseTests(TestCase):
    """Test that all pages extend base.html and include the navbar"""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        EmailAddress.objects.create(
            user=self.user,
            email="test@example.com",
            verified=True,
            primary=True
        )

    def _login(self):
        """Log in the test user."""
        self.client.login(username="testuser", password="testpass123")

    def _assert_extends_base_and_has_navbar(self, url_name, login_required=False):
        """Assert the template extends base and includes the navbar."""
        if login_required:
            self._login()
        response = self.client.get(reverse(url_name))
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "class=\"navbar\"")

    def test_login_extends_base(self):
        """Verify login extends base."""
        self._assert_extends_base_and_has_navbar("account_login")

    def test_signup_extends_base(self):
        """Verify signup extends base."""
        self._assert_extends_base_and_has_navbar("account_signup")

    def test_logout_extends_base(self):
        """Verify logout extends base."""
        self._assert_extends_base_and_has_navbar("account_logout", login_required=True)

    def test_password_change_extends_base(self):
        """Verify password change extends base."""
        self._assert_extends_base_and_has_navbar("account_change_password", login_required=True)

    def test_password_reset_extends_base(self):
        """Verify password reset extends base."""
        self._assert_extends_base_and_has_navbar("account_reset_password")

    def test_password_reset_done_extends_base(self):
        """Verify password reset done extends base."""
        self._assert_extends_base_and_has_navbar("account_reset_password_done")

    def test_email_extends_base(self):
        """Verify email extends base."""
        self._assert_extends_base_and_has_navbar("account_email", login_required=True)