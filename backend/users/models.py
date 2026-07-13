from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        AGENT = "AGENT", "Agent"
        CUSTOMER = "CUSTOMER", "Customer"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )
    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )
