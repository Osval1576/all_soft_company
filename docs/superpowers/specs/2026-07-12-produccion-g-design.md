# Endurecimiento de producción · G — Env, Redis, Docker, seguridad HTTP

**Fecha:** 2026-07-12
**Sub-proyecto:** G (endurecimiento producción)
**Estado:** Diseño aprobado, pendiente de plan de implementación

## Objetivo

Dejar AllSafe deployable en producción multi-proceso: settings 100% por variables de entorno
con defaults de dev intactos, Redis para Channels+cache, scheduler SLA fuera del proceso web,
seguridad HTTP (HTTPS/HSTS/cookies secure/nosniff), y la infraestructura concreta elegida:
**Docker Compose en un VPS con Nginx sirviendo el frontend same-origin**.

**Principio rector:** dev sigue funcionando exactamente como hoy sin instalar nada (sin Redis,
sin Docker, sin .env). Producción se configura por env y **falla ruidosamente al arrancar** si
falta algo crítico.

## Decisiones tomadas en el brainstorm

1. **Deploy target:** Docker Compose en VPS (web ASGI + scheduler + MySQL + Redis + Nginx).
2. **Frontend same-origin:** Nginx sirve el build de Vue y proxea `/api` y `/ws` bajo el mismo
   dominio → desaparece el cross-origin en prod (cookies `SameSite=Lax` nativas; CORS queda
   sólo para dev).
3. **G absorbe** los dos diferidos: estandarizar el front en `role` de `/api/me/` (con
   data-migration de backfill anti-lockout) y `TIME_ZONE` → `America/Mexico_City` por env.

## Contexto técnico relevante (estado actual, verificado)

- `config/settings.py`: SECRET_KEY placeholder hardcodeado, `DEBUG=True`, `ALLOWED_HOSTS`
  localhost, DB `root/root` hardcodeada, `InMemoryChannelLayer`, `LocMemCache`,
  CORS/CSRF_TRUSTED_ORIGINS con 6 origins localhost hardcodeados, `TIME_ZONE="UTC"`,
  email ya es env-driven (patrón `os.environ.get` a imitar).
- `config/auth_views.py`: `cookie_settings()` hardcodea `secure: False, samesite: "Lax"`.
- `config/asgi.py`: `ProtocolTypeRouter` + `JwtCookieAuthMiddleware` listos; **`daphne` ya está
  en requirements.txt** → server ASGI de prod sin dependencias nuevas.
- `sla/apps.py.ready()`: arranca el scheduler thread in-process con guard `RUN_MAIN` (sólo
  válido mono-proceso). Existe `management command check_sla` (una pasada) y `run_sla_check()`
  es idempotente.
- `tickets_t/validators.py`: **el content-sniffing de upload YA existe** (PIL `verify()` para
  imágenes, magic bytes `%PDF-` para PDF, límites 2MB/10MB). G NO lo re-implementa.
- Descarga de adjuntos: vía Django autenticado (`can_access_ticket`) — se mantiene; falta
  asegurar el header `X-Content-Type-Options: nosniff` en las respuestas.
- `/api/me/` ya expone `role` (barrido). El router de Vue (`router/index.js` beforeEach) y
  `auth.store.redirectByRole()` gatean por `is_staff`/`is_superuser`.
- `metrics.trend()` ya usa `timezone.localdate()` (preparado para TZ no-UTC).
- Deps actuales relevantes: Django 6.0.3, channels 4.3.2, daphne 4.2.2, mysqlclient, pillow.

## Diseño

### 1. Settings por env (`config/settings.py`)

Sin dependencias nuevas (patrón `os.environ.get`, como email). Variables:

