from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from tickets_t.models import Ticket
from notifications.models import Notification, NotificationPreference
from notifications.presence import mark_online, is_online, mark_offline
from notifications.emails import send_notification_email
from notifications.services import dispatch

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
