# H1 · Núcleo Multi-tenant — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aislamiento total por organización: cada empresa tiene sus admins/técnicos/clientes y ningún camino cruza tenants. "AllSafe" pasa a ser la org semilla.

**Architecture:** Schema compartido + FK `organization` (MySQL). App nueva `tenancy/` (modelo + middleware fail-closed + `scoping.py` como fuente única de querysets). `SlaConfig` deja de ser singleton → per-org. Suite adversarial + guard CI anti-queryset-crudo como entregables de calidad.

**Tech Stack:** Django 6 + DRF + Channels (existente). Sin dependencias nuevas.

## Global Constraints

- **Cada task termina con la suite tocada EN VERDE** — el orden de tasks está diseñado para eso (el middleware se registra recién en T3, después de actualizar fixtures).
- **Cross-tenant SIEMPRE 404** para recursos con ID (no revelar existencia); listas simplemente no incluyen lo ajeno.
- **Superuser de plataforma (org=None) NO ve datos de tenants por la API in-app** — sólo `/django-admin/`. `org_tickets(None)` → queryset vacío; `can_access_ticket` exige `user.organization_id == ticket.organization_id` sin excepción de superuser.
- **Fail-closed:** usuario autenticado sin org y sin `is_superuser` → 403 del middleware en `/api/`; org `is_active=False` → 403 "Organización suspendida".
- **`tenancy/scoping.py` es la fuente única** de querysets scoped. Guard de CI (T7) falla si aparece `Ticket.objects` fuera del allowlist.
- Roles ADMIN/AGENT/CUSTOMER = rol DENTRO de su org. La lógica por-rol existente se conserva, anidada dentro del scope de org.
- Referencias de ticket: `{org.slug}-YYYYMMDD-NNN` (contador por org+día; el `select_for_update` por prefijo sigue siendo correcto porque el prefijo ahora incluye el slug).
- `asignado_a` debe pertenecer a la misma org que el ticket (validación en serializer).
- Tests seed-safe: fixtures usan `tenancy.testing.create_org()`; jamás depender de seeds de migración. Gate de merge: suite completa DB fresca.

## File Structure

**Nuevos:** `backend/tenancy/` (`__init__.py`, `apps.py`, `models.py`, `admin.py`, `middleware.py`, `scoping.py`, `testing.py`, `migrations/`, `tests.py`, `tests_isolation.py`).
**Modificados:** `users/models.py` (+FK), `tickets_t/models.py` (+FK), `tickets_t/{views,serializers,permissions}.py`, `sla/{models,calendar_engine,signals,checker,admin_views}.py`, `sla/management/commands/check_sla.py`, `notifications/services.py`, `metrics/{services,views}.py`, `users/views.py`, `config/{settings,views}.py`, `frontend/src/components/AppTopBar.vue`, y las suites de tests de todas las apps.

---

### Task 1: App `tenancy/` — modelo, admin, middleware (sin registrar), scoping base

**Files:**
- Create: `backend/tenancy/__init__.py` (vacío), `apps.py`, `models.py`, `admin.py`, `middleware.py`, `scoping.py`, `tests.py`
- Modify: `backend/config/settings.py` (INSTALLED_APPS únicamente — el middleware NO se registra todavía)

**Interfaces:**
- Produces: `Organization(name, slug, is_active, created_at)`; `OrganizationMiddleware` (se registra en T3); `scoping.org_users/org_agents/org_admins/user_org` (los de tickets llegan en T5, los de sla en T4).

- [ ] **Step 1: Test que falla**

```python
# backend/tenancy/tests.py
from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Organization
from .scoping import org_admins, org_agents, org_users, user_org

User = get_user_model()


class OrganizationModelTests(TestCase):
    def test_slug_unico_y_str(self):
        org = Organization.objects.create(name="Acme Corp", slug="ACME")
        self.assertEqual(str(org), "Acme Corp")
        self.assertTrue(org.is_active)
        with self.assertRaises(Exception):
            Organization.objects.create(name="Otra", slug="ACME")


class ScopingUserTests(TestCase):
    def setUp(self):
        self.a = Organization.objects.create(name="A", slug="AAA")
        self.b = Organization.objects.create(name="B", slug="BBB")
        self.admin_a = User.objects.create_user("adm_a", role="ADMIN", organization=self.a)
        self.agent_a = User.objects.create_user("agt_a", role="AGENT", organization=self.a)
        self.cust_b = User.objects.create_user("cus_b", role="CUSTOMER", organization=self.b)

    def test_org_users_no_cruza(self):
        self.assertEqual(set(org_users(self.a)), {self.admin_a, self.agent_a})
        self.assertEqual(set(org_users(self.b)), {self.cust_b})
        self.assertEqual(org_users(None).count(), 0)

    def test_org_agents_y_admins(self):
        self.assertEqual(list(org_agents(self.a)), [self.agent_a])
        self.assertEqual(list(org_admins(self.a)), [self.admin_a])

    def test_user_org(self):
        self.assertEqual(user_org(self.admin_a), self.a)
        platform = User.objects.create_user("plat", is_superuser=True)
        self.assertIsNone(user_org(platform))
```

