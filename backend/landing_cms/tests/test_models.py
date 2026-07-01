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


class FeatureTests(TestCase):
    def test_default_order(self):
        from landing_cms.models import Feature
        f1 = Feature.objects.create(icon="ticket", title_es="A", title_en="A", order=2)
        f2 = Feature.objects.create(icon="user", title_es="B", title_en="B", order=1)
        ids = list(Feature.objects.values_list("pk", flat=True))
        self.assertEqual(ids, [f2.pk, f1.pk])


class LocationTests(TestCase):
    def test_create_with_type(self):
        from landing_cms.models import Location
        loc = Location.objects.create(
            name="Sede", address="Calle 1", lat=19.4, lng=-99.1,
            type="OFICINA", order=1,
        )
        self.assertEqual(loc.type, "OFICINA")
