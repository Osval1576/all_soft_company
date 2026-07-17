# H2 · Registro + Onboarding — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Alta self-service de organización (con verificación de email) + invitaciones por token que reemplazan el alta-con-contraseña de H1.

**Architecture:** App nueva `accounts/` con dos modelos de token (`EmailVerificationToken`, `Invitation`), endpoints públicos bajo `/api/auth/` (exentos del tenant-middleware) para registro/verify/accept y un `InvitationViewSet` scoped por org. Rol y org salen SIEMPRE del token, nunca del body. Reusa el email SMTP de G y las cookies JWT de `config/auth_views`.

**Tech Stack:** Django 6 + DRF + simplejwt (existente). Sin dependencias nuevas.

## Global Constraints

- **Rol/org del token, jamás del body:** en `accept` y `register`, el serializer NO acepta `role`/`organization`; se derivan del `Invitation`/del flujo. Test adversarial obligatorio.
- **Registro siempre crea un ADMIN de una org NUEVA** (nunca se une a una existente). Slug + email únicos.
- **Públicos exentos del middleware:** register/verify/resend/invitation-GET/accept viven bajo `/api/auth/` (el prefijo ya exento en `tenancy/middleware.py`); no dependen de `request.organization`.
- **Invitaciones scoped por `request.organization`** (mismo patrón H1): un admin no ve/revoca invitaciones de otra org → 404.
- **Anti-enumeración:** `resend-verification` responde 200 genérico siempre (no revela si el email existe). `GET invitation/<token>` sólo expone lo del propio token.
- **Anti-orphan-org:** el último admin activo de una org no puede degradarse ni desactivarse → 400.
- **Tokens:** uuid4 hex, expiran (verificación 48h, invitación 7d), un solo uso / estado; revocar = status, no delete.
- Se **retira** la acción `create` del `UserViewSet`; `is_staff` pasa a read-only en `UserSerializer`.
- Tests seed-safe (`tenancy.testing.create_org`), gate de merge en DB fresca. Copy voseo, estética v2.

## File Structure

**Backend nuevos:** `backend/accounts/` (`__init__.py`, `apps.py`, `models.py`, `admin.py`, `serializers.py`, `views.py`, `emails.py`, `urls.py`, `tests.py`, `tests_adversarial.py`, `migrations/`).
**Backend modificados:** `config/settings.py` (INSTALLED_APPS, throttle rates, `FRONTEND_BASE_URL`), `config/urls.py` (includes), `users/views.py`, `users/serializers.py`.
**Frontend nuevos:** `src/views/public/RegisterView.vue`, `VerifyEmailView.vue`, `AcceptInvitationView.vue`, `src/views/dashboards/AdminMembers.vue`, `src/api/accounts.api.js`.
**Frontend modificados:** `src/router/index.js`, `src/views/LoginView.vue` (link a registro), `src/views/dashboards/AdminDashboard.vue` (nav a miembros).

---

### Task 1: App `accounts/` — modelos, admin, email helper, settings

**Files:**
- Create: `backend/accounts/__init__.py`, `apps.py`, `models.py`, `admin.py`, `emails.py`, `tests.py`
- Modify: `backend/config/settings.py`

**Interfaces:**
- Produces: `EmailVerificationToken`, `Invitation`; `accounts.emails.send_verification_email(user, token)` / `send_invitation_email(invitation)`; settings `FRONTEND_BASE_URL`, throttle scopes `register`/`resend`.

- [ ] **Step 1: Test que falla**

```python
# backend/accounts/tests.py
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from tenancy.testing import create_org
from accounts.models import EmailVerificationToken, Invitation

User = get_user_model()


class TokenModelTests(TestCase):
    def setUp(self):
        self.org = create_org("ACC")
        self.user = User.objects.create_user("u1", email="u1@x.com",
                                              role="ADMIN", organization=self.org, is_active=False)

    def test_verification_token_valido_y_expira(self):
        t = EmailVerificationToken.objects.create(user=self.user)
        self.assertTrue(t.token)
        self.assertTrue(t.is_valid())
        t.expires_at = timezone.now() - timedelta(hours=1)
        self.assertFalse(t.is_valid())
        t.expires_at = timezone.now() + timedelta(hours=1)
        t.used_at = timezone.now()
        self.assertFalse(t.is_valid())

    def test_invitation_acceptable_y_unica_pendiente(self):
        inv = Invitation.objects.create(organization=self.org, email="a@x.com", role="AGENT")
        self.assertTrue(inv.token)
        self.assertEqual(inv.status, "pending")
        self.assertTrue(inv.is_acceptable())
        with self.assertRaises(Exception):
            Invitation.objects.create(organization=self.org, email="a@x.com", role="CUSTOMER")
        inv.status = "revoked"; inv.save()
        # revocada libera el unique parcial: se puede re-invitar
        Invitation.objects.create(organization=self.org, email="a@x.com", role="AGENT")
```