**Nota:** este test referencia `organization=` en `create_user` — el FK de User llega en T2, así que en T1 el test se escribe SOLO hasta `OrganizationModelTests` y `ScopingUserTests` queda comentado con `# T2: descomentar al agregar User.organization`. El RED de T1 es sobre `OrganizationModelTests`.

- [ ] **Step 2: RED** — `cd backend && python manage.py test tenancy -v 2 --keepdb` → ERROR (app no existe).

- [ ] **Step 3: Implementar la app**

```python
# backend/tenancy/apps.py
from django.apps import AppConfig


class TenancyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tenancy"
```

```python
# backend/tenancy/models.py
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=12, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        self.slug = (self.slug or "").upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
```

```python
# backend/tenancy/admin.py
from django.contrib import admin

from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("is_active",)
```

```python
# backend/tenancy/middleware.py
from django.http import JsonResponse


class OrganizationMiddleware:
    """Setea request.organization y aplica fail-closed en /api/.

    - Usuario autenticado sin org y sin is_superuser -> 403 (cuenta mal provisionada).
    - Org suspendida (is_active=False) -> 403.
    - Superuser de plataforma (org=None) pasa, pero con request.organization=None:
      los helpers de scoping devuelven vacio -> no ve datos de tenants por la API.
    Exentos: /api/health/ y /api/auth/ (login/refresh/logout necesitan funcionar).
    """

    EXEMPT_PREFIXES = ("/api/health/", "/api/auth/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        org = getattr(request.user, "organization", None) if request.user.is_authenticated else None
        request.organization = org
        path = request.path
        if path.startswith("/api/") and not path.startswith(self.EXEMPT_PREFIXES):
            if request.user.is_authenticated:
                if org is None and not request.user.is_superuser:
                    return JsonResponse({"detail": "Cuenta sin organización."}, status=403)
                if org is not None and not org.is_active:
                    return JsonResponse({"detail": "Organización suspendida."}, status=403)
        return self.get_response(request)
```

```python
# backend/tenancy/scoping.py
"""Fuente UNICA de querysets scoped por organizacion.

Toda vista/consumer/servicio que liste o busque recursos de un tenant DEBE
pasar por estos helpers. El guard de CI (tenancy/tests.py) falla si aparece
un queryset crudo de Ticket fuera de este modulo y su allowlist.
org=None (staff de plataforma en la API in-app) -> queryset vacio, siempre.
"""
from django.contrib.auth import get_user_model


def _User():
    return get_user_model()


def user_org(user):
    return getattr(user, "organization", None)


def org_users(org):
    qs = _User().objects.all().order_by("id")
    return qs.filter(organization=org) if org is not None else qs.none()


def org_agents(org):
    return org_users(org).filter(role="AGENT")


def org_admins(org):
    return org_users(org).filter(role="ADMIN")
```

En `config/settings.py`, agregar `"tenancy",` a INSTALLED_APPS antes de `"users"`. **NO tocar MIDDLEWARE todavía.**

- [ ] **Step 4: Migración + GREEN** — `python manage.py makemigrations tenancy && python manage.py test tenancy -v 2 --keepdb` → PASS (`OrganizationModelTests`).

- [ ] **Step 5: Commit**

```bash
git add backend/tenancy/ backend/config/settings.py
git commit -m "feat(tenancy): app base - Organization, middleware (sin registrar), scoping de usuarios"
```

---

### Task 2: FKs de organización + migración semilla + helper de testing + `/api/me/`

**Files:**
- Modify: `backend/users/models.py`, `backend/tickets_t/models.py`, `backend/config/views.py`, `backend/tenancy/tests.py` (descomentar `ScopingUserTests`)
- Create: `backend/tenancy/testing.py`, migraciones (`users`, `tickets_t` schema; `tenancy/0002_seed_org` data)

**Interfaces:**
- Produces: `User.organization` (FK null=True), `Ticket.organization` (FK null=True en esta task; NOT NULL en T7), `tenancy.testing.create_org(slug)`, `/api/me/` expone `organization` (name o null).

- [ ] **Step 1: Tests que fallan**

Append a `backend/tenancy/tests.py` (y descomentar `ScopingUserTests`):

