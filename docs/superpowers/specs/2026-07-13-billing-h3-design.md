# Billing + Planes + Stripe · H3 — Suscripciones y límites por organización

**Fecha:** 2026-07-13
**Sub-proyecto:** H3 (tercera parte de H — multi-tenant + billing; H1 núcleo (hecho) / H2 registro (hecho) / **H3 billing** / H4 branding (diferido))
**Estado:** Diseño aprobado, pendiente de plan de implementación

## Objetivo

Monetizar el SaaS: planes con límite de agentes, enforcement de ese límite, y cobro real vía
Stripe (Checkout + Customer Portal + webhooks), con trial de 14 días. El agente de IA escribe
toda la integración; **el dueño del producto configura las claves de Stripe por env** (G ya dejó
settings env-driven) — el agente nunca maneja claves ni dinero real.

**Decisiones de brainstorm:**
1. **Alcance:** planes + límites + Stripe integrado completo (checkout, portal, webhooks). Stripe
   se **mockea en tests**; el e2e con test-mode lo hace el dueño con sus claves.
2. **Planes por # de agentes:** Free (≤2 AGENTs) / Pro (≤10) / Business (ilimitado). El límite
   cuenta técnicos activos; los CUSTOMER nunca cuentan.
3. **Estado inicial:** org nueva arranca en **trial de Pro (14 días)**; al vencer sin pago →
   baja a **Free**. Over-limit tras downgrade: no se borra a nadie, pero no se puede invitar/
   activar más agentes hasta bajar la cuenta o pagar.

## Contexto técnico relevante (estado actual)

- `tenancy.Organization` (name, slug, is_active, created_at) — el enganche del plan/suscripción.
  H2 crea la org en `RegisterSerializer.create` (registro self-service) y hay un signal
  `provision_org_sla` (H1) en `Organization` post_save.
- H2: `InvitationCreateSerializer.validate_role` restringe invitaciones a AGENT/CUSTOMER;
  `perform_create` scoped por `request.organization`. El `UserViewSet` (H2-T4) permite cambiar
  rol/is_active con guards (último-admin, no auto-escalada).
- Roles: AGENT = técnico (cuenta para el límite); CUSTOMER = cliente final (no cuenta); ADMIN.
- `check_sla --loop` (G) + servicio compose dedicado + `SLA_SCHEDULER_MODE` — patrón a imitar
  para el vencimiento de trials.
- Settings env-driven (G): `_env`/`_env_bool`. `EXEMPT_PREFIXES` del middleware de tenancy =
  `("/api/health/", "/api/auth/")` — el webhook de Stripe necesita ir en un prefijo exento (es
  público, firmado por Stripe, sin `request.organization`).
- Email async, throttle scopes, `FRONTEND_BASE_URL` (para URLs de retorno de Stripe).
- Sin dependencia de Stripe todavía. `requirements.txt` pinnea deps.

## Diseño

### 1. App nueva `billing/`

```
backend/billing/
  models.py        # Plan, Subscription
  services.py      # limits (can_add_agent, active_agent_count) + trial/plan transitions
  stripe_gateway.py # wrapper de la API de Stripe (checkout, portal, verify webhook) — aislado para mockear
  views.py         # CheckoutView, PortalView, WebhookView, SubscriptionView
  urls.py
  admin.py
  emails.py        # (opcional) aviso de trial por vencer / pago fallido
  tests.py
  tests_adversarial.py
  migrations/      # 0001 modelos, 0002 seed de planes + subs para orgs existentes
```

### 2. Modelos

**`Plan`**
- `key` (unique: `free`/`pro`/`business`), `name`, `max_agents` (PositiveInteger, **null = ilimitado**),
  `stripe_price_id` (CharField, blank — editable en `/django-admin` Y overridable por env),
  `is_active` (default True), `order` (para ordenar en la UI).
- Seed (data-migration): Free (max_agents=2), Pro (10), Business (null).

