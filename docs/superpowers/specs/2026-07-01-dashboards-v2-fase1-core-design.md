# AllSafe — Dashboards v2, Fase 1 (Core) — Diseño

**Fecha:** 2026-07-01
**Sub-proyecto:** D1-Fase1 (parte de "Dashboards v2 + Comunicación + Enriquecimiento")
**Estado:** Aprobado por el usuario, listo para `writing-plans`

---

## 1. Contexto y posicionamiento

AllSafe ya tiene: landing pública + mini-CMS, sistema de tickets (backend), 3 dashboards básicos y chat en vivo por WebSocket. Los dashboards **están rotos como producto**:

- El técnico no tiene dashboard (solo `router.replace` a inbox). No puede ver métricas propias.
- El cliente ve stat cards que no le importan, ocupando espacio de la lista + chat.
- El pool de tickets nuevos sin asignar es invisible para los técnicos; el admin es cuello de botella.
- El backend no valida quién puede ser asignado; un PATCH directo asigna un ticket a cualquier usuario.
- El WebSocket usa una URL hardcoded (`ws://localhost:8000/...`), no reconecta si el server se cae, y no muestra estado.
- Las transiciones de estado no tienen reglas: RESOLVED → OPEN es posible sin restricción.
- Los dashboards siguen con paleta vieja (azul cobalto Tailwind); no se rediseñaron con la v2.

Descomposición del sub-proyecto completo (Dashboards v2):

| Fase | Contenido | Estado |
|---|---|---|
| **F1 — Core** | Bugs backend, UX invertida, WS reconnect, auditoría, rediseño dashboards paleta v2 | **Este spec** |
| F2 — Comunicación | Notif toast in-app, notif email, config SMTP | Futuro (spec propio) |
| F3 — Enriquecimiento | Adjuntos en chat, filtros + orden en tablas | Futuro (spec propio) |

## 2. Objetivo

Convertir los dashboards en algo utilizable en producción: bugs de permisos arreglados, roles con vistas apropiadas, chat resistente, look coherente con la landing v2. Al terminar F1 se puede vender/usar la app sin vergüenza.

## 3. Alcance

### 3.1 Incluido

- **Backend**
  - Validación server-side de `Ticket.asignado_a`: solo AGENT o superuser.
  - Endpoint `GET /api/tickets/pool/` — tickets sin asignar (AGENT y ADMIN pueden verlo).
  - Endpoint `POST /api/tickets/{id}/take/` — el AGENT autenticado se auto-asigna. Idempotente si ya lo tomó él; rechaza si otro lo tiene.
  - Reglas de transición de estado: OPEN → IN_PROGRESS → RESOLVED → CLOSED. Solo ADMIN puede reabrir (volver a OPEN desde RESOLVED/CLOSED).
  - Modelo `TicketEvent` para auditoría: tipo evento + actor + timestamp + payload opcional.
  - Registro automático de eventos: `ticket.created`, `ticket.assigned`, `ticket.status_changed`, `ticket.reopened`.
- **Frontend**
  - `ClientDashboard`: sin stat cards. Lista lateral + chat central + botón "Nuevo ticket" (ya existente).
  - `TechnicianDashboard`: reemplaza el redirect. Tabs "Mis tickets" + "Pool disponible". Stat cards propias arriba (asignados abiertos / resueltos hoy / resueltos esta semana). En "Pool", cada ticket tiene botón "Tomar".
  - `AdminDashboard`: mantiene funcionalidad; adopta hairline dividers, elimina sombras pesadas, tipografía v2.
  - `AppTopBar`: agrega theme toggle (reutiliza `useTheme`).
  - `ChatPanel`:
    - URL derivada de `window.location` (protocolo `ws://` en dev HTTP, `wss://` en HTTPS).
    - Reconnect automático con backoff `1s → 2s → 4s → 8s → 16s` (max 5 intentos).
    - Badge de conexión en el header: `● conectado` (verde), `● reconectando…` (naranja pulsante), `● desconectado` (gris).
  - `TicketDetail` (nuevo, dentro del chat): timeline compacto de eventos de auditoría al pie del chat (colapsable), leído por `GET /api/tickets/{id}/events/`.
  - Paleta v2 aplicada a todos los dashboards (Space Grotesk display, Inter body, JetBrains Mono utility, azul eléctrico como accent).

