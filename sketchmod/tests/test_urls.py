from django.test import SimpleTestCase
from django.urls import reverse, resolve
from sketchmod import views


class SketchModURLTests(SimpleTestCase):

    def test_canvas_url_resolves(self):
        url = reverse("sketchmod:canvas")
        self.assertEqual(url, "/sketchmod/")
        resolver = resolve(url)
        self.assertIsNotNone(resolver.func)

    def test_export_api_url_resolves(self):
        url = reverse("sketchmod:export_api")
        self.assertEqual(url, "/sketchmod/api/export/")
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.export_api)

    def test_validate_api_url_resolves(self):
        url = reverse("sketchmod:validate_api")
        self.assertEqual(url, "/sketchmod/api/validate/")
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.validate_api)

    def test_canvas_url_name(self):
        """Canvas URL should be accessible by name."""
        url = reverse("sketchmod:canvas")
        self.assertIsNotNone(url)

    def test_export_api_url_name(self):
        """Export API URL should be accessible by name."""
        url = reverse("sketchmod:export_api")
        self.assertIsNotNone(url)

    def test_validate_api_url_name(self):
        """Validate API URL should be accessible by name."""
        url = reverse("sketchmod:validate_api")
        self.assertIsNotNone(url)
