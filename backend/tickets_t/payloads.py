def attachment_payload(msg):
    if not msg.attachment:
        return None
    ct = msg.attachment_content_type or ""
    return {
        "name": msg.attachment_name,
        "size": msg.attachment_size,
        "content_type": ct,
        "is_image": ct.startswith("image/"),
        "url": f"/api/tickets_t/{msg.ticket_id}/attachments/{msg.id}/download/",
    }


def message_to_payload(msg):
    return {
        "id": msg.id,
        "ticket": msg.ticket_id,
        "sender": msg.sender_id,
        "sender_username": msg.sender.username,
        "sender_role": getattr(msg.sender, "role", None),
        "content": msg.content,
        "created_at": msg.created_at.isoformat(),
        "attachment": attachment_payload(msg),
    }