### 3.2 Excluido (out of scope)

- Notificaciones toast in-app y por email (Fase 2).
- Adjuntos en chat (Fase 3).
- Filtros + orden avanzados en tablas (Fase 3).
- IA en el chat (sub-proyecto independiente).
- CSAT / encuesta post-cierre (retomar del sub-proyecto original #1 pausado).
- Notificaciones push del navegador.

## 4. Arquitectura general

- **Backend**: cambios contenidos en `tickets_t/` (models, serializers, views, permissions). Nueva migración para `TicketEvent`. Sin nuevas apps.
- **Frontend**: cambios en `dashboards/*.vue`, `ChatPanel.vue`, `AppTopBar.vue`. Un composable nuevo `useWsConnection` que aísla la lógica de reconnect + backoff.
- **Auditoría**: eventos se escriben en `TicketEvent` desde el `TicketViewSet` (perform_create, perform_update) y desde el `take` action. Frontend los lee bajo demanda cuando se abre un ticket.

## 5. Backend — Cambios

### 5.1 Modelo `TicketEvent` (nuevo)

Archivo: `backend/tickets_t/models.py`.

```
class TicketEvent(models.Model):
    class Kind(models.TextChoices):
        CREATED = "created", "Creado"
        ASSIGNED = "assigned", "Asignado"
        UNASSIGNED = "unassigned", "Desasignado"
        STATUS_CHANGED = "status_changed", "Cambio de estado"
        REOPENED = "reopened", "Reabierto"
        PRIORITY_CHANGED = "priority_changed", "Cambio de prioridad"

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="events")
    kind = models.CharField(max_length=32, choices=Kind.choices)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)  # ej. {"from": "OPEN", "to": "IN_PROGRESS"}
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["ticket", "created_at"])]
```

Migración inicial. Antes de correr `makemigrations`, verificar la última migración de la app con `python backend/manage.py showmigrations tickets_t`. Nombrar el archivo `0002_ticketevent.py` o `0003_ticketevent.py` según corresponda.

### 5.2 Validación de `asignado_a`

Archivo: `backend/tickets_t/serializers.py`, `TicketSerializer.validate_asignado_a`:

```python
def validate_asignado_a(self, value):
    if value is None:
        return value
    if not (value.is_superuser or getattr(value, "role", None) == "AGENT"):
        raise serializers.ValidationError("Solo se puede asignar a técnicos (rol AGENT).")
    return value
```

### 5.3 Transiciones de estado

Archivo: `backend/tickets_t/serializers.py`, `TicketSerializer.validate_estado`:

```python
ALLOWED_TRANSITIONS = {
    "OPEN": {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"},
    "IN_PROGRESS": {"IN_PROGRESS", "RESOLVED", "CLOSED"},
    "RESOLVED": {"RESOLVED", "CLOSED"},  # forward only
    "CLOSED": {"CLOSED"},                 # terminal salvo ADMIN reopen
}

def validate_estado(self, value):
    if not self.instance:
        return value
    current = self.instance.estado
    request = self.context.get("request")
    is_admin = bool(request and (request.user.is_superuser or getattr(request.user, "role", None) == "ADMIN"))
    if is_admin and current in ("RESOLVED", "CLOSED") and value == "OPEN":
        return value  # reopen permitido a ADMIN
    if value not in ALLOWED_TRANSITIONS.get(current, {value}):
        raise serializers.ValidationError(
            f"Transición no permitida: {current} → {value}."
        )
    return value
```

### 5.4 Endpoints nuevos

Archivo: `backend/tickets_t/views.py`, `TicketViewSet`:

```python
@action(detail=False, methods=["get"], url_path="pool")
def pool(self, request):
    user = request.user
    r = getattr(user, "role", None)
    if r not in ("AGENT", "ADMIN") and not user.is_superuser:
        return Response(status=403)
    qs = Ticket.objects.filter(asignado_a__isnull=True).order_by("-created_at")
    return Response(TicketSerializer(qs, many=True, context={"request": request}).data)

@action(detail=True, methods=["post"], url_path="take")
def take(self, request, pk=None):
    user = request.user
    if not (getattr(user, "role", None) == "AGENT" or user.is_superuser):
        return Response({"detail": "Solo técnicos pueden tomar tickets."}, status=403)
    ticket = self.get_object()  # respeta get_queryset
    if ticket.asignado_a_id and ticket.asignado_a_id != user.id:
        return Response({"detail": "El ticket ya tiene un técnico asignado."}, status=409)
    ticket.asignado_a = user
    ticket.save(update_fields=["asignado_a"])
    TicketEvent.objects.create(ticket=ticket, kind="assigned", actor=user, payload={"self_take": True})
    return Response(TicketSerializer(ticket, context={"request": request}).data)

@action(detail=True, methods=["get"], url_path="events")
def events(self, request, pk=None):
    ticket = self.get_object()  # permisos vía get_queryset
    return Response(TicketEventSerializer(ticket.events.all(), many=True).data)
```

Nota: `pool` no respeta `get_queryset` (que filtra por `asignado_a=user` para AGENT). Es intencional — el pool es explícitamente lo que no tiene asignado.

### 5.5 Queryset del AGENT (leve ajuste)

`get_queryset` de `TicketViewSet` sigue devolviendo solo los asignados para el AGENT en la tab "Mis tickets". El pool se accede vía la action separada. **No cambia el queryset base.** Motivo: la separación en el UI es via tabs, no vía un solo listado.

### 5.6 Registro automático de eventos

En `perform_create` (Ticket nuevo → `Kind.CREATED`), y en `perform_update` (comparar campos anteriores con nuevos y emitir los events correspondientes). Actor = `request.user`.

Uso de un método privado `_emit_events(old_instance, new_instance, actor)` que compara `estado`, `asignado_a_id`, `prioridad` y emite los events.

### 5.7 TicketEventSerializer

Archivo: `backend/tickets_t/serializers.py`:

```python
class TicketEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True, default=None)
    class Meta:
        model = TicketEvent
        fields = ["id", "kind", "actor", "actor_username", "payload", "created_at"]
```

### 5.8 Tests

`backend/tickets_t/tests.py` (o nuevo `tests/test_dashboards_v2.py`):
1. `test_asignar_customer_falla` — un ADMIN intenta PATCH `asignado_a=<customer_id>`, esperar 400.
2. `test_asignar_agent_ok` — ADMIN PATCH `asignado_a=<agent_id>`, esperar 200.
3. `test_transicion_valida` — IN_PROGRESS → RESOLVED, esperar 200.
4. `test_transicion_invalida_backward` — RESOLVED → IN_PROGRESS con AGENT/CUSTOMER, esperar 400.
5. `test_admin_reopen` — ADMIN PATCH CLOSED → OPEN, esperar 200.
6. `test_take_endpoint_ok` — AGENT toma ticket sin asignar, ticket queda con `asignado_a=él` y hay `TicketEvent`.
7. `test_take_conflict` — otro AGENT intenta tomar el mismo ticket, esperar 409.
8. `test_pool_only_unassigned` — endpoint devuelve solo tickets con `asignado_a__isnull=True`.
9. `test_pool_forbidden_customer` — CUSTOMER llama a `pool`, esperar 403.

## 6. Frontend — Cambios

### 6.1 Composable `useWsConnection`

Archivo nuevo: `frontend/src/composables/useWsConnection.js`.

Interfaz:
```js
const { status, messages, send, close } = useWsConnection({
  url: () => `ws://localhost:8000/ws/chat/${ticketId}/`,  // función porque puede depender de props
  onMessage: (data) => { ... },
});
// status: ref('connecting' | 'connected' | 'reconnecting' | 'disconnected')
```

Lógica:
- Al montar: llama `connect()`.
- `connect()` crea el WebSocket, setea `status='connecting'`.
- `onopen`: `status='connected'`, resetea backoff.
- `onclose`: si `attempts < 5`, `status='reconnecting'`, agenda `setTimeout` con backoff `[1000, 2000, 4000, 8000, 16000][attempts]`. Si agotó intentos, `status='disconnected'`.
- `close()` explícito: no reintenta.
- Al desmontar: `close()`.

Uso de `window.location.protocol === "https:"` para elegir `wss://` vs `ws://`. Host: `window.location.host` en producción, `localhost:8000` en dev (env `VITE_WS_HOST`).

