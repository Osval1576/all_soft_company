# Dashboards v2 · Fase 3 — Enriquecimiento · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adjuntos (imágenes/PDF) en el chat de tickets con endpoint de descarga protegido, más filtros y orden client-side en los dashboards de Admin y Técnico.

**Architecture:** Los adjuntos entran por un endpoint REST multipart que crea el `TicketMessage` con el archivo, hace `group_send` al grupo WS `ticket_{id}` (los conectados lo ven en vivo) y dispara la notificación `new_message`. Un endpoint de descarga protegido verifica acceso al ticket antes de streamear. El frontend carga imágenes/PDF con fetch autenticado (blob → objectURL) por la cookie `SameSite=Lax` cross-origin. Filtros/orden son client-side vía un composable compartido.

**Tech Stack:** Django 6 + DRF + Channels, Pillow (validación de imagen ya presente), Vue 3.5 + Pinia, MySQL.

## Global Constraints

- Adjuntos: imágenes `image/jpeg|png|webp` ≤ 2 MB, PDF `application/pdf` ≤ 10 MB, **1 por mensaje** + caption opcional. Un mensaje es válido si tiene `content` no vacío **o** `attachment`.
- Acceso a archivos: **endpoint de descarga protegido** con la regla de acceso al ticket (ADMIN/superuser: todos; CUSTOMER: `creado_por`; AGENT: `asignado_a`). El serializer/payload expone sólo la URL del endpoint (`/api/tickets_t/<ticket_id>/attachments/<message_id>/download/`), nunca la ruta MEDIA cruda.
- Nombre en disco: uuid (evita enumeración); `attachment_name` guarda el original. `django_cleanup` ya instalado borra el archivo al borrar el mensaje.
- Cross-origin: front :5173 / API :8000, cookie `access` `SameSite=Lax` NO viaja en subrecursos `<img>` cross-site → imágenes y descargas van por **fetch autenticado** (axios `withCredentials`, `responseType: "blob"`) → objectURL.
- Filtros/orden: **client-side** (datos ya cargados), Admin + Técnico, composable compartido. Cliente queda igual.
- Estética v2: hairline 0.5px, CSS vars, voseo. Reusar estilos existentes (`.inline-select`, `.search-input`, chips hairline).
- Tests backend: `django.test.TestCase` + `APIClient` + `force_authenticate` + `SimpleUploadedFile`, siguiendo `backend/tickets_t/tests.py`. Correr desde `backend/`: `python manage.py test tickets_t -v 2` (agregar `--keepdb` si "database exists").
- Frontend sin runner de tests: verificación = `cd frontend; npm run build` limpio + checklist manual. System Python `C:\Python312\python.exe` (con Django/Pillow); no venv.

---

## File Structure

**Backend:**
- Create: `backend/tickets_t/validators.py` — `validate_attachment`
- Create: `backend/tickets_t/payloads.py` — `attachment_payload`, `message_to_payload`
- Modify: `backend/tickets_t/models.py` — campos de adjunto + `attachment_upload_to`
- Modify: `backend/tickets_t/permissions.py` — `can_access_ticket(user, ticket)`
- Modify: `backend/tickets_t/serializers.py` — `TicketMessageSerializer.attachment`
- Modify: `backend/tickets_t/views.py` — acciones `upload_attachment`, `download_attachment` + logger
- Migración nueva en `backend/tickets_t/migrations/`
- Test: `backend/tickets_t/tests.py`

**Frontend:**
- Modify: `frontend/src/api/tickets.api.js` — `uploadAttachment`, `fetchAttachmentBlob`
- Create: `frontend/src/components/tickets/MessageAttachment.vue`
- Modify: `frontend/src/components/ChatPanel.vue` — composer clip + render adjunto
- Create: `frontend/src/composables/useTicketFilters.js`
- Modify: `frontend/src/views/dashboards/AdminDashboard.vue` — filtros + orden por columnas
- Modify: `frontend/src/views/dashboards/TechnicianDashboard.vue` — filtros + orden

---

## Task 1: Modelo de adjunto + validador

**Files:**
- Create: `backend/tickets_t/validators.py`
- Modify: `backend/tickets_t/models.py`
- Test: `backend/tickets_t/tests.py`

**Interfaces:**
- Produces: `validate_attachment(file)` (raise `django.core.exceptions.ValidationError`). `TicketMessage` con campos `attachment` (FileField), `attachment_name`, `attachment_size`, `attachment_content_type`; función `attachment_upload_to(instance, filename)`.

- [ ] **Step 1: Escribir el validador**

