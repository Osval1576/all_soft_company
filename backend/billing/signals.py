from datetime import timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


@receiver(post_save, sender="tenancy.Organization")
def provision_org_subscription(sender, instance, created, **kwargs):
    if not created:
        return
    from .models import Plan, Subscription
    pro = Plan.objects.filter(key="pro").first()
    if pro is None:
        return  # planes aun no seedeados (p.ej. durante una data-migration)
    Subscription.objects.get_or_create(
        organization=instance,
        defaults={"plan": pro, "status": Subscription.Status.TRIAL,
                  "trial_ends_at": timezone.now() + timedelta(days=14)})
