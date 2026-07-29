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
    # Tope de gasto de IA por mes calendario (USD). 0 = sin tope. Al superarlo,
    # ai_enabled() apaga la IA de la org hasta el mes siguiente (degradación
    # elegante). Ver ai/metering.py.
    monthly_budget_usd = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
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


class AiUsage(models.Model):
    """Registro de una llamada de IA para medir costo por tenant (Fase 0).

    Una fila por llamada al gateway (cuando se conoce la org). Alimenta el
    presupuesto mensual (`OrgAiSettings.monthly_budget_usd`) y sirve para
    auditar costo/consumo por org, proveedor, modelo y feature (`source`).
    """
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="ai_usage")
    created_at = models.DateTimeField(auto_now_add=True)
    provider = models.CharField(max_length=20)
    model = models.CharField(max_length=80, blank=True)
    tier = models.CharField(max_length=20, blank=True)
    # Feature que originó la llamada: draft/summary/triage/sentiment/deflect/
    # insights/translate/kb_suggest.
    source = models.CharField(max_length=30, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    class Meta:
        indexes = [models.Index(fields=["organization", "created_at"])]

    def __str__(self):
        return f"AiUsage <{self.organization_id}> {self.source} ${self.cost_usd}"
