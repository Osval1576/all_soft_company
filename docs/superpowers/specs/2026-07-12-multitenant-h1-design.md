# Multi-tenant · H1 — Núcleo de tenancy y aislamiento

**Fecha:** 2026-07-12
**Sub-proyecto:** H1 (primera parte de H — multi-tenant + billing, descompuesto en H1 núcleo / H2 registro+onboarding / H3 billing+planes / H4 branding diferido)
**Estado:** Diseño aprobado, pendiente de plan de implementación

## Objetivo

Convertir el helpdesk en un producto SaaS multi-tenant: cada organización (empresa) tiene sus
propios admins, técnicos y clientes, y NO existe ningún camino por el que un usuario de una org
vea datos de otra. "AllSafe" pasa a ser la organización semilla de ejemplo — el producto es la
plataforma.

**Decisiones de brainstorm:**
1. **Modelo de negocio:** SaaS white-label (el producto se vende a empresas que traen sus
   propios técnicos y atienden a sus clientes).
2. **Membresía:** UNA organización por usuario (`User.organization` FK simple; null = staff de
   plataforma). Sin selector de org ni M2M.
3. **Aislamiento:** schema compartido + FK (MySQL; django-tenants es Postgres-only) con
   **helpers explícitos** concentrados en un módulo único + **tests adversariales** + guard de
   CI anti-queryset-crudo.
4. Las orgs se crean desde `/django-admin/` en H1 (registro self-service = H2). El staff de
   plataforma (superuser, org null) opera SÓLO por `/django-admin/`; ninguna vista in-app cruza
   tenants.

## Contexto técnico relevante (estado actual)

- Post-G: settings env-driven, Docker Compose, daphne, Redis condicional, front gatea por
  `role`, `check_sla --loop` como servicio, `/django-admin/`.
- `User.role` ∈ ADMIN/AGENT/CUSTOMER (pasa a significar rol DENTRO de su org).
- `Ticket.creado_por`/`asignado_a`; referencia `ALS-YYYYMMDD-NNN` generada en
  `tickets_t/serializers.py` con `select_for_update` sobre el prefijo del día.
- `SlaConfig` es **singleton** (`get_solo()`, pk=1) — H1 lo rompe: pasa a per-org.
  `SlaPolicy` (unique por priority) y `Holiday` (unique por date) son globales — ganan FK org y
  sus uniques pasan a ser compuestos (org, priority) / (org, date).
- `sla/calendar_engine.get_calendar()` lee el singleton; `checker.run_sla_check()` recorre
  TicketSla de tickets abiertos; `signals.py` crea TicketSla al crear ticket usando la policy de
  la prioridad.
- `notifications/services.dispatch()` resuelve destinatarios (asignado + admins → hoy TODOS los
  admins del sistema).
- `metrics/` agrega sobre queryset de tickets (`windowed_tickets`).
- `tickets_t/permissions.can_access_ticket` ya restringe por dueño/asignado/rol — pero un ADMIN
  hoy accede a TODO ticket (pasa a: todo ticket DE SU ORG).
- Consumers WS (`tickets_t/consumers.py`, notifications) autentican por cookie JWT y validan
  acceso vía `can_access_ticket`.

## Diseño

### 1. App nueva `tenancy/`

```
backend/tenancy/
  models.py        # Organization
  middleware.py    # request.organization
  scoping.py       # TODOS los querysets scoped del sistema
  tests.py         # unit de modelo/middleware
  tests_isolation.py  # suite adversarial cross-tenant
```

**`Organization`**: `name` (único), `slug` (único, corto, uppercase, usado como prefijo de
referencias de tickets), `is_active` (default True), `created_at`. Registrada en
`/django-admin/` con list/search.

### 2. Cambios de modelo (con data-migration semilla)

- `User.organization` — FK a Organization, `null=True` (null ⇔ staff de plataforma;
  se valida: usuario con role ADMIN/AGENT/CUSTOMER y org null sólo permitido si `is_superuser`).
- `Ticket.organization` — FK NOT NULL (denormalizada; se setea de `creado_por.organization` al
  crear). Índice sobre (organization, created_at).
- `SlaConfig`: se elimina el `SingletonManager`; pasa a `OneToOneField(Organization,
  related_name="sla_config")`. Al crear una org se crea su config con los defaults actuales
  (señal post_save de Organization o override de save en el admin — el plan fija el mecanismo).
- `SlaPolicy`: FK org + `unique_together (organization, priority)`. Al crear org se siembran las
  4 policies default (URGENT 30/240, HIGH 60/480, MEDIUM 120/960, LOW 240/1920).
- `Holiday`: FK org + `unique_together (organization, date)`.
- **Data-migration semilla** (una sola, al final de los cambios de schema): crea
  `Organization(name="AllSafe", slug="ALS")`; asigna esa org a todos los users con org null que
  NO sean superuser-sin-rol-operativo (regla simple: todos los users existentes → org semilla;
  el operador de plataforma se crea después a mano), a todos los tickets, y reasigna
  SlaConfig/SlaPolicy/Holiday existentes a la semilla. Reverse no-op. **Resultado: el deploy
  actual sigue idéntico con un tenant.**

### 3. Aislamiento — `tenancy/scoping.py` (fuente única)

Helpers puros (org → queryset), consumidos por TODAS las vistas/consumers/servicios:

- `org_tickets(org)` → `Ticket.objects.filter(organization=org)` (+select_related habituales)
- `org_users(org)`, `org_agents(org)` (role=AGENT), `org_admins(org)` (role=ADMIN)
- `org_sla_config(org)`, `org_policies(org)`, `org_holidays(org)`
- `user_org(user)` → org o None (plataforma)

**Middleware** (`tenancy.middleware.OrganizationMiddleware`, después de Authentication):
setea `request.organization = getattr(request.user, "organization", None)`. Usuario autenticado
sin org y sin `is_superuser` → 403 en API (cuenta mal provisionada, fail closed).

**Guard de CI**: test en `tenancy/tests.py` que escanea los `.py` del backend (fuera de
`tenancy/scoping.py`, migrations y tests) y FALLA si encuentra `Ticket.objects` — obliga a
pasar por los helpers. Lista de excepciones explícita en el propio test (p.ej.
`tickets_t/serializers.py` para la generación de referencia, justificado inline).

### 4. Cambios por app

**tickets_t:**
- `get_queryset`/`pool`: parten de `org_tickets(request.organization)`; dentro, la lógica actual
  por rol se mantiene (CUSTOMER → propios, AGENT → asignados/pool, ADMIN → todos LOS DE SU ORG).
- `can_access_ticket(user, ticket)`: primera condición nueva —
  `ticket.organization_id != user.organization_id → False` (para no-superusers). El resto igual.
- Creación: `organization=request.user.organization`; **referencia por slug**:
  `f"{org.slug}-YYYYMMDD-NNN"`, contador por org+día (el `select_for_update` actual ya filtra
  por prefijo, que ahora incluye el slug → sigue correcto).
- Consumer de chat: `user_can_access_ticket` ya delega en `can_access_ticket` (post-barrido) →
  hereda el check de org sin cambios adicionales.

**sla:**
- `get_calendar(org)` (firma cambia; lee la config de esa org).
- `signals.create_ticket_sla`: usa la policy de (org del ticket, prioridad).
- `checker.run_sla_check()`: agrupa TicketSla abiertos por org, un calendario por org;
  idempotencia intacta.
- `admin_views` (pantalla `/admin/sla` del tenant): operan sobre la config/policies/holidays de
  `request.organization`.

**notifications:** `dispatch()` resuelve admins con `org_admins(ticket.organization)`;
el consumer de notify no cambia (streams por usuario).

**metrics:** `windowed_tickets(window, org)` — ambos endpoints pasan `request.organization`;
benchmark del técnico = su org. Cero cambios de shape de respuesta.

**csat:** hereda por ticket (elegibilidad ya valida dueño). Sin cambios de API.

**users/admin del tenant:** el listado de usuarios del AdminDashboard y la creación de usuarios
quedan scoped a la org del admin (`org_users`), y el alta fuerza `organization=request.organization`.

**frontend:** cambios mínimos — mostrar `organization.name` en el TopBar (viene en `/api/me/`),
y nada más (cada rol ya ve "su mundo").

### 5. Suite adversarial (`tenancy/tests_isolation.py`)

Fixture: 2 orgs (A, B) completas (admin+agent+customer+tickets con SLA/CSAT cada una).
Matriz de ataques — para CADA rol de A contra recursos de B:
- detalle/lista de tickets (ID directo → 404), mensajes, eventos
- descarga de adjunto de B → 404/403
- WS de chat a ticket de B → conexión rechazada
- CSAT sobre ticket de B → 404
- métricas: totales del admin de A no incluyen tickets de B (conteos exactos)
- pool del técnico de A no lista tickets de B; `take` sobre ticket de B → 404
- admin de A no ve usuarios de B; no puede asignar técnico de B (validación de asignación:
  `asignado_a` debe pertenecer a la misma org)
- config SLA de A editada no toca la de B

Además: fixtures base de las suites existentes pasan a sembrar 2 orgs donde el costo sea bajo
(mínimo: metrics y sla), para que las agregaciones prueben no-mezcla.

## Manejo de errores y bordes

- Cross-tenant SIEMPRE 404 (no 403) para recursos con ID — no filtrar existencia.
- Usuario autenticado sin org (mal provisionado, no superuser) → 403 explícito del middleware.
- Org `is_active=False` → sus usuarios reciben 403 al autenticar (mensaje "organización
  suspendida") — enforcement en el middleware.
- Superuser de plataforma vía API in-app: se trata como sin-org → NO ve datos de tenants por la
  API (sólo por /django-admin/). Evita el "superuser ve todo" accidental en la app.
- El scheduler ignora orgs inactivas.

## Testing

- Suite adversarial completa (arriba) — es EL entregable de calidad de H1.
- Guard de CI anti-`Ticket.objects` crudo.
- Unit: migración semilla (todo lo existente queda en la org semilla), validación de asignación
  same-org, referencia con slug por org, calendario por org (2 orgs con ventanas distintas →
  deadlines distintos para el mismo created_at).
- Gate de merge: suite completa backend en DB fresca + build frontend.

## Fuera de alcance (H2/H3/H4)

Registro self-service, invitaciones, gestión de miembros por el admin del tenant (más allá del
alta básica scoped), billing/planes/límites, branding por tenant, subdominios, métricas de
plataforma, migración a M2M de membresía.

Ver [[allsafe-project-state]] y [[allsafe-conventions]].
