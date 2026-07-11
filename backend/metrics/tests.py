# backend/metrics/tests.py
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from tickets_t.models import Ticket
from csat.models import CSATResponse
from sla.models import SlaConfig, SlaPolicy
from sla.calendar_engine import get_calendar
from metrics import services

MX = ZoneInfo("America/Mexico_City")
User = get_user_model()


def _seed_sla():
    SlaConfig.objects.get_solo()
    for prio, fr, res in [("URGENT", 30, 240), ("HIGH", 60, 480),
                          ("MEDIUM", 120, 960), ("LOW", 240, 1920)]:
        SlaPolicy.objects.get_or_create(
            priority=prio,
            defaults={"first_response_minutes": fr, "resolution_minutes": res},
        )


class MetricsFactoryMixin:
    _n = 0

    def setUp(self):
        _seed_sla()
        self.customer = User.objects.create_user("cust", role="CUSTOMER")
        self.tech = User.objects.create_user("tech", role="AGENT")

    def make_ticket(self, *, estado="OPEN", created=None, asignado=None, prioridad="MEDIUM"):
        MetricsFactoryMixin._n += 1
        return Ticket.objects.create(
            reference=f"T{MetricsFactoryMixin._n:05d}",
            titulo="t", descripcion="d", prioridad=prioridad, estado=estado,
            creado_por=self.customer, asignado_a=asignado,
            created_at=created or timezone.now(),
        )


class VolumeAndCsatTests(MetricsFactoryMixin, TestCase):
    def test_volume_totals_counts_by_status(self):
        self.make_ticket(estado="OPEN")
        self.make_ticket(estado="IN_PROGRESS")
        self.make_ticket(estado="RESOLVED")
        self.make_ticket(estado="CLOSED")
        qs = services.windowed_tickets(30)
        self.assertEqual(services.volume_totals(qs),
                         {"total": 4, "resolved": 2, "open": 2})

    def test_csat_summary_average_and_distribution(self):
        for score in (5, 4, 4):
            t = self.make_ticket(estado="RESOLVED")
            CSATResponse.objects.create(ticket=t, score=score)
        self.make_ticket(estado="RESOLVED")  # sin CSAT
        qs = services.windowed_tickets(30)
        out = services.csat_summary(qs)
        self.assertEqual(out["count"], 3)
        # places=3: MySQL's AVG() on an integer column truncates to 4 decimal
        # places at the SQL level (div_precision_increment), so exact float
        # equality to 13/3 isn't attainable under this backend.
        self.assertAlmostEqual(out["average"], 13 / 3, places=3)
        self.assertEqual(out["distribution"], {1: 0, 2: 0, 3: 0, 4: 2, 5: 1})

    def test_csat_summary_empty_returns_none(self):
        qs = services.windowed_tickets(30)
        out = services.csat_summary(qs)
        self.assertIsNone(out["average"])
        self.assertEqual(out["count"], 0)

    def test_window_excludes_older_tickets(self):
        self.make_ticket(created=timezone.now() - timedelta(days=40))
        self.make_ticket(created=timezone.now() - timedelta(days=3))
        self.assertEqual(services.volume_totals(services.windowed_tickets(7))["total"], 1)
        self.assertEqual(services.volume_totals(services.windowed_tickets(90))["total"], 2)


class ComplianceTests(MetricsFactoryMixin, TestCase):
    def _set_sla(self, t, *, fr_met=None, fr_due=None, res_at=None, res_due=None):
        ts = t.sla
        ts.first_response_met_at = fr_met
        ts.first_response_due_at = fr_due
        ts.resolved_at = res_at
        ts.resolution_due_at = res_due
        ts.save()

    def test_resolution_compliance_on_time_vs_late(self):
        base = timezone.now()
        t_ok = self.make_ticket(estado="RESOLVED")
        self._set_sla(t_ok, res_at=base, res_due=base + timedelta(hours=1))      # a tiempo
        t_late = self.make_ticket(estado="RESOLVED")
        self._set_sla(t_late, res_at=base + timedelta(hours=2), res_due=base + timedelta(hours=1))  # tarde
        t_open = self.make_ticket(estado="OPEN")  # sin resolved_at → no cuenta
        out = services.compliance(services.windowed_tickets(30))
        self.assertAlmostEqual(out["resolution"], 0.5)  # 1 de 2 con desenlace

    def test_first_response_compliance(self):
        base = timezone.now()
        t = self.make_ticket()
        self._set_sla(t, fr_met=base, fr_due=base + timedelta(minutes=30))
        out = services.compliance(services.windowed_tickets(30))
        self.assertEqual(out["first_response"], 1.0)

    def test_compliance_none_when_no_outcome(self):
        self.make_ticket(estado="OPEN")
        out = services.compliance(services.windowed_tickets(30))
        self.assertIsNone(out["resolution"])
        self.assertIsNone(out["first_response"])


class AvgTimesTests(MetricsFactoryMixin, TestCase):
    def test_resolution_avg_business_minutes(self):
        cal = get_calendar()
        # Lun 2026-01-05 10:00 MX -> mismo día 12:30 MX = 150 min laborales
        created = datetime(2026, 1, 5, 10, 0, tzinfo=MX)
        t = self.make_ticket(estado="RESOLVED", created=created)
        ts = t.sla
        ts.resolved_at = datetime(2026, 1, 5, 12, 30, tzinfo=MX)
        ts.save()
        out = services.avg_times(services.windowed_tickets(3650), cal)
        self.assertEqual(out["resolution_min"], 150)

    def test_first_response_avg_and_empty(self):
        cal = get_calendar()
        created = datetime(2026, 1, 5, 10, 0, tzinfo=MX)
        t = self.make_ticket(created=created)
        ts = t.sla
        ts.first_response_met_at = datetime(2026, 1, 5, 11, 0, tzinfo=MX)  # 60 min
        ts.save()
        out = services.avg_times(services.windowed_tickets(3650), cal)
        self.assertEqual(out["first_response_min"], 60)
        self.assertIsNone(out["resolution_min"])
