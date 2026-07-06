from django.test import TestCase
from django.contrib.auth import get_user_model
from tickets_t.models import Ticket
from csat.models import CSATResponse
from csat.eligibility import is_eligible
from csat.payloads import csat_payload

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


class EligibilityTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="el_cu", password="x", role="CUSTOMER")

    def _ticket(self, estado, ref):
        return Ticket.objects.create(
            reference=ref, titulo="T", descripcion="d",
            prioridad="MEDIUM", estado=estado, creado_por=self.customer,
        )

    def test_eligible_states(self):
        self.assertTrue(is_eligible(self._ticket("RESOLVED", "ALS-20260101-001010")))
        self.assertTrue(is_eligible(self._ticket("CLOSED", "ALS-20260101-001011")))

    def test_not_eligible_states(self):
        self.assertFalse(is_eligible(self._ticket("OPEN", "ALS-20260101-001012")))
        self.assertFalse(is_eligible(self._ticket("IN_PROGRESS", "ALS-20260101-001013")))


class PayloadTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="pl_cu", password="x", role="CUSTOMER")
        self.ticket = Ticket.objects.create(
            reference="ALS-20260101-001020", titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="RESOLVED", creado_por=self.customer,
        )

    def test_payload_none_without_response(self):
        self.assertIsNone(csat_payload(self.ticket))

    def test_payload_with_response(self):
        CSATResponse.objects.create(ticket=self.ticket, score=5, comment="Genial")
        p = csat_payload(self.ticket)
        self.assertEqual(p["score"], 5)
        self.assertEqual(p["comment"], "Genial")
        self.assertIn("created_at", p)
