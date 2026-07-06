def is_eligible(ticket):
    return ticket.estado in ("RESOLVED", "CLOSED")
