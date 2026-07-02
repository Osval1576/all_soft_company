# AllSafe — Dashboards v2, Fase 1 (Core) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir los dashboards de AllSafe en algo utilizable en producción: validación server-side de permisos, pool de tickets para técnicos, WebSocket con reconnect, auditoría, y rediseño consistente con la landing v2.

**Architecture:** Backend contenido en `tickets_t/` (modelo nuevo `TicketEvent`, validaciones DRF, endpoints `pool` / `take` / `events`). Frontend con composable `useWsConnection` para el WebSocket resiliente, `TechnicianDashboard` reescrito con tabs (Mis tickets / Pool), `ClientDashboard` simplificado, `AdminDashboard` restilizado. Tipografía y palette hereda automáticamente de los tokens actualizados en el rediseño v2 de la landing.

**Tech Stack:** Backend Django 6 + DRF + Channels (WS existente). Frontend Vue 3.5 + Pinia + `useTheme` existente + `useWsConnection` nuevo. Tests Django estándar.

## Global Constraints

- Backend: Django 6.0.3, DRF con `CookieJWTAuthentication` (default global). Tests con `python backend/manage.py test tickets_t -v 2`.
- Frontend: Vue 3.5 + Vite 8-beta. No agregar dependencias nuevas. Tokens ya actualizados: `--font-display`, `--font-body`, `--font-mono`, `--accent` (#0038FF light / #5B7CFF dark), `--accent-2` (#0056FF light / #00E5FF dark), `--accent-glow`.
- Ramificación: crear rama `feat/dashboards-v2-fase1` desde `main` antes de empezar.
- Roles: `role` está en `users.User.role`. Valores: `CUSTOMER`, `AGENT`, `ADMIN`. Los `is_superuser` cuentan como ADMIN.
- Ticket fields relevantes: `titulo`, `descripcion`, `prioridad` (LOW/MEDIUM/HIGH/URGENT), `estado` (OPEN/IN_PROGRESS/RESOLVED/CLOSED), `creado_por` (FK User), `asignado_a` (FK User, null=True), `reference` (string ALS-YYYYMMDD-NNNNNN), `created_at`, `updated_at`.
- Nomenclatura: URL prefixes existentes `/api/tickets/...`. Nuevos endpoints como actions del `TicketViewSet`.
- State transitions permitidas: `OPEN → OPEN | IN_PROGRESS | RESOLVED | CLOSED`; `IN_PROGRESS → IN_PROGRESS | RESOLVED | CLOSED`; `RESOLVED → RESOLVED | CLOSED`; `CLOSED → CLOSED`. Excepción: ADMIN puede pasar de RESOLVED/CLOSED a OPEN (reopen).

---

## File Structure

**Backend (new):**
```
backend/tickets_t/
  migrations/
    000X_ticketevent.py           # generated
    000Y_seed_created_events.py   # data migration
```

**Backend (modified):**
- `backend/tickets_t/models.py` — agregar `TicketEvent`
- `backend/tickets_t/serializers.py` — validators + `TicketEventSerializer`
- `backend/tickets_t/views.py` — actions `pool`, `take`, `events`, `perform_create`/`perform_update` con emisión de eventos
- `backend/tickets_t/tests.py` — 9 tests nuevos (o crear `tests/test_dashboards_v2.py`)

**Frontend (new):**
```
frontend/src/
  composables/
    useWsConnection.js
  components/
    tickets/
      TicketEventTimeline.vue
      PoolList.vue
```

**Frontend (modified):**
- `frontend/src/components/ChatPanel.vue` — usar `useWsConnection`, agregar badge + timeline
- `frontend/src/components/AppTopBar.vue` — agregar theme toggle
- `frontend/src/views/dashboards/ClientDashboard.vue` — quitar stats, restyle
- `frontend/src/views/dashboards/TechnicianDashboard.vue` — reemplazar redirect por dashboard real
- `frontend/src/views/dashboards/AdminDashboard.vue` — restyle v2
- `frontend/src/api/tickets.api.js` — agregar métodos `getPool`, `takeTicket`, `getTicketEvents`
- `frontend/.env.example` — documentar `VITE_WS_HOST`
- `frontend/vite.config.js` — verificar que las env vars se exponen (no hay cambio si ya usa el prefijo `VITE_`)

---

## Task 1 — Crear rama y modelo TicketEvent

**Files:**
- Create: `backend/tickets_t/migrations/000X_ticketevent.py` (generado)
- Modify: `backend/tickets_t/models.py` (append)

**Interfaces:**
- Produces: `tickets_t.models.TicketEvent` con campos `ticket` (FK), `kind` (CharField choices), `actor` (FK nullable), `payload` (JSONField), `created_at`. Ordering ascendente por `created_at`.

- [ ] **Step 1: Crear rama de trabajo**

```bash
cd C:/Users/osvaldo/allsafe
git checkout main
git checkout -b feat/dashboards-v2-fase1
```

- [ ] **Step 2: Verificar última migración de tickets_t**

```bash
python backend/manage.py showmigrations tickets_t
```

Anotar el nombre de la última migración aplicada (por ejemplo `0001_initial`). El siguiente número es el que se usará para `ticketevent`.

- [ ] **Step 3: Agregar modelo `TicketEvent` a `models.py`**

Al final de `backend/tickets_t/models.py`, agregar:

```python
class TicketEvent(models.Model):
    class Kind(models.TextChoices):
        CREATED = "created", "Creado"
        ASSIGNED = "assigned", "Asignado"
        UNASSIGNED = "unassigned", "Desasignado"
        STATUS_CHANGED = "status_changed", "Cambio de estado"
        REOPENED = "reopened", "Reabierto"
        PRIORITY_CHANGED = "priority_changed", "Cambio de prioridad"

    ticket = models.ForeignKey(
        "Ticket",
        on_delete=models.CASCADE,
        related_name="events",
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    actor = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="+",
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["ticket", "created_at"])]

    def __str__(self):
        return f"{self.kind}@{self.ticket_id} by {self.actor_id}"
```

- [ ] **Step 4: Generar migración**

```bash
python backend/manage.py makemigrations tickets_t
```

Debe crear un archivo tipo `backend/tickets_t/migrations/000X_ticketevent.py`. Confirmar que el `Migration.dependencies` referencia la última migración anterior.

- [ ] **Step 5: Aplicar migración**

```bash
python backend/manage.py migrate tickets_t
```

Debe imprimir `Applying tickets_t.000X_ticketevent... OK`.

- [ ] **Step 6: Commit**

```bash
git add backend/tickets_t/models.py backend/tickets_t/migrations/
git commit -m "feat(tickets_t): add TicketEvent model for audit trail"
```

---

## Task 2 — Data migration para seed de eventos históricos

**Files:**
- Create: `backend/tickets_t/migrations/000Y_seed_created_events.py`

**Interfaces:**
- Produces: cada Ticket existente en DB tiene al menos un `TicketEvent` con `kind="created"` y `actor=ticket.creado_por`.

- [ ] **Step 1: Verificar último número de migración**

```bash
python backend/manage.py showmigrations tickets_t
```

Anotar el número tras `ticketevent`. La nueva migración tiene el siguiente número.

- [ ] **Step 2: Crear la data migration**

Crear `backend/tickets_t/migrations/000Y_seed_created_events.py` (reemplazar `000Y` por el número correcto):

```python
from django.db import migrations


def seed(apps, schema_editor):
    Ticket = apps.get_model("tickets_t", "Ticket")
    TicketEvent = apps.get_model("tickets_t", "TicketEvent")
    for t in Ticket.objects.all():
        if not TicketEvent.objects.filter(ticket=t, kind="created").exists():
            TicketEvent.objects.create(
                ticket=t,
                kind="created",
                actor_id=t.creado_por_id,
                payload={"seed": True},
            )


def unseed(apps, schema_editor):
    TicketEvent = apps.get_model("tickets_t", "TicketEvent")
    TicketEvent.objects.filter(kind="created", payload__seed=True).delete()


class Migration(migrations.Migration):
    dependencies = [("tickets_t", "000X_ticketevent")]  # reemplazar por el nombre real anterior
    operations = [migrations.RunPython(seed, unseed)]
```

- [ ] **Step 3: Aplicar**

```bash
python backend/manage.py migrate tickets_t
```

- [ ] **Step 4: Verificar en shell**

```bash
python backend/manage.py shell -c "from tickets_t.models import Ticket, TicketEvent; print(Ticket.objects.count(), 'tickets;', TicketEvent.objects.filter(kind='created').count(), 'created events')"
```

Los dos números deben coincidir.

- [ ] **Step 5: Commit**

```bash
git add backend/tickets_t/migrations/
git commit -m "feat(tickets_t): seed created events for existing tickets"
```

---

## Task 3 — TicketEventSerializer + validación asignado_a

**Files:**
- Modify: `backend/tickets_t/serializers.py`

**Interfaces:**
- Produces:
  - `TicketEventSerializer` con fields `id, kind, actor, actor_username, payload, created_at`.
  - `TicketSerializer.validate_asignado_a(value)` que rechaza `value` sin role AGENT/superuser.

- [ ] **Step 1: Agregar `TicketEventSerializer`**

Al final de `backend/tickets_t/serializers.py`:

```python
from .models import TicketEvent


class TicketEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True, default=None)

    class Meta:
        model = TicketEvent
        fields = ["id", "kind", "actor", "actor_username", "payload", "created_at"]
```

- [ ] **Step 2: Agregar `validate_asignado_a` al TicketSerializer**

Dentro de la clase `TicketSerializer` (o `TicketUpdateSerializer` si es la que se usa en updates — verificar en la app), agregar:

```python
def validate_asignado_a(self, value):
    if value is None:
        return value
    if not (value.is_superuser or getattr(value, "role", None) == "AGENT"):
        raise serializers.ValidationError(
            "Solo se puede asignar a técnicos (rol AGENT)."
        )
    return value
```

Nota: `value` es la instancia User resuelta por DRF a partir del pk que viene en el request.

- [ ] **Step 3: Confirmar import**

Al principio de `serializers.py`, asegurar `from rest_framework import serializers`. Ya debería estar.

- [ ] **Step 4: Correr chequeo Django**

```bash
python backend/manage.py check
```

Debe imprimir `System check identified no issues (0 silenced)`.

- [ ] **Step 5: Commit**

```bash
git add backend/tickets_t/serializers.py
git commit -m "feat(tickets_t): TicketEventSerializer + validate asignado_a is AGENT"
```

---

## Task 4 — Validación de state transitions

**Files:**
- Modify: `backend/tickets_t/serializers.py`
- Test: `backend/tickets_t/tests.py` (o `tests/test_state_transitions.py` si prefieres módulo aparte)

**Interfaces:**
- Produces: `TicketSerializer.validate_estado(value)` que rechaza transiciones inválidas usando la tabla `ALLOWED_TRANSITIONS`. ADMIN puede reabrir desde RESOLVED/CLOSED.

TDD prescribed.

- [ ] **Step 1: Escribir tests de transición (RED)**

Agregar al final de `backend/tickets_t/tests.py`:

```python
from django.contrib.auth import get_user_model
from django.test import TestCase
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
        r = self._client(self.agent).patch(f"/api/tickets/{self.ticket.id}/", {"estado": "IN_PROGRESS"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["estado"], "IN_PROGRESS")

    def test_agent_backward_transition_rejected(self):
        self.ticket.estado = "RESOLVED"
        self.ticket.save()
        r = self._client(self.agent).patch(f"/api/tickets/{self.ticket.id}/", {"estado": "IN_PROGRESS"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_admin_can_reopen_from_resolved(self):
        self.ticket.estado = "RESOLVED"
        self.ticket.save()
        r = self._client(self.admin).patch(f"/api/tickets/{self.ticket.id}/", {"estado": "OPEN"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["estado"], "OPEN")

    def test_admin_can_reopen_from_closed(self):
        self.ticket.estado = "CLOSED"
        self.ticket.save()
        r = self._client(self.admin).patch(f"/api/tickets/{self.ticket.id}/", {"estado": "OPEN"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_agent_cannot_reopen(self):
        self.ticket.estado = "RESOLVED"
        self.ticket.save()
        r = self._client(self.agent).patch(f"/api/tickets/{self.ticket.id}/", {"estado": "OPEN"}, format="json")
        self.assertEqual(r.status_code, 400)
```

- [ ] **Step 2: Correr tests, esperar RED**

```bash
python backend/manage.py test tickets_t.tests.StateTransitionTests -v 2
```

Los tests `_backward_rejected` y `_admin_can_reopen_*` y `_agent_cannot_reopen` deben fallar (200 en vez de 400, o 400 en vez de 200) porque aún no hay validación.

- [ ] **Step 3: Agregar `validate_estado` al TicketSerializer**

En `backend/tickets_t/serializers.py`, dentro de `TicketSerializer`:

```python
ALLOWED_TRANSITIONS = {
    "OPEN": {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"},
    "IN_PROGRESS": {"IN_PROGRESS", "RESOLVED", "CLOSED"},
    "RESOLVED": {"RESOLVED", "CLOSED"},
    "CLOSED": {"CLOSED"},
}


def validate_estado(self, value):
    if not self.instance:
        return value
    current = self.instance.estado
    if current == value:
        return value
    request = self.context.get("request")
    is_admin = bool(
        request
        and request.user.is_authenticated
        and (request.user.is_superuser or getattr(request.user, "role", None) == "ADMIN")
    )
    if is_admin and current in ("RESOLVED", "CLOSED") and value == "OPEN":
        return value
    allowed = self.ALLOWED_TRANSITIONS.get(current, {value})
    if value not in allowed:
        raise serializers.ValidationError(
            f"Transición no permitida: {current} → {value}."
        )
    return value
```

- [ ] **Step 4: Correr tests, esperar GREEN**

```bash
python backend/manage.py test tickets_t.tests.StateTransitionTests -v 2
```

Los 5 tests deben pasar.

- [ ] **Step 5: Commit**

```bash
git add backend/tickets_t/serializers.py backend/tickets_t/tests.py
git commit -m "feat(tickets_t): validate state transitions (admin can reopen)"
```

---

## Task 5 — Emisión automática de eventos + endpoints pool/take/events

**Files:**
- Modify: `backend/tickets_t/views.py`
- Test: `backend/tickets_t/tests.py` (append)

**Interfaces:**
- Consumes: `TicketEvent`, `TicketEventSerializer`, `validate_asignado_a` (Tasks 1, 3).
- Produces:
  - `GET /api/tickets/pool/` — devuelve tickets sin asignar. AGENT/ADMIN/superuser 200, CUSTOMER 403.
  - `POST /api/tickets/{id}/take/` — AGENT/superuser se auto-asigna. Crea `TicketEvent(kind="assigned", actor=user)`. 200/409/403.
  - `GET /api/tickets/{id}/events/` — devuelve lista serializada.
  - `perform_create` emite `Kind.CREATED`.
  - `perform_update` compara `estado`, `asignado_a_id`, `prioridad` y emite events correspondientes.

TDD prescribed.

- [ ] **Step 1: Escribir tests (RED)**

Append a `backend/tickets_t/tests.py`:

```python
class PoolAndTakeTests(TestCase, ):
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
        r = self._client(self.agent1).get("/api/tickets/pool/")
        self.assertEqual(r.status_code, 200)
        ids = [t["id"] for t in r.json()]
        self.assertIn(self.t_unassigned.id, ids)
        self.assertNotIn(self.t_assigned.id, ids)

    def test_pool_forbidden_for_customer(self):
        r = self._client(self.customer).get("/api/tickets/pool/")
        self.assertEqual(r.status_code, 403)

    def test_take_assigns_and_creates_event(self):
        from tickets_t.models import TicketEvent
        r = self._client(self.agent1).post(f"/api/tickets/{self.t_unassigned.id}/take/")
        self.assertEqual(r.status_code, 200)
        self.t_unassigned.refresh_from_db()
        self.assertEqual(self.t_unassigned.asignado_a_id, self.agent1.id)
        self.assertTrue(TicketEvent.objects.filter(ticket=self.t_unassigned, kind="assigned", actor=self.agent1).exists())

    def test_take_conflict_if_already_assigned(self):
        r = self._client(self.agent2).post(f"/api/tickets/{self.t_assigned.id}/take/")
        self.assertEqual(r.status_code, 409)

    def test_take_forbidden_for_customer(self):
        r = self._client(self.customer).post(f"/api/tickets/{self.t_unassigned.id}/take/")
        self.assertEqual(r.status_code, 403)

    def test_admin_assigns_only_to_agent(self):
        r = self._client(self.admin).patch(
            f"/api/tickets/{self.t_unassigned.id}/",
            {"asignado_a": self.customer.id},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_admin_assigns_agent_ok(self):
        r = self._client(self.admin).patch(
            f"/api/tickets/{self.t_unassigned.id}/",
            {"asignado_a": self.agent2.id},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_status_change_emits_event(self):
        from tickets_t.models import TicketEvent
        self._client(self.agent1).patch(
            f"/api/tickets/{self.t_assigned.id}/",
            {"estado": "IN_PROGRESS"},
            format="json",
        )
        self.assertTrue(TicketEvent.objects.filter(
            ticket=self.t_assigned, kind="status_changed", payload__to="IN_PROGRESS"
        ).exists())

    def test_events_endpoint_returns_history(self):
        from tickets_t.models import TicketEvent
        TicketEvent.objects.create(ticket=self.t_unassigned, kind="created", actor=self.customer)
        r = self._client(self.customer).get(f"/api/tickets/{self.t_unassigned.id}/events/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(any(e["kind"] == "created" for e in r.json()))
```

- [ ] **Step 2: Correr tests, esperar RED**

```bash
python backend/manage.py test tickets_t.tests.PoolAndTakeTests -v 2
```

Todos deben fallar (404 en actions, o 200 donde esperamos 400).

- [ ] **Step 3: Modificar `TicketViewSet` en `backend/tickets_t/views.py`**

Reemplazar el archivo completo con:

```python
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction

from .models import Ticket, TicketMessage, TicketEvent
from .serializers import (
    TicketSerializer, TicketCreateSerializer, TicketMessageSerializer,
    TicketEventSerializer,
)


def _role(user):
    return getattr(user, "role", None)


def _is_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or _role(user) == "ADMIN"))


def _is_agent(user):
    return bool(user and user.is_authenticated and (_role(user) == "AGENT" or user.is_superuser))


class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

    def get_queryset(self):
        user = self.request.user
        r = _role(user)
        qs = Ticket.objects.all().order_by("-created_at")
        if r == "ADMIN" or user.is_superuser:
            return qs
        if r == "AGENT":
            return qs.filter(asignado_a=user)
        return qs.filter(creado_por=user)

    def get_serializer_class(self):
        if self.action == "create":
            return TicketCreateSerializer
        return TicketSerializer

    # ---- event emission helpers ----
    def _emit(self, ticket, kind, actor, payload=None):
        TicketEvent.objects.create(ticket=ticket, kind=kind, actor=actor, payload=payload or {})

    def perform_create(self, serializer):
        with transaction.atomic():
            ticket = serializer.save()
            self._emit(ticket, "created", self.request.user)

    def perform_update(self, serializer):
        instance_before = self.get_object()
        old = {
            "estado": instance_before.estado,
            "asignado_a_id": instance_before.asignado_a_id,
            "prioridad": instance_before.prioridad,
        }
        with transaction.atomic():
            ticket = serializer.save()
            actor = self.request.user
            new = {
                "estado": ticket.estado,
                "asignado_a_id": ticket.asignado_a_id,
                "prioridad": ticket.prioridad,
            }
            if old["estado"] != new["estado"]:
                kind = "reopened" if (old["estado"] in ("RESOLVED", "CLOSED") and new["estado"] == "OPEN") else "status_changed"
                self._emit(ticket, kind, actor, {"from": old["estado"], "to": new["estado"]})
            if old["asignado_a_id"] != new["asignado_a_id"]:
                if new["asignado_a_id"] is None:
                    self._emit(ticket, "unassigned", actor, {"from_user_id": old["asignado_a_id"]})
                else:
                    self._emit(ticket, "assigned", actor, {"to_user_id": new["asignado_a_id"]})
            if old["prioridad"] != new["prioridad"]:
                self._emit(ticket, "priority_changed", actor, {"from": old["prioridad"], "to": new["prioridad"]})

    # ---- messages (existing) ----
    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        ticket = self.get_object()
        qs = TicketMessage.objects.filter(ticket=ticket).order_by("created_at")
        return Response(TicketMessageSerializer(qs, many=True).data)

    # ---- pool ----
    @action(detail=False, methods=["get"], url_path="pool")
    def pool(self, request):
        user = request.user
        if not (_is_admin(user) or _is_agent(user)):
            return Response({"detail": "Solo técnicos o admin."}, status=403)
        qs = Ticket.objects.filter(asignado_a__isnull=True).order_by("-created_at")
        return Response(TicketSerializer(qs, many=True, context={"request": request}).data)

    # ---- take ----
    @action(detail=True, methods=["post"], url_path="take")
    def take(self, request, pk=None):
        user = request.user
        if not _is_agent(user):
            return Response({"detail": "Solo técnicos pueden tomar tickets."}, status=403)
        try:
            ticket = Ticket.objects.get(pk=pk)
        except Ticket.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=404)
        if ticket.asignado_a_id and ticket.asignado_a_id != user.id:
            return Response({"detail": "Ya asignado a otro técnico."}, status=409)
        if ticket.asignado_a_id == user.id:
            return Response(TicketSerializer(ticket, context={"request": request}).data)
        with transaction.atomic():
            ticket.asignado_a = user
            ticket.save(update_fields=["asignado_a"])
            self._emit(ticket, "assigned", user, {"self_take": True, "to_user_id": user.id})
        return Response(TicketSerializer(ticket, context={"request": request}).data)

    # ---- events ----
    @action(detail=True, methods=["get"], url_path="events")
    def events(self, request, pk=None):
        ticket = self.get_object()
        return Response(TicketEventSerializer(ticket.events.all(), many=True).data)
```

Nota: `pool` y `take` NO usan `get_object()` (que aplicaría el `get_queryset` restrictivo del AGENT). Usan lookups directos.

- [ ] **Step 4: Correr tests, esperar GREEN**

```bash
python backend/manage.py test tickets_t.tests.PoolAndTakeTests -v 2
```

Los 9 tests deben pasar.

También correr la suite completa de tickets_t:

```bash
python backend/manage.py test tickets_t -v 2
```

Esperar 0 failures.

- [ ] **Step 5: Commit**

```bash
git add backend/tickets_t/views.py backend/tickets_t/tests.py
git commit -m "feat(tickets_t): pool/take/events endpoints + audit trail via TicketEvent"
```

---

## Task 6 — Composable useWsConnection (frontend)

**Files:**
- Create: `frontend/src/composables/useWsConnection.js`
- Create: `frontend/.env.example`

**Interfaces:**
- Produces:
  ```js
  const { status, send, close, retry } = useWsConnection({
    url: () => string,           // función que devuelve la URL completa
    onMessage: (data) => void,   // callback por cada frame recibido (JSON.parse ya aplicado)
  });
  // status: ref('connecting' | 'connected' | 'reconnecting' | 'disconnected')
  // send(payload): stringify + envía si conectado
  // close(): cierra sin retry
  // retry(): fuerza un intento de reconexión desde 'disconnected'
  ```

- [ ] **Step 1: Crear el composable**

Crear `frontend/src/composables/useWsConnection.js`:

```js
import { ref, onMounted, onBeforeUnmount } from "vue";

const BACKOFFS_MS = [1000, 2000, 4000, 8000, 16000];

export function useWsConnection({ url, onMessage }) {
  const status = ref("connecting");
  let socket = null;
  let attempts = 0;
  let retryTimer = null;
  let closedByUser = false;

  function connect() {
    if (socket && socket.readyState !== WebSocket.CLOSED) return;
    try {
      status.value = attempts === 0 ? "connecting" : "reconnecting";
      const target = typeof url === "function" ? url() : url;
      socket = new WebSocket(target);
    } catch (e) {
      scheduleRetry();
      return;
    }

    socket.onopen = () => {
      attempts = 0;
      status.value = "connected";
    };

    socket.onmessage = (evt) => {
      try {
        const parsed = JSON.parse(evt.data);
        if (onMessage) onMessage(parsed);
      } catch (_) { /* frame no JSON, ignorar */ }
    };

    socket.onerror = () => { /* onclose se dispara después */ };

    socket.onclose = () => {
      if (closedByUser) return;
      scheduleRetry();
    };
  }

  function scheduleRetry() {
    if (attempts >= BACKOFFS_MS.length) {
      status.value = "disconnected";
      return;
    }
    status.value = "reconnecting";
    const wait = BACKOFFS_MS[attempts];
    attempts += 1;
    retryTimer = setTimeout(connect, wait);
  }

  function send(payload) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return false;
    socket.send(typeof payload === "string" ? payload : JSON.stringify(payload));
    return true;
  }

  function close() {
    closedByUser = true;
    if (retryTimer) clearTimeout(retryTimer);
    if (socket) socket.close();
  }

  function retry() {
    if (retryTimer) clearTimeout(retryTimer);
    attempts = 0;
    closedByUser = false;
    connect();
  }

  onMounted(connect);
  onBeforeUnmount(close);

  return { status, send, close, retry };
}
```

- [ ] **Step 2: Documentar VITE_WS_HOST en env.example**

Crear (o modificar si existe) `frontend/.env.example`:

```
# Host del backend Django para WebSocket. En dev normalmente 'localhost:8000'.
# En producción se ignora — la URL se deriva de window.location.host.
VITE_WS_HOST=localhost:8000
```

- [ ] **Step 3: Verificar build**

```bash
cd frontend && npm run build
```

Debe compilar sin errores. El composable no se está usando aún — el build es solo verificar sintaxis.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/composables/useWsConnection.js frontend/.env.example
git commit -m "feat(frontend): useWsConnection composable with backoff + retry"
```

---

## Task 7 — API client: getPool, takeTicket, getTicketEvents

**Files:**
- Modify: `frontend/src/api/tickets.api.js`

**Interfaces:**
- Produces:
  - `getPool(): Promise<Ticket[]>` — `GET /api/tickets/pool/`
  - `takeTicket(id): Promise<Ticket>` — `POST /api/tickets/{id}/take/`
  - `getTicketEvents(id): Promise<TicketEvent[]>` — `GET /api/tickets/{id}/events/`

- [ ] **Step 1: Ver el shape actual del archivo**

```bash
cat frontend/src/api/tickets.api.js | head -30
```

Anotar cómo están definidas las funciones existentes (probablemente usan `http` importado desde `./http`).

- [ ] **Step 2: Agregar los 3 métodos**

Append al final de `frontend/src/api/tickets.api.js` (usar el mismo estilo que las funciones existentes):

```js
export function getPool() {
  return http.get("/api/tickets/pool/").then(r => r.data);
}

export function takeTicket(id) {
  return http.post(`/api/tickets/${id}/take/`).then(r => r.data);
}

export function getTicketEvents(id) {
  return http.get(`/api/tickets/${id}/events/`).then(r => r.data);
}
```

Si el archivo usa un pattern distinto (por ejemplo, exportar un objeto `ticketsApi`), adaptar. Confirmar leyendo el archivo antes de escribir.

- [ ] **Step 3: Verificar build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/tickets.api.js
git commit -m "feat(frontend): tickets api — pool, take, events"
```

---

## Task 8 — TicketEventTimeline component

**Files:**
- Create: `frontend/src/components/tickets/TicketEventTimeline.vue`

**Interfaces:**
- Props: `events: Array` (formato del `TicketEventSerializer`), `collapsed: Boolean = true` (opcional).
- Renderiza: lista con icono Tabler por `kind`, texto humano, timestamp relativo. Contenedor colapsable.

- [ ] **Step 1: Crear el componente**

Crear `frontend/src/components/tickets/TicketEventTimeline.vue`:

```vue
<template>
  <section class="tet">
    <header class="tet-head" @click="open = !open" role="button" :aria-expanded="open">
      <span class="tet-title">Historial</span>
      <span class="tet-count">{{ events.length }} eventos</span>
      <i :class="open ? 'ti ti-chevron-up' : 'ti ti-chevron-down'" aria-hidden="true"></i>
    </header>

    <ol v-if="open" class="tet-list">
      <li v-for="e in events" :key="e.id" class="tet-item">
        <span class="tet-icon"><i :class="iconFor(e.kind)" aria-hidden="true"></i></span>
        <div class="tet-body">
          <p class="tet-text">{{ label(e) }}</p>
          <p class="tet-time">{{ relativeTime(e.created_at) }}</p>
        </div>
      </li>
      <li v-if="!events.length" class="tet-empty">Sin eventos.</li>
    </ol>
  </section>
</template>

<script setup>
import { ref } from "vue";

defineProps({
  events: { type: Array, default: () => [] },
});

const open = ref(false);

const ICON = {
  created: "ti ti-star",
  assigned: "ti ti-user-check",
  unassigned: "ti ti-user-x",
  status_changed: "ti ti-arrow-right",
  reopened: "ti ti-refresh",
  priority_changed: "ti ti-flag",
};

function iconFor(kind) { return ICON[kind] || "ti ti-circle"; }

function label(e) {
  const who = e.actor_username || "Sistema";
  const p = e.payload || {};
  switch (e.kind) {
    case "created": return `${who} creó el ticket`;
    case "assigned": return `${who} asignó el ticket${p.self_take ? " (se lo tomó)" : ""}`;
    case "unassigned": return `${who} desasignó el ticket`;
    case "status_changed": return `${who} cambió estado: ${p.from} → ${p.to}`;
    case "reopened": return `${who} reabrió el ticket`;
    case "priority_changed": return `${who} cambió prioridad: ${p.from} → ${p.to}`;
    default: return `${who} · ${e.kind}`;
  }
}

function relativeTime(iso) {
  try {
    const then = new Date(iso).getTime();
    const now = Date.now();
    const diff = Math.max(0, now - then);
    const s = Math.floor(diff / 1000);
    if (s < 60) return "hace un momento";
    const m = Math.floor(s / 60);
    if (m < 60) return `hace ${m} min`;
    const h = Math.floor(m / 60);
    if (h < 24) return `hace ${h} h`;
    const d = Math.floor(h / 24);
    return `hace ${d} d`;
  } catch { return iso; }
}
</script>

<style scoped>
.tet {
  border-top: 0.5px solid var(--border);
  padding: 12px 16px 16px;
  background: var(--bg);
}
.tet-head {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-3);
  padding: 6px 0;
}
.tet-title { color: var(--text-2); }
.tet-count { color: var(--text-3); }
.tet-head i { margin-left: auto; font-size: 14px; }

.tet-list { list-style: none; margin: 12px 0 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.tet-item { display: flex; gap: 10px; align-items: flex-start; }
.tet-icon {
  width: 22px; height: 22px;
  border-radius: 4px;
  background: var(--surface-2);
  color: var(--accent);
  display: grid; place-items: center;
  flex-shrink: 0;
}
[data-theme="dark"] .tet-icon { color: var(--accent-2); }
.tet-icon i { font-size: 12px; }
.tet-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.tet-text {
  margin: 0;
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--text);
  line-height: 1.4;
}
.tet-time {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--text-3);
}
.tet-empty {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--text-3);
  text-transform: uppercase;
}
</style>
```

- [ ] **Step 2: Verificar build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/tickets/TicketEventTimeline.vue
git commit -m "feat(frontend): TicketEventTimeline collapsible history component"
```

---

## Task 9 — ChatPanel: useWsConnection + badge + timeline

**Files:**
- Modify: `frontend/src/components/ChatPanel.vue`

**Interfaces:**
- Consumes: `useWsConnection` (Task 6), `TicketEventTimeline` (Task 8), `getTicketEvents` (Task 7).
- Cambios visibles: badge de conexión en el header, timeline al pie, WS URL derivada de `window.location`, botón "Reintentar" cuando `status==='disconnected'`.

- [ ] **Step 1: Reemplazar ChatPanel.vue**

Sobrescribir `frontend/src/components/ChatPanel.vue` con:

```vue
<template>
  <div class="panel">
    <header v-if="showHeader" class="panel-header">
      <div class="header-info">
        <span class="header-title">{{ title }}</span>
        <div class="header-meta">
          <span class="conn-badge" :class="`conn-badge--${wsStatus}`">
            <span class="conn-dot" aria-hidden="true"></span>
            <span>{{ CONN_LABEL[wsStatus] || wsStatus }}</span>
          </span>
          <button
            v-if="wsStatus === 'disconnected'"
            @click="wsRetry"
            class="btn-retry"
          >Reintentar</button>
        </div>
      </div>
      <div v-if="status && canUpdateStatus" class="status-control">
        <select :value="status" @change="$emit('update:status', $event.target.value)" class="status-select">
          <option value="OPEN">Abierto</option>
          <option value="IN_PROGRESS">En proceso</option>
          <option value="RESOLVED">Resuelto</option>
          <option value="CLOSED">Cerrado</option>
        </select>
      </div>
    </header>

    <section class="messages" ref="messagesEl">
      <div v-if="loading" class="loading-state">Cargando mensajes...</div>

      <template v-else>
        <div v-if="messages.length === 0" class="empty-messages">
          No hay mensajes aún. Sé el primero en escribir.
        </div>

        <div
          v-for="m in messages"
          :key="m.id"
          class="msg-row"
          :class="m.sender_username === me ? 'msg-row--me' : 'msg-row--other'"
        >
          <div class="bubble">
            <div class="bubble-meta">
              <span v-if="m.sender_username !== me" class="bubble-sender">{{ m.sender_username }}</span>
              <span class="bubble-time">{{ formatTime(m.created_at) }}</span>
            </div>
            <div class="bubble-content">{{ m.content }}</div>
          </div>
        </div>
      </template>
    </section>

    <footer class="composer">
      <input
        v-model="draft"
        @keydown.enter.prevent="send"
        :placeholder="composerPlaceholder"
        class="composer-input"
        :disabled="wsStatus === 'disconnected'"
      />
      <button
        @click="send"
        :disabled="!draft.trim() || wsStatus !== 'connected'"
        class="composer-btn"
      >Enviar</button>
    </footer>

    <TicketEventTimeline :events="events" />
  </div>
</template>

<script setup>
import { nextTick, ref, watch, computed } from "vue";
import { getTicketMessages, getTicketEvents } from "../api/tickets.api";
import { useAuthStore } from "../stores/auth.store";
import { useWsConnection } from "../composables/useWsConnection";
import TicketEventTimeline from "./tickets/TicketEventTimeline.vue";

const props = defineProps({
  ticketId:        { type: Number, required: true },
  title:           { type: String, default: "" },
  showHeader:      { type: Boolean, default: true },
  status:          { type: String, default: null },
  canUpdateStatus: { type: Boolean, default: false },
});

defineEmits(["update:status"]);

const auth = useAuthStore();
const me   = computed(() => auth.user?.username);

const messages = ref([]);
const events = ref([]);
const loading = ref(false);
const draft = ref("");
const messagesEl = ref(null);

const CONN_LABEL = {
  connecting: "Conectando…",
  connected: "Conectado",
  reconnecting: "Reconectando…",
  disconnected: "Desconectado",
};

const composerPlaceholder = computed(() =>
  wsStatus.value === "connected" ? "Escribe un mensaje..." : "Chat desconectado"
);

function scrollToBottom() {
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
  } catch { return iso; }
}