`backend/tickets_t/validators.py`:
```python
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
IMAGE_MAX_BYTES = 2 * 1024 * 1024
PDF_MAX_BYTES = 10 * 1024 * 1024


def validate_attachment(file):
    content_type = getattr(file, "content_type", None)
    if content_type in IMAGE_TYPES:
        if file.size > IMAGE_MAX_BYTES:
            raise ValidationError("La imagen excede 2 MB.")
        try:
            Image.open(file).verify()
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
            raise ValidationError("El archivo no es una imagen válida.")
        finally:
            file.seek(0)
    elif content_type == "application/pdf":
        if file.size > PDF_MAX_BYTES:
            raise ValidationError("El PDF excede 10 MB.")
        head = file.read(5)
        file.seek(0)
        if head != b"%PDF-":
            raise ValidationError("El archivo no es un PDF válido.")
    else:
        raise ValidationError("Tipo de archivo no permitido (imágenes o PDF).")
```

- [ ] **Step 2: Escribir el test que falla (modelo + validador)**

Agregar a `backend/tickets_t/tests.py` (al final):
```python
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from tickets_t.validators import validate_attachment


def _png_bytes():
    # PNG 1x1 mínimo válido
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
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
```

- [ ] **Step 3: Correr el test para verificar que falla**

Run (desde `backend/`): `python manage.py test tickets_t.tests.AttachmentModelTests -v 2`
Expected: FAIL (los campos `attachment*` no existen / import de validators falla).

- [ ] **Step 4: Agregar los campos al modelo**

En `backend/tickets_t/models.py`, arriba (imports) agregar:
```python
import os
import uuid
from .validators import validate_attachment


def attachment_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    now = timezone.now()
    return f"ticket_adjuntos/{now:%Y/%m}/{uuid.uuid4().hex}{ext}"
```
(`timezone` ya está importado en models.py.) Dentro de `class TicketMessage`, después de `content`:
```python
    attachment = models.FileField(
        upload_to=attachment_upload_to, null=True, blank=True,
        validators=[validate_attachment],
    )
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_size = models.PositiveIntegerField(null=True, blank=True)
    attachment_content_type = models.CharField(max_length=100, blank=True)
```

- [ ] **Step 5: Generar la migración**

Run (desde `backend/`): `python manage.py makemigrations tickets_t`
Expected: crea una migración que agrega los 4 campos a `TicketMessage`.

- [ ] **Step 6: Correr los tests para verificar que pasan**

Run: `python manage.py test tickets_t.tests.AttachmentModelTests -v 2`
Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
git add backend/tickets_t/validators.py backend/tickets_t/models.py backend/tickets_t/migrations backend/tickets_t/tests.py
git commit -m "feat(tickets_t): campos de adjunto en TicketMessage + validate_attachment"
```

---

## Task 2: Regla de acceso reutilizable + payload/serializer del adjunto

**Files:**
- Modify: `backend/tickets_t/permissions.py`
- Create: `backend/tickets_t/payloads.py`
- Modify: `backend/tickets_t/serializers.py`
- Test: `backend/tickets_t/tests.py`

**Interfaces:**
- Consumes: `TicketMessage` con campos de adjunto (Task 1).
- Produces:
  - `can_access_ticket(user, ticket) -> bool` (en `permissions.py`).
  - `attachment_payload(msg) -> dict | None` y `message_to_payload(msg) -> dict` (en `payloads.py`).
  - `TicketMessageSerializer` con campo `attachment` (objeto o null).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `backend/tickets_t/tests.py`:
```python
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
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `python manage.py test tickets_t.tests.AccessAndPayloadTests -v 2`
Expected: FAIL (ImportError: `can_access_ticket` / `payloads`).

- [ ] **Step 3: Agregar `can_access_ticket` a permissions.py**

Al final de `backend/tickets_t/permissions.py`:
```python
def can_access_ticket(user, ticket):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    r = getattr(user, "role", None)
    if r == "ADMIN" or user.is_superuser:
        return True
    if r == "CUSTOMER":
        return ticket.creado_por_id == user.id
    if r == "AGENT":
        return ticket.asignado_a_id == user.id
    return False
```

- [ ] **Step 4: Crear payloads.py**

`backend/tickets_t/payloads.py`:
```python
def attachment_payload(msg):
    if not msg.attachment:
        return None
    ct = msg.attachment_content_type or ""
    return {
        "name": msg.attachment_name,
        "size": msg.attachment_size,
        "content_type": ct,
        "is_image": ct.startswith("image/"),
        "url": f"/api/tickets_t/{msg.ticket_id}/attachments/{msg.id}/download/",
    }


def message_to_payload(msg):
    return {
        "id": msg.id,
        "ticket": msg.ticket_id,
        "sender": msg.sender_id,
        "sender_username": msg.sender.username,
        "sender_role": getattr(msg.sender, "role", None),
        "content": msg.content,
        "created_at": msg.created_at.isoformat(),
        "attachment": attachment_payload(msg),
    }
```

