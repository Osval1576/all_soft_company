# Dashboards v2 · Fase 2 — Comunicación · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Notificaciones in-app (toast + centro persistido con campanita) y por email (SMTP, opt-out granular) para todos los actores del help-desk.

**Architecture:** Una app Django nueva `notifications/` con modelos `Notification` y `NotificationPreference`, un dispatcher explícito (`services.dispatch`) invocado desde los dos únicos embudos de eventos (el helper `_emit` del `TicketViewSet` vía `transaction.on_commit`, y `create_message` del `TicketChatConsumer`). Un consumer WS por-usuario (`ws/notify/`) transporta los toasts y trackea presence en cache. El frontend tiene un store Pinia dueño del socket, un `ToastContainer` persistente en `App.vue`, una campanita en `AppTopBar` y una pantalla de preferencias.

**Tech Stack:** Django 6 + DRF + Channels, Vue 3.5 + Pinia, cache LocMemCache (presence), SMTP (Mailtrap dev / console fallback).

## Global Constraints

- Backend models/campos existentes en español (app `tickets_t`); la app `notifications` usa nombres en inglés para modelos/campos y **copy visible en español rioplatense (voseo)**.
- Roles: `CUSTOMER`, `AGENT`, `ADMIN`. "Admin" a efectos de notificación = `is_superuser` **o** `role == "ADMIN"`. "Técnico/pool" = `role == "AGENT"`.
- Estética v2: bordes hairline `0.5px`, palette azul eléctrico (`#0038FF` light / `#5B7CFF` dark, cyan `#00E5FF`), tipografía Space Grotesk / Inter / JetBrains Mono, sin sombras pesadas. Usar variables CSS existentes (`--accent`, `--surface`, `--border`, `--text`, etc.).
- WS auth ya resuelto por `JwtCookieAuthMiddleware` (cookie `access`). Consumers nuevos la heredan.
- Channels `InMemoryChannelLayer` y cache `LocMemCache`: asumimos **mono-proceso** (runserver) hasta el sub-proyecto G (Redis).
- Tests backend con `django.test.TestCase` + `rest_framework.test.APIClient` + `force_authenticate`, siguiendo `backend/tickets_t/tests.py`. Correr con `python backend/manage.py test notifications -v 2`.
- Frontend sin runner de tests: la verificación de cada tarea de front es `npm run build` limpio + checklist manual.
- Email en tests: determinístico vía `@override_settings(NOTIFICATIONS_EMAIL_ASYNC=False)` + `django.core.mail.outbox`.

---

## File Structure

**Backend (nueva app `notifications/`):**
- `backend/notifications/__init__.py` — app package
- `backend/notifications/apps.py` — AppConfig
- `backend/notifications/models.py` — `Notification`, `NotificationPreference`
- `backend/notifications/presence.py` — helpers de presence sobre cache
- `backend/notifications/emails.py` — `send_notification_email`
- `backend/notifications/services.py` — `dispatch`, `notify_for_event`, `_recipients_for`
- `backend/notifications/consumers.py` — `NotifyConsumer`
- `backend/notifications/routing.py` — `websocket_urlpatterns`
- `backend/notifications/serializers.py` — serializers DRF
- `backend/notifications/views.py` — `NotificationViewSet`, `NotificationPreferenceView`
- `backend/notifications/urls.py` — router + preferences path
- `backend/notifications/migrations/` — migraciones
- `backend/notifications/tests.py` — tests

**Backend (modificados):**
- `backend/config/settings.py` — INSTALLED_APPS, email config, CACHES, flag async
- `backend/config/urls.py` — include de `notifications.urls`
- `backend/config/asgi.py` — sumar routing de notify
- `backend/tickets_t/views.py` — `_emit` invoca `notify_for_event`
- `backend/tickets_t/consumers.py` — `create_message` invoca `dispatch("new_message", ...)`

**Frontend (nuevos):**
- `frontend/src/api/notifications.api.js`
- `frontend/src/stores/notifications.store.js`
- `frontend/src/components/notifications/ToastContainer.vue`
- `frontend/src/components/notifications/NotificationBell.vue`
- `frontend/src/views/settings/NotificationSettings.vue`

**Frontend (modificados):**
- `frontend/src/App.vue` — monta ToastContainer + lifecycle del store
- `frontend/src/components/AppTopBar.vue` — campanita + link a ajustes
- `frontend/src/components/ChatPanel.vue` — setea `activeTicketId`
- `frontend/src/router/index.js` — ruta de ajustes

---

## Task 1: App `notifications` + modelos

**Files:**
- Create: `backend/notifications/__init__.py`, `backend/notifications/apps.py`, `backend/notifications/models.py`, `backend/notifications/tests.py`
- Modify: `backend/config/settings.py` (INSTALLED_APPS)

**Interfaces:**
- Produces: `Notification(recipient, kind, ticket, actor, title, body, is_read, created_at)`; `Notification.Kind` con `TICKET_CREATED="ticket_created"`, `ASSIGNED="assigned"`, `NEW_MESSAGE="new_message"`, `STATUS_CHANGED="status_changed"`. `NotificationPreference(user, email_on_assigned, email_on_new_message, email_on_status_changed, email_on_ticket_created)` + classmethod `for_user(user) -> NotificationPreference`.

- [ ] **Step 1: Crear el package y AppConfig**

`backend/notifications/__init__.py`: archivo vacío.

`backend/notifications/apps.py`:
```python
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"
```

- [ ] **Step 2: Registrar la app en settings**

En `backend/config/settings.py`, dentro de `INSTALLED_APPS`, agregar `"notifications",` justo después de `"tickets_t",`:
```python
    "users",
    "tickets_t",
    "notifications",
    "channels",
```

- [ ] **Step 3: Escribir el test que falla (modelos + defaults)**

`backend/notifications/tests.py`:
```python
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
```

- [ ] **Step 4: Correr el test para verificar que falla**

Run: `python backend/manage.py test notifications -v 2`
Expected: FAIL (ImportError: cannot import name 'Notification').

- [ ] **Step 5: Implementar los modelos**

