from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class CSATResponse(models.Model):
    ticket = models.OneToOneField(
        "tickets_t.Ticket", on_delete=models.CASCADE, related_name="csat"
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CSAT {self.score} - ticket {self.ticket_id}"
