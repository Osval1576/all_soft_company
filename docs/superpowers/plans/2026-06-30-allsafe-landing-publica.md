# AllSafe — Landing pública + mini-CMS — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public, GSAP-animated, ES/EN landing page for AllSafe, fully editable from a new mini-CMS in the ADMIN dashboard, including a contact form that creates Tickets in the existing help-desk.

**Architecture:** Add a Django app `landing_cms` with 6 i18n models (3 singletons, 3 ordered lists) plus public and admin REST endpoints. Reorganize the Vue SPA into a public zone (landing + login) and a private zone (existing dashboards). Add 3 admin screens for the CMS. Landing consumes the public endpoints and renders with vue-i18n + GSAP + Google Maps. Contact form POSTs to a new endpoint that creates Ticket + User on the existing `tickets_t` app.

**Tech Stack:** Backend — Django 6, DRF, Pillow, django-cleanup. Frontend — Vue 3.5, Pinia, Vue Router, vue-i18n 9, gsap (+ ScrollTrigger), @vueuse/core, vuedraggable, Google Maps JS API + Places. Spec reference: `docs/superpowers/specs/2026-06-30-allsafe-landing-publica-design.md`.

## Global Constraints

- Backend: Django 6.0.3, Python 3.x, MySQL 8 (utf8mb4), DRF default auth = `CookieJWTAuthentication`. New endpoints must explicitly set `permission_classes` (public = `[AllowAny]`, admin = `[IsAdminRole]`).
- i18n strategy: paired `_es` / `_en` fields on the same model. Both languages always returned; frontend picks via locale store.
- File uploads: `MEDIA_ROOT = BASE_DIR / "media"`, `MEDIA_URL = "/media/"`. Validation: Pillow `Image.verify()` + size ≤ 2 MB + content-type in `{jpeg, png, webp}`.
- Throttling on `POST /api/public/contact/`: 5/hour per IP via a scoped DRF `ScopedRateThrottle` (scope `"contact"`). Applied **only** at the view level — must NOT be set as `DEFAULT_THROTTLE_CLASSES` (that would throttle the public GETs too and break the landing after one visit).
- Singleton pattern: `pk=1` enforced in `save()`; helper `cls.load()` returns the unique row, creating it if missing.
- Frontend: keep current Vite 8 / Vue 3.5 / Pinia / Vue Router. No bundler swap. No SSR.
- Naming: app folder `landing_cms`. URL prefixes `/api/public/` and `/api/admin/landing/`. Vue routes `/`, `/admin/sitio/contenido`, `/admin/sitio/equipo`, `/admin/sitio/ubicaciones`.
- Commits: small, frequent, conventional (`feat:`, `test:`, `chore:`, `docs:`). One per task minimum.

---

## File Structure

**Backend (new):**
```
backend/landing_cms/
  __init__.py
  apps.py
  models.py
  managers.py        # SingletonManager
  serializers.py
  permissions.py     # IsAdminRole
  validators.py      # validate_image_file
  public_views.py
  admin_views.py
  public_urls.py
  admin_urls.py
  admin.py           # Django admin registration
  migrations/
    0001_initial.py
    0002_seed_singletons.py
  tests/
    __init__.py
    test_models.py
    test_public_endpoints.py
    test_admin_endpoints.py
    test_contact_endpoint.py
```

**Backend (modified):**
- `backend/config/settings.py` — add INSTALLED_APPS, MEDIA_*, throttling
- `backend/config/urls.py` — include new url modules + media static in DEBUG
- `backend/requirements.txt` (if exists, otherwise document install)

**Frontend (new):**
```
frontend/src/
  layouts/
    PublicLayout.vue
    AdminLayout.vue
  i18n/
    index.js
    locales/
      es.json
      en.json
  composables/
    useScrollReveal.js
    useLandingContent.js
    usePick.js
  stores/
    locale.store.js
    landing.store.js
  api/
    landing.api.js
  views/
    public/
      LandingHome.vue
    admin/site/
      AdminContent.vue
      AdminTeam.vue
      AdminLocations.vue
  components/
    public/
      PublicHeader.vue
      PublicFooter.vue
      HeroSection.vue
      FeaturesSection.vue
      AboutSection.vue
      LocationsSection.vue
      ContactSection.vue
    admin/site/
      I18nField.vue
      DragHandleList.vue
      ImageDrop.vue
      TeamMemberFormModal.vue
      LocationFormModal.vue
      FeatureFormRow.vue
```

**Frontend (modified):**
- `frontend/package.json` — new dependencies
- `frontend/src/main.js` — register vue-i18n
- `frontend/src/router/index.js` — new routes, layouts, public meta flag
- `frontend/src/views/LoginView.vue` — wrap in PublicLayout (header/footer)
- `frontend/src/views/dashboards/AdminDashboard.vue` — add sidebar group "Sitio web"

---

## Task 1 — Bootstrap Django app `landing_cms`

**Files:**
- Create: `backend/landing_cms/__init__.py`
- Create: `backend/landing_cms/apps.py`
- Modify: `backend/config/settings.py` (INSTALLED_APPS + MEDIA + throttling)
- Modify: `backend/config/urls.py` (media static in DEBUG)

**Interfaces:**
- Consumes: nothing
- Produces: registered Django app `landing_cms`; settings `MEDIA_URL`, `MEDIA_ROOT`; throttling defaults

- [ ] **Step 1: Install Pillow and django-cleanup**

Run (in the backend's Python env):
```
pip install Pillow django-cleanup
```

If `backend/requirements.txt` exists, append:
```
Pillow>=10.0
django-cleanup>=8.0
```
Otherwise create `backend/requirements.txt` with the above two lines plus `Django==6.0.3`, `djangorestframework`, `django-cors-headers`, `channels`, `djangorestframework-simplejwt`, `mysqlclient` (or whatever the project already uses — check `pip freeze`).

- [ ] **Step 2: Create the app package**

Create `backend/landing_cms/__init__.py` (empty).

Create `backend/landing_cms/apps.py`:
```python
from django.apps import AppConfig


class LandingCmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "landing_cms"
```

- [ ] **Step 3: Register in settings**

Modify `backend/config/settings.py`. In `INSTALLED_APPS` add:
```python
    "landing_cms",
    "django_cleanup.apps.CleanupConfig",
```

Below `STATIC_URL = "static/"` add:
```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

In the `REST_FRAMEWORK` dict (currently at the bottom) add ONLY a `DEFAULT_THROTTLE_RATES` entry for the scope used by the contact endpoint — do NOT add `DEFAULT_THROTTLE_CLASSES`, that would throttle every anonymous request including the landing's public GETs. The contact view itself declares the scoped throttle in Task 10.

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "config.authentication.CookieJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "contact": "5/hour",
    },
}
```

- [ ] **Step 4: Serve media in dev**

Modify `backend/config/urls.py`. At the top add:
```python
from django.conf import settings
from django.conf.urls.static import static
```

At the bottom (after `urlpatterns = [...]`) add:
```python
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- [ ] **Step 5: Verify the app loads**

Run:
```
python backend/manage.py check
```
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 6: Commit**

```
git add backend/landing_cms backend/config/settings.py backend/config/urls.py backend/requirements.txt
git commit -m "feat(landing_cms): bootstrap app with MEDIA + throttling"
```

---

## Task 2 — Singleton manager + base validators

**Files:**
- Create: `backend/landing_cms/managers.py`
- Create: `backend/landing_cms/validators.py`
- Create: `backend/landing_cms/tests/__init__.py`
- Create: `backend/landing_cms/tests/test_validators.py`

**Interfaces:**
- Produces:
  - `landing_cms.managers.SingletonManager` — manager with `get_solo()` returning the unique row (create if missing).
  - `landing_cms.validators.validate_image_file(file)` — raises `ValidationError` if file is not a valid jpeg/png/webp or exceeds 2 MB.

- [ ] **Step 1: Write the failing test for the validator**

Create `backend/landing_cms/tests/__init__.py` (empty).

Create `backend/landing_cms/tests/test_validators.py`:
```python
from io import BytesIO
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from landing_cms.validators import validate_image_file


def _png_bytes(w=10, h=10):
    buf = BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="PNG")
    return buf.getvalue()


class ValidateImageFileTests(TestCase):
    def test_accepts_small_png(self):
        f = SimpleUploadedFile("ok.png", _png_bytes(), content_type="image/png")
        validate_image_file(f)  # must not raise

    def test_rejects_non_image(self):
        f = SimpleUploadedFile("evil.txt", b"hello", content_type="text/plain")
        with self.assertRaises(ValidationError):
            validate_image_file(f)

    def test_rejects_oversize(self):
        big = b"\x00" * (2 * 1024 * 1024 + 1)
        f = SimpleUploadedFile("big.png", big, content_type="image/png")
        with self.assertRaises(ValidationError):
            validate_image_file(f)
```

- [ ] **Step 2: Run to see it fail**

Run:
```
python backend/manage.py test landing_cms.tests.test_validators -v 2
```
Expected: `ModuleNotFoundError: No module named 'landing_cms.validators'`.

- [ ] **Step 3: Implement the validator**

Create `backend/landing_cms/validators.py`:
```python
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 2 * 1024 * 1024


def validate_image_file(file):
    if file.size > MAX_BYTES:
        raise ValidationError("La imagen excede 2 MB.")
    if getattr(file, "content_type", None) not in ALLOWED_CONTENT_TYPES:
        raise ValidationError("Tipo de archivo no permitido (usa jpg, png o webp).")
    try:
        img = Image.open(file)
        img.verify()
    except (UnidentifiedImageError, Exception):
        raise ValidationError("El archivo no es una imagen válida.")
    finally:
        file.seek(0)
```

- [ ] **Step 4: Run to confirm green**

Run:
```
python backend/manage.py test landing_cms.tests.test_validators -v 2
```
Expected: `OK` with 3 tests passing.

- [ ] **Step 5: Implement SingletonManager**

Create `backend/landing_cms/managers.py`:
```python
from django.db import models


class SingletonManager(models.Manager):
    def get_solo(self):
        obj, _ = self.get_or_create(pk=1)
        return obj
```

- [ ] **Step 6: Commit**

```
git add backend/landing_cms/managers.py backend/landing_cms/validators.py backend/landing_cms/tests/
git commit -m "feat(landing_cms): SingletonManager + image validator"
```

---

## Task 3 — Models: singletons (Hero, About, SiteSettings)

**Files:**
- Create: `backend/landing_cms/models.py`
- Create: `backend/landing_cms/tests/test_models.py`
- Create: migration `backend/landing_cms/migrations/0001_initial.py` (generated)

**Interfaces:**
- Produces:
  - `landing_cms.models.HeroContent` with fields `title_es`, `title_en`, `subtitle_es`, `subtitle_en`, `primary_cta_label_es`, `primary_cta_label_en`, `primary_cta_url`, `secondary_cta_label_es`, `secondary_cta_label_en`, `secondary_cta_url`, `updated_at`. Manager: `objects` (SingletonManager). `save()` forces `pk=1`.
  - Same pattern for `AboutContent` (fields `mission_es`, `mission_en`, `vision_es`, `vision_en`, `values_es`, `values_en`, `updated_at`).
  - `SiteSettings` with `logo`, `footer_text_es`, `footer_text_en`, `social_links` (JSONField default `dict`), `google_maps_api_key`.

- [ ] **Step 1: Write failing tests for singleton behavior**

Create `backend/landing_cms/tests/test_models.py`:
```python
from django.test import TestCase
from landing_cms.models import HeroContent, AboutContent, SiteSettings


class HeroContentSingletonTests(TestCase):
    def test_load_creates_if_missing(self):
        obj = HeroContent.objects.get_solo()
        self.assertEqual(obj.pk, 1)

    def test_load_returns_same_row(self):
        a = HeroContent.objects.get_solo()
        b = HeroContent.objects.get_solo()
        self.assertEqual(a.pk, b.pk)

    def test_save_forces_pk_1(self):
        h = HeroContent(pk=99, title_es="x", title_en="x")
        h.save()
        self.assertEqual(h.pk, 1)


class AboutContentSingletonTests(TestCase):
    def test_load_creates_if_missing(self):
        obj = AboutContent.objects.get_solo()
        self.assertEqual(obj.pk, 1)


class SiteSettingsSingletonTests(TestCase):
    def test_load_creates_if_missing(self):
        obj = SiteSettings.objects.get_solo()
        self.assertEqual(obj.pk, 1)
```

- [ ] **Step 2: Run, expect failure**

Run:
```
python backend/manage.py test landing_cms.tests.test_models -v 2
```
Expected: `ModuleNotFoundError: ... models`.

- [ ] **Step 3: Implement the models**

Create `backend/landing_cms/models.py`:
```python
from django.db import models
from .managers import SingletonManager
from .validators import validate_image_file


class _SingletonBase(models.Model):
    objects = SingletonManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class HeroContent(_SingletonBase):
    title_es = models.CharField(max_length=200, blank=True)
    title_en = models.CharField(max_length=200, blank=True)
    subtitle_es = models.TextField(blank=True)
    subtitle_en = models.TextField(blank=True)

    primary_cta_label_es = models.CharField(max_length=50, default="Iniciar sesión")
    primary_cta_label_en = models.CharField(max_length=50, default="Sign in")
    primary_cta_url = models.CharField(max_length=200, default="/login")

    secondary_cta_label_es = models.CharField(max_length=50, default="Contactar")
    secondary_cta_label_en = models.CharField(max_length=50, default="Contact us")
    secondary_cta_url = models.CharField(max_length=200, default="#contacto")

    updated_at = models.DateTimeField(auto_now=True)


