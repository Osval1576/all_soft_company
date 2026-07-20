from django.core.exceptions import ValidationError
from django.test import TestCase

from tenancy.testing import create_org
from tenancy.models import OrganizationBranding


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
