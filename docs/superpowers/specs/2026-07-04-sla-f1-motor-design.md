# SLA · F1 — Motor de SLA + semáforo

**Fecha:** 2026-07-04
**Sub-proyecto:** F1 (primera parte de F — SLAs + CSAT + métricas)
**Estado:** Diseño aprobado, pendiente de plan de implementación

## Objetivo

Dar al help-desk medición y visibilidad de acuerdos de nivel de servicio (SLA): dos relojes
por ticket (primera respuesta + resolución) con objetivos por prioridad, medidos en **tiempo
laboral** (L-V 9-18 + feriados), un **semáforo** de 3 estados por reloj, y **notificación
proactiva** al cruzar a en-riesgo/vencido vía un scheduler en proceso.

F se descompone en F1 (este spec: motor + semáforo + config), **F2 · CSAT** y
**F3 · Métricas/dashboards**. Cada uno con su propio ciclo spec→plan→SDD. F1 es la base.

## Contexto técnico relevante (estado actual)

- **Greenfield para SLA/CSAT** — no existe nada previo (`grep` sin resultados).
- `Ticket`: `prioridad` (LOW/MEDIUM/HIGH/URGENT), `estado` (OPEN/IN_PROGRESS/RESOLVED/CLOSED),
  `creado_por`, `asignado_a`, `created_at`, `updated_at`.
- **Audit trail `TicketEvent`** (kinds: created/assigned/unassigned/status_changed/reopened/
  priority_changed, con `created_at`) — da los datos crudos de timing, pero F1 guarda deadlines
  propios (no recomputa desde eventos en cada lectura).
- **Mensajes** se crean en `TicketChatConsumer.create_message` (WS) y en el endpoint de
  adjuntos `upload_attachment` (REST) — ambos son los puntos donde detectar la 1ª respuesta.
- **`_emit`** en `TicketViewSet` centraliza los eventos de ticket (incl. `status_changed`) —
  punto para detectar la resolución.
- **Notificaciones (Fase 2):** app `notifications` con `dispatch(kind, ticket, actor, extra)`,
  enum `Notification.Kind`, ruteo de destinatarios por kind, transporte WS `ws/notify/` +
  email presence-gated. F1 lo extiende con kinds de SLA.
- **Config singleton pattern:** `landing_cms.SiteSettings` + `_SingletonBase` (pk=1) — modelo
  a seguir para `SlaConfig`. Admin CRUD pattern en `landing_cms/admin_views.py`.
- `settings.TIME_ZONE = "UTC"`, `USE_TZ = True`, `LANGUAGE_CODE = "es-mx"`.
- **AppConfig.ready()** disponible para arrancar el hilo del scheduler (patrón estándar).

## Decisiones tomadas en el brainstorm

- Relojes: **primera respuesta + resolución**, objetivos **por prioridad**.
- Fin del reloj de 1ª respuesta = **primer mensaje de un AGENT/ADMIN** en el chat.
- Calendario: default **America/Mexico_City**; el admin edita ventana (días+horas, default
  L-V 9-18), zona horaria y feriados.
- Semáforo: **3 estados** (verde/amarillo/rojo) con umbral de "en riesgo" **configurable**
  (default 25% del presupuesto restante).
- Detección: **scheduler en proceso** que notifica al cruzar de nivel (con el resguardo de que
  el hilo es un wrapper sobre una función reusable + management command).

## Enfoque elegido: deadlines guardados + nivel on-read + scheduler idempotente (Opción A)

Al crear el ticket se calculan y persisten los deadlines (con la matemática de tiempo laboral).
El nivel del semáforo se computa on-the-fly al leer (now vs deadline). El scheduler notifica
sólo al **cruzar** de nivel, guardando el último nivel notificado por reloj → sin duplicados.
Alternativas descartadas: recomputar todo desde `TicketEvent` en cada lectura (caro, sin
detección de transiciones) y guardar deadlines sin scheduler (no notifica).

## Diseño

### 1. Modelos (app nueva `sla/`)