`backend/notifications/models.py`:
```python
from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        TICKET_CREATED = "ticket_created", "Ticket creado"
        ASSIGNED = "assigned", "Asignado"
        NEW_MESSAGE = "new_message", "Nuevo mensaje"
        STATUS_CHANGED = "status_changed", "Cambio de estado"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    ticket = models.ForeignKey(
        "tickets_t.Ticket", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        return f"{self.kind} -> {self.recipient_id}"


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notif_prefs"
    )
    email_on_assigned = models.BooleanField(default=True)
    email_on_new_message = models.BooleanField(default=True)
    email_on_status_changed = models.BooleanField(default=True)
    email_on_ticket_created = models.BooleanField(default=True)

    @classmethod
    def for_user(cls, user):
        obj, _ = cls.objects.get_or_create(user=user)
        return obj

    def __str__(self):
        return f"prefs<{self.user_id}>"
```

- [ ] **Step 6: Generar migración**

Run: `python backend/manage.py makemigrations notifications`
Expected: crea `0001_initial.py` con ambos modelos.

- [ ] **Step 7: Correr los tests para verificar que pasan**

Run: `python backend/manage.py test notifications -v 2`
Expected: PASS (3 tests).

- [ ] **Step 8: Commit**

```bash
git add backend/notifications backend/config/settings.py
git commit -m "feat(notifications): app + Notification/NotificationPreference models"
```

---

## Task 2: Presence tracking (cache)

**Files:**
- Create: `backend/notifications/presence.py`
- Modify: `backend/config/settings.py` (CACHES)
- Test: `backend/notifications/tests.py`

**Interfaces:**
- Produces: `mark_online(user_id)`, `is_online(user_id) -> bool`, `mark_offline(user_id)`. TTL `PRESENCE_TTL = 60`.

- [ ] **Step 1: Configurar cache LocMem en settings**

Al final de `backend/config/settings.py` agregar:
```python
# Cache (presence de notificaciones). LocMem hoy; Redis en sub-proyecto G.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "allsafe-default",
    }
}
```

- [ ] **Step 2: Escribir el test que falla**

Agregar a `backend/notifications/tests.py`:
```python
from notifications.presence import mark_online, is_online, mark_offline


class PresenceTests(TestCase):
    def test_online_lifecycle(self):
        self.assertFalse(is_online(999))
        mark_online(999)
        self.assertTrue(is_online(999))
        mark_offline(999)
        self.assertFalse(is_online(999))
```

- [ ] **Step 3: Correr el test para verificar que falla**

Run: `python backend/manage.py test notifications.tests.PresenceTests -v 2`
Expected: FAIL (ModuleNotFoundError: notifications.presence).

- [ ] **Step 4: Implementar presence.py**

`backend/notifications/presence.py`:
```python
from django.core.cache import cache

PRESENCE_TTL = 60  # segundos


def _key(user_id):
    return f"presence:user:{user_id}"


def mark_online(user_id):
    cache.set(_key(user_id), True, PRESENCE_TTL)


def is_online(user_id):
    return bool(cache.get(_key(user_id)))


def mark_offline(user_id):
    cache.delete(_key(user_id))
```

- [ ] **Step 5: Correr el test para verificar que pasa**

Run: `python backend/manage.py test notifications.tests.PresenceTests -v 2`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/notifications/presence.py backend/config/settings.py backend/notifications/tests.py
git commit -m "feat(notifications): presence tracking sobre cache LocMem"
```

---

## Task 3: Config de email + helper de envío

**Files:**
- Create: `backend/notifications/emails.py`
- Modify: `backend/config/settings.py` (email + flag async)
- Test: `backend/notifications/tests.py`

**Interfaces:**
- Produces: `send_notification_email(recipient, subject, body)` — no-op si `recipient.email` vacío; usa `settings.DEFAULT_FROM_EMAIL`, `fail_silently=True`.
- Settings nuevos: `EMAIL_BACKEND` (SMTP si `EMAIL_HOST` en env, si no console), `DEFAULT_FROM_EMAIL`, `NOTIFICATIONS_EMAIL_ASYNC = True`.

- [ ] **Step 1: Configurar email en settings**

Al final de `backend/config/settings.py` agregar:
```python
import os

# Email: Mailtrap (u otro SMTP) por env en dev; console si no hay EMAIL_HOST.
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "AllSafe <no-reply@allsafe.local>")

# Envío de emails en thread daemon (no bloquea WS/request). En tests se pone False.
NOTIFICATIONS_EMAIL_ASYNC = True
```

- [ ] **Step 2: Escribir el test que falla**

Agregar a `backend/notifications/tests.py`:
```python
from django.core import mail
from notifications.emails import send_notification_email


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
```

- [ ] **Step 3: Correr el test para verificar que falla**

Run: `python backend/manage.py test notifications.tests.EmailHelperTests -v 2`
Expected: FAIL (ModuleNotFoundError: notifications.emails).

- [ ] **Step 4: Implementar emails.py**

`backend/notifications/emails.py`:
```python
from django.conf import settings
from django.core.mail import send_mail


def send_notification_email(recipient, subject, body):
    email = getattr(recipient, "email", "")
    if not email:
        return
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=True,
    )
```

- [ ] **Step 5: Correr el test para verificar que pasa**

Run: `python backend/manage.py test notifications.tests.EmailHelperTests -v 2`
Expected: PASS (2 tests). (El test runner de Django fuerza el backend locmem, así `mail.outbox` funciona.)

- [ ] **Step 6: Commit**

```bash
git add backend/notifications/emails.py backend/config/settings.py backend/notifications/tests.py
git commit -m "feat(notifications): config de email por env + helper send_notification_email"
```

---

## Task 4: Dispatcher (`services.dispatch`)

**Files:**
- Create: `backend/notifications/services.py`
- Test: `backend/notifications/tests.py`

**Interfaces:**
- Consumes: `Notification`, `NotificationPreference.for_user` (Task 1); `is_online` (Task 2); `send_notification_email` (Task 3).
- Produces:
  - `dispatch(kind, ticket, actor=None, extra=None)` — crea `Notification` por destinatario (excluye al `actor`), hace `group_send("user_{id}", {"type": "notify.message", "data": {...}})`, y envía email según preferencia (+ presence para `new_message`).
  - `notify_for_event(ticket, event_kind, actor, payload=None)` — mapea un `event_kind` de `TicketEvent` a `dispatch(...)` vía `transaction.on_commit`.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `backend/notifications/tests.py`:
```python
from django.test import override_settings
from notifications.services import dispatch
from notifications.models import Notification, NotificationPreference
from notifications.presence import mark_online


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
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `python backend/manage.py test notifications.tests.DispatchTests -v 2`
Expected: FAIL (ModuleNotFoundError: notifications.services).