- [ ] **Step 5: Agregar el campo `attachment` al serializer**

En `backend/tickets_t/serializers.py`, en `TicketMessageSerializer` agregar el método-field y sumarlo a `fields`:
```python
class TicketMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)
    sender_role = serializers.CharField(source="sender.role", read_only=True)
    attachment = serializers.SerializerMethodField()

    class Meta:
        model = TicketMessage
        fields = [
            "id", "ticket", "sender", "sender_username", "sender_role",
            "content", "created_at", "attachment",
        ]
        read_only_fields = [
            "id", "ticket", "sender", "sender_username", "sender_role",
            "created_at", "attachment",
        ]

    def get_attachment(self, obj):
        from .payloads import attachment_payload
        return attachment_payload(obj)
```

- [ ] **Step 6: Correr los tests para verificar que pasan**

Run: `python manage.py test tickets_t.tests.AccessAndPayloadTests -v 2`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add backend/tickets_t/permissions.py backend/tickets_t/payloads.py backend/tickets_t/serializers.py backend/tickets_t/tests.py
git commit -m "feat(tickets_t): can_access_ticket reutilizable + payload/serializer de adjunto"
```

---

## Task 3: Endpoint de upload de adjunto

**Files:**
- Modify: `backend/tickets_t/views.py`
- Test: `backend/tickets_t/tests.py`

**Interfaces:**
- Consumes: `validate_attachment` (T1), `can_access_ticket`, `message_to_payload` (T2).
- Produces: `POST /api/tickets_t/<id>/attachments/` (multipart `file` + `content`).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `backend/tickets_t/tests.py`:
```python
from django.test import override_settings
from rest_framework.test import APIClient


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
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `python manage.py test tickets_t.tests.UploadAttachmentTests -v 2`
Expected: FAIL (404 — la acción no existe).

- [ ] **Step 3: Implementar la acción `upload_attachment`**

En `backend/tickets_t/views.py`, agregar imports arriba:
```python
import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .validators import validate_attachment
from .permissions import can_access_ticket
from .payloads import message_to_payload

logger = logging.getLogger(__name__)
```
Dentro de `TicketViewSet`, agregar la acción (después de `events`):
```python
    @action(detail=True, methods=["post"], url_path="attachments",
            parser_classes=[MultiPartParser, FormParser])
    def upload_attachment(self, request, pk=None):
        ticket = Ticket.objects.filter(pk=pk).first()
        if ticket is None:
            return Response({"detail": "No encontrado."}, status=404)
        if not can_access_ticket(request.user, ticket):
            return Response({"detail": "Sin acceso al ticket."}, status=403)
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "Falta el archivo."}, status=400)
        try:
            validate_attachment(file)
        except DjangoValidationError as e:
            return Response({"detail": e.messages[0]}, status=400)

        caption = (request.data.get("content") or "").strip()
        msg = TicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            content=caption,
            attachment=file,
            attachment_name=file.name[:255],
            attachment_size=file.size,
            attachment_content_type=getattr(file, "content_type", "") or "",
        )
        payload = message_to_payload(msg)

        layer = get_channel_layer()
        if layer is not None:
            try:
                async_to_sync(layer.group_send)(
                    f"ticket_{ticket.id}", {"type": "chat.message", "message": payload}
                )
            except Exception:
                logger.exception("attachment broadcast failed for ticket %s", ticket.id)

        from notifications.services import dispatch
        try:
            dispatch("new_message", ticket, actor=request.user,
                     extra={"content": caption or file.name})
        except Exception:
            logger.exception("notification dispatch failed for ticket %s", ticket.id)

        return Response(payload, status=201)
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `python manage.py test tickets_t.tests.UploadAttachmentTests -v 2`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/tickets_t/views.py backend/tickets_t/tests.py
git commit -m "feat(tickets_t): endpoint POST attachments (crea mensaje + broadcast + notifica)"
```

---

## Task 4: Endpoint de descarga protegido

**Files:**
- Modify: `backend/tickets_t/views.py`
- Test: `backend/tickets_t/tests.py`