function wsUrl() {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = import.meta.env.VITE_WS_HOST || window.location.host;
  return `${proto}//${host}/ws/chat/${props.ticketId}/`;
}

const { status: wsStatus, send: wsSend, retry: wsRetry, close: wsClose } = useWsConnection({
  url: wsUrl,
  onMessage: async (m) => {
    messages.value.push(m);
    await nextTick();
    scrollToBottom();
  },
});

async function loadAll() {
  loading.value = true;
  try {
    const [msgs, evts] = await Promise.all([
      getTicketMessages(props.ticketId),
      getTicketEvents(props.ticketId).catch(() => []),
    ]);
    messages.value = msgs;
    events.value = evts;
    await nextTick();
    scrollToBottom();
  } finally {
    loading.value = false;
  }
}

function send() {
  const text = draft.value.trim();
  if (!text) return;
  if (wsSend({ content: text })) {
    draft.value = "";
  }
}

watch(() => props.ticketId, async () => {
  wsClose();
  await loadAll();
  wsRetry();
}, { immediate: true });
</script>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface);
  border-radius: var(--r);
  overflow: hidden;
  border: 0.5px solid var(--border);
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 0.5px solid var(--border);
  flex-shrink: 0;
  gap: 12px;
}
.header-info { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.header-title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 14px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.header-meta { display: flex; align-items: center; gap: 10px; }
.conn-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-3);
}
.conn-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--text-3); }
.conn-badge--connected .conn-dot { background: var(--c-resolved, #10B981); box-shadow: 0 0 0 3px rgba(16,185,129,.15); }
.conn-badge--connected { color: var(--c-resolved, #10B981); }
.conn-badge--connecting .conn-dot,
.conn-badge--reconnecting .conn-dot {
  background: var(--c-open, #F59E0B);
  animation: conn-pulse 1s ease-in-out infinite;
}
.conn-badge--connecting,
.conn-badge--reconnecting { color: var(--c-open, #F59E0B); }
@keyframes conn-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.btn-retry {
  padding: 4px 10px;
  border: 0.5px solid var(--border);
  border-radius: 4px;
  background: transparent;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--accent);
  cursor: pointer;
}
[data-theme="dark"] .btn-retry { color: var(--accent-2); }
.status-select {
  padding: 4px 10px;
  border: 0.5px solid var(--border);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  color: var(--text);
  font-size: 12px;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--surface-2);
}
.loading-state, .empty-messages {
  color: var(--text-3);
  font-size: 13px;
  text-align: center;
  margin: auto;
}
.msg-row { display: flex; }
.msg-row--me    { justify-content: flex-end; }
.msg-row--other { justify-content: flex-start; }
.bubble { max-width: 72%; display: flex; flex-direction: column; gap: 3px; }
.msg-row--me .bubble {
  background: var(--accent);
  color: var(--accent-fg);
  border-radius: var(--r) var(--r-sm) var(--r) var(--r);
  padding: 8px 12px;
}
.msg-row--other .bubble {
  background: var(--surface);
  color: var(--text);
  border-radius: var(--r-sm) var(--r) var(--r) var(--r);
  padding: 8px 12px;
  border: 0.5px solid var(--border);
}
.bubble-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  opacity: .75;
  font-family: var(--font-mono);
  letter-spacing: 0.5px;
}
.msg-row--me .bubble-meta { justify-content: flex-end; }
.bubble-sender { font-weight: 600; }
.bubble-content { font-size: 13px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
.composer {
  display: flex;
  gap: 8px;
  padding: 12px 14px;
  border-top: 0.5px solid var(--border);
  background: var(--surface);
  flex-shrink: 0;
}
.composer-input {
  flex: 1;
  padding: 9px 14px;
  border: 0.5px solid var(--border);
  border-radius: var(--r);
  background: var(--surface-2);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 13px;
}
.composer-input:focus { border-color: var(--accent); outline: none; }
.composer-input:disabled { opacity: 0.5; }
.composer-btn {
  padding: 9px 18px;
  border-radius: var(--r);
  background: var(--accent);
  color: var(--accent-fg);
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
  border: none;
  cursor: pointer;
}
.composer-btn:hover:not(:disabled) { background: var(--accent-hover); }
.composer-btn:disabled { opacity: .4; cursor: not-allowed; }
</style>
```

- [ ] **Step 2: Verificar build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Smoke manual**

Con backend corriendo:
1. Loguearse como CUSTOMER, abrir un ticket → badge verde "Conectado" aparece.
2. Enviar un mensaje → llega al servidor.
3. Matar el backend (Ctrl+C). Badge pasa a naranja pulsante "Reconectando".
4. Después de ~30s (5 intentos), badge queda "Desconectado" con botón "Reintentar".
5. Arrancar backend, click "Reintentar" → vuelve a "Conectado".

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ChatPanel.vue
git commit -m "feat(chat): resilient WS with badge, retry button, and event timeline"
```

---

## Task 10 — ClientDashboard sin stats

**Files:**
- Modify: `frontend/src/views/dashboards/ClientDashboard.vue`

- [ ] **Step 1: Quitar el bloque de stats**

En `frontend/src/views/dashboards/ClientDashboard.vue`, eliminar el `<div class="stats-row">...</div>` completo (las 4 stat-cards con Total / Abiertos / En proceso / Resueltos).

También quitar del `<style scoped>` las reglas `.stats-row`, `.stat-card`, `.stat-card--*`, `.stat-value`, `.stat-label` (ya no se usan en esta vista).

- [ ] **Step 2: Aplicar tipografía v2 a los elementos restantes**

En el mismo archivo, actualizar las reglas de estilo restantes para usar los tokens v2:

- `.ticket-ref` → agregar `font-family: var(--font-mono);` (si no lo tenía) y quitar la fuente `monospace` explícita.
- `.ticket-date` → `font-family: var(--font-mono); letter-spacing: 0.5px;`
- `.ticket-title` → `font-family: var(--font-body);`
- `.stat-card` reglas se pueden borrar (ya no se usan).

- [ ] **Step 3: Ajustar el padding del `.content`**

Reducir el gap si queda demasiado espacio arriba. Sustituir en `.content`:
```css
.content { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 16px 20px; gap: 12px; }
```
por
```css
.content { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 16px 20px; }
```

- [ ] **Step 4: Build + smoke**

```bash
cd frontend && npm run build
```

Loguear como CUSTOMER. Confirmar que no aparecen las stat cards; lista + chat ocupan toda la vista.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/dashboards/ClientDashboard.vue
git commit -m "feat(dashboards): client dashboard drops stats, focuses on chat"
```

---

## Task 11 — PoolList component

**Files:**
- Create: `frontend/src/components/tickets/PoolList.vue`

**Interfaces:**
- Props: `tickets: Array<Ticket>`.
- Emits: `take(ticket)` cuando el técnico hace click en "Tomar".

- [ ] **Step 1: Crear el componente**

Crear `frontend/src/components/tickets/PoolList.vue`:

```vue
<template>
  <ul class="pl">
    <li v-for="t in tickets" :key="t.id" class="pl-card">
      <div class="pl-top">
        <PriorityDot :priority="t.prioridad" />
        <span class="pl-ref">{{ t.reference }}</span>
        <span class="pl-time">{{ relativeTime(t.created_at) }}</span>
      </div>
      <p class="pl-title">{{ t.titulo }}</p>
      <p class="pl-desc">{{ (t.descripcion || "").slice(0, 140) }}{{ (t.descripcion || "").length > 140 ? "…" : "" }}</p>
      <div class="pl-actions">
        <button class="btn-take" @click="$emit('take', t)">Tomar</button>
      </div>
    </li>
    <li v-if="!tickets.length" class="pl-empty">
      No hay tickets sin asignar.
    </li>
  </ul>
</template>

<script setup>
import PriorityDot from "../PriorityDot.vue";

defineProps({
  tickets: { type: Array, default: () => [] },
});
defineEmits(["take"]);

function relativeTime(iso) {
  try {
    const then = new Date(iso).getTime();
    const now = Date.now();
    const diff = Math.max(0, now - then);
    const s = Math.floor(diff / 1000);
    if (s < 60) return "ahora";
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h`;
    const d = Math.floor(h / 24);
    return `${d}d`;
  } catch { return iso; }
}
</script>

<style scoped>
.pl { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.pl-card {
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-radius: var(--r);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: border-color .15s;
}
.pl-card:hover { border-color: var(--accent); }
.pl-top { display: flex; align-items: center; gap: 8px; }
.pl-ref {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--text-2);
}
.pl-time {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--text-3);
}
.pl-title {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 14px;
  color: var(--text);
}
.pl-desc {
  margin: 0;
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.5;
}
.pl-actions { display: flex; justify-content: flex-end; }
.btn-take {
  padding: 6px 14px;
  border-radius: 4px;
  background: var(--accent);
  color: var(--accent-fg);
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 500;
  border: none;
  cursor: pointer;
}
.btn-take:hover { background: var(--accent-hover); }
.pl-empty {
  padding: 32px 12px;
  text-align: center;
  color: var(--text-3);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 1px;
  text-transform: uppercase;
}
</style>
```

- [ ] **Step 2: Build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/tickets/PoolList.vue
git commit -m "feat(tickets): PoolList component for unassigned tickets"
```

---

## Task 12 — TechnicianDashboard rehecho

**Files:**
- Modify: `frontend/src/views/dashboards/TechnicianDashboard.vue`

**Interfaces:**
- Consumes: `listMyTickets` (existente), `getPool`, `takeTicket` (Task 7), `PoolList` (Task 11), `ChatPanel` (Task 9), `PriorityDot`, `StatusBadge`.

- [ ] **Step 1: Reemplazar el archivo completo**

Sobrescribir `frontend/src/views/dashboards/TechnicianDashboard.vue`:

```vue
<template>
  <div class="page">
    <AppTopBar title="Panel del técnico" />

    <div class="content">
      <div class="stats-row">
        <div class="stat-card">
          <span class="stat-value">{{ stats.open }}</span>
          <span class="stat-label">Asignados abiertos</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ stats.in_progress }}</span>
          <span class="stat-label">En proceso</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ stats.resolved_today }}</span>
          <span class="stat-label">Resueltos hoy</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ stats.resolved_week }}</span>
          <span class="stat-label">Resueltos esta semana</span>
        </div>
      </div>

      <div class="tabs">
        <button
          v-for="tab in TABS"
          :key="tab.id"
          class="tab-btn"
          :class="{ 'tab-btn--active': activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
          <span class="tab-count">{{ tab.id === 'mine' ? mine.length : pool.length }}</span>
        </button>
      </div>

      <div v-if="activeTab === 'mine'" class="main-area">
        <aside class="ticket-list">
          <div v-if="loading" class="list-state">Cargando...</div>
          <template v-else>
            <div v-if="mine.length === 0" class="list-state">No tienes tickets asignados.</div>
            <button
              v-for="t in mine"
              :key="t.id"
              class="ticket-item"
              :class="{ 'ticket-item--active': selectedTicket?.id === t.id }"
              @click="selectedTicket = t"
            >
              <div class="ticket-item-top">
                <PriorityDot :priority="t.prioridad" />
                <span class="ticket-ref">{{ t.reference }}</span>
                <StatusBadge :status="t.estado" />
              </div>
              <div class="ticket-title">{{ t.titulo }}</div>
            </button>
          </template>
        </aside>

        <main class="chat-area">
          <div v-if="!selectedTicket" class="empty-chat">
            <p>Selecciona un ticket para abrir el chat.</p>
          </div>
          <ChatPanel
            v-else
            :ticket-id="selectedTicket.id"
            :title="`${selectedTicket.reference} — ${selectedTicket.titulo}`"
            :status="selectedTicket.estado"
            :can-update-status="true"
            @update:status="onStatusChange"
          />
        </main>
      </div>

      <div v-if="activeTab === 'pool'" class="pool-area">
        <div v-if="loadingPool" class="list-state">Cargando pool...</div>
        <PoolList v-else :tickets="pool" @take="onTake" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import AppTopBar from "../../components/AppTopBar.vue";
import ChatPanel from "../../components/ChatPanel.vue";
import PoolList from "../../components/tickets/PoolList.vue";
import StatusBadge from "../../components/StatusBadge.vue";
import PriorityDot from "../../components/PriorityDot.vue";
import { listMyTickets, updateTicket, getPool, takeTicket } from "../../api/tickets.api";

const TABS = [
  { id: "mine", label: "Mis tickets" },
  { id: "pool", label: "Pool disponible" },
];

const activeTab = ref("mine");
const loading = ref(false);
const loadingPool = ref(false);
const mine = ref([]);
const pool = ref([]);
const selectedTicket = ref(null);

const stats = computed(() => {
  const now = new Date();
  const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const isResolved = t => t.estado === "RESOLVED";
  return {
    open: mine.value.filter(t => t.estado === "OPEN").length,
    in_progress: mine.value.filter(t => t.estado === "IN_PROGRESS").length,
    resolved_today: mine.value.filter(t => isResolved(t) && new Date(t.updated_at) >= startOfDay).length,
    resolved_week: mine.value.filter(t => isResolved(t) && new Date(t.updated_at) >= weekAgo).length,
  };
});

async function loadMine() {
  loading.value = true;
  try {
    mine.value = await listMyTickets();
    if (!selectedTicket.value && mine.value.length) selectedTicket.value = mine.value[0];
  } finally { loading.value = false; }
}

async function loadPool() {
  loadingPool.value = true;
  try { pool.value = await getPool(); }
  finally { loadingPool.value = false; }
}

async function onTake(ticket) {
  try {
    const updated = await takeTicket(ticket.id);
    pool.value = pool.value.filter(t => t.id !== ticket.id);
    mine.value.unshift(updated);
    selectedTicket.value = updated;
    activeTab.value = "mine";
  } catch (e) {
    if (e?.response?.status === 409) {
      alert("Otro técnico tomó este ticket.");
      await loadPool();
    } else {
      alert("No se pudo tomar el ticket.");
    }
  }
}

async function onStatusChange(newStatus) {
  if (!selectedTicket.value) return;
  try {
    const updated = await updateTicket(selectedTicket.value.id, { estado: newStatus });
    const idx = mine.value.findIndex(t => t.id === updated.id);
    if (idx !== -1) mine.value[idx] = updated;
    selectedTicket.value = updated;
  } catch (e) {
    alert(e?.response?.data?.estado?.[0] || "No se pudo cambiar el estado.");
  }
}

onMounted(async () => {
  await Promise.all([loadMine(), loadPool()]);
});
</script>

<style scoped>
.page { display: flex; flex-direction: column; height: 100%; }
.content { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 16px 20px; gap: 16px; overflow: hidden; }

.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; flex-shrink: 0; }
.stat-card {
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-radius: var(--r);
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stat-value {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 500;
  color: var(--text);
  line-height: 1.05;
  letter-spacing: -0.02em;
}
.stat-label {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-3);
}

