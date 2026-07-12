from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from tickets_t.models import Ticket
from tickets_t.validators import validate_attachment

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


class PoolAndTakeTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="adm2", password="x", role="ADMIN")
        self.agent1 = User.objects.create_user(username="ag1", password="x", role="AGENT")
        self.agent2 = User.objects.create_user(username="ag2", password="x", role="AGENT")
        self.customer = User.objects.create_user(username="cu2", password="x", role="CUSTOMER")
        self.t_unassigned = Ticket.objects.create(
            reference="ALS-20260101-000010",
            titulo="U", descripcion="d",
            prioridad="MEDIUM", estado="OPEN",
            creado_por=self.customer,
        )
        self.t_assigned = Ticket.objects.create(
            reference="ALS-20260101-000011",
            titulo="A", descripcion="d",
            prioridad="MEDIUM", estado="OPEN",
            creado_por=self.customer, asignado_a=self.agent1,
        )

    def _client(self, u):
        c = APIClient()
        c.force_authenticate(user=u)
        return c

    def test_pool_lists_only_unassigned(self):
        r = self._client(self.agent1).get("/api/tickets_t/pool/")
        self.assertEqual(r.status_code, 200)
        ids = [t["id"] for t in r.json()]
        self.assertIn(self.t_unassigned.id, ids)
        self.assertNotIn(self.t_assigned.id, ids)

    def test_pool_forbidden_for_customer(self):
        r = self._client(self.customer).get("/api/tickets_t/pool/")
        self.assertEqual(r.status_code, 403)

    def test_take_assigns_and_creates_event(self):
        from tickets_t.models import TicketEvent
        r = self._client(self.agent1).post(f"/api/tickets_t/{self.t_unassigned.id}/take/")
        self.assertEqual(r.status_code, 200)
        self.t_unassigned.refresh_from_db()
        self.assertEqual(self.t_unassigned.asignado_a_id, self.agent1.id)
        self.assertTrue(TicketEvent.objects.filter(ticket=self.t_unassigned, kind="assigned", actor=self.agent1).exists())

    def test_take_conflict_if_already_assigned(self):
        r = self._client(self.agent2).post(f"/api/tickets_t/{self.t_assigned.id}/take/")
        self.assertEqual(r.status_code, 409)

    def test_take_forbidden_for_customer(self):
        r = self._client(self.customer).post(f"/api/tickets_t/{self.t_unassigned.id}/take/")
        self.assertEqual(r.status_code, 403)

    def test_admin_assigns_only_to_agent(self):
        r = self._client(self.admin).patch(
            f"/api/tickets_t/{self.t_unassigned.id}/",
            {"asignado_a": self.customer.id},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_admin_assigns_agent_ok(self):
        r = self._client(self.admin).patch(
            f"/api/tickets_t/{self.t_unassigned.id}/",
            {"asignado_a": self.agent2.id},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_status_change_emits_event(self):
        from tickets_t.models import TicketEvent
        self._client(self.agent1).patch(
            f"/api/tickets_t/{self.t_assigned.id}/",
            {"estado": "IN_PROGRESS"},
            format="json",
        )
        self.assertTrue(TicketEvent.objects.filter(
            ticket=self.t_assigned, kind="status_changed", payload__to="IN_PROGRESS"
        ).exists())

    def test_events_endpoint_returns_history(self):
        from tickets_t.models import TicketEvent
        TicketEvent.objects.create(ticket=self.t_unassigned, kind="created", actor=self.customer)
        r = self._client(self.customer).get(f"/api/tickets_t/{self.t_unassigned.id}/events/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(any(e["kind"] == "created" for e in r.json()))


def _png_bytes():
    # PNG 1x1 mínimo válido
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"
    )


class AttachmentModelTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="atc", password="x", role="CUSTOMER")
        self.ticket = Ticket.objects.create(
            reference="ALS-20260101-000400", titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="OPEN", creado_por=self.customer,
        )

    def test_message_with_attachment_fields(self):
        from tickets_t.models import TicketMessage
        f = SimpleUploadedFile("foto.png", _png_bytes(), content_type="image/png")
        m = TicketMessage.objects.create(
            ticket=self.ticket, sender=self.customer, content="",
            attachment=f, attachment_name="foto.png",
            attachment_size=len(_png_bytes()), attachment_content_type="image/png",
        )
        self.assertTrue(m.attachment.name.startswith("ticket_adjuntos/"))
        self.assertTrue(m.attachment.name.endswith(".png"))
        self.assertEqual(m.attachment_name, "foto.png")

    def test_validate_attachment_accepts_png(self):
        f = SimpleUploadedFile("foto.png", _png_bytes(), content_type="image/png")
        validate_attachment(f)  # no raise

    def test_validate_attachment_rejects_bad_type(self):
        f = SimpleUploadedFile("x.txt", b"hola", content_type="text/plain")
        with self.assertRaises(DjangoValidationError):
            validate_attachment(f)

    def test_validate_attachment_rejects_fake_pdf(self):
        f = SimpleUploadedFile("x.pdf", b"noPDF", content_type="application/pdf")
        with self.assertRaises(DjangoValidationError):
            validate_attachment(f)

    def test_validate_attachment_rejects_oversized_image(self):
        from tickets_t.validators import IMAGE_MAX_BYTES
        f = SimpleUploadedFile(
            "big.png", b"\x00" * (IMAGE_MAX_BYTES + 1), content_type="image/png",
        )
        with self.assertRaises(DjangoValidationError):
            validate_attachment(f)


from tickets_t.permissions import can_access_ticket
from tickets_t.payloads import message_to_payload
from tickets_t.serializers import TicketMessageSerializer


class AccessAndPayloadTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="pa_adm", password="x", role="ADMIN")
        self.agent = User.objects.create_user(username="pa_ag", password="x", role="AGENT")
        self.other_agent = User.objects.create_user(username="pa_ag2", password="x", role="AGENT")
        self.customer = User.objects.create_user(username="pa_cu", password="x", role="CUSTOMER")
        self.other_customer = User.objects.create_user(username="pa_cu2", password="x", role="CUSTOMER")
        self.ticket = Ticket.objects.create(
            reference="ALS-20260101-000410", titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="OPEN",
            creado_por=self.customer, asignado_a=self.agent,
        )

    def test_access_matrix(self):
        self.assertTrue(can_access_ticket(self.admin, self.ticket))
        self.assertTrue(can_access_ticket(self.customer, self.ticket))
        self.assertTrue(can_access_ticket(self.agent, self.ticket))
        self.assertFalse(can_access_ticket(self.other_customer, self.ticket))
        self.assertFalse(can_access_ticket(self.other_agent, self.ticket))

    def test_payload_without_attachment_is_null(self):
        from tickets_t.models import TicketMessage
        m = TicketMessage.objects.create(ticket=self.ticket, sender=self.customer, content="hola")
        p = message_to_payload(m)
        self.assertIsNone(p["attachment"])
        self.assertEqual(p["content"], "hola")
        self.assertEqual(p["sender_username"], "pa_cu")

    def test_payload_with_attachment(self):
        from tickets_t.models import TicketMessage
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("foto.png", _png_bytes(), content_type="image/png")
        m = TicketMessage.objects.create(
            ticket=self.ticket, sender=self.customer, content="",
            attachment=f, attachment_name="foto.png",
            attachment_size=123, attachment_content_type="image/png",
        )
        p = message_to_payload(m)
        self.assertEqual(p["attachment"]["name"], "foto.png")
        self.assertTrue(p["attachment"]["is_image"])
        self.assertEqual(
            p["attachment"]["url"],
            f"/api/tickets_t/{self.ticket.id}/attachments/{m.id}/download/",
        )
        # el serializer produce el mismo objeto attachment
        s = TicketMessageSerializer(m).data
        self.assertEqual(s["attachment"]["name"], "foto.png")


