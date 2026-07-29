# Omnicanal — ingesta de canales externos (Fase 5.1)

App `inbound`: recibe mensajes de canales externos (WhatsApp primero) y los
convierte en tickets, con hilo por contacto y **deflección RAG** (reusa la KB /
3B) para responder solo, escalando a humano cuando la KB no alcanza.

## Piezas
- `models.ChannelAccount`: mapea la cuenta del canal (p. ej. el `phone_number_id`
  de WhatsApp) → organización. La ingesta usa esto para saber a qué tenant va el
  mensaje. Se administra en `/api/admin/inbound/accounts/` (ADMIN del tenant).
- `models.ChannelThread`: hilo del contacto → ticket actual (para que los mensajes
  sucesivos caigan en el mismo ticket mientras siga abierto).
- `services.handle_inbound_message`: núcleo agnóstico del canal (org → contacto →
  ticket → mensaje → sentimiento 2B → deflección 3B). Devuelve la respuesta
  automática o `None` (queda para un agente).
- `whatsapp.py`: adapter de WhatsApp Cloud API (parseo del webhook, verificación de
  firma, envío saliente). Único lugar que conoce el formato de Meta.
- `views.WhatsAppWebhookView`: webhook `GET` (verificación) + `POST` (mensajes).

## Configurar WhatsApp (Cloud API de Meta)
1. En Meta: creá una app de WhatsApp Business, obtené el número emisor y su
   `phone_number_id`, un access token y el app secret.
2. Variables de entorno del backend (ver `.env.example`):
   ```
   WHATSAPP_VERIFY_TOKEN=...   # el que ponés en Meta al configurar el webhook
   WHATSAPP_TOKEN=...          # access token del Graph API
   WHATSAPP_PHONE_NUMBER_ID=...
   WHATSAPP_APP_SECRET=...     # valida X-Hub-Signature-256 (recomendado)
   ```
3. En Meta, configurá el webhook apuntando a `https://TU_DOMINIO/api/inbound/whatsapp/`
   (verificación por `GET` con `WHATSAPP_VERIFY_TOKEN`).
4. Registrá la cuenta del tenant: `POST /api/admin/inbound/accounts/`
   `{ "channel": "whatsapp", "external_id": "<phone_number_id>" }` (como ADMIN).

## Configurar Email-to-ticket
1. En tu proveedor de inbound-parse (SendGrid Inbound Parse, Mailgun Routes,
   Postmark, etc.): apuntá el parseo del buzón de soporte a
   `https://TU_DOMINIO/api/inbound/email/`.
2. (Opcional, recomendado) Seteá `INBOUND_EMAIL_SECRET` y pasá `?token=<secret>`
   (o header `X-Inbound-Token`) en la URL del webhook, para que solo tu proveedor
   pueda postear.
3. Registrá la cuenta del tenant: `POST /api/admin/inbound/accounts/`
   `{ "channel": "email", "external_id": "soporte@tucliente.com" }` (la dirección
   a la que escriben los clientes; se resuelve por el `to` del mail).
4. La respuesta automática de deflección sale por el email backend de Django
   (configurá `EMAIL_HOST`/SMTP; sin eso va a consola).

El adapter (`email.py`) normaliza los campos comunes de los proveedores (`from`,
`to`, `subject`, `text`/`body-plain`/`TextBody`); ajustá si el tuyo difiere.

## Widget web embebible
Deflección pública en la web del cliente: un visitante anónimo pregunta, la IA
responde con la KB publicada, y si no alcanza deja su email → se crea un ticket
(canal `widget`).

1. Registrá el widget del tenant: `POST /api/admin/inbound/accounts/`
   `{ "channel": "widget", "external_id": "<CLAVE_PUBLICA>" }` (una clave no
   adivinable, p. ej. un UUID; es pública, va en el HTML del cliente).
2. El cliente agrega en su sitio:
   ```html
   <script src="https://TU_DOMINIO/widget.js"
           data-key="CLAVE_PUBLICA" data-api="https://TU_DOMINIO"></script>
   ```
3. Endpoints (públicos, CORS abierto — solo exponen KB publicada + creación de
   ticket): `POST /api/widget/<key>/ask/` (deflección) y
   `POST /api/widget/<key>/contact/` (crea el ticket con el email del visitante).

## Notas / siguientes pasos
- El procesamiento es inline en el webhook (la llamada de IA suma latencia). Para
  volumen alto conviene una cola/worker (deja el 200 inmediato y procesa aparte).
- Registrar la auto-respuesta como mensaje del ticket (hoy solo se envía por el
  canal) y opción de auto-resolver el ticket cuando la deflección lo cierra.
- Próximos canales sobre la misma abstracción: email-to-ticket, widget web, IG/Messenger.
