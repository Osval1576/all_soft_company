from datetime import datetime, time, date
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from tenancy.testing import create_org
from tickets_t.models import Ticket, TicketMessage, TicketEvent
from sla.models import SlaConfig, SlaPolicy, TicketSla
from sla.calendar_engine import Calendar, add_business_time, business_minutes_between
from sla.levels import compute_levels
from sla.checker import run_sla_check
from notifications.models import Notification

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
    def test_config_provisioned_defaults(self):
        org = create_org("MDT1")
        cfg = SlaConfig.objects.get(organization=org)
        self.assertEqual(cfg.business_timezone, "America/Mexico_City")
        self.assertEqual(cfg.work_days, "1,2,3,4,5")
        self.assertEqual(cfg.at_risk_threshold_pct, 25)
        # idempotente: create_org() de nuevo con el mismo slug no duplica
        create_org("MDT1")
        self.assertEqual(SlaConfig.objects.filter(organization=org).count(), 1)

    def test_policies_seeded(self):
        org = create_org("MDT2")
        self.assertEqual(SlaPolicy.objects.filter(organization=org).count(), 4)
        urgent = SlaPolicy.objects.get(organization=org, priority="URGENT")
        self.assertEqual(urgent.first_response_minutes, 30)
        self.assertEqual(urgent.resolution_minutes, 240)

    def test_ticket_sla_onetoone(self):
        org = create_org("SLT")
        cu = User.objects.create_user(username="c", password="x", role="CUSTOMER", organization=org)
        t = Ticket.objects.create(
            reference="ALS-20260101-000500", titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="OPEN", creado_por=cu,
            organization=org,
        )
        # El signal de creacion (Task 4) ya crea un TicketSla automaticamente;
        # se limpia para probar el modelo/relacion OneToOne en aislamiento.
        TicketSla.objects.filter(ticket=t).delete()
        ts = TicketSla.objects.create(ticket=t, first_response_budget_min=120, resolution_budget_min=960)
        t.refresh_from_db()
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


class LevelTests(TestCase):
    def setUp(self):
        self.org = create_org("SLT")
        cu = User.objects.create_user(username="lc", password="x", role="CUSTOMER", organization=self.org)
        self.t = Ticket.objects.create(
            reference="ALS-20260101-000510", titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="OPEN", creado_por=cu,
            organization=self.org,
        )

    def _sla(self, **kw):
        from sla.models import TicketSla
        defaults = dict(
            ticket=self.t, first_response_budget_min=120, resolution_budget_min=960,
        )
        defaults.update(kw)
        return TicketSla(**defaults)

    def test_met_when_met_at_set(self):
        now = _mx(2026, 1, 5, 12, 0)
        s = self._sla(first_response_met_at=_mx(2026, 1, 5, 11, 0),
                      first_response_due_at=_mx(2026, 1, 5, 11, 30))
        self.assertEqual(compute_levels(s, now, _cal())["fr"], "met")

    def test_breached_when_now_past_due(self):
        now = _mx(2026, 1, 5, 12, 0)
        s = self._sla(first_response_due_at=_mx(2026, 1, 5, 11, 0))
        self.assertEqual(compute_levels(s, now, _cal())["fr"], "breached")

    def test_at_risk_within_threshold(self):
        # presupuesto 120min, umbral 25% => 30min. Due a las 12:00, now 11:40 => quedan 20min laborales <=30 => at_risk
        now = _mx(2026, 1, 5, 11, 40)
        s = self._sla(first_response_due_at=_mx(2026, 1, 5, 12, 0))
        self.assertEqual(compute_levels(s, now, _cal())["fr"], "at_risk")

    def test_ok_when_plenty_left(self):
        # quedan 110min > 30 => ok
        now = _mx(2026, 1, 5, 10, 10)
        s = self._sla(first_response_due_at=_mx(2026, 1, 5, 12, 0))
        self.assertEqual(compute_levels(s, now, _cal())["fr"], "ok")


