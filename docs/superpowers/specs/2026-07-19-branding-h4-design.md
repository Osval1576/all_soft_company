# H4 · Branding por tenant — Diseño

**Fecha:** 2026-07-19
**Estado:** Aprobado (diseño) → pendiente plan de implementación
**Sub-proyecto:** H4 (branding white-label por organización), última pieza del roadmap A–H.

## Contexto

AllSafe es un producto SaaS helpdesk white-label multi-tenant. Cada `Organization`
(schema-shared + FK `organization`) hoy comparte una identidad visual única: acento
azul eléctrico (`--accent #0038FF`), cuadrito "AS" + nombre "AllSafe" en el `TopBar`.

H4 permite que cada organización de **plan pago (Pro/Business)** personalice su
identidad visual: color de acento, logo, nombre visible y tema inicial. El branding
aparece en la app autenticada, en las páginas pre-auth accesibles por slug
(`/o/:slug/login`, invitación) y opcionalmente en emails (pieza final, ver Fuera de
alcance / opcional).

### Estado del código relevante

- **`tenancy/models.py`** · `Organization(name unique, slug unique uppercase max 12,
  is_active, created_at)`. Sin campos de branding.
- **Theming front** · `frontend/src/style.css` define TODO vía CSS custom properties
  (`--accent`, `--accent-hover`, `--accent-2`, `--accent-light`, `--accent-glow`,
  `--accent-fg`), con claro/oscuro por `[data-theme]`. `useTheme.js` fija `data-theme`
  en `documentElement` y persiste en `localStorage`. `AppTopBar.vue` tiene el mark
  "AS" + "AllSafe" hardcodeados y muestra `auth.user.organization` (string).
- **`/api/me/`** (`config/views.py`) · devuelve `organization: org.name`. Punto natural
  para inyectar branding del usuario autenticado.
- **Pre-auth** · `RegisterView.vue` NO tiene tenant (crea uno). `AcceptInvitationView.vue`
  resuelve la org por el token (`invitation.organization`). El login por defecto tampoco
  conoce la org hasta autenticar → por eso el branding pre-auth requiere slug en la URL.
- **Billing** · `billing/models.py` · `Subscription.effective_plan` devuelve el `Plan`
  efectivo (trial vencido → free). `Plan.key ∈ {free, pro, business}`. `billing/services.py`
  tiene helpers scoped por org. El gating de branding reutiliza `effective_plan.key`.
- **Media** · `settings.py` ya define `MEDIA_URL="/media/"` y `MEDIA_ROOT=BASE_DIR/"media"`;
  `Pillow>=10.0` está en `requirements.txt`; `config/urls.py` sirve media en `DEBUG`. En
  prod los sirve Nginx (Compose de G-T7).

## Objetivos

1. Una organización de plan pago puede definir: **color de acento**, **logo** (archivo
   subido), **nombre visible** (display), **tema inicial** (claro/oscuro).
2. El branding se aplica en: (a) app autenticada (TopBar + tema), (b) páginas pre-auth
   por slug (login, invitación), con caída a la marca del producto (AllSafe) cuando no
   hay branding.
3. El branding es **feature de pago**: solo Pro/Business. Free ve la marca AllSafe.
4. Aislamiento multi-tenant estricto: un admin solo edita el branding de su propia org;
   el endpoint público no filtra datos sensibles ni branding de orgs inactivas/Free.

## No-objetivos (fuera de alcance)

- **Branding en emails** — pieza **opcional al final** del plan; no bloquea el cierre de
  H4. Si se implementa, va como última tarea (logo/color en plantillas de verificación
  e invitación).
- Subdominios por tenant (DNS wildcard). Se descartó a favor de slug en la ruta.
- Personalización de tipografías o de la paleta completa (solo el acento; el resto de
  tokens neutros permanecen).
- Branding de la landing CMS de marketing (queda como sitio del producto, intacto).
- Temas por usuario (el toggle claro/oscuro por usuario ya existe y se conserva; H4 solo
  agrega un **default por org** para usuarios nuevos).

