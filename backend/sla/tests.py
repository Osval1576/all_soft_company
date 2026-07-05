from datetime import datetime, time, date
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.contrib.auth import get_user_model
from tickets_t.models import Ticket
from sla.models import SlaConfig, SlaPolicy, Holiday, TicketSla
from sla.calendar_engine import Calendar, add_business_time, business_minutes_between

User = get_user_model()

MX = ZoneInfo("America/Mexico_City")
UTC = ZoneInfo("UTC")


def _cal(holidays=None):
    return Calendar(
        tz=MX, work_days={1, 2, 3, 4, 5},
        work_start=time(9, 0), work_end=time(18, 0),
        holidays=set(holidays or []), at_risk_pct=25,
    )


def _mx(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=MX)


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


class CalendarTests(TestCase):
    def test_add_within_same_day(self):
        # Lunes 2026-01-05 10:00 + 120min laborales = 12:00
        start = _mx(2026, 1, 5, 10, 0)
        got = add_business_time(start, 120, _cal()).astimezone(MX)
        self.assertEqual(got, _mx(2026, 1, 5, 12, 0))

    def test_add_rolls_over_night(self):
        # Lunes 17:00 + 120min = Martes 10:00 (1h lunes + 1h martes)
        start = _mx(2026, 1, 5, 17, 0)
        got = add_business_time(start, 120, _cal()).astimezone(MX)
        self.assertEqual(got, _mx(2026, 1, 6, 10, 0))

    def test_add_skips_weekend(self):
        # Viernes 2026-01-09 17:00 + 120min = Lunes 2026-01-12 10:00
        start = _mx(2026, 1, 9, 17, 0)
        got = add_business_time(start, 120, _cal()).astimezone(MX)
        self.assertEqual(got, _mx(2026, 1, 12, 10, 0))

    def test_add_skips_holiday(self):
        # Jueves 2026-01-01 es feriado; miércoles 2025-12-31 17:00 + 120min salta al viernes 2026-01-02 10:00
        cal = _cal(holidays=[date(2026, 1, 1)])
        start = _mx(2025, 12, 31, 17, 0)
        got = add_business_time(start, 120, cal).astimezone(MX)
        self.assertEqual(got, _mx(2026, 1, 2, 10, 0))

    def test_add_before_hours_snaps_to_open(self):
        # Lunes 07:00 + 60min = Lunes 10:00 (arranca a las 09:00)
        start = _mx(2026, 1, 5, 7, 0)
        got = add_business_time(start, 60, _cal()).astimezone(MX)
        self.assertEqual(got, _mx(2026, 1, 5, 10, 0))

    def test_between_same_day(self):
        a = _mx(2026, 1, 5, 10, 0)
        b = _mx(2026, 1, 5, 12, 30)
        self.assertEqual(business_minutes_between(a, b, _cal()), 150)

    def test_between_spans_night(self):
        # Lunes 17:00 → Martes 10:00 = 60 (lun) + 60 (mar) = 120
        a = _mx(2026, 1, 5, 17, 0)
        b = _mx(2026, 1, 6, 10, 0)
        self.assertEqual(business_minutes_between(a, b, _cal()), 120)

    def test_between_clamps_outside_hours(self):
        # 07:00 → 20:00 mismo día laboral = jornada completa 9h = 540
        a = _mx(2026, 1, 5, 7, 0)
        b = _mx(2026, 1, 5, 20, 0)
        self.assertEqual(business_minutes_between(a, b, _cal()), 540)