Archivo `.env` del frontend documenta `VITE_WS_HOST=localhost:8000` para dev.

### 6.2 `ChatPanel.vue`

- Reemplaza el manejo manual del WS por `useWsConnection`.
- Header: badge de conexión al lado del título.
  - `● conectado` verde
  - `● reconectando…` naranja pulsante
  - `● desconectado` gris con botón "Reintentar".
- Reset del historial cuando `ticketId` cambia (ya funciona).
- Timeline de auditoría al pie: `<TicketEventTimeline :events="events" />` colapsable (colapsado por default), carga vía `GET /api/tickets/{id}/events/` al montar.

### 6.3 `TicketEventTimeline.vue` (nuevo)

Componente compacto que renderiza una lista de eventos:
- Ícono según `kind` (created = star, assigned = user-check, status_changed = arrow-right, reopened = refresh).
- Texto humano: "Ana asignó a Pedro", "Estado: OPEN → IN_PROGRESS", "Reabierto por Admin".
- Timestamp relativo ("hace 3 h").
- Estilo hairline, mono para timestamps.

### 6.4 `ClientDashboard.vue`

- Eliminar `<div class="stats-row">` completo (líneas 6-23).
- Aumentar tamaño del chat: el `.main-area` puede ganar el espacio libre.
- Aplicar tipografía v2 en labels y bordes (usar `var(--font-display)` en `.ticket-title`, `var(--font-mono)` en `.ticket-ref` y `.ticket-date`).

