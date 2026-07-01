from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from tickets_t.models import Ticket, TicketMessage

User = get_user_model()


class ContactEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/public/contact/"

    def test_creates_user_and_ticket(self):
        r = self.client.post(self.url, {
            "name": "Ana",
            "email": "ana@example.com",
            "subject": "Cotización",
            "message": "Quiero información.",
        }, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertIn("ticket_reference", r.json())
        self.assertTrue(User.objects.filter(email="ana@example.com").exists())
        t = Ticket.objects.get(reference=r.json()["ticket_reference"])
        self.assertEqual(t.titulo, "Cotización")
        self.assertEqual(t.prioridad, "MEDIUM")
        self.assertEqual(t.estado, "OPEN")
        self.assertEqual(TicketMessage.objects.filter(ticket=t).count(), 1)

    def test_reuses_existing_user(self):
        User.objects.create_user(username="ana@example.com",
                                 email="ana@example.com", password="x",
                                 role="CUSTOMER")
        self.client.post(self.url, {
            "name": "Ana", "email": "ana@example.com",
            "subject": "S", "message": "M",
        }, format="json")
        self.assertEqual(User.objects.filter(email="ana@example.com").count(), 1)

    def test_honeypot_short_circuits(self):
        r = self.client.post(self.url, {
            "name": "Bot", "email": "bot@example.com",
            "subject": "S", "message": "M", "website": "spam.com",
        }, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_validation_error(self):
        r = self.client.post(self.url, {"name": "Ana"}, format="json")
        self.assertEqual(r.status_code, 400)
