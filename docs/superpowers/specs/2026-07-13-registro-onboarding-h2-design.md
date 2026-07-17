# Registro + Onboarding · H2 — Alta self-service de organización e invitaciones

**Fecha:** 2026-07-13
**Sub-proyecto:** H2 (segunda parte de H — multi-tenant + billing; descompuesto en H1 núcleo (hecho) / **H2 registro+onboarding** / H3 billing / H4 branding)
**Estado:** Diseño aprobado, pendiente de plan de implementación

## Objetivo

Cerrar el ciclo de alta del SaaS: una empresa se registra sola (con verificación de email) y su
admin suma miembros (técnicos/clientes) por invitación con token. Reemplaza el alta directa
con contraseña de H1 por el flujo de invitación (más seguro: ningún admin conoce contraseñas
ajenas; emails validados de paso).

**Decisiones de brainstorm:**
1. Registro **self-service con verificación de email** (cuenta inactiva hasta confirmar).
2. Miembros por **invitación por email con token** (el invitado pone su propia contraseña).
3. El alta directa con contraseña de H1 (`UserViewSet.create`) **se retira**; el rol/org salen
   SIEMPRE del token de invitación, nunca del body del invitado.
4. Tokens como **modelos explícitos con expiración** (auditable/testeable), no signing opaco.
5. Clientes finales entran **sólo por invitación** en H2 (self-signup de clientes = fuera de
   alcance, posible H2.5).

## Contexto técnico relevante (estado actual, verificado)

- Auth por **cookie JWT** (`config/auth_views.py`: login-cookie/refresh-cookie/logout;
  `cookie_settings()` con secure derivado de DEBUG). No hay endpoint de registro.
- Email: `notifications/emails.send_notification_email` usa `django.core.mail.send_mail` con
  `settings.DEFAULT_FROM_EMAIL` y `fail_silently=True`; SMTP configurable por env (G). H2 hará
  su propio helper de email transaccional (no `fail_silently` para el link — si falla el envío,
  hay que saberlo).
- `users/serializers.UserCreateSerializer` (admin-crea-con-password, scoped por org en H1) —
  **se retira su uso en el viewset**. `UserSerializer` expone role/is_staff writable (follow-up
  de H1 a revisar acá).
- `users/views.UserViewSet`: `get_queryset` → `org_users(request.organization)` (H1);
  `perform_create` fuerza org. H2 quita la acción `create`.
- Middleware `tenancy.middleware.OrganizationMiddleware`: fail-closed en `/api/`, **exentos
  `/api/health/` y `/api/auth/`** — el registro y el accept de invitación viven bajo prefijos
  exentos (son públicos, sin `request.organization`).
- `tenancy.Organization(name unique, slug unique uppercase, is_active)`; su SLA default se
  provisiona con un signal post_save (H1). `User.organization` FK; una org por usuario.
- Público existente con throttle: `landing_cms/contact_view` usa `ScopedRateThrottle` (rate
  `contact: 5/hour` en settings) — patrón a reusar para registro/reenvío.
- Frontend: router role-gated; rutas públicas `landing`/`login` con `meta.public`. Store auth
  con `login()`/`loadMe()`/`redirectByRole()` (por role, H1).

## Diseño

### 1. App nueva `accounts/`

```
backend/accounts/
  models.py        # EmailVerificationToken, Invitation
  serializers.py   # Register, VerifyEmail, InvitationCreate, InvitationPublic, AcceptInvitation
  views.py         # RegisterView, VerifyEmailView, ResendVerificationView, InvitationViewSet, AcceptInvitationView
  emails.py        # envío transaccional de verificación e invitación
  urls.py
  tests.py
  tests_adversarial.py
```

### 2. Modelos

**`EmailVerificationToken`**
- `user = OneToOneField(User, on_delete=CASCADE, related_name="email_verification")`
- `token = CharField(unique, default=uuid4 hex)`, `created_at`, `expires_at` (created + 48h),
  `used_at` (null hasta consumirse).
- Método `is_valid()` = `used_at is None and now < expires_at`.

**`Invitation`**
- `organization = FK(Organization, CASCADE, related_name="invitations")`
- `email`, `role` (choices AGENT/CUSTOMER — un admin no invita otro ADMIN en H2; ver bordes),
  `token` (uuid unique), `invited_by = FK(User, SET_NULL, null)`, `created_at`,
  `expires_at` (created + 7d), `status` (pending/accepted/revoked).
- `Meta.constraints`: `UniqueConstraint(organization, email, condition=status="pending",
  name="uniq_pending_invitation")` — una invitación pendiente por email/org.
- `is_acceptable()` = `status == "pending" and now < expires_at`.

### 3. Endpoints

**Registro (públicos, bajo `/api/auth/` → exentos del middleware):**
- `POST /api/auth/register/` — body `{org_name, org_slug?, first_name, last_name, email,
  password}`. Throttle `register: 5/hour` (ScopedRateThrottle). En una transacción:
  crea `Organization` (slug autogenerado del nombre si no viene, validado único y uppercased),
  crea `User(role=ADMIN, organization=org, is_active=False)`, crea `EmailVerificationToken`,
  envía email con link `/verificar/<token>`. Responde 201 sin datos sensibles. Email o slug
  duplicado → 400.
