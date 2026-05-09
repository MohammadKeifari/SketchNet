from django.test import TestCase
from django.urls import reverse, resolve


class AccountURLTests(TestCase):

    def test_login_url_resolves(self):
        """Test login URL name resolves"""
        url = reverse("account_login")
        self.assertEqual(url, "/accounts/login/")

    def test_signup_url_resolves(self):
        """Test signup URL name resolves"""
        url = reverse("account_signup")
        self.assertEqual(url, "/accounts/signup/")

    def test_logout_url_resolves(self):
        """Test logout URL name resolves"""
        url = reverse("account_logout")
        self.assertEqual(url, "/accounts/logout/")

    def test_profile_url_resolves(self):
        """Test profile URL name resolves"""
        url = reverse("profile")
        self.assertEqual(url, "/accounts/profile/")


class HomeURLTests(TestCase):

    def test_home_url_resolves(self):
        """Test home URL returns 200"""
        url = reverse("home")
        self.assertEqual(url, "/")

    def test_home_page_loads(self):
        """Test home page loads with navbar"""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")
        self.assertContains(response, "SketchMod")
