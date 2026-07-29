"""Lógica del wedge de IA sobre el modelo de datos de tickets.

Fase 1A: auto-borrador de respuesta para el agente. Gateado por plan (Pro/
Business, igual que branding) + flag global AI_FEATURES_ENABLED.
"""
from django.conf import settings


def ai_enabled(org):
    """True si la org puede usar features de IA.

    Combina: flag global (AI_FEATURES_ENABLED) + plan pago (Pro/Business) +
    opt-in de la org (OrgAiSettings.enabled). Cualquiera en falso apaga la IA sin
    romper el resto del producto (degradación elegante)."""
    if not getattr(settings, "AI_FEATURES_ENABLED", False):
        return False
    if org is None:
        return False
    sub = getattr(org, "subscription", None)
    if sub is None:
        return False
    if sub.effective_plan.key not in ("pro", "business"):
        return False
    from .models import OrgAiSettings
    if not OrgAiSettings.get_for(org).enabled:
        return False
    from . import metering
    return not metering.over_budget(org)


def build_draft_prompt(ticket):
    """Arma (system, user_prompt) para el borrador a partir del ticket."""
    org_name = ticket.organization.name
    system = (
        f"Sos un agente de soporte de {org_name}. Redactás respuestas claras, "
        "cordiales y accionables, en español, para clientes. Devolvés SOLO el "
        "borrador de la respuesta al cliente, sin preámbulos ni comillas."
    )
    lines = [
        f"Ticket {ticket.reference}: {ticket.titulo}",
        f"Descripción del cliente: {ticket.descripcion}",
        "",
        "Conversación hasta ahora:",
    ]
    msgs = ticket.messages.select_related("sender").order_by("created_at")
    if msgs:
        for m in msgs:
            lines.append(f"- {m.sender.username}: {m.content}")
    else:
        lines.append("(sin mensajes todavía)")
    lines.append("")
    lines.append("Redactá un borrador de respuesta del agente al cliente.")
    return system, "\n".join(lines)


def draft_reply(ticket):
    """Genera un borrador de respuesta para el ticket (llama al gateway de IA)."""
    from . import gateway
    system, user_prompt = build_draft_prompt(ticket)
    return gateway.generate(system=system, user_prompt=user_prompt, tier="quality",
                            org=ticket.organization, source="draft")


# --- Fase 2A: resumen de conversación ----------------------------------------

def build_summary_prompt(ticket):
    """Arma (system, user_prompt) para resumir el hilo del ticket."""
    system = (
        "Sos un asistente de soporte. Resumís el hilo de un ticket para que un "
        "agente que recién lo toma se ponga al día. En español, 3 a 4 líneas: "
        "el problema del cliente, lo que ya se intentó y el próximo paso "
        "pendiente. Sin preámbulos ni comillas."
    )
    lines = [
        f"Ticket {ticket.reference}: {ticket.titulo}",
        f"Descripción del cliente: {ticket.descripcion}",
        "",
        "Conversación:",
    ]
    msgs = ticket.messages.select_related("sender").order_by("created_at")
    if msgs:
        for m in msgs:
            lines.append(f"- {m.sender.username}: {m.content}")
    else:
        lines.append("(sin mensajes todavía)")
    lines.append("")
    lines.append("Resumí el hilo para el agente que se pone al día.")
    return system, "\n".join(lines)


def summarize_ticket(ticket):
    """Genera un resumen del hilo del ticket (llama al gateway de IA)."""
    from . import gateway
    system, user_prompt = build_summary_prompt(ticket)
    return gateway.generate(system=system, user_prompt=user_prompt, tier="quality",
                            org=ticket.organization, source="summary")


# --- Fase 1B: auto-triage de prioridad ---------------------------------------

VALID_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "URGENT"}


def build_triage_prompt(ticket):
    """Arma (system, user_prompt) para clasificar la prioridad del ticket."""
    system = (
        "Sos un clasificador de prioridad para tickets de soporte. Según la "
        "urgencia y el impacto que exprese el cliente, respondés con UNA sola "
        "palabra en mayúsculas: LOW, MEDIUM, HIGH o URGENT. Sin explicaciones "
        "ni puntuación."
    )
    user_prompt = (
        f"Título: {ticket.titulo}\n"
        f"Descripción: {ticket.descripcion}\n\n"
        "Prioridad (LOW, MEDIUM, HIGH o URGENT):"
    )
    return system, user_prompt


