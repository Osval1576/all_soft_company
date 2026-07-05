from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from tickets_t.models import Ticket
from notifications.models import Notification, NotificationPreference
from notifications.presence import mark_online, is_online, mark_offline
from notifications.emails import send_notification_email
from notifications.services import dispatch
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from config.asgi import application
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class ModelTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="c", password="x", role="CUSTOMER", email="c@x.com")
        self.ticket = Ticket.objects.create(
            reference="ALS-20260101-000001", titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="OPEN", creado_por=self.customer,
        )

    def test_notification_created(self):
        n = Notification.objects.create(
            recipient=self.customer, kind=Notification.Kind.STATUS_CHANGED,
            ticket=self.ticket, title="Titulo", body="Cuerpo",
        )
        self.assertFalse(n.is_read)
        self.assertEqual(n.recipient, self.customer)

    def test_preference_for_user_defaults_true(self):
        prefs = NotificationPreference.for_user(self.customer)
        self.assertTrue(prefs.email_on_assigned)
        self.assertTrue(prefs.email_on_new_message)
        self.assertTrue(prefs.email_on_status_changed)
        self.assertTrue(prefs.email_on_ticket_created)

    def test_preference_for_user_is_idempotent(self):
        a = NotificationPreference.for_user(self.customer)
        b = NotificationPreference.for_user(self.customer)
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(NotificationPreference.objects.count(), 1)


class PresenceTests(TestCase):
    def test_online_lifecycle(self):
        self.assertFalse(is_online(999))
        mark_online(999)
        self.assertTrue(is_online(999))
        mark_offline(999)
        self.assertFalse(is_online(999))


class EmailHelperTests(TestCase):
    def test_sends_when_recipient_has_email(self):
        u = User.objects.create_user(username="e1", password="x", role="CUSTOMER", email="e1@x.com")
        send_notification_email(u, "Asunto", "Cuerpo del mail")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Asunto")
        self.assertEqual(mail.outbox[0].to, ["e1@x.com"])

    def test_noop_without_email(self):
        u = User.objects.create_user(username="e2", password="x", role="CUSTOMER", email="")
        send_notification_email(u, "Asunto", "Cuerpo")
        self.assertEqual(len(mail.outbox), 0)


