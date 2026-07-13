from rest_framework import serializers
from .models import SlaConfig, SlaPolicy, Holiday


class SlaConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlaConfig
        exclude = ["id", "organization"]


class SlaPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SlaPolicy
        fields = ["priority", "first_response_minutes", "resolution_minutes"]


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ["id", "date", "name"]
