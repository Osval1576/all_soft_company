# CSAT · F2 — Encuesta de satisfacción in-app

**Fecha:** 2026-07-05
**Sub-proyecto:** F2 (segunda parte de F — SLAs + CSAT + métricas)
**Estado:** Diseño aprobado, pendiente de plan de implementación

## Objetivo

Dar al cliente una forma simple de calificar la atención recibida en un ticket una vez
resuelto: 1-5 estrellas + comentario opcional, mostrado inline en el chat del ticket, visible
en modo lectura para el cliente, el técnico asignado y el admin.

F se descompone en F1 (motor de SLA, hecho), **F2 (este spec: CSAT)** y F3 (métricas +
dashboards, consume F1 y F2). F2 es independiente de F1 salvo por convención de desacople
(app nueva, imports lazy desde `tickets_t`).

## Contexto técnico relevante (estado actual)

- **Greenfield para CSAT** — no existe nada previo (`grep` sin resultados).
- `Ticket`: `estado` (OPEN/IN_PROGRESS/RESOLVED/CLOSED), `creado_por`, `asignado_a`.
- **Patrón de desacople establecido en F1**: la app `sla/` no es importada por `tickets_t` a
  nivel de módulo; el serializer/vista hacen imports lazy dentro de los métodos. `csat/` sigue
  el mismo patrón — evita acoplar `tickets_t` a features add-on.
- **Notificaciones (Fase 2):** ya existe `dispatch("status_changed", ...)` que notifica al
  cliente cuando su ticket pasa a RESOLVED/CLOSED. **F2 no agrega notificación propia** — esa
  notificación ya funciona como nudge; el prompt de calificar vive inline en el chat.
- **Frontend:** `ChatPanel.vue` es el componente compartido de chat de ticket (usado por los
  tres dashboards). `ClientDashboard`, `TechnicianDashboard`, `AdminDashboard` ya muestran
  tickets en listas/tabla.
- **Serializer pattern:** `TicketSerializer` ya tiene un campo `sla` (SerializerMethodField con
  import lazy) — mismo patrón para `csat`/`can_rate`.

## Decisiones tomadas en el brainstorm

- Escala: **1-5 estrellas + comentario opcional**.
- Disparador de elegibilidad: **al pasar a RESUELTO** (`estado in ("RESOLVED", "CLOSED")` —
  cerrado también es elegible, ya que normalmente se llega a cerrado pasando por resuelto).
- Nudge: **prompt inline en el chat**, sin notificación dedicada nueva.
- Una calificación por ticket, **inmutable** tras enviarla.

## Diseño

### 1. Backend — app nueva `csat/`

```
CSATResponse   (OneToOne Ticket, related_name="csat")
  ticket      OneToOneField(tickets_t.Ticket, on_delete=CASCADE, related_name="csat")
  score       PositiveSmallIntegerField, validators=[MinValueValidator(1), MaxValueValidator(5)]
  comment     TextField(blank=True)
  created_at  DateTimeField(auto_now_add=True)
```

**Helper `csat_payload(ticket)`** (en `csat/payloads.py`): devuelve
`{"score": int, "comment": str, "created_at": iso}` si `ticket.csat` existe, si no `None`.
Consumido por el serializer de `tickets_t` (una sola fuente de verdad del shape).

**Elegibilidad** (`csat/eligibility.py::is_eligible(ticket) -> bool`):
`ticket.estado in ("RESOLVED", "CLOSED")`.

**Endpoint submit:** `POST /api/csat/<ticket_id>/` (vista simple, no ViewSet — un solo verbo).
- Permiso: el usuario autenticado debe ser `ticket.creado_por` (el dueño). Si no → 403.
- Si el ticket no es elegible → 400 ("El ticket todavía no está resuelto.").
- Si ya existe `CSATResponse` para ese ticket → 409 ("Ya calificaste este ticket.").
- Payload de entrada: `{"score": int, "comment": str opcional}`. `score` fuera de 1-5 → 400
  (validación del serializer).
- Crea el `CSATResponse` y devuelve `csat_payload(ticket)` con 201.

### 2. Backend — exposición en el ticket

`TicketSerializer` (en `tickets_t/serializers.py`) suma dos `SerializerMethodField` (import
lazy de `csat`, igual que el patrón ya usado para `sla`):

- **`csat`**: `csat_payload(obj)` — objeto o `null`. Visible para cualquiera con acceso al
  ticket (dueño, técnico asignado, admin) — es información de solo lectura del ticket.
- **`can_rate`**: `True` únicamente si:
  1. `request.user.id == obj.creado_por_id` (es el dueño), **y**
  2. `is_eligible(obj)` (RESOLVED o CLOSED), **y**
  3. `obj.csat` no existe todavía.
  El campo lee `self.context["request"].user` (ya presente en el contexto de DRF por
  defecto). Para técnico/admin es siempre `False` (no son quienes califican).

### 3. Frontend

- **`api/csat.api.js`**: `submitCsat(ticketId, {score, comment})` → `POST /api/csat/<id>/`.
- **`CsatPrompt.vue`**: banner con 5 estrellas clickeables (hover preview) + textarea de
  comentario opcional + botón "Enviar calificación". Se muestra dentro de `ChatPanel.vue`
  (o como sección debajo del historial) **sólo si `ticket.can_rate === true`**. Al enviar:
  llama `submitCsat`, y en éxito emite un evento que el padre usa para refrescar el ticket
  (`can_rate` pasa a `false`, `csat` queda seteado) — no hace falta recargar toda la lista.
- **`CsatDisplay.vue`**: read-only — muestra las 5 estrellas (llenas hasta `score`) + el
  comentario si existe + fecha. Se muestra cuando `ticket.csat` no es null:
  - **Cliente**: ve su propia calificación enviada (reemplaza el prompt).
  - **Técnico** (`TechnicianDashboard`, lista "Mis tickets"): ve el score del cliente en el
    ticket seleccionado/chat.
  - **Admin** (`AdminDashboard`, tabla de tickets): columna nueva "CSAT" con las estrellas
    (o "—" si `csat` es null), igual patrón que la columna SLA de F1.
- Estética v2: hairline 0.5px, CSS vars, voseo ("Calificá tu experiencia", "¡Gracias por tu
  calificación!").

### 4. Testing

Backend (foco):
- Submit: crea `CSATResponse` con score/comment correctos; 403 si no es el dueño; 400 si el
  ticket no es elegible (OPEN/IN_PROGRESS); 409 si ya existe una respuesta; 400 si `score`
  fuera de 1-5.
- `is_eligible`: True para RESOLVED/CLOSED, False para OPEN/IN_PROGRESS.
- Serializer: `csat` es `null` sin respuesta y el objeto correcto con respuesta; `can_rate`
  es `True` sólo para el dueño con ticket elegible y sin respuesta previa, `False` en
  cualquier otro caso (no-dueño, no elegible, ya calificado).

Frontend: build limpio + checklist manual (calificar un ticket resuelto propio, ver
read-only después de enviar, verificar que técnico/admin ven el score pero no el prompt).

## Fuera de alcance (YAGNI, ciclos futuros)

- Métricas agregadas (CSAT promedio, tendencia, por técnico/prioridad) → **F3**.
- Editar o re-calificar una respuesta ya enviada (inmutable).
- Recalificar tras reabrir un ticket (el reloj de SLA de F1 tampoco crea un reloj nuevo al
  reabrir; CSAT sigue la misma filosofía — una respuesta por ticket, punto).
- Notificación dedicada de CSAT (se apoya en la notificación existente de "resuelto").
- Email de CSAT (in-app únicamente, igual que las notificaciones de SLA en F1).