class SignalTests(TestCase):
    def setUp(self):
        self.org = create_org("SLT")
        self.agent = User.objects.create_user(username="sg_ag", password="x", role="AGENT", organization=self.org)
        self.customer = User.objects.create_user(username="sg_cu", password="x", role="CUSTOMER", organization=self.org)

    def _ticket(self, prioridad="MEDIUM"):
        return Ticket.objects.create(
            reference=f"ALS-20260101-0006{prioridad[:2]}", titulo="T", descripcion="d",
            prioridad=prioridad, estado="OPEN",
            creado_por=self.customer, asignado_a=self.agent,
            organization=self.org,
        )

    def test_ticket_creation_creates_sla_with_budgets(self):
        t = self._ticket("MEDIUM")
        ts = TicketSla.objects.get(ticket=t)
        self.assertEqual(ts.first_response_budget_min, 120)
        self.assertEqual(ts.resolution_budget_min, 960)
        self.assertIsNotNone(ts.first_response_due_at)
        self.assertIsNotNone(ts.resolution_due_at)

    def test_agent_message_marks_first_response(self):
        t = self._ticket()
        TicketMessage.objects.create(ticket=t, sender=self.agent, content="hola")
        t.sla.refresh_from_db()
        self.assertIsNotNone(t.sla.first_response_met_at)
        self.assertEqual(t.sla.fr_level, "met")

    def test_customer_message_does_not_mark_first_response(self):
        t = self._ticket()
        TicketMessage.objects.create(ticket=t, sender=self.customer, content="hola")
        t.sla.refresh_from_db()
        self.assertIsNone(t.sla.first_response_met_at)

    def test_first_response_is_idempotent(self):
        t = self._ticket()
        TicketMessage.objects.create(ticket=t, sender=self.agent, content="uno")
        first = TicketSla.objects.get(ticket=t).first_response_met_at
        TicketMessage.objects.create(ticket=t, sender=self.agent, content="dos")
        self.assertEqual(TicketSla.objects.get(ticket=t).first_response_met_at, first)

    def test_status_resolved_event_sets_resolved_at(self):
        t = self._ticket()
        TicketEvent.objects.create(ticket=t, kind="status_changed", actor=self.agent,
                                   payload={"from": "OPEN", "to": "RESOLVED"})
        t.sla.refresh_from_db()
        self.assertIsNotNone(t.sla.resolved_at)
        self.assertEqual(t.sla.res_level, "met")

    def test_priority_change_recomputes_unmet_deadlines(self):
        t = self._ticket("MEDIUM")
        old_due = TicketSla.objects.get(ticket=t).resolution_due_at
        t.prioridad = "URGENT"
        t.save(update_fields=["prioridad"])
        TicketEvent.objects.create(ticket=t, kind="priority_changed", actor=self.agent,
                                   payload={"from": "MEDIUM", "to": "URGENT"})
        ts = TicketSla.objects.get(ticket=t)
        self.assertEqual(ts.resolution_budget_min, 240)  # URGENT
        self.assertNotEqual(ts.resolution_due_at, old_due)


@override_settings(NOTIFICATIONS_EMAIL_ASYNC=False)
class CheckerTests(TestCase):
    def setUp(self):
        self.org = create_org("SLT")
        self.agent = User.objects.create_user(username="ck_ag", password="x", role="AGENT", organization=self.org)
        self.admin = User.objects.create_user(username="ck_adm", password="x", role="ADMIN", organization=self.org)
        self.customer = User.objects.create_user(username="ck_cu", password="x", role="CUSTOMER", organization=self.org)

    def _ticket_with_breached_res(self):
        t = Ticket.objects.create(
            reference="ALS-20260101-000800", titulo="T", descripcion="d",
            prioridad="HIGH", estado="OPEN", creado_por=self.customer, asignado_a=self.agent,
            organization=self.org,
        )
        ts = t.sla
        # forzar reloj de resolución vencido y 1a respuesta ya cumplida
        ts.first_response_met_at = timezone.now()
        ts.fr_level = "met"
        ts.resolution_due_at = timezone.now() - timezone.timedelta(hours=1)
        ts.res_level = "ok"
        ts.save()
        return t

    def test_check_notifies_on_breach_and_is_idempotent(self):
        t = self._ticket_with_breached_res()
        run_sla_check()
        n1 = Notification.objects.filter(kind="sla_breached").count()
        self.assertGreaterEqual(n1, 1)  # agent + admin(s)
        t.sla.refresh_from_db()
        self.assertEqual(t.sla.res_level, "breached")
        # segunda corrida: no re-notifica
        run_sla_check()
        self.assertEqual(Notification.objects.filter(kind="sla_breached").count(), n1)

    def test_check_ignores_resolved_tickets(self):
        t = self._ticket_with_breached_res()
        t.estado = "RESOLVED"
        t.save(update_fields=["estado"])
        run_sla_check()
        self.assertEqual(Notification.objects.filter(kind="sla_breached").count(), 0)


from rest_framework.test import APIClient


