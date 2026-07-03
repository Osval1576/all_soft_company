# Dashboards v2 · Fase 2 — Comunicación (notificaciones in-app + email)

**Fecha:** 2026-07-03
**Sub-proyecto:** D (roadmap AllSafe)
**Estado:** Diseño aprobado, pendiente de plan de implementación

## Objetivo

Cerrar el loop de comunicación del help-desk: que cada actor se entere de lo que le
concierne sin tener que estar mirando la vista correcta. Dos canales:

1. **In-app**: toast efímero + centro de notificaciones persistido (campanita con
   badge de no-leídas e historial).
2. **Email**: avisos por SMTP para los eventos de alto valor, con preferencias
   granulares por usuario (opt-out por tipo de evento).

Continúa Dashboards v2 Fase 1 (Core), que dejó el audit trail (`TicketEvent`),
los endpoints `pool`/`take`/`events` y el WS de chat resiliente (`useWsConnection`).

## Contexto técnico relevante (estado actual)

- **Mensajes de chat**: se crean **sólo** vía WebSocket, dentro de
  `TicketChatConsumer.receive()` → `create_message()` (no hay endpoint REST de
  escritura). WS por-ticket: `ws/chat/{id}/`, grupo `ticket_{id}`.
- **Eventos de ticket** (`created`, `assigned`, `unassigned`, `status_changed`,
  `reopened`, `priority_changed`): se emiten vía REST en `TicketViewSet` a través de
  un único helper `_emit()` → `TicketEvent.objects.create(...)`.
- **Auth WS**: `JwtCookieAuthMiddleware` lee la cookie `access` y setea `scope["user"]`.
  Un consumer nuevo hereda esta auth sin cambios.
- **Channels**: `InMemoryChannelLayer` (mono-proceso; el fan-out por-usuario funciona
  dentro del `runserver`). Redis queda para el sub-proyecto G.
- **Email**: no hay `EMAIL_BACKEND` configurado. Se parte de cero.
- **Frontend shell**: `App.vue` es sólo `<router-view/>`. Cada dashboard
  (`ClientDashboard`, `TechnicianDashboard`, `AdminDashboard`) es una ruta top-level y
  monta su propio `AppTopBar`. **No hay shell persistente compartido**, por lo que el
  socket de notificaciones no puede vivir dentro de una vista (se desmontaría al navegar).
- **Roles**: `CUSTOMER`, `AGENT`, `ADMIN` (+ `is_superuser`). En el router el gating usa
  `is_staff` (AGENT) / `is_superuser` (ADMIN).

## Matriz de eventos → destinatarios

`in-app` = toast + fila de notificación persistida. `✉️` = además email (sujeto a
preferencia del destinatario).

| Evento                          | CUSTOMER (dueño) | AGENT (asignado)      | ADMIN        | Pool (técnicos libres)          |
|---------------------------------|------------------|-----------------------|--------------|---------------------------------|
| Ticket **creado** (nuevo)       | —                | —                     | in-app ✉️    | in-app (hay ticket sin tomar)   |
| Ticket **asignado / tomado**    | in-app ✉️        | in-app                | —            | —                               |
| **Nuevo mensaje** en el chat    | in-app ✉️*       | in-app ✉️*            | —            | —                               |
| **Cambio de estado** (resuelto/cerrado) | in-app ✉️  | —                     | —            | —                               |

\* El email de "nuevo mensaje" se envía **sólo si el destinatario NO está online**
(presence tracking). Si está conectado a la app, ya recibió el toast y no se le manda mail.

Notas:
- "Pool (técnicos libres)" = usuarios AGENT (o superuser con rol técnico) para avisar de
  un ticket nuevo sin asignar. Toast in-app, sin email.
- El toast de "nuevo mensaje" se **suprime en el frontend** para el ticket que el usuario
  tiene abierto en ese momento (ya ve el mensaje en vivo).
- "Cambio de estado" notifica al cliente cuando pasa a `RESOLVED` o `CLOSED`.

## Enfoque elegido: dispatcher explícito (Opción B)

Todos los eventos pasan por exactamente dos embudos:

- **Mensajes** → `create_message()` en el consumer.
- **Eventos de ticket** → `_emit()` en el `TicketViewSet`.

En vez de `post_save` signals (footguns de timing de transacción + contexto async del
consumer), se llama a un **dispatcher explícito** desde esos dos puntos. Sólo dos call
sites, control total sobre destinatarios / presence / email.

## Diseño

### 1. Backend — app nueva `notifications/`

Modelos:

```
Notification
  recipient   FK users.User (related_name="notifications", on_delete CASCADE)
  kind        CharField choices: ticket_created | assigned | new_message
                                 | status_changed | resolved
  ticket      FK tickets_t.Ticket (null=True, on_delete SET_NULL)   # deep-link
  actor       FK users.User (null=True, on_delete SET_NULL, related_name="+")
  title       CharField(200)   # texto ya renderizado (voseo)
  body        CharField(255)   # línea secundaria
  is_read     BooleanField default False
  created_at  DateTimeField auto_now_add
  Meta: ordering ["-created_at"], indexes [(recipient, is_read)]

NotificationPreference   (OneToOne User, related_name="notif_prefs", defaults True)
  email_on_assigned        Bool   # aplica a CUSTOMER
  email_on_new_message     Bool   # CUSTOMER + AGENT
  email_on_status_changed  Bool   # CUSTOMER (resuelto/cerrado)
  email_on_ticket_created  Bool   # ADMIN
```

