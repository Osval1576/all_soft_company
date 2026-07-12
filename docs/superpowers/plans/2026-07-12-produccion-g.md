# G · Endurecimiento Producción — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AllSafe deployable en producción multi-proceso: settings 100% env con guard de arranque, Redis condicional, scheduler SLA fuera del proceso web, seguridad HTTP, rol en el front, y Docker Compose + Nginx same-origin.

**Architecture:** Settings env-driven con defaults de dev intactos (sin `.env` obligatorio en dev). `REDIS_URL` activa channels-redis/django-redis; vacío → InMemory/LocMem actuales. Scheduler como servicio compose dedicado (`check_sla --loop`). Nginx sirve el build de Vue y proxea `/api`+`/ws`+`/django-admin` → daphne (ya dependencia).

**Tech Stack:** Django 6.0.3 + Channels 4.3.2 + daphne 4.2.2 (existentes); nuevos: channels-redis, django-redis. Docker Compose (mysql:8.4, redis:7-alpine, nginx:1.27-alpine, node:22 para build).

## Global Constraints

- **Dev intacto:** sin `REDIS_URL` ni env vars, todo funciona EXACTAMENTE como hoy (mismos defaults). `DJANGO_DEBUG` default `true`.
- **Guard de arranque:** con `DEBUG=false`, SECRET_KEY placeholder/vacía o `ALLOWED_HOSTS` vacío → system check `Error` (ids `config.E001`/`config.E002`) que bloquea `migrate`/`check`/`runserver`. El entrypoint de Docker corre `migrate` primero, así que es el punto de enforcement en prod (daphne solo no corre checks).
- **Redis explícito, sin fallback silencioso:** `REDIS_URL` seteado + Redis caído = error ruidoso, nunca degradar a LocMem.
- **Scheduler:** thread in-process sólo si `SLA_SCHEDULER_MODE=="thread"` (default) Y `RUN_MAIN=="true"`. `check_sla --loop` re-lee el intervalo de `SlaConfig` en cada pasada; una excepción por pasada se loguea y el loop sigue.
- **Cookies JWT:** `secure` derivado de `settings.AUTH_COOKIE_SECURE` (= `not DEBUG`, overridable con env `COOKIE_SECURE`); `samesite` queda `"Lax"` (same-origin).
- **Contrib admin se muda a `/django-admin/`** (la SPA usa `/admin` — chocan same-origin).
- **Rol estricto en el front:** router y redirects por `user.role` de `/api/me/` (ADMIN/AGENT/CUSTOMER). Esto es un cambio deliberado: un ADMIN ya NO entra a rutas AGENT (consistente con el backend, donde `IsAgent` ya le devuelve 403 en `/api/metrics/me/`). Data-migration de backfill ANTES del switch.
- **TIME_ZONE:** `_env("TIME_ZONE", "America/Mexico_City")`. Auditoría ya hecha en diseño: cero usos de `timezone.now().date()`/`__date=` en backend fuera de tests/migrations — no hay código que corregir.
- **Sin Docker en esta máquina de dev** (`docker --version` no existe): los archivos de infra se entregan + se validan por revisión; `docker compose up` real queda documentado en el runbook para el VPS.
- **Tests seed-safe** (SlaConfig/SlaPolicy en setUp) y gate de merge en DB fresca, como siempre.

## File Structure

**Backend:** modificar `config/settings.py`, `config/auth_views.py`, `config/views.py`, `config/urls.py`, `sla/apps.py`, `sla/management/commands/check_sla.py`, `users/apps.py`, `users/tests.py`, `sla/tests.py`, `tickets_t/tests.py`, `backend/requirements.txt`; crear `config/checks.py`, `users/migrations/0002_backfill_roles.py`, `backend/Dockerfile`, `backend/entrypoint.sh`.
**Frontend:** modificar `src/stores/auth.store.js`, `src/router/index.js`, `src/api/http.js`, `frontend/.env.example`; crear `frontend/Dockerfile`, `frontend/nginx.conf`.
**Raíz:** crear `docker-compose.yml`, `.env.example`, `docs/deploy.md`.

---

### Task 1: Settings env-driven + guard de arranque + TIME_ZONE

