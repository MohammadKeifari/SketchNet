from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


class CustomUserModelTests(TestCase):

    def test_create_user(self):
        """Test creating a regular user works"""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpass123"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        """Test creating a superuser works"""
        admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_email_is_unique(self):
        """Test email field is unique"""
        User.objects.create_user(
            username="user1", email="same@example.com", password="pass123"
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username="user2", email="same@example.com", password="pass456"
            )

    def test_user_str_method(self):
        """Test string representation"""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.assertEqual(str(user), "testuser")
