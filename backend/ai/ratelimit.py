"""Rate limiting de IA por tenant (Fase 0 — guardrail de costo/abuso).

Contador de ventana fija sobre el cache de Django (Redis en prod, LocMem en dev/
tests). Barato y suficiente para frenar picos/abuso; no pretende ser exacto en el
borde de la ventana. Los topes salen de `OrgAiSettings` (0 = sin tope).

Se aplica en dos frentes:
- `allow_user(org, user_id)`: acciones de IA autenticadas (borrador, resumen,
  traducción, insights) por usuario/minuto.
- `allow_public(org)`: deflección desde canales públicos (widget, WhatsApp/DM)
  por org/hora — el endpoint anónimo que corre una llamada de IA por consulta.
"""
import time

from django.core.cache import cache

from .models import OrgAiSettings


def _hit(key, limit, window):
    """True si la llamada entra dentro del tope para la ventana actual.

    `cache.add` crea el contador en 0 con TTL solo si no existe (idempotente ante
    concurrencia); `incr` es atómico en Redis. Ante un race donde la clave expira
    entre el add y el incr, se recrea de forma conservadora."""
    cache.add(key, 0, window)
    try:
        n = cache.incr(key)
    except ValueError:
        cache.set(key, 1, window)
        n = 1
    return n <= limit


def allow_user(org, user_id):
    """Acción de IA autenticada. False si el usuario superó su tope por minuto."""
    limit = OrgAiSettings.get_for(org).rate_limit_per_min
    if limit <= 0:
        return True
    org_id = getattr(org, "id", "0")
    bucket = int(time.time()) // 60
    return _hit(f"ai:rl:u:{org_id}:{user_id}:{bucket}", limit, 60)


def allow_public(org):
    """Deflección desde un canal público. False si la org superó su tope horario."""
    limit = OrgAiSettings.get_for(org).public_rate_limit_per_hour
    if limit <= 0:
        return True
    org_id = getattr(org, "id", "0")
    bucket = int(time.time()) // 3600
    return _hit(f"ai:rl:pub:{org_id}:{bucket}", limit, 3600)