```
SlaConfig  (singleton, pk=1, patrón _SingletonBase)
  business_timezone         Char   default "America/Mexico_City"
  work_days                 Char   default "1,2,3,4,5"   # ISO weekday 1=Lun..7=Dom (L-V)
  work_start                Time   default 09:00
  work_end                  Time   default 18:00
  at_risk_threshold_pct     PositiveInt  default 25       # % de presupuesto restante
  scheduler_interval_minutes PositiveInt default 10
  scheduler_enabled         Bool   default True

SlaPolicy   (una por prioridad; seed 4 filas)
  priority                  Char unique (choices = Ticket.Priority)
  first_response_minutes    PositiveInt   # minutos de tiempo laboral
  resolution_minutes        PositiveInt
  # Defaults seed: URGENT 30/240, HIGH 60/480, MEDIUM 120/960, LOW 240/1920

Holiday
  date                      Date unique
  name                      Char

TicketSla   (OneToOne Ticket, related_name="sla", created al crear el ticket)
  first_response_due_at     DateTime null
  first_response_met_at     DateTime null
  resolution_due_at         DateTime null
  resolved_at               DateTime null
  fr_level                  Char default "ok"   # último nivel notificado: ok|at_risk|breached|met
  res_level                 Char default "ok"
```

### 2. Motor de calendario (`sla/calendar_engine.py`, puro y testeable)

- `get_calendar() -> Calendar`: lee `SlaConfig` + `Holiday` y arma un objeto con tz, días/horas
  laborales y set de feriados. (Nombre `calendar_engine` para no chocar con el stdlib `calendar`.)
- `add_business_time(start_dt, minutes, cal) -> datetime`: suma `minutes` minutos de tiempo
  laboral a `start_dt`, salteando fuera-de-horario, fines de semana y feriados. Trabaja en la
  tz del negocio y devuelve UTC-aware.
- `business_minutes_between(a, b, cal) -> int`: minutos laborales entre dos datetimes.
- `compute_levels(ticket_sla, now, cal) -> {"fr": level, "res": level}`: para cada reloj —
  `met` si el `*_met_at`/`resolved_at` está seteado; si no: `breached` si `now > due`; `at_risk`
  si el tiempo laboral restante ≤ `at_risk_threshold_pct`% del presupuesto total; si no `ok`.

### 3. Hooks en el flujo existente

- **Crear ticket** (`TicketViewSet.perform_create`): tras crear el ticket, crear su `TicketSla`
  con `first_response_due_at = add_business_time(created_at, policy.first_response_minutes)` y
  `resolution_due_at = add_business_time(created_at, policy.resolution_minutes)`.
- **1ª respuesta** (`create_message` del consumer **y** `upload_attachment`): helper
  `mark_first_response(ticket, sender)` — si `sender` es AGENT/ADMIN y `first_response_met_at`
  vacío, setearlo a now y `fr_level="met"`. Idempotente. Envuelto en try/except (no debe romper
  el chat, igual que el dispatch de notificaciones).
- **Resolución** (`_emit`, cuando el nuevo estado es RESOLVED): setear `resolved_at=now`,
  `res_level="met"` si aún no estaba. Vía `transaction.on_commit` como el resto de `_emit`.
- **Cambio de prioridad** (`_emit`, `priority_changed`): recomputar los deadlines **no cumplidos**
  (`first_response_met_at`/`resolved_at` vacíos) con la nueva política, desde `ticket.created_at`.

### 4. Scheduler + notificaciones

- `sla/checker.py::run_sla_check()`: recorre `Ticket` con estado en (OPEN, IN_PROGRESS) que
  tengan `TicketSla`; computa niveles; para cada reloj cuyo nivel computado **avanzó** respecto
  del guardado (`ok→at_risk→breached`) → `dispatch(kind, ticket, actor=None, ...)` y persiste el
  nuevo nivel. Idempotente: nunca re-notifica el mismo nivel. Devuelve un resumen (contadores).
- Management command **`check_sla`** (`sla/management/commands/check_sla.py`) → llama
  `run_sla_check()`. Para cron/fallback y para prod hasta Celery.