- [ ] **Step 3: Implementar services.py**

`backend/notifications/services.py`:
```python
import threading

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction

from .emails import send_notification_email
from .models import Notification, NotificationPreference
from .presence import is_online

User = get_user_model()

STATUS_LABELS = {
    "OPEN": "Abierto", "IN_PROGRESS": "En proceso",
    "RESOLVED": "Resuelto", "CLOSED": "Cerrado",
}


def _admins():
    return User.objects.filter(models.Q(is_superuser=True) | models.Q(role="ADMIN"))


def _agents():
    return User.objects.filter(role="AGENT")


def _push(user_id, notification):
    layer = get_channel_layer()
    if layer is None:
        return
    payload = {
        "type": "notify.message",
        "data": {
            "id": notification.id,
            "kind": notification.kind,
            "ticket": notification.ticket_id,
            "title": notification.title,
            "body": notification.body,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
        },
    }
    try:
        async_to_sync(layer.group_send)(f"user_{user_id}", payload)
    except Exception:
        pass


def _send_email(recipient, subject, body):
    if getattr(settings, "NOTIFICATIONS_EMAIL_ASYNC", True):
        threading.Thread(
            target=send_notification_email, args=(recipient, subject, body), daemon=True
        ).start()
    else:
        send_notification_email(recipient, subject, body)


def _recipients_for(kind, ticket, actor, extra):
    """Devuelve una lista de dicts:
    {user, title, body, email(bool), pref_field(str), subject, email_body, offline_only(bool)}
    """
    ref = ticket.reference
    specs = []

    if kind == "ticket_created":
        for admin in _admins():
            specs.append({
                "user": admin,
                "title": f"Nuevo ticket {ref}",
                "body": ticket.titulo,
                "email": True,
                "pref_field": "email_on_ticket_created",
                "subject": f"[AllSafe] Nuevo ticket {ref}",
                "email_body": f"Entró un ticket nuevo: {ref} — {ticket.titulo}.",
                "offline_only": False,
            })
        for agent in _agents():
            specs.append({
                "user": agent, "title": f"Ticket sin asignar: {ref}",
                "body": ticket.titulo, "email": False, "pref_field": None,
                "subject": "", "email_body": "", "offline_only": False,
            })

    elif kind == "assigned":
        if ticket.creado_por_id:
            specs.append({
                "user": ticket.creado_por,
                "title": f"Tu ticket {ref} fue asignado",
                "body": "Un técnico se está ocupando de tu caso.",
                "email": True, "pref_field": "email_on_assigned",
                "subject": f"[AllSafe] Tu ticket {ref} fue asignado",
                "email_body": f"Tu ticket {ref} ya tiene un técnico asignado. Pronto vas a tener novedades.",
                "offline_only": False,
            })
        if ticket.asignado_a_id:
            specs.append({
                "user": ticket.asignado_a,
                "title": f"Se te asignó el ticket {ref}",
                "body": ticket.titulo, "email": False, "pref_field": None,
                "subject": "", "email_body": "", "offline_only": False,
            })

    elif kind == "new_message":
        preview = (extra or {}).get("content", "")
        for user in (ticket.creado_por, ticket.asignado_a):
            if not user:
                continue
            specs.append({
                "user": user,
                "title": f"Nuevo mensaje en {ref}",
                "body": preview[:120],
                "email": True, "pref_field": "email_on_new_message",
                "subject": f"[AllSafe] Nuevo mensaje en tu ticket {ref}",
                "email_body": f"Tenés un mensaje nuevo en el ticket {ref}. Entrá a AllSafe para responder.",
                "offline_only": True,
            })

    elif kind == "status_changed":
        if ticket.creado_por_id:
            label = STATUS_LABELS.get(ticket.estado, ticket.estado)
            specs.append({
                "user": ticket.creado_por,
                "title": f"Tu ticket {ref} cambió de estado",
                "body": f"Ahora está: {label}.",
                "email": True, "pref_field": "email_on_status_changed",
                "subject": f"[AllSafe] Tu ticket {ref} ahora está {label}",
                "email_body": f"El estado de tu ticket {ref} cambió a: {label}.",
                "offline_only": False,
            })

    return specs


def dispatch(kind, ticket, actor=None, extra=None):
    actor_id = actor.id if actor else None
    for spec in _recipients_for(kind, ticket, actor, extra):
        user = spec["user"]
        if actor_id and user.id == actor_id:
            continue
        notif = Notification.objects.create(
            recipient=user, kind=kind, ticket=ticket, actor=actor,
            title=spec["title"], body=spec.get("body", ""),
        )
        _push(user.id, notif)
        if not spec.get("email"):
            continue
        if spec.get("offline_only") and is_online(user.id):
            continue
        prefs = NotificationPreference.for_user(user)
        if getattr(prefs, spec["pref_field"], True):
            _send_email(user, spec["subject"], spec["email_body"])


EVENT_TO_KIND = {"created": "ticket_created", "assigned": "assigned"}


def notify_for_event(ticket, event_kind, actor, payload=None):
    payload = payload or {}

    def _run():
        if event_kind in ("status_changed", "reopened"):
            if ticket.estado in ("RESOLVED", "CLOSED"):
                dispatch("status_changed", ticket, actor, payload)
            return
        mapped = EVENT_TO_KIND.get(event_kind)
        if mapped:
            dispatch(mapped, ticket, actor, payload)

    transaction.on_commit(_run)
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `python backend/manage.py test notifications.tests.DispatchTests -v 2`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/notifications/services.py backend/notifications/tests.py
git commit -m "feat(notifications): dispatcher con matriz de destinatarios, presence y email"
```

---

## Task 5: Consumer WS `ws/notify/` + routing

