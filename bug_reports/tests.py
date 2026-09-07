from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import BugReport

User = get_user_model()


class AdminCanvasSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.report = BugReport.objects.create(
            issue_type="other",
            title="xss",
            description="payload",
            graph_json={
                "nodes": [],
                "links": [],
                "evil": "</script><script>alert(1)</script>",
            },
        )

    def test_admin_canvas_requires_staff(self):
        url = reverse("bug_reports:admin_canvas", args=[self.report.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_admin_canvas_uses_json_script(self):
        self.client.login(username="staffuser", password="testpass123")
        url = reverse("bug_reports:admin_canvas", args=[self.report.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="sketchnet-template-data"')
        self.assertNotContains(response, "</script><script>alert(1)</script>")
        self.assertContains(response, "\\u003C/script\\u003E")
