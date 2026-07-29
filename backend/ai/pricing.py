"""Precios de referencia por (proveedor, modelo) para medir el costo de IA.

USD por 1.000.000 de tokens (input, output). Los de Anthropic son las tarifas
de la API de primera mano; los de Gemini/OpenAI son estimaciones públicas y
pueden variar por despliegue (planes/regiones). El objetivo es acotar el gasto,
no facturar con exactitud: un modelo sin tarifa conocida cuenta como costo 0
(no rompe el presupuesto, pero conviene agregarlo acá).

Override por despliegue: AI_PRICE_<PROVIDER>_<MODEL>_IN / _OUT (USD por 1M),
p. ej. AI_PRICE_OPENAI_GPT-5.1_IN=1.25 (los puntos del modelo se pasan tal cual).
"""
import os
from decimal import Decimal

# (input_por_millon, output_por_millon) en USD.
_PRICES = {
    "anthropic": {
        "claude-opus-4-8": (Decimal("5"), Decimal("25")),
        "claude-opus-5": (Decimal("5"), Decimal("25")),
        "claude-opus-4-7": (Decimal("5"), Decimal("25")),
        "claude-sonnet-5": (Decimal("3"), Decimal("15")),
        "claude-sonnet-4-6": (Decimal("3"), Decimal("15")),
        "claude-haiku-4-5": (Decimal("1"), Decimal("5")),
    },
    # Estimaciones públicas (revisar contra la consola del proveedor).
    "gemini": {
        "gemini-flash-latest": (Decimal("0.30"), Decimal("2.50")),
        "gemini-flash-lite-latest": (Decimal("0.10"), Decimal("0.40")),
        "gemini-2.5-pro": (Decimal("1.25"), Decimal("10")),
    },
    "openai": {
        "gpt-5.1": (Decimal("1.25"), Decimal("10")),
        "gpt-5.1-mini": (Decimal("0.25"), Decimal("2")),
    },
}

_MILLION = Decimal("1000000")


def _rates(provider, model):
    """(in, out) por millón para (provider, model), con override por env. None si
    no hay tarifa conocida."""
    if provider and model:
        env_in = os.environ.get(f"AI_PRICE_{provider.upper()}_{model.upper()}_IN")
        env_out = os.environ.get(f"AI_PRICE_{provider.upper()}_{model.upper()}_OUT")
        if env_in is not None and env_out is not None:
            try:
                return Decimal(env_in), Decimal(env_out)
            except (ValueError, ArithmeticError):
                pass
    return _PRICES.get(provider, {}).get(model)


def cost_for(provider, model, input_tokens, output_tokens):
    """Costo en USD (Decimal) de una llamada. 0 si el modelo no tiene tarifa."""
    rates = _rates(provider, model)
    if not rates:
        return Decimal("0")
    rate_in, rate_out = rates
    return ((Decimal(input_tokens) * rate_in)
            + (Decimal(output_tokens) * rate_out)) / _MILLION
