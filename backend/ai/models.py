"""Configuración de IA por tenant (Fase 0 — guardrails de costo/abuso).

`OrgAiSettings` es opt-in y controla el ritmo de uso de IA de una org:
- `enabled`: interruptor de la org, independiente del plan. Permite apagar la IA
  sin bajar de plan (o cumplir un pedido de "no mandar mis datos a la IA").
- `rate_limit_per_min`: tope de acciones de IA autenticadas por usuario/minuto
  (borrador, resumen, traducción, insights). 0 = sin tope.
- `public_rate_limit_per_hour`: tope de llamadas de deflección desde canales
  PÚBLICOS (widget web, WhatsApp/DM) por org/hora. Es el control de costo/abuso
  del endpoint anónimo, que corre una llamada de IA por consulta. 0 = sin tope.

No hace falta backfill: las orgs sin fila usan los defaults vía `get_for`.
"""
from django.db import models

from tenancy.models import Organization


class OrgAiSettings(models.Model):
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="ai_settings")
    enabled = models.BooleanField(default=True)
    rate_limit_per_min = models.PositiveIntegerField(default=30)
    public_rate_limit_per_hour = models.PositiveIntegerField(default=60)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "configuración de IA"
        verbose_name_plural = "configuraciones de IA"

    def __str__(self):
        return f"AI settings <{self.organization.slug}>"

    @classmethod
    def get_for(cls, org):
        """Config de la org: la fila existente o un default sin persistir (los
        valores por defecto del modelo). No escribe en la DB, así que las orgs
        sin fila funcionan igual y sin backfill."""
        if org is None:
            return cls()
        existing = cls.objects.filter(organization=org).first()
        return existing if existing is not None else cls(organization=org)
