# Wedge de IA — configuración de proveedor

Toda la IA del producto pasa por un **único gateway** (`ai/gateway.py`). El
despliegue elige el proveedor con una variable de entorno; el resto del código
(services, views) es agnóstico.

## Elegir proveedor

```bash
AI_FEATURES_ENABLED=true      # enciende las features de IA (gateado además por plan)
AI_PROVIDER=anthropic         # anthropic (Claude) | gemini (Google) | openai (ChatGPT)
```

Y la **key del proveedor elegido** (solo una hace falta):

| `AI_PROVIDER` | Variable de key | SDK |
|---|---|---|
| `anthropic` | `ANTHROPIC_API_KEY` | `anthropic` |
| `gemini` | `GEMINI_API_KEY` (o `GOOGLE_API_KEY`) | `google-genai` |
| `openai` | `OPENAI_API_KEY` | `openai` |

Aliases aceptados en `AI_PROVIDER`: `claude`→anthropic, `google`→gemini,
`chatgpt`/`gpt`→openai.

Si falta la key del proveedor configurado, el gateway levanta `AiNotConfigured`
y las features degradan con gracia (503 en los endpoints de generación; no-op
silencioso en las clasificaciones), sin romper el resto de la app.

## Modelos por tarea (tier)

El gateway pide un **tier** según la tarea y lo mapea al modelo del proveedor:

- `quality` — generación (borrador, resumen, deflección, insights).
- `fast` — clasificación de alto volumen (auto-triage, sentimiento).

Defaults (overrideables por env `AI_<PROVEEDOR>_<TIER>_MODEL`):

| Tier | anthropic | gemini | openai |
|---|---|---|---|
| `quality` | `claude-opus-4-8` | `gemini-flash-latest` | `gpt-5.1` |
| `fast` | `claude-haiku-4-5` | `gemini-flash-lite-latest` | `gpt-5.1-mini` |

Ejemplo de override:

```bash
AI_GEMINI_QUALITY_MODEL=gemini-2.5-pro
AI_OPENAI_FAST_MODEL=gpt-5.1-nano
```

> Ajustá los IDs de modelo a los que tu cuenta del proveedor tenga habilitados.

## Agregar un proveedor nuevo

1. Sumar un adapter `_<proveedor>(system, user_prompt, model, max_tokens) -> str`
   en `ai/gateway.py` (import perezoso del SDK).
2. Registrarlo en `generate()`, en `_PROVIDER_ALIASES` y en `_MODEL_DEFAULTS`.

Nada más cambia: services y views siguen llamando `gateway.generate(...)`.

## Procesamiento async de los hooks (triage, sentimiento, KB, omnicanal)

Los hooks fire-and-forget corren fuera del request vía `config/background.py::run_async`,
en cascada:

- `AI_ASYNC=false` (tests) → inline.
- `AI_TASK_QUEUE=celery` (prod) → se encola en **Celery** (worker aparte, escala).
- si no → **thread daemon** in-process (dev/single-process; sin worker).

### Correr el worker de Celery (prod)
```bash
# broker por defecto: REDIS_URL (el mismo Redis que Channels/cache)
celery -A config worker -l info
# en Windows dev: agregar  --pool=solo
```
Las tasks son fire-and-forget (sin backend de resultado). Se encolan por ruta
punteada (`config.tasks.run_task`), así que no hace falta registrar una task por hook.