def triage_priority(ticket):
    """Clasifica la prioridad del ticket vía IA.

    Devuelve una prioridad válida (LOW/MEDIUM/HIGH/URGENT) o None si la respuesta
    no es una etiqueta reconocida. Puede propagar excepciones del gateway: el
    llamador decide el fallback (auto-triage nunca debe romper la creación).
    """
    from . import gateway
    system, user_prompt = build_triage_prompt(ticket)
    raw = gateway.generate(system=system, user_prompt=user_prompt, max_tokens=8,
                           tier="fast", org=ticket.organization, source="triage")
    val = (raw or "").strip().upper()
    return val if val in VALID_PRIORITIES else None


# --- Fase 2B: sentimiento del mensaje -> prioridad ---------------------------

def build_sentiment_prompt(ticket, message_text):
    """Arma (system, user_prompt) para evaluar la prioridad que amerita el
    último mensaje del cliente según su sentimiento/urgencia."""
    system = (
        "Analizás el sentimiento y la urgencia del último mensaje de un cliente "
        "en un ticket de soporte. Considerá frustración, enojo, impacto en el "
        "negocio y urgencia explícita. Respondés con UNA sola palabra en "
        "mayúsculas indicando la prioridad que amerita: LOW, MEDIUM, HIGH o "
        "URGENT. Sin explicaciones ni puntuación."
    )
    user_prompt = (
        f"Ticket: {ticket.titulo}\n"
        f"Último mensaje del cliente: {message_text}\n\n"
        "Prioridad que amerita (LOW, MEDIUM, HIGH o URGENT):"
    )
    return system, user_prompt


def assess_sentiment_priority(ticket, message_text):
    """Devuelve la prioridad que amerita el mensaje (LOW/MEDIUM/HIGH/URGENT) o
    None si la respuesta no es válida. Puede propagar excepciones del gateway."""
    from . import gateway
    system, user_prompt = build_sentiment_prompt(ticket, message_text)
    raw = gateway.generate(system=system, user_prompt=user_prompt, max_tokens=8,
                           tier="fast", org=ticket.organization, source="sentiment")
    val = (raw or "").strip().upper()
    return val if val in VALID_PRIORITIES else None


# --- Fase 3B: deflección (RAG sobre la KB) -----------------------------------

# Sentinela que devuelve el modelo cuando los artículos no alcanzan para responder.
NO_ANSWER = "NO_SE"


def build_deflection_prompt(query, articles):
    """Arma (system, user_prompt) para responder la consulta usando SOLO los
    artículos de la KB provistos."""
    system = (
        "Sos un asistente de soporte. Respondés la consulta del cliente usando "
        "EXCLUSIVAMENTE la información de los artículos provistos. No inventes ni "
        "uses conocimiento externo. Si los artículos no contienen la respuesta, "
        f"respondés exactamente '{NO_ANSWER}' y nada más. Respondé en español, "
        "claro y breve."
    )
    parts = [f"# {a.title}\n{a.body}" for a in articles]
    context = "\n\n".join(parts) if parts else "(sin artículos)"
    user_prompt = (
        f"Artículos de la base de conocimiento:\n{context}\n\n"
        f"Consulta del cliente: {query}\n\nRespuesta:"
    )
    return system, user_prompt


def answer_from_kb(query, articles, org=None):
    """Genera una respuesta a partir de los artículos. Devuelve el texto, o None
    si el modelo indica que la KB no alcanza (sentinela NO_SE). Puede propagar
    excepciones del gateway: el llamador decide la degradación."""
    from . import gateway
    system, user_prompt = build_deflection_prompt(query, articles)
    raw = gateway.generate(system=system, user_prompt=user_prompt, tier="quality",
                           org=org, source="deflect")
    text = (raw or "").strip()
    if not text or text.upper().startswith(NO_ANSWER):
        return None
    return text


