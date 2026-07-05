from django.test import TestCase
from django.contrib.auth import get_user_model
from tickets_t.models import Ticket
from sla.models import SlaConfig, SlaPolicy, Holiday, TicketSla

User = get_user_model()


class ModelTests(TestCase):
    def test_config_singleton_defaults(self):
        cfg = SlaConfig.objects.get_solo()
        self.assertEqual(cfg.pk, 1)
        self.assertEqual(cfg.business_timezone, "America/Mexico_City")
        self.assertEqual(cfg.work_days, "1,2,3,4,5")
        self.assertEqual(cfg.at_risk_threshold_pct, 25)
        # idempotente
        self.assertEqual(SlaConfig.objects.get_solo().pk, 1)
        self.assertEqual(SlaConfig.objects.count(), 1)

    def test_policies_seeded(self):
        self.assertEqual(SlaPolicy.objects.count(), 4)
        urgent = SlaPolicy.objects.get(priority="URGENT")
        self.assertEqual(urgent.first_response_minutes, 30)
        self.assertEqual(urgent.resolution_minutes, 240)

    def test_ticket_sla_onetoone(self):
        cu = User.objects.create_user(username="c", password="x", role="CUSTOMER")
        t = Ticket.objects.create(
            reference="ALS-20260101-000500", titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="OPEN", creado_por=cu,
        )
        ts = TicketSla.objects.create(ticket=t, first_response_budget_min=120, resolution_budget_min=960)
        self.assertEqual(t.sla, ts)
        self.assertEqual(ts.fr_level, "ok")
