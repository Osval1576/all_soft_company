"""Lógica del wedge de IA sobre el modelo de datos de tickets.

Fase 1A: auto-borrador de respuesta para el agente. Gateado por plan (Pro/
Business, igual que branding) + flag global AI_FEATURES_ENABLED.
"""
from django.conf import settings


def ai_enabled(org):
    """True si la org puede usar features de IA (flag global + plan pago)."""
    if not getattr(settings, "AI_FEATURES_ENABLED", False):
        return False
    if org is None:
        return False
    sub = getattr(org, "subscription", None)
    if sub is None:
        return False
    return sub.effective_plan.key in ("pro", "business")


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
    return gateway.generate(system=system, user_prompt=user_prompt)


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
    model = getattr(settings, "AI_SUMMARY_MODEL", None)
    return gateway.generate(system=system, user_prompt=user_prompt, model=model)


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
    model = getattr(settings, "AI_TRIAGE_MODEL", "claude-haiku-4-5")
    raw = gateway.generate(system=system, user_prompt=user_prompt, max_tokens=8, model=model)
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
    model = getattr(settings, "AI_SENTIMENT_MODEL", "claude-haiku-4-5")
    raw = gateway.generate(system=system, user_prompt=user_prompt, max_tokens=8, model=model)
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


def answer_from_kb(query, articles):
    """Genera una respuesta a partir de los artículos. Devuelve el texto, o None
    si el modelo indica que la KB no alcanza (sentinela NO_SE). Puede propagar
    excepciones del gateway: el llamador decide la degradación."""
    from . import gateway
    system, user_prompt = build_deflection_prompt(query, articles)
    model = getattr(settings, "AI_DEFLECT_MODEL", None)  # None -> usa AI_DRAFT_MODEL
    raw = gateway.generate(system=system, user_prompt=user_prompt, model=model)
    text = (raw or "").strip()
    if not text or text.upper().startswith(NO_ANSWER):
        return None
    return text
