from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone


def _token():
    return uuid4().hex


def _verif_expiry():
    return timezone.now() + timedelta(hours=48)


def _invite_expiry():
    return timezone.now() + timedelta(days=7)


class EmailVerificationToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="email_verification")
    token = models.CharField(max_length=64, unique=True, default=_token)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_verif_expiry)
    used_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        return self.used_at is None and timezone.now() < self.expires_at


class Invitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        ACCEPTED = "accepted", "Aceptada"
        REVOKED = "revoked", "Revocada"

    organization = models.ForeignKey("tenancy.Organization", on_delete=models.CASCADE,
                                     related_name="invitations")
    email = models.EmailField()
    role = models.CharField(max_length=20)  # AGENT | CUSTOMER
    token = models.CharField(max_length=64, unique=True, default=_token)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="invitations_sent")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_invite_expiry)

    # Unicidad de invitación PENDIENTE por (organization, email) se valida en el
    # serializer (H2-T3): MySQL no soporta UniqueConstraint condicional (W036).

    def is_acceptable(self):
        return self.status == self.Status.PENDING and timezone.now() < self.expires_at