**Files:**
- Create: `backend/notifications/consumers.py`, `backend/notifications/routing.py`
- Modify: `backend/config/asgi.py`
- Test: `backend/notifications/tests.py`

**Interfaces:**
- Consumes: `mark_online`, `mark_offline` (Task 2).
- Produces: `NotifyConsumer` en `ws/notify/`; grupo `user_{id}`; handler `notify_message`; refresca presence en `connect` y en `{"type":"ping"}`; limpia en `disconnect`.

- [ ] **Step 1: Escribir el test async que falla (auth + presence en connect)**

Agregar a `backend/notifications/tests.py`:
```python
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from config.asgi import application
from notifications.presence import is_online
from rest_framework_simplejwt.tokens import AccessToken


class NotifyConsumerTests(TestCase):
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
```

Note: `TestCase` corre estos métodos async vía el runner de Django (soporta `async def` test methods). El middleware `JwtCookieAuthMiddleware` lee la cookie `access` del header.

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `python backend/manage.py test notifications.tests.NotifyConsumerTests -v 2`
Expected: FAIL (ImportError: NotifyConsumer / ruta inexistente).

- [ ] **Step 3: Implementar el consumer**

`backend/notifications/consumers.py`:
```python
import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from .presence import mark_online, mark_offline


class NotifyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.user_id = user.id
        self.group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._mark_online()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if hasattr(self, "user_id"):
            await self._mark_offline()

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data or "{}")
        if data.get("type") == "ping":
            await self._mark_online()

    async def notify_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    @database_sync_to_async
    def _mark_online(self):
        mark_online(self.user_id)

    @database_sync_to_async
    def _mark_offline(self):
        mark_offline(self.user_id)
```

- [ ] **Step 4: Crear routing de la app**

`backend/notifications/routing.py`:
```python
from django.urls import re_path
from .consumers import NotifyConsumer

websocket_urlpatterns = [
    re_path(r"^ws/notify/$", NotifyConsumer.as_asgi()),
]
```

- [ ] **Step 5: Sumar el routing en asgi**

Modificar `backend/config/asgi.py` para combinar ambos routers:
```python
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

from tickets_t.routing import websocket_urlpatterns as chat_ws  # noqa: E402
from notifications.routing import websocket_urlpatterns as notify_ws  # noqa: E402
from .ws_auth import JwtCookieAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JwtCookieAuthMiddleware(
            URLRouter(chat_ws + notify_ws)
        ),
    }
)
```

- [ ] **Step 6: Correr el test para verificar que pasa**

Run: `python backend/manage.py test notifications.tests.NotifyConsumerTests -v 2`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add backend/notifications/consumers.py backend/notifications/routing.py backend/config/asgi.py backend/notifications/tests.py
git commit -m "feat(notifications): NotifyConsumer ws/notify/ + presence + routing"
```

---

## Task 6: API REST (listar / leer / preferencias)

**Files:**
- Create: `backend/notifications/serializers.py`, `backend/notifications/views.py`, `backend/notifications/urls.py`
- Modify: `backend/config/urls.py`
- Test: `backend/notifications/tests.py`

**Interfaces:**
- Produces (endpoints, todos bajo `/api/`):
  - `GET /api/notifications/` → lista del usuario (array, sin paginar).
  - `POST /api/notifications/{id}/read/` → marca una leída.
  - `POST /api/notifications/read-all/` → marca todas leídas.
  - `GET /api/notifications/preferences/` y `PATCH` → preferencias del usuario.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `backend/notifications/tests.py`:
```python
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
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `python backend/manage.py test notifications.tests.ApiTests -v 2`
Expected: FAIL (404 en las rutas — no existen).

- [ ] **Step 3: Implementar serializers**

`backend/notifications/serializers.py`:
```python
from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "ticket", "actor", "title", "body", "is_read", "created_at"]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "email_on_assigned",
            "email_on_new_message",
            "email_on_status_changed",
            "email_on_ticket_created",
        ]
```

- [ ] **Step 4: Implementar views**

`backend/notifications/views.py`:
```python
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, NotificationPreference
from .serializers import NotificationSerializer, NotificationPreferenceSerializer


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=["post"], url_path="read")
    def read(self, request, pk=None):
        n = self.get_queryset().filter(pk=pk).first()
        if not n:
            return Response({"detail": "No encontrada."}, status=404)
        if not n.is_read:
            n.is_read = True
            n.save(update_fields=["is_read"])
        return Response(NotificationSerializer(n).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"status": "ok"})


class NotificationPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prefs = NotificationPreference.for_user(request.user)
        return Response(NotificationPreferenceSerializer(prefs).data)

    def patch(self, request):
        prefs = NotificationPreference.for_user(request.user)
        ser = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)
```

- [ ] **Step 5: Implementar urls**

`backend/notifications/urls.py`:
```python
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet, NotificationPreferenceView

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notifications")

# La ruta de preferences va ANTES del router para que no matchee como detail pk.
urlpatterns = [
    path("notifications/preferences/", NotificationPreferenceView.as_view()),
] + router.urls
```

- [ ] **Step 6: Incluir en config/urls**

En `backend/config/urls.py`, dentro de `urlpatterns`, agregar debajo de la línea de `tickets_t.urls`:
```python
    path("api/", include("tickets_t.urls")),
    path("api/", include("notifications.urls")),
```

- [ ] **Step 7: Correr los tests para verificar que pasan**

Run: `python backend/manage.py test notifications.tests.ApiTests -v 2`
Expected: PASS (5 tests).

- [ ] **Step 8: Commit**

```bash
git add backend/notifications/serializers.py backend/notifications/views.py backend/notifications/urls.py backend/config/urls.py backend/notifications/tests.py
git commit -m "feat(notifications): API REST listar/leer/preferencias"
```

---

## Task 7: Cablear el dispatch en los dos embudos

**Files:**
- Modify: `backend/tickets_t/views.py` (`_emit`), `backend/tickets_t/consumers.py` (`create_message`)
- Test: `backend/notifications/tests.py`

**Interfaces:**
- Consumes: `notify_for_event` y `dispatch` (Task 4).

- [ ] **Step 1: Escribir los tests de integración que fallan**