**Files:**
- Modify: `backend/config/settings.py`, `backend/users/apps.py`
- Create: `backend/config/checks.py`
- Test: `backend/users/tests.py` (append)

**Interfaces:**
- Produces: helpers `_env`/`_env_bool`/`_env_csv` en settings; settings `DEV_SECRET_KEY_PLACEHOLDER`, `STATIC_ROOT`; check `config.checks.prod_settings_check` (ids E001/E002). Tasks 2 y 4 agregan bloques que usan estos helpers.

- [ ] **Step 1: Escribir el test que falla**

Append a `backend/users/tests.py` (si el archivo no existe o está vacío, crearlo con los imports):

```python
from django.test import TestCase, override_settings

from config.checks import prod_settings_check


class ProdSettingsCheckTests(TestCase):
    @override_settings(DEBUG=False, SECRET_KEY="CHANGE_ME__PUT_YOUR_OWN_SECRET_KEY_HERE")
    def test_prod_con_placeholder_falla(self):
        errors = prod_settings_check(None)
        self.assertTrue(any(e.id == "config.E001" for e in errors))

    @override_settings(DEBUG=False, SECRET_KEY="k" * 50, ALLOWED_HOSTS=[])
    def test_prod_sin_hosts_falla(self):
        errors = prod_settings_check(None)
        self.assertTrue(any(e.id == "config.E002" for e in errors))

    @override_settings(DEBUG=True)
    def test_dev_pasa_sin_errores(self):
        self.assertEqual(prod_settings_check(None), [])
```

- [ ] **Step 2: Correr — debe fallar**

Run: `cd backend && python manage.py test users.tests.ProdSettingsCheckTests -v 2 --keepdb`
Expected: ERROR (`config.checks` no existe).

- [ ] **Step 3: Crear `config/checks.py`**

```python
from django.conf import settings
from django.core.checks import Error, register


@register()
def prod_settings_check(app_configs, **kwargs):
    """Con DEBUG=false, exige configuración de producción real."""
    errors = []
    if settings.DEBUG:
        return errors
    placeholder = getattr(settings, "DEV_SECRET_KEY_PLACEHOLDER", "")
    if not settings.SECRET_KEY or settings.SECRET_KEY == placeholder:
        errors.append(Error(
            "DJANGO_SECRET_KEY es obligatoria (y distinta del placeholder) con DJANGO_DEBUG=false.",
            id="config.E001",
        ))
    if not settings.ALLOWED_HOSTS:
        errors.append(Error(
            "DJANGO_ALLOWED_HOSTS es obligatoria con DJANGO_DEBUG=false.",
            id="config.E002",
        ))
    return errors
```

- [ ] **Step 4: Registrar el check vía `users/apps.py`**

Reemplazar `backend/users/apps.py` completo por:

```python
from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'

    def ready(self):
        from config import checks  # noqa: F401  registra los system checks de prod
```

- [ ] **Step 5: Envificar `config/settings.py`**

(a) Reemplazar el bloque de imports/SECRET_KEY/DEBUG/ALLOWED_HOSTS (líneas 7-19 actuales) por:

```python
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(name, default=""):
    return os.environ.get(name, default)


def _env_bool(name, default):
    return _env(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _env_csv(name, default):
    return [x.strip() for x in _env(name, default).split(",") if x.strip()]


# Placeholder de dev: el system check config.E001 impide arrancar prod con este valor.
DEV_SECRET_KEY_PLACEHOLDER = "CHANGE_ME__PUT_YOUR_OWN_SECRET_KEY_HERE"
SECRET_KEY = _env("DJANGO_SECRET_KEY", DEV_SECRET_KEY_PLACEHOLDER)

DEBUG = _env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = _env_csv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
```

(b) El `import os` que estaba a mitad de archivo (sección email) se elimina (ya está arriba).

