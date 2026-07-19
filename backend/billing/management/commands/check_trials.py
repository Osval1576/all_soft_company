import logging
import time

from django.core.management.base import BaseCommand

from billing.services import expire_trials

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Baja a Free los trials vencidos. Con --loop corre como servicio."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true")
        parser.add_argument("--max-loops", type=int, default=0)
        parser.add_argument("--interval-min", type=int, default=60)

    def handle(self, *args, **o):
        if not o["loop"]:
            self._pass()
            return
        loops = 0
        while True:
            try:
                self._pass()
            except KeyboardInterrupt:
                break
            except Exception:
                logger.exception("error en check_trials --loop")
            loops += 1
            if o["max_loops"] and loops >= o["max_loops"]:
                break
            try:
                time.sleep(max(1, o["interval_min"]) * 60)
            except KeyboardInterrupt:
                break

    def _pass(self):
        n = expire_trials()
        self.stdout.write(self.style.SUCCESS(f"{n} trials vencidos -> Free."))