```python
import importlib


class SeedMigrationTests(TestCase):
    def test_seed_asigna_todo_a_la_org_semilla(self):
        from tickets_t.models import Ticket
        u = User.objects.create_user("legacy_user", role="CUSTOMER")
        t = Ticket.objects.create(reference="LEG-001", titulo="t", descripcion="d",
                                  creado_por=u)
        mod = importlib.import_module("tenancy.migrations.0002_seed_org")
        from django.apps import apps as global_apps
        mod.seed_org(global_apps, None)
        u.refresh_from_db(); t.refresh_from_db()
        self.assertIsNotNone(u.organization)
        self.assertEqual(u.organization.slug, "ALS")
        self.assertEqual(t.organization_id, u.organization_id)

    def test_seed_idempotente(self):
        mod = importlib.import_module("tenancy.migrations.0002_seed_org")
        from django.apps import apps as global_apps
        mod.seed_org(global_apps, None)
        mod.seed_org(global_apps, None)
        self.assertEqual(Organization.objects.filter(slug="ALS").count(), 1)
```

- [ ] **Step 2: RED** — `python manage.py test tenancy -v 2 --keepdb` → ERROR (FKs/migración no existen).

- [ ] **Step 3: FKs**

En `backend/users/models.py`, dentro de `class User`, después de `role`:

```python
    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )
```

En `backend/tickets_t/models.py`, dentro de `class Ticket`, después de `asignado_a`:

```python
    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        null=True,   # NOT NULL en T7, cuando todo el codigo ya la setea
        blank=True,
        related_name="tickets",
    )
```

y en su `Meta`/índices: `models.Index(fields=["organization", "created_at"])` (si Ticket no tiene Meta, crearla con `indexes = [...]`).

`python manage.py makemigrations users tickets_t`

- [ ] **Step 4: Migración semilla**

`backend/tenancy/migrations/0002_seed_org.py` (ajustar `dependencies` a los nombres reales que generó makemigrations):

```python
from django.db import migrations


def seed_org(apps, schema_editor):
    Organization = apps.get_model("tenancy", "Organization")
    User = apps.get_model("users", "User")
    Ticket = apps.get_model("tickets_t", "Ticket")
    org, _ = Organization.objects.get_or_create(slug="ALS", defaults={"name": "AllSafe"})
    User.objects.filter(organization__isnull=True).update(organization=org)
    Ticket.objects.filter(organization__isnull=True).update(organization=org)


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0001_initial"),
        ("users", "XXXX_user_organization"),      # nombre real de makemigrations
        ("tickets_t", "XXXX_ticket_organization"), # nombre real de makemigrations
    ]

    operations = [
        migrations.RunPython(seed_org, migrations.RunPython.noop),
    ]
```

- [ ] **Step 5: Helper de testing**

```python
# backend/tenancy/testing.py
"""Helpers de fixtures multi-org para las suites. NO usar seeds de migracion."""
from .models import Organization

_DEFAULT_POLICIES = [("URGENT", 30, 240), ("HIGH", 60, 480),
                     ("MEDIUM", 120, 960), ("LOW", 240, 1920)]


def create_org(slug="TST", name=None):
    """Crea una org con SLA config + policies default. Idempotente por slug."""
    org, created = Organization.objects.get_or_create(
        slug=slug, defaults={"name": name or f"Org {slug}"})
    # Provision SLA (T4 agrega el signal de produccion; el helper garantiza
    # el estado en tests aunque el signal exista — get_or_create es idempotente).
    from sla.models import SlaConfig, SlaPolicy
    SlaConfig.objects.get_or_create(organization=org)
    for prio, fr, res in _DEFAULT_POLICIES:
        SlaPolicy.objects.get_or_create(
            organization=org, priority=prio,
            defaults={"first_response_minutes": fr, "resolution_minutes": res})
    return org
```

**Nota:** `testing.py` referencia el schema per-org de sla que llega en T4. En T2, crear el archivo con la parte de SLA envuelta en `try/except ImportError`/`TypeError` NO — en cambio: en T2 el helper crea SOLO la org (las líneas de SLA se agregan en T4, donde también se actualizan las fixtures que lo usan). Dejar el bloque SLA comentado con `# T4: descomentar`.

- [ ] **Step 6: `/api/me/` expone organization**

En `config/views.py` `me()`, agregar al dict:

```python
            "organization": u.organization.name if u.organization_id else None,
```

- [ ] **Step 7: GREEN** — `python manage.py test tenancy users -v 1 --keepdb` → PASS. Luego `python manage.py migrate` (aplica FKs + semilla a la DB de dev; los usuarios/tickets existentes quedan en ALS).

- [ ] **Step 8: Commit**

```bash
git add backend/tenancy/ backend/users/ backend/tickets_t/models.py backend/tickets_t/migrations/ backend/config/views.py
git commit -m "feat(tenancy): FKs de organizacion + migracion semilla ALS + /api/me/ organization"
```

---

### Task 3: Fixtures multi-org en TODAS las suites + registrar el middleware

**Files:**
- Modify: `backend/config/settings.py` (MIDDLEWARE), `backend/tenancy/tests.py` (tests del middleware), y los `setUp`/helpers de: `tickets_t/tests.py`, `sla/tests.py`, `csat/tests.py`, `metrics/tests.py`, `notifications/tests.py`, `users/tests.py`