@override_settings(NOTIFICATIONS_EMAIL_ASYNC=False)
class DispatchTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="adm", password="x", role="ADMIN", email="adm@x.com")
        self.agent = User.objects.create_user(username="ag", password="x", role="AGENT", email="ag@x.com")
        self.customer = User.objects.create_user(username="cu", password="x", role="CUSTOMER", email="cu@x.com")
        self.ticket = Ticket.objects.create(
            reference="ALS-20260101-000100", titulo="Impresora rota", descripcion="d",
            prioridad="MEDIUM", estado="RESOLVED",
            creado_por=self.customer, asignado_a=self.agent,
        )

    def test_status_changed_notifies_customer_with_email(self):
        dispatch("status_changed", self.ticket, actor=self.agent)
        notifs = Notification.objects.filter(recipient=self.customer, kind="status_changed")
        self.assertEqual(notifs.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["cu@x.com"])

    def test_status_changed_pref_off_suppresses_email_but_keeps_notification(self):
        prefs = NotificationPreference.for_user(self.customer)
        prefs.email_on_status_changed = False
        prefs.save()
        dispatch("status_changed", self.ticket, actor=self.agent)
        self.assertEqual(Notification.objects.filter(recipient=self.customer).count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_assigned_notifies_customer_and_excludes_actor(self):
        dispatch("assigned", self.ticket, actor=self.agent)
        self.assertEqual(Notification.objects.filter(recipient=self.customer, kind="assigned").count(), 1)
        # el agent es el actor -> no se notifica a sí mismo
        self.assertEqual(Notification.objects.filter(recipient=self.agent).count(), 0)

    def test_new_message_notifies_other_party_not_sender(self):
        dispatch("new_message", self.ticket, actor=self.customer, extra={"content": "hola"})
        self.assertEqual(Notification.objects.filter(recipient=self.agent, kind="new_message").count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.customer).count(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ag@x.com"])

    def test_new_message_email_suppressed_when_recipient_online(self):
        mark_online(self.agent.id)
        dispatch("new_message", self.ticket, actor=self.customer, extra={"content": "hola"})
        self.assertEqual(Notification.objects.filter(recipient=self.agent).count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_ticket_created_notifies_admins_and_agents(self):
        new_ticket = Ticket.objects.create(
            reference="ALS-20260101-000101", titulo="Nuevo", descripcion="d",
            prioridad="MEDIUM", estado="OPEN", creado_por=self.customer,
        )
        dispatch("ticket_created", new_ticket, actor=self.customer)
        self.assertEqual(Notification.objects.filter(recipient=self.admin, kind="ticket_created").count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.agent, kind="ticket_created").count(), 1)
        # email solo al admin (los agentes son aviso de pool, sin email)
        self.assertEqual([m.to for m in mail.outbox], [["adm@x.com"]])


from rest_framework.test import APIClient


class ApiTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="apic", password="x", role="CUSTOMER", email="apic@x.com")
        self.other = User.objects.create_user(username="apio", password="x", role="CUSTOMER", email="o@x.com")
        self.ticket = Ticket.objects.create(
            reference="ALS-20260101-000200", titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="OPEN", creado_por=self.customer,
        )
        self.n1 = Notification.objects.create(recipient=self.customer, kind="status_changed", ticket=self.ticket, title="A")
        self.n2 = Notification.objects.create(recipient=self.customer, kind="status_changed", ticket=self.ticket, title="B")
        Notification.objects.create(recipient=self.other, kind="status_changed", ticket=self.ticket, title="C")

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_list_only_own(self):
        r = self._client(self.customer).get("/api/notifications/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 2)

    def test_mark_one_read(self):
        r = self._client(self.customer).post(f"/api/notifications/{self.n1.id}/read/")
        self.assertEqual(r.status_code, 200)
        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)

    def test_cannot_read_others_notification(self):
        r = self._client(self.other).post(f"/api/notifications/{self.n1.id}/read/")
        self.assertEqual(r.status_code, 404)

    def test_read_all(self):
        r = self._client(self.customer).post("/api/notifications/read-all/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Notification.objects.filter(recipient=self.customer, is_read=False).count(), 0)

    def test_get_and_patch_preferences(self):
        c = self._client(self.customer)
        r = c.get("/api/notifications/preferences/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["email_on_new_message"])
        r2 = c.patch("/api/notifications/preferences/", {"email_on_new_message": False}, format="json")
        self.assertEqual(r2.status_code, 200)
        self.assertFalse(r2.json()["email_on_new_message"])


class NotifyConsumerTests(TransactionTestCase):
    # TransactionTestCase (no atomic wrapper) en vez de TestCase: los tests async
    # usan database_sync_to_async, que hace close_old_connections() antes/despues
    # de cada llamada. Con TestCase (atomic por test), esto corrompe el estado del
    # savepoint (needs_rollback queda True espuriamente) porque el cierre de
    # conexiones no es compatible con el bloque atomic anidado en MySQL.
    async def test_anonymous_rejected(self):
        communicator = WebsocketCommunicator(application, "/ws/notify/")
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_authed_connects_and_marks_online(self):
        user = await database_sync_to_async(User.objects.create_user)(
            username="wsu", password="x", role="CUSTOMER"
        )
        token = str(AccessToken.for_user(user))
        communicator = WebsocketCommunicator(application, "/ws/notify/")
        communicator.scope["headers"] = [(b"cookie", f"access={token}".encode())]
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        online = await database_sync_to_async(is_online)(user.id)
        self.assertTrue(online)
        await communicator.disconnect()


@override_settings(NOTIFICATIONS_EMAIL_ASYNC=False)
class IntegrationTests(TransactionTestCase):
    # TransactionTestCase en vez de TestCase: test_message_creates_notification_for_other_party
    # ejecuta create_message vía async_to_sync, que está envuelto en @database_sync_to_async
    # (channels.db). Ese wrapper hace close_old_connections() antes/después de la llamada,
    # lo cual corrompe el savepoint del bloque atomic de TestCase en MySQL (mismo problema
    # documentado en NotifyConsumerTests, Task 5).
    def setUp(self):
        self.agent = User.objects.create_user(username="iag", password="x", role="AGENT", email="iag@x.com")
        self.customer = User.objects.create_user(username="icu", password="x", role="CUSTOMER", email="icu@x.com")
        self.ticket = Ticket.objects.create(
            reference="ALS-20260101-000300", titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="IN_PROGRESS",
            creado_por=self.customer, asignado_a=self.agent,
        )

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_resolving_ticket_notifies_customer(self):
        r = self._client(self.agent).patch(
            f"/api/tickets_t/{self.ticket.id}/", {"estado": "RESOLVED"}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            Notification.objects.filter(recipient=self.customer, kind="status_changed").count(), 1
        )

    def test_message_creates_notification_for_other_party(self):
        from asgiref.sync import async_to_sync
        from tickets_t.consumers import TicketChatConsumer
        consumer = TicketChatConsumer()
        # create_message está envuelto por @database_sync_to_async: async_to_sync
        # lo ejecuta hasta completarse (corre el path real, incluido el dispatch).
        async_to_sync(consumer.create_message)(self.customer.id, self.ticket.id, "hola")
        self.assertEqual(
            Notification.objects.filter(recipient=self.agent, kind="new_message").count(), 1
        )


@override_settings(NOTIFICATIONS_EMAIL_ASYNC=False)
class SlaNotificationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="sn_adm", password="x", role="ADMIN", email="adm@x.com")
        self.agent = User.objects.create_user(username="sn_ag", password="x", role="AGENT", email="ag@x.com")
        self.customer = User.objects.create_user(username="sn_cu", password="x", role="CUSTOMER")
        self.ticket = Ticket.objects.create(
            reference="ALS-20260101-000700", titulo="T", descripcion="d",
            prioridad="HIGH", estado="OPEN", creado_por=self.customer, asignado_a=self.agent,
        )

    def test_sla_breached_notifies_agent_and_admins_in_app_only(self):
        from notifications.services import dispatch
        from notifications.models import Notification
        dispatch("sla_breached", self.ticket, actor=None, extra={"clock": "resolución"})
        self.assertEqual(Notification.objects.filter(recipient=self.agent, kind="sla_breached").count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.admin, kind="sla_breached").count(), 1)
        # SLA es sólo in-app: sin emails
        self.assertEqual(len(mail.outbox), 0)

    def test_sla_at_risk_kind_routes(self):
        from notifications.services import dispatch
        from notifications.models import Notification
        dispatch("sla_at_risk", self.ticket, actor=None, extra={"clock": "primera respuesta"})
        self.assertEqual(Notification.objects.filter(kind="sla_at_risk").count(), 2)  # agent + admin
