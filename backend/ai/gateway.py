"""Gateway de IA — punto ÚNICO que habla con el proveedor de LLM (Fase 0).

Multi-proveedor por despliegue: el cliente elige "anthropic" (Claude), "gemini"
(Google) u "openai" (ChatGPT) con la variable AI_PROVIDER, y provee la key
correspondiente por entorno. El resto del código (services/views) es agnóstico:
llama a `generate(system=, user_prompt=, tier=)` y no sabe qué proveedor hay
detrás. Los tests mockean `ai.gateway.generate`, así que este módulo importa sin
ninguno de los SDKs instalados (imports perezosos por adapter).

Selección de modelo por (proveedor, tier): "quality" para generación (borrador,
resumen, deflección, insights) y "fast" para clasificación de alto volumen
(triage, sentimiento). Overrideable por env: AI_<PROVIDER>_<TIER>_MODEL,
p. ej. AI_GEMINI_QUALITY_MODEL=gemini-2.5-pro.
"""
import os

from django.conf import settings

# Aliases de proveedor -> nombre canónico.
_PROVIDER_ALIASES = {
    "anthropic": "anthropic", "claude": "anthropic",
    "gemini": "gemini", "google": "gemini",
    "openai": "openai", "chatgpt": "openai", "gpt": "openai",
}

# Modelo por defecto (proveedor, tier). Overrideable por env.
_MODEL_DEFAULTS = {
    "anthropic": {"quality": "claude-opus-4-8", "fast": "claude-haiku-4-5"},
    "gemini": {"quality": "gemini-flash-latest", "fast": "gemini-flash-lite-latest"},
    "openai": {"quality": "gpt-5.1", "fast": "gpt-5.1-mini"},
}

# Clientes cacheados por proceso (uno por proveedor).
_clients = {}


class AiNotConfigured(RuntimeError):
    """La feature de IA está habilitada pero falta la credencial del proveedor."""


def _provider():
    raw = (os.environ.get("AI_PROVIDER")
           or getattr(settings, "AI_PROVIDER", "") or "anthropic").strip().lower()
    return _PROVIDER_ALIASES.get(raw, raw)


def _model_for(provider, tier):
    env_key = f"AI_{provider.upper()}_{tier.upper()}_MODEL"
    return os.environ.get(env_key) or _MODEL_DEFAULTS.get(provider, {}).get(tier)


def generate(*, system, user_prompt, tier="quality", max_tokens=1024):
    """Una sola llamada al LLM del proveedor configurado. Devuelve texto plano.

    Levanta AiNotConfigured si falta la key del proveedor. Cualquier otro error
    del proveedor se propaga (el llamador decide el fallback).
    """
    provider = _provider()
    model = _model_for(provider, tier)
    if provider == "anthropic":
        return _anthropic(system, user_prompt, model, max_tokens)
    if provider == "gemini":
        return _gemini(system, user_prompt, model, max_tokens)
    if provider == "openai":
        return _openai(system, user_prompt, model, max_tokens)
    raise AiNotConfigured(f"AI_PROVIDER desconocido: {provider!r}")


# --- Adapters --------------------------------------------------------------

def _anthropic(system, user_prompt, model, max_tokens):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise AiNotConfigured("Falta ANTHROPIC_API_KEY en el entorno del backend.")
    client = _clients.get("anthropic")
    if client is None:
        import anthropic
        client = _clients["anthropic"] = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def _gemini(system, user_prompt, model, max_tokens):
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise AiNotConfigured("Falta GEMINI_API_KEY en el entorno del backend.")
    client = _clients.get("gemini")
    if client is None:
        from google import genai
        client = _clients["gemini"] = genai.Client(api_key=key)
    from google.genai import types
    # Piso holgado: los modelos Gemini "thinking" consumen tokens de salida
    # razonando; con un tope chico (p. ej. el 8 del triage) volverían vacíos.
    resp = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max(max_tokens, 512),
            temperature=0.3,
        ),
    )
    try:
        text = resp.text
    except Exception:
        text = None
    return (text or "").strip()


def _openai(system, user_prompt, model, max_tokens):
    if not os.environ.get("OPENAI_API_KEY"):
        raise AiNotConfigured("Falta OPENAI_API_KEY en el entorno del backend.")
    client = _clients.get("openai")
    if client is None:
        from openai import OpenAI
        client = _clients["openai"] = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        # max_completion_tokens (no max_tokens): requerido por los modelos de
        # razonamiento actuales. Piso holgado por el mismo motivo que Gemini.
        max_completion_tokens=max(max_tokens, 512),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
    )
    return (resp.choices[0].message.content or "").strip()