- `POST /api/auth/verify-email/` — body `{token}`. Valida → `user.is_active=True`,
  `token.used_at=now`. 200 con `{ok:true}`. Token inválido/expirado/usado → 400. Idempotente-ish
  (usado → 400 claro).
- `POST /api/auth/resend-verification/` — body `{email}`. Throttle. Si existe user inactivo con
  ese email, regenera token y reenvía (respuesta 200 genérica **siempre**, no revela si el email
  existe).

**Invitaciones:**
- `InvitationViewSet` (admin del tenant, `IsAuthenticated + IsAdmin`), **scoped por
  `request.organization`**:
  - `POST /api/invitations/` — `{email, role}`. Crea `Invitation(organization=request.organization,
    invited_by=request.user, ...)`, envía email con link `/invitacion/<token>`. Email que ya es
    user (de cualquier org) → 400 (una org por usuario). Pendiente duplicada → 400.
  - `GET /api/invitations/` — lista pendientes de SU org. `DELETE /api/invitations/<id>/` →
    status=revoked (no borra, auditable). Cross-org → 404 (queryset scoped).
- Aceptación (públicos, bajo `/api/auth/`):
  - `GET /api/auth/invitation/<token>/` — devuelve `{organization_name, role, email}` para pintar
    la pantalla (sin nada sensible). Inválida/expirada/aceptada → 404/410.
  - `POST /api/auth/invitation/<token>/accept/` — `{first_name, last_name, password}`.
    **Rol y org salen del token, JAMÁS del body.** Crea `User(organization=inv.organization,
    role=inv.role, email=inv.email, is_active=True)`, marca `inv.status=accepted`, setea cookies
    JWT (loguea). Token no aceptable → 410/400.

**Users (modificación):** `UserViewSet` pierde `create` (`http_method_names` sin POST, o
`get_permissions`/`create` deshabilitado); conserva list/retrieve/update/destroy scoped. Se retira
`UserCreateSerializer` de la ruta pública del alta. `UserSerializer`: `role` sigue editable por el
admin same-org (cambiar rol de un miembro es legítimo); `is_staff` pasa a **read-only** (cierra el
follow-up de H1 — el acceso a django-admin no se gestiona desde la app del tenant).

### 4. Seguridad (el corazón de H2)

- **Rol/org del token, no del body:** en `accept`, el serializer NO acepta `role`/`organization`;
  se toman de `Invitation`. Test adversarial explícito.
- **Registro siempre crea ADMIN** de una org nueva; nunca puede unirse a una org existente (eso
  es invitación). El slug/email únicos evitan colisión.
- **Enumeración:** resend-verification y (opcional) register responden genérico, sin confirmar si
  el email existe. El `GET invitation/<token>` sólo expone org+rol+email del propio token.
- **Public endpoints exentos del tenant-middleware** pero con throttle; el accept/verify no
  dependen de `request.organization`.
- **Tokens:** uuid4 hex (no adivinables), expiran, un solo uso (verificación) / estado
  (invitación). Revocar = status, no delete.
- Org `is_active=False` no puede emitir invitaciones ni sus users loguear (middleware de H1).

### 5. Frontend

- **Públicas:** `/registro` (form empresa + admin → POST register → pantalla "revisá tu email");
  `/verificar/:token` (POST verify → éxito → redirige a login); `/invitacion/:token` (GET pinta
  "Te invitaron a <org> como <rol>", form nombre+contraseña → POST accept → logueado → dashboard
  por rol).
- **Admin del tenant:** `/admin/miembros` — miembros de la org (activar/desactivar, cambiar rol)
  + invitaciones pendientes (invitar por email+rol, revocar, reenviar). Reemplaza cualquier UI de
  alta-con-contraseña.
- Link "Registrá tu empresa" en el login.
- Estética v2, copy voseo.

### 6. Manejo de errores y bordes

- Email duplicado en registro → 400 "Ya existe una cuenta con ese email".
- Invitar email que ya es user (cualquier org) → 400 (una org por usuario). Invitar a alguien ya
  invitado (pendiente) → 400.
- Token expirado → 410; usado/aceptado/revocado → 400/410 con mensaje claro. Reenvío disponible.
- Registro concurrente del mismo slug/email → la unicidad de DB lo resuelve (400).
- Un ADMIN no se puede auto-quitar el rol si es el último admin activo de la org → 400
  (evita orgs sin admin). (Validación en el update de rol.)

### 7. Testing

- **Felices:** registro→verificación→login; invitación→GET→accept→login; reenvío de verificación.
- **Adversariales (`accounts/tests_adversarial.py`):**
  - accept forzando `role=ADMIN`/`organization=<otra>` en el body → se ignoran (user queda con
    rol/org del token).
  - token de invitación de org B usado por contexto de A / sin sesión → funciona sólo con lo del
    token (es público) pero crea user en la org del token, no en otra.
  - token expirado/reusado/revocado → 410/400.
  - registrar org con slug/email duplicado → 400.
  - invitar cross-org (admin de A revoca invitación de B) → 404.
  - resend-verification no revela existencia del email.
  - último admin no puede degradarse.
- Gate: suite completa fresca + build frontend.

## Fuera de alcance (H3/H4)

Selección de plan en el registro (H3 lo engancha sobre este flujo), límites por plan, billing,
branding por tenant, subdominios, self-signup de clientes finales sin invitación (posible H2.5).

Ver [[allsafe-project-state]] y [[allsafe-conventions]].
