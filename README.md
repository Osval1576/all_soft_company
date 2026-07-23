# AllSafe — Plataforma de Soporte Técnico Multi-Tenant

![Django](https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.4-4479A1?logo=mysql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![Stripe](https://img.shields.io/badge/Stripe-Billing-635BFF?logo=stripe&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

Sistema de gestión de tickets, SLA y soporte técnico en tiempo real, con arquitectura **multi-tenant** (multi-organización). Nace pensado para una empresa de sistemas de seguridad (cámaras, alarmas), con una arquitectura preparada para operar como SaaS para cualquier negocio que dé soporte técnico a clientes.

**Estado del proyecto:** en desarrollo activo. Los módulos núcleo (autenticación, tickets, chat en tiempo real, SLA, facturación, multi-tenancy) están implementados; el proyecto sigue en refinamiento.

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
- Servicios independientes para web, scheduler de SLA, scheduler de periodos de prueba, base de datos y caché

## Arquitectura destacada

- **Multi-tenancy**: cada organización opera de forma aislada (scoping por tenant), con su propio slug de acceso, login e invitaciones de equipo.
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

## Roadmap

- [ ] Refinamiento de flujos de agente/administrador
- [ ] Cobertura de pruebas end-to-end en frontend
- [ ] Documentación de API

## Autor

**Osvaldo Saldaña Nogal** — Ingeniero en Informática, Desarrollador Full Stack
[LinkedIn](https://www.linkedin.com/in/osvaldo-salda%C3%B1a-nogal-6401b2301/) · [GitHub](https://github.com/Osval1576)