**`Subscription`**
- `organization = OneToOneField(Organization, CASCADE, related_name="subscription")`
- `plan = ForeignKey(Plan, PROTECT)`
- `status` (trial/active/past_due/canceled — TextChoices)
- `trial_ends_at` (null), `current_period_end` (null)
- `stripe_customer_id`, `stripe_subscription_id` (CharField blank)
- Propiedades: `is_trial_active` (status==trial and now<trial_ends_at); `effective_plan` (el plan
  vigente considerando trial vencido → Free si trial expiró sin pago; el enforcement usa esto).

**Provisioning:** signal post_save de `Organization` (created) → crea `Subscription(plan=Pro,
status=trial, trial_ends_at=now+14d)`. La data-migration crea subs para las orgs existentes:
ALS → Business (grandfathered), el resto → según corresponda (probablemente Free o trial).
`billing.testing`/`tenancy.testing.create_org` provisiona la sub para tests (idempotente).

### 3. Enforcement de límites (`billing/services.py`)

- `active_agent_count(org)` = `org_users(org).filter(role="AGENT", is_active=True).count()`.
- `agent_limit(org)` = `org.subscription.effective_plan.max_agents` (None = ilimitado).
- `can_add_agent(org)` = límite None **o** `active_agent_count(org) < límite`.
- **Puntos de enforcement:**
  - `InvitationCreateSerializer` (H2): si `role == "AGENT"` y `not can_add_agent(org)` → 400
    "Alcanzaste el límite de agentes de tu plan (N). Mejorá el plan para sumar más."
  - `UserViewSet` update (H2): activar un AGENT inactivo, o cambiar un user a role=AGENT, cuando
    `not can_add_agent(org)` → 400. (Degradar/desactivar nunca se bloquea por límite.)
- Over-limit (downgrade con más agentes que el tope): los agentes existentes **no** se tocan;
  `can_add_agent` simplemente da False hasta que bajen por debajo del límite.

### 4. Stripe (`billing/stripe_gateway.py` + `views.py`)

**Gateway aislado** (para mockear en tests y degradar sin claves):
- `is_configured()` = hay `STRIPE_SECRET_KEY`.
- `create_checkout_session(org, plan, success_url, cancel_url)` → devuelve la URL de Checkout;
  crea/reusa el `stripe_customer_id`.
- `create_portal_session(org, return_url)` → URL del Customer Portal.
- `verify_and_parse_webhook(payload, sig_header)` → evento verificado (o lanza si la firma falla).

**Endpoints:**
- `POST /api/billing/checkout/` (IsAuthenticated + IsAdmin, scoped): body `{plan_key}` → si Stripe
  no está configurado → **503** claro; si el plan es Free → 400 (Free no se paga); else devuelve
  `{url}` de la sesión. `success_url`/`cancel_url` = `FRONTEND_BASE_URL/admin/suscripcion?success|canceled`.
- `POST /api/billing/portal/` (admin, scoped) → `{url}` del portal (503 si no configurado o sin
  `stripe_customer_id`).
- `GET /api/billing/subscription/` (admin, scoped) → `{plan, status, trial_ends_at,
  current_period_end, agent_count, agent_limit, plans: [...]}` — todo lo que la pantalla necesita.
- `POST /api/billing/webhook/` (**AllowAny, público, exento del middleware**): lee el raw body,
  verifica la firma con `STRIPE_WEBHOOK_SECRET`; firma inválida → **400**. Maneja:
  - `checkout.session.completed` → activa la sub (status=active, plan del price, guarda
    stripe_subscription_id/customer_id, current_period_end).
  - `customer.subscription.updated` → sincroniza status/plan/current_period_end.
  - `customer.subscription.deleted` → status=canceled → baja a Free.
  - `invoice.payment_failed` → status=past_due.
  - **Idempotencia:** registrar `event.id` procesados (modelo `ProcessedStripeEvent` o campo);
    re-entrega del mismo evento → no-op.
  - **El webhook es la ÚNICA fuente de verdad del estado pago** — el front nunca marca "pagado".