### 6.5 `TechnicianDashboard.vue` (rehecho)

- Reemplazar el `router.replace` por dashboard real.
- Estructura:
  ```
  <AppTopBar title="Panel del técnico" />
  <StatsRow>
    <StatCard label="Asignados abiertos" :value="stats.open" />
    <StatCard label="En proceso" :value="stats.in_progress" />
    <StatCard label="Resueltos hoy" :value="stats.resolved_today" />
    <StatCard label="Resueltos esta semana" :value="stats.resolved_week" />
  </StatsRow>
  <Tabs>
    <Tab id="mine" label="Mis tickets" :count="mine.length">
      <TicketListWithChat :tickets="mine" />
    </Tab>
    <Tab id="pool" label="Pool disponible" :count="pool.length">
      <PoolList :tickets="pool" @take="onTake" />
    </Tab>
  </Tabs>
  ```
- `mine` viene de `GET /api/tickets/` (queryset ya filtra por `asignado_a=user` para AGENT).
- `pool` viene de `GET /api/tickets/pool/`.
- `stats` se calcula client-side sobre `mine`: `open`, `in_progress`, `resolved_today` (filtra por `updated_at >= today` + `estado === "RESOLVED"`), `resolved_week` (últimos 7 días).
- Al tomar (`onTake(ticket)`): `POST /api/tickets/{id}/take/`, mover el ticket de `pool` a `mine`, seleccionar en la lista.

### 6.6 `PoolList.vue` (nuevo)

Componente compacto. La lógica de "lista de tickets con click para abrir chat" hoy vive **inline** en `ClientDashboard.vue` (aside con `.ticket-item`); durante F1 no la refactorizamos globalmente. `PoolList` es un componente distinto con estas características:
- Cards ordenados por `created_at` desc.
- Cada card muestra: prioridad dot, referencia, título, tiempo relativo, botón "Tomar".
- El botón `Tomar` emite `@take(ticket)`.

### 6.7 `AdminDashboard.vue`

- Mantiene lógica.
- Aplica hairline dividers: reemplaza `border: 1px solid var(--border)` en cards por `border: 0.5px solid var(--border)` y quita `box-shadow: var(--shadow-sm)`.
- Tipografía: `var(--font-display)` en headings y valores, `var(--font-mono)` en labels y referencias.
- Stat cards siguen ordenadas pero con estilo v2 (menos peso visual).

### 6.8 `AppTopBar.vue`

- Agregar botón theme toggle a la derecha (mismo componente que en `PublicHeader`).
- Aplicar tipografía v2 en el título.
- Mantiene menú usuario / logout ya existente.

### 6.9 Estilos v2 en tokens

