from django.conf import settings
from django.db import models

class TicketMessage(models.Model):
    ticket = models.ForeignKey("tickets_t.Ticket", on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]