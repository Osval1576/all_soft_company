"""Suite adversarial de aislamiento cross-tenant.

Fixture: dos organizaciones completas (admin+agent+customer+ticket con
SLA/CSAT cada una). Cada test ataca recursos de B autenticado como A.
Regla: cross-tenant con ID directo -> 404 (nunca 200 ni 403 que revele existencia).
"""
import base64

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from csat.models import CSATResponse
from tenancy.testing import create_org
from tickets_t.models import Ticket, TicketMessage

User = get_user_model()


def _png_bytes():
    # PNG 1x1 minimo valido (mismo fixture que tickets_t/tests.py)
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"
    )


def _png_file():
    return SimpleUploadedFile("foto.png", _png_bytes(), content_type="image/png")


class OrgFixture:
    """Organizacion completa: admin/agent/customer + 1 ticket resuelto con
    SLA (auto-provisionado por el signal), CSAT y un adjunto."""

    def __init__(self, slug):
        self.org = create_org(slug)
        low = slug.lower()
        self.admin = User.objects.create_user(f"{low}_adm", password="x", role="ADMIN", organization=self.org)
        self.agent = User.objects.create_user(f"{low}_agt", password="x", role="AGENT", organization=self.org)
        self.customer = User.objects.create_user(f"{low}_cus", password="x", role="CUSTOMER", organization=self.org)
        self.ticket = Ticket.objects.create(
            reference=f"{slug}-20260101-000001", titulo="Ticket", descripcion="d",
            prioridad="MEDIUM", estado="RESOLVED",
            creado_por=self.customer, asignado_a=self.agent, organization=self.org,
        )
        self.message = TicketMessage.objects.create(
            ticket=self.ticket, sender=self.customer, content="hola",
        )
        self.attachment_message = TicketMessage.objects.create(
            ticket=self.ticket, sender=self.customer, content="",
            attachment=_png_file(), attachment_name="foto.png",
            attachment_size=len(_png_bytes()), attachment_content_type="image/png",
        )
        self.csat = CSATResponse.objects.create(ticket=self.ticket, score=5, comment="bien")


