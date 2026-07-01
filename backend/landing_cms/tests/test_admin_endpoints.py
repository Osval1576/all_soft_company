from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from landing_cms.models import Feature

User = get_user_model()


def _png_upload(name="t.png"):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from io import BytesIO
    from PIL import Image
    buf = BytesIO()
    Image.new("RGB", (10, 10), "white").save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


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

    def test_reorder_rejects_non_list(self):
        c = self._admin_client()
        r = c.post("/api/admin/landing/features/reorder/", {"ids": "notalist"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_reorder_rejects_partial_ids(self):
        c = self._admin_client()
        f1 = Feature.objects.create(icon="x", title_es="1", title_en="1", order=0)
        f2 = Feature.objects.create(icon="x", title_es="2", title_en="2", order=1)
        r = c.post("/api/admin/landing/features/reorder/", {"ids": [f1.pk]}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_reorder_rejects_unknown_pk(self):
        c = self._admin_client()
        f1 = Feature.objects.create(icon="x", title_es="1", title_en="1", order=0)
        r = c.post("/api/admin/landing/features/reorder/", {"ids": [f1.pk, 999999]}, format="json")
        self.assertEqual(r.status_code, 400)


class TeamAdminTests(TestCase, _AdminAuthMixin):
    def test_team_create_with_photo(self):
        photo = _png_upload()
        c = self._admin_client()
        r = c.post(
            "/api/admin/landing/team/",
            {"name": "Ana", "role_es": "CTO", "role_en": "CTO", "bio_es": "", "bio_en": "",
             "order": 0, "is_active": True, "photo": photo},
            format="multipart",
        )
        self.assertEqual(r.status_code, 201)
        self.assertIn("photo", r.json())
        self.assertTrue(r.json()["photo"])  # non-empty URL