# --- Fase 4: insights de negocio sobre métricas/CSAT -------------------------

def build_insights_prompt(snapshot):
    """Arma (system, user_prompt) para el análisis ejecutivo a partir del snapshot
    de métricas de la org."""
    import json
    system = (
        "Sos un analista de una mesa de ayuda. A partir de las métricas de "
        "soporte de una organización, redactás un análisis ejecutivo breve en "
        "español para el administrador, con tres secciones y viñetas: "
        "1) Tendencias clave, 2) Temas recurrentes, 3) 2 o 3 acciones concretas "
        "recomendadas. Sé específico con los números del resumen. No inventes "
        "datos que no estén en el resumen."
    )
    user_prompt = (
        "Métricas del período (JSON):\n"
        + json.dumps(snapshot, ensure_ascii=False, default=str)
        + "\n\nRedactá el análisis para el administrador."
    )
    return system, user_prompt


def generate_insights(snapshot, org=None):
    """Genera el análisis ejecutivo a partir del snapshot. Puede propagar
    excepciones del gateway (el llamador decide el fallback)."""
    from . import gateway
    system, user_prompt = build_insights_prompt(snapshot)
    return gateway.generate(system=system, user_prompt=user_prompt, max_tokens=1024,
                            tier="quality", org=org, source="insights")


# --- Fase 5.2: KB auto-alimentada (sugerencia desde ticket resuelto) ----------

def build_kb_suggestion_prompt(ticket):
    """Arma (system, user_prompt) para redactar un artículo de KB a partir del
    hilo de un ticket resuelto."""
    system = (
        "Sos un redactor de base de conocimiento. A partir de un ticket de soporte "
        "resuelto, escribís un artículo de KB GENÉRICO y reutilizable (no menciones "
        "datos personales del cliente ni el ticket puntual). Formato ESTRICTO: la "
        "PRIMERA línea es el título (sin prefijos ni comillas); de la segunda línea "
        "en adelante, el contenido en pasos claros. En español."
    )
    lines = [
        f"Título del ticket: {ticket.titulo}",
        f"Descripción del cliente: {ticket.descripcion}",
        "",
        "Conversación:",
    ]
    msgs = list(ticket.messages.select_related("sender").order_by("created_at"))
    for m in msgs:
        lines.append(f"- {m.sender.username}: {m.content}")
    if not msgs:
        lines.append("(sin mensajes)")
    lines.append("")
    lines.append("Escribí el artículo de KB (título en la primera línea, luego el cuerpo).")
    return system, "\n".join(lines)


def suggest_kb_article(ticket):
    """Genera (title, body) para un artículo de KB desde el ticket, o None si la
    respuesta viene vacía. Puede propagar excepciones del gateway."""
    from . import gateway
    system, user_prompt = build_kb_suggestion_prompt(ticket)
    raw = (gateway.generate(system=system, user_prompt=user_prompt, tier="quality",
                            org=ticket.organization, source="kb_suggest") or "").strip()
    if not raw:
        return None
    parts = raw.split("\n", 1)
    title = parts[0].strip().lstrip("#").strip().strip('"')[:200]
    body = parts[1].strip() if len(parts) > 1 else ""
    if not title:
        return None
    return title, body


# --- Fase 5.3: multilingüe (traducción) --------------------------------------

_LANG_NAMES = {
    "es": "español", "en": "inglés", "pt": "portugués", "fr": "francés",
    "it": "italiano", "de": "alemán",
}


def translate_text(text, target_lang="es", org=None):
    """Traduce el texto al idioma destino (código ISO, p. ej. 'es', 'en', 'pt').
    Devuelve solo la traducción. Puede propagar excepciones del gateway."""
    from . import gateway
    target = _LANG_NAMES.get(target_lang, target_lang)
    system = (
        f"Sos un traductor profesional. Traducí el texto del usuario al {target}. "
        "Devolvés SOLO la traducción, sin comillas, prefijos ni notas. Si el texto "
        "ya está en ese idioma, lo devolvés igual. Conservá el tono."
    )
    return (gateway.generate(system=system, user_prompt=text, tier="fast",
                             org=org, source="translate") or "").strip()
