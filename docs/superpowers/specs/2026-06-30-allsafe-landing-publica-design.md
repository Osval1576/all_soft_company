# AllSafe — Landing pública con mini-CMS — Diseño

**Fecha:** 2026-06-30
**Sub-proyecto:** #3 en la descomposición de AllSafe (ver "Contexto y posicionamiento")
**Estado:** Aprobado por el usuario, listo para `writing-plans`

---

## 1. Contexto y posicionamiento

AllSafe es un help-desk single-tenant funcional (Django 6 + DRF + Channels + MySQL en backend, Vue 3 + Pinia + Vite en frontend). El usuario está construyendo una plataforma SaaS multi-producto para PYMEs y empresas. AllSafe es **uno** de los módulos planeados; por ahora es el único concreto.

Descomposición acordada de toda la iniciativa (este spec cubre el #3):

| # | Sub-proyecto | Estado |
|---|---|---|
| 1 | AllSafe v2 — SLAs + CSAT + métricas | Pausado (decisiones tomadas, retomar después) |
| 2 | Rediseño UI/UX + design system | Futuro |
| **3** | **Landing pública + mini-CMS** | **Este spec** |
| 4 | Endurecimiento producción | Futuro |
| 5 | Multi-tenant + billing | Futuro |
| 6 | Plataforma multi-módulo | Solo si aparece un segundo producto |

## 2. Objetivo

Construir una landing pública profesional para el producto AllSafe, accesible en `/`, **enteramente administrable desde el dashboard de ADMIN** (mini-CMS). Incluye internacionalización ES/EN y un formulario de contacto que se integra con el sistema de tickets existente.

## 3. Alcance

### 3.1 Incluido

- Landing one-page con 7 secciones (header, hero, features, sobre nosotros, ubicaciones, contacto, footer)
- Internacionalización ES/EN
- Mini-CMS con 6 modelos (Hero, Feature, About, TeamMember, Location, SiteSettings)
- 3 pantallas nuevas en `/admin/sitio/` (contenido, equipo, ubicaciones)
- Integración Google Maps (mapa público) + Google Places (autocomplete admin)
- Formulario de contacto que crea Ticket + User CUSTOMER automáticamente
- Animaciones GSAP + ScrollTrigger nivel intermedio
- Estilo visual moderno minimalista (Linear/Stripe/Vercel)

### 3.2 Excluido

- Pricing, FAQ, testimonios (no se eligieron)
- Self-signup público (CTA principal es "Iniciar sesión", no registro)
- Email transaccional / SMTP (formulario crea ticket, no envía email)
- SEO avanzado / SSG (vivimos dentro del Vue SPA; meta tags vía `useHead` sí, pero sin pre-render)
- Blog / contenido editorial
- Subida a S3 (almacenamiento local en `MEDIA_ROOT` por ahora)

## 4. Arquitectura general

Tres zonas en el frontend Vue, separadas por layout:

- **Zona pública** (`PublicLayout`, sin auth): `/` landing one-page, `/login` ya existente
- **Zona privada** (dashboards, sin cambios estructurales): `/cliente`, `/tecnico`, `/admin`
- **Admin del CMS** (dentro de `/admin/sitio/...`, requiere rol ADMIN): 3 pantallas nuevas

En el backend Django se crea una nueva app `landing_cms` con sus modelos, serializadores, viewsets y URLs. La app `tickets_t` recibe un endpoint nuevo `POST /api/public/contact/` que crea Ticket + User.

## 5. Modelos de datos

Nueva app: `backend/landing_cms/`.

**Estrategia i18n:** campos duplicados con sufijo `_es` y `_en` en el mismo modelo. Explícito, sin dependencias extra, suficiente para 2 idiomas. Si en el futuro se agregan más idiomas conviene migrar a `django-modeltranslation`.

### 5.1 HeroContent (singleton)
```
title_es, title_en           CharField(200)
subtitle_es, subtitle_en     TextField
primary_cta_label_es/_en     CharField(50)
primary_cta_url              CharField(200)     # default "/login"
secondary_cta_label_es/_en   CharField(50)
secondary_cta_url            CharField(200)     # default "#contacto"
updated_at                   DateTimeField(auto_now=True)
```

### 5.2 Feature (lista ordenable)
```
icon          CharField(50)     # nombre del Tabler icon, ej. "ticket"
title_es/_en  CharField(100)
description_es/_en TextField
order         PositiveIntegerField
is_active     BooleanField(default=True)
```

### 5.3 AboutContent (singleton)
```
mission_es/_en  TextField
vision_es/_en   TextField
values_es/_en   TextField(blank=True)
updated_at      DateTimeField(auto_now=True)
```

### 5.4 TeamMember (lista ordenable)
```
photo         ImageField(upload_to="team/")
name          CharField(100)
role_es/_en   CharField(100)
bio_es/_en    TextField(blank=True)
order         PositiveIntegerField
is_active     BooleanField(default=True)
```

### 5.5 Location (lista ordenable)
```
name                  CharField(100)        # nombre interno, no i18n
address               CharField(255)        # devuelto por Google Places
lat                   DecimalField(max_digits=9, decimal_places=6)
lng                   DecimalField(max_digits=9, decimal_places=6)
phone                 CharField(50, blank=True)
email                 EmailField(blank=True)
hours_es/_en          CharField(200, blank=True)
photo                 ImageField(upload_to="locations/", blank=True)
description_es/_en    TextField(blank=True)
type                  CharField(20, choices=[("SUCURSAL","Sucursal"),("OFICINA","Oficina"),("CENTRO","Centro de servicio")])
order                 PositiveIntegerField
is_active             BooleanField(default=True)
```

### 5.6 SiteSettings (singleton)
```
logo                 ImageField(upload_to="site/", blank=True)
footer_text_es/_en   TextField(blank=True)
social_links         JSONField(default=dict)    # {"twitter": "...", "linkedin": "..."}
google_maps_api_key  CharField(100, blank=True) # admin la pega aquí; el frontend la lee del endpoint público
```

### 5.7 Patrón singleton

Para los 3 singletons (`HeroContent`, `AboutContent`, `SiteSettings`):
- `save()` fuerza `pk=1`
- `Meta.constraints` con `UniqueConstraint(name="...singleton", fields=["pk"], condition=Q(pk=1))` (o más simple: el `save()` override)
- Helper `cls.load()` → `objects.get_or_create(pk=1)[0]`

### 5.8 Formulario de contacto — sin modelo propio

`POST /api/public/contact/` con body `{name, email, subject, message}`:
1. Busca o crea `User` con `email=...`, `username=email`, `role=CUSTOMER`, password aleatoria no usable (`set_unusable_password()`).
2. Crea `Ticket` con `titulo=subject`, `descripcion=message`, `prioridad="MEDIUM"`, `estado="OPEN"`, `creado_por=ese_user`, `reference=` autogenerado (mismo patrón actual).
3. Devuelve `201` con `{ticket_reference}`.

Validación: rate-limit por IP (5 envíos por hora) usando el throttling propio de DRF (`AnonRateThrottle`, ver Sección 8.1). Honeypot field `website` que si viene lleno se descarta silenciosamente (anti-spam básico).

## 6. API

Dos namespaces nuevos en `config/urls.py`:

### 6.1 Públicos — sin auth (`/api/public/`)

| Método | Ruta | Devuelve |
|---|---|---|
| GET | `/api/public/landing/hero/` | objeto HeroContent serializado |
| GET | `/api/public/landing/features/` | lista de Features activas, ordenadas |
| GET | `/api/public/landing/about/` | objeto AboutContent serializado |
| GET | `/api/public/landing/team/` | lista de TeamMembers activos, ordenados |
| GET | `/api/public/landing/locations/` | lista de Locations activas, ordenadas |
| GET | `/api/public/site-settings/` | logo, footer, redes, google_maps_api_key |
| POST | `/api/public/contact/` | crea Ticket+User, devuelve {ticket_reference} |

Permission class: `AllowAny`. Cache-Control: `public, max-age=60` en los GETs (cache 60s en navegador para no pegarle al backend en cada navegación).

### 6.2 Admin — rol ADMIN (`/api/admin/landing/`)

| Método | Ruta | Acción |
|---|---|---|
| GET, PUT | `/api/admin/landing/hero/` | leer/actualizar singleton |
| GET, PUT | `/api/admin/landing/about/` | leer/actualizar singleton |
| GET, PUT | `/api/admin/site-settings/` | leer/actualizar singleton |
| ModelViewSet | `/api/admin/landing/features/` | CRUD |
| ModelViewSet | `/api/admin/landing/team/` | CRUD |
| ModelViewSet | `/api/admin/landing/locations/` | CRUD |
| POST | `/api/admin/landing/{recurso}/reorder/` | body `{ids: [3,1,2]}` reasigna order |

Permission class nueva: `IsAdminRole` (`user.is_authenticated and (user.is_superuser or user.role == "ADMIN")`).

Subida de imágenes: `multipart/form-data` en los PUT/POST de team/locations/site-settings.

## 7. Frontend

### 7.1 Routing

`frontend/src/router/index.js` añade:

```js
// públicas
{ path: "/", name: "landing", component: LandingHome, meta: { public: true } }
// admin del CMS, anidadas bajo /admin
{ path: "/admin/sitio/contenido", component: AdminContent, meta: { role: "ADMIN" } }
{ path: "/admin/sitio/equipo",     component: AdminTeam,    meta: { role: "ADMIN" } }
{ path: "/admin/sitio/ubicaciones",component: AdminLocations, meta: { role: "ADMIN" } }
```

Cambio en el guard global: si `to.meta.public` no exigir auth; el redirect actual `/` → `/login` se elimina (ahora `/` es la landing).

### 7.2 Layouts

No existe `frontend/src/layouts/`; se crea como parte de este spec.

- `layouts/PublicLayout.vue` — wrapper con header sticky y footer. El header tiene logo, anchor nav, language toggle, botón "Iniciar sesión".
- `layouts/AdminLayout.vue` — wrapper para `/admin/*` con sidebar que ahora incluye el grupo "Sitio web". Hoy los dashboards tienen su propio chrome inline; este spec **no** los refactoriza, solo agrega `AdminLayout` para las 3 pantallas nuevas. El refactor del resto cae en sub-proyecto #2.

`LoginView` también se envuelve en `PublicLayout` (header + footer compartidos).

### 7.3 Componentes nuevos

```
views/public/
  LandingHome.vue          # orquesta las 6 secciones
components/public/
  HeroSection.vue
  FeaturesSection.vue
  AboutSection.vue
  LocationsSection.vue     # mapa Google + lista lateral
  ContactSection.vue       # formulario que POST a /api/public/contact/
  PublicHeader.vue
  PublicFooter.vue
views/admin/site/
  AdminContent.vue         # editor de Hero + About + SiteSettings + tabla Features
  AdminTeam.vue            # CRUD miembros
  AdminLocations.vue       # CRUD ubicaciones con mapa + Places autocomplete
components/admin/site/
  LocationFormModal.vue    # con GooglePlacesAutocomplete + DraggablePinMap
  TeamMemberFormModal.vue
  FeatureFormRow.vue
  I18nField.vue            # input/textarea con tabs ES/EN
  DragHandleList.vue       # wrapper que da drag-to-reorder
api/
  landing.api.js           # llamadas a /api/public/landing/* y /api/admin/landing/*
stores/
  landing.store.js         # cache del contenido público (TTL 60s)
  locale.store.js          # idioma actual + getter t() simplificado
```

### 7.4 i18n

`vue-i18n` con dos locales: `es` (default) y `en`.

- **Textos estáticos del chrome** (header nav, etiquetas de formulario, mensajes de error): archivos `locales/es.json` y `locales/en.json`.
- **Contenido dinámico del CMS**: el frontend recibe ambos campos `_es` y `_en` y elige según `locale.current`. Helper: `pick(obj, locale)` → `obj[`field_${locale}`]`.

`locale.store.js` persiste la preferencia en `localStorage`. Toggle ES/EN en el `PublicHeader`.

### 7.5 Animaciones

- Librería: `gsap` + `ScrollTrigger`.
- Patrón: composable `useScrollReveal()` que aplica fade-up con stagger cuando el elemento entra al viewport.
- Hero: parallax sutil del fondo + counters animados si se agregan métricas.
- Performance: `prefers-reduced-motion` respetado (todas las animaciones se deshabilitan).

### 7.6 Google Maps

- Carga del SDK con `loader.load()` usando la API key recibida desde `/api/public/site-settings/`.
- En la **landing**: un solo mapa con todos los pines, click en pin abre InfoWindow con nombre/foto/dirección/teléfono.
- En el **admin** (`LocationFormModal`): mapa con un pin arrastrable + buscador con `PlaceAutocomplete`. Al seleccionar una predicción de Places se rellena `address/lat/lng` automáticamente; el usuario puede arrastrar el pin para ajustar las coordenadas finales.

**Importante:** la API key vive en `SiteSettings.google_maps_api_key`. El frontend la consume vía el endpoint público. Si no está configurada, la sección de ubicaciones muestra solo la lista (sin mapa), y el modal admin muestra un aviso pidiendo configurarla en `/admin/sitio/contenido` → tab "Site settings".

### 7.7 Subida de fotos

Componente reutilizable `<ImageDrop>` que envuelve `<input type="file">` con drag-and-drop, preview inline, validación cliente (max 2 MB, jpg/png/webp). En envío usa `FormData`.

## 8. Configuración Django

### 8.1 Settings (`config/settings.py`)

```python
INSTALLED_APPS += [
    "landing_cms",
    "django_cleanup.apps.CleanupConfig",  # borra archivos al borrar registros
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Throttle global para /api/public/contact/
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = ["rest_framework.throttling.AnonRateThrottle"]
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {"anon": "5/hour"}
```

### 8.2 URLs (`config/urls.py`)

```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns += [
    path("api/public/", include("landing_cms.public_urls")),
    path("api/admin/landing/", include("landing_cms.admin_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

En producción real, servir `MEDIA_ROOT` con nginx/whitenoise (fuera del scope de este spec — entra en sub-proyecto #4).

### 8.3 Migraciones de datos iniciales

Migración `0002_seed_singletons.py` que crea las instancias singleton vacías con `pk=1` para `HeroContent`, `AboutContent`, `SiteSettings`. Así el admin nunca se enfrenta a "no existe la fila" — siempre hay algo que editar.

## 9. UX y comportamiento

### 9.1 Landing (público)

- One-page con anchor navigation suave (`scroll-behavior: smooth` + offset por header sticky).
- Carga: un solo `Promise.all` al montar `LandingHome` que pega los 6 endpoints públicos. Mientras cargan: skeleton screens por sección (no spinners).
- Si un endpoint falla: la sección se oculta silenciosamente; el resto de la landing renderiza igual.
- Cambio de idioma: instantáneo, sin recarga; los textos del CMS cambian leyendo del estado en memoria (ya tenemos ambos idiomas).
- Formulario de contacto: validación cliente, después POST; al recibir `201` mostrar mensaje de éxito con el `ticket_reference` ("Recibimos tu mensaje, referencia AS-00042"). Si falla: error inline.

### 9.2 Admin del CMS

- Sidebar de `/admin` recibe un nuevo grupo "Sitio web" con 3 entradas: Contenido, Equipo, Ubicaciones.
- **Contenido** (`AdminContent`): vista con secciones colapsables — Hero, Sobre nosotros, Features, Site settings. Cada bloque tiene "Guardar" propio (no un guardar global). Toast de éxito.
- **Equipo** (`AdminTeam`): tabla con foto, nombre, cargo (ES), activo, drag handle. Botón "+ Agregar miembro" abre modal. Click en fila edita.
- **Ubicaciones** (`AdminLocations`): igual patrón. Modal incluye Places autocomplete + pin arrastrable (ver Sección 7.6).
- Reordenamiento: drag-and-drop con `vuedraggable`; al soltar manda `POST .../reorder/` con la nueva lista de IDs.

## 10. Seguridad

- **Endpoints públicos GET:** sin auth pero con cache 60s. Solo devuelven objetos `is_active=True`.
- **POST /api/public/contact/:** throttling 5/hora por IP + honeypot. El User creado tiene contraseña no usable (no puede loguearse hasta que ADMIN le invite).
- **Endpoints admin:** `IsAdminRole` permission. Si `user.role != "ADMIN"` y no es `is_superuser`, 403.
- **Subidas de archivos:** validación con `Pillow.Image.verify()` (ya disponible al instalar Pillow), límite 2 MB, sólo jpg/png/webp.
- **Google Maps API key:** se devuelve al frontend público pero **siempre debe tener restricciones HTTP referrer en la consola de Google Cloud** (documentar en README). Si se filtra sin restricciones, el costo lo paga el usuario. Documentar advertencia.

## 11. Testing

- **Backend:** tests unitarios por modelo (singleton enforcement, validaciones); tests de cada endpoint público (200, contenido correcto, filtra inactivos); tests de cada endpoint admin (permisos, CRUD, reorder); test específico de `/api/public/contact/` que verifica la creación de Ticket+User y el rate-limit.
- **Frontend:** test de `pick(obj, locale)`; test del store `locale`; smoke tests de cada componente público.
- **E2E mínimo (manual):** flujo completo "ADMIN edita Hero → recarga landing → ve cambios"; "Visitante envía contacto → AGENT ve ticket en su inbox".

## 12. Riesgos y trade-offs

| Riesgo | Mitigación |
|---|---|
| API key de Google Maps expuesta | Documentar restricciones por referrer; rotar si se filtra. La key se gestiona en `SiteSettings`, fácil de cambiar. |
| Costos Google Maps si la landing tiene tráfico alto | Free tier de ~$200/mes suele bastar para una landing inicial. Monitorear desde Google Cloud. |
| i18n duplicado en campos `_es`/`_en` se vuelve incómodo con 3+ idiomas | Si pasa, migrar a `django-modeltranslation`. Para 2 idiomas, manual es más claro. |
| Subir archivos a `MEDIA_ROOT` local en producción rompe con múltiples instancias | Fuera de scope (sub-proyecto #4 endurecimiento). Por ahora asume una instancia. |
| SSG/SEO limitado al ser SPA | Aceptado. AllSafe es B2B, no depende de SEO orgánico. Si más adelante se necesita, migrar la landing a Astro/Next con SSR (refactor del sub-proyecto #2 o #6). |
| Spam en el formulario de contacto | Honeypot + throttling. Si crece el problema, agregar reCAPTCHA en una iteración futura. |

## 13. Estimación gruesa

| Bloque | Esfuerzo |
|---|---|
| Backend (app `landing_cms`, modelos, migraciones, viewsets, urls) | 2-3 días |
| Endpoint contacto + integración tickets | 0.5 día |
| Frontend público: layout, secciones, animaciones GSAP | 4-5 días |
| Frontend admin: 3 pantallas + modal con Google Places | 4-5 días |
| i18n (configurar vue-i18n, traducir chrome) | 1-2 días |
| Tests + ajustes | 1-2 días |
| **Total** | **~2.5 - 3 semanas** de un dev solo |

## 14. Out of scope explícito (no hacer en este spec)

- Pricing page, FAQ, testimonios, blog.
- Self-signup público.
- SSG / SSR.
- Email transaccional / SMTP.
- Subida de imágenes a S3 / CDN.
- reCAPTCHA / captcha avanzado.
- A/B testing en la landing.
- Analytics (GA4, Plausible). Se pueden meter después en una iteración micro.

---

**Próximo paso:** revisión del usuario; al aprobar, se invoca `superpowers:writing-plans` para producir el plan de implementación.
