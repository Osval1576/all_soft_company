from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from tenancy.testing import create_org
from kb.models import Article

User = get_user_model()

BASE = "/api/admin/kb/articles/"


class KbAdminTests(TestCase):
    def setUp(self):
        self.org = create_org("KBORG")
        self.admin = User.objects.create_user("kb_admin", role="ADMIN",
                                               organization=self.org, is_active=True)
        self.agent = User.objects.create_user("kb_agent", role="AGENT",
                                               organization=self.org, is_active=True)
        self.customer = User.objects.create_user("kb_cust", role="CUSTOMER",
                                                  organization=self.org, is_active=True)
        self.c = APIClient()

    def _admin(self):
        self.c.force_authenticate(self.admin)
        return self.c

    # ---- create ----
    def test_admin_creates_article_sets_org_author_and_slug(self):
        r = self._admin().post(BASE, {"title": "Cómo reiniciar el panel",
                                      "body": "Andá a Ajustes y tocá Reiniciar."}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        art = Article.objects.get(id=r.data["id"])
        self.assertEqual(art.organization_id, self.org.id)
        self.assertEqual(art.author_id, self.admin.id)
        self.assertEqual(art.slug, "como-reiniciar-el-panel")
        self.assertFalse(art.is_published)  # borrador por defecto

    def test_slug_dedup_per_org(self):
        self._admin().post(BASE, {"title": "Guía"}, format="json")
        r = self._admin().post(BASE, {"title": "Guía"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        slugs = set(Article.objects.filter(organization=self.org).values_list("slug", flat=True))
        self.assertEqual(slugs, {"guia", "guia-2"})

    def test_client_cannot_set_org_or_author(self):
        other = create_org("KBEVIL")
        r = self._admin().post(BASE, {"title": "X", "organization": other.id,
                                      "author": self.customer.id}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        art = Article.objects.get(id=r.data["id"])
        self.assertEqual(art.organization_id, self.org.id)   # ignoró el campo
        self.assertEqual(art.author_id, self.admin.id)

    # ---- list scoping ----
    def test_list_only_own_org(self):
        Article.objects.create(organization=self.org, title="Mía")
        other = create_org("KBOTHER")
        Article.objects.create(organization=other, title="Ajena")
        r = self._admin().get(BASE)
        self.assertEqual(r.status_code, 200)
        titles = [a["title"] for a in r.data]
        self.assertEqual(titles, ["Mía"])

    def test_cross_org_article_is_404(self):
        other = create_org("KBOTHER")
        alien = Article.objects.create(organization=other, title="Ajena")
        r = self._admin().get(f"{BASE}{alien.id}/")
        self.assertEqual(r.status_code, 404)
        r = self._admin().patch(f"{BASE}{alien.id}/", {"title": "hack"}, format="json")
        self.assertEqual(r.status_code, 404)
        r = self._admin().delete(f"{BASE}{alien.id}/")
        self.assertEqual(r.status_code, 404)

    # ---- update / publish / delete ----
    def test_admin_updates_and_publishes(self):
        art = Article.objects.create(organization=self.org, title="Borrador")
        r = self._admin().patch(f"{BASE}{art.id}/", {"is_published": True,
                                                     "body": "listo"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        art.refresh_from_db()
        self.assertTrue(art.is_published)
        self.assertEqual(art.body, "listo")

    def test_admin_deletes(self):
        art = Article.objects.create(organization=self.org, title="Temporal")
        r = self._admin().delete(f"{BASE}{art.id}/")
        self.assertEqual(r.status_code, 204)
        self.assertFalse(Article.objects.filter(id=art.id).exists())

    # ---- role gating ----
    def test_agent_forbidden(self):
        self.c.force_authenticate(self.agent)
        self.assertEqual(self.c.get(BASE).status_code, 403)
        self.assertEqual(self.c.post(BASE, {"title": "x"}, format="json").status_code, 403)

    def test_customer_forbidden(self):
        self.c.force_authenticate(self.customer)
        self.assertEqual(self.c.get(BASE).status_code, 403)

    def test_anonymous_unauthorized(self):
        self.assertIn(self.c.get(BASE).status_code, (401, 403))