**Interfaces:**
- Consumes: `create_org` (T2). Produces: middleware activo; toda suite corre con usuarios que tienen org.

- [ ] **Step 1: Tests del middleware (RED)**

Append a `backend/tenancy/tests.py`:

```python
from rest_framework.test import APIClient


class MiddlewareTests(TestCase):
    def setUp(self):
        from .testing import create_org
        self.org = create_org("MWA")
        self.client_api = APIClient()

    def test_user_sin_org_403(self):
        u = User.objects.create_user("sinorg", role="CUSTOMER")
        self.client_api.force_authenticate(u)
        r = self.client_api.get("/api/tickets_t/")
        self.assertEqual(r.status_code, 403)
        self.assertIn("organización", r.json()["detail"].lower())

    def test_org_suspendida_403(self):
        self.org.is_active = False
        self.org.save()
        u = User.objects.create_user("susp", role="CUSTOMER", organization=self.org)
        self.client_api.force_authenticate(u)
        r = self.client_api.get("/api/tickets_t/")
        self.assertEqual(r.status_code, 403)

    def test_health_y_auth_exentos(self):
        self.assertEqual(self.client_api.get("/api/health/").status_code, 200)
```

**Nota:** la URL de lista de tickets es la que registre el router de `tickets_t/urls.py` — el implementer la verifica (`/api/tickets_t/` o la real) y usa esa.

- [ ] **Step 2: Registrar el middleware**

En `config/settings.py` MIDDLEWARE, inmediatamente después de `AuthenticationMiddleware`:

```python
    "tenancy.middleware.OrganizationMiddleware",
```

- [ ] **Step 3: Actualizar TODAS las fixtures**

Patrón mecánico por suite (el implementer lo aplica en cada `setUp` que crea usuarios):

```python
from tenancy.testing import create_org
# en setUp:
self.org = create_org("TST")   # o el slug que distinga la suite
# y cada create_user(...) de la fixture gana organization=self.org
# los superusers de plataforma de tests de /django-admin quedan sin org
```

Los tests que crean `Ticket` directamente agregan `organization=self.org` (mientras el FK es null=True no es obligatorio, pero las fixtures deben quedar correctas ya).
En `metrics/tests.py`, `MetricsFactoryMixin.setUp` crea `self.org` y lo propaga; `make_ticket` gana `organization=self.org`.

- [ ] **Step 4: GREEN total** — `python manage.py test --noinput -v 1` (suite completa fresca; es el punto de mayor churn del plan, se valida entera). Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat(tenancy): middleware fail-closed activo + fixtures multi-org en todas las suites"
```

---

### Task 4: SLA por organización

**Files:**
- Modify: `backend/sla/models.py`, `calendar_engine.py`, `signals.py`, `checker.py`, `admin_views.py`, `management/commands/check_sla.py`, `sla/tests.py`, `backend/tenancy/testing.py` (descomentar bloque SLA), `metrics/tests.py` y `csat/tests.py` (sus `_seed_sla` locales), `backend/tickets_t/views.py` (contexto de calendario), `backend/metrics/views.py` (get_calendar(org))
- Create: migraciones de `sla` (schema + data reasignación a ALS)

**Interfaces:**
- Produces: `SlaConfig.organization` (OneToOne), `SlaPolicy/Holiday.organization` (FK, uniques compuestos), `get_calendar(org)`, provisioning automático al crear org (signal), checker/scheduler por org.

- [ ] **Step 1: Tests que fallan** (append a `sla/tests.py`)

```python
class PerOrgSlaTests(TestCase):
    def setUp(self):
        from tenancy.testing import create_org
        self.a = create_org("SLA1")
        self.b = create_org("SLB2")

    def test_config_por_org_independiente(self):
        ca = SlaConfig.objects.get(organization=self.a)
        cb = SlaConfig.objects.get(organization=self.b)
        ca.work_start = time(7, 0); ca.save()
        cb.refresh_from_db()
        self.assertEqual(cb.work_start, time(9, 0))

    def test_calendarios_distintos_producen_deadlines_distintos(self):
        from sla.calendar_engine import get_calendar, add_business_time
        ca = SlaConfig.objects.get(organization=self.a)
        ca.work_end = time(20, 0); ca.save()
        start = datetime(2026, 1, 5, 17, 0, tzinfo=MX)  # lunes 17:00
        due_a = add_business_time(start, 120, get_calendar(self.a))  # hasta 20h: mismo dia
        due_b = add_business_time(start, 120, get_calendar(self.b))  # hasta 18h: cruza al martes
        self.assertNotEqual(due_a, due_b)

    def test_provisioning_al_crear_org(self):
        from tenancy.models import Organization
        org = Organization.objects.create(name="Nueva", slug="NEW")
        self.assertTrue(SlaConfig.objects.filter(organization=org).exists())
        self.assertEqual(SlaPolicy.objects.filter(organization=org).count(), 4)
