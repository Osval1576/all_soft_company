import logging
import threading
import time

logger = logging.getLogger(__name__)

_started = False


def start_scheduler():
    global _started
    if _started:
        return
    _started = True
    t = threading.Thread(target=_loop, name="sla-scheduler", daemon=True)
    t.start()


def _loop():
    from .checker import run_sla_check
    from .models import SlaConfig
    while True:
        interval = 10
        try:
            # scheduler por org: una pasada cubre todas las orgs activas; la
            # cadencia toma el intervalo mas exigente entre orgs activas con
            # el scheduler habilitado.
            active_cfgs = list(SlaConfig.objects.filter(
                organization__is_active=True, scheduler_enabled=True))
            if active_cfgs:
                interval = max(1, min(c.scheduler_interval_minutes for c in active_cfgs))
                run_sla_check()
        except Exception:
            logger.exception("error en el loop del scheduler de SLA")
            interval = 10
        time.sleep(interval * 60)
