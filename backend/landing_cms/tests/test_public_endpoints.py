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