```

(imports `time`/`datetime`/`MX` según los ya presentes en el archivo; agregar los que falten.)

- [ ] **Step 2: RED** — `python manage.py test sla.tests.PerOrgSlaTests -v 2 --keepdb`.

- [ ] **Step 3: Schema per-org**

En `sla/models.py`:
- Eliminar `SingletonManager` y el `objects = SingletonManager()` / override de `save` de `SlaConfig`.
- `SlaConfig` gana `organization = models.OneToOneField("tenancy.Organization", on_delete=models.CASCADE, related_name="sla_config", null=True)` (null transitorio para la migración; el data-migration puebla y una migración posterior en esta misma task lo vuelve NOT NULL).
- `SlaPolicy`: quitar `unique=True` de `priority`; agregar `organization = models.ForeignKey("tenancy.Organization", on_delete=models.CASCADE, null=True)` y `Meta.constraints = [models.UniqueConstraint(fields=["organization", "priority"], name="uniq_policy_org_priority")]`.
- `Holiday`: agregar FK org igual + `UniqueConstraint(fields=["organization", "date"], name="uniq_holiday_org_date")` (quitando el `unique=True` del date).

Migración de datos (en `sla/migrations/`): asigna la config/policies/holidays existentes a la org `slug="ALS"` (creándola con get_or_create si no existe — DBs de test). Luego `AlterField` a `null=False` para los tres FKs.

- [ ] **Step 4: Provisioning signal** (en `sla/signals.py`)

```python
DEFAULT_POLICIES = [("URGENT", 30, 240), ("HIGH", 60, 480),
                    ("MEDIUM", 120, 960), ("LOW", 240, 1920)]


@receiver(post_save, sender="tenancy.Organization")
def provision_org_sla(sender, instance, created, **kwargs):
    if not created:
        return
    from .models import SlaConfig, SlaPolicy
    SlaConfig.objects.get_or_create(organization=instance)
    for prio, fr, res in DEFAULT_POLICIES:
        SlaPolicy.objects.get_or_create(
            organization=instance, priority=prio,
            defaults={"first_response_minutes": fr, "resolution_minutes": res})
```

- [ ] **Step 5: Motor y consumidores por org**

- `calendar_engine.get_calendar(org)`: `cfg = SlaConfig.objects.get(organization=org)`; holidays filtrados por org. Callers actualizados:
  - `signals.create_ticket_sla`: `policy = SlaPolicy.objects.filter(organization=ticket.organization, priority=...).first()`; `cal = get_calendar(ticket.organization)`; ídem `_recompute_unmet`.
  - `checker.run_sla_check()`: agrupa por `ts.ticket.organization_id`, construye un calendar por org (dict cache), procesa igual. Ignora orgs `is_active=False`.
  - `tickets_t/views.get_serializer_context`: `get_calendar(self.request.organization)` (si None → no setear el contexto).
  - `metrics/views`: `cal = get_calendar(request.organization)`.
  - `sla/admin_views`: `ConfigView` opera sobre `SlaConfig.objects.get(organization=request.organization)`; `PoliciesView` filtra por org; `HolidayViewSet.get_queryset` filtra por org y `perform_create` setea org.
- `tenancy/testing.py`: descomentar el bloque SLA del helper.
- Actualizar los `_seed_sla`/fixtures de `sla/metrics/csat` para el mundo per-org (usar `create_org`; donde los tests editaban `SlaConfig.objects.get_solo()`, pasan a `SlaConfig.objects.get(organization=self.org)`).

- [ ] **Step 6: GREEN** — `python manage.py test sla metrics csat tickets_t -v 1 --keepdb` → PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/sla/ backend/tenancy/testing.py backend/metrics/ backend/csat/ backend/tickets_t/views.py
git commit -m "feat(sla): configuracion, policies, feriados y scheduler por organizacion"
```

---

### Task 5: Scoping de `tickets_t`

**Files:**
- Modify: `backend/tenancy/scoping.py` (+`org_tickets`), `backend/tickets_t/views.py`, `permissions.py`, `serializers.py`, `tests.py`

**Interfaces:**
- Produces: `org_tickets(org)`; `can_access_ticket` exige same-org; referencia `{slug}-YYYYMMDD-NNN`; validación asignado same-org; pool/take/upload/download scoped.

- [ ] **Step 1: Tests que fallan** (append a `tickets_t/tests.py`; la suite ya tiene `self.org` de T3 — estos tests crean una segunda org)

