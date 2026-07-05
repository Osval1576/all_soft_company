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
        try:
            cfg = SlaConfig.objects.get_solo()
            interval = max(1, cfg.scheduler_interval_minutes)
            if cfg.scheduler_enabled:
                run_sla_check()
        except Exception:
            logger.exception("error en el loop del scheduler de SLA")
            interval = 10
        time.sleep(interval * 60)