- [ ] **Step 2: RED** — `cd backend && C:/Python312/python.exe manage.py test accounts -v 2 --keepdb` → ERROR (app no existe). (Usar `python` si está en PATH.)

- [ ] **Step 3: `apps.py` + `models.py`**

```python
# backend/accounts/apps.py
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
```

```python
# backend/accounts/models.py
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone


def _token():
    return uuid4().hex


def _verif_expiry():
    return timezone.now() + timedelta(hours=48)


def _invite_expiry():
    return timezone.now() + timedelta(days=7)


class EmailVerificationToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="email_verification")
    token = models.CharField(max_length=64, unique=True, default=_token)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_verif_expiry)
    used_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        return self.used_at is None and timezone.now() < self.expires_at


class Invitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        ACCEPTED = "accepted", "Aceptada"
        REVOKED = "revoked", "Revocada"

    organization = models.ForeignKey("tenancy.Organization", on_delete=models.CASCADE,
                                     related_name="invitations")
    email = models.EmailField()
    role = models.CharField(max_length=20)  # AGENT | CUSTOMER
    token = models.CharField(max_length=64, unique=True, default=_token)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="invitations_sent")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_invite_expiry)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "email"],
                condition=models.Q(status="pending"),
                name="uniq_pending_invitation",
            )
        ]

    def is_acceptable(self):
        return self.status == self.Status.PENDING and timezone.now() < self.expires_at
```

- [ ] **Step 4: `admin.py` + `emails.py` + settings**

```python
# backend/accounts/admin.py
from django.contrib import admin

from .models import EmailVerificationToken, Invitation


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "organization", "role", "status", "created_at", "expires_at")
    list_filter = ("status", "role")
    search_fields = ("email", "organization__name")


admin.site.register(EmailVerificationToken)
```

```python
# backend/accounts/emails.py
from django.conf import settings
from django.core.mail import send_mail


def _base():
    return getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")


def send_verification_email(user, token):
    link = f"{_base()}/verificar/{token}"
    send_mail(
        "Confirmá tu cuenta en AllSafe",
        f"Hola {user.first_name or ''},\n\nConfirmá tu email para activar tu cuenta:\n{link}\n\n"
        "El enlace vence en 48 horas.",
        settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False,
    )


def send_invitation_email(invitation):
    link = f"{_base()}/invitacion/{invitation.token}"
    send_mail(
        f"Te invitaron a {invitation.organization.name} en AllSafe",
        f"Te invitaron a unirte a {invitation.organization.name}.\n\n"
        f"Aceptá la invitación y creá tu contraseña:\n{link}\n\nEl enlace vence en 7 días.",
        settings.DEFAULT_FROM_EMAIL, [invitation.email], fail_silently=False,
    )
```

En `config/settings.py`: agregar `"accounts",` a INSTALLED_APPS (después de `"tenancy"`); en `DEFAULT_THROTTLE_RATES` sumar `"register": "5/hour"` y `"resend": "5/hour"`; y agregar `FRONTEND_BASE_URL = _env("FRONTEND_BASE_URL", "http://localhost:5173")` junto a los otros `_env`.

- [ ] **Step 5: Migración + GREEN** — `makemigrations accounts && manage.py test accounts -v 2 --keepdb` → PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/accounts/ backend/config/settings.py
git commit -m "feat(accounts): modelos de token (verificacion + invitacion) + email helper + settings"
```

---

### Task 2: Registro self-service + verificación de email

**Files:**
- Create: `backend/accounts/serializers.py` (parcial), `backend/accounts/views.py` (parcial), `backend/accounts/urls.py`
- Modify: `backend/config/urls.py`, `backend/accounts/tests.py`

**Interfaces:**
- Produces: `POST /api/auth/register/`, `POST /api/auth/verify-email/`, `POST /api/auth/resend-verification/`.

- [ ] **Step 1: Tests que fallan** (append a `accounts/tests.py`)

```python
from rest_framework.test import APIClient
from accounts.models import EmailVerificationToken