class SerializerSlaTests(TestCase):
    def setUp(self):
        self.org = create_org("SLT")
        self.customer = User.objects.create_user(username="ss_cu", password="x", role="CUSTOMER", organization=self.org)
        self.ticket = Ticket.objects.create(
            reference="ALS-20260101-000900", titulo="T", descripcion="d",
            prioridad="MEDIUM", estado="OPEN", creado_por=self.customer,
            organization=self.org,
        )

    def test_ticket_payload_includes_sla(self):
        c = APIClient()
        c.force_authenticate(user=self.customer)
        r = c.get(f"/api/tickets_t/{self.ticket.id}/")
        self.assertEqual(r.status_code, 200)
        sla = r.json()["sla"]
        self.assertIn("first_response", sla)
        self.assertIn("level", sla["first_response"])
        self.assertIn(sla["first_response"]["level"], ["ok", "at_risk", "breached", "met"])

    def test_ticket_list_avoids_n_plus_one_on_sla(self):
        # Segundo ticket del mismo customer: si `sla` no se precarga con
        # select_related, cada ticket listado dispara un SELECT extra a
        # sla_ticketsla (N+1). El numero de queries debe mantenerse fijo
        # sin importar cuantos tickets haya en la lista.
        Ticket.objects.create(
            reference="ALS-20260101-000901", titulo="T2", descripcion="d",
            prioridad="MEDIUM", estado="OPEN", creado_por=self.customer,
            organization=self.org,
        )
        c = APIClient()
        c.force_authenticate(user=self.customer)
        with self.assertNumQueries(3):
            r = c.get("/api/tickets_t/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 2)


class AdminApiTests(TestCase):
    def setUp(self):
        self.org = create_org("SLT")
        self.admin = User.objects.create_user(username="aa_adm", password="x", role="ADMIN", organization=self.org)
        self.customer = User.objects.create_user(username="aa_cu", password="x", role="CUSTOMER", organization=self.org)

    def _c(self, u):
        c = APIClient(); c.force_authenticate(user=u); return c

    def test_config_requires_admin(self):
        self.assertEqual(self._c(self.customer).get("/api/admin/sla/config/").status_code, 403)

    def test_get_and_patch_config(self):
        c = self._c(self.admin)
        self.assertEqual(c.get("/api/admin/sla/config/").status_code, 200)
        r = c.patch("/api/admin/sla/config/", {"at_risk_threshold_pct": 40}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["at_risk_threshold_pct"], 40)

    def test_list_and_patch_policies(self):
        c = self._c(self.admin)
        r = c.get("/api/admin/sla/policies/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 4)
        r2 = c.patch("/api/admin/sla/policies/",
                     [{"priority": "URGENT", "first_response_minutes": 15, "resolution_minutes": 120}],
                     format="json")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(
            SlaPolicy.objects.get(organization=self.org, priority="URGENT").first_response_minutes, 15)

    def test_holidays_crud(self):
        c = self._c(self.admin)
        r = c.post("/api/admin/sla/holidays/", {"date": "2026-12-25", "name": "Navidad"}, format="json")
        self.assertEqual(r.status_code, 201)
        hid = r.json()["id"]
        self.assertEqual(c.get("/api/admin/sla/holidays/").status_code, 200)
        self.assertEqual(c.delete(f"/api/admin/sla/holidays/{hid}/").status_code, 204)


from io import StringIO
from unittest import mock

from django.core.management import call_command


class CheckSlaLoopTests(TestCase):
    def setUp(self):
        org = create_org("CKL")
        cfg = SlaConfig.objects.get(organization=org)
        cfg.scheduler_interval_minutes = 1
        cfg.scheduler_enabled = True
        cfg.save()

    @mock.patch("sla.management.commands.check_sla.time.sleep")
    def test_loop_corre_max_loops_pasadas_y_duerme_el_intervalo(self, sleep_mock):
        out = StringIO()
        call_command("check_sla", "--loop", "--max-loops=2", stdout=out)
        self.assertEqual(out.getvalue().count("SLA check:"), 2)
        sleep_mock.assert_called_once_with(60)  # 1 min entre pasada 1 y 2; tras la última no duerme

    def test_sin_loop_una_pasada(self):
        out = StringIO()
        call_command("check_sla", stdout=out)
        self.assertEqual(out.getvalue().count("SLA check:"), 1)


class PerOrgSlaTests(TestCase):
    def setUp(self):
        from tenancy.testing import create_org
        self.a = create_org("SLA1")
        self.b = create_org("SLB2")

    def test_config_por_org_independiente(self):
        ca = SlaConfig.objects.get(organization=self.a)
        cb = SlaConfig.objects.get(organization=self.b)
        ca.work_start = time(7, 0); ca.save()
        cb.refresh_from_db()
        self.assertEqual(cb.work_start, time(9, 0))

    def test_calendarios_distintos_producen_deadlines_distintos(self):
        from sla.calendar_engine import get_calendar, add_business_time
        ca = SlaConfig.objects.get(organization=self.a)
        ca.work_end = time(20, 0); ca.save()
        start = datetime(2026, 1, 5, 17, 0, tzinfo=MX)  # lunes 17:00
        due_a = add_business_time(start, 120, get_calendar(self.a))  # hasta 20h: mismo dia
        due_b = add_business_time(start, 120, get_calendar(self.b))  # hasta 18h: cruza al martes
        self.assertNotEqual(due_a, due_b)

    def test_provisioning_al_crear_org(self):
        from tenancy.models import Organization
        org = Organization.objects.create(name="Nueva", slug="NEW")
        self.assertTrue(SlaConfig.objects.filter(organization=org).exists())
        self.assertEqual(SlaPolicy.objects.filter(organization=org).count(), 4)
