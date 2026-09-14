from pathlib import Path

from django.test import SimpleTestCase, TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from config.whitenoise_headers import add_static_headers
from sketchmod.views import _canvas_asset_version

User = get_user_model()

CANVAS_JS = (
    Path(__file__).resolve().parents[1] / "static" / "sketchmod" / "js" / "canvas.js"
)


class CanvasStaticIntegrityTests(SimpleTestCase):
    def test_canvas_js_is_complete(self):
        """A truncated production copy of canvas.js never builds the left palette."""
        text = CANVAS_JS.read_text(encoding="utf-8")
        self.assertGreater(len(text), 340_000)
        self.assertIn("function handleSave", text)
        self.assertIn("_scheduleFit", text)
        self.assertIn("window.SketchMod = SketchMod", text)
        self.assertTrue(text.rstrip().endswith("SketchMod;"))

    def test_js_headers_include_no_transform(self):
        headers = {"Cache-Control": "max-age=60, public"}
        add_static_headers(
            headers,
            "/static/sketchmod/js/canvas.js",
            "/static/sketchmod/js/canvas.js",
        )
        self.assertIn("no-transform", headers["Cache-Control"])
        self.assertIn("max-age=60", headers["Cache-Control"])

    def test_non_js_headers_unchanged(self):
        headers = {"Cache-Control": "max-age=60, public"}
        add_static_headers(
            headers, "/static/images/logo.svg", "/static/images/logo.svg"
        )
        self.assertEqual(headers["Cache-Control"], "max-age=60, public")


class CanvasAssetVersionTests(TestCase):
    def setUp(self):
        User.objects.create_user(
            username="testuser", password="testpass123", email="t@example.com"
        )

    def test_canvas_scripts_are_cache_busted(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("sketchmod:canvas"))
        version = _canvas_asset_version()
        self.assertContains(response, f"sketchmod/js/canvas.js?v={version}")
        self.assertContains(response, 'data-cfasync="false"')
        self.assertContains(response, "SketchMod failed to load")