Los tokens ya se actualizaron en el rediseño de la landing (Task 55). Los dashboards heredan automáticamente. Solo hay que:
- Reemplazar `font-family: -apple-system, BlinkMacSystemFont, ...` por `var(--font-body)` en `body` (ya hecho).
- Añadir `font-family: var(--font-display)` explícito en `.stat-value`, `.header-title`, `.ticket-title`, `.list-name`.
- Añadir `font-family: var(--font-mono)` en `.mono`, `.ticket-ref`, `.ticket-date`, `.eyebrow-label`.

## 7. Datos y migraciones

- Nueva migración: `0003_ticketevent.py` (o el número que corresponda).
- Migración de datos opcional: registrar un evento `created` para cada Ticket existente con `actor=creado_por`. **Incluido en la Fase 1** — hace que el timeline funcione para tickets viejos.

## 8. UX y comportamiento

### 8.1 Cliente
- Al entrar: lista + chat. Si tiene 0 tickets, empty state con CTA "Crear tu primer ticket".
- El chat muestra el timeline de eventos colapsado al pie (opcional, click para ver).

### 8.2 Técnico
- Al entrar: tab "Mis tickets" activa. Si tiene 0 asignados pero hay pool > 0, muestra hint "Hay N tickets sin asignar en el pool".
- Al tomar un ticket del pool, el técnico se cambia automáticamente a la tab "Mis tickets" con el ticket seleccionado.
- Si pierde conexión WS, el chat muestra el badge naranja pulsante y no bloquea el composer (el mensaje puede quedar en cola para reenviar cuando reconecte).

### 8.3 Admin
- Sin cambios funcionales grandes. Look coherente con lo demás.

## 9. Seguridad

- `validate_asignado_a`: solo AGENT/superuser. Cubre PATCH directo.
- `take` action: solo AGENT/superuser.
- `pool` action: solo AGENT/ADMIN/superuser (CUSTOMER 403).
- State transitions: server-side. Cliente puede enviar cualquier cosa; server rechaza.
- `events` action: respeta `get_queryset`. Un CUSTOMER solo ve events de sus propios tickets.

## 10. Testing

- Backend: 9 tests nuevos (Sec 5.8).
- Frontend: smoke manual — abrir cliente, abrir técnico, tomar ticket del pool, ver evento en timeline, reconectar chat matando y arrancando backend.
- Regresión: correr suite backend completa; landing_cms sigue en 30/30.

## 11. Riesgos y trade-offs

| Riesgo | Mitigación |
|---|---|
| Migración de eventos históricos para tickets pre-existentes | Hacerlo en migración de datos, no en runtime. Tickets sin eventos también funcionan (timeline vacío). |
| `pool` action expone todos los tickets sin asignar a cualquier AGENT | Aceptado — es el diseño. Si más adelante hay múltiples equipos, se agrega filtro por equipo. |
| Reconnect infinito si el server nunca vuelve | Backoff limitado (5 intentos, 31s total). Después el usuario debe recargar. |
| El botón "Tomar" puede tener race: dos técnicos hacen click al mismo tiempo | El endpoint `take` chequea `if ticket.asignado_a_id` y devuelve 409. El primer request gana. UX: mostrar "Otro técnico tomó este ticket" al perder. |
| Costos: tests con auditoría hacen más writes por request | Insignificante en dev/prod para el volumen esperado. |

## 12. Estimación gruesa

| Bloque | Esfuerzo |
|---|---|
| Backend (modelo, migraciones, serializers, endpoints, eventos) | 2 días |
| Composable `useWsConnection` + refactor ChatPanel | 1 día |
| TechnicianDashboard nuevo (tabs, stats, pool, take) | 1.5 días |
| ClientDashboard limpieza + timeline | 0.5 día |
| AdminDashboard restyle v2 | 0.5 día |
| AppTopBar theme toggle + micro-restyles | 0.5 día |
| Tests backend + verificación manual | 1 día |
| **Total F1** | **~7 días** |

## 13. Out of scope explícito (para futuras fases)

- Notificaciones toast in-app (F2)
- Notificaciones por email + config SMTP (F2)
- Adjuntos en el chat (F3)
- Filtros + orden avanzados (F3)
- IA en el chat (sub-proyecto separado)
- CSAT / encuesta post-cierre
- Auto-asignación round-robin
- Multi-tenant / multi-team

---

**Próximo paso:** revisión del usuario; al aprobar, se invoca `superpowers:writing-plans` para producir el plan de implementación de F1.
