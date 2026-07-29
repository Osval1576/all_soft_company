"""Metering de costo de IA por tenant (Fase 0 — presupuesto).

Registra el costo de cada llamada (`record`) y responde el gasto del mes
(`month_cost`) y si la org superó su presupuesto (`over_budget`). El gasto
mensual se cachea unos segundos para no correr un SUM en cada chequeo (ai_enabled
lo consulta seguido). Todo es resiliente: si el metering falla, la llamada de IA
sigue (no rompe el producto).
"""
import logging
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone

from . import pricing
from .models import AiUsage, OrgAiSettings

logger = logging.getLogger(__name__)

_CACHE_TTL = 120  # segundos


def _month_key(org):
    now = timezone.now()
    return f"ai:cost:{org.id}:{now.year}{now.month:02d}"


def record(org, *, provider, model, tier, source, usage):
    """Registra el costo de una llamada. `usage` = {"input": n, "output": n}.
    No-op si no hay org o usage. Nunca levanta (resiliente)."""
    if org is None or not usage:
        return
    try:
        in_tok = int(usage.get("input", 0) or 0)
        out_tok = int(usage.get("output", 0) or 0)
        cost = pricing.cost_for(provider, model, in_tok, out_tok)
        AiUsage.objects.create(
            organization=org, provider=provider or "", model=model or "",
            tier=tier or "", source=source or "",
            input_tokens=in_tok, output_tokens=out_tok, cost_usd=cost)
        # Mantené el cache al día si ya estaba poblado (evita esperar el TTL).
        cached = cache.get(_month_key(org))
        if cached is not None:
            cache.set(_month_key(org), Decimal(cached) + cost, _CACHE_TTL)
    except Exception:
        logger.warning("metering de IA falló para org %s",
                       getattr(org, "id", None), exc_info=True)


def month_cost(org):
    """Gasto de IA de la org en el mes calendario actual (Decimal USD)."""
    if org is None:
        return Decimal("0")
    key = _month_key(org)
    cached = cache.get(key)
    if cached is not None:
        return Decimal(cached)
    # Filtro por rango (>= inicio de mes), no __year/__month: en MySQL esos
    # lookups usan CONVERT_TZ(), que devuelve NULL si faltan las tablas de tz.
    start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = (AiUsage.objects
             .filter(organization=org, created_at__gte=start)
             .aggregate(s=Sum("cost_usd"))["s"] or Decimal("0"))
    cache.set(key, total, _CACHE_TTL)
    return total


def over_budget(org):
    """True si la org tiene presupuesto (>0) y ya lo alcanzó este mes."""
    if org is None:
        return False
    budget = OrgAiSettings.get_for(org).monthly_budget_usd
    if not budget or budget <= 0:
        return False
    return month_cost(org) >= budget
