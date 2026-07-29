from rest_framework import serializers

from .models import OrgAiSettings


class OrgAiSettingsSerializer(serializers.ModelSerializer):
    # Gasto de IA del mes calendario en curso (solo lectura, informativo).
    current_month_cost_usd = serializers.SerializerMethodField()

    class Meta:
        model = OrgAiSettings
        fields = ["enabled", "rate_limit_per_min", "public_rate_limit_per_hour",
                  "monthly_budget_usd", "current_month_cost_usd", "updated_at"]
        read_only_fields = ["current_month_cost_usd", "updated_at"]

    def get_current_month_cost_usd(self, obj):
        from . import metering
        return str(metering.month_cost(obj.organization))
