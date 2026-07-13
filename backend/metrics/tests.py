# backend/metrics/tests.py
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from tenancy.testing import create_org
from tickets_t.models import Ticket
from csat.models import CSATResponse
from sla.models import SlaConfig, SlaPolicy
from sla.calendar_engine import get_calendar
from metrics import services

MX = ZoneInfo("America/Mexico_City")
User = get_user_model()


def _seed_sla(org):
    # create_org() ya provisiona SlaConfig/SlaPolicy per-org (via signal +
    # refuerzo idempotente); esto queda como no-op defensivo por si algun
    # test necesita forzar la creacion antes de crear el ticket.
    SlaConfig.objects.get_or_create(organization=org)
    for prio, fr, res in [("URGENT", 30, 240), ("HIGH", 60, 480),
                          ("MEDIUM", 120, 960), ("LOW", 240, 1920)]:
        SlaPolicy.objects.get_or_create(
            organization=org, priority=prio,
            defaults={"first_response_minutes": fr, "resolution_minutes": res},
        )


class MetricsFactoryMixin:
    _n = 0

    def setUp(self):
        self.org = create_org("MET")
        _seed_sla(self.org)
        self.customer = User.objects.create_user("cust", role="CUSTOMER", organization=self.org)
        self.tech = User.objects.create_user("tech", role="AGENT", organization=self.org)

    def make_ticket(self, *, estado="OPEN", created=None, asignado=None, prioridad="MEDIUM"):
        MetricsFactoryMixin._n += 1
        return Ticket.objects.create(
            reference=f"T{MetricsFactoryMixin._n:05d}",
            titulo="t", descripcion="d", prioridad=prioridad, estado=estado,
            creado_por=self.customer, asignado_a=asignado,
            created_at=created or timezone.now(),
            organization=self.org,
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

    def test_first_response_compliance_late(self):
        base = timezone.now()
        t = self.make_ticket()
        self._set_sla(t, fr_met=base + timedelta(minutes=45), fr_due=base + timedelta(minutes=30))
        out = services.compliance(services.windowed_tickets(30))
        self.assertEqual(out["first_response"], 0.0)

    def test_resolution_compliance_excludes_partial_null(self):
        base = timezone.now()
        t_partial = self.make_ticket(estado="RESOLVED")
        self._set_sla(t_partial, res_at=base, res_due=None)  # resolution_due_at ausente
        out = services.compliance(services.windowed_tickets(30))
        self.assertIsNone(out["resolution"])  # no cuenta en el denominador


class AvgTimesTests(MetricsFactoryMixin, TestCase):
    def test_resolution_avg_business_minutes(self):
        cal = get_calendar(self.org)
        # Lun 2026-01-05 10:00 MX -> mismo día 12:30 MX = 150 min laborales
        created = datetime(2026, 1, 5, 10, 0, tzinfo=MX)
        t = self.make_ticket(estado="RESOLVED", created=created)
        ts = t.sla
        ts.resolved_at = datetime(2026, 1, 5, 12, 30, tzinfo=MX)
        ts.save()
        out = services.avg_times(services.windowed_tickets(3650), cal)
        self.assertEqual(out["resolution_min"], 150)

    def test_first_response_avg_and_empty(self):
        cal = get_calendar(self.org)
        created = datetime(2026, 1, 5, 10, 0, tzinfo=MX)
        t = self.make_ticket(created=created)
        ts = t.sla
        ts.first_response_met_at = datetime(2026, 1, 5, 11, 0, tzinfo=MX)  # 60 min
        ts.save()
        out = services.avg_times(services.windowed_tickets(3650), cal)
        self.assertEqual(out["first_response_min"], 60)
        self.assertIsNone(out["resolution_min"])

    def test_resolution_avg_crosses_weekend(self):
        cal = get_calendar(self.org)
        # Viernes 2026-01-09 17:00 MX -> Lunes 2026-01-12 10:00 MX.
        # Laboral: vie 17:00-18:00 (60) + lun 09:00-10:00 (60) = 120 min.
        # Un bug wall-clock daría ~3900 min (65 h), así que este caso lo detecta.
        created = datetime(2026, 1, 9, 17, 0, tzinfo=MX)
        t = self.make_ticket(estado="RESOLVED", created=created)
        ts = t.sla
        ts.resolved_at = datetime(2026, 1, 12, 10, 0, tzinfo=MX)
        ts.save()
        out = services.avg_times(services.windowed_tickets(3650), cal)
        self.assertEqual(out["resolution_min"], 120)


class TrendTests(MetricsFactoryMixin, TestCase):
    def test_trend_shape_and_zero_fill(self):
        self.make_ticket(created=timezone.now() - timedelta(days=1))
        self.make_ticket(created=timezone.now() - timedelta(days=1))
        series = services.trend(services.windowed_tickets(7), 7)
        self.assertEqual(len(series), 8)                       # window + 1 días
        self.assertEqual(sorted(series, key=lambda r: r["date"]), series)  # asc
        self.assertEqual(sum(r["created"] for r in series), 2)
        self.assertTrue(any(r["created"] == 0 for r in series))  # hay zero-fill
        self.assertTrue(all(set(r) == {"date", "created", "resolved"} for r in series))

    def test_trend_counts_resolved(self):
        t = self.make_ticket(estado="RESOLVED", created=timezone.now() - timedelta(days=1))
        ts = t.sla
        ts.resolved_at = timezone.now() - timedelta(days=1)
        ts.save()
        series = services.trend(services.windowed_tickets(7), 7)
        self.assertEqual(sum(r["resolved"] for r in series), 1)
        self.assertEqual(sum(r["created"] for r in series), 1)


class RankingTests(MetricsFactoryMixin, TestCase):
    def test_ranking_groups_by_technician_and_sorts(self):
        cal = get_calendar(self.org)
        base = timezone.now()
        tech2 = User.objects.create_user("tech2", role="AGENT", first_name="Ana", last_name="Paz", organization=self.org)
        # tech: 1 resuelto a tiempo (sla_pct=1.0)
        t1 = self.make_ticket(estado="RESOLVED", asignado=self.tech)
        ts = t1.sla; ts.resolved_at = base; ts.resolution_due_at = base + timedelta(hours=1); ts.save()
        CSATResponse.objects.create(ticket=t1, score=5)
        # tech2: 1 resuelto tarde (sla_pct=0.0)
        t2 = self.make_ticket(estado="RESOLVED", asignado=tech2)
        ts2 = t2.sla; ts2.resolved_at = base + timedelta(hours=2); ts2.resolution_due_at = base + timedelta(hours=1); ts2.save()
        # ticket sin asignar → no aparece
        self.make_ticket(estado="OPEN", asignado=None)
        rows = services.technician_ranking(services.windowed_tickets(30), cal)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["technician_id"], self.tech.id)   # sla_pct 1.0 primero
        self.assertEqual(rows[0]["sla_pct"], 1.0)
        self.assertEqual(rows[0]["csat_avg"], 5.0)
        self.assertEqual(rows[1]["sla_pct"], 0.0)
        self.assertEqual(rows[1]["name"], "Ana Paz")

    def test_ranking_sorts_none_last_and_covers_optional_fields(self):
        cal = get_calendar(self.org)
        base = timezone.now()
        # técnico con un resuelto a tiempo -> sla_pct 1.0, con CSAT y tiempo de resolución
        t1 = self.make_ticket(estado="RESOLVED", asignado=self.tech)
        ts = t1.sla
        ts.resolved_at = base
        ts.resolution_due_at = base + timedelta(hours=1)
        ts.save()
        CSATResponse.objects.create(ticket=t1, score=5)
        # técnico con sólo un ticket OPEN (sin desenlace) -> sla_pct None, csat None
        tech3 = User.objects.create_user("tech3r", role="AGENT", organization=self.org)
        self.make_ticket(estado="OPEN", asignado=tech3)
        rows = services.technician_ranking(services.windowed_tickets(30), cal)
        self.assertEqual(rows[-1]["technician_id"], tech3.id)   # None al final
        self.assertIsNone(rows[-1]["sla_pct"])
        self.assertIsNone(rows[-1]["csat_avg"])
        self.assertEqual(rows[0]["sla_pct"], 1.0)
        self.assertIsNotNone(rows[0]["avg_resolution_min"])