Agregar a `backend/notifications/tests.py`:
```python
@override_settings(NOTIFICATIONS_EMAIL_ASYNC=False)
class IntegrationTests(TestCase):
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
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `python backend/manage.py test notifications.tests.IntegrationTests -v 2`
Expected: FAIL (0 notificaciones creadas — aún no hay cableado).

- [ ] **Step 3: Cablear el viewset**

En `backend/tickets_t/views.py`, modificar el helper `_emit` (líneas 47-48) para disparar la notificación tras registrar el evento:
```python
    # ---- event emission helpers ----
    def _emit(self, ticket, kind, actor, payload=None):
        TicketEvent.objects.create(ticket=ticket, kind=kind, actor=actor, payload=payload or {})
        from notifications.services import notify_for_event
        notify_for_event(ticket, kind, actor, payload or {})
```

- [ ] **Step 4: Cablear el consumer**

En `backend/tickets_t/consumers.py`, dentro de `create_message` (después de crear `m` y antes del `return`, ~línea 90), agregar el dispatch:
```python
        m = TicketMessage.objects.create(
            ticket=ticket,
            sender=user,
            content=content,
        )
        from notifications.services import dispatch
        dispatch("new_message", ticket, actor=user, extra={"content": content})
        return {
            "id": m.id,
            "sender_id": user.id,
            "sender_username": user.username,
            "sender_role": getattr(user, "role", None),
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
```

- [ ] **Step 5: Correr los tests para verificar que pasan**

Run: `python backend/manage.py test notifications.tests.IntegrationTests -v 2`
Expected: PASS (2 tests).

- [ ] **Step 6: Correr toda la suite backend (regresión)**

Run: `python backend/manage.py test -v 1`
Expected: PASS — 44 previos + los nuevos de `notifications`.

- [ ] **Step 7: Commit**

```bash
git add backend/tickets_t/views.py backend/tickets_t/consumers.py backend/notifications/tests.py
git commit -m "feat(notifications): cablear dispatch en _emit (on_commit) y create_message"
```

---

## Task 8: Frontend — API client + store Pinia

**Files:**
- Create: `frontend/src/api/notifications.api.js`, `frontend/src/stores/notifications.store.js`

**Interfaces:**
- Produces:
  - api: `listNotifications()`, `markRead(id)`, `markAllRead()`, `getNotifPreferences()`, `updateNotifPreferences(data)`.
  - store `useNotificationsStore`: state `{ connected, unreadCount, items, toasts, activeTicketId }`; actions `init()`, `disconnect()`, `setActiveTicket(id)`, `markRead(id)`, `markAllRead()`, `dismissToast(id)`.

- [ ] **Step 1: Implementar el API client**

`frontend/src/api/notifications.api.js`:
```javascript
import { http } from "./http";

export async function listNotifications() {
  const res = await http.get("/api/notifications/");
  return res.data;
}

export async function markRead(id) {
  const res = await http.post(`/api/notifications/${id}/read/`);
  return res.data;
}

export async function markAllRead() {
  await http.post("/api/notifications/read-all/");
}

export async function getNotifPreferences() {
  const res = await http.get("/api/notifications/preferences/");
  return res.data;
}

export async function updateNotifPreferences(data) {
  const res = await http.patch("/api/notifications/preferences/", data);
  return res.data;
}
```

- [ ] **Step 2: Implementar el store**

`frontend/src/stores/notifications.store.js`. El socket y los timers viven en variables de módulo (no en el state) para que Vue no los envuelva en proxies reactivos:
```javascript
import { defineStore } from "pinia";
import {
  listNotifications,
  markRead as apiMarkRead,
  markAllRead as apiMarkAllRead,
} from "../api/notifications.api";

const BACKOFFS_MS = [1000, 2000, 4000, 8000, 16000];

let socket = null;
let attempts = 0;
let retryTimer = null;
let pingTimer = null;
let closedByUser = false;
let toastSeq = 0;

export const useNotificationsStore = defineStore("notifications", {
  state: () => ({
    connected: false,
    unreadCount: 0,
    items: [],
    toasts: [],
    activeTicketId: null,
  }),

  actions: {
    async init() {
      await this.loadHistory();
      this.connect();
    },

    async loadHistory() {
      try {
        const data = await listNotifications();
        this.items = data;
        this.unreadCount = data.filter((n) => !n.is_read).length;
      } catch (_) {}
    },

    connect() {
      if (socket && socket.readyState !== WebSocket.CLOSED) return;
      closedByUser = false;
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = import.meta.env.VITE_WS_HOST || window.location.host;
      let s;
      try {
        s = new WebSocket(`${proto}//${host}/ws/notify/`);
      } catch (_) {
        this._scheduleRetry();
        return;
      }
      socket = s;
      s.onopen = () => {
        this.connected = true;
        attempts = 0;
        this._startPing();
      };
      s.onmessage = (evt) => {
        try {
          this._onMessage(JSON.parse(evt.data));
        } catch (_) {}
      };
      s.onclose = () => {
        this.connected = false;
        this._stopPing();
        if (!closedByUser) this._scheduleRetry();
      };
      s.onerror = () => {};
    },

    _onMessage(n) {
      this.items.unshift(n);
      if (!n.is_read) this.unreadCount += 1;
      // Suprimir el toast del ticket que el usuario está mirando (ya lo ve en vivo).
      if (n.kind === "new_message" && n.ticket && n.ticket === this.activeTicketId) return;
      this._pushToast(n);
    },

    _pushToast(n) {
      const id = ++toastSeq;
      this.toasts.push({ toastId: id, ...n });
      setTimeout(() => this.dismissToast(id), 5000);
    },

    dismissToast(id) {
      this.toasts = this.toasts.filter((t) => t.toastId !== id);
    },

    setActiveTicket(id) {
      this.activeTicketId = id;
    },

    async markRead(id) {
      const n = this.items.find((x) => x.id === id);
      if (n && !n.is_read) {
        n.is_read = true;
        this.unreadCount = Math.max(0, this.unreadCount - 1);
      }
      try {
        await apiMarkRead(id);
      } catch (_) {}
    },

    async markAllRead() {
      this.items.forEach((n) => (n.is_read = true));
      this.unreadCount = 0;
      try {
        await apiMarkAllRead();
      } catch (_) {}
    },

    _startPing() {
      this._stopPing();
      pingTimer = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);
    },

    _stopPing() {
      if (pingTimer) {
        clearInterval(pingTimer);
        pingTimer = null;
      }
    },

    _scheduleRetry() {
      if (attempts >= BACKOFFS_MS.length) return;
      const wait = BACKOFFS_MS[attempts++];
      retryTimer = setTimeout(() => this.connect(), wait);
    },

    disconnect() {
      closedByUser = true;
      this._stopPing();
      if (retryTimer) clearTimeout(retryTimer);
      if (socket) {
        try {
          socket.close();
        } catch (_) {}
      }
      socket = null;
      attempts = 0;
      this.connected = false;
      this.unreadCount = 0;
      this.items = [];
      this.toasts = [];
      this.activeTicketId = null;
    },
  },
});
```

- [ ] **Step 3: Verificar build**

Run: `cd frontend && npm run build`
Expected: build limpio, sin errores de import.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/notifications.api.js frontend/src/stores/notifications.store.js
git commit -m "feat(frontend): notifications api client + Pinia store con socket ws/notify"
```

