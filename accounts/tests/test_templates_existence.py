from django.test import TestCase
from django.template.loader import get_template


class TemplateExistenceTests(TestCase):
    """Test that every account template file exists and compiles"""

    TEMPLATES = [
        "account/login.html",
        "account/signup.html",
        "account/signup_closed.html",
        "account/logout.html",
        "account/password_change.html",
        "account/password_reset.html",
        "account/password_reset_done.html",
        "account/password_reset_from_key.html",
        "account/password_reset_from_key_done.html",
        "account/email.html",
        "account/email_confirm.html",
        "account/verification_sent.html",
        "account/verified_email_required.html",
        "account/account_inactive.html",
        "account/reauthenticate.html",
    ]

    def test_all_templates_exist(self):
        """Every account template can be loaded without error"""
        for template_name in self.TEMPLATES:
            with self.subTest(template=template_name):
                try:
                    get_template(template_name)
                except Exception as e:
                    self.fail(f"Failed to load {template_name}: {e}")
