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