---

## Task 9: Frontend — ToastContainer + lifecycle en App.vue + activeTicket en ChatPanel

**Files:**
- Create: `frontend/src/components/notifications/ToastContainer.vue`
- Modify: `frontend/src/App.vue`, `frontend/src/components/ChatPanel.vue`

**Interfaces:**
- Consumes: `useNotificationsStore` (Task 8), `useAuthStore`.

- [ ] **Step 1: Implementar ToastContainer**

`frontend/src/components/notifications/ToastContainer.vue`:
```vue
<template>
  <div class="toast-stack" aria-live="polite">
    <TransitionGroup name="toast">
      <button
        v-for="t in store.toasts"
        :key="t.toastId"
        class="toast"
        @click="onClick(t)"
      >
        <span class="toast-dot" aria-hidden="true"></span>
        <span class="toast-body">
          <span class="toast-title">{{ t.title }}</span>
          <span v-if="t.body" class="toast-sub">{{ t.body }}</span>
        </span>
        <span class="toast-close" @click.stop="store.dismissToast(t.toastId)">✕</span>
      </button>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";
import { useNotificationsStore } from "../../stores/notifications.store";
import { useAuthStore } from "../../stores/auth.store";

const store = useNotificationsStore();
const auth = useAuthStore();
const router = useRouter();

function dashboardRoute() {
  if (auth.user?.is_superuser) return { name: "admin" };
  if (auth.user?.is_staff) return { name: "tecnico-inbox" };
  return { name: "cliente" };
}

function onClick(t) {
  store.markRead(t.id);
  store.dismissToast(t.toastId);
  const target = dashboardRoute();
  if (t.ticket) target.query = { ticket: t.ticket };
  router.push(target);
}
</script>

<style scoped>
.toast-stack {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 340px;
}
.toast {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  text-align: left;
  padding: 12px 14px;
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-left: 2px solid var(--accent);
  border-radius: var(--r);
  cursor: pointer;
  color: var(--text);
}
.toast:hover { background: var(--surface-2); }
.toast-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent); margin-top: 5px; flex-shrink: 0;
}
.toast-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.toast-title { font-family: var(--font-display); font-weight: 600; font-size: 13px; }
.toast-sub {
  font-size: 12px; color: var(--text-2);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.toast-close { margin-left: auto; color: var(--text-3); font-size: 12px; }
.toast-enter-active, .toast-leave-active { transition: all .25s ease; }
.toast-enter-from { opacity: 0; transform: translateX(20px); }
.toast-leave-to { opacity: 0; transform: translateX(20px); }
</style>
```

- [ ] **Step 2: Montar ToastContainer + lifecycle del store en App.vue**

`frontend/src/App.vue`:
```vue
<template>
  <router-view />
  <ToastContainer v-if="auth.user" />
</template>

<script setup>
import { watch } from "vue";
import { useAuthStore } from "./stores/auth.store";
import { useNotificationsStore } from "./stores/notifications.store";
import ToastContainer from "./components/notifications/ToastContainer.vue";

const auth = useAuthStore();
const notif = useNotificationsStore();

watch(
  () => auth.user,
  (user, prev) => {
    if (user && !prev) notif.init();
    if (!user && prev) notif.disconnect();
  },
  { immediate: true }
);
</script>
```

- [ ] **Step 3: Setear activeTicketId desde ChatPanel**

En `frontend/src/components/ChatPanel.vue`, importar el store y sincronizar el ticket activo. Agregar al bloque `<script setup>` (después de la línea `const auth = useAuthStore();`, ~línea 89):
```javascript
import { onBeforeUnmount } from "vue";
import { useNotificationsStore } from "../stores/notifications.store";

const notif = useNotificationsStore();
```
Y dentro del `watch(() => props.ticketId, ...)` existente (~línea 158), como primera línea del callback, agregar:
```javascript
  notif.setActiveTicket(props.ticketId);
```
Y al final del `<script setup>` agregar el cleanup:
```javascript
onBeforeUnmount(() => notif.setActiveTicket(null));
```

- [ ] **Step 4: Verificar build**

Run: `cd frontend && npm run build`
Expected: build limpio.

- [ ] **Step 5: Verificación manual**

