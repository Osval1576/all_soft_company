from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from .models import Ticket
from .models import TicketMessage
from .models import TicketEvent

def role(user):
    return getattr(user, "role", None)


class TicketSerializer(serializers.ModelSerializer):
    ALLOWED_TRANSITIONS = {
        "OPEN": {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"},
        "IN_PROGRESS": {"IN_PROGRESS", "RESOLVED", "CLOSED"},
        "RESOLVED": {"RESOLVED", "CLOSED"},
        "CLOSED": {"CLOSED"},
    }

    sla = serializers.SerializerMethodField()
    csat = serializers.SerializerMethodField()
    can_rate = serializers.SerializerMethodField()

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
            "sla",
            "csat",
            "can_rate",
        ]
        read_only_fields = ["id", "reference", "creado_por", "created_at", "updated_at"]

    def get_sla(self, obj):
        ts = getattr(obj, "sla", None)
        if ts is None:
            return None
        if obj.organization_id is None:
            return None
        from sla.calendar_engine import get_calendar
        from sla.levels import compute_levels
        from django.utils import timezone
        ctx = self.context
        # Memoiza por organizacion dentro del request (evita N queries); el
        # queryset puede incluir tickets de mas de una org (p.ej. vista admin
        # global antes de que tickets_t quede scoped por org).
        cache = ctx.setdefault("sla_calendars", {}) if isinstance(ctx, dict) else {}
        cal = cache.get(obj.organization_id)
        if cal is None:
            cal = get_calendar(obj.organization)
            cache[obj.organization_id] = cal
        levels = compute_levels(ts, timezone.now(), cal)
        return {
            "first_response": {"level": levels["fr"], "due_at": ts.first_response_due_at},
            "resolution": {"level": levels["res"], "due_at": ts.resolution_due_at},
        }

    def get_csat(self, obj):
        from csat.payloads import csat_payload
        return csat_payload(obj)

    def get_can_rate(self, obj):
        from csat.eligibility import is_eligible
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        if obj.creado_por_id != request.user.id:
            return False
        if not is_eligible(obj):
            return False
        return getattr(obj, "csat", None) is None

    def validate_asignado_a(self, value):
        if value is None:
            return value
        if not (value.is_superuser or getattr(value, "role", None) == "AGENT"):
            raise serializers.ValidationError(
                "Solo se puede asignar a técnicos (rol AGENT)."
            )
        request = self.context.get("request")
        org = getattr(request, "organization", None) if request else None
        if org is None or value.organization_id != org.id:
            raise serializers.ValidationError("El técnico debe pertenecer a tu organización.")
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
        org = request.user.organization

        prefix = f"{org.slug}-" + timezone.localdate().strftime("%Y%m%d") + "-"
        last = (
            Ticket.objects.select_for_update()
            .filter(reference__startswith=prefix)
            .order_by("-reference")
            .first()
        )
        next_num = int(last.reference.split("-")[-1]) + 1 if last else 1

        validated_data["reference"] = f"{prefix}{next_num:06d}"
        validated_data["creado_por"] = request.user
        validated_data["organization"] = org
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