(c) `DATABASES` pasa a:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": _env("DB_NAME", "allsafe"),
        "USER": _env("DB_USER", "root"),
        "PASSWORD": _env("DB_PASSWORD", "root"),
        "HOST": _env("DB_HOST", "127.0.0.1"),
        "PORT": _env("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}
```

(d) `TIME_ZONE = "UTC"` pasa a `TIME_ZONE = _env("TIME_ZONE", "America/Mexico_City")` (se elimina el comentario de "en producción normalmente...").

(e) Tras `STATIC_URL = "static/"` agregar:

```python
STATIC_ROOT = _env("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles"))
```

(f) `CORS_ALLOWED_ORIGINS` y `CSRF_TRUSTED_ORIGINS` pasan a env con los defaults actuales:

```python
_DEV_ORIGINS = ",".join(
    f"http://{h}:{p}" for h in ("localhost", "127.0.0.1") for p in (5173, 5174, 5175)
)
CORS_ALLOWED_ORIGINS = _env_csv("CORS_ALLOWED_ORIGINS", _DEV_ORIGINS)
```
y (en su sección actual):
```python
CSRF_TRUSTED_ORIGINS = _env_csv("CSRF_TRUSTED_ORIGINS", _DEV_ORIGINS)
```

- [ ] **Step 6: Correr — debe pasar (y la suite de sanity)**

Run: `cd backend && python manage.py test users -v 2 --keepdb`
Expected: PASS (3 nuevos + los existentes de users).
Run: `python manage.py check`
Expected: `System check identified no issues` (dev: DEBUG=true → el check no aplica).

- [ ] **Step 7: Commit**

```bash
git add backend/config/settings.py backend/config/checks.py backend/users/apps.py backend/users/tests.py
git commit -m "feat(config): settings env-driven + guard de arranque prod + TZ Mexico_City"
```

---

### Task 2: Redis condicional (channels + cache)

**Files:**
- Modify: `backend/config/settings.py`, `backend/requirements.txt`

**Interfaces:**
- Consumes: `_env` de Task 1.
- Produces: setting `REDIS_URL`; `CHANNEL_LAYERS`/`CACHES` condicionales.

- [ ] **Step 1: Instalar dependencias**

Run: `pip install channels-redis django-redis`
Expected: instala OK. Anotar las versiones exactas resueltas (`pip show channels-redis django-redis | grep -E "Name|Version"`).

- [ ] **Step 2: Pinnear en `backend/requirements.txt`**

Agregar (con las versiones que resolvió pip en Step 1; si difieren de estas, usar las reales):

```
channels-redis==4.3.0
django-redis==6.0.0
```

- [ ] **Step 3: Bloques condicionales en settings**

Reemplazar los bloques actuales de `CHANNEL_LAYERS` y `CACHES` por:

```python
# Redis (G): con REDIS_URL seteado, channels + cache van a Redis (multi-proceso).
# Sin REDIS_URL (dev), quedan los backends in-process de siempre.
REDIS_URL = _env("REDIS_URL")

if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
```

y (donde hoy está `CACHES`):

```python
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "allsafe-default",
        }
    }
```

(Nota: `CACHES` aparece hoy ANTES de `SIMPLE_JWT`; mantener la posición. `CHANNEL_LAYERS` mantiene la suya.)

- [ ] **Step 4: Verificar que dev no cambió**

Run: `cd backend && python manage.py check && python manage.py test notifications --keepdb -v 1`
Expected: check limpio; suite de notifications (usa cache/presence y channel layer in-memory) PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/config/settings.py backend/requirements.txt
git commit -m "feat(config): Redis condicional para channels y cache via REDIS_URL"
```

---

### Task 3: Scheduler multi-proceso — `SLA_SCHEDULER_MODE` + `check_sla --loop`

**Files:**
- Modify: `backend/sla/apps.py`, `backend/sla/management/commands/check_sla.py`
- Test: `backend/sla/tests.py` (append)

**Interfaces:**
- Consumes: `run_sla_check()` (idempotente), `SlaConfig.get_solo()`.
- Produces: env `SLA_SCHEDULER_MODE` ("thread" default | "off"); flags `--loop` y `--max-loops` en `check_sla`.

- [ ] **Step 1: Escribir el test que falla**

Append a `backend/sla/tests.py`:

```python
from io import StringIO
from unittest import mock

from django.core.management import call_command


class CheckSlaLoopTests(TestCase):
    def setUp(self):
        cfg = SlaConfig.objects.get_solo()
        cfg.scheduler_interval_minutes = 1
        cfg.scheduler_enabled = True
        cfg.save()

    @mock.patch("sla.management.commands.check_sla.time.sleep")
    def test_loop_corre_max_loops_pasadas_y_duerme_el_intervalo(self, sleep_mock):
        out = StringIO()
        call_command("check_sla", "--loop", "--max-loops=2", stdout=out)
        self.assertEqual(out.getvalue().count("SLA check:"), 2)
        sleep_mock.assert_called_once_with(60)  # 1 min entre pasada 1 y 2; tras la última no duerme

    def test_sin_loop_una_pasada(self):
        out = StringIO()
        call_command("check_sla", stdout=out)
        self.assertEqual(out.getvalue().count("SLA check:"), 1)
```

(`TestCase` y `SlaConfig` ya están importados en `sla/tests.py`.)

- [ ] **Step 2: Correr — debe fallar**

Run: `cd backend && python manage.py test sla.tests.CheckSlaLoopTests -v 2 --keepdb`
Expected: FAIL (`--loop` no reconocido).

- [ ] **Step 3: Reescribir el command**

Reemplazar `backend/sla/management/commands/check_sla.py` completo por:

```python
import logging
import time

from django.core.management.base import BaseCommand

from sla.checker import run_sla_check

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Chequea SLAs de tickets abiertos y notifica cruces de nivel. Con --loop corre como servicio."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true",
                            help="Correr en bucle usando el intervalo de SlaConfig (servicio scheduler).")
        parser.add_argument("--max-loops", type=int, default=0,
                            help="Con --loop: cortar tras N pasadas (0 = infinito; pensado para tests).")

    def handle(self, *args, **options):
        if not options["loop"]:
            self._one_pass()
            return

        from sla.models import SlaConfig
        loops = 0
        while True:
            interval_min = 10
            try:
                cfg = SlaConfig.objects.get_solo()
                interval_min = max(1, cfg.scheduler_interval_minutes)
                if cfg.scheduler_enabled:
                    self._one_pass()
                else:
                    self.stdout.write("scheduler_enabled=False; pasada omitida.")
            except KeyboardInterrupt:
                break
            except Exception:
                logger.exception("error en pasada de check_sla --loop")
            loops += 1
            if options["max_loops"] and loops >= options["max_loops"]:
                break
            try:
                time.sleep(interval_min * 60)
            except KeyboardInterrupt:
                break

    def _one_pass(self):
        result = run_sla_check()
        self.stdout.write(self.style.SUCCESS(
            f"SLA check: {result['checked']} revisados, {result['notified']} notificaciones."
        ))
```

- [ ] **Step 4: Gate del thread in-process en `sla/apps.py`**

En `ready()`, reemplazar la condición actual por:

```python
        # Thread in-process sólo en dev (runserver): en prod el scheduler es un
        # servicio dedicado (manage.py check_sla --loop) y aquí va MODE=off.
        mode = os.environ.get("SLA_SCHEDULER_MODE", "thread")
        if mode == "thread" and os.environ.get("RUN_MAIN") == "true":
```

(el cuerpo del `if` — try/import/start — queda igual).

- [ ] **Step 5: Correr — debe pasar**

Run: `cd backend && python manage.py test sla -v 1 --keepdb`
Expected: PASS (suite sla completa, incl. los 2 nuevos).

- [ ] **Step 6: Commit**

```bash
git add backend/sla/apps.py backend/sla/management/commands/check_sla.py backend/sla/tests.py
git commit -m "feat(sla): check_sla --loop + gate SLA_SCHEDULER_MODE para multi-proceso"
```

---

### Task 4: Seguridad HTTP + cookies env + `/api/health/` + admin a `/django-admin/`

**Files:**
- Modify: `backend/config/settings.py`, `backend/config/auth_views.py`, `backend/config/views.py`, `backend/config/urls.py`
- Test: `backend/users/tests.py` (append), `backend/tickets_t/tests.py` (append)

**Interfaces:**
- Consumes: `_env`/`_env_bool`, `DEBUG` (Task 1).
- Produces: setting `AUTH_COOKIE_SECURE`; endpoint `GET /api/health/` (sin auth); contrib admin en `/django-admin/`.

- [ ] **Step 1: Escribir los tests que fallan**

Append a `backend/users/tests.py`:

```python
class HealthEndpointTests(TestCase):
    def test_health_sin_auth_devuelve_ok(self):
        resp = self.client.get("/api/health/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"ok": True})
```

Append a `backend/tickets_t/tests.py`, dentro de la clase existente de tests de adjuntos (la que ya sube un adjunto y lo descarga — seguir su patrón de creación de ticket+mensaje+archivo):

```python
    def test_download_lleva_nosniff(self):
        # reutilizar el helper/flujo de descarga ya existente en esta clase
        resp = self._download_ok_response()  # ver nota abajo
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
```

**Nota al implementer:** si la clase de adjuntos no tiene un helper reutilizable, replicá las 3-4 líneas del test de descarga exitosa existente (upload + GET al endpoint de download con el dueño autenticado) y assertá el header sobre esa respuesta; no inventes un flujo nuevo.

- [ ] **Step 2: Correr — deben fallar**

Run: `cd backend && python manage.py test users.tests.HealthEndpointTests tickets_t -v 1 --keepdb`
Expected: Health 404 (no existe); el de nosniff puede pasar ya (SecurityMiddleware lo agrega por default en Django moderno) — si pasa, perfecto: queda como test de regresión.

- [ ] **Step 3: Bloque de seguridad en settings**

Agregar al final de `config/settings.py`:

```python
# -----------------------
# Seguridad HTTP (prod)
# -----------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]  # healthcheck de compose entra por http directo
SECURE_HSTS_SECONDS = int(_env("SECURE_HSTS_SECONDS", "0" if DEBUG else "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_REFERRER_POLICY = "same-origin"

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
# Cookies JWT (config/auth_views.py)
AUTH_COOKIE_SECURE = _env_bool("COOKIE_SECURE", not DEBUG)
```

- [ ] **Step 4: `cookie_settings()` env-driven**

En `config/auth_views.py`, agregar `from django.conf import settings` a los imports y reemplazar `cookie_settings()` por:

```python
def cookie_settings():
    # secure=True en prod (DEBUG=false), False en dev http. SameSite Lax alcanza
    # porque en prod el front es same-origin detrás de Nginx.
    return {
        "httponly": True,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": "Lax",
        "path": "/",
    }
```

- [ ] **Step 5: Health endpoint + admin URL**

En `config/views.py` agregar (los imports de `api_view`/`permission_classes`/`Response` ya existen; sumar `AllowAny` y `connection`):

```python
from django.db import connection
from rest_framework.permissions import AllowAny


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    with connection.cursor() as cur:
        cur.execute("SELECT 1")
    return Response({"ok": True})
```

En `config/urls.py`: importar `health` junto a `me`, cambiar `path("admin/", admin.site.urls)` por `path("django-admin/", admin.site.urls)`, y agregar `path("api/health/", health, name="health")` junto a `api/me/`.

- [ ] **Step 6: Correr — deben pasar**

Run: `cd backend && python manage.py test users tickets_t -v 1 --keepdb`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/config/settings.py backend/config/auth_views.py backend/config/views.py backend/config/urls.py backend/users/tests.py backend/tickets_t/tests.py
git commit -m "feat(config): seguridad HTTP prod + health endpoint + admin en /django-admin/"
```

---

### Task 5: Rol en el frontend + data-migration de backfill

**Files:**
- Create: `backend/users/migrations/0002_backfill_roles.py`
- Modify: `frontend/src/stores/auth.store.js`, `frontend/src/router/index.js`
- Test: `backend/users/tests.py` (append)

**Interfaces:**
- Consumes: `/api/me/` ya expone `role` (barrido pre-G).
- Produces: front gatea por `role`; usuarios legacy backfilleados.

- [ ] **Step 1: Escribir el test que falla**

Append a `backend/users/tests.py` (sumar `from django.contrib.auth import get_user_model` e `import importlib` a los imports del archivo si no están):

```python
class BackfillRolesTests(TestCase):
    def test_backfill_corrige_legacy_y_no_toca_correctos(self):
        User = get_user_model()
        legacy_super = User.objects.create_user("gsuper", is_superuser=True, role="CUSTOMER")
        legacy_staff = User.objects.create_user("gstaff", is_staff=True, role="CUSTOMER")
        ok_admin = User.objects.create_user("gadmin", role="ADMIN")
        ok_customer = User.objects.create_user("gcust", role="CUSTOMER")

        from django.apps import apps as global_apps
        mod = importlib.import_module("users.migrations.0002_backfill_roles")
        mod.backfill_roles(global_apps, None)

        legacy_super.refresh_from_db(); legacy_staff.refresh_from_db()
        ok_admin.refresh_from_db(); ok_customer.refresh_from_db()
        self.assertEqual(legacy_super.role, "ADMIN")
        self.assertEqual(legacy_staff.role, "AGENT")
        self.assertEqual(ok_admin.role, "ADMIN")
        self.assertEqual(ok_customer.role, "CUSTOMER")