class EndpointTests(MetricsFactoryMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user("admin", role="ADMIN", organization=self.org)
        self.client = APIClient()

    def test_admin_endpoint_requires_admin(self):
        self.client.force_authenticate(self.tech)
        self.assertEqual(self.client.get("/api/metrics/admin/").status_code, 403)
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get("/api/metrics/admin/").status_code, 403)
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/metrics/admin/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.data), {"window", "totals", "compliance", "avg_times", "csat", "trend", "ranking"})
        self.assertEqual(r.data["window"], 30)

    def test_me_endpoint_scopes_to_self_and_has_benchmark(self):
        tech2 = User.objects.create_user("tech2b", role="AGENT", organization=self.org)
        self.make_ticket(estado="RESOLVED", asignado=self.tech)
        self.make_ticket(estado="RESOLVED", asignado=tech2)
        self.client.force_authenticate(self.tech)
        r = self.client.get("/api/metrics/me/?window=7")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["window"], 7)
        self.assertEqual(r.data["totals"]["total"], 1)       # sólo el suyo
        self.assertIn("benchmark", r.data)
        self.assertNotIn("ranking", r.data)

    def test_me_endpoint_forbidden_for_admin_and_customer(self):
        for u in (self.admin, self.customer):
            self.client.force_authenticate(u)
            self.assertEqual(self.client.get("/api/metrics/me/").status_code, 403)

    def test_invalid_window_defaults_to_30(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/metrics/admin/?window=999").data["window"], 30)
        self.assertEqual(self.client.get("/api/metrics/admin/?window=abc").data["window"], 30)

    def test_admin_endpoint_platform_superuser_without_org_returns_404(self):
        # Superuser de plataforma (organization=None) no debe 500 al pegarle
        # a metricas scoped por organizacion: 404 explicito antes de get_calendar().
        su = User.objects.create_user(
            "platform_su_metrics", role="ADMIN", is_superuser=True, organization=None)
        self.client.force_authenticate(su)
        r = self.client.get("/api/metrics/admin/")
        self.assertEqual(r.status_code, 404)

    def test_admin_query_count_independent_of_ticket_count(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        self.client.force_authenticate(self.admin)
        # baseline con pocos tickets asignados a UN técnico fijo
        self.make_ticket(estado="RESOLVED", asignado=self.tech)
        with CaptureQueriesContext(connection) as ctx1:
            self.client.get("/api/metrics/admin/")
        baseline = len(ctx1.captured_queries)
        # agregar más tickets al MISMO técnico: el diseño agrega en DB + un loop
        # acotado por #técnicos (fijo), así que el conteo NO debe crecer con #tickets.
        # Si crece, es un N+1 real y este assert falla.
        for _ in range(8):
            self.make_ticket(estado="RESOLVED", asignado=self.tech)
        with CaptureQueriesContext(connection) as ctx2:
            self.client.get("/api/metrics/admin/")
        self.assertEqual(len(ctx2.captured_queries), baseline)
