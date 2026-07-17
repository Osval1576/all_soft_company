from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
        ]
        read_only_fields = ["id", "is_staff", "is_superuser", "date_joined"]

    def validate(self, attrs):
        inst = self.instance
        if inst is not None and inst.role == "ADMIN":
            demoting = attrs.get("role", inst.role) != "ADMIN"
            deactivating = attrs.get("is_active", inst.is_active) is False
            if demoting or deactivating:
                others = User.objects.filter(organization=inst.organization, role="ADMIN",
                                             is_active=True).exclude(pk=inst.pk).exists()
                if not others:
                    raise serializers.ValidationError(
                        "No podés dejar la organización sin un admin activo.")
        return attrs


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "password",
            "is_active",
            "is_staff",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user