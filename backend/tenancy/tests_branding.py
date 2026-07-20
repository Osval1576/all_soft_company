import io

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from billing.models import Plan, Subscription
from tenancy.testing import create_org
from tenancy.models import OrganizationBranding

User = get_user_model()


def _png_bytes():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "#0038FF").save(buf, format="PNG")
    buf.seek(0)
    buf.name = "logo.png"
    return buf


class BrandingModelTests(TestCase):
    def test_effective_display_name_falls_back_to_org_name(self):
        org = create_org("BR1", name="Acme SA")
        b = OrganizationBranding.objects.create(organization=org)
        self.assertEqual(b.effective_display_name, "Acme SA")
        b.display_name = "Acme Support"
        self.assertEqual(b.effective_display_name, "Acme Support")

    def test_accent_color_rejects_non_hex(self):
        org = create_org("BR2")
        b = OrganizationBranding(organization=org, accent_color="red")
        with self.assertRaises(ValidationError):
            b.full_clean()

    def test_accent_color_accepts_hex(self):
        org = create_org("BR3")
        b = OrganizationBranding(organization=org, accent_color="#0038FF")
        b.full_clean()  # no debe levantar


class BrandingAdminApiTests(TestCase):
    def setUp(self):
        self.org = create_org("BRA")  # provision_test_org -> Business (plan pago)
        self.admin = User.objects.create_user("bra_admin", email="a@x.com",
                                               role="ADMIN", organization=self.org)
        self.c = APIClient(); self.c.force_authenticate(self.admin)

    def test_get_returns_defaults_without_persisting(self):
        r = self.c.get("/api/branding/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["accent_color"], "")
        self.assertEqual(r.data["effective_display_name"], self.org.name)
        from tenancy.models import OrganizationBranding
        self.assertEqual(OrganizationBranding.objects.count(), 0)

    def test_put_saves_branding(self):
        r = self.c.put("/api/branding/", {"display_name": "Acme Support",
                                          "accent_color": "#123456",
                                          "default_dark": True}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["accent_color"], "#123456")
        self.assertTrue(r.data["default_dark"])

    def test_put_rejects_bad_color(self):
        r = self.c.put("/api/branding/", {"accent_color": "red"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_put_bad_color_does_not_persist_row(self):
        r = self.c.put("/api/branding/", {"accent_color": "red"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(OrganizationBranding.objects.count(), 0)

    def test_put_accepts_png_logo(self):
        r = self.c.put("/api/branding/", {"logo": _png_bytes()}, format="multipart")
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(r.data["logo_url"])

    def test_put_rejects_non_allowed_format(self):
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (4, 4)).save(buf, format="GIF")
        buf.seek(0)
        buf.name = "logo.gif"
        r = self.c.put("/api/branding/", {"logo": buf}, format="multipart")
        self.assertEqual(r.status_code, 400)

    def test_free_plan_cannot_edit(self):
        sub = self.org.subscription
        sub.plan = Plan.objects.get(key="free")
        sub.status = Subscription.Status.ACTIVE
        sub.save()
        r = self.c.put("/api/branding/", {"accent_color": "#123456"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_non_admin_cannot_edit(self):
        agent = User.objects.create_user("bra_ag", email="ag@x.com",
                                         role="AGENT", organization=self.org)
        c = APIClient(); c.force_authenticate(agent)
        r = c.put("/api/branding/", {"accent_color": "#123456"}, format="json")
        self.assertEqual(r.status_code, 403)