```python
class TenantScopingTests(TestCase):
    def setUp(self):
        from tenancy.testing import create_org
        self.org_a = create_org("TSA")
        self.org_b = create_org("TSB")
        self.cust_a = User.objects.create_user("tsc_a", role="CUSTOMER", organization=self.org_a)
        self.admin_a = User.objects.create_user("tsa_a", role="ADMIN", organization=self.org_a)
        self.agent_b = User.objects.create_user("tsg_b", role="AGENT", organization=self.org_b)
        self.t_b = Ticket.objects.create(reference="TSB-X-1", titulo="b", descripcion="d",
                                         creado_por=User.objects.create_user(
                                             "tscust_b", role="CUSTOMER", organization=self.org_b),
                                         organization=self.org_b)
        self.client_api = APIClient()

    def test_admin_no_ve_tickets_de_otra_org(self):
        self.client_api.force_authenticate(self.admin_a)
        r = self.client_api.get(f"/api/tickets_t/{self.t_b.id}/")
        self.assertEqual(r.status_code, 404)

    def test_referencia_usa_slug_de_la_org(self):
        self.client_api.force_authenticate(self.cust_a)
        r = self.client_api.post("/api/tickets_t/", {"titulo": "t", "descripcion": "d",
                                                     "prioridad": "MEDIUM"})
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.json()["reference"].startswith("TSA-"))

    def test_asignar_tecnico_de_otra_org_falla(self):
        t = Ticket.objects.create(reference="TSA-X-1", titulo="a", descripcion="d",
                                  creado_por=self.cust_a, organization=self.org_a)
        self.client_api.force_authenticate(self.admin_a)
        r = self.client_api.patch(f"/api/tickets_t/{t.id}/", {"asignado_a": self.agent_b.id})
        self.assertEqual(r.status_code, 400)

    def test_can_access_niega_cross_org_y_superuser_sin_org(self):
        self.assertFalse(can_access_ticket(self.admin_a, self.t_b))
        plat = User.objects.create_user("plat_su", is_superuser=True)
        self.assertFalse(can_access_ticket(plat, self.t_b))
```

(URLs según el router real; `can_access_ticket` ya está importado en el archivo.)

- [ ] **Step 2: RED**, **Step 3: Implementación**

`tenancy/scoping.py` — agregar:

```python
def org_tickets(org):
    from tickets_t.models import Ticket
    qs = Ticket.objects.select_related("sla", "csat")
    return qs.filter(organization=org) if org is not None else qs.none()
```

`tickets_t/permissions.py` — `can_access_ticket`, primera condición tras el check de autenticación:

```python
    if getattr(user, "organization_id", None) != ticket.organization_id:
        return False
```

(y se elimina la excepción `user.is_superuser` del branch de ADMIN — plataforma no entra por la API).

`tickets_t/views.py`:
- `get_queryset`: base `org_tickets(self.request.organization).order_by("-created_at")`; los branch por rol se aplican sobre esa base (ADMIN → base; AGENT → `.filter(asignado_a=user)`; CUSTOMER → `.filter(creado_por=user)`). `_is_admin`/`_is_agent` pierden el shortcut `is_superuser`.
- `pool`: `org_tickets(request.organization).filter(asignado_a__isnull=True, estado__in=[...])`.
- `take`: `org_tickets(request.organization).select_for_update().get(pk=pk)` dentro del atomic (DoesNotExist → 404 como hoy).
- `upload_attachment`/`download_attachment`: `org_tickets(request.organization).filter(pk=pk).first()` (defensa en profundidad: `can_access_ticket` se mantiene después).

`tickets_t/serializers.py`:
- `TicketCreateSerializer.create`: `org = request.user.organization`; `prefix = f"{org.slug}-" + timezone.localdate().strftime("%Y%m%d") + "-"`; el ticket se crea con `organization=org`.
- `TicketSerializer`: agregar `validate_asignado_a`:

```python
    def validate_asignado_a(self, value):
        if value is None:
            return value
        request = self.context.get("request")
        org = getattr(request, "organization", None) if request else None
        if org is None or value.organization_id != org.id:
            raise serializers.ValidationError("El técnico debe pertenecer a tu organización.")
        return value
```

- [ ] **Step 4: GREEN** — `python manage.py test tickets_t -v 1 --keepdb` → PASS (incluye la suite previa: los tests de Channels heredan el org-check vía `can_access_ticket`).

- [ ] **Step 5: Commit**

```bash
git add backend/tenancy/scoping.py backend/tickets_t/
git commit -m "feat(tickets_t): scoping por organizacion (querysets, referencia por slug, asignacion same-org)"
```

---

### Task 6: Scoping de `notifications`, `metrics` y `users`

**Files:**
- Modify: `backend/notifications/services.py`, `backend/metrics/services.py`, `backend/metrics/views.py`, `backend/users/views.py`, tests de las tres apps

**Interfaces:**
- Produces: `_admins(org)`/`_agents(org)` en notifications (org = `ticket.organization`); `windowed_tickets(window, org)`; `UserViewSet` scoped + alta con org forzada.

- [ ] **Step 1: Tests que fallan**

`notifications/tests.py` — append:

