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
