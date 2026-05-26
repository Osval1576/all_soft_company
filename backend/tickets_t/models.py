from django.conf import settings
from django.db import models
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response



class Ticket(models.Model):
    class Priority(models.TextChoices):
        LOW = "LOW", "Baja"
        MEDIUM = "MEDIUM", "Media"
        HIGH = "HIGH", "Alta"
        URGENT = "URGENT", "Urgente"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Abierto"
        IN_PROGRESS = "IN_PROGRESS", "En proceso"
        RESOLVED = "RESOLVED", "Resuelto"
        CLOSED = "CLOSED", "Cerrado"

    reference = models.CharField(max_length=32, unique=True, db_index=True)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()

    prioridad = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    estado = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tickets_creados",
    )
    asignado_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_asignados",
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return f"{self.reference} - {self.titulo}"



class TicketMessage(models.Model):
    ticket = models.ForeignKey("tickets_t.Ticket", on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