```python
class TenantNotificationTests(TestCase):
    def test_ticket_created_no_notifica_admins_de_otra_org(self):
        from tenancy.testing import create_org
        a, b = create_org("NTA"), create_org("NTB")
        admin_a = User.objects.create_user("nta_adm", role="ADMIN", organization=a)
        admin_b = User.objects.create_user("ntb_adm", role="ADMIN", organization=b)
        cust_a = User.objects.create_user("nta_cus", role="CUSTOMER", organization=a)
        t = Ticket.objects.create(reference="NTA-1", titulo="x", descripcion="d",
                                  creado_por=cust_a, organization=a)
        dispatch("ticket_created", t)
        recipients = set(Notification.objects.filter(kind="ticket_created")
                         .values_list("recipient_id", flat=True))
        self.assertIn(admin_a.id, recipients)
        self.assertNotIn(admin_b.id, recipients)
```

`metrics/tests.py` — append (el mixin ya tiene `self.org` de T3):

```python
class TenantMetricsTests(MetricsFactoryMixin, TestCase):
    def test_windowed_no_mezcla_orgs(self):
        from tenancy.testing import create_org
        other = create_org("MTB")
        other_cust = User.objects.create_user("mtb_c", role="CUSTOMER", organization=other)
        Ticket.objects.create(reference="MTB-1", titulo="x", descripcion="d",
                              creado_por=other_cust, organization=other)
        self.make_ticket()
        self.assertEqual(services.volume_totals(services.windowed_tickets(30, self.org))["total"], 1)
        self.assertEqual(services.volume_totals(services.windowed_tickets(30, None))["total"], 0)
```

`users/tests.py` — append:

```python
class TenantUserAdminTests(TestCase):
    def test_admin_solo_lista_y_crea_en_su_org(self):
        from tenancy.testing import create_org
        a, b = create_org("UTA"), create_org("UTB")
        admin_a = User.objects.create_user("uta_adm", role="ADMIN", organization=a)
        User.objects.create_user("utb_user", role="CUSTOMER", organization=b)
        c = APIClient(); c.force_authenticate(admin_a)
        usernames = {u["username"] for u in c.get("/api/users/users/").json()}
        self.assertNotIn("utb_user", usernames)
        r = c.post("/api/users/users/", {"username": "nuevo_uta", "password": "x9!k2#pQ7",
                                         "role": "CUSTOMER"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(User.objects.get(username="nuevo_uta").organization_id, a.id)
```

(URLs/campos del create según el router y `UserCreateSerializer` reales — el implementer los verifica y ajusta el payload mínimo válido.)

- [ ] **Step 2: RED**, **Step 3: Implementación**

`notifications/services.py`: `_admins(org)` / `_agents(org)` delegan en `tenancy.scoping.org_admins/org_agents`; en `_recipients_for`, todos los usos pasan `ticket.organization` (p.ej. `for admin in _admins(ticket.organization)`; ídem el bloque SLA).

`metrics/services.py`: `windowed_tickets(window, org)` — el queryset parte de `tenancy.scoping.org_tickets(org)` y aplica el cutoff (org None → vacío, ya garantizado por el helper). `metrics/views.py`: ambos endpoints pasan `request.organization`; en `me/`, `team = windowed_tickets(window, request.organization)` (el "equipo" ES la org).

`users/views.py`: `get_queryset` → `org_users(self.request.organization)`; `perform_create` fuerza `serializer.save(organization=self.request.organization)`.

- [ ] **Step 4: GREEN** — `python manage.py test notifications metrics users -v 1 --keepdb` → PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/notifications/ backend/metrics/ backend/users/
git commit -m "feat(tenancy): notifications, metrics y gestion de usuarios scoped por organizacion"
```

---

### Task 7: Suite adversarial + guard CI + `Ticket.organization` NOT NULL

**Files:**
- Create: `backend/tenancy/tests_isolation.py`
- Modify: `backend/tenancy/tests.py` (guard CI), migración `tickets_t` (AlterField NOT NULL)

**Interfaces:**
- Consumes: todo lo anterior. Produces: la matriz adversarial completa; guard anti-queryset-crudo.

- [ ] **Step 1: Guard CI** (append a `tenancy/tests.py`)

```python
import pathlib


class RawQuerysetGuardTests(TestCase):
    ALLOWED = {
        "tenancy/scoping.py",            # fuente unica
        "tickets_t/serializers.py",      # contador de referencia por prefijo (org-scoped por slug)
    }

    def test_sin_ticket_objects_crudo_fuera_del_allowlist(self):
        backend = pathlib.Path(__file__).resolve().parent.parent
        offenders = []
        for path in backend.rglob("*.py"):
            rel = path.relative_to(backend).as_posix()
            if ("migrations" in rel or rel.startswith("tenancy/tests")
                    or rel.endswith(("tests.py", "tests_isolation.py"))
                    or rel in self.ALLOWED):
                continue
            if "Ticket.objects" in path.read_text(encoding="utf-8", errors="ignore"):
                offenders.append(rel)
        self.assertEqual(offenders, [],
                         f"Queryset crudo de Ticket fuera de tenancy/scoping.py: {offenders}")
