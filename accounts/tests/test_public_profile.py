
import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class PublicProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="publicuser",
            email="public@example.com",
            password="pass",
        )
        self.user.settings.public_profile = True
        self.user.settings.save()

    def test_public_profile_visible(self):
        response = self.client.get(
            reverse("public_profile", args=["publicuser"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "publicuser")

    def test_private_profile_hidden(self):
        self.user.settings.public_profile = False
        self.user.settings.save()
        response = self.client.get(
            reverse("public_profile", args=["publicuser"])
        )
        self.assertEqual(response.status_code, 404)

    def test_owner_sees_private_profile(self):
        self.user.settings.public_profile = False
        self.user.settings.save()
        self.client.login(username="publicuser", password="pass")
        response = self.client.get(
            reverse("public_profile", args=["publicuser"])
        )
        self.assertEqual(response.status_code, 200)
