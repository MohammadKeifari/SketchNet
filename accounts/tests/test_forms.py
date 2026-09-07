from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.forms import CustomSignupForm, ProfileForm

User = get_user_model()


class CustomSignupFormTests(TestCase):

    def test_form_valid_data(self):
        """Test form is valid with correct data"""
        form = CustomSignupForm(
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            }
        )
        self.assertTrue(form.is_valid())

    def test_form_empty_data(self):
        """Test form is invalid with empty data"""
        form = CustomSignupForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)
        self.assertIn("email", form.errors)
        self.assertIn("password1", form.errors)
        self.assertIn("password2", form.errors)

    def test_form_password_mismatch(self):
        """Test form rejects mismatched passwords"""
        form = CustomSignupForm(
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": "StrongPass123",
                "password2": "DifferentPass456",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_form_duplicate_username(self):
        """Test form rejects duplicate username"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        User.objects.create_user(
            username="existing", email="existing@example.com", password="pass123"
        )

        form = CustomSignupForm(
            data={
                "username": "existing",
                "email": "new@example.com",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_form_duplicate_email(self):
        """Test form rejects duplicate email"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        User.objects.create_user(
            username="existing", email="taken@example.com", password="pass123"
        )

        form = CustomSignupForm(
            data={
                "username": "newuser",
                "email": "taken@example.com",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_form_password_too_short(self):
        """Test form rejects short passwords"""
        form = CustomSignupForm(
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": "ab",
                "password2": "ab",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)

    def test_form_save_creates_user(self):
        """Test form.save() creates a user with hashed password"""
        form = CustomSignupForm(
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            }
        )
        self.assertTrue(form.is_valid())
        user = form.save()

        self.assertEqual(user.username, "newuser")
        self.assertEqual(user.email, "new@example.com")
        self.assertTrue(user.check_password("StrongPass123"))


class ProfileFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="formuser", email="form@example.com", password="pass12345"
        )

    def test_bio_saved(self):
        form = ProfileForm(
            data={"bio": "Hello from SketchNet."},
            instance=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, "Hello from SketchNet.")