**Interfaces:**
- Consumes: `can_access_ticket` (T2).
- Produces: `GET /api/tickets_t/<id>/attachments/<message_id>/download/`.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `backend/tickets_t/tests.py`:
```python
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

    def test_download_404_for_missing_message(self):
        r = self._client(self.customer).get(self._url(mid=999999))
        self.assertEqual(r.status_code, 404)
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `python manage.py test tickets_t.tests.DownloadAttachmentTests -v 2`
Expected: FAIL (404 — la acción no existe).

- [ ] **Step 3: Implementar la acción `download_attachment`**

En `backend/tickets_t/views.py`, agregar el import de `FileResponse` arriba:
```python
from django.http import FileResponse
```
Dentro de `TicketViewSet`, agregar la acción:
```python
    @action(detail=True, methods=["get"],
            url_path=r"attachments/(?P<message_id>[^/.]+)/download")
    def download_attachment(self, request, pk=None, message_id=None):
        ticket = Ticket.objects.filter(pk=pk).first()
        if ticket is None:
            return Response({"detail": "No encontrado."}, status=404)
        if not can_access_ticket(request.user, ticket):
            return Response({"detail": "Sin acceso al ticket."}, status=403)
        msg = TicketMessage.objects.filter(pk=message_id, ticket=ticket).first()
        if msg is None or not msg.attachment:
            return Response({"detail": "Adjunto no encontrado."}, status=404)
        resp = FileResponse(
            msg.attachment.open("rb"),
            content_type=msg.attachment_content_type or "application/octet-stream",
        )
        resp["Content-Disposition"] = f'attachment; filename="{msg.attachment_name}"'
        return resp
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `python manage.py test tickets_t.tests.DownloadAttachmentTests -v 2`
Expected: PASS (3 tests).

- [ ] **Step 5: Correr toda la suite tickets_t (regresión)**

Run: `python manage.py test tickets_t -v 1`
Expected: PASS (tests previos + los nuevos de adjuntos).

- [ ] **Step 6: Commit**

```bash
git add backend/tickets_t/views.py backend/tickets_t/tests.py
git commit -m "feat(tickets_t): endpoint GET download de adjunto protegido por acceso al ticket"
```

---

## Task 5: Frontend — API + composer con adjunto en ChatPanel

**Files:**
- Modify: `frontend/src/api/tickets.api.js`
- Modify: `frontend/src/components/ChatPanel.vue`

**Interfaces:**
- Produces: `uploadAttachment(ticketId, file, caption)`, `fetchAttachmentBlob(url)`.

- [ ] **Step 1: Agregar los wrappers de API**

En `frontend/src/api/tickets.api.js`, al final:
```javascript
export async function uploadAttachment(ticketId, file, caption) {
  const form = new FormData();
  form.append("file", file);
  if (caption) form.append("content", caption);
  const res = await http.post(`/api/tickets_t/${ticketId}/attachments/`, form);
  return res.data;
}

export async function fetchAttachmentBlob(url) {
  const res = await http.get(url, { responseType: "blob" });
  return res.data;
}
```
(`http` de axios ya tiene `baseURL: http://localhost:8000` y `withCredentials: true`; una `url` que empieza con `/api/...` se resuelve contra el baseURL.)

- [ ] **Step 2: Agregar el composer de adjunto a ChatPanel**

En `frontend/src/components/ChatPanel.vue`, reemplazar el `<footer class="composer">` actual por:
```html
    <footer class="composer">
      <input
        ref="fileInput"
        type="file"
        accept="image/jpeg,image/png,image/webp,application/pdf"
        class="file-hidden"
        @change="onFilePicked"
      />
      <button
        class="clip-btn"
        :disabled="wsStatus === 'disconnected' || uploading"
        @click="fileInput?.click()"
        aria-label="Adjuntar archivo"
      >📎</button>

      <div class="composer-main">
        <div v-if="pendingFile" class="pending-chip">
          <span class="pending-name">{{ pendingFile.name }}</span>
          <span class="pending-size">{{ prettySize(pendingFile.size) }}</span>
          <button class="pending-remove" @click="clearPending" aria-label="Quitar">✕</button>
        </div>
        <input
          v-model="draft"
          @keydown.enter.prevent="send"
          :placeholder="pendingFile ? 'Agregá un comentario (opcional)…' : composerPlaceholder"
          class="composer-input"
          :disabled="wsStatus === 'disconnected' && !pendingFile"
        />
      </div>

      <button
        @click="send"
        :disabled="!canSend"
        class="composer-btn"
      >{{ uploading ? 'Subiendo…' : 'Enviar' }}</button>
    </footer>
```
En el `<script setup>`, agregar el import y el estado (después de la línea `const draft = ref("");`):
```javascript
import { uploadAttachment } from "../api/tickets.api";

const fileInput = ref(null);
const pendingFile = ref(null);
const uploading = ref(false);

const canSend = computed(() => {
  if (uploading.value) return false;
  if (pendingFile.value) return true;
  return !!draft.value.trim() && wsStatus.value === "connected";
});

function onFilePicked(e) {
  const f = e.target.files?.[0];
  if (f) pendingFile.value = f;
  e.target.value = "";
}
function clearPending() { pendingFile.value = null; }
function prettySize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
```
Reemplazar la función `send()` existente por:
```javascript
async function send() {
  if (pendingFile.value) {
    uploading.value = true;
    try {
      // El mensaje llega por WS (broadcast del backend); no lo insertamos localmente.
      await uploadAttachment(props.ticketId, pendingFile.value, draft.value.trim());
      pendingFile.value = null;
      draft.value = "";
    } catch (err) {
      alert(err?.response?.data?.detail || "No se pudo subir el archivo.");
    } finally {
      uploading.value = false;
    }
    return;
  }
  const text = draft.value.trim();
  if (!text) return;
  if (wsSend({ content: text })) {
    draft.value = "";
  }
}
```

