from rest_framework import serializers
from .models import (
    HeroContent, AboutContent, SiteSettings,
    Feature, TeamMember, Location,
)


class HeroSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroContent
        exclude = ["id"]


class AboutSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutContent
        exclude = ["id"]


class SiteSettingsSerializer(serializers.ModelSerializer):
    logo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = SiteSettings
        exclude = ["id"]


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = "__all__"


class TeamMemberSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = TeamMember
        fields = "__all__"


class LocationSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=False, allow_null=True)
    lat = serializers.DecimalField(max_digits=9, decimal_places=6, coerce_to_string=False)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6, coerce_to_string=False)

    class Meta:
        model = Location
        fields = "__all__"


class ContactSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    subject = serializers.CharField(max_length=200)
    message = serializers.CharField(max_length=5000)
    website = serializers.CharField(required=False, allow_blank=True)  # honeypot
