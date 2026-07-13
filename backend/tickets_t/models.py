import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .validators import validate_attachment


def attachment_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    now = timezone.now()
    return f"ticket_adjuntos/{now:%Y/%m}/{uuid.uuid4().hex}{ext}"



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
    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        null=True,   # NOT NULL en T7, cuando todo el codigo ya la setea
        blank=True,
        related_name="tickets",
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "created_at"])]

    def __str__(self):
        return f"{self.reference} - {self.titulo}"



class TicketMessage(models.Model):
    ticket = models.ForeignKey("tickets_t.Ticket", on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField()
    attachment = models.FileField(
        upload_to=attachment_upload_to, null=True, blank=True,
        validators=[validate_attachment],
    )
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_size = models.PositiveIntegerField(null=True, blank=True)
    attachment_content_type = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class TicketEvent(models.Model):
    class Kind(models.TextChoices):
        CREATED = "created", "Creado"
        ASSIGNED = "assigned", "Asignado"
        UNASSIGNED = "unassigned", "Desasignado"
        STATUS_CHANGED = "status_changed", "Cambio de estado"
        REOPENED = "reopened", "Reabierto"
        PRIORITY_CHANGED = "priority_changed", "Cambio de prioridad"

    ticket = models.ForeignKey(
        "Ticket",
        on_delete=models.CASCADE,
        related_name="events",
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    actor = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="+",
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["ticket", "created_at"])]

    def __str__(self):
        return f"{self.kind}@{self.ticket_id} by {self.actor_id}"

