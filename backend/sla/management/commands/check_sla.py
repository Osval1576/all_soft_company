from django.core.management.base import BaseCommand
from sla.checker import run_sla_check


class Command(BaseCommand):
    help = "Chequea SLAs de tickets abiertos y notifica cruces de nivel."

    def handle(self, *args, **options):
        result = run_sla_check()
        self.stdout.write(self.style.SUCCESS(
            f"SLA check: {result['checked']} revisados, {result['notified']} notificaciones."
        ))
