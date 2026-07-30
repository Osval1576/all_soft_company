# AllSafe — Plataforma de Soporte Técnico Multi-Tenant

![Django](https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.4-4479A1?logo=mysql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![Stripe](https://img.shields.io/badge/Stripe-Billing-635BFF?logo=stripe&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

Sistema de gestión de tickets, SLA y soporte técnico en tiempo real, con arquitectura **multi-tenant** (multi-organización). Nace pensado para una empresa de sistemas de seguridad (cámaras, alarmas), con una arquitectura preparada para operar como SaaS para cualquier negocio que dé soporte técnico a clientes.

**Estado del proyecto:** en desarrollo activo. Los módulos núcleo (autenticación, tickets, chat en tiempo real, SLA, facturación, multi-tenancy) están implementados, junto con un **wedge de IA completo** (auto-borrador, auto-triage, resumen, sentimiento→prioridad, base de conocimiento con deflección RAG, insights), **IA sin lock-in** (elegís Claude / Gemini / ChatGPT y traés tu key) y **omnicanal** (WhatsApp, email, widget web, Messenger/Instagram). El procesamiento de IA corre **async** (cola Celery en prod, thread in-process en dev).

## Descripción

AllSafe conecta a **clientes**, **agentes/técnicos** y **administradores** en una sola plataforma. Un cliente reporta un problema con su servicio, se genera un ticket, y un técnico lo atiende por chat en tiempo real o, si la gravedad del caso lo requiere, agenda una visita física. Cada empresa que usa la plataforma opera de forma aislada (tenant independiente), con su propio slug de acceso, marca visual y equipo de trabajo.

## Roles y funcionalidades

### 👤 Cliente
- Genera tickets describiendo su problema o solicitud de soporte
- Chatea en tiempo real con el técnico asignado
- Consulta el estado y avance de sus casos
- Recibe notificaciones de actualizaciones

### 🛠️ Agente / Técnico
- Bandeja de entrada de tickets asignados y disponibles para tomar
- Chat en tiempo real con el cliente vía WebSockets
- Métricas propias de desempeño
- Puede escalar a visita física según la gravedad del caso

### 🧑‍💼 Administrador
- Asignación y gestión de tickets del equipo
- Gestión de miembros/técnicos de la organización (invitaciones)
- Configuración de SLA: niveles de servicio y calendario de atención
- Gestión de suscripción y facturación (Stripe)
- Personalización de marca (branding) por organización
- Administración del contenido del landing page y formulario de registro
- Panel de métricas generales

## Stack técnico

**Backend**
- Django 6 + Django REST Framework
- Django Channels + Daphne (WebSockets / ASGI) para chat y notificaciones en tiempo real
- MySQL 8
- Redis (canales en tiempo real y caché)
- JWT (djangorestframework-simplejwt) para autenticación
- Stripe para facturación y suscripciones
- Gateway de IA multi-proveedor (Anthropic Claude / Google Gemini / OpenAI), elegible por despliegue
- Celery + Redis para el procesamiento async de los hooks de IA (con fallback a thread in-process)
- Docker / Docker Compose para despliegue

**Frontend**
- Vue 3 + Vite
- Pinia (manejo de estado)
- Vue Router
- Vue I18n (español / inglés)
- ApexCharts (dashboards y métricas)
- Axios

**Infraestructura**
- Nginx como proxy reverso con TLS
- Servicios independientes para web, worker de Celery (hooks de IA async), scheduler de SLA, scheduler de periodos de prueba, base de datos y caché

## Arquitectura destacada

- **Multi-tenancy**: cada organización opera de forma aislada (scoping por tenant), con su propio slug de acceso, login e invitaciones de equipo.
- **Wedge de IA (AI-native)**: auto-borrador de respuesta, auto-triage de prioridad, resumen del hilo, escalada por sentimiento, **base de conocimiento con deflección RAG**, KB que se auto-alimenta al resolver tickets, e insights de negocio — todo sobre el propio modelo de datos, gateado por plan y con humano en el loop.
- **IA sin lock-in (BYO-AI)**: el despliegue elige el proveedor (Claude / Gemini / ChatGPT) y usa su propia API key; un único gateway aislado enruta según config.
- **Omnicanal**: WhatsApp (Cloud API), email-to-ticket, widget web embebible e Instagram/Messenger entran por una misma abstracción de canal (ticket + hilo por contacto + deflección + aislamiento por tenant).
- **Procesamiento async**: los hooks de IA fire-and-forget corren fuera del request/webhook — cola **Celery** en producción (worker aparte), thread daemon in-process en dev, inline en tests.
- **Multilingüe**: traducción con IA para atender clientes en otros idiomas sin equipo bilingüe.
- **Motor de SLA**: cálculo de tiempos de atención con calendario de negocio configurable y verificación automática mediante un proceso `scheduler` independiente.
- **Tiempo real**: chat técnico–cliente y notificaciones push mediante WebSockets, con tracking de presencia (en línea / desconectado).
- **Facturación**: integración con Stripe, incluye verificación automática de periodos de prueba.
- **CSAT**: encuestas de satisfacción post-atención con reglas de elegibilidad.
- **Internacionalización**: interfaz disponible en español e inglés.
- **Pruebas automatizadas**: suites de pruebas por módulo, incluyendo pruebas orientadas a seguridad (aislamiento entre organizaciones y permisos por rol).

## Estructura del proyecto

```
all_soft_company/
├── backend/                   # Django REST + Channels
│   ├── accounts/               # Registro, invitaciones, verificación de cuenta
│   ├── users/                  # Usuarios y roles (ADMIN / AGENT / CUSTOMER)
│   ├── tenancy/                 # Multi-tenant: aislamiento y branding por organización
│   ├── tickets_t/               # Tickets y chat en tiempo real (WebSockets)
│   ├── sla/                     # Motor de SLA: niveles, calendario, scheduler
│   ├── billing/                 # Suscripciones y pagos (Stripe)
│   ├── csat/                    # Encuestas de satisfacción
│   ├── notifications/           # Notificaciones en tiempo real + presencia
│   ├── metrics/                  # Analíticas y dashboards
│   ├── ai/                      # Gateway multi-proveedor + features de IA (ver ai/README.md)
│   ├── kb/                      # Base de conocimiento + deflección RAG + KB auto-alimentada
│   ├── inbound/                 # Omnicanal: WhatsApp, email, widget, Messenger/IG
│   ├── config/                  # Settings, Celery y background tasks
│   └── landing_cms/             # Contenido del landing page público
├── frontend/                    # Vue 3 + Vite
│   ├── src/views/dashboards/     # Dashboards por rol
│   ├── src/views/admin/          # Configuración de la organización
│   ├── src/components/           # Chat, tickets, métricas, notificaciones
│   └── src/i18n/                  # Traducciones ES/EN
├── docker-compose.yml
└── docs/
```

## Cómo levantarlo localmente

```bash
git clone https://github.com/Osval1576/all_soft_company.git
cd all_soft_company
cp .env.example .env      # completar variables: DB, SECRET_KEY, Stripe, email, etc.
docker compose up --build
```

- Backend (API): `http://localhost:8000`
- Healthcheck: `http://localhost:8000/api/health/`
- Frontend (vía Nginx): `http://localhost`
- **Documentación de API (Swagger)**: `http://localhost:8000/api/docs/` · Redoc: `http://localhost:8000/api/redoc/` · esquema OpenAPI 3: `http://localhost:8000/api/schema/`

`docker compose up` levanta todos los servicios: `web` (API/ASGI), `worker` (Celery — procesa los hooks de IA async), `scheduler` y `trial-scheduler` (loops de SLA y periodos de prueba), `mysql`, `redis` y `nginx`. El `web` aplica las migraciones al arrancar; el resto espera a que esté sano.

## IA y omnicanal — configuración

La IA es **opt-in** por despliegue y **gateada por plan** (Pro/Business). Se elige el proveedor y se trae la key (ver `.env.example` y `backend/ai/README.md`):

```bash
AI_FEATURES_ENABLED=true
AI_PROVIDER=gemini            # anthropic | gemini | openai
GEMINI_API_KEY=...            # la key del proveedor elegido
AI_TASK_QUEUE=celery          # cola real en prod (vacío = thread in-process)
```

Con Docker Compose el **worker de Celery** ya corre como servicio (`worker`), así que no hay que arrancarlo a mano. Para dev **sin** Docker (o para depurar), se corre aparte:

```bash
celery -A config worker -l info -Q allsafe      # Windows dev: agregar --pool=solo
```

Los canales de entrada (WhatsApp / email / widget / Messenger-IG) se configuran por env y se registran por tenant en `/api/admin/inbound/accounts/` (ver `backend/inbound/README.md`). Sin credenciales de IA, todo **degrada con gracia** (el helpdesk sigue funcionando sin IA).

Cada organización controla su uso de IA en `/api/admin/ai/settings/` (`OrgAiSettings`): **opt-in** (`enabled`), **rate limits** — acciones de IA autenticadas por usuario/minuto y llamadas de deflección desde canales públicos por org/hora — y **presupuesto mensual** (`monthly_budget_usd`). El tope público protege el endpoint anónimo del widget/WhatsApp (que corre una llamada de IA por consulta) de picos de costo/abuso: superado el límite, la consulta escala a un humano sin gastar IA. El costo de cada llamada se registra (`AiUsage`, con precios por proveedor/modelo); al alcanzar el presupuesto del mes, la IA de la org se apaga hasta el mes siguiente (el mismo endpoint devuelve el gasto acumulado en `current_month_cost_usd`). Los precios se pueden ajustar por despliegue con `AI_PRICE_<PROVIDER>_<MODEL>_IN/_OUT`.

## Roadmap

**Hecho**
- [x] Wedge de IA: auto-borrador, auto-triage, resumen, sentimiento→prioridad, insights
- [x] Base de conocimiento + deflección RAG + KB auto-alimentada
- [x] Gateway de IA multi-proveedor (Claude / Gemini / OpenAI) — "IA sin lock-in"
- [x] Omnicanal: WhatsApp, email-to-ticket, widget web, Messenger/Instagram
- [x] Multilingüe (traducción con IA)
- [x] Procesamiento async con cola (Celery + Redis, fallback a thread)
- [x] Guardrails de IA por tenant: opt-in (`OrgAiSettings`) + rate limiting + presupuesto mensual con metering de costo (`AiUsage`)
- [x] Documentación de API (OpenAPI 3 con drf-spectacular: Swagger `/api/docs/`, Redoc `/api/redoc/`)
- [x] Tests de componentes de frontend (Vitest + happy-dom: paneles admin + wedge de IA del ChatPanel)

**Pendiente**
- [ ] Traducción automática en el pipeline de mensajes (hoy asistida por el agente)
- [ ] Refinamiento de flujos de agente/administrador
- [ ] Cobertura de pruebas end-to-end en frontend (flujo completo con navegador)

## Autor

**Osvaldo Saldaña Nogal** — Ingeniero en Informática, Desarrollador Full Stack
[LinkedIn](https://www.linkedin.com/in/osvaldo-salda%C3%B1a-nogal-6401b2301/) · [GitHub](https://github.com/Osval1576)