```

- [ ] **Step 2: Correr — debe fallar**

Run: `cd backend && python manage.py test users.tests.BackfillRolesTests -v 2 --keepdb`
Expected: ERROR (módulo de migración no existe).

- [ ] **Step 3: Crear la migración**

`backend/users/migrations/0002_backfill_roles.py`:

```python
from django.db import migrations


def backfill_roles(apps, schema_editor):
    """Anti-lockout para el switch del front a role: usuarios legacy creados via
    createsuperuser/flags quedaron con role=CUSTOMER (default)."""
    User = apps.get_model("users", "User")
    User.objects.filter(is_superuser=True).exclude(role="ADMIN").update(role="ADMIN")
    User.objects.filter(is_staff=True, is_superuser=False, role="CUSTOMER").update(role="AGENT")


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_roles, migrations.RunPython.noop),
    ]
```

- [ ] **Step 4: Correr test + migrar la DB de dev**

Run: `cd backend && python manage.py test users.tests.BackfillRolesTests -v 2 --keepdb`
Expected: PASS.
Run: `python manage.py migrate users`
Expected: `Applying users.0002_backfill_roles... OK`.

- [ ] **Step 5: Switch del front a `role`**

En `frontend/src/stores/auth.store.js`, reemplazar `redirectByRole()` por:

```javascript
redirectByRole() {
  if (this.user?.role === "ADMIN") return { name: "admin" };
  if (this.user?.role === "AGENT") return { name: "tecnico-inbox" };
  return { name: "cliente" };
},
```

En `frontend/src/router/index.js`, reemplazar las tres líneas de gating del `beforeEach` por:

```javascript
  const required = to.meta?.role;
  const role = auth.user?.role;
  if (required === "ADMIN" && role !== "ADMIN") return auth.redirectByRole();
  if (required === "AGENT" && role !== "AGENT") return auth.redirectByRole();
  if (required === "CUSTOMER" && role !== "CUSTOMER") return auth.redirectByRole();
```

(La línea `const required = to.meta?.role;` ya existe — no duplicarla.)

- [ ] **Step 6: Build + verificación en navegador**

Run: `cd frontend && npm run build` → limpio.
Manual (si hay servers corriendo): login `demo_admin` → cae en `/admin`; `demo_tech` → `/tecnico/inbox`; `demo_tech` intentando `/admin/metricas` → redirigido. (Los usuarios demo ya tienen role correcto.)

- [ ] **Step 7: Commit**

```bash
git add backend/users/migrations/0002_backfill_roles.py backend/users/tests.py frontend/src/stores/auth.store.js frontend/src/router/index.js
git commit -m "feat(auth): front gatea por role de /api/me/ + backfill anti-lockout"
```

---

### Task 6: Base de API del front por env (same-origin ready)

**Files:**
- Modify: `frontend/src/api/http.js`, `frontend/.env.example`

**Interfaces:**
- Produces: `VITE_API_BASE` (build-time). Task 7 la setea a `""` en el Dockerfile del front.

- [ ] **Step 1: `http.js`**

Reemplazar `frontend/src/api/http.js` completo por:

```javascript
import axios from "axios";

