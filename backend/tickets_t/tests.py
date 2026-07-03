from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tickets_t.models import Ticket

User = get_user_model()


class StateTransitionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="adm", password="x", role="ADMIN")
        self.agent = User.objects.create_user(username="ag", password="x", role="AGENT")
        self.customer = User.objects.create_user(username="cu", password="x", role="CUSTOMER")
        self.ticket = Ticket.objects.create(
            reference="ALS-20260101-000001",
            titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="OPEN",
            creado_por=self.customer, asignado_a=self.agent,
        )

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_agent_forward_transition_ok(self):
        r = self._client(self.agent).patch(f"/api/tickets_t/{self.ticket.id}/", {"estado": "IN_PROGRESS"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["estado"], "IN_PROGRESS")

    def test_agent_backward_transition_rejected(self):
        self.ticket.estado = "RESOLVED"
        self.ticket.save()
        r = self._client(self.agent).patch(f"/api/tickets_t/{self.ticket.id}/", {"estado": "IN_PROGRESS"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_admin_can_reopen_from_resolved(self):
        self.ticket.estado = "RESOLVED"
        self.ticket.save()
        r = self._client(self.admin).patch(f"/api/tickets_t/{self.ticket.id}/", {"estado": "OPEN"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["estado"], "OPEN")

    def test_admin_can_reopen_from_closed(self):
        self.ticket.estado = "CLOSED"
        self.ticket.save()
        r = self._client(self.admin).patch(f"/api/tickets_t/{self.ticket.id}/", {"estado": "OPEN"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_agent_cannot_reopen(self):
        self.ticket.estado = "RESOLVED"
        self.ticket.save()
        r = self._client(self.agent).patch(f"/api/tickets_t/{self.ticket.id}/", {"estado": "OPEN"}, format="json")
        self.assertEqual(r.status_code, 400)
