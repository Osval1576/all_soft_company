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
        request = self.context.get("request")
        inst = self.instance
        actor_is_admin = bool(request and getattr(request.user, "role", None) == "ADMIN")
        # Un usuario no-admin editando su propia cuenta no puede cambiar su rol ni su estado.
        if inst is not None and not actor_is_admin:
            if "role" in attrs and attrs["role"] != inst.role:
                raise serializers.ValidationError({"role": "No podés cambiar tu propio rol."})
            if "is_active" in attrs and attrs["is_active"] != inst.is_active:
                raise serializers.ValidationError({"is_active": "No podés cambiar tu estado."})
        if inst is not None and inst.role == "ADMIN":
            demoting = attrs.get("role", inst.role) != "ADMIN"
            deactivating = attrs.get("is_active", inst.is_active) is False
            if demoting or deactivating:
                others = User.objects.filter(organization=inst.organization, role="ADMIN",
                                             is_active=True).exclude(pk=inst.pk).exists()
                if not others:
                    raise serializers.ValidationError(
                        "No podés dejar la organización sin un admin activo.")
        # límite de agentes (billing): activar/convertir en agente sobre el tope
        becomes_active_agent = (
            attrs.get("role", inst.role if inst else None) == "AGENT"
            and attrs.get("is_active", inst.is_active if inst else None) is True
            and not (inst is not None and inst.role == "AGENT" and inst.is_active))
        if inst is not None and becomes_active_agent:
            from billing.services import can_add_agent
            if not can_add_agent(inst.organization):
                raise serializers.ValidationError(
                    "Alcanzaste el límite de agentes de tu plan. Mejorá el plan para sumar más.")
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