- [ ] **Step 3: Agregar estilos del composer**

En el `<style scoped>` de `ChatPanel.vue`, agregar:
```css
.file-hidden { display: none; }
.clip-btn {
  flex-shrink: 0;
  width: 38px; height: 38px;
  border: 0.5px solid var(--border);
  border-radius: var(--r);
  background: var(--surface-2);
  cursor: pointer;
  font-size: 16px;
}
.clip-btn:hover:not(:disabled) { background: var(--border); }
.clip-btn:disabled { opacity: .4; cursor: not-allowed; }
.composer-main { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.pending-chip {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 4px 8px;
  border: 0.5px solid var(--border);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  font-size: 12px;
  align-self: flex-start;
}
.pending-name { color: var(--text); font-weight: 500; }
.pending-size { color: var(--text-3); font-family: var(--font-mono); font-size: 10px; }
.pending-remove { color: var(--text-3); font-size: 11px; }
.pending-remove:hover { color: var(--c-urgent); }
```

- [ ] **Step 4: Verificar build**

Run: `cd frontend; npm run build`
Expected: build limpio.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/tickets.api.js frontend/src/components/ChatPanel.vue
git commit -m "feat(frontend): composer de adjuntos en ChatPanel + uploadAttachment"
```

---

## Task 6: Frontend — render del adjunto (MessageAttachment)

**Files:**
- Create: `frontend/src/components/tickets/MessageAttachment.vue`
- Modify: `frontend/src/components/ChatPanel.vue`

**Interfaces:**
- Consumes: `fetchAttachmentBlob(url)` (T5).

- [ ] **Step 1: Crear MessageAttachment.vue**

`frontend/src/components/tickets/MessageAttachment.vue`:
```vue
<template>
  <div class="att">
    <template v-if="att.is_image">
      <img
        v-if="objectUrl"
        :src="objectUrl"
        class="att-img"
        :alt="att.name"
        @click="openBlob"
      />
      <div v-else-if="error" class="att-error">No se pudo cargar la imagen</div>
      <div v-else class="att-loading">Cargando imagen…</div>
    </template>

    <button v-else class="att-file" @click="download">
      <span class="att-icon">📄</span>
      <span class="att-meta">
        <span class="att-name">{{ att.name }}</span>
        <span class="att-size">{{ prettySize(att.size) }}</span>
      </span>
      <span class="att-dl">↓</span>
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import { fetchAttachmentBlob } from "../../api/tickets.api";

const props = defineProps({ att: { type: Object, required: true } });

const objectUrl = ref(null);
const error = ref(false);

