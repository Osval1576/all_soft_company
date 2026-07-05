from django.db import models
from django.conf import settings


class SingletonManager(models.Manager):
    def get_solo(self):
        obj, created = self.get_or_create(pk=1)
        if created:
            # Tras el create, releer de la DB: los defaults "crudos" (p.ej. TimeField
            # default="09:00") quedan como str en la instancia en memoria en vez de
            # castearse a datetime.time, lo que rompe Calendar._start_of/_end_of.
            obj.refresh_from_db()
        return obj


class SlaConfig(models.Model):
    business_timezone = models.CharField(max_length=64, default="America/Mexico_City")
    work_days = models.CharField(max_length=20, default="1,2,3,4,5")  # ISO weekday 1=Lun..7=Dom
    work_start = models.TimeField(default="09:00")
    work_end = models.TimeField(default="18:00")
    at_risk_threshold_pct = models.PositiveIntegerField(default=25)
    scheduler_interval_minutes = models.PositiveIntegerField(default=10)
    scheduler_enabled = models.BooleanField(default=True)

    objects = SingletonManager()

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class SlaPolicy(models.Model):
    priority = models.CharField(max_length=20, unique=True)  # Ticket.Priority values
    first_response_minutes = models.PositiveIntegerField()
    resolution_minutes = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.priority}: {self.first_response_minutes}/{self.resolution_minutes}"


class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.date} {self.name}"


class TicketSla(models.Model):
    ticket = models.OneToOneField(
        "tickets_t.Ticket", on_delete=models.CASCADE, related_name="sla"
    )
    first_response_due_at = models.DateTimeField(null=True, blank=True)
    first_response_met_at = models.DateTimeField(null=True, blank=True)
    first_response_budget_min = models.PositiveIntegerField(null=True, blank=True)
    resolution_due_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_budget_min = models.PositiveIntegerField(null=True, blank=True)
    fr_level = models.CharField(max_length=12, default="ok")   # ok|at_risk|breached|met
    res_level = models.CharField(max_length=12, default="ok")