| Variable | Default (dev) | Prod |
|---|---|---|
| `DJANGO_SECRET_KEY` | el placeholder actual | requerida |
| `DJANGO_DEBUG` | `"true"` | `"false"` |
| `DJANGO_ALLOWED_HOSTS` | `"127.0.0.1,localhost"` | dominio(s), CSV |
| `DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT` | valores actuales | del compose |
| `REDIS_URL` | vacío (→ LocMem/InMemory) | `redis://redis:6379/0` |
| `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` | los 6 localhost actuales, CSV | según necesidad (same-origin ⇒ casi vacío) |
| `TIME_ZONE` | `America/Mexico_City` | ídem |
| `SLA_SCHEDULER_MODE` | `"thread"` | `"off"` en web; el servicio scheduler usa el command |
| `COOKIE_SECURE` | derivado: `not DEBUG` | `true` implícito |

**Guard de arranque:** si `DJANGO_DEBUG=false` y `DJANGO_SECRET_KEY` es el placeholder o vacío
→ `ImproperlyConfigured` (falla el boot). Ídem si `DEBUG=false` y `ALLOWED_HOSTS` vacío.

**TIME_ZONE default pasa a `America/Mexico_City`** (alineado con el calendario SLA). Se audita
el backend por usos de `timezone.now().date()`/`.date()` que asuman UTC (fuera de `trend()` que
ya está corregido) y se corrigen con `timezone.localdate()` donde aplique.

### 2. Redis condicional

Dependencias nuevas: `channels-redis`, `django-redis` (sólo activas con `REDIS_URL`):

```python
if REDIS_URL:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels_redis.core.RedisChannelLayer",
                                   "CONFIG": {"hosts": [REDIS_URL]}}}
    CACHES = {"default": {"BACKEND": "django_redis.cache.RedisCache", "LOCATION": REDIS_URL, ...}}
else:
    # InMemory/LocMem actuales (dev sin Redis)
```

Presence de notificaciones y cualquier cache existente funcionan sin cambios (usan la API de
cache de Django).

### 3. Scheduler SLA multi-proceso

- `sla/apps.py.ready()`: arranca el thread **sólo si** `SLA_SCHEDULER_MODE == "thread"`
  (además del guard `RUN_MAIN` actual). Default dev = `thread` (comportamiento idéntico a hoy).
- `check_sla` gana flag `--loop`: corre `run_sla_check()` en bucle durmiendo
  `SlaConfig.scheduler_interval_minutes` entre pasadas (re-lee el intervalo en cada vuelta),
  maneja `KeyboardInterrupt`/SIGTERM limpio. Sin flag → una pasada (comportamiento actual).
- En compose: servicio `scheduler` (single-replica) corriendo `manage.py check_sla --loop`;
  los workers `web` llevan `SLA_SCHEDULER_MODE=off`. `run_sla_check()` es idempotente
  (rank-based), así que un doble-run accidental no re-notifica.

### 4. Seguridad HTTP (activa cuando `DEBUG=false`)

- `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` (Nginx termina TLS).
- `SECURE_SSL_REDIRECT=true` (env-overridable), HSTS gradual: `SECURE_HSTS_SECONDS` por env
  (default prod 3600; subir a 31536000 cuando el dominio esté estable; sin preload por default).
- `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` = `not DEBUG`.
- `config/auth_views.cookie_settings()`: `secure` pasa a derivarse del setting (no hardcodeado);
  `samesite` queda `"Lax"` (same-origin lo permite).
- `SECURE_CONTENT_TYPE_NOSNIFF` (default Django True — se verifica que el header llegue en la
  descarga de adjuntos y se agrega test que lo asserte, más `Content-Disposition` correcto).
- `SECURE_REFERRER_POLICY = "same-origin"`.

### 5. Docker Compose + Nginx (raíz del repo: `docker/` + `docker-compose.yml`)

- **`backend/Dockerfile`**: python slim, instala requirements, `collectstatic`, corre
  `daphne config.asgi:application` (HTTP+WS en un solo server, ya es dependencia).
- **`frontend/Dockerfile`** (multi-stage): node build (`npm ci && npm run build`) → los
  estáticos van a la imagen de Nginx.
