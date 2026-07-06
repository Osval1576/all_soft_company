from django.test import TestCase
from django.contrib.auth import get_user_model
from tickets_t.models import Ticket
from csat.models import CSATResponse

User = get_user_model()


class ModelTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="cs_m_cu", password="x", role="CUSTOMER")
        self.ticket = Ticket.objects.create(
            reference="ALS-20260101-001000", titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="RESOLVED", creado_por=self.customer,
        )

    def test_creates_response_with_defaults(self):
        r = CSATResponse.objects.create(ticket=self.ticket, score=4)
        self.assertEqual(r.comment, "")
        self.assertIsNotNone(r.created_at)
        self.assertEqual(self.ticket.csat, r)

    def test_one_response_per_ticket(self):
        CSATResponse.objects.create(ticket=self.ticket, score=5)
        with self.assertRaises(Exception):
            CSATResponse.objects.create(ticket=self.ticket, score=3)
