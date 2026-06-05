from django.test import SimpleTestCase
from django.urls import reverse, resolve
from sketchmod import views


class UrlsTest(SimpleTestCase):
    def test_canvas_url_resolves(self):
        """Verify canvas url resolves."""
        url = reverse("sketchmod:canvas")
        self.assertEqual(resolve(url).func, views.canvas)

    def test_export_api_url_resolves(self):
        """Verify export api url resolves."""
        url = reverse("sketchmod:export_api")
        self.assertEqual(resolve(url).func, views.export_api)

    def test_validate_api_url_resolves(self):
        """Verify validate api url resolves."""
        url = reverse("sketchmod:validate_api")
        self.assertEqual(resolve(url).func, views.validate_api)

    def test_highlight_path_api_url_resolves(self):
        """Verify highlight path api url resolves."""
        url = reverse("sketchmod:highlight_path_api")
        self.assertEqual(resolve(url).func, views.highlight_path_api)

    def test_dataset_columns_url_resolves(self):
        # This URL expects a dataset_id parameter
        """Verify dataset columns url resolves."""
        url = reverse("sketchmod:api_dataset_columns", args=["abc12345"])
        self.assertEqual(resolve(url).func, views.api_dataset_columns)