## Arquitectura

### Componente 1 — Modelo `OrganizationBranding`

Tabla nueva en `tenancy/`, OneToOne con `Organization` (no columnas sueltas en
`Organization`: aísla la responsabilidad y sigue el patrón de `Subscription` en H3).

```python
class OrganizationBranding(models.Model):
    organization = models.OneToOneField(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="branding"
    )
    display_name = models.CharField(max_length=80, blank=True)   # cae a org.name si vacío
    accent_color = models.CharField(max_length=7, blank=True)    # "#RRGGBB" validado
    logo = models.ImageField(upload_to="branding/logos/", blank=True, null=True)
    default_dark = models.BooleanField(default=False)            # tema inicial usuarios nuevos
    updated_at = models.DateTimeField(auto_now=True)
```

- `accent_color`: validación de patrón hex `^#[0-9A-Fa-f]{6}$` (validator a nivel modelo
  y serializer). Vacío = usar acento del producto.
- `logo`: `ImageField` → Pillow verifica que el archivo sea imagen real al validar (no
  basta la extensión). Límite de tamaño (≤ 512 KB) y tipos permitidos (PNG, JPEG, SVG no
  soportado por Pillow → PNG/JPEG/WebP) validados en el serializer.
- `display_name` vacío → el front/serializer resuelve a `org.name`.
- Método/propiedad de conveniencia para serializar branding "efectivo" (con fallbacks).

### Componente 2 — API

Tres superficies:

| Endpoint | Auth | Descripción |
|---|---|---|
| `GET /api/branding/` | Admin de la org | Devuelve el branding propio; si aún no existe registro, devuelve defaults en memoria (no persiste). Scoped a `request.user.organization`. |
| `PUT /api/branding/` | Admin de la org | Actualiza branding propio (multipart para logo). **Gateado**: si `org.subscription.effective_plan.key not in {"pro","business"}` → **403** con `detail` claro. Valida color/imagen. |
| `GET /api/public/branding/<slug>/` | AllowAny (público) | Pre-auth. Devuelve **solo** `{display_name, accent_color, logo_url, default_dark}` de orgs `is_active` **y** con plan pago. Si la org no existe, está inactiva, o no es plan pago → **404** (el front cae a marca AllSafe). |

Además, **extender `/api/me/`**: agregar clave `branding: {display_name, accent_color,
logo_url, default_dark} | null`, tomada de la org del usuario (null si Free/no branding),
para aplicar tema apenas carga la app autenticada.

**Ubicación**: el endpoint público va bajo `/api/public/` (junto a `landing_cms.public_urls`)
y **exento del middleware de tenancy** como el resto de `/api/public/`. El endpoint de
edición (`/api/branding/`) es tenant-scoped normal (pasa por middleware, resuelve org del
usuario).

**Permisos**: edición solo para rol `ADMIN` de la org. `GET /api/branding/` puede ser
legible por admin; el público es AllowAny pero de superficie mínima.

### Componente 3 — Frontend: aplicación runtime del tema

- **`composables/useBranding.js`** (nuevo): función `applyBranding({accent_color,
  default_dark})` que sobreescribe las CSS custom properties en `documentElement.style`:
  setea `--accent` y deriva `--accent-hover`, `--accent-2`, `--accent-light`,
  `--accent-glow` con `color-mix(in srgb, ...)`. Un único punto de inyección; el resto de
  componentes ya consume esas variables. `clearBranding()` revierte a los tokens del
  producto (remueve las overrides inline).
- **App autenticada**: `auth.store` ya llama `/api/me/`. Al recibir `branding`, llama
  `applyBranding`. `AppTopBar.vue` muestra el `logo_url` (o el mark "AS" como fallback) y
  el `display_name` (o `org.name`).
