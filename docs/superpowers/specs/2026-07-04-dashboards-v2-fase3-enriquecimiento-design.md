# Dashboards v2 · Fase 3 — Enriquecimiento (adjuntos en chat + filtros/orden en tablas)

**Fecha:** 2026-07-04
**Sub-proyecto:** E (roadmap AllSafe)
**Estado:** Diseño aprobado, pendiente de plan de implementación

## Objetivo

Enriquecer la operación diaria del help-desk con dos capacidades independientes:

1. **Adjuntos en el chat** — subir imágenes (jpg/png/webp) y PDF a la conversación de un
   ticket, con preview inline para imágenes y chip de archivo para PDF, servidos por un
   endpoint con control de acceso.
2. **Filtros + orden en las tablas/listas** — filtrar y ordenar tickets en los dashboards
   de Admin (tabla) y Técnico (lista), client-side.

Un solo spec; el plan implementa **adjuntos primero**, luego filtros/orden.

## Contexto técnico relevante (estado actual)

- **Mensajes de chat** se crean **sólo** por WebSocket, en `TicketChatConsumer.receive()` →
  `create_message()`. Payload broadcast al grupo `ticket_{id}`. El historial se lee por
  `GET /api/tickets_t/<id>/messages/` (`TicketMessageSerializer`).
- `TicketMessage`: `ticket` FK, `sender` FK, `content` TextField, `created_at`.
- **Notificaciones (Fase 2):** `dispatch("new_message", ticket, actor, extra)` en
  `notifications/services.py` ya existe y se llama desde `create_message`.
- **Upload/validación existente:** `landing_cms/validators.py::validate_image_file`
  (PIL `.verify()`, 2 MB, jpg/png/webp). `MEDIA_ROOT`/`MEDIA_URL` configurados;
  `django_cleanup` instalado (borra el archivo físico al borrar el modelo). En dev,
  `config/urls.py` sirve `MEDIA_URL` con `static()` (sólo dev).
- **Auth:** cookie JWT `access` (`SameSite=Lax`). Front (:5173) y API (:8000) son
  **cross-origin**; `CORS_ALLOW_CREDENTIALS=True`.
- **Dashboards:** `AdminDashboard` tiene una `<table class="data-table">` real (columnas
  ref/título/estado/prioridad/creado_por/asignado_a) con búsqueda client-side ya presente;
  `TechnicianDashboard` es una **lista** (aside) con tabs "Mis tickets"/"Pool";
  `ClientDashboard` es una lista. Todos cargan los tickets enteros client-side vía
  `listMyTickets()` (`GET /api/tickets_t/`).
- **Acceso a ticket (regla del chat):** `user_can_access_ticket` en el consumer —
  ADMIN/superuser: todos; CUSTOMER: `creado_por`; AGENT: `asignado_a`.

## Parte 1 — Adjuntos en el chat

### Decisiones

- Tipos: imágenes jpg/png/webp (≤ 2 MB) + PDF (≤ 10 MB).
- **Un** adjunto por mensaje, con caption (texto) opcional.
- Acceso: **endpoint de descarga protegido** (chequeo de acceso al ticket). El serializer
  expone sólo la URL del endpoint, nunca la ruta MEDIA cruda.

### Enfoque elegido: upload REST → crea mensaje → broadcast WS (Opción A)

Un binario no viaja por el WebSocket JSON. El adjunto entra por un endpoint REST multipart
que: crea el `TicketMessage` con el archivo, hace `group_send` al grupo `ticket_{id}` para
que los clientes conectados lo vean en vivo (mismo canal que el chat), y dispara
`dispatch("new_message", ...)`. Alternativas descartadas: upload-luego-referencia-por-WS
(dos pasos, race) y base64-sobre-WS (tamaño de frame, memoria).

### Backend

