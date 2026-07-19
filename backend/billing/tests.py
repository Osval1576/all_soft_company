from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from tenancy.models import Organization
from billing.models import Plan, Subscription
from billing.testing import seed_plans


class ModelTests(TestCase):
    def setUp(self):
        seed_plans()

    def test_seed_planes(self):
        self.assertEqual(Plan.objects.get(key="free").max_agents, 2)
        self.assertEqual(Plan.objects.get(key="pro").max_agents, 10)
        self.assertIsNone(Plan.objects.get(key="business").max_agents)

    def test_org_nueva_arranca_trial_pro(self):
        org = Organization.objects.create(name="Nueva Co", slug="NEWCO")
        sub = org.subscription
        self.assertEqual(sub.plan.key, "pro")
        self.assertEqual(sub.status, "trial")
        self.assertTrue(sub.is_trial_active)

    def test_effective_plan_trial_vencido_es_free(self):
        org = Organization.objects.create(name="Vieja Co", slug="OLDCO")
        sub = org.subscription
        sub.trial_ends_at = timezone.now() - timedelta(days=1)
        sub.save()
        self.assertEqual(sub.effective_plan.key, "free")