`NotificationPreference` se crea on-demand (get_or_create con defaults) al leerla o al
evaluar un email; no requiere backfill de usuarios existentes.

### 2. Backend — dispatcher, presence, transporte, email

- **`notifications/services.py`** → `dispatch(kind, ticket, actor=None, extra=None)`:
  1. Calcula destinatarios según la matriz (excluyendo al `actor` — no te notificás a vos mismo).
  2. Renderiza `title`/`body` en español (voseo).
  3. Crea una fila `Notification` por destinatario.
  4. `group_send("user_{id}", {...})` a cada destinatario conectado (toast + badge).
  5. Decide email por destinatario: consulta `NotificationPreference` (get_or_create) y,
     para `new_message`, además el gate de presence.
- **`NotifyConsumer`** en `ws/notify/`:
  - on connect (autenticado): marca `presence:user:{id}` en cache (TTL 60s) y
    `group_add("user_{id}")`. Rechaza anónimos (code 4401).
  - `receive`: maneja `{"type": "ping"}` refrescando el TTL de presence.
  - handler `notify_message(event)` → reenvía el payload al socket.
  - on disconnect: `cache.delete("presence:user:{id}")` + `group_discard`.
- **Presence** vía `django.core.cache` (LocMemCache hoy → Redis en G sin tocar lógica).
  Helpers `mark_online(user_id)`, `is_online(user_id)`, `mark_offline(user_id)`.
- **Email**:
  - Backend por env: si hay `EMAIL_HOST` (Mailtrap dev) usar SMTP; si no,
    `django.core.mail.backends.console.EmailBackend`. Config leída en `settings.py`
    desde variables de entorno (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`,
    `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`).
  - Envío en un **thread daemon** para no bloquear el WS/request; errores se loguean y
    se tragan (un fallo de SMTP no debe romper el chat ni el update de ticket).
  - Templates de texto plano simples con voseo + deep-link a la app.
  - *(Cola async real con Celery/Redis → diferida al sub-proyecto G.)*

### 3. Frontend

- **`notifications.store.js` (Pinia)**: dueño único del socket `ws/notify/`.
  - `connect()` tras login (una vez), `disconnect()` en logout. Reusa `useWsConnection`
    fuera de un componente (instancia manual) + heartbeat `ping` cada ~30s.
  - Estado: `toasts[]` (cola), `unreadCount`, `items[]` (historial de la campanita).
  - Al recibir un mensaje del socket: push toast (salvo supresión por ticket abierto),
    incrementar `unreadCount`, prepend a `items`.
- **`ToastContainer.vue`** montado en `App.vue` (persistente, se renderiza sólo si hay
  usuario autenticado): stack de toasts hairline azul eléctrico, auto-dismiss ~5s,
  click → navega al ticket (deep-link) y marca leído. Suprime el toast cuyo `ticket`
  coincide con el que el usuario está mirando (el store expone `activeTicketId`, seteado
  por `ChatPanel`).
- **Campanita en `AppTopBar`**: icono `ti-bell` + badge de no-leídas + dropdown con
  historial. Marca leídas al abrir / al click en un item; botón "marcar todas".
- **Vista de preferencias**: pantalla simple de ajustes con los toggles de email
  relevantes al rol del usuario. Ruta autenticada nueva (ej. `/ajustes/notificaciones`).
- **API REST** (app `notifications`):
  - `GET /api/notifications/` — historial paginado del usuario.
  - `POST /api/notifications/{id}/read/` — marca una leída.
  - `POST /api/notifications/read-all/` — marca todas leídas.
  - `GET/PATCH /api/notifications/preferences/` — lee/actualiza los toggles del usuario.
- **api/notifications.api.js**: wrappers de los endpoints anteriores.

### 4. Estética

Respetar la convención v2: bordes hairline 0.5px, palette azul eléctrico
(`#0038FF` light / `#5B7CFF` dark, cyan `#00E5FF` pop), tipografía Space Grotesk /
Inter / JetBrains Mono, copy en voseo cercano. Toasts y dropdown de campanita sin
sombras pesadas; badge de no-leídas en accent.

## Testing

Backend (~12–15 tests nuevos):
- Matriz de destinatarios por cada evento (created/assigned/new_message/status_changed).
- Exclusión del actor.
- Respeto de `NotificationPreference` (email suprimido si el toggle está off).
- Gate de presence para email de `new_message` (online → sin email; offline → email).
- Endpoints: listar, marcar leída, marcar todas, get/patch preferences.
- Creación on-demand de `NotificationPreference` con defaults.

Frontend: build limpio; verificación manual del toast + campanita + supresión por
ticket abierto (checklist VERIFY).

## Fuera de alcance (YAGNI, ciclos futuros)

- Cola async real de emails (Celery) → sub-proyecto G (endurecimiento producción).
- Redis para Channels/cache → sub-proyecto G.
- Digest / resumen de emails.
- Web Push / PWA / notificaciones del navegador.
- Notificaciones de SLA → sub-proyecto F.
- Adjuntos en notificaciones → sub-proyecto E.

## Decisiones tomadas en el brainstorm

- Matriz de eventos → destinatarios: aceptada tal cual (arriba).
- Email por mensaje: **presence-gated** (sólo si el destinatario está offline).
- Notificaciones in-app: **persistidas** (modelo + campanita + historial), no efímeras.
- Preferencias de email: **granulares por tipo de evento**.
- Dispatcher: **explícito** en los dos embudos (no signals).