- **Hilo scheduler** en `SlaConfig`'s AppConfig `ready()`: si `os.environ.get("RUN_MAIN")` (evita
  duplicado del autoreloader) y `SlaConfig.scheduler_enabled`, arranca un `threading.Thread`
  daemon que hace loop: `sleep(interval*60)` → `run_sla_check()` dentro de try/except (un error
  no mata el loop). *(Prod → Celery beat en G; el hilo es conveniencia de dev.)*
- **Notificaciones:** extender `notifications.Notification.Kind` con `SLA_AT_RISK="sla_at_risk"`
  y `SLA_BREACHED="sla_breached"`, y agregar su ruteo en `notifications/services.py`
  (`_recipients_for`): destinatarios = **técnico asignado** (si hay) + **admins**; título/cuerpo
  en voseo (ej. "El ticket {ref} está por vencer / venció su SLA de {reloj}"). **F1 notifica SLA
  sólo in-app** (toast + campanita): los specs de SLA en `_recipients_for` no marcan `email`, así
  que no tocan el gate de presence ni las preferencias de email. (Email dedicado de SLA → futuro.)

### 5. API + serializer

- **`TicketSerializer`** suma `sla` (SerializerMethodField, on-read): calcula niveles con
  `compute_levels` y devuelve `{"first_response": {"level", "due_at"}, "resolution": {"level",
  "due_at"}}`. Null si el ticket no tiene `TicketSla`.
- **API admin** (`/api/admin/sla/`, permiso admin):
  - `GET/PATCH policies/` — lista/edita las 4 `SlaPolicy`.
  - `GET/PATCH config/` — singleton `SlaConfig`.
  - `GET/POST/DELETE holidays/` — CRUD de `Holiday`.

### 6. Frontend

- **`SlaBadge.vue`**: recibe el objeto `sla` de un ticket; muestra los dos relojes como dot de
  color (verde `ok` / amarillo `at_risk` / rojo `breached` / ✓ `met`) + label del reloj +
  tiempo restante o "vencido". Hairline v2. Se usa en:
  - **Cliente** (`ClientDashboard`): en su lista/detalle de tickets.
  - **Técnico** (`TechnicianDashboard`): en la lista "Mis tickets".
  - **Admin** (`AdminDashboard`): una columna en la tabla.
- **Pantalla admin de SLA** (`/admin/sla`, ruta nueva, layout admin): editar políticas
  (4 prioridades × 2 duraciones), ventana laboral (días/horas/TZ), umbral de riesgo, y CRUD de
  feriados. `api/sla.api.js` con los wrappers.

### 7. Testing

Backend (foco — el motor es la parte crítica):
- Calendario: `add_business_time` cruzando noche, fin de semana y feriado; suma dentro del mismo
  día; `business_minutes_between`; borde exacto de fin de jornada.
- `compute_levels`: los 4 niveles por reloj (ok/at_risk/breached/met) con un umbral dado.
- Hooks: deadlines correctos al crear (por prioridad); `mark_first_response` idempotente y sólo
  para AGENT/ADMIN; `resolved_at` al pasar a RESOLVED; recomputo de deadlines no cumplidos al
  cambiar prioridad.
- `run_sla_check`: notifica una vez al cruzar a at_risk y una vez a breached; NO re-notifica el
  mismo nivel en corridas sucesivas (idempotencia); ignora tickets resueltos/cerrados.
- API admin: permiso (no-admin 403), get/patch config y policies, CRUD holidays.
- El **hilo** NO se testea; sí `run_sla_check()` (que es lo que el hilo invoca).

Frontend: build limpio + checklist manual (semáforo con datos sembrados; pantalla de config).

## Fuera de alcance (YAGNI, ciclos futuros)
- Métricas agregadas / dashboards de cumplimiento y CSAT → **F3**.
- CSAT (encuesta post-resolución) → **F2**.
- Pausa de SLA por "esperando al cliente" (no existe ese estado hoy).
- Celery/Redis para el scheduler real → **G** (el hilo in-process es dev; el management command
  `check_sla` es el puente a cron/prod).
- Reapertura: el reloj de resolución se mide a la **primera** resolución; reabrir no crea un
  reloj nuevo (se afina en F3 si las métricas lo requieren).
- Email dedicado de SLA con preferencia propia (F1 notifica in-app).