```

**Nota:** si al correrlo aparecen offenders legítimos no refactorizados (p.ej. `sla/checker.py` o `tickets_t/consumers.py`), la regla es: refactorizarlos para recibir el queryset/ticket ya scoped o justificar UNA POR UNA en `ALLOWED` con comentario. El objetivo es que el allowlist sea mínimo y justificado, no que el test pase.

- [ ] **Step 2: Suite adversarial** — `backend/tenancy/tests_isolation.py` con la matriz del spec. Estructura:

```python
"""Suite adversarial de aislamiento cross-tenant.

Fixture: dos organizaciones completas (admin+agent+customer+ticket con
SLA/CSAT cada una). Cada test ataca recursos de B autenticado como A.
Regla: cross-tenant con ID directo -> 404 (nunca 200 ni 403 que revele existencia).
"""
```

Tests mínimos (cada uno con asserts exactos; usar los patrones de fixture de las suites existentes para mensajes/adjuntos/CSAT):
1. `test_detalle_ticket_cross_404` (admin, agent y customer de A → ticket de B)
2. `test_lista_tickets_no_incluye_otra_org` (por los 3 roles)
3. `test_mensajes_y_eventos_cross_404`
4. `test_download_adjunto_cross_404`
5. `test_upload_adjunto_cross_404`
6. `test_csat_cross_404` (customer de A → POST csat a ticket de B)
7. `test_pool_take_cross` (pool de agent A no lista B; take sobre ticket de B → 404)
8. `test_metricas_no_mezclan` (admin A: totals exactos sólo de A)
9. `test_usuarios_cross` (admin A no lista ni puede editar usuarios de B → 404)
10. `test_sla_config_cross` (admin A edita SU config; la de B queda intacta — y no existe endpoint para tocar la de B)
11. `test_ws_chat_cross_rechazado` (WebsocketCommunicator: user de A a `ws/chat/<ticket_B>/` → conexión cerrada; usar el patrón de los tests de Channels existentes en `tickets_t/tests.py`, `TransactionTestCase`)

- [ ] **Step 3: NOT NULL** — migración `tickets_t`: `AlterField` `organization` a `null=False` (la semilla de T2 pobló todo; el código de creación la setea desde T5).

- [ ] **Step 4: GREEN** — `python manage.py test tenancy tickets_t -v 1 --keepdb` → PASS (guard + adversarial + regresión).

- [ ] **Step 5: Commit**

```bash
git add backend/tenancy/ backend/tickets_t/migrations/
git commit -m "test(tenancy): suite adversarial cross-tenant + guard CI + Ticket.organization NOT NULL"
```

---

### Task 8: Frontend (org en TopBar) + verificación

**Files:**
- Modify: `frontend/src/components/AppTopBar.vue`

**Interfaces:**
- Consumes: `/api/me/` con `organization` (T2).

- [ ] **Step 1:** En `AppTopBar.vue`, junto al username/rol ya mostrados, agregar el nombre de la org:

```html
      <span v-if="auth.user?.organization" class="tb-org">{{ auth.user.organization }}</span>
```

con estilo scoped acorde (`font-family: var(--font-mono); font-size: 11px; color: var(--text-3);` — mismo look que el chip de rol; el implementer ubica el anchor exacto leyendo el template actual).

- [ ] **Step 2: Build** — `cd frontend && npm run build` → limpio.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/AppTopBar.vue
git commit -m "feat(frontend): nombre de la organizacion en el TopBar"
```

---

## Self-Review (autor del plan)

- **Cobertura del spec:** Organization+middleware+scoping (T1), FKs+semilla+me (T2), fixtures+enforcement (T3), SLA per-org+provisioning+scheduler (T4), tickets scoped+referencia slug+asignación same-org (T5), notifications/metrics/users (T6), adversarial+guard+NOT NULL (T7), TopBar (T8). Cross-tenant 404, superuser-sin-org bloqueado, org suspendida 403: T1/T5/T7. ✅
- **Verde por task:** el middleware se registra recién en T3 junto con las fixtures; el FK de Ticket es nullable hasta T7; el bloque SLA de `testing.py` se activa en T4. Ningún task deja la suite rota. ✅
- **Consistencia de firmas:** `get_calendar(org)` cambia en T4 y TODOS sus callers se actualizan en la misma task (signals, checker, tickets_t context, metrics views, admin_views). `windowed_tickets(window, org)` cambia en T6 junto con sus 2 callers y sus tests. ✅
- **Deuda consciente:** los tests nuevos usan URLs "según el router real" en 3 lugares — el implementer las verifica antes del RED (instrucción explícita). El guard CI puede revelar offenders no anticipados — la regla de triage está escrita en el propio step. ✅
- **Riesgo mayor:** T3 (churn de fixtures en 6 suites) y T4 (romper el singleton). Ambos validan con suite completa/amplia antes de commitear. ✅
