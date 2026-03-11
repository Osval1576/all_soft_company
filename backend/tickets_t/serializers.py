from datetime import datetime
from django.db import transaction
from rest_framework import serializers
from .models import Ticket

def role(user):
    return getattr(user, "role", None)


class TicketSerializer(serializers.ModelSerializer):
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
        read_only_fields = ["id", "reference", "creado_por", "created_at"]

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