class AdversarialIsolationTests(TestCase):
    def setUp(self):
        self.a = OrgFixture("ADA")
        self.b = OrgFixture("ADB")

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    # 1. detalle de ticket cross-org, por los 3 roles de A
    def test_detalle_ticket_cross_404(self):
        for user in (self.a.admin, self.a.agent, self.a.customer):
            r = self._client(user).get(f"/api/tickets_t/{self.b.ticket.id}/")
            self.assertEqual(r.status_code, 404, f"{user.username} debio recibir 404")

    # 2. la lista de tickets nunca incluye tickets de la otra org, por los 3 roles
    def test_lista_tickets_no_incluye_otra_org(self):
        for user in (self.a.admin, self.a.agent, self.a.customer):
            r = self._client(user).get("/api/tickets_t/")
            self.assertEqual(r.status_code, 200)
            ids = [t["id"] for t in r.json()]
            self.assertNotIn(self.b.ticket.id, ids, f"{user.username} vio el ticket de B")

    # 3. mensajes y eventos de un ticket cross-org -> 404
    def test_mensajes_y_eventos_cross_404(self):
        r = self._client(self.a.admin).get(f"/api/tickets_t/{self.b.ticket.id}/messages/")
        self.assertEqual(r.status_code, 404)
        r2 = self._client(self.a.admin).get(f"/api/tickets_t/{self.b.ticket.id}/events/")
        self.assertEqual(r2.status_code, 404)

    # 4. descarga de adjunto cross-org -> 404 (nunca revela si el adjunto existe)
    def test_download_adjunto_cross_404(self):
        url = f"/api/tickets_t/{self.b.ticket.id}/attachments/{self.b.attachment_message.id}/download/"
        r = self._client(self.a.customer).get(url)
        self.assertEqual(r.status_code, 404)

    # 5. subida de adjunto a un ticket cross-org -> 404, y no crea el mensaje
    def test_upload_adjunto_cross_404(self):
        before = TicketMessage.objects.filter(ticket=self.b.ticket).count()
        url = f"/api/tickets_t/{self.b.ticket.id}/attachments/"
        r = self._client(self.a.customer).post(url, {"file": _png_file()}, format="multipart")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(TicketMessage.objects.filter(ticket=self.b.ticket).count(), before)

    # 6. CSAT: customer de A intenta calificar un ticket de B -> 404, nunca 403
    #    (403 revelaria que el ticket existe pero no es del calificador)
    def test_csat_cross_404(self):
        r = self._client(self.a.customer).post(
            f"/api/csat/{self.b.ticket.id}/", {"score": 3}, format="json")
        self.assertEqual(r.status_code, 404)
        # la calificacion original de B sigue intacta
        self.b.csat.refresh_from_db()
        self.assertEqual(self.b.csat.score, 5)

    # 7. pool de A no lista tickets de B; take sobre un ticket de B -> 404
    def test_pool_take_cross(self):
        unassigned_b = Ticket.objects.create(
            reference=f"{self.b.org.slug}-20260101-000002", titulo="pool", descripcion="d",
            prioridad="MEDIUM", estado="OPEN", creado_por=self.b.customer, organization=self.b.org,
        )
        r = self._client(self.a.agent).get("/api/tickets_t/pool/")
        self.assertEqual(r.status_code, 200)
        ids = [t["id"] for t in r.json()]
        self.assertNotIn(unassigned_b.id, ids)

        r2 = self._client(self.a.agent).post(f"/api/tickets_t/{unassigned_b.id}/take/")
        self.assertEqual(r2.status_code, 404)
        unassigned_b.refresh_from_db()
        self.assertIsNone(unassigned_b.asignado_a_id)

    # 8. metricas de admin: totales exactos, sin mezclar tickets de otra org
    def test_metricas_no_mezclan(self):
        Ticket.objects.create(
            reference=f"{self.a.org.slug}-20260101-000002", titulo="t2", descripcion="d",
            prioridad="MEDIUM", estado="OPEN", creado_por=self.a.customer, organization=self.a.org,
        )
        r = self._client(self.a.admin).get("/api/metrics/admin/")
        self.assertEqual(r.status_code, 200)
        totals = r.json()["totals"]
        self.assertEqual(totals["total"], 2)
        self.assertEqual(totals["resolved"], 1)
        self.assertEqual(totals["open"], 1)

    # 9. admin de A no lista ni puede editar usuarios de B (ID directo) -> 404
    def test_usuarios_cross(self):
        r = self._client(self.a.admin).get("/api/users/users/")
        self.assertEqual(r.status_code, 200)
        ids = [u["id"] for u in r.json()]
        self.assertNotIn(self.b.customer.id, ids)
        self.assertNotIn(self.b.admin.id, ids)

        r2 = self._client(self.a.admin).get(f"/api/users/users/{self.b.customer.id}/")
        self.assertEqual(r2.status_code, 404)

        r3 = self._client(self.a.admin).patch(
            f"/api/users/users/{self.b.customer.id}/", {"first_name": "Hackeado"}, format="json")
        self.assertEqual(r3.status_code, 404)
        self.b.customer.refresh_from_db()
        self.assertNotEqual(self.b.customer.first_name, "Hackeado")

    # 10. admin de A edita SU config de SLA; la de B queda intacta. No existe
    #     endpoint que reciba un id de organizacion para tocar la config de otro
    #     tenant (ConfigView siempre resuelve por request.organization).
    def test_sla_config_cross(self):
        from sla.models import SlaConfig
        b_before = SlaConfig.objects.get(organization=self.b.org).at_risk_threshold_pct

        r = self._client(self.a.admin).patch(
            "/api/admin/sla/config/", {"at_risk_threshold_pct": 40}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["at_risk_threshold_pct"], 40)

        cfg_a = SlaConfig.objects.get(organization=self.a.org)
        self.assertEqual(cfg_a.at_risk_threshold_pct, 40)
        cfg_b = SlaConfig.objects.get(organization=self.b.org)
        self.assertEqual(cfg_b.at_risk_threshold_pct, b_before)
        self.assertNotEqual(cfg_b.at_risk_threshold_pct, 40)


from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken

from config.asgi import application


class WsChatCrossTenantTests(TransactionTestCase):
    # TransactionTestCase (no atomic wrapper): mismo motivo que
    # notifications.tests.NotifyConsumerTests -- database_sync_to_async hace
    # close_old_connections() antes/despues de cada llamada, lo cual corrompe
    # el savepoint atomic de TestCase en MySQL.
    async def test_ws_chat_cross_rechazado(self):
        # 11. user de A intenta conectarse al chat de un ticket de B -> rechazado
        org_a = await database_sync_to_async(create_org)("WSA")
        org_b = await database_sync_to_async(create_org)("WSB")
        cust_b = await database_sync_to_async(User.objects.create_user)(
            username="ws_cust_b", password="x", role="CUSTOMER", organization=org_b)
        ticket_b = await database_sync_to_async(Ticket.objects.create)(
            reference="WSB-20260101-000001", titulo="t", descripcion="d",
            prioridad="MEDIUM", estado="OPEN", creado_por=cust_b, organization=org_b,
        )
        user_a = await database_sync_to_async(User.objects.create_user)(
            username="ws_user_a", password="x", role="CUSTOMER", organization=org_a)

        token = str(AccessToken.for_user(user_a))
        communicator = WebsocketCommunicator(application, f"/ws/chat/{ticket_b.id}/")
        communicator.scope["headers"] = [(b"cookie", f"access={token}".encode())]
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()