Con backend (`python backend/manage.py runserver`) + `runserver` ASGI y frontend (`npm run dev`), abrir dos sesiones (cliente y técnico), el técnico manda un mensaje → el cliente ve un toast azul arriba a la derecha (si NO tiene ese ticket abierto). Con el ticket abierto, el toast se suprime pero el mensaje llega en vivo al chat.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/notifications/ToastContainer.vue frontend/src/App.vue frontend/src/components/ChatPanel.vue
git commit -m "feat(frontend): ToastContainer + lifecycle del store + activeTicket en ChatPanel"
```

---

## Task 10: Frontend — Campanita en AppTopBar

**Files:**
- Create: `frontend/src/components/notifications/NotificationBell.vue`
- Modify: `frontend/src/components/AppTopBar.vue`

**Interfaces:**
- Consumes: `useNotificationsStore` (Task 8).

- [ ] **Step 1: Implementar NotificationBell**

`frontend/src/components/notifications/NotificationBell.vue`:
```vue
<template>
  <div class="bell-wrap">
    <button class="bell-btn" @click="toggle" aria-label="Notificaciones">
      <i class="ti ti-bell" aria-hidden="true"></i>
      <span v-if="store.unreadCount > 0" class="bell-badge">{{ badgeText }}</span>
    </button>

    <div v-if="open" class="bell-panel" @click.stop>
      <div class="bell-head">
        <span>Notificaciones</span>
        <button v-if="store.unreadCount > 0" class="bell-readall" @click="store.markAllRead()">
          Marcar todas
        </button>
      </div>
      <div class="bell-list">
        <p v-if="store.items.length === 0" class="bell-empty">Sin novedades.</p>
        <button
          v-for="n in store.items.slice(0, 20)"
          :key="n.id"
          class="bell-item"
          :class="{ 'bell-item--unread': !n.is_read }"
          @click="onItem(n)"
        >
          <span class="bell-item-title">{{ n.title }}</span>
          <span v-if="n.body" class="bell-item-body">{{ n.body }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import { useNotificationsStore } from "../../stores/notifications.store";
import { useAuthStore } from "../../stores/auth.store";

const store = useNotificationsStore();
const auth = useAuthStore();
const router = useRouter();
const open = ref(false);

const badgeText = computed(() => (store.unreadCount > 9 ? "9+" : String(store.unreadCount)));

function toggle() {
  open.value = !open.value;
}

function dashboardRoute() {
  if (auth.user?.is_superuser) return { name: "admin" };
  if (auth.user?.is_staff) return { name: "tecnico-inbox" };
  return { name: "cliente" };
}

function onItem(n) {
  store.markRead(n.id);
  open.value = false;
  const target = dashboardRoute();
  if (n.ticket) target.query = { ticket: n.ticket };
  router.push(target);
}

function onDocClick() {
  open.value = false;
}
onMounted(() => document.addEventListener("click", onDocClick));
onBeforeUnmount(() => document.removeEventListener("click", onDocClick));
</script>

<style scoped>
.bell-wrap { position: relative; }
.bell-btn {
  width: 34px; height: 34px;
  border: 0.5px solid var(--border);
  border-radius: 6px;
  display: grid; place-items: center;
  color: var(--text-2); background: transparent; cursor: pointer;
  position: relative;
}
.bell-btn:hover { background: var(--surface-2); color: var(--text); }
.bell-btn i { font-size: 15px; }
.bell-badge {
  position: absolute; top: -4px; right: -4px;
  min-width: 16px; height: 16px; padding: 0 4px;
  background: var(--accent); color: var(--accent-fg);
  border-radius: 100px; font-size: 9px; font-weight: 700;
  display: grid; place-items: center;
}
.bell-panel {
  position: absolute; top: 42px; right: 0;
  width: 300px; max-height: 380px; overflow-y: auto;
  background: var(--surface); border: 0.5px solid var(--border);
  border-radius: var(--r); z-index: 1001;
}
.bell-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; border-bottom: 0.5px solid var(--border);
  font-family: var(--font-display); font-weight: 600; font-size: 13px;
}
.bell-readall {
  font-size: 11px; color: var(--accent); background: transparent; cursor: pointer;
}
.bell-list { display: flex; flex-direction: column; }
.bell-empty { padding: 16px; text-align: center; color: var(--text-3); font-size: 13px; }
.bell-item {
  display: flex; flex-direction: column; gap: 2px;
  padding: 10px 12px; text-align: left; cursor: pointer;
  border-bottom: 0.5px solid var(--border); background: transparent; color: var(--text);
}
.bell-item:hover { background: var(--surface-2); }
.bell-item--unread { background: var(--accent-light); }
.bell-item-title { font-size: 13px; font-weight: 500; }
.bell-item-body {
  font-size: 12px; color: var(--text-2);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
</style>
```

- [ ] **Step 2: Insertar la campanita en AppTopBar**

En `frontend/src/components/AppTopBar.vue`, en el `<template>`, dentro de `.topbar-right`, agregar la campanita entre `.user-chip` y el botón de theme (después de la línea 18):
```html
      <NotificationBell />
      <button class="tb-theme" @click="toggle" :aria-label="isDark ? 'Modo claro' : 'Modo oscuro'">
```
Y en el `<script setup>` importar el componente (después de la línea 30):
```javascript
import NotificationBell from './notifications/NotificationBell.vue'
```

- [ ] **Step 3: Verificar build**

Run: `cd frontend && npm run build`
Expected: build limpio.

- [ ] **Step 4: Verificación manual**

Login como cualquier rol → aparece la campanita en el topbar. Al recibir una notificación, sube el badge; al abrir el panel se ve el historial; "Marcar todas" baja el badge a 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/notifications/NotificationBell.vue frontend/src/components/AppTopBar.vue
git commit -m "feat(frontend): campanita de notificaciones en AppTopBar"
```

---

## Task 11: Frontend — Pantalla de preferencias de email

**Files:**
- Create: `frontend/src/views/settings/NotificationSettings.vue`
- Modify: `frontend/src/router/index.js`, `frontend/src/components/AppTopBar.vue`

**Interfaces:**
- Consumes: `getNotifPreferences`, `updateNotifPreferences` (Task 8); `useAuthStore` para mostrar sólo los toggles del rol.

- [ ] **Step 1: Implementar la vista de preferencias**

`frontend/src/views/settings/NotificationSettings.vue`:
```vue
<template>
  <div class="page">
    <AppTopBar title="Notificaciones" />
    <div class="wrap">
      <h1 class="title">Preferencias de email</h1>
      <p class="sub">Elegí qué avisos querés recibir por correo. Las notificaciones dentro de la app siempre están activas.</p>

      <div v-if="loading" class="state">Cargando…</div>

      <div v-else class="rows">
        <label v-for="opt in visibleOptions" :key="opt.field" class="row">
          <span class="row-info">
            <span class="row-label">{{ opt.label }}</span>
            <span class="row-desc">{{ opt.desc }}</span>
          </span>
          <input
            type="checkbox"
            :checked="prefs[opt.field]"
            @change="onToggle(opt.field, $event.target.checked)"
          />
        </label>
      </div>

      <p v-if="saved" class="saved">Guardado ✓</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import AppTopBar from "../../components/AppTopBar.vue";
import { useAuthStore } from "../../stores/auth.store";
import { getNotifPreferences, updateNotifPreferences } from "../../api/notifications.api";

const auth = useAuthStore();
const loading = ref(true);
const saved = ref(false);
const prefs = ref({});

const ALL_OPTIONS = [
  { field: "email_on_assigned", label: "Ticket asignado", desc: "Cuando un técnico toma tu ticket.", roles: ["CUSTOMER"] },
  { field: "email_on_new_message", label: "Nuevos mensajes", desc: "Cuando te escriben y no estás conectado.", roles: ["CUSTOMER", "AGENT"] },
  { field: "email_on_status_changed", label: "Cambios de estado", desc: "Cuando tu ticket se resuelve o cierra.", roles: ["CUSTOMER"] },
  { field: "email_on_ticket_created", label: "Tickets nuevos", desc: "Cuando entra un ticket nuevo al sistema.", roles: ["ADMIN"] },
];

const myRole = computed(() => {
  if (auth.user?.is_superuser) return "ADMIN";
  if (auth.user?.is_staff) return "AGENT";
  return "CUSTOMER";
});

const visibleOptions = computed(() =>
  ALL_OPTIONS.filter((o) => o.roles.includes(myRole.value))
);

async function onToggle(field, value) {
  prefs.value[field] = value;
  saved.value = false;
  const updated = await updateNotifPreferences({ [field]: value });
  prefs.value = updated;
  saved.value = true;
  setTimeout(() => (saved.value = false), 1500);
}

onMounted(async () => {
  try {
    prefs.value = await getNotifPreferences();
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.wrap { max-width: 560px; margin: 0 auto; padding: 28px 20px; }
.title { font-family: var(--font-display); font-size: 22px; font-weight: 600; color: var(--text); }
.sub { color: var(--text-2); font-size: 14px; margin: 6px 0 24px; }
.state { color: var(--text-3); }
.rows { display: flex; flex-direction: column; gap: 2px; }
.row {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 14px 4px; border-bottom: 0.5px solid var(--border); cursor: pointer;
}
.row-info { display: flex; flex-direction: column; gap: 2px; }
.row-label { font-size: 14px; font-weight: 500; color: var(--text); }
.row-desc { font-size: 12px; color: var(--text-2); }
.row input { width: 18px; height: 18px; accent-color: var(--accent); }
.saved { margin-top: 16px; color: var(--accent); font-size: 13px; }
</style>
```

- [ ] **Step 2: Registrar la ruta**

En `frontend/src/router/index.js`, importar la vista (después de la línea 16, con los demás imports de admin):
```javascript
import NotificationSettings from "../views/settings/NotificationSettings.vue";
```
Y agregar la ruta al array `routes` (después de la ruta `/admin`, ~línea 32). Sin `meta.role` → basta con estar autenticado (el guard existente exige auth para rutas no públicas):
```javascript
  { path: "/ajustes/notificaciones", name: "notif-settings", component: NotificationSettings, meta: { authed: true } },
```

- [ ] **Step 3: Agregar acceso desde el topbar**

En `frontend/src/components/AppTopBar.vue`, en `.topbar-right` (antes de la campanita), agregar un botón de ajustes que navegue a la ruta:
```html
      <RouterLink to="/ajustes/notificaciones" class="tb-theme" aria-label="Ajustes de notificaciones">
        <i class="ti ti-settings" aria-hidden="true"></i>
      </RouterLink>
      <NotificationBell />
```
(`RouterLink` ya está disponible globalmente por vue-router; reutiliza la clase `.tb-theme` para el estilo del botón.)

- [ ] **Step 4: Verificar build**

Run: `cd frontend && npm run build`
Expected: build limpio.

- [ ] **Step 5: Verificación manual**

Ir a `/ajustes/notificaciones` con cada rol → se ven sólo los toggles relevantes al rol; togglear uno persiste (recargar la página lo mantiene); aparece "Guardado ✓".

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/settings/NotificationSettings.vue frontend/src/router/index.js frontend/src/components/AppTopBar.vue
git commit -m "feat(frontend): pantalla de preferencias de email de notificaciones"
```

---

## Self-Review (completado por el autor del plan)

**Spec coverage:**
- Toast in-app → Task 9. Centro persistido + campanita → Tasks 1, 6, 10. Email SMTP → Tasks 3, 4. Config SMTP env/console → Task 3. Presence gate → Tasks 2, 4, 5. Preferencias granulares → Tasks 1, 6, 11. Matriz de eventos → Task 4 (`_recipients_for`) + Task 7 (cableado). WS por-usuario → Task 5. Shell persistente → Task 9 (App.vue). ✔ Todas las secciones del spec tienen tarea.

**Placeholders:** ninguno — todo el código está completo. Sin "TBD"/"handle edge cases".

**Type consistency:** `dispatch(kind, ticket, actor, extra)`, `notify_for_event(ticket, event_kind, actor, payload)`, store actions (`init/disconnect/setActiveTicket/markRead/markAllRead/dismissToast`), campos `toastId` (toast) vs `id` (notificación) usados consistentemente. Endpoints y wrappers del api client coinciden (`/api/notifications/...`).

## Limitación conocida (decisión de alcance)

No existe una ruta por-ticket en el router actual (los tickets se seleccionan dentro del dashboard). Por eso el click en un toast/notificación **navega al dashboard del rol con `?ticket=<id>`** y marca la notificación como leída, pero **no preselecciona** el ticket automáticamente. El deep-link real (preseleccionar el ticket desde el query param en cada dashboard) queda como follow-up liviano, fuera del alcance de este ciclo.

## Execution Handoff

Dos opciones de ejecución:
1. **Subagent-Driven (recomendada)** — un subagente fresco por tarea, review entre tareas.
2. **Inline** — ejecutar en esta sesión con checkpoints.
