from rest_framework import serializers

from .models import ChannelAccount


class ChannelAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChannelAccount
        fields = ["id", "channel", "external_id", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]
