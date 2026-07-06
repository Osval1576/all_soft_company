def csat_payload(ticket):
    resp = getattr(ticket, "csat", None)
    if resp is None:
        return None
    return {
        "score": resp.score,
        "comment": resp.comment,
        "created_at": resp.created_at.isoformat(),
    }
