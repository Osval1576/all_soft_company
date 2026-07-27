"""Gateway aislado hacia la API de Claude (Fase 0 del wedge de IA).

Único punto que habla con el SDK de Anthropic — mismo patrón que el gateway de
Stripe en `billing`: un solo lugar, mockeable en tests, sin fugar el cliente al
resto del código. Los tests mockean `ai.gateway.generate`, así que este módulo
importa sin necesidad del paquete `anthropic` (import perezoso).
"""
import os

from django.conf import settings

_client = None


class AiNotConfigured(RuntimeError):
    """La feature de IA está habilitada pero falta la credencial (ANTHROPIC_API_KEY)."""


def _get_client():
    global _client
    if _client is None:
        # Falla temprano y claro si no hay credencial, en vez de un TypeError
        # opaco del SDK al construir los headers.
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise AiNotConfigured("Falta ANTHROPIC_API_KEY en el entorno del backend.")
        import anthropic  # perezoso: solo hace falta en runtime real
        # Lee ANTHROPIC_API_KEY del entorno (o el perfil de `ant auth login`).
        _client = anthropic.Anthropic()
    return _client


def generate(*, system, user_prompt, max_tokens=1024, model=None):
    """Una sola llamada a Claude para generar texto. Devuelve el texto plano.

    Modelo por defecto configurable con AI_DRAFT_MODEL (default claude-opus-5).
    Para bajar costo de generación se puede setear a un modelo Sonnet vía env.
    """
    model = model or getattr(settings, "AI_DRAFT_MODEL", "claude-opus-5")
    resp = _get_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()
