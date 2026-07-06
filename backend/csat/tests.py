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


from rest_framework.test import APIClient


class SubmitCsatTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="sub_cu", password="x", role="CUSTOMER")
        self.stranger = User.objects.create_user(username="sub_x", password="x", role="CUSTOMER")
        self.agent = User.objects.create_user(username="sub_ag", password="x", role="AGENT")
        self.ticket = Ticket.objects.create(
            reference="ALS-20260101-001030", titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="RESOLVED",
            creado_por=self.customer, asignado_a=self.agent,
        )

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def _url(self):
        return f"/api/csat/{self.ticket.id}/"

    def test_submit_creates_response(self):
        r = self._client(self.customer).post(self._url(), {"score": 5, "comment": "Excelente"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["score"], 5)
        self.assertEqual(r.json()["comment"], "Excelente")
        self.assertEqual(CSATResponse.objects.filter(ticket=self.ticket).count(), 1)

    def test_submit_without_comment(self):
        r = self._client(self.customer).post(self._url(), {"score": 3}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["comment"], "")

    def test_submit_forbidden_for_non_owner(self):
        r = self._client(self.stranger).post(self._url(), {"score": 4}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_submit_rejected_if_not_eligible(self):
        self.ticket.estado = "OPEN"
        self.ticket.save(update_fields=["estado"])
        r = self._client(self.customer).post(self._url(), {"score": 4}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_submit_rejected_if_already_rated(self):
        CSATResponse.objects.create(ticket=self.ticket, score=3, comment="")
        r = self._client(self.customer).post(self._url(), {"score": 5}, format="json")
        self.assertEqual(r.status_code, 409)

    def test_submit_rejects_invalid_score(self):
        r = self._client(self.customer).post(self._url(), {"score": 6}, format="json")
        self.assertEqual(r.status_code, 400)
        r2 = self._client(self.customer).post(self._url(), {"score": 0}, format="json")
        self.assertEqual(r2.status_code, 400)