function prettySize(bytes) {
  if (!bytes && bytes !== 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

async function loadImage() {
  try {
    const blob = await fetchAttachmentBlob(props.att.url);
    objectUrl.value = URL.createObjectURL(blob);
  } catch (_) {
    error.value = true;
  }
}

function openBlob() {
  if (objectUrl.value) window.open(objectUrl.value, "_blank");
}

async function download() {
  try {
    const blob = await fetchAttachmentBlob(props.att.url);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = props.att.name || "archivo";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (_) {
    alert("No se pudo descargar el archivo.");
  }
}

onMounted(() => { if (props.att.is_image) loadImage(); });
onBeforeUnmount(() => { if (objectUrl.value) URL.revokeObjectURL(objectUrl.value); });
</script>

<style scoped>
.att { margin-top: 4px; }
.att-img {
  max-width: 220px; max-height: 220px;
  border-radius: var(--r-sm);
  border: 0.5px solid var(--border);
  cursor: pointer;
  display: block;
}
.att-loading, .att-error { font-size: 12px; color: var(--text-3); }
.att-file {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 8px 12px;
  border: 0.5px solid var(--border);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  cursor: pointer;
  max-width: 240px;
}
.att-file:hover { background: var(--border); }
.att-icon { font-size: 18px; }
.att-meta { display: flex; flex-direction: column; min-width: 0; text-align: left; }
.att-name {
  font-size: 12px; font-weight: 500; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.att-size { font-size: 10px; color: var(--text-3); font-family: var(--font-mono); }
.att-dl { margin-left: auto; color: var(--text-3); }
</style>
```

- [ ] **Step 2: Renderizar el adjunto en las burbujas de ChatPanel**

En `frontend/src/components/ChatPanel.vue`, importar el componente en `<script setup>`:
```javascript
import MessageAttachment from "./tickets/MessageAttachment.vue";
```
En el template, dentro de `.bubble`, después del `<div class="bubble-content">`, agregar el render del adjunto (y hacer que el content sólo se muestre si existe):
```html
            <div v-if="m.content" class="bubble-content">{{ m.content }}</div>
            <MessageAttachment v-if="m.attachment" :att="m.attachment" />
```
(Reemplaza la línea existente `<div class="bubble-content">{{ m.content }}</div>` por esas dos líneas.)

- [ ] **Step 3: Verificar build**

Run: `cd frontend; npm run build`
Expected: build limpio.

- [ ] **Step 4: Verificación manual**

Con backend (`python backend/manage.py runserver`) ASGI + frontend (`npm run dev`): en un ticket, adjuntar una imagen → aparece thumbnail inline (cargada por fetch autenticado); click → abre en pestaña nueva. Adjuntar un PDF → chip con nombre; click → descarga. La contraparte conectada ve el adjunto en vivo por WS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/tickets/MessageAttachment.vue frontend/src/components/ChatPanel.vue
git commit -m "feat(frontend): render de adjuntos (imagen inline + chip PDF) con fetch autenticado"
```

---

## Task 7: Frontend — composable useTicketFilters

**Files:**
- Create: `frontend/src/composables/useTicketFilters.js`

**Interfaces:**
- Produces: `useTicketFilters(ticketsRef)` → `{ estado, prioridad, asignado, sortKey, sortDir, toggleSort, result }`.

- [ ] **Step 1: Crear el composable**

`frontend/src/composables/useTicketFilters.js`:
```javascript
import { ref, computed, unref } from "vue";

const PRIORITY_RANK = { LOW: 0, MEDIUM: 1, HIGH: 2, URGENT: 3 };

export function useTicketFilters(ticketsRef) {
  const estado = ref("");        // "" = todos
  const prioridad = ref("");
  const asignado = ref("");      // "" = todos, "none" = sin asignar, o id (string)
  const sortKey = ref("created_at");
  const sortDir = ref("desc");   // "asc" | "desc"

  function toggleSort(key) {
    if (sortKey.value === key) {
      sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
    } else {
      sortKey.value = key;
      sortDir.value = "asc";
    }
  }

  function sortValue(t, key) {
    if (key === "prioridad") return PRIORITY_RANK[t.prioridad] ?? -1;
    if (key === "created_at" || key === "updated_at") return new Date(t[key]).getTime();
    return (t[key] ?? "").toString().toLowerCase();
  }

  const result = computed(() => {
    let list = [...unref(ticketsRef)];
    if (estado.value) list = list.filter((t) => t.estado === estado.value);
    if (prioridad.value) list = list.filter((t) => t.prioridad === prioridad.value);
    if (asignado.value === "none") {
      list = list.filter((t) => !t.asignado_a);
    } else if (asignado.value) {
      list = list.filter((t) => String(t.asignado_a) === String(asignado.value));
    }
    const key = sortKey.value;
    const dir = sortDir.value === "asc" ? 1 : -1;
    list.sort((a, b) => {
      const va = sortValue(a, key);
      const vb = sortValue(b, key);
      if (va < vb) return -1 * dir;
      if (va > vb) return 1 * dir;
      return 0;
    });
    return list;
  });

  return { estado, prioridad, asignado, sortKey, sortDir, toggleSort, result };
}
```

- [ ] **Step 2: Verificar build (import válido)**

Run: `cd frontend; npm run build`
Expected: build limpio (el composable aún no se usa; sólo se valida que compila).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useTicketFilters.js
git commit -m "feat(frontend): composable useTicketFilters (filtro + orden client-side)"
```

---

## Task 8: Frontend — filtros + orden en la tabla de Admin

**Files:**
- Modify: `frontend/src/views/dashboards/AdminDashboard.vue`

**Interfaces:**
- Consumes: `useTicketFilters` (T7).

- [ ] **Step 1: Cablear el composable y reemplazar filteredTickets**

En `frontend/src/views/dashboards/AdminDashboard.vue` `<script setup>`:
- Importar: `import { useTicketFilters } from "../../composables/useTicketFilters.js";`
  (nota: el archivo es `useTicketFilters.js`; respetar el casing exacto del import.)
- Después de `const tickets = ref([]);`, crear el filtro sobre una computed que combina la búsqueda existente:
```javascript
import { useTicketFilters } from "../../composables/useTicketFilters.js";

const searchedTickets = computed(() => {
  const q = ticketSearch.value.toLowerCase();
  return q
    ? tickets.value.filter(
        (t) => t.titulo.toLowerCase().includes(q) || t.reference.toLowerCase().includes(q)
      )
    : tickets.value;
});

const tf = useTicketFilters(searchedTickets);
```
- Reemplazar el uso de `filteredTickets` en el template por `tf.result`. Borrar la `const filteredTickets` anterior (queda sustituida por `searchedTickets` + `tf.result`).

- [ ] **Step 2: Agregar la barra de filtros y headers ordenables al template**

En el bloque `v-if="activeTab === 'tickets'"`, dentro de `.toolbar` (después del `search-input`), agregar los selects de filtro:
```html
          <select v-model="tf.estado.value" class="inline-select">
            <option value="">Estado: todos</option>
            <option value="OPEN">Abierto</option>
            <option value="IN_PROGRESS">En proceso</option>
            <option value="RESOLVED">Resuelto</option>
            <option value="CLOSED">Cerrado</option>
          </select>
          <select v-model="tf.prioridad.value" class="inline-select">
            <option value="">Prioridad: todas</option>
            <option value="LOW">Baja</option>
            <option value="MEDIUM">Media</option>
            <option value="HIGH">Alta</option>
            <option value="URGENT">Urgente</option>
          </select>
          <select v-model="tf.asignado.value" class="inline-select">
            <option value="">Asignado: todos</option>
            <option value="none">Sin asignar</option>
            <option v-for="a in agents" :key="a.id" :value="String(a.id)">{{ a.username }}</option>
          </select>
```
Reemplazar el `<thead>` de la tabla de tickets por headers clickeables:
```html
            <thead>
              <tr>
                <th class="th-sort" @click="tf.toggleSort('reference')">Referencia <span class="sort-ind">{{ sortInd('reference') }}</span></th>
                <th>Título</th>
                <th class="th-sort" @click="tf.toggleSort('estado')">Estado <span class="sort-ind">{{ sortInd('estado') }}</span></th>
                <th class="th-sort" @click="tf.toggleSort('prioridad')">Prioridad <span class="sort-ind">{{ sortInd('prioridad') }}</span></th>
                <th>Creado por</th>
                <th>Asignado a</th>
                <th class="th-sort" @click="tf.toggleSort('created_at')">Fecha <span class="sort-ind">{{ sortInd('created_at') }}</span></th>
                <th>Asignar agente</th>
              </tr>
            </thead>
```
En `<tbody>` reemplazar `filteredTickets` por `tf.result` en el `v-for` y el `v-if` de fila vacía (y `colspan="8"` porque ahora hay 8 columnas). Agregar la celda de fecha antes de "Asignar agente":
```html
              <tr v-if="tf.result.length === 0"><td colspan="8" class="empty-cell">Sin resultados.</td></tr>
              <tr v-for="t in tf.result" :key="t.id">
                ...
                <td class="mono">{{ formatDate(t.created_at) }}</td>
                <td> ... (el select de asignar agente que ya existe) ... </td>
              </tr>
```

- [ ] **Step 3: Agregar el helper sortInd, formatDate y estilos**

En `<script setup>`:
```javascript
function sortInd(key) {
  if (tf.sortKey.value !== key) return "";
  return tf.sortDir.value === "asc" ? "▲" : "▼";
}
function formatDate(iso) {
  try { return new Date(iso).toLocaleDateString("es-MX", { day: "2-digit", month: "2-digit", year: "2-digit" }); }
  catch { return ""; }
}
```
En `<style scoped>`:
```css
.th-sort { cursor: pointer; user-select: none; }
.th-sort:hover { color: var(--text); }
.sort-ind { font-size: 9px; color: var(--accent); }
```

- [ ] **Step 4: Verificar build**

Run: `cd frontend; npm run build`
Expected: build limpio.

- [ ] **Step 5: Verificación manual**

En el dashboard de Admin: filtrar por estado/prioridad/asignado (se combinan con la búsqueda); click en los headers Referencia/Estado/Prioridad/Fecha alterna asc/desc con indicador ▲/▼.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/dashboards/AdminDashboard.vue
git commit -m "feat(frontend): filtros + orden por columnas en la tabla de Admin"
```

---

## Task 9: Frontend — filtros + orden en la lista del Técnico

**Files:**
- Modify: `frontend/src/views/dashboards/TechnicianDashboard.vue`

**Interfaces:**
- Consumes: `useTicketFilters` (T7).

- [ ] **Step 1: Cablear el composable sobre "mine"**

En `frontend/src/views/dashboards/TechnicianDashboard.vue` `<script setup>`:
```javascript
import { useTicketFilters } from "../../composables/useTicketFilters.js";

const tf = useTicketFilters(mine);
```
(`mine` es el `ref` de tickets asignados.)

- [ ] **Step 2: Agregar controles de filtro/orden y usar tf.result en la lista**

En el bloque `v-if="activeTab === 'mine'"`, antes de `<aside class="ticket-list">`, agregar una barra de controles:
```html
        <div class="mine-controls">
          <select v-model="tf.estado.value" class="inline-select">
            <option value="">Estado: todos</option>
            <option value="OPEN">Abierto</option>
            <option value="IN_PROGRESS">En proceso</option>
            <option value="RESOLVED">Resuelto</option>
            <option value="CLOSED">Cerrado</option>
          </select>
          <select v-model="tf.prioridad.value" class="inline-select">
            <option value="">Prioridad: todas</option>
            <option value="LOW">Baja</option>
            <option value="MEDIUM">Media</option>
            <option value="HIGH">Alta</option>
            <option value="URGENT">Urgente</option>
          </select>
          <select :value="tf.sortKey.value" @change="tf.toggleSort($event.target.value)" class="inline-select">
            <option value="prioridad">Orden: prioridad</option>
            <option value="created_at">Orden: fecha</option>
          </select>
        </div>
```
En el `v-for` de `.ticket-item`, reemplazar `mine` por `tf.result` y el `v-if` de vacío por `tf.result.length === 0`.

Nota: el `.main-area` usa un grid; envolver los controles + el aside en un contenedor de columna. Cambiar el contenedor del tab "mine" para que los controles queden arriba de la lista:
```html
      <div v-if="activeTab === 'mine'" class="main-area">
        <div class="mine-col">
          <div class="mine-controls"> ... (los selects de arriba) ... </div>
          <aside class="ticket-list"> ... </aside>
        </div>
        <main class="chat-area"> ... </main>
      </div>
```

- [ ] **Step 3: Ajustar estilos**

En `<style scoped>`, ajustar el grid y agregar los estilos de controles:
```css
.mine-col { display: flex; flex-direction: column; gap: 8px; min-height: 0; }
.mine-col .ticket-list { flex: 1; }
.mine-controls { display: flex; gap: 6px; flex-shrink: 0; }
.mine-controls .inline-select {
  flex: 1;
  padding: 6px 8px;
  border: 0.5px solid var(--border);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  color: var(--text);
  font-size: 12px;
}
```
(La regla `.main-area { grid-template-columns: 320px 1fr; }` sigue valiendo: la primera columna ahora es `.mine-col` en vez de `.ticket-list` directo.)

- [ ] **Step 4: Verificar build**

Run: `cd frontend; npm run build`
Expected: build limpio.

- [ ] **Step 5: Verificación manual**

En el dashboard de Técnico, tab "Mis tickets": filtrar por estado/prioridad y cambiar el orden (prioridad/fecha) reordena la lista. El tab "Pool" queda intacto. El chat sigue funcionando al seleccionar un ticket.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/dashboards/TechnicianDashboard.vue
git commit -m "feat(frontend): filtros + orden en la lista Mis tickets del Técnico"
```

---

## Self-Review (completado por el autor del plan)

**Spec coverage:**
- Modelo + validador de adjunto → Task 1. Regla de acceso reutilizable + payload/serializer → Task 2. Upload REST + broadcast + notificación → Task 3. Download protegido → Task 4. Composer + API front → Task 5. Render (imagen fetch-blob + chip PDF) → Task 6. Composable filtros/orden → Task 7. Admin tabla → Task 8. Técnico lista → Task 9. ✔ Todas las secciones del spec tienen tarea.

**Placeholders:** ninguno — código completo en cada paso.

**Type consistency:** `attachment_payload`/`message_to_payload` (T2) consumidos por el serializer (T2), el upload (T3) y el front vía el objeto `attachment` con claves `name/size/content_type/is_image/url` (T5/T6). `can_access_ticket(user, ticket)` usado en T3/T4. `useTicketFilters(ticketsRef)` → `{estado, prioridad, asignado, sortKey, sortDir, toggleSort, result}` usado consistentemente en T8/T9. La `url` del adjunto (`/api/tickets_t/<id>/attachments/<mid>/download/`) coincide entre payload (T2) y endpoint (T4). Import del composable respeta el casing `useTicketFilters.js`.

## Notas de riesgo (para el review)
- **Cookie cross-origin en descargas:** el flujo fetch-blob (axios `withCredentials`) es el camino confiable; un `<img src>` directo al endpoint fallaría la auth (SameSite=Lax no manda cookie en subrecurso cross-site). Verificado en el diseño; el plan usa fetch-blob en T6.
- **`@action` con regex en `url_path`** (T4): DRF pasa el grupo nombrado `message_id` como kwarg a la acción — patrón soportado; el test de download lo ejercita end-to-end.
- **Doble notificación:** el upload dispara `dispatch("new_message")` una vez; el path WS de texto sigue disparándola en `create_message`. No hay doble para un mismo mensaje (son mensajes distintos).

## Execution Handoff

Dos opciones de ejecución:
1. **Subagent-Driven (recomendada)** — un subagente fresco por tarea, review entre tareas.
2. **Inline** — ejecutar en esta sesión con checkpoints.
