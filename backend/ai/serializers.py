from rest_framework import serializers

from .models import OrgAiSettings


class OrgAiSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgAiSettings
        fields = ["enabled", "rate_limit_per_min", "public_rate_limit_per_hour",
                  "updated_at"]
        read_only_fields = ["updated_at"]
