from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")


class Calendar:
    def __init__(self, tz, work_days, work_start, work_end, holidays, at_risk_pct):
        self.tz = tz
        self.work_days = set(work_days)      # ISO weekday ints, Mon=1..Sun=7
        self.work_start = work_start          # datetime.time
        self.work_end = work_end              # datetime.time
        self.holidays = set(holidays)         # set of date
        self.at_risk_pct = at_risk_pct

    def is_workday(self, d):
        return d.isoweekday() in self.work_days and d not in self.holidays

    def _start_of(self, local_dt):
        return local_dt.replace(hour=self.work_start.hour, minute=self.work_start.minute,
                                second=0, microsecond=0)

    def _end_of(self, local_dt):
        return local_dt.replace(hour=self.work_end.hour, minute=self.work_end.minute,
                                second=0, microsecond=0)


def get_calendar():
    from .models import SlaConfig, Holiday
    cfg = SlaConfig.objects.get_solo()
    tz = ZoneInfo(cfg.business_timezone)
    work_days = {int(x) for x in cfg.work_days.split(",") if x.strip()}
    holidays = set(Holiday.objects.values_list("date", flat=True))
    return Calendar(tz, work_days, cfg.work_start, cfg.work_end, holidays,
                    cfg.at_risk_threshold_pct)


def _next_working_instant(local, cal):
    """Devuelve el primer instante >= local que cae dentro de una ventana laboral."""
    while True:
        d = local.date()
        if cal.is_workday(d):
            ws = cal._start_of(local)
            we = cal._end_of(local)
            if local < ws:
                return ws
            if local < we:
                return local
        # no laborable o pasó el cierre: saltar al inicio del día siguiente
        nxt = local + timedelta(days=1)
        local = cal._start_of(nxt)


def add_business_time(start_dt, minutes, cal):
    remaining = timedelta(minutes=minutes)
    local = start_dt.astimezone(cal.tz)
    while True:
        local = _next_working_instant(local, cal)
        avail = cal._end_of(local) - local
        if remaining <= avail:
            return (local + remaining).astimezone(UTC)
        remaining -= avail
        # ir al inicio del día siguiente (el próximo instante laboral lo re-snapea)
        local = cal._start_of(local + timedelta(days=1))


def business_minutes_between(a, b, cal):
    if b <= a:
        return 0
    local_b = b.astimezone(cal.tz)
    cur = a.astimezone(cal.tz)
    total = timedelta()
    while cur < local_b:
        d = cur.date()
        if cal.is_workday(d):
            ws = cal._start_of(cur)
            we = cal._end_of(cur)
            seg_start = max(cur, ws)
            seg_end = min(we, local_b)
            if seg_end > seg_start:
                total += (seg_end - seg_start)
        cur = cal._start_of(cur + timedelta(days=1))
    return int(total.total_seconds() // 60)
