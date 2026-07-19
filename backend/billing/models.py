from django.db import models
from django.utils import timezone


class Plan(models.Model):
    key = models.CharField(max_length=20, unique=True)         # free | pro | business
    name = models.CharField(max_length=60)
    max_agents = models.PositiveIntegerField(null=True, blank=True)  # None = ilimitado
    stripe_price_id = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


class Subscription(models.Model):
    class Status(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Activa"
        PAST_DUE = "past_due", "Pago pendiente"
        CANCELED = "canceled", "Cancelada"

    organization = models.OneToOneField("tenancy.Organization", on_delete=models.CASCADE,
                                        related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.TRIAL)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=120, blank=True)
    stripe_subscription_id = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f"{self.organization} · {self.plan.key} ({self.status})"

    @property
    def is_trial_active(self):
        return (self.status == self.Status.TRIAL and self.trial_ends_at is not None
                and timezone.now() < self.trial_ends_at)

    @property
    def effective_plan(self):
        # Trial vencido sin pago => se comporta como Free para el limite.
        if (self.status == self.Status.TRIAL and self.trial_ends_at is not None
                and timezone.now() >= self.trial_ends_at):
            return Plan.objects.filter(key="free").first() or self.plan
        return self.plan


class ProcessedStripeEvent(models.Model):
    event_id = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
