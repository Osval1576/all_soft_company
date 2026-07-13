import logging
import time

from django.core.management.base import BaseCommand

from sla.checker import run_sla_check

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Chequea SLAs de tickets abiertos y notifica cruces de nivel. Con --loop corre como servicio."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true",
                            help="Correr en bucle usando el intervalo de SlaConfig (servicio scheduler).")
        parser.add_argument("--max-loops", type=int, default=0,
                            help="Con --loop: cortar tras N pasadas (0 = infinito; pensado para tests).")

    def handle(self, *args, **options):
        if not options["loop"]:
            self._one_pass()
            return

        from sla.models import SlaConfig
        loops = 0
        while True:
            interval_min = 10
            try:
                cfg = SlaConfig.objects.get_solo()
                interval_min = max(1, cfg.scheduler_interval_minutes)
                if cfg.scheduler_enabled:
                    self._one_pass()
                else:
                    self.stdout.write("scheduler_enabled=False; pasada omitida.")
            except KeyboardInterrupt:
                break
            except Exception:
                logger.exception("error en pasada de check_sla --loop")
            loops += 1
            if options["max_loops"] and loops >= options["max_loops"]:
                break
            try:
                time.sleep(interval_min * 60)
            except KeyboardInterrupt:
                break

    def _one_pass(self):
        result = run_sla_check()
        self.stdout.write(self.style.SUCCESS(
            f"SLA check: {result['checked']} revisados, {result['notified']} notificaciones."
        ))
