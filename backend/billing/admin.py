from django.contrib import admin

from .models import Plan, Subscription, ProcessedStripeEvent


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "max_agents", "stripe_price_id", "is_active", "order")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("organization", "plan", "status", "trial_ends_at", "current_period_end")
    list_filter = ("status", "plan")
    search_fields = ("organization__name",)


admin.site.register(ProcessedStripeEvent)