**Config:** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY` (front, por env
del build), price IDs por plan (env con fallback al campo del modelo). Dependencia `stripe` en
requirements. El webhook path se agrega a `EXEMPT_PREFIXES` del middleware (o va bajo un prefijo
ya exento — decidir en el plan; probablemente `/api/billing/webhook/` con exención explícita).

### 5. Vencimiento del trial

- Management command `check_trials` con `--loop`/`--max-loops` (idéntico patrón a `check_sla` de
  G): busca `Subscription(status=trial, trial_ends_at<now)` → baja a Free (plan=Free,
  status=active o un status "free"). Idempotente. Servicio dedicado en compose (o folded en el
  scheduler existente — el plan decide). Opcional: email de aviso "tu trial vence en 3 días".

### 6. Frontend

- **`/admin/suscripcion`** (`AdminSubscription.vue`, rol ADMIN): plan actual + estado + días de
  trial restantes + uso de agentes ("3/10"); tarjetas de los 3 planes con **Mejorar** (→ POST
  checkout → `window.location = url`) y **Gestionar** (→ POST portal → redirect). Al volver de
  Stripe con `?success`/`?canceled` → toast + refetch. Si billing no configurado (503) → estado
  "billing no disponible" en dev.
- **`/admin/miembros`** (H2): mostrar el límite ("Agentes: 3/10") y bloquear el form de invitar
  técnico con prompt de upgrade cuando `agent_count >= agent_limit` (link a `/admin/suscripcion`).
- Link "Suscripción" en la nav de AdminDashboard.
- `STRIPE_PUBLISHABLE_KEY` por env del front (mínima superficie: con Checkout Session el front
  sólo redirige a la URL que arma el backend).

### 7. Seguridad / tenancy

- `Subscription`/checkout/portal/subscription-GET scoped por `request.organization` (patrón H1):
  un admin nunca ve/gestiona la sub de otra org.
- Webhook público pero **rechaza sin firma Stripe válida**; idempotente por event.id (no se puede
  forjar un "pagado" ni re-disparar transiciones).
- El estado de pago viene SÓLO del webhook; el front no puede auto-activar un plan.
- Sólo ADMIN hace checkout/portal.

### 8. Testing

- **Enforcement:** invitar 3er agente en Free → 400; en trial-Pro permite hasta 10; activar agente
  over-limit → 400; degradar/desactivar nunca bloqueado; CUSTOMER no cuenta.
- **Webhook:** eventos mockeados (`checkout.session.completed` activa; `subscription.deleted`
  baja a Free; `payment_failed` → past_due); firma inválida → 400; idempotencia (mismo event.id
  2 veces → 1 sola transición).
- **Trial:** `check_trials` baja trials vencidos a Free; no toca trials vigentes ni subs pagas.
- **Downgrade over-limit:** Pro→Free con 8 agentes → agentes intactos, `can_add_agent` False.
- **Adversarial (`billing/tests_adversarial.py`):** admin de A no hace checkout/portal/ve la sub
  de B (404/scoped); webhook sin firma no altera ninguna sub; el front no puede setear status.
- **Stripe mockeado** (nunca se llama la API real en tests — se mockea `stripe_gateway`).
- Gate: suite completa fresca + build. Runbook: cómo configurar Stripe test-mode + registrar el
  webhook endpoint + probar el e2e (fuera del código, lo hace el dueño).

## Manejo de errores y bordes

- Sin claves de Stripe (dev): checkout/portal → 503 claro; el resto (límites, subscription-GET,
  trial) funciona.
- Webhook con firma inválida o secret ausente → 400 (nunca procesa).
- Evento de un plan/price desconocido → log + no-op (no crashea el webhook).
- Org sin Subscription (dato viejo pre-migración) → la migración las crea; defensivamente,
  `agent_limit` trata "sin sub" como Free.
- Cancelación en Stripe → `subscription.deleted` → Free (no se suspende la org; sólo baja el tope).

## Fuera de alcance (post-H3 / H4)

Proration fina, facturas PDF/descargables, impuestos, dunning avanzado, múltiples métodos de pago,
branding por tenant (H4), self-signup de clientes finales, planes anuales/múltiples monedas.

Ver [[allsafe-project-state]] y [[allsafe-conventions]].
