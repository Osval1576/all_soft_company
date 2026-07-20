"""Suite adversarial de branding (H4): confirma que
- una org Free no puede editar branding ni exponerlo públicamente,
- un admin de org A no puede editar/leer el branding de org B,
- el endpoint público solo expone los 4 campos de branding (sin plan, agentes, etc.),
- un no-admin no puede editar branding.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from tenancy.testing import create_org
from tenancy.models import OrganizationBranding
from billing.models import Plan, Subscription

User = get_user_model()


class BrandingAdversarialTests(TestCase):
    def setUp(self):
        self.org_a = create_org("BXA", name="Org A")  # Business
        self.org_b = create_org("BXB", name="Org B")  # Business
        self.admin_a = User.objects.create_user("bxa_admin", email="a@x.com",
                                                 role="ADMIN", organization=self.org_a)
        self.c = APIClient(); self.c.force_authenticate(self.admin_a)

    def test_put_ignores_org_in_body_and_scopes_to_user_org(self):
        # aunque el body traiga otra org, el branding editado es el de la org del user
        self.c.put("/api/branding/", {"accent_color": "#111111",
                                      "organization": self.org_b.id}, format="json")
        self.assertTrue(OrganizationBranding.objects.filter(
            organization=self.org_a, accent_color="#111111").exists())
        self.assertFalse(OrganizationBranding.objects.filter(
            organization=self.org_b).exists())

    def test_admin_a_cannot_read_org_b_branding_via_admin_endpoint(self):
        OrganizationBranding.objects.create(organization=self.org_b, accent_color="#B0B0B0")
        r = self.c.get("/api/branding/")  # siempre devuelve el de la org del user (A)
        self.assertNotEqual(r.data.get("accent_color"), "#B0B0B0")

    def test_public_endpoint_leaks_only_branding_fields(self):
        OrganizationBranding.objects.create(organization=self.org_b, accent_color="#C0C0C0")
        r = APIClient().get(f"/api/public/branding/{self.org_b.slug}/")
        self.assertEqual(r.status_code, 200)
        forbidden = {"plan", "agent_count", "agent_limit", "status", "id",
                     "organization", "stripe_customer_id"}
        self.assertEqual(set(r.data.keys()) & forbidden, set())

    def test_free_org_branding_not_public(self):
        OrganizationBranding.objects.create(organization=self.org_b, accent_color="#D0D0D0")
        sub = self.org_b.subscription
        sub.plan = Plan.objects.get(key="free")
        sub.status = Subscription.Status.ACTIVE
        sub.save()
        r = APIClient().get(f"/api/public/branding/{self.org_b.slug}/")
        self.assertEqual(r.status_code, 404)

    def test_customer_cannot_edit_branding(self):
        cust = User.objects.create_user("bxa_c", email="c@x.com",
                                        role="CUSTOMER", organization=self.org_a)
        c = APIClient(); c.force_authenticate(cust)
        r = c.put("/api/branding/", {"accent_color": "#EEEEEE"}, format="json")
        self.assertEqual(r.status_code, 403)
