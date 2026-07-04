from datetime import datetime
from django.db import transaction
from rest_framework import serializers
from .models import Ticket
from .models import TicketMessage
from .models import TicketEvent
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

def role(user):
    return getattr(user, "role", None)


class TicketSerializer(serializers.ModelSerializer):
    ALLOWED_TRANSITIONS = {
        "OPEN": {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"},
        "IN_PROGRESS": {"IN_PROGRESS", "RESOLVED", "CLOSED"},
        "RESOLVED": {"RESOLVED", "CLOSED"},
        "CLOSED": {"CLOSED"},
    }

    class Meta:
        model = Ticket
        fields = [
            "id",
            "reference",
            "titulo",
            "descripcion",
            "prioridad",
            "estado",
            "creado_por",
            "asignado_a",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "reference", "creado_por", "created_at", "updated_at"]

    def validate_asignado_a(self, value):
        if value is None:
            return value
        if not (value.is_superuser or getattr(value, "role", None) == "AGENT"):
            raise serializers.ValidationError(
                "Solo se puede asignar a técnicos (rol AGENT)."
            )
        return value

    def validate_estado(self, value):
        if not self.instance:
            return value
        current = self.instance.estado
        if current == value:
            return value
        request = self.context.get("request")
        is_admin = bool(
            request
            and request.user.is_authenticated
            and (request.user.is_superuser or getattr(request.user, "role", None) == "ADMIN")
        )
        if is_admin and current in ("RESOLVED", "CLOSED") and value == "OPEN":
            return value
        allowed = self.ALLOWED_TRANSITIONS.get(current, {value})
        if value not in allowed:
            raise serializers.ValidationError(
                f"Transición no permitida: {current} → {value}."
            )
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if not request:
            return attrs

        r = role(request.user)

        # Nadie puede cambiar creado_por/reference desde API
        attrs.pop("creado_por", None)
        attrs.pop("reference", None)

        if r == "CUSTOMER":
            # Customer no puede asignar
            if "asignado_a" in attrs:
                raise serializers.ValidationError({"asignado_a": "No permitido."})
            # Customer no puede cerrar/resolver
            if "estado" in attrs and attrs["estado"] in ["RESOLVED", "CLOSED"]:
                raise serializers.ValidationError({"estado": "No permitido para CUSTOMER."})

        if r == "AGENT":
            # Agent no reasigna
            if "asignado_a" in attrs:
                raise serializers.ValidationError({"asignado_a": "No permitido para AGENT."})

        return attrs


class TicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = [
            "id",
            "reference",
            "titulo",
            "descripcion",
            "prioridad",
            "estado",
            "creado_por",
            "asignado_a",
            "created_at",
        ]
        read_only_fields = ["id", "reference", "creado_por", "created_at", "estado", "asignado_a"]

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]

        prefix = "ALS-" + datetime.utcnow().strftime("%Y%m%d") + "-"
        last = (
            Ticket.objects.select_for_update()
            .filter(reference__startswith=prefix)
            .order_by("-reference")
            .first()
        )
        next_num = int(last.reference.split("-")[-1]) + 1 if last else 1

        validated_data["reference"] = f"{prefix}{next_num:06d}"
        validated_data["creado_por"] = request.user
        return super().create(validated_data)
    



class TicketMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)
    sender_role = serializers.CharField(source="sender.role", read_only=True)
    attachment = serializers.SerializerMethodField()

    class Meta:
        model = TicketMessage
        fields = [
            "id", "ticket", "sender", "sender_username", "sender_role",
            "content", "created_at", "attachment",
        ]
        read_only_fields = [
            "id", "ticket", "sender", "sender_username", "sender_role",
            "created_at", "attachment",
        ]

    def get_attachment(self, obj):
        from .payloads import attachment_payload
        return attachment_payload(obj)


class TicketEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True, default=None)

    class Meta:
        model = TicketEvent
        fields = ["id", "kind", "actor", "actor_username", "payload", "created_at"]