- **Pre-auth por slug**: rutas nuevas `/o/:slug/login` y `/o/:slug/invitacion/:token`
  (las rutas existentes sin slug se conservan con marca AllSafe). Un guard/onMounted
  resuelve `GET /api/public/branding/:slug`, aplica branding antes de pintar; 404 → marca
  del producto. La página de invitación existente puede además leer branding por el slug
  de la org de la invitación.
- **Pantalla admin `/admin/branding`**: formulario con color picker (input color + hex),
  upload de logo con preview, toggle de tema por defecto, campo nombre visible. Si el plan
  es Free: estado "upsell" (deshabilitado + CTA a `/admin/suscripcion`). El gating visual
  es cosmético; la verdad la impone el backend (403).

### Componente 4 — Plan gating (fuente de verdad = servidor)

El gating vive en el backend vía `effective_plan.key ∈ {pro, business}`. El front puede
ocultar/deshabilitar el editor para Free, pero aunque se invoque el `PUT` directo, el
backend responde 403. Doctrina heredada de H3: el estado pagado solo lo determina el
servidor (webhook Stripe firmado); ningún camino del front puede auto-habilitar branding.

El endpoint público también respeta el gating: branding de orgs Free → 404 (no se sirve).

## Flujo de datos

**Editar (admin, plan pago):**
1. Admin abre `/admin/branding` → `GET /api/branding/` (branding actual o defaults).
2. Cambia color/logo/nombre/tema → `PUT /api/branding/` (multipart).
3. Backend valida plan (403 si Free), valida color/imagen, guarda, devuelve branding.
4. Front aplica `applyBranding` inmediatamente.

**App autenticada (cualquier usuario de org paga):**
1. Login → `/api/me/` devuelve `branding`.
2. `useBranding.applyBranding` sobrescribe CSS vars; TopBar pinta logo + display_name.

**Pre-auth por slug:**
1. Usuario abre `/o/ACME/login` → `GET /api/public/branding/ACME`.
2. 200 → aplica branding (color + logo en la pantalla de auth). 404 → marca AllSafe.

## Manejo de errores

- Color inválido (no hex) → 400 con mensaje de campo.
- Imagen inválida / muy grande / tipo no soportado → 400 con mensaje de campo.
- Plan Free intenta `PUT` → 403 `{"detail": "El branding es una función de los planes Pro y Business."}`.
- No-admin intenta editar → 403.
- Admin de org A intenta editar branding de org B → imposible por diseño (el endpoint
  resuelve la org del usuario; no acepta org por body/param).
- Público pide slug inexistente/inactivo/Free → 404 (front cae a marca producto, sin error visible).

## Testing

- **Unit**: validación hex de color (acepta `#0038FF`, rechaza `red`, `#GGG`, `0038FF`);
  validación de imagen (rechaza archivo no-imagen aunque tenga extensión `.png`; rechaza
  > 512 KB); fallback `display_name` vacío → `org.name`; derivación de branding efectivo.
- **Adversarial** (línea H1/H3):
  - (a) org Free no puede editar branding → 403 (y su branding público → 404).
  - (b) admin de org A no puede editar/ver branding de org B (scoped) → sin fuga.
  - (c) endpoint público devuelve **solo** los 4 campos de branding; nunca plan, conteo
    de agentes, ni datos de la org; no sirve branding de orgs inactivas.
  - (d) no-admin (AGENT/CLIENT) no puede editar branding → 403.
- **Gate**: suite completa en DB fresca (`--noinput`) al cerrar la rama.

## Nota de deploy

Los logos subidos se guardan en `MEDIA_ROOT` (`branding/logos/`). En dev los sirve Django
(`DEBUG`); en prod los sirve Nginx bajo `/media/` (ya en el Compose de G-T7). Documentar
en el runbook (`docs/deploy.md` o equivalente) que el volumen de media debe persistir.

## Opcional (última tarea, no bloquea H4)

**Branding en emails**: inyectar `logo_url` y `accent_color` de la org en las plantillas
de verificación e invitación (accounts). Se implementa como tarea final del plan; si el
tiempo aprieta, se difiere sin afectar el cierre de H4.