**Modelo — extender `tickets_t.models.TicketMessage`:**
```
attachment              FileField(upload_to="ticket_adjuntos/%Y/%m/", null=True, blank=True,
                                  validators=[validate_attachment])   # nombre uuid
attachment_name         CharField(max_length=255, blank=True)   # nombre original
attachment_size         PositiveIntegerField(null=True, blank=True)  # bytes
attachment_content_type CharField(max_length=100, blank=True)
```
Un mensaje es válido si tiene `content` no vacío **o** `attachment`. El nombre en disco es
un uuid (evita colisión/enumeración); `attachment_name` guarda el original para mostrar.

**`tickets_t/validators.py` (nuevo) — `validate_attachment(file)`:**
- Imágenes (`image/jpeg|png|webp`): ≤ 2 MB + `PIL.Image.open(file).verify()` (misma lógica
  que `landing_cms`).
- PDF (`application/pdf`): ≤ 10 MB + el archivo empieza con la firma `%PDF-`.
- Cualquier otro content-type → `ValidationError`.
- Siempre `file.seek(0)` al final.

**Helper `message_to_payload(msg)`** (en `tickets_t`, p.ej. en serializers o un `payloads.py`):
devuelve el dict que consumen el WS y el historial, incluyendo:
`id, ticket, sender, sender_username, sender_role, content, created_at` y, si hay adjunto,
`attachment: { name, size, content_type, is_image, url }` donde `url` es la ruta del endpoint
de descarga protegido (`/api/tickets_t/<ticket_id>/attachments/<message_id>/download/`).
Sin adjunto → `attachment: null`. **Consumido por:** el consumer (`receive`/`create_message`),
el endpoint `messages` (historial) y el broadcast del upload — una sola fuente de verdad del shape.

**Endpoints (en `TicketViewSet`):**
- `POST /api/tickets_t/<id>/attachments/` (multipart `file` + `content` opcional):
  permiso `user_can_access_ticket(request.user, ticket)`; valida el archivo; crea el
  `TicketMessage(sender=request.user, content=caption, attachment=file, attachment_name=...,
  attachment_size=..., attachment_content_type=...)`; `group_send("ticket_{id}",
  {"type": "chat.message", "message": message_to_payload(msg)})`; `dispatch("new_message",
  ticket, actor=request.user, extra={"content": caption or attachment_name})`; devuelve
  `message_to_payload(msg)` (201). Rechaza no-participante (403) y archivo inválido (400).
- `GET /api/tickets_t/<id>/attachments/<message_id>/download/`: permiso de acceso al ticket;
  valida que el mensaje pertenezca al ticket y tenga adjunto; `FileResponse` con
  `content_type` correcto y `Content-Disposition: attachment; filename="<attachment_name>"`.
  403 (sin acceso) / 404 (no existe / sin adjunto).

**Serializer:** `TicketMessageSerializer` refleja `message_to_payload` (agrega el objeto
`attachment`). Nunca expone `attachment.url`/`path` del FileField crudo.

**Regla de acceso reutilizable:** extraer la lógica de `user_can_access_ticket` (hoy dentro
del consumer) a un helper sincrónico reutilizable por los endpoints (p.ej. en
`tickets_t/permissions.py` o `views.py`), y que el consumer lo use también. Evita duplicar
la matriz de acceso.

### Frontend

- **Composer (`ChatPanel.vue`):** botón clip → `<input type="file">` oculto (accept
  imágenes+pdf). Al elegir archivo: chip pendiente (nombre, tamaño, botón quitar); el caption
  va en el input de texto existente. Al enviar:
  - Con archivo pendiente → `POST` multipart al endpoint (vía nuevo `uploadAttachment(ticketId,
    file, caption)` en `tickets.api.js`); al 201, el mensaje llega por WS igual (broadcast), así
    que no hace falta insertarlo localmente (evitar duplicado: el WS ya lo push-ea).
  - Sin archivo → WS `send` como hoy.
  - Deshabilitar el botón enviar mientras sube; mostrar estado "Subiendo…".
