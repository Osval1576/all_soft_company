from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        TICKET_CREATED = "ticket_created", "Ticket creado"
        ASSIGNED = "assigned", "Asignado"
        NEW_MESSAGE = "new_message", "Nuevo mensaje"
        STATUS_CHANGED = "status_changed", "Cambio de estado"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    ticket = models.ForeignKey(
        "tickets_t.Ticket", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        return f"{self.kind} -> {self.recipient_id}"


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notif_prefs"
    )
    email_on_assigned = models.BooleanField(default=True)
    email_on_new_message = models.BooleanField(default=True)
    email_on_status_changed = models.BooleanField(default=True)
    email_on_ticket_created = models.BooleanField(default=True)

    @classmethod
    def for_user(cls, user):
        obj, _ = cls.objects.get_or_create(user=user)
        return obj

    def __str__(self):
        return f"prefs<{self.user_id}>"
