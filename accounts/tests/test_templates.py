from django.test import TestCase
from django.urls import reverse


class TemplateStructureTests(TestCase):

    def test_home_extends_base(self):
        """Test home.html extends base.html"""
        response = self.client.get(reverse("home"))
        self.assertTemplateUsed(response, "base.html")
        self.assertTemplateUsed(response, "home.html")

    def test_navbar_included_in_base(self):
        """Test navbar is included in base template"""
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'class="navbar"')
        self.assertContains(response, "Home")
        self.assertContains(response, "Data")
        self.assertContains(response, "Models")
        self.assertContains(response, "SketchMod")
        self.assertContains(response, "Account")
        self.assertContains(response, "Settings")

    def test_current_page_attribute(self):
        """Test body has data-current-page attribute"""

        response = self.client.get(reverse("home"))
        self.assertRegex(response.content.decode(), r'data-current-page="\s*home\s*"')

    def test_login_template_extends_base(self):
        """Test login page extends base.html"""
        response = self.client.get(reverse("account_login"))
        self.assertTemplateUsed(response, "base.html")
        self.assertTemplateUsed(response, "account/login.html")

    def test_signup_template_extends_base(self):
        """Test signup page extends base.html"""
        response = self.client.get(reverse("account_signup"))
        self.assertTemplateUsed(response, "base.html")
        self.assertTemplateUsed(response, "account/signup.html")