class AboutContent(_SingletonBase):
    mission_es = models.TextField(blank=True)
    mission_en = models.TextField(blank=True)
    vision_es = models.TextField(blank=True)
    vision_en = models.TextField(blank=True)
    values_es = models.TextField(blank=True)
    values_en = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class SiteSettings(_SingletonBase):
    logo = models.ImageField(
        upload_to="site/", blank=True, null=True,
        validators=[validate_image_file],
    )
    footer_text_es = models.TextField(blank=True)
    footer_text_en = models.TextField(blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    google_maps_api_key = models.CharField(max_length=100, blank=True)
```

- [ ] **Step 4: Generate and apply migration**

Run:
```
python backend/manage.py makemigrations landing_cms
python backend/manage.py migrate landing_cms
```
Expected: migration `0001_initial.py` created, applied successfully.

- [ ] **Step 5: Run tests, expect green**

Run:
```
python backend/manage.py test landing_cms.tests.test_models -v 2
```
Expected: 5 tests OK.

- [ ] **Step 6: Commit**

```
git add backend/landing_cms/models.py backend/landing_cms/migrations/ backend/landing_cms/tests/test_models.py
git commit -m "feat(landing_cms): singleton models Hero/About/SiteSettings"
```

---

## Task 4 — Models: ordered lists (Feature, TeamMember, Location)

**Files:**
- Modify: `backend/landing_cms/models.py`
- Modify: `backend/landing_cms/tests/test_models.py`
- Create: migration `0002_ordered_models.py` (generated)

**Interfaces:**
- Produces:
  - `Feature(icon, title_es, title_en, description_es, description_en, order, is_active)` — `Meta.ordering = ["order", "pk"]`.
  - `TeamMember(photo, name, role_es, role_en, bio_es, bio_en, order, is_active)`.
  - `Location(name, address, lat, lng, phone, email, hours_es, hours_en, photo, description_es, description_en, type, order, is_active)`. `type` choices `SUCURSAL/OFICINA/CENTRO`.

- [ ] **Step 1: Append failing tests**

Append to `backend/landing_cms/tests/test_models.py`:
```python
from landing_cms.models import Feature, TeamMember, Location


class FeatureTests(TestCase):
    def test_default_order(self):
        f1 = Feature.objects.create(icon="ticket", title_es="A", title_en="A", order=2)
        f2 = Feature.objects.create(icon="user", title_es="B", title_en="B", order=1)
        ids = list(Feature.objects.values_list("pk", flat=True))
        self.assertEqual(ids, [f2.pk, f1.pk])


class LocationTests(TestCase):
    def test_create_with_type(self):
        loc = Location.objects.create(
            name="Sede", address="Calle 1", lat=19.4, lng=-99.1,
            type="OFICINA", order=1,
        )
        self.assertEqual(loc.type, "OFICINA")
```

- [ ] **Step 2: Run, expect ImportError**

Run:
```
python backend/manage.py test landing_cms.tests.test_models -v 2
```
Expected: ImportError for `Feature` / `Location`.

- [ ] **Step 3: Append models**

Append to `backend/landing_cms/models.py`:
```python
class _Ordered(models.Model):
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ["order", "pk"]


class Feature(_Ordered):
    icon = models.CharField(max_length=50)
    title_es = models.CharField(max_length=100)
    title_en = models.CharField(max_length=100)
    description_es = models.TextField(blank=True)
    description_en = models.TextField(blank=True)

    def __str__(self):
        return self.title_es or self.title_en


class TeamMember(_Ordered):
    photo = models.ImageField(
        upload_to="team/", blank=True, null=True,
        validators=[validate_image_file],
    )
    name = models.CharField(max_length=100)
    role_es = models.CharField(max_length=100, blank=True)
    role_en = models.CharField(max_length=100, blank=True)
    bio_es = models.TextField(blank=True)
    bio_en = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Location(_Ordered):
    class Type(models.TextChoices):
        SUCURSAL = "SUCURSAL", "Sucursal"
        OFICINA = "OFICINA", "Oficina"
        CENTRO = "CENTRO", "Centro de servicio"

    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    hours_es = models.CharField(max_length=200, blank=True)
    hours_en = models.CharField(max_length=200, blank=True)
    photo = models.ImageField(
        upload_to="locations/", blank=True, null=True,
        validators=[validate_image_file],
    )
    description_es = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.OFICINA)

    def __str__(self):
        return self.name
```

- [ ] **Step 4: Migrate**

Run:
```
python backend/manage.py makemigrations landing_cms
python backend/manage.py migrate landing_cms
```
Expected: `0002_*` created and applied.

- [ ] **Step 5: Run tests, expect green**

Run:
```
python backend/manage.py test landing_cms.tests.test_models -v 2
```
Expected: 7 tests OK.

- [ ] **Step 6: Commit**

```
git add backend/landing_cms/models.py backend/landing_cms/migrations/ backend/landing_cms/tests/test_models.py
git commit -m "feat(landing_cms): ordered models Feature/TeamMember/Location"
```

---

## Task 5 — Seed singletons (data migration)

**Files:**
- Create: `backend/landing_cms/migrations/0003_seed_singletons.py`

**Interfaces:**
- Produces: at app install, `HeroContent`, `AboutContent`, `SiteSettings` each have a single row with `pk=1` so the admin never sees "no row to edit."

- [ ] **Step 1: Create the data migration**

Create `backend/landing_cms/migrations/0003_seed_singletons.py`:
```python
from django.db import migrations


def seed(apps, schema_editor):
    Hero = apps.get_model("landing_cms", "HeroContent")
    About = apps.get_model("landing_cms", "AboutContent")
    Settings_ = apps.get_model("landing_cms", "SiteSettings")
    Hero.objects.update_or_create(pk=1, defaults={
        "title_es": "Soporte que no se hace esperar.",
        "title_en": "Support that won't keep you waiting.",
        "subtitle_es": "La plataforma de help-desk para tu equipo.",
        "subtitle_en": "The help-desk platform for your team.",
    })
    About.objects.update_or_create(pk=1, defaults={
        "mission_es": "Edita esta misión en el admin.",
        "mission_en": "Edit this mission from the admin.",
        "vision_es": "Edita esta visión en el admin.",
        "vision_en": "Edit this vision from the admin.",
    })
    Settings_.objects.update_or_create(pk=1, defaults={})


def unseed(apps, schema_editor):
    # leave data on rollback; nothing to do
    pass


class Migration(migrations.Migration):
    dependencies = [("landing_cms", "0002_ordered_models")]
    operations = [migrations.RunPython(seed, unseed)]
```

(Adjust dependency name if `makemigrations` produced a different filename in Task 4 — run `python backend/manage.py showmigrations landing_cms` to confirm.)

- [ ] **Step 2: Apply migration**

Run:
```
python backend/manage.py migrate landing_cms
```
Expected: `Applying landing_cms.0003_seed_singletons... OK`.

- [ ] **Step 3: Verify in shell**

Run:
```
python backend/manage.py shell -c "from landing_cms.models import HeroContent; print(HeroContent.objects.get_solo().title_es)"
```
Expected output: `Soporte que no se hace esperar.`

- [ ] **Step 4: Commit**

```
git add backend/landing_cms/migrations/0003_seed_singletons.py
git commit -m "feat(landing_cms): seed default singleton rows"
```

---

## Task 6 — Serializers

**Files:**
- Create: `backend/landing_cms/serializers.py`

**Interfaces:**
- Produces:
  - `HeroSerializer`, `AboutSerializer`, `SiteSettingsSerializer` — full model serializers.
  - `FeatureSerializer`, `TeamMemberSerializer`, `LocationSerializer` — full model serializers, photo accepts upload + returns absolute URL.
  - `ContactSerializer` — `name`, `email`, `subject`, `message`, `website` (honeypot, ignored).

- [ ] **Step 1: Implement serializers**

Create `backend/landing_cms/serializers.py`:
```python
from rest_framework import serializers
from .models import (
    HeroContent, AboutContent, SiteSettings,
    Feature, TeamMember, Location,
)


class HeroSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroContent
        exclude = ["id"]


class AboutSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutContent
        exclude = ["id"]


class SiteSettingsSerializer(serializers.ModelSerializer):
    logo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = SiteSettings
        exclude = ["id"]


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = "__all__"


class TeamMemberSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = TeamMember
        fields = "__all__"


class LocationSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=False, allow_null=True)
    lat = serializers.DecimalField(max_digits=9, decimal_places=6, coerce_to_string=False)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6, coerce_to_string=False)

    class Meta:
        model = Location
        fields = "__all__"


class ContactSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    subject = serializers.CharField(max_length=200)
    message = serializers.CharField(max_length=5000)
    website = serializers.CharField(required=False, allow_blank=True)  # honeypot
```

- [ ] **Step 2: Verify import works**

Run:
```
python backend/manage.py shell -c "from landing_cms.serializers import HeroSerializer, ContactSerializer; print('ok')"
```
Expected: `ok`.

- [ ] **Step 3: Commit**

```
git add backend/landing_cms/serializers.py
git commit -m "feat(landing_cms): serializers for CMS + contact"
```

---

## Task 7 — Public endpoints (read-only)

**Files:**
- Create: `backend/landing_cms/public_views.py`
- Create: `backend/landing_cms/public_urls.py`
- Modify: `backend/config/urls.py` (include public urls)
- Create: `backend/landing_cms/tests/test_public_endpoints.py`

**Interfaces:**
- Produces:
  - `GET /api/public/landing/hero/` → 200, body matches HeroSerializer
  - `GET /api/public/landing/about/` → 200
  - `GET /api/public/site-settings/` → 200
  - `GET /api/public/landing/features/` → 200, list, only `is_active=True`, ordered by `order`
  - `GET /api/public/landing/team/` → 200, list, only active, ordered
  - `GET /api/public/landing/locations/` → 200, list, only active, ordered
- All `AllowAny`. All set `Cache-Control: public, max-age=60`.

- [ ] **Step 1: Write failing tests**

Create `backend/landing_cms/tests/test_public_endpoints.py`:
```python
from django.test import TestCase
from rest_framework.test import APIClient
from landing_cms.models import Feature, TeamMember, Location


class PublicSingletonEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_hero_returns_seeded_singleton(self):
        r = self.client.get("/api/public/landing/hero/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("title_es", r.json())

    def test_about_ok(self):
        self.assertEqual(self.client.get("/api/public/landing/about/").status_code, 200)

    def test_settings_ok(self):
        self.assertEqual(self.client.get("/api/public/site-settings/").status_code, 200)


class PublicListEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        Feature.objects.create(icon="x", title_es="A", title_en="A", order=2, is_active=True)
        Feature.objects.create(icon="x", title_es="B", title_en="B", order=1, is_active=True)
        Feature.objects.create(icon="x", title_es="OFF", title_en="OFF", order=0, is_active=False)

    def test_features_lists_only_active_in_order(self):
        r = self.client.get("/api/public/landing/features/")
        self.assertEqual(r.status_code, 200)
        titles = [f["title_es"] for f in r.json()]
        self.assertEqual(titles, ["B", "A"])

    def test_locations_empty_ok(self):
        r = self.client.get("/api/public/landing/locations/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])
```

- [ ] **Step 2: Run, expect 404s**

Run:
```
python backend/manage.py test landing_cms.tests.test_public_endpoints -v 2
```
Expected: failures (404 status, because URLs not wired yet).

- [ ] **Step 3: Implement views**

Create `backend/landing_cms/public_views.py`:
```python
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    HeroContent, AboutContent, SiteSettings,
    Feature, TeamMember, Location,
)
from .serializers import (
    HeroSerializer, AboutSerializer, SiteSettingsSerializer,
    FeatureSerializer, TeamMemberSerializer, LocationSerializer,
)


def _cache(resp):
    resp["Cache-Control"] = "public, max-age=60"
    return resp


class _SingletonView(APIView):
    permission_classes = [AllowAny]
    model = None
    serializer_class = None

    def get(self, request):
        obj = self.model.objects.get_solo()
        return _cache(Response(self.serializer_class(obj, context={"request": request}).data))


class HeroPublicView(_SingletonView):
    model = HeroContent
    serializer_class = HeroSerializer


class AboutPublicView(_SingletonView):
    model = AboutContent
    serializer_class = AboutSerializer


class SiteSettingsPublicView(_SingletonView):
    model = SiteSettings
    serializer_class = SiteSettingsSerializer


class _ActiveListView(generics.ListAPIView):
    permission_classes = [AllowAny]

    def get_queryset(self):
        return self.queryset_model.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        return _cache(super().list(request, *args, **kwargs))


class FeatureListView(_ActiveListView):
    queryset_model = Feature
    serializer_class = FeatureSerializer


class TeamListView(_ActiveListView):
    queryset_model = TeamMember
    serializer_class = TeamMemberSerializer


class LocationListView(_ActiveListView):
    queryset_model = Location
    serializer_class = LocationSerializer
```

- [ ] **Step 4: Wire URLs**

Create `backend/landing_cms/public_urls.py`:
```python
from django.urls import path
from . import public_views as v

urlpatterns = [
    path("landing/hero/", v.HeroPublicView.as_view()),
    path("landing/about/", v.AboutPublicView.as_view()),
    path("site-settings/", v.SiteSettingsPublicView.as_view()),
    path("landing/features/", v.FeatureListView.as_view()),
    path("landing/team/", v.TeamListView.as_view()),
    path("landing/locations/", v.LocationListView.as_view()),
]
```

Modify `backend/config/urls.py`. In the `urlpatterns` list, before the existing `path("api/", include("tickets_t.urls"))` line, add:
```python
    path("api/public/", include("landing_cms.public_urls")),
```

- [ ] **Step 5: Run tests, expect green**

Run:
```
python backend/manage.py test landing_cms.tests.test_public_endpoints -v 2
```
Expected: 5 tests OK.

- [ ] **Step 6: Commit**

```
git add backend/landing_cms/public_views.py backend/landing_cms/public_urls.py backend/landing_cms/tests/test_public_endpoints.py backend/config/urls.py
git commit -m "feat(landing_cms): public read-only endpoints"
```

---

## Task 8 — Permission class IsAdminRole

**Files:**
- Create: `backend/landing_cms/permissions.py`

**Interfaces:**
- Produces: `landing_cms.permissions.IsAdminRole` — passes if `user.is_authenticated and (user.is_superuser or getattr(user, "role", None) == "ADMIN")`.

- [ ] **Step 1: Implement**

Create `backend/landing_cms/permissions.py`:
```python
from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    message = "Solo administradores."

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if u.is_superuser:
            return True
        return getattr(u, "role", None) == "ADMIN"
```

- [ ] **Step 2: Commit**

```
git add backend/landing_cms/permissions.py
git commit -m "feat(landing_cms): IsAdminRole permission"
```

---

## Task 9 — Admin endpoints (singletons PUT + ordered CRUD + reorder)

**Files:**
- Create: `backend/landing_cms/admin_views.py`
- Create: `backend/landing_cms/admin_urls.py`
- Modify: `backend/config/urls.py`
- Create: `backend/landing_cms/tests/test_admin_endpoints.py`

**Interfaces:**
- Produces:
  - `GET, PUT /api/admin/landing/hero/` — admin-only, returns/updates singleton
  - same for `/about/`, `/site-settings/`
  - `GET/POST/GET-PK/PUT-PK/PATCH-PK/DELETE-PK /api/admin/landing/features/[id]/`
  - same for `/team/` and `/locations/`
  - `POST /api/admin/landing/features/reorder/` body `{"ids": [3,1,2]}` → reassigns `order` 0..n-1 in that sequence; returns `204`. Same for `/team/reorder/` and `/locations/reorder/`.
- All require `IsAdminRole`.

- [ ] **Step 1: Failing tests**

Create `backend/landing_cms/tests/test_admin_endpoints.py`:
```python
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from landing_cms.models import Feature

User = get_user_model()


class _AdminAuthMixin:
    def _admin_client(self):
        u = User.objects.create_user(username="adm", password="x", role="ADMIN")
        u.is_superuser = True
        u.is_staff = True
        u.save()
        c = APIClient()
        c.force_authenticate(user=u)
        return c

    def _customer_client(self):
        u = User.objects.create_user(username="cu", password="x", role="CUSTOMER")
        c = APIClient()
        c.force_authenticate(user=u)
        return c


class HeroAdminTests(TestCase, _AdminAuthMixin):
    def test_get_ok(self):
        r = self._admin_client().get("/api/admin/landing/hero/")
        self.assertEqual(r.status_code, 200)

    def test_put_updates(self):
        r = self._admin_client().put(
            "/api/admin/landing/hero/",
            {"title_es": "Nuevo", "title_en": "New"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["title_es"], "Nuevo")

    def test_customer_forbidden(self):
        r = self._customer_client().get("/api/admin/landing/hero/")
        self.assertEqual(r.status_code, 403)


class FeatureAdminTests(TestCase, _AdminAuthMixin):
    def test_create_and_list(self):
        c = self._admin_client()
        r = c.post("/api/admin/landing/features/", {
            "icon": "x", "title_es": "A", "title_en": "A", "order": 0,
            "description_es": "", "description_en": "", "is_active": True,
        }, format="json")
        self.assertEqual(r.status_code, 201)
        r = c.get("/api/admin/landing/features/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 1)

    def test_reorder(self):
        c = self._admin_client()
        f1 = Feature.objects.create(icon="x", title_es="1", title_en="1", order=0)
        f2 = Feature.objects.create(icon="x", title_es="2", title_en="2", order=1)
        f3 = Feature.objects.create(icon="x", title_es="3", title_en="3", order=2)
        r = c.post("/api/admin/landing/features/reorder/",
                   {"ids": [f3.pk, f1.pk, f2.pk]}, format="json")
        self.assertEqual(r.status_code, 204)
        ordered = list(Feature.objects.values_list("pk", flat=True))
        self.assertEqual(ordered, [f3.pk, f1.pk, f2.pk])
```

- [ ] **Step 2: Run, expect failures**

Run:
```
python backend/manage.py test landing_cms.tests.test_admin_endpoints -v 2
```
Expected: 404s / import errors.

- [ ] **Step 3: Implement admin views**

Create `backend/landing_cms/admin_views.py`:
```python
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    HeroContent, AboutContent, SiteSettings,
    Feature, TeamMember, Location,
)
from .permissions import IsAdminRole
from .serializers import (
    HeroSerializer, AboutSerializer, SiteSettingsSerializer,
    FeatureSerializer, TeamMemberSerializer, LocationSerializer,
)


class _SingletonAdminView(APIView):
    permission_classes = [IsAdminRole]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    model = None
    serializer_class = None

    def get(self, request):
        obj = self.model.objects.get_solo()
        return Response(self.serializer_class(obj, context={"request": request}).data)

    def put(self, request):
        obj = self.model.objects.get_solo()
        ser = self.serializer_class(obj, data=request.data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class HeroAdminView(_SingletonAdminView):
    model = HeroContent
    serializer_class = HeroSerializer


class AboutAdminView(_SingletonAdminView):
    model = AboutContent
    serializer_class = AboutSerializer


class SiteSettingsAdminView(_SingletonAdminView):
    model = SiteSettings
    serializer_class = SiteSettingsSerializer


class _OrderedAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @action(detail=False, methods=["post"])
    def reorder(self, request):
        ids = request.data.get("ids", [])
        if not isinstance(ids, list):
            return Response({"detail": "ids must be a list"}, status=400)
        for idx, pk in enumerate(ids):
            self.queryset.filter(pk=pk).update(order=idx)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FeatureAdminViewSet(_OrderedAdminViewSet):
    queryset = Feature.objects.all()
    serializer_class = FeatureSerializer


class TeamAdminViewSet(_OrderedAdminViewSet):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer


class LocationAdminViewSet(_OrderedAdminViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
```

- [ ] **Step 4: Wire admin URLs**

Create `backend/landing_cms/admin_urls.py`:
```python
from django.urls import path
from rest_framework.routers import DefaultRouter
from . import admin_views as v

router = DefaultRouter()
router.register("features", v.FeatureAdminViewSet, basename="adm-features")
router.register("team", v.TeamAdminViewSet, basename="adm-team")
router.register("locations", v.LocationAdminViewSet, basename="adm-locations")

urlpatterns = [
    path("hero/", v.HeroAdminView.as_view()),
    path("about/", v.AboutAdminView.as_view()),
] + router.urls
```

Note: site-settings lives under `/api/admin/site-settings/`, not under `landing/`, to stay consistent with the public URL. Add it in `config/urls.py` instead — see Step 5.

Modify `backend/config/urls.py`. Add two new lines in `urlpatterns` (next to the public include):
```python
    path("api/admin/landing/", include("landing_cms.admin_urls")),
    path("api/admin/site-settings/", v_settings_admin),
```

At the top of `backend/config/urls.py` add:
```python
from landing_cms.admin_views import SiteSettingsAdminView
v_settings_admin = SiteSettingsAdminView.as_view()
```

- [ ] **Step 5: Run tests, expect green**

Run:
```
python backend/manage.py test landing_cms.tests.test_admin_endpoints -v 2
```
Expected: 5 tests OK.

- [ ] **Step 6: Commit**

```
git add backend/landing_cms/admin_views.py backend/landing_cms/admin_urls.py backend/landing_cms/tests/test_admin_endpoints.py backend/config/urls.py
git commit -m "feat(landing_cms): admin endpoints + reorder"
```

---

## Task 10 — Public contact endpoint (creates Ticket + User)

**Files:**
- Create: `backend/landing_cms/contact_view.py`
- Modify: `backend/landing_cms/public_urls.py`
- Create: `backend/landing_cms/tests/test_contact_endpoint.py`

**Interfaces:**
- Produces: `POST /api/public/contact/` body `{name, email, subject, message, website?}`.
  - 201 with body `{"ticket_reference": "ALS-YYYYMMDD-NNNNNN"}` on success.
  - 400 if validation fails.
  - 200 with `{"ok": true}` if honeypot `website` is non-empty (discarded silently).
  - Creates `User` (role CUSTOMER, unusable password) if email not registered; reuses existing user otherwise.
  - Creates `Ticket` (priority MEDIUM, state OPEN) and a `TicketMessage` with the full message.

- [ ] **Step 1: Failing tests**

Create `backend/landing_cms/tests/test_contact_endpoint.py`:
```python
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from tickets_t.models import Ticket, TicketMessage

User = get_user_model()


class ContactEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/public/contact/"

    def test_creates_user_and_ticket(self):
        r = self.client.post(self.url, {
            "name": "Ana",
            "email": "ana@example.com",
            "subject": "Cotización",
            "message": "Quiero información.",
        }, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertIn("ticket_reference", r.json())
        self.assertTrue(User.objects.filter(email="ana@example.com").exists())
        t = Ticket.objects.get(reference=r.json()["ticket_reference"])
        self.assertEqual(t.titulo, "Cotización")
        self.assertEqual(t.prioridad, "MEDIUM")
        self.assertEqual(t.estado, "OPEN")
        self.assertEqual(TicketMessage.objects.filter(ticket=t).count(), 1)

    def test_reuses_existing_user(self):
        User.objects.create_user(username="ana@example.com",
                                 email="ana@example.com", password="x",
                                 role="CUSTOMER")
        self.client.post(self.url, {
            "name": "Ana", "email": "ana@example.com",
            "subject": "S", "message": "M",
        }, format="json")
        self.assertEqual(User.objects.filter(email="ana@example.com").count(), 1)

    def test_honeypot_short_circuits(self):
        r = self.client.post(self.url, {
            "name": "Bot", "email": "bot@example.com",
            "subject": "S", "message": "M", "website": "spam.com",
        }, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_validation_error(self):
        r = self.client.post(self.url, {"name": "Ana"}, format="json")
        self.assertEqual(r.status_code, 400)
```

- [ ] **Step 2: Run, expect 404 / failures**

Run:
```
python backend/manage.py test landing_cms.tests.test_contact_endpoint -v 2
```
Expected: failures.

- [ ] **Step 3: Implement contact view**

Create `backend/landing_cms/contact_view.py`:
```python
from datetime import datetime
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets_t.models import Ticket, TicketMessage
from .serializers import ContactSerializer

User = get_user_model()


def _next_reference():
    prefix = "ALS-" + datetime.utcnow().strftime("%Y%m%d") + "-"
    last = (
        Ticket.objects.select_for_update()
        .filter(reference__startswith=prefix)
        .order_by("-reference")
        .first()
    )
    n = int(last.reference.split("-")[-1]) + 1 if last else 1
    return f"{prefix}{n:06d}"


from rest_framework.throttling import ScopedRateThrottle


class ContactView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "contact"

    @transaction.atomic
    def post(self, request):
        ser = ContactSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        if data.get("website"):
            return Response({"ok": True})

        user = User.objects.filter(email=data["email"]).first()
        if user is None:
            user = User(
                username=data["email"],
                email=data["email"],
                first_name=data["name"][:30],
                role="CUSTOMER",
            )
            user.set_unusable_password()
            user.save()

        ticket = Ticket.objects.create(
            reference=_next_reference(),
            titulo=data["subject"],
            descripcion=data["message"],
            prioridad="MEDIUM",
            estado="OPEN",
            creado_por=user,
        )
        TicketMessage.objects.create(
            ticket=ticket, sender=user, content=data["message"],
        )
        return Response({"ticket_reference": ticket.reference},
                        status=status.HTTP_201_CREATED)
```

- [ ] **Step 4: Wire URL**

Modify `backend/landing_cms/public_urls.py`. Add import and route:
```python
from .contact_view import ContactView
```
Append to `urlpatterns`:
```python
    path("contact/", ContactView.as_view()),
```

- [ ] **Step 5: Run tests, expect green**

Run:
```
python backend/manage.py test landing_cms.tests.test_contact_endpoint -v 2
```
Expected: 4 tests OK.

- [ ] **Step 6: Commit**

```
git add backend/landing_cms/contact_view.py backend/landing_cms/public_urls.py backend/landing_cms/tests/test_contact_endpoint.py
git commit -m "feat(landing_cms): public contact endpoint creates Ticket + User"
```

---

## Task 11 — Django admin registration

**Files:**
- Create: `backend/landing_cms/admin.py`

**Interfaces:**
- Produces: all 6 models visible under `/admin/landing_cms/` for fallback editing.

- [ ] **Step 1: Implement admin**

Create `backend/landing_cms/admin.py`:
```python
from django.contrib import admin
from .models import (
    HeroContent, AboutContent, SiteSettings,
    Feature, TeamMember, Location,
)


@admin.register(HeroContent)
class HeroAdmin(admin.ModelAdmin):
    pass


@admin.register(AboutContent)
class AboutAdmin(admin.ModelAdmin):
    pass


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    pass


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ("title_es", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "role_es", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "order", "is_active")
    list_editable = ("order", "is_active")
```

- [ ] **Step 2: Verify with check**

Run:
```
python backend/manage.py check
```
Expected: no issues.

- [ ] **Step 3: Commit**

```
git add backend/landing_cms/admin.py
git commit -m "feat(landing_cms): register models in Django admin"
```

---

## Task 12 — Frontend: install dependencies

**Files:**
- Modify: `frontend/package.json`

**Interfaces:**
- Produces: new deps installed: `vue-i18n@^9`, `gsap@^3`, `@vueuse/core@^11`, `vuedraggable@^4`, `@googlemaps/js-api-loader@^1`.

- [ ] **Step 1: Install**

Run (from `frontend/`):
```
npm install vue-i18n@9 gsap @vueuse/core vuedraggable @googlemaps/js-api-loader
```

- [ ] **Step 2: Verify package.json**

Run:
```
cat frontend/package.json
```
Expected: the five new packages listed under `dependencies`.

- [ ] **Step 3: Commit**

```
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(frontend): add landing/CMS dependencies"
```

---

## Task 13 — vue-i18n + locale store + pick helper

**Files:**
- Create: `frontend/src/i18n/index.js`
- Create: `frontend/src/i18n/locales/es.json`
- Create: `frontend/src/i18n/locales/en.json`
- Create: `frontend/src/stores/locale.store.js`
- Create: `frontend/src/composables/usePick.js`
- Modify: `frontend/src/main.js`

**Interfaces:**
- Produces:
  - i18n instance with locales `es` (default) and `en`.
  - `useLocaleStore()` with state `{ locale }`, action `setLocale(code)`, persists to `localStorage` key `"locale"`.
  - `usePick()` returns a function `pick(obj, field)` → `obj[`${field}_${currentLocale}`]`.

- [ ] **Step 1: i18n setup**

Create `frontend/src/i18n/locales/es.json`:
```json
{
  "nav": { "features": "Funcionalidades", "about": "Nosotros", "locations": "Ubicaciones", "contact": "Contacto", "signin": "Iniciar sesión" },
  "contact": {
    "title": "Contáctanos",
    "name": "Nombre", "email": "Email", "subject": "Asunto", "message": "Mensaje",
    "send": "Enviar mensaje", "success": "Recibimos tu mensaje. Referencia: {ref}",
    "error": "No se pudo enviar. Intenta de nuevo."
  },
  "loading": "Cargando..."
}
```

Create `frontend/src/i18n/locales/en.json`:
```json
{
  "nav": { "features": "Features", "about": "About", "locations": "Locations", "contact": "Contact", "signin": "Sign in" },
  "contact": {
    "title": "Get in touch",
    "name": "Name", "email": "Email", "subject": "Subject", "message": "Message",
    "send": "Send message", "success": "Got your message. Reference: {ref}",
    "error": "Failed to send. Please try again."
  },
  "loading": "Loading..."
}
```

Create `frontend/src/i18n/index.js`:
```js
import { createI18n } from "vue-i18n";
import es from "./locales/es.json";
import en from "./locales/en.json";

const saved = typeof localStorage !== "undefined" ? localStorage.getItem("locale") : null;

export const i18n = createI18n({
  legacy: false,
  locale: saved || "es",
  fallbackLocale: "es",
  messages: { es, en },
});
```

- [ ] **Step 2: Register in main**

Modify `frontend/src/main.js`:
```js
import { createApp } from "vue";
import "./style.css";
import App from "./App.vue";
import { createPinia } from "pinia";
import router from "./router";
import { i18n } from "./i18n";

createApp(App)
  .use(createPinia())
  .use(router)
  .use(i18n)
  .mount("#app");
```

- [ ] **Step 3: Locale store**

Create `frontend/src/stores/locale.store.js`:
```js
import { defineStore } from "pinia";
import { i18n } from "../i18n";

export const useLocaleStore = defineStore("locale", {
  state: () => ({ locale: i18n.global.locale.value }),
  actions: {
    setLocale(code) {
      if (code !== "es" && code !== "en") return;
      this.locale = code;
      i18n.global.locale.value = code;
      try { localStorage.setItem("locale", code); } catch (_) {}
    },
  },
});
```

- [ ] **Step 4: usePick composable**

Create `frontend/src/composables/usePick.js`:
```js
import { computed } from "vue";
import { useLocaleStore } from "../stores/locale.store";

export function usePick() {
  const store = useLocaleStore();
  const locale = computed(() => store.locale);
  function pick(obj, field) {
    if (!obj) return "";
    return obj[`${field}_${locale.value}`] ?? "";
  }
  return { pick, locale };
}
```

- [ ] **Step 5: Smoke test in browser**

Run (from `frontend/`):
```
npm run dev
```
Then add to any visible component a temporary `<p>{{ $t("nav.signin") }}</p>` and confirm in the browser it renders "Iniciar sesión". Revert the change.

- [ ] **Step 6: Commit**

```
git add frontend/src/i18n frontend/src/stores/locale.store.js frontend/src/composables/usePick.js frontend/src/main.js
git commit -m "feat(frontend): i18n ES/EN + locale store + pick helper"
```

---

## Task 14 — Landing API client + landing store

**Files:**
- Create: `frontend/src/api/landing.api.js`
- Create: `frontend/src/stores/landing.store.js`

**Interfaces:**
- Produces:
  - `landing.api.js` exports `getHero()`, `getAbout()`, `getFeatures()`, `getTeam()`, `getLocations()`, `getSiteSettings()`, `postContact(payload)`. All return raw axios responses (`.data`).
  - `useLandingStore()` with state `{ hero, about, features, team, locations, settings, loaded, error }` and action `loadAll()` that issues `Promise.all` over the 6 GETs and stores results.

- [ ] **Step 1: API client**

Create `frontend/src/api/landing.api.js`:
```js
import { http } from "./http";

const P = "/api/public";

export const landingApi = {
  getHero: () => http.get(`${P}/landing/hero/`).then(r => r.data),
  getAbout: () => http.get(`${P}/landing/about/`).then(r => r.data),
  getFeatures: () => http.get(`${P}/landing/features/`).then(r => r.data),
  getTeam: () => http.get(`${P}/landing/team/`).then(r => r.data),
  getLocations: () => http.get(`${P}/landing/locations/`).then(r => r.data),
  getSiteSettings: () => http.get(`${P}/site-settings/`).then(r => r.data),
  postContact: (payload) => http.post(`${P}/contact/`, payload).then(r => r.data),
};
```

- [ ] **Step 2: Store**

Create `frontend/src/stores/landing.store.js`:
```js
import { defineStore } from "pinia";
import { landingApi } from "../api/landing.api";

export const useLandingStore = defineStore("landing", {
  state: () => ({
    hero: null,
    about: null,
    features: [],
    team: [],
    locations: [],
    settings: null,
    loaded: false,
    error: null,
  }),
  actions: {
    async loadAll() {
      this.error = null;
      try {
        const [hero, about, features, team, locations, settings] = await Promise.all([
          landingApi.getHero().catch(() => null),
          landingApi.getAbout().catch(() => null),
          landingApi.getFeatures().catch(() => []),
          landingApi.getTeam().catch(() => []),
          landingApi.getLocations().catch(() => []),
          landingApi.getSiteSettings().catch(() => null),
        ]);
        this.hero = hero;
        this.about = about;
        this.features = features;
        this.team = team;
        this.locations = locations;
        this.settings = settings;
      } catch (e) {
        this.error = e;
      } finally {
        this.loaded = true;
      }
    },
  },
});
```

- [ ] **Step 3: Commit**

```
git add frontend/src/api/landing.api.js frontend/src/stores/landing.store.js
git commit -m "feat(frontend): landing API client + store"
```

---

## Task 15 — PublicLayout + AdminLayout

**Files:**
- Create: `frontend/src/layouts/PublicLayout.vue`
- Create: `frontend/src/layouts/AdminLayout.vue`
- Create: `frontend/src/components/public/PublicHeader.vue`
- Create: `frontend/src/components/public/PublicFooter.vue`

**Interfaces:**
- Produces:
  - `<PublicLayout>` — header sticky (logo, anchor nav, language toggle, "Iniciar sesión"), `<router-view/>`, footer.
  - `<AdminLayout>` — sidebar with sections "Tickets" (link to existing dashboard) and "Sitio web" (3 links to CMS screens), `<router-view/>`. Used only for new `/admin/sitio/*` routes; the existing dashboard routes keep their current layout.

- [ ] **Step 1: PublicHeader**

Create `frontend/src/components/public/PublicHeader.vue`:
```vue
<template>
  <header class="ph">
    <div class="ph-inner">
      <a href="#top" class="brand">
        <span class="mark">AS</span>
        <span class="name">AllSafe</span>
      </a>
      <nav class="nav">
        <a href="#features">{{ $t("nav.features") }}</a>
        <a href="#about">{{ $t("nav.about") }}</a>
        <a href="#locations">{{ $t("nav.locations") }}</a>
        <a href="#contacto">{{ $t("nav.contact") }}</a>
      </nav>
      <div class="actions">
        <button class="lang" @click="toggle">{{ locale === "es" ? "ES" : "EN" }}</button>
        <router-link to="/login" class="btn-signin">{{ $t("nav.signin") }}</router-link>
      </div>
    </div>
  </header>
</template>

<script setup>
import { useLocaleStore } from "../../stores/locale.store";
import { storeToRefs } from "pinia";
const store = useLocaleStore();
const { locale } = storeToRefs(store);
function toggle() { store.setLocale(locale.value === "es" ? "en" : "es"); }
</script>

<style scoped>
.ph { position: sticky; top: 0; background: var(--surface); border-bottom: 1px solid var(--border); z-index: 50; }
.ph-inner { max-width: 1180px; margin: 0 auto; padding: 14px 24px; display: flex; align-items: center; justify-content: space-between; }
.brand { display: flex; align-items: center; gap: 10px; text-decoration: none; color: var(--text); }
.mark { width: 32px; height: 32px; background: var(--accent); color: var(--accent-fg); border-radius: 8px; display: grid; place-items: center; font-weight: 700; font-size: 12px; }
.name { font-weight: 600; font-size: 15px; }
.nav { display: flex; gap: 28px; }
.nav a { color: var(--text-2); text-decoration: none; font-size: 14px; }
.nav a:hover { color: var(--text); }
.actions { display: flex; align-items: center; gap: 12px; }
.lang { border: 1px solid var(--border); padding: 6px 10px; border-radius: var(--r-sm); background: transparent; color: var(--text-2); font-size: 12px; }
.btn-signin { background: var(--accent); color: var(--accent-fg); padding: 8px 16px; border-radius: var(--r); font-size: 13px; font-weight: 600; text-decoration: none; }
</style>
```

- [ ] **Step 2: PublicFooter**

Create `frontend/src/components/public/PublicFooter.vue`:
```vue
<template>
  <footer class="pf">
    <div class="pf-inner">
      <span>© {{ year }} AllSafe</span>
      <nav>
        <a href="#features">{{ $t("nav.features") }}</a>
        <a href="#about">{{ $t("nav.about") }}</a>
        <a href="#contacto">{{ $t("nav.contact") }}</a>
      </nav>
    </div>
  </footer>
</template>

<script setup>
const year = new Date().getFullYear();
</script>

<style scoped>
.pf { border-top: 1px solid var(--border); padding: 24px; color: var(--text-3); font-size: 13px; margin-top: 60px; }
.pf-inner { max-width: 1180px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }
.pf nav a { color: var(--text-3); text-decoration: none; margin-left: 20px; }
.pf nav a:hover { color: var(--text); }
</style>
```

- [ ] **Step 3: PublicLayout**

Create `frontend/src/layouts/PublicLayout.vue`:
```vue
<template>
  <div id="top" class="public-shell">
    <PublicHeader />
    <main><router-view /></main>
    <PublicFooter />
  </div>
</template>

<script setup>
import PublicHeader from "../components/public/PublicHeader.vue";
import PublicFooter from "../components/public/PublicFooter.vue";
</script>

<style scoped>
.public-shell { min-height: 100vh; background: var(--bg); color: var(--text); }
</style>
```

- [ ] **Step 4: AdminLayout**

Create `frontend/src/layouts/AdminLayout.vue`:
```vue
<template>
  <div class="adm">
    <aside class="adm-side">
      <div class="brand">AllSafe</div>
      <nav>
        <div class="group">Tickets</div>
        <router-link to="/admin">Dashboard</router-link>

        <div class="group">Sitio web</div>
        <router-link to="/admin/sitio/contenido">Contenido</router-link>
        <router-link to="/admin/sitio/equipo">Equipo</router-link>
        <router-link to="/admin/sitio/ubicaciones">Ubicaciones</router-link>
      </nav>
    </aside>
    <section class="adm-main"><router-view /></section>
  </div>
</template>

<style scoped>
.adm { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }
.adm-side { background: var(--surface); border-right: 1px solid var(--border); padding: 20px 16px; }
.adm-side .brand { font-weight: 700; margin-bottom: 24px; }
.adm-side .group { font-size: 11px; text-transform: uppercase; color: var(--text-3); margin: 16px 0 6px; letter-spacing: .5px; }
.adm-side nav a { display: block; padding: 8px 10px; color: var(--text-2); text-decoration: none; border-radius: var(--r-sm); font-size: 14px; }
.adm-side nav a:hover, .adm-side nav a.router-link-active { background: var(--surface-2); color: var(--text); }
.adm-main { padding: 28px 32px; }
</style>
```

- [ ] **Step 5: Commit**

```
git add frontend/src/layouts/ frontend/src/components/public/PublicHeader.vue frontend/src/components/public/PublicFooter.vue
git commit -m "feat(frontend): public + admin layouts"
```

---

## Task 16 — Router rework

**Files:**
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/views/LoginView.vue` (no change to logic; only ensure it does not conflict with PublicLayout — currently it has its own background)

**Interfaces:**
- Produces: route table:
  - `/` → `PublicLayout` > `LandingHome`
  - `/login` → `PublicLayout` > `LoginView`
  - `/cliente`, `/tecnico`, `/tecnico/inbox`, `/admin` → unchanged (current dashboards keep their existing chrome)
  - `/admin/sitio/contenido` → `AdminLayout` > `AdminContent`
  - `/admin/sitio/equipo` → `AdminLayout` > `AdminTeam`
  - `/admin/sitio/ubicaciones` → `AdminLayout` > `AdminLocations`
- Guard: routes with `meta.public` skip auth. Existing role-based redirects unchanged.

- [ ] **Step 1: Rewrite router**

Replace `frontend/src/router/index.js` with:
```js
import { createRouter, createWebHistory } from "vue-router";

import PublicLayout from "../layouts/PublicLayout.vue";
import AdminLayout from "../layouts/AdminLayout.vue";

import LoginView from "../views/LoginView.vue";
import LandingHome from "../views/public/LandingHome.vue";

import ClientDashboard from "../views/dashboards/ClientDashboard.vue";
import TechnicianDashboard from "../views/dashboards/TechnicianDashboard.vue";
import AdminDashboard from "../views/dashboards/AdminDashboard.vue";
import TechnicianInboxView from "../views/dashboards/TechnicianInboxView.vue";

import AdminContent from "../views/admin/site/AdminContent.vue";
import AdminTeam from "../views/admin/site/AdminTeam.vue";
import AdminLocations from "../views/admin/site/AdminLocations.vue";

import { useAuthStore } from "../stores/auth.store";

const routes = [
  {
    path: "/",
    component: PublicLayout,
    children: [
      { path: "", name: "landing", component: LandingHome, meta: { public: true } },
      { path: "login", name: "login", component: LoginView, meta: { public: true } },
    ],
  },
  { path: "/cliente", name: "cliente", component: ClientDashboard, meta: { role: "CUSTOMER" } },
  { path: "/tecnico", name: "tecnico", component: TechnicianDashboard, meta: { role: "AGENT" } },
  { path: "/tecnico/inbox", name: "tecnico-inbox", component: TechnicianInboxView, meta: { role: "AGENT" } },
  { path: "/admin", name: "admin", component: AdminDashboard, meta: { role: "ADMIN" } },
  {
    path: "/admin/sitio",
    component: AdminLayout,
    children: [
      { path: "contenido", name: "admin-content", component: AdminContent, meta: { role: "ADMIN" } },
      { path: "equipo", name: "admin-team", component: AdminTeam, meta: { role: "ADMIN" } },
      { path: "ubicaciones", name: "admin-locations", component: AdminLocations, meta: { role: "ADMIN" } },
    ],
  },
];

const router = createRouter({ history: createWebHistory(), routes });

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (to.meta?.public) return true;
  if (to.name === "login") return true;

  if (!auth.loaded) await auth.loadMe();
  if (!auth.user) return { name: "login" };

  const required = to.meta?.role;
  if (required === "ADMIN" && !auth.user.is_superuser) return auth.redirectByRole();
  if (required === "AGENT" && !auth.user.is_staff) return auth.redirectByRole();
  if (required === "CUSTOMER" && (auth.user.is_staff || auth.user.is_superuser)) {
    return auth.redirectByRole();
  }
  return true;
});

export default router;
```

- [ ] **Step 2: Adjust LoginView if it breaks**

Run `npm run dev`, navigate to `/login`. If the header shows double brand (login already has its own), remove from `frontend/src/views/LoginView.vue` the `.login-brand` block to avoid duplication. The page still works because the PublicLayout header shows the brand.

- [ ] **Step 3: Commit**

```
git add frontend/src/router/index.js frontend/src/views/LoginView.vue
git commit -m "feat(frontend): public/admin layouts + new routes"
```

---

## Task 17 — Landing skeleton page + loader

**Files:**
- Create: `frontend/src/views/public/LandingHome.vue`
- Create: `frontend/src/composables/useScrollReveal.js`

**Interfaces:**
- Produces: `LandingHome.vue` that calls `useLandingStore().loadAll()` on mount and renders 5 section placeholders (one per: hero, features, about, locations, contact). Shows skeleton boxes while `loaded === false`.
- `useScrollReveal(refOrSelector)` — uses GSAP + ScrollTrigger to animate the target with `opacity:0,y:24 → 1,0` when entering viewport. Respects `prefers-reduced-motion`.

- [ ] **Step 1: useScrollReveal**

Create `frontend/src/composables/useScrollReveal.js`:
```js
import { onMounted, onBeforeUnmount } from "vue";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

export function useScrollReveal(getEl) {
  const reduced = typeof window !== "undefined"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let st;

  onMounted(() => {
    if (reduced) return;
    const el = typeof getEl === "function" ? getEl() : getEl;
    if (!el) return;
    gsap.from(el, {
      opacity: 0,
      y: 24,
      duration: 0.6,
      ease: "power2.out",
      scrollTrigger: { trigger: el, start: "top 85%" },
    });
  });

  onBeforeUnmount(() => st && st.kill());
}
```

- [ ] **Step 2: LandingHome skeleton**

Create `frontend/src/views/public/LandingHome.vue`:
```vue
<template>
  <div class="landing">
    <section v-if="!store.loaded" class="skeleton">
      <div class="sk" style="height:360px"></div>
      <div class="sk" style="height:200px"></div>
      <div class="sk" style="height:300px"></div>
    </section>

    <template v-else>
      <HeroSection :hero="store.hero" />
      <FeaturesSection :features="store.features" />
      <AboutSection :about="store.about" :team="store.team" />
      <LocationsSection :locations="store.locations" :settings="store.settings" />
      <ContactSection />
    </template>
  </div>
</template>

<script setup>
import { onMounted } from "vue";
import { useLandingStore } from "../../stores/landing.store";

import HeroSection from "../../components/public/HeroSection.vue";
import FeaturesSection from "../../components/public/FeaturesSection.vue";
import AboutSection from "../../components/public/AboutSection.vue";
import LocationsSection from "../../components/public/LocationsSection.vue";
import ContactSection from "../../components/public/ContactSection.vue";

const store = useLandingStore();
onMounted(() => { if (!store.loaded) store.loadAll(); });
</script>

<style scoped>
.landing { max-width: 1180px; margin: 0 auto; padding: 32px 24px; }
.skeleton { display: flex; flex-direction: column; gap: 24px; }
.sk { background: var(--surface-2); border-radius: var(--r-lg); }
</style>
```

- [ ] **Step 3: Stub the 5 section components so the page renders**

Create each of the 5 files with a placeholder `<template><section class="placeholder">…</section></template>` so `npm run dev` does not crash. They get fleshed out in Tasks 18–22.

Create `frontend/src/components/public/HeroSection.vue`, `FeaturesSection.vue`, `AboutSection.vue`, `LocationsSection.vue`, `ContactSection.vue` — each with the minimal template:
```vue
<template><section class="ph"><p>WIP</p></section></template>
<style scoped>.ph{padding:48px 0}</style>
```

- [ ] **Step 4: Smoke test**

Run `npm run dev`, open `/`. Expect to see the AllSafe header, the WIP placeholders, the footer. Then refresh — the skeleton flashes briefly, then content swaps in (still WIP boxes).

- [ ] **Step 5: Commit**

```
git add frontend/src/views/public frontend/src/composables/useScrollReveal.js frontend/src/components/public
git commit -m "feat(frontend): landing skeleton + section stubs"
```

---

## Task 18 — HeroSection

**Files:**
- Modify: `frontend/src/components/public/HeroSection.vue`

**Interfaces:**
- Consumes: prop `hero` (object) from store; `usePick` for i18n; `useScrollReveal` for entrance animation.

- [ ] **Step 1: Implement**

Replace `frontend/src/components/public/HeroSection.vue` with:
```vue
<template>
  <section ref="root" class="hero">
    <h1 class="title">{{ pick(hero, "title") || "AllSafe" }}</h1>
    <p class="subtitle">{{ pick(hero, "subtitle") }}</p>
    <div class="ctas">
      <a :href="hero?.primary_cta_url || '/login'" class="cta primary">
        {{ pick(hero, "primary_cta_label") || $t("nav.signin") }}
      </a>
      <a :href="hero?.secondary_cta_url || '#contacto'" class="cta ghost">
        {{ pick(hero, "secondary_cta_label") }}
      </a>
    </div>
  </section>
</template>

<script setup>
import { ref } from "vue";
import { usePick } from "../../composables/usePick";
import { useScrollReveal } from "../../composables/useScrollReveal";

defineProps({ hero: { type: Object, default: null } });

const { pick } = usePick();
const root = ref(null);
useScrollReveal(() => root.value);
</script>

<style scoped>
.hero { padding: 96px 0 64px; text-align: center; }
.title { font-size: clamp(36px, 6vw, 64px); font-weight: 700; letter-spacing: -0.02em; margin: 0 0 16px; }
.subtitle { font-size: 18px; color: var(--text-2); max-width: 640px; margin: 0 auto 28px; }
.ctas { display: flex; justify-content: center; gap: 12px; }
.cta { padding: 12px 22px; border-radius: var(--r); font-weight: 600; font-size: 14px; text-decoration: none; transition: opacity .15s; }
.cta.primary { background: var(--accent); color: var(--accent-fg); }
.cta.ghost { border: 1px solid var(--border); color: var(--text); }
.cta:hover { opacity: .9; }
</style>
```

- [ ] **Step 2: Verify in browser**

Run `npm run dev`. Open `/`. Confirm the seeded `Soporte que no se hace esperar.` renders, and that the CTAs appear. Toggle EN in the header — title should switch to English.

- [ ] **Step 3: Commit**

```
git add frontend/src/components/public/HeroSection.vue
git commit -m "feat(landing): hero section with i18n + reveal"
```

---

## Task 19 — FeaturesSection

**Files:**
- Modify: `frontend/src/components/public/FeaturesSection.vue`

**Interfaces:**
- Consumes: prop `features` (array).

- [ ] **Step 1: Implement**

Replace `frontend/src/components/public/FeaturesSection.vue` with:
```vue
<template>
  <section id="features" ref="root" class="features">
    <h2 class="title">{{ $t("nav.features") }}</h2>
    <div class="grid">
      <article v-for="f in features" :key="f.id" class="card">
        <i :class="`ti ti-${f.icon || 'sparkles'}`" aria-hidden="true"></i>
        <h3>{{ pick(f, "title") }}</h3>
        <p>{{ pick(f, "description") }}</p>
      </article>
      <p v-if="!features.length" class="empty">{{ $t("loading") }}</p>
    </div>
  </section>
</template>

<script setup>
import { ref } from "vue";
import { usePick } from "../../composables/usePick";
import { useScrollReveal } from "../../composables/useScrollReveal";

defineProps({ features: { type: Array, default: () => [] } });
const { pick } = usePick();
const root = ref(null);
useScrollReveal(() => root.value);
</script>

<style scoped>
.features { padding: 64px 0; }
.title { text-align: center; font-size: 32px; margin: 0 0 36px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; }
.card { padding: 24px; border: 1px solid var(--border); border-radius: var(--r-lg); background: var(--surface); }
.card i { font-size: 24px; color: var(--accent); }
.card h3 { font-size: 16px; margin: 12px 0 6px; }
.card p { color: var(--text-2); font-size: 14px; margin: 0; }
.empty { text-align: center; color: var(--text-3); grid-column: 1/-1; }
</style>
```

Tabler icons are not yet loaded in the public app. If the icons don't render, add the CDN to `frontend/index.html` head:
```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/3.10.0/tabler-icons.min.css">
```

- [ ] **Step 2: Seed sample features in Django shell**

Run:
```
python backend/manage.py shell -c "from landing_cms.models import Feature; Feature.objects.create(icon='ticket', title_es='Tickets', title_en='Tickets', description_es='Captura y seguimiento.', description_en='Capture and track.', order=0); Feature.objects.create(icon='messages', title_es='Chat en vivo', title_en='Live chat', description_es='Respuestas inmediatas.', description_en='Real-time replies.', order=1)"
```

- [ ] **Step 3: Verify**

Refresh `/`. The Features section shows 2 cards.

- [ ] **Step 4: Commit**

```
git add frontend/src/components/public/FeaturesSection.vue frontend/index.html
git commit -m "feat(landing): features section + tabler icons"
```

---

## Task 20 — AboutSection (mission/vision + team grid)

**Files:**
- Modify: `frontend/src/components/public/AboutSection.vue`

**Interfaces:**
- Consumes: props `about` (object), `team` (array).

- [ ] **Step 1: Implement**

Replace `frontend/src/components/public/AboutSection.vue` with:
```vue
<template>
  <section id="about" ref="root" class="about">
    <h2 class="title">{{ $t("nav.about") }}</h2>
    <div class="mv">
      <div class="card">
        <h3>Misión</h3>
        <p>{{ pick(about, "mission") }}</p>
      </div>
      <div class="card">
        <h3>Visión</h3>
        <p>{{ pick(about, "vision") }}</p>
      </div>
    </div>
    <div v-if="team.length" class="team">
      <article v-for="m in team" :key="m.id" class="member">
        <img v-if="m.photo" :src="m.photo" :alt="m.name" />
        <div v-else class="avatar">{{ initials(m.name) }}</div>
        <p class="name">{{ m.name }}</p>
        <p class="role">{{ pick(m, "role") }}</p>
      </article>
    </div>
  </section>
</template>

<script setup>
import { ref } from "vue";
import { usePick } from "../../composables/usePick";
import { useScrollReveal } from "../../composables/useScrollReveal";

defineProps({
  about: { type: Object, default: null },
  team: { type: Array, default: () => [] },
});

const { pick } = usePick();
const root = ref(null);
useScrollReveal(() => root.value);

function initials(name = "") {
  return name.split(/\s+/).slice(0, 2).map(s => s[0] || "").join("").toUpperCase();
}
</script>

<style scoped>
.about { padding: 64px 0; }
.title { text-align: center; font-size: 32px; margin: 0 0 36px; }
.mv { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; margin-bottom: 48px; }
.card { padding: 28px; border-radius: var(--r-lg); background: var(--surface); border: 1px solid var(--border); }
.card h3 { margin: 0 0 10px; font-size: 16px; }
.card p { color: var(--text-2); margin: 0; line-height: 1.6; }
.team { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; }
.member { text-align: center; }
.member img, .member .avatar { width: 72px; height: 72px; border-radius: 50%; margin: 0 auto 8px; display: block; object-fit: cover; }
.member .avatar { background: var(--surface-2); display: grid; place-items: center; font-weight: 600; color: var(--text-2); }
.name { font-weight: 600; margin: 0; font-size: 14px; }
.role { color: var(--text-3); margin: 2px 0 0; font-size: 12px; }
</style>
```

- [ ] **Step 2: Commit**

```
git add frontend/src/components/public/AboutSection.vue
git commit -m "feat(landing): about section with mission/vision + team grid"
```

---

## Task 21 — LocationsSection with Google Maps

**Files:**
- Modify: `frontend/src/components/public/LocationsSection.vue`

**Interfaces:**
- Consumes: props `locations` (array), `settings` (object with `google_maps_api_key`).

- [ ] **Step 1: Implement**

Replace `frontend/src/components/public/LocationsSection.vue` with:
```vue
<template>
  <section id="locations" ref="root" class="loc">
    <h2 class="title">{{ $t("nav.locations") }}</h2>
    <div v-if="!apiKey" class="warn">Google Maps no configurado.</div>
    <div v-else class="layout">
      <div ref="mapEl" class="map"></div>
      <ul class="list">
        <li v-for="l in locations" :key="l.id" @click="focus(l)">
          <p class="name">{{ l.name }}</p>
          <p class="addr">{{ l.address }}</p>
          <p v-if="l.phone" class="phone">{{ l.phone }}</p>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { Loader } from "@googlemaps/js-api-loader";
import { useScrollReveal } from "../../composables/useScrollReveal";

const props = defineProps({
  locations: { type: Array, default: () => [] },
  settings: { type: Object, default: null },
});

const root = ref(null);
const mapEl = ref(null);
useScrollReveal(() => root.value);

const apiKey = computed(() => props.settings?.google_maps_api_key || "");

let mapInstance = null;
let markers = [];

async function initMap() {
  if (!apiKey.value || !mapEl.value) return;
  const loader = new Loader({ apiKey: apiKey.value, version: "weekly", libraries: ["maps", "marker"] });
  const { Map, InfoWindow } = await loader.importLibrary("maps");
  const { Marker } = await loader.importLibrary("marker");

  const center = props.locations[0]
    ? { lat: Number(props.locations[0].lat), lng: Number(props.locations[0].lng) }
    : { lat: 19.4326, lng: -99.1332 };
  mapInstance = new Map(mapEl.value, { center, zoom: 12, mapTypeControl: false });

  markers.forEach(m => m.setMap(null));
  markers = props.locations.map(l => {
    const marker = new Marker({
      position: { lat: Number(l.lat), lng: Number(l.lng) },
      map: mapInstance, title: l.name,
    });
    const info = new InfoWindow({
      content: `<strong>${l.name}</strong><br>${l.address}${l.phone ? `<br>${l.phone}` : ""}`,
    });
    marker.addListener("click", () => info.open({ anchor: marker, map: mapInstance }));
    return marker;
  });
}

function focus(l) {
  if (!mapInstance) return;
  mapInstance.panTo({ lat: Number(l.lat), lng: Number(l.lng) });
  mapInstance.setZoom(14);
}

onMounted(() => { if (apiKey.value && props.locations.length) initMap(); });
watch(() => [apiKey.value, props.locations.length], () => initMap());
</script>

<style scoped>
.loc { padding: 64px 0; }
.title { text-align: center; font-size: 32px; margin: 0 0 36px; }
.warn { text-align: center; color: var(--text-3); padding: 32px; border: 1px dashed var(--border); border-radius: var(--r); }
.layout { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }
@media (max-width: 720px) { .layout { grid-template-columns: 1fr; } }
.map { height: 420px; border-radius: var(--r-lg); overflow: hidden; background: var(--surface-2); }
.list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; max-height: 420px; overflow-y: auto; }
.list li { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 14px; cursor: pointer; transition: background .15s; }
.list li:hover { background: var(--surface-2); }
.list .name { font-weight: 600; margin: 0; font-size: 14px; }
.list .addr { color: var(--text-2); margin: 4px 0 0; font-size: 13px; }
.list .phone { color: var(--text-3); margin: 4px 0 0; font-size: 12px; }
</style>
```

- [ ] **Step 2: Configure API key**

Visit Django admin at `/admin/landing_cms/sitesettings/1/change/` and paste a Google Maps API key (with both Maps JavaScript API and Places API enabled). Add HTTP referrer restriction for `http://localhost:5173` in Google Cloud Console.

- [ ] **Step 3: Smoke test**

Reload `/`. If a location was seeded, a map should render with its pin. If no key, the "no configurado" warning appears (not an error).

- [ ] **Step 4: Commit**

```
git add frontend/src/components/public/LocationsSection.vue
git commit -m "feat(landing): locations section with Google Maps"
```

---

## Task 22 — ContactSection

**Files:**
- Modify: `frontend/src/components/public/ContactSection.vue`

**Interfaces:**
- Consumes: `landingApi.postContact`.

- [ ] **Step 1: Implement**

Replace `frontend/src/components/public/ContactSection.vue` with:
```vue
<template>
  <section id="contacto" ref="root" class="contact">
    <h2 class="title">{{ $t("contact.title") }}</h2>
    <form @submit.prevent="submit" class="form">
      <div class="row">
        <label>
          <span>{{ $t("contact.name") }}</span>
          <input v-model="form.name" required maxlength="100" />
        </label>
        <label>
          <span>{{ $t("contact.email") }}</span>
          <input v-model="form.email" type="email" required />
        </label>
      </div>
      <label>
        <span>{{ $t("contact.subject") }}</span>
        <input v-model="form.subject" required maxlength="200" />
      </label>
      <label>
        <span>{{ $t("contact.message") }}</span>
        <textarea v-model="form.message" required maxlength="5000" rows="5"></textarea>
      </label>
      <input v-model="form.website" tabindex="-1" autocomplete="off" class="hp" aria-hidden="true" />
      <p v-if="success" class="ok">{{ success }}</p>
      <p v-if="error" class="err">{{ error }}</p>
      <button :disabled="sending">{{ sending ? "..." : $t("contact.send") }}</button>
    </form>
  </section>
</template>

<script setup>
import { reactive, ref } from "vue";
import { landingApi } from "../../api/landing.api";
import { useScrollReveal } from "../../composables/useScrollReveal";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
const root = ref(null);
useScrollReveal(() => root.value);

const form = reactive({ name: "", email: "", subject: "", message: "", website: "" });
const sending = ref(false);
const success = ref("");
const error = ref("");

async function submit() {
  sending.value = true; success.value = ""; error.value = "";
  try {
    const r = await landingApi.postContact({ ...form });
    if (r.ticket_reference) {
      success.value = t("contact.success", { ref: r.ticket_reference });
      form.name = form.email = form.subject = form.message = "";
    } else {
      success.value = t("contact.success", { ref: "—" });
    }
  } catch (e) {
    error.value = t("contact.error");
  } finally {
    sending.value = false;
  }
}
</script>

<style scoped>
.contact { padding: 64px 0; }
.title { text-align: center; font-size: 32px; margin: 0 0 28px; }
.form { max-width: 560px; margin: 0 auto; display: flex; flex-direction: column; gap: 14px; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: var(--text-2); font-weight: 600; }
input, textarea { padding: 10px 12px; border: 1px solid var(--border); border-radius: var(--r); background: var(--surface); color: var(--text); font-size: 14px; resize: vertical; }
input:focus, textarea:focus { outline: 2px solid var(--accent); }
.hp { position: absolute; left: -9999px; }
button { background: var(--accent); color: var(--accent-fg); border: none; padding: 12px; border-radius: var(--r); font-weight: 600; font-size: 14px; cursor: pointer; }
button:disabled { opacity: .6; cursor: not-allowed; }
.ok { color: var(--c-success, #2a8); font-size: 13px; }
.err { color: var(--c-urgent, #c33); font-size: 13px; }
</style>
```

- [ ] **Step 2: Smoke test**

Reload `/`. Fill in form, submit. Should see "Recibimos tu mensaje. Referencia: ALS-…". Verify in Django admin (`/admin/tickets_t/ticket/`) the new ticket exists.

- [ ] **Step 3: Commit**

```
git add frontend/src/components/public/ContactSection.vue
git commit -m "feat(landing): contact section posts to public API"
```

---

## Task 23 — Admin shared components: I18nField + ImageDrop + DragHandleList

**Files:**
- Create: `frontend/src/components/admin/site/I18nField.vue`
- Create: `frontend/src/components/admin/site/ImageDrop.vue`
- Create: `frontend/src/components/admin/site/DragHandleList.vue`

**Interfaces:**
- `<I18nField v-model:es="..." v-model:en="..." label="..." type="input|textarea" />` — renders a labeled input/textarea with ES/EN tabs.
- `<ImageDrop v-model:file="..." :existingUrl="..." />` — drag-drop + preview.
- `<DragHandleList :items="..." @reorder="(ids) => ..." />` — wraps `vuedraggable`.

- [ ] **Step 1: I18nField**

Create `frontend/src/components/admin/site/I18nField.vue`:
```vue
<template>
  <div class="i18n-field">
    <label>{{ label }}</label>
    <div class="tabs">
      <button :class="{active: tab==='es'}" @click="tab='es'" type="button">ES</button>
      <button :class="{active: tab==='en'}" @click="tab='en'" type="button">EN</button>
    </div>
    <template v-if="type==='textarea'">
      <textarea v-if="tab==='es'" :value="es" @input="$emit('update:es', $event.target.value)" rows="4"></textarea>
      <textarea v-else :value="en" @input="$emit('update:en', $event.target.value)" rows="4"></textarea>
    </template>
    <template v-else>
      <input v-if="tab==='es'" :value="es" @input="$emit('update:es', $event.target.value)" />
      <input v-else :value="en" @input="$emit('update:en', $event.target.value)" />
    </template>
  </div>
</template>

<script setup>
import { ref } from "vue";
defineProps({
  label: String, es: String, en: String,
  type: { type: String, default: "input" },
});
defineEmits(["update:es", "update:en"]);
const tab = ref("es");
</script>

<style scoped>
.i18n-field { display: flex; flex-direction: column; gap: 6px; }
label { font-size: 12px; color: var(--text-2); font-weight: 600; }
.tabs { display: flex; gap: 4px; }
.tabs button { padding: 2px 10px; font-size: 11px; border: 1px solid var(--border); border-radius: var(--r-sm); background: transparent; color: var(--text-3); }
.tabs button.active { background: var(--accent); color: var(--accent-fg); border-color: transparent; }
input, textarea { padding: 8px 10px; border: 1px solid var(--border); border-radius: var(--r); background: var(--surface); color: var(--text); font-size: 14px; }
</style>
```

- [ ] **Step 2: ImageDrop**

Create `frontend/src/components/admin/site/ImageDrop.vue`:
```vue
<template>
  <div class="drop" :class="{drag: drag}"
       @dragover.prevent="drag=true" @dragleave="drag=false"
       @drop.prevent="onDrop">
    <img v-if="previewUrl" :src="previewUrl" alt="" class="preview" />
    <p v-else class="hint">Arrastra o <label>elige una imagen<input type="file" accept="image/*" @change="onPick" /></label></p>
    <button v-if="previewUrl" type="button" class="clear" @click="clear">×</button>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
const props = defineProps({ file: File, existingUrl: String });
const emit = defineEmits(["update:file"]);
const drag = ref(false);
const localUrl = ref(null);

const previewUrl = computed(() => localUrl.value || props.existingUrl || "");

function onPick(e) { setFile(e.target.files[0]); }
function onDrop(e) { drag.value = false; setFile(e.dataTransfer.files[0]); }
function setFile(f) {
  if (!f) return;
  emit("update:file", f);
  if (localUrl.value) URL.revokeObjectURL(localUrl.value);
  localUrl.value = URL.createObjectURL(f);
}
function clear() {
  emit("update:file", null);
  if (localUrl.value) URL.revokeObjectURL(localUrl.value);
  localUrl.value = null;
}
</script>

<style scoped>
.drop { position: relative; border: 1px dashed var(--border); border-radius: var(--r); padding: 16px; text-align: center; min-height: 100px; display: grid; place-items: center; }
.drop.drag { border-color: var(--accent); background: var(--accent-light, transparent); }
.preview { max-width: 100%; max-height: 160px; border-radius: var(--r-sm); }
.hint { color: var(--text-3); font-size: 13px; }
.hint label { color: var(--accent); cursor: pointer; }
.hint input { display: none; }
.clear { position: absolute; top: 6px; right: 6px; border: 1px solid var(--border); background: var(--surface); border-radius: 50%; width: 24px; height: 24px; cursor: pointer; }
</style>
```

- [ ] **Step 3: DragHandleList**

Create `frontend/src/components/admin/site/DragHandleList.vue`:
```vue
<template>
  <draggable :model-value="items" @update:model-value="onUpdate" item-key="id" handle=".handle">
    <template #item="{ element }">
      <div class="row">
        <span class="handle">⋮⋮</span>
        <slot :item="element" />
      </div>
    </template>
  </draggable>
</template>

<script setup>
import draggable from "vuedraggable";
defineProps({ items: { type: Array, required: true } });
const emit = defineEmits(["reorder"]);
function onUpdate(newList) {
  emit("reorder", newList.map(x => x.id));
}
</script>

<style scoped>
.row { display: flex; align-items: center; gap: 10px; padding: 8px; border: 1px solid var(--border); border-radius: var(--r); margin-bottom: 6px; background: var(--surface); }
.handle { cursor: grab; color: var(--text-3); user-select: none; }
</style>
```

- [ ] **Step 4: Commit**

```
git add frontend/src/components/admin/site/I18nField.vue frontend/src/components/admin/site/ImageDrop.vue frontend/src/components/admin/site/DragHandleList.vue
git commit -m "feat(admin): shared I18nField, ImageDrop, DragHandleList"
```

---

## Task 24 — AdminContent screen (Hero + About + Site settings + Features list)

**Files:**
- Modify: `frontend/src/api/landing.api.js` (add admin methods)
- Create: `frontend/src/views/admin/site/AdminContent.vue`

**Interfaces:**
- Produces:
  - `landingApi.adminGetHero/PutHero`, same for `about` and `siteSettings`.
  - `landingApi.adminListFeatures/CreateFeature/UpdateFeature/DeleteFeature/ReorderFeatures`.
  - `<AdminContent>` view with 4 collapsible sections, each with its own Save button.

- [ ] **Step 1: Extend API client**

Append to `frontend/src/api/landing.api.js`:
```js
const A = "/api/admin";

export const landingAdminApi = {
  // singletons
  getHero: () => http.get(`${A}/landing/hero/`).then(r => r.data),
  putHero: (data) => http.put(`${A}/landing/hero/`, data).then(r => r.data),
  getAbout: () => http.get(`${A}/landing/about/`).then(r => r.data),
  putAbout: (data) => http.put(`${A}/landing/about/`, data).then(r => r.data),
  getSettings: () => http.get(`${A}/site-settings/`).then(r => r.data),
  putSettings: (formData) => http.put(`${A}/site-settings/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  }).then(r => r.data),
  // features
  listFeatures: () => http.get(`${A}/landing/features/`).then(r => r.data),
  createFeature: (data) => http.post(`${A}/landing/features/`, data).then(r => r.data),
  updateFeature: (id, data) => http.put(`${A}/landing/features/${id}/`, data).then(r => r.data),
  deleteFeature: (id) => http.delete(`${A}/landing/features/${id}/`),
  reorderFeatures: (ids) => http.post(`${A}/landing/features/reorder/`, { ids }),
  // team
  listTeam: () => http.get(`${A}/landing/team/`).then(r => r.data),
  createTeam: (formData) => http.post(`${A}/landing/team/`, formData, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data),
  updateTeam: (id, formData) => http.put(`${A}/landing/team/${id}/`, formData, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data),
  deleteTeam: (id) => http.delete(`${A}/landing/team/${id}/`),
  reorderTeam: (ids) => http.post(`${A}/landing/team/reorder/`, { ids }),
  // locations
  listLocations: () => http.get(`${A}/landing/locations/`).then(r => r.data),
  createLocation: (formData) => http.post(`${A}/landing/locations/`, formData, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data),
  updateLocation: (id, formData) => http.put(`${A}/landing/locations/${id}/`, formData, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data),
  deleteLocation: (id) => http.delete(`${A}/landing/locations/${id}/`),
  reorderLocations: (ids) => http.post(`${A}/landing/locations/reorder/`, { ids }),
};
```

- [ ] **Step 2: AdminContent view**

Create `frontend/src/views/admin/site/AdminContent.vue`:
```vue
<template>
  <div class="ac">
    <h1>Contenido del sitio</h1>

    <section class="block">
      <header><h2>Hero</h2><button @click="saveHero" :disabled="busy.hero">Guardar</button></header>
      <I18nField label="Título" v-model:es="hero.title_es" v-model:en="hero.title_en" />
      <I18nField label="Subtítulo" type="textarea" v-model:es="hero.subtitle_es" v-model:en="hero.subtitle_en" />
      <I18nField label="CTA primario - etiqueta" v-model:es="hero.primary_cta_label_es" v-model:en="hero.primary_cta_label_en" />
      <label>CTA primario - URL <input v-model="hero.primary_cta_url" /></label>
    </section>

    <section class="block">
      <header><h2>Sobre nosotros</h2><button @click="saveAbout" :disabled="busy.about">Guardar</button></header>
      <I18nField label="Misión" type="textarea" v-model:es="about.mission_es" v-model:en="about.mission_en" />
      <I18nField label="Visión" type="textarea" v-model:es="about.vision_es" v-model:en="about.vision_en" />
    </section>

    <section class="block">
      <header><h2>Site settings</h2><button @click="saveSettings" :disabled="busy.settings">Guardar</button></header>
      <label>Google Maps API key <input v-model="settings.google_maps_api_key" /></label>
      <I18nField label="Pie de página" type="textarea" v-model:es="settings.footer_text_es" v-model:en="settings.footer_text_en" />
    </section>

    <section class="block">
      <header><h2>Funcionalidades (cards del landing)</h2><button @click="addFeature">+ Agregar</button></header>
      <DragHandleList :items="features" @reorder="onReorder" v-slot="{ item }">
        <FeatureFormRow :feature="item" @save="onSaveFeature" @remove="onRemoveFeature" />
      </DragHandleList>
    </section>

    <p v-if="msg" class="toast">{{ msg }}</p>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from "vue";
import { landingAdminApi } from "../../../api/landing.api";
import I18nField from "../../../components/admin/site/I18nField.vue";
import DragHandleList from "../../../components/admin/site/DragHandleList.vue";
import FeatureFormRow from "../../../components/admin/site/FeatureFormRow.vue";

const hero = reactive({});
const about = reactive({});
const settings = reactive({});
const features = ref([]);
const busy = reactive({ hero: false, about: false, settings: false });
const msg = ref("");

function toast(t) { msg.value = t; setTimeout(() => (msg.value = ""), 1800); }

async function load() {
  const [h, a, s, fs] = await Promise.all([
    landingAdminApi.getHero(), landingAdminApi.getAbout(),
    landingAdminApi.getSettings(), landingAdminApi.listFeatures(),
  ]);
  Object.assign(hero, h); Object.assign(about, a); Object.assign(settings, s);
  features.value = fs;
}

async function saveHero() { busy.hero = true; try { await landingAdminApi.putHero(hero); toast("Hero guardado"); } finally { busy.hero = false; } }
async function saveAbout() { busy.about = true; try { await landingAdminApi.putAbout(about); toast("Nosotros guardado"); } finally { busy.about = false; } }
async function saveSettings() {
  busy.settings = true;
  const fd = new FormData();
  Object.entries(settings).forEach(([k, v]) => {
    if (v === null || v === undefined) return;
    if (typeof v === "object") fd.append(k, JSON.stringify(v));
    else fd.append(k, v);
  });
  try { await landingAdminApi.putSettings(fd); toast("Ajustes guardados"); }
  finally { busy.settings = false; }
}

async function addFeature() {
  const f = await landingAdminApi.createFeature({
    icon: "sparkles", title_es: "Nuevo", title_en: "New",
    description_es: "", description_en: "", order: features.value.length, is_active: true,
  });
  features.value.push(f);
}
async function onSaveFeature(f) { await landingAdminApi.updateFeature(f.id, f); toast("Card guardada"); }
async function onRemoveFeature(id) {
  await landingAdminApi.deleteFeature(id);
  features.value = features.value.filter(x => x.id !== id);
}
async function onReorder(ids) {
  await landingAdminApi.reorderFeatures(ids);
  const map = Object.fromEntries(features.value.map(f => [f.id, f]));
  features.value = ids.map(id => map[id]);
}

onMounted(load);
</script>

<style scoped>
.ac { display: flex; flex-direction: column; gap: 28px; max-width: 760px; }
h1 { font-size: 24px; margin: 0; }
.block { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); padding: 20px; display: flex; flex-direction: column; gap: 12px; }
.block header { display: flex; justify-content: space-between; align-items: center; }
.block header h2 { font-size: 16px; margin: 0; }
.block header button { background: var(--accent); color: var(--accent-fg); border: none; padding: 6px 14px; border-radius: var(--r); font-size: 13px; font-weight: 600; cursor: pointer; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: var(--text-2); font-weight: 600; }
label input { padding: 8px 10px; border: 1px solid var(--border); border-radius: var(--r); background: var(--surface); color: var(--text); }
.toast { position: fixed; bottom: 24px; right: 24px; background: var(--accent); color: var(--accent-fg); padding: 10px 16px; border-radius: var(--r); }
</style>
```

- [ ] **Step 3: FeatureFormRow component**

Create `frontend/src/components/admin/site/FeatureFormRow.vue`:
```vue
<template>
  <div class="row">
    <input v-model="local.icon" placeholder="icon" style="width:90px" />
    <input v-model="local.title_es" placeholder="Título ES" />
    <input v-model="local.title_en" placeholder="Title EN" />
    <input type="checkbox" v-model="local.is_active" title="Activo" />
    <button @click="$emit('save', local)">Guardar</button>
    <button @click="$emit('remove', local.id)" class="del">Borrar</button>
  </div>
</template>

<script setup>
import { reactive, watch } from "vue";
const props = defineProps({ feature: Object });
const local = reactive({ ...props.feature });
watch(() => props.feature, (v) => Object.assign(local, v));
</script>

<style scoped>
.row { display: flex; gap: 6px; align-items: center; width: 100%; }
input[type=text], input:not([type]) { flex: 1; padding: 6px 8px; border: 1px solid var(--border); border-radius: var(--r-sm); background: var(--surface); color: var(--text); font-size: 13px; }
button { padding: 5px 10px; border-radius: var(--r-sm); border: 1px solid var(--border); background: var(--surface); color: var(--text); cursor: pointer; font-size: 12px; }
button.del { color: var(--c-urgent, #c33); }
</style>
```

- [ ] **Step 4: Smoke test**

Run `npm run dev`. Login as superuser, navigate to `/admin/sitio/contenido`. Verify hero/about load, you can edit and save, features list loads with seeded data.

- [ ] **Step 5: Commit**

```
git add frontend/src/api/landing.api.js frontend/src/views/admin/site/AdminContent.vue frontend/src/components/admin/site/FeatureFormRow.vue
git commit -m "feat(admin): site content screen (hero/about/settings/features)"
```

---

## Task 25 — AdminTeam screen with modal

**Files:**
- Create: `frontend/src/views/admin/site/AdminTeam.vue`
- Create: `frontend/src/components/admin/site/TeamMemberFormModal.vue`

**Interfaces:**
- `<AdminTeam>` lists team members with drag-to-reorder; "+" opens `<TeamMemberFormModal>`; click row also opens it for editing.

- [ ] **Step 1: TeamMemberFormModal**

Create `frontend/src/components/admin/site/TeamMemberFormModal.vue`:
```vue
<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="modal">
      <header><h3>{{ member?.id ? "Editar miembro" : "Agregar miembro" }}</h3><button @click="$emit('close')">×</button></header>
      <ImageDrop v-model:file="photoFile" :existingUrl="member?.photo" />
      <label>Nombre <input v-model="form.name" required /></label>
      <I18nField label="Cargo" v-model:es="form.role_es" v-model:en="form.role_en" />
      <I18nField label="Bio" type="textarea" v-model:es="form.bio_es" v-model:en="form.bio_en" />
      <label class="check"><input type="checkbox" v-model="form.is_active" /> Activo</label>
      <footer>
        <button @click="$emit('close')">Cancelar</button>
        <button class="primary" @click="save" :disabled="busy">{{ busy ? "..." : "Guardar" }}</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import I18nField from "./I18nField.vue";
import ImageDrop from "./ImageDrop.vue";

const props = defineProps({ member: Object });
const emit = defineEmits(["close", "saved"]);

const form = reactive({
  name: props.member?.name || "",
  role_es: props.member?.role_es || "",
  role_en: props.member?.role_en || "",
  bio_es: props.member?.bio_es || "",
  bio_en: props.member?.bio_en || "",
  is_active: props.member?.is_active ?? true,
  order: props.member?.order ?? 0,
});
const photoFile = ref(null);
const busy = ref(false);

async function save() {
  busy.value = true;
  const fd = new FormData();
  Object.entries(form).forEach(([k, v]) => fd.append(k, v ?? ""));
  if (photoFile.value) fd.append("photo", photoFile.value);
  emit("saved", { id: props.member?.id, formData: fd });
  busy.value = false;
}
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: grid; place-items: center; z-index: 100; }
.modal { background: var(--surface); border-radius: var(--r-lg); padding: 24px; width: min(520px, 92vw); display: flex; flex-direction: column; gap: 12px; max-height: 90vh; overflow-y: auto; }
header { display: flex; justify-content: space-between; align-items: center; }
header h3 { margin: 0; font-size: 16px; }
header button { background: transparent; border: none; font-size: 22px; color: var(--text-3); cursor: pointer; }
label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-2); font-weight: 600; }
label.check { flex-direction: row; align-items: center; gap: 8px; font-weight: 400; }
input { padding: 8px 10px; border: 1px solid var(--border); border-radius: var(--r); background: var(--surface); color: var(--text); font-size: 14px; }
footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
footer button { padding: 8px 16px; border-radius: var(--r); border: 1px solid var(--border); background: var(--surface); color: var(--text); cursor: pointer; }
footer button.primary { background: var(--accent); color: var(--accent-fg); border-color: transparent; }
</style>
```

- [ ] **Step 2: AdminTeam view**

Create `frontend/src/views/admin/site/AdminTeam.vue`:
```vue
<template>
  <div class="at">
    <header class="top">
      <h1>Equipo</h1>
      <button @click="openNew">+ Agregar miembro</button>
    </header>

    <DragHandleList :items="members" @reorder="onReorder" v-slot="{ item }">
      <div class="row" @click="openEdit(item)">
        <img v-if="item.photo" :src="item.photo" :alt="item.name" />
        <div v-else class="avatar">{{ initials(item.name) }}</div>
        <div class="info">
          <p class="name">{{ item.name }}</p>
          <p class="role">{{ item.role_es }}</p>
        </div>
        <span :class="['dot', item.is_active ? 'on' : 'off']"></span>
      </div>
    </DragHandleList>

    <TeamMemberFormModal v-if="open" :member="editing" @close="open=false" @saved="onSaved" />
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { landingAdminApi } from "../../../api/landing.api";
import DragHandleList from "../../../components/admin/site/DragHandleList.vue";
import TeamMemberFormModal from "../../../components/admin/site/TeamMemberFormModal.vue";

const members = ref([]);
const open = ref(false);
const editing = ref(null);

function initials(name="") {
  return name.split(/\s+/).slice(0,2).map(s=>s[0]||"").join("").toUpperCase();
}

async function load() { members.value = await landingAdminApi.listTeam(); }
function openNew() { editing.value = null; open.value = true; }
function openEdit(m) { editing.value = m; open.value = true; }
async function onSaved({ id, formData }) {
  if (id) await landingAdminApi.updateTeam(id, formData);
  else await landingAdminApi.createTeam(formData);
  open.value = false;
  await load();
}
async function onReorder(ids) {
  await landingAdminApi.reorderTeam(ids);
  const map = Object.fromEntries(members.value.map(m => [m.id, m]));
  members.value = ids.map(id => map[id]);
}

onMounted(load);
</script>

<style scoped>
.top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.top h1 { font-size: 24px; margin: 0; }
.top button { background: var(--accent); color: var(--accent-fg); border: none; padding: 8px 16px; border-radius: var(--r); font-weight: 600; cursor: pointer; }
.row { display: flex; align-items: center; gap: 12px; width: 100%; cursor: pointer; }
.row img, .row .avatar { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; }
.row .avatar { background: var(--surface-2); display: grid; place-items: center; font-weight: 600; font-size: 12px; color: var(--text-2); }
.info { flex: 1; }
.info .name { margin: 0; font-weight: 600; font-size: 14px; }
.info .role { margin: 0; color: var(--text-3); font-size: 12px; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.on { background: var(--c-success, #2a8); }
.dot.off { background: var(--text-3); }
</style>
```

- [ ] **Step 3: Smoke test**

Navigate to `/admin/sitio/equipo`. Add a member with a photo. Verify it shows in the list. Reorder via drag. Reload `/` and check the team grid.

- [ ] **Step 4: Commit**

```
git add frontend/src/views/admin/site/AdminTeam.vue frontend/src/components/admin/site/TeamMemberFormModal.vue
git commit -m "feat(admin): team CRUD screen with modal"
```

---

## Task 26 — AdminLocations screen with Google Places autocomplete + draggable pin

**Files:**
- Create: `frontend/src/views/admin/site/AdminLocations.vue`
- Create: `frontend/src/components/admin/site/LocationFormModal.vue`

**Interfaces:**
- `<AdminLocations>` mirrors AdminTeam structure but for `Location`.
- `<LocationFormModal>` includes:
  - Google Places autocomplete input — picking a prediction fills `address`, `lat`, `lng`.
  - Map with one draggable marker — dragging it updates `lat`, `lng`.
  - Extra fields: `name`, `type`, `phone`, `email`, `hours_es/_en`, `description_es/_en`, `photo`, `is_active`.

- [ ] **Step 1: LocationFormModal**

Create `frontend/src/components/admin/site/LocationFormModal.vue`:
```vue
<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="modal">
      <header><h3>{{ location?.id ? "Editar ubicación" : "Agregar ubicación" }}</h3><button @click="$emit('close')">×</button></header>

      <label>Buscar dirección (Google Places)
        <input ref="placesInput" placeholder="Comienza a escribir una dirección..." />
      </label>

      <div ref="mapEl" class="map"></div>

      <div class="grid">
        <label>Lat <input :value="form.lat" readonly /></label>
        <label>Lng <input :value="form.lng" readonly /></label>
      </div>

      <div class="grid">
        <label>Nombre interno <input v-model="form.name" required /></label>
        <label>Tipo
          <select v-model="form.type">
            <option value="SUCURSAL">Sucursal</option>
            <option value="OFICINA">Oficina</option>
            <option value="CENTRO">Centro de servicio</option>
          </select>
        </label>
      </div>

      <label>Dirección <input v-model="form.address" /></label>

      <div class="grid">
        <label>Teléfono <input v-model="form.phone" /></label>
        <label>Email <input v-model="form.email" type="email" /></label>
      </div>

      <I18nField label="Horario" v-model:es="form.hours_es" v-model:en="form.hours_en" />
      <I18nField label="Descripción" type="textarea" v-model:es="form.description_es" v-model:en="form.description_en" />

      <label>Foto</label>
      <ImageDrop v-model:file="photoFile" :existingUrl="location?.photo" />

      <label class="check"><input type="checkbox" v-model="form.is_active" /> Activo</label>

      <footer>
        <button @click="$emit('close')">Cancelar</button>
        <button class="primary" @click="save" :disabled="busy">{{ busy ? "..." : "Guardar" }}</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from "vue";
import { Loader } from "@googlemaps/js-api-loader";
import { landingAdminApi } from "../../../api/landing.api";
import I18nField from "./I18nField.vue";
import ImageDrop from "./ImageDrop.vue";

const props = defineProps({ location: Object });
const emit = defineEmits(["close", "saved"]);

const form = reactive({
  name: props.location?.name || "",
  address: props.location?.address || "",
  lat: props.location?.lat ?? 19.4326,
  lng: props.location?.lng ?? -99.1332,
  type: props.location?.type || "OFICINA",
  phone: props.location?.phone || "",
  email: props.location?.email || "",
  hours_es: props.location?.hours_es || "",
  hours_en: props.location?.hours_en || "",
  description_es: props.location?.description_es || "",
  description_en: props.location?.description_en || "",
  is_active: props.location?.is_active ?? true,
  order: props.location?.order ?? 0,
});
const photoFile = ref(null);
const busy = ref(false);
const placesInput = ref(null);
const mapEl = ref(null);

let marker = null;
let mapInstance = null;

async function initMap() {
  const settings = await landingAdminApi.getSettings();
  const key = settings.google_maps_api_key;
  if (!key) { alert("Configura primero la Google Maps API key en Contenido del sitio."); return; }
  const loader = new Loader({ apiKey: key, version: "weekly", libraries: ["maps", "marker", "places"] });
  const { Map } = await loader.importLibrary("maps");
  const { Marker } = await loader.importLibrary("marker");
  const { Autocomplete } = await loader.importLibrary("places");

  const center = { lat: Number(form.lat), lng: Number(form.lng) };
  mapInstance = new Map(mapEl.value, { center, zoom: 13, mapTypeControl: false });
  marker = new Marker({ position: center, map: mapInstance, draggable: true });
  marker.addListener("dragend", () => {
    const p = marker.getPosition();
    form.lat = Number(p.lat().toFixed(6));
    form.lng = Number(p.lng().toFixed(6));
  });

  const ac = new Autocomplete(placesInput.value, { fields: ["formatted_address", "geometry"] });
  ac.addListener("place_changed", () => {
    const place = ac.getPlace();
    if (!place.geometry) return;
    const loc = place.geometry.location;
    form.address = place.formatted_address || form.address;
    form.lat = Number(loc.lat().toFixed(6));
    form.lng = Number(loc.lng().toFixed(6));
    mapInstance.panTo(loc);
    marker.setPosition(loc);
  });
}

async function save() {
  busy.value = true;
  const fd = new FormData();
  Object.entries(form).forEach(([k, v]) => fd.append(k, v ?? ""));
  if (photoFile.value) fd.append("photo", photoFile.value);
  emit("saved", { id: props.location?.id, formData: fd });
  busy.value = false;
}

onMounted(initMap);
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: grid; place-items: center; z-index: 100; }
.modal { background: var(--surface); border-radius: var(--r-lg); padding: 24px; width: min(640px, 94vw); display: flex; flex-direction: column; gap: 12px; max-height: 92vh; overflow-y: auto; }
header { display: flex; justify-content: space-between; align-items: center; }
header h3 { margin: 0; font-size: 16px; }
header button { background: transparent; border: none; font-size: 22px; color: var(--text-3); cursor: pointer; }
.map { height: 220px; border-radius: var(--r); background: var(--surface-2); }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-2); font-weight: 600; }
label.check { flex-direction: row; align-items: center; gap: 8px; font-weight: 400; }
input, select { padding: 8px 10px; border: 1px solid var(--border); border-radius: var(--r); background: var(--surface); color: var(--text); font-size: 14px; }
footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
footer button { padding: 8px 16px; border-radius: var(--r); border: 1px solid var(--border); background: var(--surface); color: var(--text); cursor: pointer; }
footer button.primary { background: var(--accent); color: var(--accent-fg); border-color: transparent; }
</style>
```

- [ ] **Step 2: AdminLocations view**

Create `frontend/src/views/admin/site/AdminLocations.vue`:
```vue
<template>
  <div class="al">
    <header class="top">
      <h1>Ubicaciones</h1>
      <button @click="openNew">+ Agregar ubicación</button>
    </header>

    <DragHandleList :items="items" @reorder="onReorder" v-slot="{ item }">
      <div class="row" @click="openEdit(item)">
        <div class="pin">{{ item.type[0] }}</div>
        <div class="info">
          <p class="name">{{ item.name }}</p>
          <p class="addr">{{ item.address }}</p>
        </div>
        <span :class="['dot', item.is_active ? 'on' : 'off']"></span>
      </div>
    </DragHandleList>

    <LocationFormModal v-if="open" :location="editing" @close="open=false" @saved="onSaved" />
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { landingAdminApi } from "../../../api/landing.api";
import DragHandleList from "../../../components/admin/site/DragHandleList.vue";
import LocationFormModal from "../../../components/admin/site/LocationFormModal.vue";

const items = ref([]);
const open = ref(false);
const editing = ref(null);

async function load() { items.value = await landingAdminApi.listLocations(); }
function openNew() { editing.value = null; open.value = true; }
function openEdit(l) { editing.value = l; open.value = true; }
async function onSaved({ id, formData }) {
  if (id) await landingAdminApi.updateLocation(id, formData);
  else await landingAdminApi.createLocation(formData);
  open.value = false;
  await load();
}
async function onReorder(ids) {
  await landingAdminApi.reorderLocations(ids);
  const map = Object.fromEntries(items.value.map(x => [x.id, x]));
  items.value = ids.map(id => map[id]);
}
onMounted(load);
</script>

<style scoped>
.top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.top h1 { font-size: 24px; margin: 0; }
.top button { background: var(--accent); color: var(--accent-fg); border: none; padding: 8px 16px; border-radius: var(--r); font-weight: 600; cursor: pointer; }
.row { display: flex; align-items: center; gap: 12px; width: 100%; cursor: pointer; }
.pin { width: 32px; height: 32px; border-radius: 50%; background: var(--accent); color: var(--accent-fg); display: grid; place-items: center; font-weight: 700; font-size: 13px; }
.info { flex: 1; }
.info .name { margin: 0; font-weight: 600; font-size: 14px; }
.info .addr { margin: 0; color: var(--text-3); font-size: 12px; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.on { background: var(--c-success, #2a8); }
.dot.off { background: var(--text-3); }
</style>
```

- [ ] **Step 3: Smoke test**

Navigate to `/admin/sitio/ubicaciones`. Add a location: type an address, pick a Places prediction, drag the pin slightly, fill the name/type, save. Reload `/`; the pin appears on the public map.

- [ ] **Step 4: Commit**

```
git add frontend/src/views/admin/site/AdminLocations.vue frontend/src/components/admin/site/LocationFormModal.vue
git commit -m "feat(admin): locations CRUD with Google Places + draggable pin"
```

---

## Task 27 — Link sidebar from existing AdminDashboard

**Files:**
- Modify: `frontend/src/views/dashboards/AdminDashboard.vue`

**Interfaces:**
- Adds visible link buttons (or sidebar entries) from the existing admin dashboard to the 3 new CMS screens, so the superuser can reach them without typing the URL.

- [ ] **Step 1: Add navigation buttons to AdminDashboard**

Open `frontend/src/views/dashboards/AdminDashboard.vue`. Locate the main `<template>` body (where the dashboard cards are). Add at the top of the dashboard a new section:
```vue
<section style="display:flex; gap:12px; margin-bottom:24px;">
  <router-link to="/admin/sitio/contenido" class="cms-link">Contenido del sitio</router-link>
  <router-link to="/admin/sitio/equipo" class="cms-link">Equipo</router-link>
  <router-link to="/admin/sitio/ubicaciones" class="cms-link">Ubicaciones</router-link>
</section>
```

And in the `<style scoped>` block add:
```css
.cms-link { padding: 8px 14px; border: 1px solid var(--border); border-radius: var(--r); color: var(--text); text-decoration: none; font-size: 13px; font-weight: 600; }
.cms-link:hover { background: var(--surface-2); }
```

- [ ] **Step 2: Smoke test**

Login as superuser, navigate to `/admin`. The 3 CMS link buttons appear.

- [ ] **Step 3: Commit**

```
git add frontend/src/views/dashboards/AdminDashboard.vue
git commit -m "feat(admin): link CMS screens from main admin dashboard"
```

---

## Task 28 — End-to-end smoke test + spec README link

**Files:**
- Create: `docs/superpowers/plans/2026-06-30-allsafe-landing-publica-VERIFY.md`

**Interfaces:**
- Produces: a manual verification checklist documenting that all flows work end-to-end. No new code.

- [ ] **Step 1: Run full test suite**

```
python backend/manage.py test landing_cms -v 2
```
Expected: all tests pass (models, public, admin, contact, validators — roughly 15+ tests OK).

- [ ] **Step 2: Manual happy path**

In a clean browser session:
1. Visit `/` — landing renders with seeded hero, 2 features, mission/vision, 0 team, 0 locations.
2. Toggle EN — texts switch.
3. Submit contact form with valid data — success message with `ALS-…` reference.
4. Log in as superuser, go to `/admin`. Click "Contenido del sitio". Edit hero, save, reload `/` — change visible.
5. `/admin/sitio/equipo` — add 2 members with photos. Reload `/` — they appear in team grid.
6. `/admin/sitio/ubicaciones` — add 2 locations with Google Places. Reload `/` — pins on map, list on right.
7. Log in as CUSTOMER, try `/admin/sitio/contenido` — redirected away by guard.

- [ ] **Step 3: Write verification document**

Create `docs/superpowers/plans/2026-06-30-allsafe-landing-publica-VERIFY.md`:
```markdown
# Landing pública — Verificación manual

- [ ] Tests backend `python manage.py test landing_cms` → OK
- [ ] `/` carga con i18n ES/EN
- [ ] Contacto crea ticket
- [ ] Admin edita Hero
- [ ] Admin agrega miembro de equipo con foto
- [ ] Admin agrega ubicación con Google Places
- [ ] Mapa público muestra pines
- [ ] CUSTOMER no puede entrar al admin CMS
- [ ] `prefers-reduced-motion: reduce` deshabilita animaciones
```

- [ ] **Step 4: Commit**

```
git add docs/superpowers/plans/2026-06-30-allsafe-landing-publica-VERIFY.md
git commit -m "docs: verification checklist for landing"
```

---

## Self-review

**Spec coverage:**
- Sec 4 Arquitectura: Tasks 1, 12, 15, 16.
- Sec 5 Modelos: Tasks 3, 4, 5.
- Sec 6 API: Tasks 7, 9, 10.
- Sec 7 Frontend (routing/layouts/components/i18n/animaciones/maps/photo): Tasks 13–26.
- Sec 8 Configuración Django: Task 1.
- Sec 9 UX: Tasks 17, 24, 25, 26.
- Sec 10 Seguridad: Task 2 (validador), Task 8 (permission), Task 1 (throttling).
- Sec 11 Testing: Tasks 2, 3, 4, 7, 9, 10 (unit + endpoint tests). Frontend smoke testing in Task 28.
- Out-of-scope items from Sec 14 not implemented as expected.

**Placeholder scan:** No "TBD/TODO/implement later" found. Every code step shows the actual code.

**Type consistency:**
- `SingletonManager.get_solo()` used in views (Task 7, 9). ✓
- `IsAdminRole` referenced in Task 9 matches definition in Task 8. ✓
- `landingApi` and `landingAdminApi` named consistently across Tasks 14 and 24. ✓
- `pick(obj, field)` signature stable across Tasks 13, 18, 19, 20. ✓
- `useScrollReveal(getEl)` signature stable across Tasks 17, 18, 19, 20, 21, 22. ✓
- All Vue prop names (`hero`, `features`, `about`, `team`, `locations`, `settings`) match between `LandingHome.vue` (Task 17) and each section (Tasks 18–22). ✓

No issues found.
