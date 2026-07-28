from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from tenancy.testing import create_org
from kb.models import Article, ArticleSuggestion
from tickets_t.models import Ticket

User = get_user_model()

BASE = "/api/admin/kb/articles/"
DEFLECT = "/api/kb/deflect/"
SUGG = "/api/admin/kb/suggestions/"
KB_ARTICLE = "Restablecer contraseña\n\nAndá a Ajustes y tocá Restablecer."


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


class KbSearchTests(TestCase):
    """Retrieval por relevancia sobre la KB publicada de la org."""

    def setUp(self):
        self.org = create_org("KBSRCH")
        Article.objects.create(organization=self.org, title="Restablecer contraseña",
                               body="Andá a Ajustes y tocá Restablecer.", is_published=True)
        Article.objects.create(organization=self.org, title="Configurar el panel",
                               body="El panel se configura en preferencias.", is_published=True)
        Article.objects.create(organization=self.org, title="Borrador oculto",
                               body="contraseña secreta interna", is_published=False)

    def test_finds_published_by_relevance(self):
        from kb.search import search_articles
        res = search_articles(self.org, "cómo restablezco mi contraseña")
        self.assertTrue(res)
        self.assertEqual(res[0].title, "Restablecer contraseña")

    def test_excludes_unpublished(self):
        from kb.search import search_articles
        res = search_articles(self.org, "contraseña secreta interna")
        self.assertNotIn("Borrador oculto", [a.title for a in res])

    def test_scoped_to_org(self):
        from kb.search import search_articles
        other = create_org("KBSRCH2")
        Article.objects.create(organization=other, title="Restablecer contraseña",
                               body="ajeno", is_published=True)
        res = search_articles(self.org, "restablecer contraseña")
        for a in res:
            self.assertEqual(a.organization_id, self.org.id)

    def test_no_match_is_empty(self):
        from kb.search import search_articles
        self.assertEqual(search_articles(self.org, "zxqw nonexistent topic"), [])