- **Render en burbujas:** si `m.attachment`:
  - `is_image` → thumbnail inline. Como la cookie `SameSite=Lax` **no** viaja en subrecursos
    `<img>` cross-site, la imagen se carga con **fetch autenticado** (axios `withCredentials`,
    `responseType: "blob"`) → `URL.createObjectURL` → `<img :src>`. Click → abrir el blob en
    pestaña nueva (lightbox simple). Revocar los objectURL al desmontar.
  - PDF → chip (ícono + `attachment_name` + tamaño). Click → descarga autenticada (fetch blob →
    `a.download`), por la misma razón cross-origin.
- Componente `MessageAttachment.vue` encapsula el fetch-autenticado + render (imagen/pdf) para
  no inflar `ChatPanel`.

### Testing (backend)
- Upload: crea `TicketMessage` con adjunto + metadata; 403 para usuario sin acceso al ticket;
  400 para archivo oversize / content-type no permitido / PDF sin firma `%PDF`; mensaje
  attachment-only (sin content) es válido; genera una notificación `new_message` para la
  contraparte (reusa el gate de Fase 2).
- Download: 200 + bytes correctos + `Content-Disposition` para participante; 403 para
  no-participante; 404 para message_id inexistente o sin adjunto.
- APIClient con `SimpleUploadedFile` para multipart.

## Parte 2 — Filtros + orden en tablas/listas

### Decisiones
- **Client-side** (los datos ya están cargados enteros). Alcance: **Admin + Técnico**
  (Cliente queda con su búsqueda actual).

### Composable `useTicketFilters` (nuevo, `frontend/src/composables/`)
Recibe un `ref`/getter de la lista de tickets y expone estado reactivo de filtros
(`estado`, `prioridad`, `asignado`) + orden (`sortKey`, `sortDir`) y una computed
`result` (lista filtrada + ordenada). Orden por: `reference`, `estado`, `prioridad`
(usando un rank LOW<MEDIUM<HIGH<URGENT), `created_at`/`updated_at`. Reutilizable por Admin
y Técnico; DRY frente a duplicar la lógica.

### Admin (`AdminDashboard.vue`, tab Tickets)
- Barra de filtros sobre la tabla: dropdowns `estado`, `prioridad`, `asignado` (agente / sin
  asignar). Se mantiene el `search` existente (se combina con los filtros).
- Headers de columna clickeables (ref, estado, prioridad, fecha) → alternan asc/desc con
  indicador visual (▲/▼). Usa `useTicketFilters`.

### Técnico (`TechnicianDashboard.vue`, tab "Mis tickets")
- Controles sobre la lista: filtros `estado`, `prioridad` + dropdown de orden
  (prioridad / fecha). Usa `useTicketFilters`. El tab "Pool" queda igual.

### Testing (frontend)
- Build limpio + checklist manual: filtrar por cada dimensión, combinar filtro+búsqueda,
  ordenar asc/desc por cada columna, verificar que el conteo de tabs/stats no se rompe.

## Estética
Convención v2: hairline 0.5px, palette azul eléctrico via CSS vars, tipografía Space Grotesk
/ Inter / JetBrains Mono, copy en voseo. Los controles de filtro/orden y el chip de adjunto
siguen los estilos existentes (`.inline-select`, `.search-input`, chips hairline).

## Fuera de alcance (YAGNI, ciclos futuros)
- Varios adjuntos por mensaje (galería / multi-upload).
- Render inline de PDF (sólo chip + descarga).
- Drag-and-drop y paste de imágenes al composer.
- Edición/recorte de imagen.
- Antivirus / escaneo de archivos → sub-proyecto G (producción).
- Filtro/orden server-side + paginación → sólo si los volúmenes lo exigen (no PYME hoy).
- Filtros/orden en el dashboard de Cliente.

## Decisiones tomadas en el brainstorm
- Alcance: un spec, **adjuntos primero**, luego filtros.
- Adjuntos: imágenes + PDF, **1 por mensaje** + caption; campos en `TicketMessage`.
- Acceso a archivos: **endpoint de descarga protegido** (chequeo de acceso al ticket).
- Upload: **REST multipart → crea mensaje → broadcast WS** (Opción A).
- Filtros/orden: **client-side**, Admin + Técnico, composable compartido.
