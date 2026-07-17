import re

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from tenancy.models import Organization
from .models import EmailVerificationToken, Invitation

User = get_user_model()


def _make_slug(name):
    base = re.sub(r"[^A-Za-z0-9]", "", name or "").upper()[:12] or "ORG"
    slug, i = base, 1
    while Organization.objects.filter(slug=slug).exists():
        suffix = str(i)
        slug = (base[: 12 - len(suffix)] + suffix)
        i += 1
    return slug


class RegisterSerializer(serializers.Serializer):
    org_name = serializers.CharField(max_length=120)
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con ese email.")
        return value

    def validate_org_name(self, value):
        if Organization.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una organización con ese nombre.")
        return value

    @transaction.atomic
    def create(self, data):
        org = Organization.objects.create(name=data["org_name"], slug=_make_slug(data["org_name"]))
        user = User(username=data["email"], email=data["email"],
                    first_name=data["first_name"], last_name=data.get("last_name", ""),
                    role="ADMIN", organization=org, is_active=False)
        user.set_password(data["password"])
        user.save()
        token = EmailVerificationToken.objects.create(user=user)
        return user, token