from django.test import override_settings


@override_settings(NOTIFICATIONS_EMAIL_ASYNC=False)
class UploadAttachmentTests(TestCase):
    def setUp(self):
        self.agent = User.objects.create_user(username="up_ag", password="x", role="AGENT", email="a@x.com")
        self.customer = User.objects.create_user(username="up_cu", password="x", role="CUSTOMER", email="c@x.com")
        self.stranger = User.objects.create_user(username="up_x", password="x", role="CUSTOMER")
        self.ticket = Ticket.objects.create(
            reference="ALS-20260101-000420", titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="IN_PROGRESS",
            creado_por=self.customer, asignado_a=self.agent,
        )

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def _png(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile("foto.png", _png_bytes(), content_type="image/png")

    def test_upload_creates_message_with_attachment(self):
        from tickets_t.models import TicketMessage
        r = self._client(self.customer).post(
            f"/api/tickets_t/{self.ticket.id}/attachments/",
            {"file": self._png(), "content": "mirá esto"}, format="multipart",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["attachment"]["name"], "foto.png")
        self.assertTrue(r.json()["attachment"]["is_image"])
        self.assertEqual(r.json()["content"], "mirá esto")
        m = TicketMessage.objects.get(id=r.json()["id"])
        self.assertEqual(m.sender, self.customer)
        self.assertTrue(m.attachment)

    def test_upload_attachment_only_no_caption(self):
        r = self._client(self.agent).post(
            f"/api/tickets_t/{self.ticket.id}/attachments/",
            {"file": self._png()}, format="multipart",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["content"], "")

    def test_upload_notifies_other_party(self):
        from notifications.models import Notification
        self._client(self.customer).post(
            f"/api/tickets_t/{self.ticket.id}/attachments/",
            {"file": self._png()}, format="multipart",
        )
        self.assertEqual(
            Notification.objects.filter(recipient=self.agent, kind="new_message").count(), 1
        )

    def test_upload_forbidden_for_stranger(self):
        r = self._client(self.stranger).post(
            f"/api/tickets_t/{self.ticket.id}/attachments/",
            {"file": self._png()}, format="multipart",
        )
        self.assertEqual(r.status_code, 403)

    def test_upload_rejects_bad_type(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        bad = SimpleUploadedFile("x.txt", b"hola", content_type="text/plain")
        r = self._client(self.customer).post(
            f"/api/tickets_t/{self.ticket.id}/attachments/",
            {"file": bad}, format="multipart",
        )
        self.assertEqual(r.status_code, 400)

    def test_upload_missing_file(self):
        r = self._client(self.customer).post(
            f"/api/tickets_t/{self.ticket.id}/attachments/", {}, format="multipart",
        )
        self.assertEqual(r.status_code, 400)


class DownloadAttachmentTests(TestCase):
    def setUp(self):
        self.agent = User.objects.create_user(username="dl_ag", password="x", role="AGENT")
        self.customer = User.objects.create_user(username="dl_cu", password="x", role="CUSTOMER")
        self.stranger = User.objects.create_user(username="dl_x", password="x", role="CUSTOMER")
        self.ticket = Ticket.objects.create(
            reference="ALS-20260101-000430", titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="OPEN",
            creado_por=self.customer, asignado_a=self.agent,
        )
        from tickets_t.models import TicketMessage
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("foto.png", _png_bytes(), content_type="image/png")
        self.msg = TicketMessage.objects.create(
            ticket=self.ticket, sender=self.customer, content="",
            attachment=f, attachment_name="foto.png",
            attachment_size=len(_png_bytes()), attachment_content_type="image/png",
        )

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def _url(self, mid=None):
        return f"/api/tickets_t/{self.ticket.id}/attachments/{mid or self.msg.id}/download/"

    def test_download_ok_for_participant(self):
        r = self._client(self.customer).get(self._url())
        self.assertEqual(r.status_code, 200)
        self.assertIn("foto.png", r["Content-Disposition"])
        self.assertEqual(b"".join(r.streaming_content), _png_bytes())

    def test_download_forbidden_for_stranger(self):
        r = self._client(self.stranger).get(self._url())
        self.assertEqual(r.status_code, 403)

    def test_download_lleva_nosniff(self):
        r = self._client(self.customer).get(self._url())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")

    def test_download_404_for_missing_message(self):
        r = self._client(self.customer).get(self._url(mid=999999))
        self.assertEqual(r.status_code, 404)
