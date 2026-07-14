from django.db import models


class SlaConfig(models.Model):
    organization = models.OneToOneField(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="sla_config",
    )
    business_timezone = models.CharField(max_length=64, default="America/Mexico_City")
    work_days = models.CharField(max_length=20, default="1,2,3,4,5")  # ISO weekday 1=Lun..7=Dom
    work_start = models.TimeField(default="09:00")
    work_end = models.TimeField(default="18:00")
    at_risk_threshold_pct = models.PositiveIntegerField(default=25)
    scheduler_interval_minutes = models.PositiveIntegerField(default=10)
    scheduler_enabled = models.BooleanField(default=True)


class SlaPolicy(models.Model):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
    )
    priority = models.CharField(max_length=20)  # Ticket.Priority values
    first_response_minutes = models.PositiveIntegerField()
    resolution_minutes = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "priority"],
                                    name="uniq_policy_org_priority"),
        ]

    def __str__(self):
        return f"{self.priority}: {self.first_response_minutes}/{self.resolution_minutes}"


class Holiday(models.Model):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
    )
    date = models.DateField()
    name = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "date"],
                                    name="uniq_holiday_org_date"),
        ]

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