// Base de la API. En dev, el backend corre aparte en :8000.
// En el build de producción (same-origin detrás de Nginx) se define
// VITE_API_BASE="" y todas las llamadas quedan relativas al mismo dominio.
const base = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export const http = axios.create({
  baseURL: base,
  withCredentials: true,
});
```

(Nota: `??` y no `||` — el string vacío de prod es un valor válido.)

- [ ] **Step 2: Documentar en `.env.example` del front**

Append a `frontend/.env.example`:

```
# Base URL de la API. En dev, dejá sin definir (usa http://localhost:8000).
# En el build de producción same-origin se define vacía: VITE_API_BASE=
# VITE_API_BASE=
```

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: limpio. (Las URLs de WS ya usan `VITE_WS_HOST || window.location.host` — no cambian.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/http.js frontend/.env.example
git commit -m "feat(frontend): base de API por VITE_API_BASE (same-origin en prod)"
```

---

### Task 7: Docker Compose + Nginx + runbook

**Files:**
- Create: `backend/Dockerfile`, `backend/entrypoint.sh`, `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml` (raíz), `.env.example` (raíz), `docs/deploy.md`

**Interfaces:**
- Consumes: todo lo anterior (`REDIS_URL`, `SLA_SCHEDULER_MODE`, `check_sla --loop`, `/api/health/`, `/django-admin/`, `VITE_API_BASE`, `STATIC_ROOT`).

- [ ] **Step 1: `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# mysqlclient necesita headers de MySQL; curl para el healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential default-libmysqlclient-dev pkg-config curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/staticfiles /app/media

COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
```

- [ ] **Step 2: `backend/entrypoint.sh`**

```sh
#!/bin/sh
set -e

if [ "$RUN_MIGRATIONS" != "false" ]; then
  echo "Aplicando migraciones..."
  python manage.py migrate --noinput
fi

if [ "$COLLECT_STATIC" = "true" ]; then
  echo "Recolectando estaticos..."
  python manage.py collectstatic --noinput
fi

exec "$@"
```

- [ ] **Step 3: `frontend/Dockerfile`**

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Build same-origin: la API queda relativa al dominio; el WS usa window.location.host.
ENV VITE_API_BASE=""
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

- [ ] **Step 4: `frontend/nginx.conf`**

```nginx
# AllSafe same-origin: SPA + proxy /api /ws /django-admin -> daphne.
# TLS: este archivo escucha 80 (staging / detras de otro proxy). Para servir
# HTTPS directo en el VPS, ver docs/deploy.md (bloque 443 + redirect).
server {
    listen 80;
    server_name _;
    client_max_body_size 12m;

    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /django-admin/ {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Estaticos de Django (admin) desde el volumen compartido con web.
    location /static/ {
        alias /staticfiles/;
    }

    location /ws/ {
        proxy_pass http://web:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
    }

    # /media NO se sirve: la descarga de adjuntos es autenticada via Django.

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 5: `docker-compose.yml` (raíz)**

```yaml
services:
  mysql:
    image: mysql:8.4
    environment:
      MYSQL_DATABASE: ${DB_NAME:-allsafe}
      MYSQL_USER: ${DB_USER:-allsafe}
      MYSQL_PASSWORD: ${DB_PASSWORD:?definir en .env}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:?definir en .env}
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1", "-uroot", "-p$${MYSQL_ROOT_PASSWORD}"]
      interval: 10s
      timeout: 5s
      retries: 12

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 10

  web:
    build: ./backend
    env_file: .env
    environment:
      DB_HOST: mysql
      REDIS_URL: redis://redis:6379/0
      SLA_SCHEDULER_MODE: "off"
      COLLECT_STATIC: "true"
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/api/health/"]
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 40s

  scheduler:
    build: ./backend
    command: python manage.py check_sla --loop
    env_file: .env
    environment:
      DB_HOST: mysql
      REDIS_URL: redis://redis:6379/0
      RUN_MIGRATIONS: "false"
    depends_on:
      web:
        condition: service_healthy

  nginx:
    build: ./frontend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - static_volume:/staticfiles:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      web:
        condition: service_healthy

volumes:
  mysql_data:
  static_volume:
  media_volume:
```

- [ ] **Step 6: `.env.example` (raíz)**

```
# ==== Django ====
DJANGO_SECRET_KEY=            # obligatoria: generar con `python -c "import secrets; print(secrets.token_urlsafe(64))"`
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=allsafe.example.com
TIME_ZONE=America/Mexico_City

# HTTPS (con TLS en Nginx). En staging http-only poner SECURE_SSL_REDIRECT=false.
SECURE_SSL_REDIRECT=true
SECURE_HSTS_SECONDS=3600
CSRF_TRUSTED_ORIGINS=https://allsafe.example.com