- **`docker-compose.yml`**: servicios `web` (daphne, env-driven, healthcheck a `/api/health/`),
  `scheduler` (`check_sla --loop`), `mysql` (volumen persistente, healthcheck), `redis`
  (`redis:7-alpine`), `nginx` (puertos 80/443, certs montados de `./certs`, sirve el build de
  Vue, proxea `/api` y `/django-admin` a `web:8000`, `/ws` con headers Upgrade,
  `client_max_body_size 12m` por los PDFs de 10MB; `/media` NO se sirve directo — la descarga
  sigue autenticada vía Django).
- **`.env.example`** en la raíz documentando todas las variables (sin valores reales).
- **`/api/health/`**: endpoint GET sin auth que devuelve `{"ok": true}` + un `SELECT 1` a la DB
  — para healthchecks de compose y monitoreo básico.
- **Migraciones en deploy:** el servicio `web` corre `manage.py migrate --noinput` antes de
  daphne (entrypoint script). MySQL espera con healthcheck+depends_on condition.
- **Estáticos de Django admin:** `collectstatic` + whitenoise NO — los sirve Nginx desde un
  volumen compartido `static_volume` (evita dependencia nueva).
- **TLS:** certs montados (`./certs/fullchain.pem`, `privkey.pem`) + documentación de cómo
  generarlos con certbot standalone o `mkcert` para staging. Renovación fuera de alcance
  (doc apunta a certbot renew + reload).

### 6. Rol en el frontend (diferido absorbido)

- `auth.store.js`: `redirectByRole()` pasa a decidir por `user.role`
  (`ADMIN→admin`, `AGENT→tecnico-inbox`, resto→cliente).
- `router/index.js` beforeEach: `required === "ADMIN"` → `user.role === "ADMIN"`; ídem AGENT y
  CUSTOMER. Sin cambios de rutas ni de meta.
- **Data-migration en `users`** (anti-lockout, corre antes del switch): usuarios con
  `is_superuser=True` y `role != "ADMIN"` → `role = "ADMIN"`; usuarios con `is_staff=True`,
  no superuser y `role == "CUSTOMER"` → `role = "AGENT"`. Idempotente, con reverse no-op.
- El backend no cambia (ya gatea por role; `/api/me/` ya expone role).

### 7. Testing

- Guard de arranque: test que simula `DEBUG=false` + placeholder → `ImproperlyConfigured`
  (vía `override_settings`/reimport o llamando la función de validación extraída).
- `check_sla --loop`: el loop se factoriza para poder testear una iteración (`--max-iterations 1`
  interno o inyección); test de que respeta el intervalo de `SlaConfig`.
- Migración de backfill de roles: test con usuarios legacy (superuser role CUSTOMER, staff role
  CUSTOMER) → quedan ADMIN/AGENT; usuarios correctos no se tocan.
- `/api/health/`: 200 sin auth, `{"ok": true}`.
- Header `X-Content-Type-Options: nosniff` presente en la descarga de adjuntos (test).
- Frontend: build limpio + verificación en navegador del login/redirect por rol (usuarios demo
  ya tienen role correcto).
- Gate de merge: suite completa backend en DB fresca, como siempre.
- **Verificación de deploy** (manual, documentada): `docker compose up` en local →
  health check verde, login por Nginx, WS de chat conecta, upload/download de adjunto, y las
  notificaciones/presence funcionan con 2+ workers web (prueba real de Redis).

## Manejo de errores y bordes

- Boot de prod sin SECRET_KEY/ALLOWED_HOSTS → falla explícita con mensaje claro.
- `REDIS_URL` seteado pero Redis caído → Channels/cache fallan ruidosamente (no fallback
  silencioso a LocMem, que ocultaría un outage).
- Scheduler `--loop`: si una pasada lanza excepción, se loguea y el loop continúa (no muere el
  servicio por un error transitorio de DB).
- Usuarios legacy sin role correcto: cubiertos por la data-migration ANTES de que el front
  cambie a role.

## Fuera de alcance (post-G)

- CI/CD, backups automatizados de MySQL, monitoring/Sentry, rate-limiting global, certbot
  automatizado dentro del compose, multi-tenant (H).

Ver [[allsafe-project-state]] y [[allsafe-conventions]].