class RegisterFlowTests(TestCase):
    def setUp(self):
        self.c = APIClient()

    def test_registro_crea_org_admin_inactivo_y_token(self):
        r = self.c.post("/api/auth/register/", {
            "org_name": "Acme Corp", "first_name": "Ana", "last_name": "Paz",
            "email": "ana@acme.com", "password": "s3cretpass"}, format="json")
        self.assertEqual(r.status_code, 201)
        u = User.objects.get(email="ana@acme.com")
        self.assertFalse(u.is_active)
        self.assertEqual(u.role, "ADMIN")
        self.assertIsNotNone(u.organization)
        self.assertTrue(EmailVerificationToken.objects.filter(user=u).exists())

    def test_email_duplicado_400(self):
        User.objects.create_user("x", email="dup@x.com", organization=create_org("DUP"))
        r = self.c.post("/api/auth/register/", {
            "org_name": "Otra", "first_name": "a", "last_name": "b",
            "email": "dup@x.com", "password": "s3cretpass"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_verificar_activa_y_permite_login(self):
        self.c.post("/api/auth/register/", {
            "org_name": "Beta", "first_name": "a", "last_name": "b",
            "email": "beta@x.com", "password": "s3cretpass"}, format="json")
        tok = EmailVerificationToken.objects.get(user__email="beta@x.com")
        r = self.c.post("/api/auth/verify-email/", {"token": tok.token}, format="json")
        self.assertEqual(r.status_code, 200)
        tok.refresh_from_db()
        self.assertIsNotNone(tok.used_at)
        self.assertTrue(User.objects.get(email="beta@x.com").is_active)
        # token reusado -> 400
        self.assertEqual(self.c.post("/api/auth/verify-email/", {"token": tok.token},
                                     format="json").status_code, 400)

    def test_resend_no_revela_existencia(self):
        r1 = self.c.post("/api/auth/resend-verification/", {"email": "nadie@x.com"}, format="json")
        self.assertEqual(r1.status_code, 200)
```

- [ ] **Step 2: RED** — `manage.py test accounts.tests.RegisterFlowTests -v 2 --keepdb`.

- [ ] **Step 3: Serializers**

```python
# backend/accounts/serializers.py
import re

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from tenancy.models import Organization
from .models import EmailVerificationToken, Invitation

User = get_user_model()


def _make_slug(name):
    base = re.sub(r"[^A-Za-z0-9]", "", name or "").upper()[:12] or "ORG"
    slug, i = base, 1
    while Organization.objects.filter(slug=slug).exists():
        suffix = str(i)
        slug = (base[: 12 - len(suffix)] + suffix)
        i += 1
    return slug


class RegisterSerializer(serializers.Serializer):
    org_name = serializers.CharField(max_length=120)
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con ese email.")
        return value

    def validate_org_name(self, value):
        if Organization.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una organización con ese nombre.")
        return value

    @transaction.atomic
    def create(self, data):
        org = Organization.objects.create(name=data["org_name"], slug=_make_slug(data["org_name"]))
        user = User(username=data["email"], email=data["email"],
                    first_name=data["first_name"], last_name=data.get("last_name", ""),
                    role="ADMIN", organization=org, is_active=False)
        user.set_password(data["password"])
        user.save()
        token = EmailVerificationToken.objects.create(user=user)
        return user, token
```

- [ ] **Step 4: Views + urls**

```python
# backend/accounts/views.py
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .emails import send_verification_email
from .models import EmailVerificationToken
from .serializers import RegisterSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user, token = ser.save()
        send_verification_email(user, token.token)
        return Response({"ok": True}, status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        obj = EmailVerificationToken.objects.filter(token=token).select_related("user").first()
        if obj is None or not obj.is_valid():
            return Response({"detail": "Token inválido o vencido."}, status=400)
        from django.utils import timezone
        obj.user.is_active = True
        obj.user.save(update_fields=["is_active"])
        obj.used_at = timezone.now()
        obj.save(update_fields=["used_at"])
        return Response({"ok": True})


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "resend"

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.filter(email__iexact=email, is_active=False).first()
        if user is not None:
            EmailVerificationToken.objects.filter(user=user).delete()
            tok = EmailVerificationToken.objects.create(user=user)
            send_verification_email(user, tok.token)
        return Response({"ok": True})  # generico siempre (anti-enumeracion)
```

```python
# backend/accounts/urls.py
from django.urls import path

from .views import RegisterView, VerifyEmailView, ResendVerificationView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
]
```

En `config/urls.py`: `path("api/auth/", include("accounts.urls")),` (junto a las otras rutas `api/auth/`; el prefijo ya está exento del tenant-middleware).

- [ ] **Step 5: GREEN** — `manage.py test accounts -v 1 --keepdb` → PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/accounts/ backend/config/urls.py
git commit -m "feat(accounts): registro self-service + verificacion de email (anti-enumeracion)"
```

---

### Task 3: Invitaciones (viewset scoped + accept público)

**Files:**
- Modify: `backend/accounts/serializers.py`, `backend/accounts/views.py`, `backend/accounts/urls.py`, `backend/config/urls.py`, `backend/accounts/tests.py`

**Interfaces:**
- Consumes: `config.auth_views.cookie_settings/COOKIE_ACCESS_NAME/COOKIE_REFRESH_NAME`, `simplejwt.RefreshToken`, `tickets_t.permissions.IsAdmin`.
- Produces: `InvitationViewSet` (`/api/invitations/`), `GET/POST /api/auth/invitation/<token>/[accept/]`.

- [ ] **Step 1: Tests que fallan** (append a `accounts/tests.py`)

```python
from accounts.models import Invitation


class InvitationFlowTests(TestCase):
    def setUp(self):
        self.org = create_org("INV")
        self.admin = User.objects.create_user("adm", email="adm@inv.com", role="ADMIN",
                                               organization=self.org)
        self.c = APIClient()

    def test_admin_invita_y_el_invitado_acepta_con_su_password(self):
        self.c.force_authenticate(self.admin)
        r = self.c.post("/api/invitations/", {"email": "tec@inv.com", "role": "AGENT"},
                        format="json")
        self.assertEqual(r.status_code, 201)
        inv = Invitation.objects.get(email="tec@inv.com")
        pub = APIClient()
        g = pub.get(f"/api/auth/invitation/{inv.token}/")
        self.assertEqual(g.status_code, 200)
        self.assertEqual(g.json()["role"], "AGENT")
        a = pub.post(f"/api/auth/invitation/{inv.token}/accept/",
                     {"first_name": "Tec", "last_name": "Uno", "password": "s3cretpass"},
                     format="json")
        self.assertEqual(a.status_code, 200)
        u = User.objects.get(email="tec@inv.com")
        self.assertEqual(u.role, "AGENT")
        self.assertEqual(u.organization_id, self.org.id)
        self.assertTrue(u.is_active)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "accepted")

    def test_invitar_email_ya_usuario_400(self):
        self.c.force_authenticate(self.admin)
        r = self.c.post("/api/invitations/", {"email": "adm@inv.com", "role": "AGENT"},
                        format="json")
        self.assertEqual(r.status_code, 400)

    def test_lista_y_revoca_solo_de_su_org(self):
        self.c.force_authenticate(self.admin)
        self.c.post("/api/invitations/", {"email": "p@inv.com", "role": "CUSTOMER"}, format="json")
        inv = Invitation.objects.get(email="p@inv.com")
        self.assertEqual(len(self.c.get("/api/invitations/").json()), 1)
        self.assertEqual(self.c.delete(f"/api/invitations/{inv.id}/").status_code, 204)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "revoked")
```

- [ ] **Step 2: RED**, **Step 3: Serializers** (append a `accounts/serializers.py`)

```python
class InvitationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ["id", "email", "role", "status", "created_at", "expires_at"]
        read_only_fields = ["id", "status", "created_at", "expires_at"]

    def validate_role(self, value):
        if value not in ("AGENT", "CUSTOMER"):
            raise serializers.ValidationError("Rol inválido para invitación.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ese email ya tiene una cuenta.")
        org = self.context["request"].organization
        if Invitation.objects.filter(organization=org, email__iexact=value,
                                     status="pending").exists():
            raise serializers.ValidationError("Ya hay una invitación pendiente para ese email.")
        return value


class AcceptInvitationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True)
    # NO acepta role/organization: se toman del token en la vista (anti-escalada).
```

- [ ] **Step 4: Views** (append a `accounts/views.py`)

```python
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from config.auth_views import cookie_settings, COOKIE_ACCESS_NAME, COOKIE_REFRESH_NAME
from tickets_t.permissions import IsAdmin
from .emails import send_invitation_email
from .models import Invitation
from .serializers import InvitationCreateSerializer, AcceptInvitationSerializer


def _login_response(user, data, status_code=200):
    refresh = RefreshToken.for_user(user)
    resp = Response(data, status=status_code)
    opts = cookie_settings()
    resp.set_cookie(COOKIE_ACCESS_NAME, str(refresh.access_token), **opts)
    resp.set_cookie(COOKIE_REFRESH_NAME, str(refresh), **opts)
    return resp


class InvitationViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                        mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = InvitationCreateSerializer

    def get_queryset(self):
        return Invitation.objects.filter(
            organization=self.request.organization, status="pending").order_by("-created_at")

    def perform_create(self, serializer):
        inv = serializer.save(organization=self.request.organization,
                              invited_by=self.request.user)
        send_invitation_email(inv)

    def perform_destroy(self, instance):
        instance.status = Invitation.Status.REVOKED
        instance.save(update_fields=["status"])


class InvitationPublicView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        inv = Invitation.objects.filter(token=token).select_related("organization").first()
        if inv is None or not inv.is_acceptable():
            return Response({"detail": "Invitación inválida o vencida."}, status=404)
        return Response({"organization": inv.organization.name, "role": inv.role,
                         "email": inv.email})

    def post(self, request, token):
        inv = Invitation.objects.filter(token=token).select_related("organization").first()
        if inv is None or not inv.is_acceptable():
            return Response({"detail": "Invitación inválida o vencida."}, status=410)
        ser = AcceptInvitationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from django.contrib.auth import get_user_model
        from django.db import transaction
        with transaction.atomic():
            user = get_user_model()(
                username=inv.email, email=inv.email,
                first_name=ser.validated_data["first_name"],
                last_name=ser.validated_data.get("last_name", ""),
                role=inv.role, organization=inv.organization, is_active=True)
            user.set_password(ser.validated_data["password"])
            user.save()
            inv.status = Invitation.Status.ACCEPTED
            inv.save(update_fields=["status"])
        return _login_response(user, {"ok": True})
```

`accounts/urls.py` — agregar las rutas públicas de aceptación:

```python
from .views import InvitationPublicView
# ... en urlpatterns:
    path("invitation/<str:token>/", InvitationPublicView.as_view(), name="invitation-public"),
    path("invitation/<str:token>/accept/", InvitationPublicView.as_view(), name="invitation-accept"),
```

(El GET y el POST los maneja la misma `InvitationPublicView`; la ruta `/accept/` apunta al mismo `post`. Para evitar ambigüedad, `post` vive en ambas rutas — la de `/accept/` es la que usa el front; ambas resuelven por `post`.) **Nota implementer:** si preferís, separá en dos vistas (`InvitationDetailView.get` + `AcceptInvitationView.post`) para que cada ruta tenga un método; el plan lo permite siempre que el contrato de URLs quede igual.

`config/urls.py` — agregar el router de invitaciones (NO exento, necesita org):

```python
    path("api/invitations/", include("accounts.invitation_urls")),
```

con `accounts/invitation_urls.py`:

```python
from rest_framework.routers import DefaultRouter
from .views import InvitationViewSet

router = DefaultRouter()
router.register("", InvitationViewSet, basename="invitations")
urlpatterns = router.urls
```

- [ ] **Step 5: GREEN** — `manage.py test accounts -v 1 --keepdb` → PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/accounts/ backend/config/urls.py
git commit -m "feat(accounts): invitaciones por token (viewset scoped + accept publico que loguea)"
```

---

### Task 4: Retirar alta-con-password + is_staff read-only + guard último-admin

**Files:**
- Modify: `backend/users/views.py`, `backend/users/serializers.py`, `backend/users/tests.py`

**Interfaces:**
- Produces: `UserViewSet` sin `create`; `UserSerializer.is_staff` read-only; validación último-admin.

- [ ] **Step 1: Tests que fallan** (append a `users/tests.py`)

```python
class RetireCreateAndLastAdminTests(TestCase):
    def setUp(self):
        from tenancy.testing import create_org
        self.org = create_org("RCA")
        self.admin = User.objects.create_user("rca_adm", role="ADMIN", organization=self.org)
        self.c = APIClient(); self.c.force_authenticate(self.admin)

    def test_create_deshabilitado(self):
        r = self.c.post("/api/users/users/", {"username": "x", "password": "s3cretpass",
                                              "role": "AGENT"}, format="json")
        self.assertIn(r.status_code, (403, 405))

    def test_no_puede_degradar_al_ultimo_admin(self):
        r = self.c.patch(f"/api/users/users/{self.admin.id}/", {"role": "AGENT"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_is_staff_read_only(self):
        agent = User.objects.create_user("rca_ag", role="AGENT", organization=self.org)
        self.c.patch(f"/api/users/users/{agent.id}/", {"is_staff": True}, format="json")
        agent.refresh_from_db()
        self.assertFalse(agent.is_staff)
```

- [ ] **Step 2: RED**, **Step 3: Implementación**

`users/serializers.py`: en `UserSerializer.Meta.read_only_fields` agregar `"is_staff"`. Agregar validación del último admin en `update` (o en `UserViewSet.perform_update`):

```python
    def validate(self, attrs):
        inst = self.instance
        if inst is not None and inst.role == "ADMIN":
            demoting = attrs.get("role", inst.role) != "ADMIN"
            deactivating = attrs.get("is_active", inst.is_active) is False
            if demoting or deactivating:
                others = User.objects.filter(organization=inst.organization, role="ADMIN",
                                             is_active=True).exclude(pk=inst.pk).exists()
                if not others:
                    raise serializers.ValidationError(
                        "No podés dejar la organización sin un admin activo.")
        return attrs
```

`users/views.py`: retirar `create` — en `UserViewSet` agregar `http_method_names = ["get", "patch", "put", "delete", "head", "options"]` (sin `post`); quitar el branch de `create` de `get_serializer_class`/`get_permissions` si queda muerto, y el import de `UserCreateSerializer` si ya no se usa. (No borrar `UserCreateSerializer` del archivo por si algún test lo referencia; sólo dejar de rutearlo.)

- [ ] **Step 4: GREEN** — `manage.py test users -v 1 --keepdb` → PASS. (Ojo: tests viejos que hacían POST a users ahora esperan 405 — si alguno rompe, actualizarlo para reflejar que el alta ahora es por invitación.)

- [ ] **Step 5: Commit**

```bash
git add backend/users/
git commit -m "feat(users): retirar alta-con-password (ahora por invitacion) + is_staff read-only + guard ultimo-admin"
```

---

### Task 5: Suite adversarial de accounts

**Files:**
- Create: `backend/accounts/tests_adversarial.py`

- [ ] **Step 1: Escribir la suite** (todos deben pasar contra el código de T2-T4)

```python
# backend/accounts/tests_adversarial.py
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from tenancy.testing import create_org
from accounts.models import Invitation

User = get_user_model()


class InvitationAdversarialTests(TestCase):
    def setUp(self):
        self.org_a = create_org("ADA")
        self.org_b = create_org("ADB")
        self.admin_a = User.objects.create_user("ada_adm", email="ada@x.com", role="ADMIN",
                                                 organization=self.org_a)
        self.admin_b = User.objects.create_user("adb_adm", email="adb@x.com", role="ADMIN",
                                                 organization=self.org_b)

    def _invite(self, admin, email, role="AGENT"):
        c = APIClient(); c.force_authenticate(admin)
        c.post("/api/invitations/", {"email": email, "role": role}, format="json")
        return Invitation.objects.get(email=email)

    def test_accept_ignora_role_y_org_del_body(self):
        inv = self._invite(self.admin_a, "victim@x.com", role="CUSTOMER")
        pub = APIClient()
        r = pub.post(f"/api/auth/invitation/{inv.token}/accept/", {
            "first_name": "V", "password": "s3cretpass",
            "role": "ADMIN", "organization": self.org_b.id}, format="json")
        self.assertEqual(r.status_code, 200)
        u = User.objects.get(email="victim@x.com")
        self.assertEqual(u.role, "CUSTOMER")            # del token, no del body
        self.assertEqual(u.organization_id, self.org_a.id)  # del token, no del body

    def test_admin_no_revoca_invitacion_de_otra_org(self):
        inv_b = self._invite(self.admin_b, "b_guy@x.com")
        c = APIClient(); c.force_authenticate(self.admin_a)
        self.assertEqual(c.delete(f"/api/invitations/{inv_b.id}/").status_code, 404)
        inv_b.refresh_from_db()
        self.assertEqual(inv_b.status, "pending")

    def test_token_expirado_no_acepta(self):
        inv = self._invite(self.admin_a, "late@x.com")
        inv.expires_at = timezone.now() - timedelta(days=1); inv.save()
        r = APIClient().post(f"/api/auth/invitation/{inv.token}/accept/",
                             {"first_name": "L", "password": "s3cretpass"}, format="json")
        self.assertEqual(r.status_code, 410)
        self.assertFalse(User.objects.filter(email="late@x.com").exists())

    def test_token_reusado_no_crea_segundo_user(self):
        inv = self._invite(self.admin_a, "once@x.com")
        pub = APIClient()
        pub.post(f"/api/auth/invitation/{inv.token}/accept/",
                 {"first_name": "O", "password": "s3cretpass"}, format="json")
        r2 = pub.post(f"/api/auth/invitation/{inv.token}/accept/",
                      {"first_name": "O2", "password": "s3cretpass"}, format="json")
        self.assertIn(r2.status_code, (400, 410))
        self.assertEqual(User.objects.filter(email="once@x.com").count(), 1)

    def test_get_invitation_publico_no_expone_de mas(self):
        inv = self._invite(self.admin_a, "peek@x.com")
        data = APIClient().get(f"/api/auth/invitation/{inv.token}/").json()
        self.assertEqual(set(data), {"organization", "role", "email"})
```

**Nota implementer:** corregir el nombre del último método (`test_get_invitation_publico_no_expone_demas`, sin espacio) — es un typo del plan.

- [ ] **Step 2: GREEN** — `manage.py test accounts.tests_adversarial -v 2 --keepdb` → PASS. Si algún ataque pasa (p.ej. el body pisa el rol), es un bug real en T3 → arreglar el serializer/vista, no el test.

- [ ] **Step 3: Commit**

```bash
git add backend/accounts/tests_adversarial.py
git commit -m "test(accounts): suite adversarial (anti-escalada de rol/org, cross-org, token expirado/reusado)"
```

---

### Task 6: Frontend — vistas públicas (registro, verificación, aceptar invitación)

**Files:**
- Create: `frontend/src/api/accounts.api.js`, `src/views/public/RegisterView.vue`, `VerifyEmailView.vue`, `AcceptInvitationView.vue`
- Modify: `frontend/src/router/index.js`, `frontend/src/views/LoginView.vue`

**Interfaces:**
- Consumes: los endpoints de T2/T3.

- [ ] **Step 1: API client**

```javascript
// frontend/src/api/accounts.api.js
import { http } from "./http";

export async function registerOrg(payload) {
  return (await http.post("/api/auth/register/", payload)).data;
}
export async function verifyEmail(token) {
  return (await http.post("/api/auth/verify-email/", { token })).data;
}
export async function resendVerification(email) {
  return (await http.post("/api/auth/resend-verification/", { email })).data;
}
export async function getInvitation(token) {
  return (await http.get(`/api/auth/invitation/${token}/`)).data;
}
export async function acceptInvitation(token, payload) {
  return (await http.post(`/api/auth/invitation/${token}/accept/`, payload)).data;
}
```

- [ ] **Step 2: Vistas** — crear las tres SFCs (form + estados de error/éxito, estética v2, voseo):
  - `RegisterView.vue` (`/registro`): form `org_name/first_name/last_name/email/password` → `registerOrg` → pantalla "Revisá tu email para activar la cuenta" con botón de reenvío (`resendVerification`).
  - `VerifyEmailView.vue` (`/verificar/:token`): al montar llama `verifyEmail(route.params.token)` → éxito "Cuenta activada, iniciá sesión" con link a `/login`; error → mensaje + opción de reenvío.
  - `AcceptInvitationView.vue` (`/invitacion/:token`): al montar `getInvitation` → muestra "Te invitaron a **{organization}** como {rol}" + form `first_name/last_name/password` → `acceptInvitation` → como queda logueado (cookies), `auth.loadMe()` y redirigir con `auth.redirectByRole()`; token inválido → estado de error.

  (El implementer escribe el markup siguiendo el estilo de `LoginView.vue`: layout público, tokens CSS, hairlines.)

- [ ] **Step 3: Rutas** — en `router/index.js`, como hijos públicos de `PublicLayout` (junto a `login`), agregar con `meta: { public: true }`:

```javascript
      { path: "registro", name: "registro", component: RegisterView, meta: { public: true } },
      { path: "verificar/:token", name: "verificar", component: VerifyEmailView, meta: { public: true } },
      { path: "invitacion/:token", name: "invitacion", component: AcceptInvitationView, meta: { public: true } },
```

(importar las tres vistas arriba). En `LoginView.vue`, agregar un link "Registrá tu empresa" → `/registro`.

- [ ] **Step 4: Build** — `cd frontend && npm run build` → limpio.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/accounts.api.js frontend/src/views/public/ frontend/src/router/index.js frontend/src/views/LoginView.vue
git commit -m "feat(frontend): vistas publicas de registro, verificacion e invitacion"
```

---

### Task 7: Frontend — pantalla admin de miembros

**Files:**
- Create: `frontend/src/views/dashboards/AdminMembers.vue`
- Modify: `frontend/src/api/accounts.api.js` (helpers de invitaciones + miembros), `frontend/src/router/index.js`, `frontend/src/views/dashboards/AdminDashboard.vue`

**Interfaces:**
- Consumes: `/api/invitations/` (list/create/delete), `/api/users/users/` (list/patch/delete).

- [ ] **Step 1: API helpers** (append a `accounts.api.js`)

```javascript
export async function listInvitations() {
  return (await http.get("/api/invitations/")).data;
}
export async function createInvitation(email, role) {
  return (await http.post("/api/invitations/", { email, role })).data;
}
export async function revokeInvitation(id) {
  await http.delete(`/api/invitations/${id}/`);
}
export async function listMembers() {
  return (await http.get("/api/users/users/")).data;
}
export async function updateMember(id, patch) {
  return (await http.patch(`/api/users/users/${id}/`, patch)).data;
}
```

- [ ] **Step 2: `AdminMembers.vue`** (`/admin/miembros`, rol ADMIN): dos secciones —
  - **Miembros:** tabla de `listMembers()` con rol (select AGENT/CUSTOMER/ADMIN → `updateMember`), activar/desactivar (`is_active`), respetando errores del backend (toast del guard último-admin).
  - **Invitaciones pendientes:** form invitar (email + rol) → `createInvitation`; lista con botón revocar (`revokeInvitation`). Errores por toast (reusa el sistema del barrido).
  - Estados de carga/error, estética v2, voseo.

- [ ] **Step 3: Ruta + nav** — en `router/index.js` agregar `{ path: "/admin/miembros", name: "admin-miembros", component: AdminMembers, meta: { role: "ADMIN" } }`; en `AdminDashboard.vue`, agregar el link `<router-link to="/admin/miembros" class="cms-link">Miembros</router-link>` en la barra de nav (junto a SLA/Métricas).

- [ ] **Step 4: Build + verificación** — `npm run build` limpio. Manual (con servers): registrar una org demo, verificar por el token (leerlo de la consola de email en dev), loguear, invitar un técnico, aceptar en otra pestaña.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/dashboards/AdminMembers.vue frontend/src/api/accounts.api.js frontend/src/router/index.js frontend/src/views/dashboards/AdminDashboard.vue
git commit -m "feat(frontend): pantalla admin de miembros e invitaciones"
```

---

## Self-Review (autor del plan)

- **Cobertura del spec:** modelos+email (T1), registro+verify+resend (T2), invitaciones viewset+accept (T3), retiro del alta-con-password + is_staff read-only + último-admin (T4), suite adversarial (T5), vistas públicas (T6), pantalla de miembros (T7). ✅
- **Seguridad:** el rol/org del `accept` salen del token (T3, `AcceptInvitationSerializer` sin esos campos) y hay test adversarial que lo prueba forzándolos por el body (T5). Registro siempre ADMIN de org nueva. Público exento del middleware pero con throttle. ✅
- **Verde por task:** cada task backend corre su suite; T4 avisa que tests viejos de POST a users pueden requerir actualización (esperado, documentado). ✅
- **Consistencia:** `_login_response` reusa `cookie_settings/COOKIE_*` de `auth_views`; `InvitationViewSet` usa `IsAdmin` de `tickets_t.permissions` (mismo que H1) + scope por `request.organization`; el guard CI de H1 no aplica (accounts no toca `Ticket.objects`). ✅
- **Riesgos:** typo intencional señalado en T5 (nombre de método) para que el implementer lo corrija; la doble-ruta de `InvitationPublicView` (GET detalle / POST accept) tiene nota de alternativa por si el reviewer prefiere vistas separadas. ✅