# ==== Base de datos ====
DB_NAME=allsafe
DB_USER=allsafe
DB_PASSWORD=
DB_PORT=3306
MYSQL_ROOT_PASSWORD=

# ==== Email (opcional; sin EMAIL_HOST los mails van a consola) ====
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=AllSafe <no-reply@allsafe.example.com>
```

- [ ] **Step 7: `docs/deploy.md`** — runbook con EXACTAMENTE estas secciones (redactar cada una completa, sin TBD):
  1. **Requisitos del VPS** (docker + compose plugin, dominio apuntando, puertos 80/443).
  2. **Primer deploy**: clonar, `cp .env.example .env` + completar, `docker compose up -d --build`, `docker compose exec web python manage.py createsuperuser`.
  3. **TLS**: generar certs con certbot standalone (`certbot certonly --standalone -d dominio`), copiarlos a `./certs/`, y el bloque `server { listen 443 ssl; ... }` completo para pegar en `frontend/nginx.conf` (con `ssl_certificate /etc/nginx/certs/fullchain.pem;`, redirect 80→443, y rebuild de nginx). Renovación: `certbot renew` + `docker compose restart nginx` (cron mensual).
  4. **Smoke checklist post-deploy**: health verde (`docker compose ps`), login por el dominio, WS de chat conecta (badge "conectado"), upload+download de adjunto, notificaciones entre 2 sesiones (prueba real de Redis), `/django-admin/` accesible.
  5. **Escalar web**: `docker compose up -d --scale web=2` — requiere Redis (ya activo); scheduler SIEMPRE single-replica.
  6. **Troubleshooting**: boot falla con `config.E001/E002` → falta env; redirect loop en staging http → `SECURE_SSL_REDIRECT=false`.

- [ ] **Step 8: Verificación (sin Docker en esta máquina)**

- `python -c "import yaml"` — si PyYAML está disponible, validar sintaxis: `python -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"`; si no está instalado, skip (la validación real es `docker compose config` en el VPS, documentada en el runbook).
- Verificación estática cruzada (a mano, listarla en el reporte): nombres de servicio (`web`, `mysql`, `redis`) vs `DB_HOST`/`REDIS_URL`/`proxy_pass`; paths de volúmenes (`/app/staticfiles` ↔ `/staticfiles`); env vars del compose vs las que lee `settings.py`/`entrypoint.sh`.

- [ ] **Step 9: Commit**

```bash
git add backend/Dockerfile backend/entrypoint.sh frontend/Dockerfile frontend/nginx.conf docker-compose.yml .env.example docs/deploy.md
git commit -m "feat(infra): Docker Compose completo (web+scheduler+mysql+redis+nginx) + runbook"
```

---

## Self-Review (autor del plan)

- **Cobertura del spec:** settings env+guard (T1), Redis condicional (T2), scheduler multi-proceso (T3), seguridad HTTP+cookies+health+nosniff (T4), rol front+backfill (T5), same-origin API base (T6), compose+nginx+runbook (T7). Auditoría TZ: hecha en diseño (cero hallazgos), T1 sólo cambia el default. ✅
- **Consistencia:** `AUTH_COOKIE_SECURE` definido en T4 y consumido en T4; `STATIC_ROOT` (T1) ↔ `collectstatic` (T7); `check_sla --loop` (T3) ↔ compose `scheduler` (T7); `/api/health/` (T4) ↔ healthchecks (T7); `/django-admin/` (T4) ↔ nginx (T7); `VITE_API_BASE` (T6) ↔ Dockerfile front (T7); `SECURE_REDIRECT_EXEMPT` cubre el healthcheck directo a :8000. ✅
- **Sin placeholders:** todo el código/config completo; el runbook tiene contenido enumerado por sección con los comandos exactos. ✅
- **Riesgos anotados:** pins de channels-redis/django-redis pueden ajustarse a lo que resuelva pip (T2 lo instruye explícitamente); el test de nosniff puede nacer verde (T4 lo anticipa); rol estricto cambia el acceso de ADMIN a rutas AGENT (deliberado, documentado en Global Constraints).