.tabs { display: flex; gap: 4px; border-bottom: 0.5px solid var(--border); flex-shrink: 0; }
.tab-btn {
  padding: 10px 18px;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-2);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: -1px;
}
.tab-btn--active { color: var(--accent); border-bottom-color: var(--accent); }
[data-theme="dark"] .tab-btn--active { color: var(--accent-2); border-bottom-color: var(--accent-2); }
.tab-count {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--text-3);
  background: var(--surface-2);
  padding: 2px 6px;
  border-radius: 3px;
}

.main-area { flex: 1; min-height: 0; display: grid; grid-template-columns: 320px 1fr; gap: 12px; }
.ticket-list {
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-radius: var(--r);
  overflow-y: auto;
}
.list-state {
  color: var(--text-3);
  font-size: 13px;
  text-align: center;
  padding: 24px 16px;
}
.ticket-item {
  width: 100%;
  text-align: left;
  padding: 12px 14px;
  border-bottom: 0.5px solid var(--border);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: transparent;
  border-left: none;
  border-right: none;
  border-top: none;
}
.ticket-item:hover { background: var(--surface-2); }
.ticket-item--active { background: var(--accent-light); }
.ticket-item-top { display: flex; align-items: center; gap: 7px; }
.ticket-ref {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--text-2);
}
.ticket-title {
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.chat-area { min-height: 0; }
.empty-chat {
  height: 100%;
  display: grid;
  place-items: center;
  color: var(--text-3);
  font-size: 13px;
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-radius: var(--r);
}

.pool-area { flex: 1; overflow-y: auto; padding-right: 4px; }
</style>
```

- [ ] **Step 2: Build + smoke**

```bash
cd frontend && npm run build
```

Loguear como AGENT. Verificar:
- Tab "Mis tickets" muestra tickets asignados + stats.
- Tab "Pool disponible" muestra tickets sin asignar.
- Click "Tomar" en un ticket del pool → aparece en Mis tickets, tab activa cambia.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/dashboards/TechnicianDashboard.vue
git commit -m "feat(dashboards): technician dashboard with tabs, stats, and pool"
```

---

## Task 13 — AdminDashboard restyle v2

**Files:**
- Modify: `frontend/src/views/dashboards/AdminDashboard.vue`

- [ ] **Step 1: Aplicar tipografía v2 y hairlines**

En `frontend/src/views/dashboards/AdminDashboard.vue`, en el bloque `<style scoped>`, hacer estos reemplazos (mantener toda la lógica del script):

- `.stat-card` → cambiar `border: 1px solid var(--border)` a `border: 0.5px solid var(--border)`. Eliminar `box-shadow: var(--shadow-sm);`.
- `.stat-value` → agregar `font-family: var(--font-display); letter-spacing: -0.02em; font-weight: 500;` (mantener font-size existente).
- `.stat-label` → cambiar por: `font-family: var(--font-mono); font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--text-3); font-weight: 400;`
- `.tabs` → cambiar `border-bottom: 1px solid var(--border);` a `border-bottom: 0.5px solid var(--border);`.
- `.tab-btn` → cambiar `border-color: var(--border)` a `border-color: transparent` en base; en `.tab-btn--active` cambiar a `border-bottom: 2px solid var(--accent); color: var(--accent); background: transparent;` (borrar el `border-color: var(--border)` viejo).
- `.data-table th` → agregar `font-family: var(--font-mono);` `letter-spacing: 1.2px;`.
- `.mono` → cambiar por `font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.5px; color: var(--text-2);`.
- Todas las `border: 1px solid var(--border)` → `border: 0.5px solid var(--border)`.
- Todos los `.data-table td` → agregar `font-family: var(--font-body);`.
- `.tab-content` → quitar `box-shadow: var(--shadow-sm);`.
- `.modal` → cambiar `border: 1px solid var(--border)` a `border: 0.5px solid var(--border)`.

- [ ] **Step 2: Build + smoke**

```bash
cd frontend && npm run build
```

Loguear como ADMIN. Verificar look coherente con landing v2.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/dashboards/AdminDashboard.vue
git commit -m "feat(dashboards): admin dashboard restyled to v2 palette + typography"
```

---

## Task 14 — AppTopBar con theme toggle

**Files:**
- Modify: `frontend/src/components/AppTopBar.vue`

**Interfaces:**
- Consumes: `useTheme` (existente en `frontend/src/composables/useTheme.js`).

- [ ] **Step 1: Ver el archivo actual**

```bash
cat frontend/src/components/AppTopBar.vue
```

Identificar dónde vive el bloque derecho (probablemente donde está el menú usuario / logout).

- [ ] **Step 2: Agregar el botón theme toggle**

Antes del botón/menu de logout, agregar:

```vue
<button
  class="tb-theme"
  @click="toggle"
  :aria-label="isDark ? 'Modo claro' : 'Modo oscuro'"
>
  <i :class="isDark ? 'ti ti-sun' : 'ti ti-moon'" aria-hidden="true"></i>
</button>
```

En el `<script setup>` agregar:

```js
import { useTheme } from "../composables/useTheme";
const { isDark, toggle } = useTheme();
```

En `<style scoped>` agregar:

```css
.tb-theme {
  width: 34px;
  height: 34px;
  border: 0.5px solid var(--border);
  border-radius: 6px;
  display: grid;
  place-items: center;
  color: var(--text-2);
  background: transparent;
  cursor: pointer;
  transition: background .15s, color .15s, border-color .15s;
}
.tb-theme:hover { background: var(--surface-2); color: var(--text); border-color: var(--text-3); }
.tb-theme i { font-size: 15px; }
```

- [ ] **Step 3: Aplicar tipografía v2 al título del topbar**

En la regla del título (probablemente `.tb-title` o similar), agregar:

```css
font-family: var(--font-display);
letter-spacing: -0.01em;
```

- [ ] **Step 4: Build + smoke**

```bash
cd frontend && npm run build
```

Loguear como cualquier rol. Confirmar que aparece el botón sun/moon y funciona.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/AppTopBar.vue
git commit -m "feat(topbar): theme toggle + v2 typography"
```

---

## Task 15 — Verificación E2E manual + VERIFY doc

**Files:**
- Create: `docs/superpowers/plans/2026-07-01-dashboards-v2-fase1-VERIFY.md`

- [ ] **Step 1: Correr suite backend completa**

```bash
python backend/manage.py test tickets_t landing_cms -v 2
```

Esperar 0 failures. Nota: suma landing_cms para asegurar no hubo regresión.

- [ ] **Step 2: Build frontend limpio**

```bash
cd frontend && npm run build
```

Esperar `built in Xs` sin errores.

- [ ] **Step 3: Escribir checklist de verificación**

Crear `docs/superpowers/plans/2026-07-01-dashboards-v2-fase1-VERIFY.md`:

```markdown
# Dashboards v2 · Fase 1 — Verificación manual

## Backend
- [ ] `python backend/manage.py test tickets_t -v 2` → todos OK (14+ tests)
- [ ] `curl -X PATCH /api/tickets/{id}/ -d '{"asignado_a": <customer_id>}'` como ADMIN → 400 con mensaje "Solo se puede asignar a técnicos"
- [ ] `curl -X POST /api/tickets/{id}/take/` como CUSTOMER → 403
- [ ] `curl -X POST /api/tickets/{id}/take/` como AGENT (ticket sin asignar) → 200
- [ ] Segundo `take/` del mismo ticket con otro AGENT → 409

## Frontend / Cliente
- [ ] Loguear como CUSTOMER: no aparecen stat cards, se ven lista lateral + chat.
- [ ] Crear un nuevo ticket → aparece en la lista, se auto-selecciona.
- [ ] Abrir un ticket viejo: aparece el historial al pie del chat (colapsable).

## Frontend / Técnico
- [ ] Loguear como AGENT: dashboard con tabs, stat cards arriba.
- [ ] Tab "Pool disponible": ver tickets sin asignar. Click "Tomar" → ticket pasa a "Mis tickets", tab cambia automáticamente.
- [ ] Cambiar estado a IN_PROGRESS desde el select del ChatPanel → 200 y evento aparece en timeline.
- [ ] Intentar cambiar de RESOLVED a IN_PROGRESS → 400.

## Frontend / Admin
- [ ] Loguear como ADMIN: cards con hairline (sin shadow), typography v2.
- [ ] Assign dropdown solo muestra AGENTs.
- [ ] Cambiar CLOSED a OPEN → 200 (reopen ADMIN).

## Chat resiliente
- [ ] Abrir un ticket, badge verde "Conectado".
- [ ] Matar backend → badge naranja "Reconectando…" pulsante.
- [ ] Esperar ~30 s sin backend → badge gris "Desconectado" + botón "Reintentar".
- [ ] Arrancar backend, click "Reintentar" → verde "Conectado" de nuevo.

## Theme toggle
- [ ] Click sun/moon en topbar → cambia el theme. Persiste al recargar.
```

- [ ] **Step 4: Commit y crear PR**

```bash
git add docs/superpowers/plans/2026-07-01-dashboards-v2-fase1-VERIFY.md
git commit -m "docs: verify checklist for dashboards v2 fase 1"
```

- [ ] **Step 5: Push y decidir merge/PR**

```bash
git push -u origin feat/dashboards-v2-fase1
```

Después usar `superpowers:finishing-a-development-branch` para elegir merge local o PR.

---

## Self-review

**Spec coverage:**
- Sec 5.1 TicketEvent → Task 1 ✓
- Sec 5.2 validate_asignado_a → Task 3 ✓
- Sec 5.3 validate_estado → Task 4 ✓
- Sec 5.4 pool/take/events → Task 5 ✓
- Sec 5.5 queryset AGENT (no cambio) → notado ✓
- Sec 5.6 emission perform_create/update → Task 5 ✓
- Sec 5.7 TicketEventSerializer → Task 3 ✓
- Sec 5.8 9 tests → Tasks 4 (5 tests transitions) + 5 (9 tests pool/take/events + validate_asignado_a) ✓
- Sec 6.1 useWsConnection → Task 6 ✓
- Sec 6.2 ChatPanel refactor → Task 9 ✓
- Sec 6.3 TicketEventTimeline → Task 8 ✓
- Sec 6.4 ClientDashboard → Task 10 ✓
- Sec 6.5 TechnicianDashboard → Task 12 ✓
- Sec 6.6 PoolList → Task 11 ✓
- Sec 6.7 AdminDashboard → Task 13 ✓
- Sec 6.8 AppTopBar → Task 14 ✓
- Sec 6.9 estilos v2 → Tasks 10, 13, 14 ✓
- Sec 7 seed de eventos históricos → Task 2 ✓

Todas las secciones cubiertas.

**Placeholder scan:** ninguna instancia de "TBD", "TODO" o "add error handling". Los `000X` / `000Y` en las migraciones tienen instrucciones explícitas para reemplazarlos por el número real.

**Type consistency:** `TicketEvent` (modelo), `TicketEventSerializer` (serializer), `useWsConnection` (composable), `getPool`/`takeTicket`/`getTicketEvents` (api) — todos los nombres se usan consistentemente en Tasks 1, 3, 5, 6, 7, 8, 9, 12.

No hay issues. Plan listo.
