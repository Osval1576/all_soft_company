from django.test import TestCase
from django.contrib.auth import get_user_model
from tickets_t.models import Ticket
from notifications.models import Notification, NotificationPreference

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
