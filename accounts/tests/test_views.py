from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()


class AuthViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        # Verify the email so login works without redirecting
        EmailAddress.objects.create(
            user=self.user, email="test@example.com", verified=True, primary=True
        )

    def test_login_page_loads(self):
        """Test login page returns 200"""
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/login.html")
        self.assertContains(response, "Sign in")

    def test_signup_page_loads(self):
        """Test signup page returns 200"""
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/signup.html")
        self.assertContains(response, "Create Account")

    def test_login_with_valid_credentials(self):
        """Test login with correct username and password"""
        response = self.client.post(
            reverse("account_login"),
            {
                "login": "testuser",
                "password": "testpass123",
            },
        )
        self.assertRedirects(response, "/")

    def test_login_with_email(self):
        """Test login using email instead of username"""
        response = self.client.post(
            reverse("account_login"),
            {
                "login": "test@example.com",
                "password": "testpass123",
            },
        )
        self.assertRedirects(response, "/")

    def test_login_with_invalid_credentials(self):
        """Test login with wrong password fails"""
        response = self.client.post(
            reverse("account_login"),
            {
                "login": "testuser",
                "password": "wrongpassword",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "The username and/or password you specified are not correct"
        )

    def test_signup_creates_user(self):
        """Test signup creates a new user"""
        response = self.client.post(
            reverse("account_signup"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )
        self.assertEqual(User.objects.count(), 2)  # setUp user + new one
        new_user = User.objects.get(username="newuser")
        self.assertEqual(new_user.email, "new@example.com")

    def test_profile_requires_login(self):
        """Test profile page redirects unauthenticated users"""
        response = self.client.get(reverse("profile"))
        self.assertRedirects(
            response, f"{reverse('account_login')}?next={reverse('profile')}"
        )

    def test_profile_accessible_when_logged_in(self):
        """Test profile page loads for authenticated users"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/profile.html")

    def test_logout(self):
        """Test logout redirects to home"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(reverse("account_logout"))
        self.assertRedirects(response, "/")