class KbDeflectTests(TestCase):
    """Agente de deflección (RAG) sobre la KB publicada de la org (3B)."""

    def setUp(self):
        self.org = create_org("KBDEF")  # Business por defecto
        self.customer = User.objects.create_user("def_cust", role="CUSTOMER",
                                                  organization=self.org, is_active=True)
        Article.objects.create(
            organization=self.org, title="Restablecer contraseña",
            body="Andá a Ajustes → Seguridad y tocá Restablecer.", is_published=True)
        self.c = APIClient()
        self.c.force_authenticate(self.customer)

    @patch("ai.gateway.generate", return_value="Andá a Ajustes → Seguridad y restablecé.")
    def test_resolved_with_sources(self, mock_gen):
        r = self.c.post(DEFLECT, {"query": "cómo restablezco mi contraseña"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.data["available"])
        self.assertTrue(r.data["resolved"])
        self.assertTrue(r.data["answer"])
        self.assertEqual(r.data["sources"][0]["title"], "Restablecer contraseña")
        # el prompt lleva el cuerpo del artículo como contexto
        prompt = mock_gen.call_args.kwargs["user_prompt"]
        self.assertIn("Ajustes → Seguridad", prompt)

    @patch("ai.gateway.generate", return_value="NO_SE")
    def test_unresolved_when_model_says_no(self, mock_gen):
        r = self.c.post(DEFLECT, {"query": "cómo restablezco mi contraseña"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["resolved"])
        self.assertIsNone(r.data["answer"])

    @patch("ai.gateway.generate")
    def test_no_articles_skips_ai(self, mock_gen):
        r = self.c.post(DEFLECT, {"query": "zxqw nonexistent topic"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["resolved"])
        mock_gen.assert_not_called()

    @patch("ai.gateway.generate", return_value="algo")
    def test_free_plan_unavailable(self, mock_gen):
        from billing.models import Plan
        from billing.testing import seed_plans
        seed_plans()
        self.org.subscription.plan = Plan.objects.get(key="free")
        self.org.subscription.save()
        r = self.c.post(DEFLECT, {"query": "restablecer contraseña"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["available"])
        self.assertFalse(r.data["resolved"])
        mock_gen.assert_not_called()

    @patch("ai.gateway.generate", side_effect=RuntimeError("boom"))
    def test_ai_failure_is_graceful(self, mock_gen):
        r = self.c.post(DEFLECT, {"query": "restablecer contraseña"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["resolved"])

    def test_requires_query(self):
        r = self.c.post(DEFLECT, {}, format="json")
        self.assertEqual(r.status_code, 400)


class KbSuggestionTests(TestCase):
    """Fase 5.2 — KB auto-alimentada: sugerencia al resolver + cola admin."""

    def setUp(self):
        self.org = create_org("KBSUG")  # Business
        self.admin = User.objects.create_user("sug_admin", role="ADMIN",
                                               organization=self.org, is_active=True)
        self.agent = User.objects.create_user("sug_agent", role="AGENT",
                                               organization=self.org, is_active=True)
        self.customer = User.objects.create_user("sug_cust", role="CUSTOMER",
                                                  organization=self.org, is_active=True)
        self.ticket = Ticket.objects.create(
            reference="SUG-1", titulo="No me llega el mail de verificación",
            descripcion="No recibo el correo de verificación al registrarme.",
            creado_por=self.customer, asignado_a=self.agent,
            organization=self.org, estado="OPEN")

    # ---- generación / orquestador ----
    @patch("ai.gateway.generate", return_value=KB_ARTICLE)
    def test_maybe_suggest_creates_pending(self, _g):
        from kb.suggestions import maybe_suggest_from_ticket
        s = maybe_suggest_from_ticket(self.ticket)
        self.assertIsNotNone(s)
        self.assertEqual(s.status, "pending")
        self.assertEqual(s.title, "Restablecer contraseña")
        self.assertIn("Andá a Ajustes", s.body)
        self.assertEqual(s.source_ticket_id, self.ticket.id)

    @patch("ai.gateway.generate", return_value=KB_ARTICLE)
    def test_no_duplicate_pending(self, _g):
        from kb.suggestions import maybe_suggest_from_ticket
        maybe_suggest_from_ticket(self.ticket)
        maybe_suggest_from_ticket(self.ticket)
        self.assertEqual(ArticleSuggestion.objects.filter(source_ticket=self.ticket).count(), 1)

    @patch("ai.gateway.generate", return_value=KB_ARTICLE)
    def test_free_plan_no_suggestion(self, _g):
        from billing.models import Plan
        from billing.testing import seed_plans
        seed_plans()
        self.org.subscription.plan = Plan.objects.get(key="free")
        self.org.subscription.save()
        from kb.suggestions import maybe_suggest_from_ticket
        self.assertIsNone(maybe_suggest_from_ticket(self.ticket))

    @patch("ai.gateway.generate", side_effect=RuntimeError("boom"))
    def test_ai_failure_is_silent(self, _g):
        from kb.suggestions import maybe_suggest_from_ticket
        self.assertIsNone(maybe_suggest_from_ticket(self.ticket))

    # ---- hook al resolver el ticket (integración vía API) ----
    @patch("ai.gateway.generate", return_value=KB_ARTICLE)
    def test_resolving_ticket_creates_suggestion(self, _g):
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.patch(f"/api/tickets_t/{self.ticket.id}/", {"estado": "RESOLVED"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(ArticleSuggestion.objects.filter(
            source_ticket=self.ticket, status="pending").exists())

    # ---- cola admin ----
    def _sugg(self):
        return ArticleSuggestion.objects.create(
            organization=self.org, title="Cómo verificar tu correo",
            body="Revisá spam y reenviá el correo desde tu perfil.",
            source_ticket=self.ticket)

    def test_admin_lists_pending_scoped(self):
        self._sugg()
        other = create_org("KBSUG2")
        ArticleSuggestion.objects.create(organization=other, title="ajena", body="x")
        c = APIClient(); c.force_authenticate(self.admin)
        r = c.get(SUGG)
        self.assertEqual(r.status_code, 200)
        self.assertEqual([s["title"] for s in r.data], ["Cómo verificar tu correo"])

    def test_accept_creates_published_article(self):
        s = self._sugg()
        c = APIClient(); c.force_authenticate(self.admin)
        r = c.post(f"{SUGG}{s.id}/accept/")
        self.assertEqual(r.status_code, 201, r.content)
        art = Article.objects.get(id=r.data["article_id"])
        self.assertTrue(art.is_published)
        self.assertEqual(art.organization_id, self.org.id)
        s.refresh_from_db()
        self.assertEqual(s.status, "accepted")

    def test_dismiss(self):
        s = self._sugg()
        c = APIClient(); c.force_authenticate(self.admin)
        r = c.post(f"{SUGG}{s.id}/dismiss/")
        self.assertEqual(r.status_code, 200)
        s.refresh_from_db()
        self.assertEqual(s.status, "dismissed")

    def test_agent_forbidden(self):
        c = APIClient(); c.force_authenticate(self.agent)
        self.assertEqual(c.get(SUGG).status_code, 403)
