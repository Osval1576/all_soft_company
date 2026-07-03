from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction

from .models import Ticket, TicketMessage, TicketEvent
from .serializers import (
    TicketSerializer, TicketCreateSerializer, TicketMessageSerializer,
    TicketEventSerializer,
)


def _role(user):
    return getattr(user, "role", None)


def _is_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or _role(user) == "ADMIN"))


def _is_agent(user):
    return bool(user and user.is_authenticated and (_role(user) == "AGENT" or user.is_superuser))


class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

    def get_queryset(self):
        user = self.request.user
        r = _role(user)
        qs = Ticket.objects.all().order_by("-created_at")
        if r == "ADMIN" or user.is_superuser:
            return qs
        if r == "AGENT":
            return qs.filter(asignado_a=user)
        return qs.filter(creado_por=user)

    def get_serializer_class(self):
        if self.action == "create":
            return TicketCreateSerializer
        return TicketSerializer

    # ---- event emission helpers ----
    def _emit(self, ticket, kind, actor, payload=None):
        TicketEvent.objects.create(ticket=ticket, kind=kind, actor=actor, payload=payload or {})

    def perform_create(self, serializer):
        with transaction.atomic():
            ticket = serializer.save()
            self._emit(ticket, "created", self.request.user)

    def perform_update(self, serializer):
        instance_before = self.get_object()
        old = {
            "estado": instance_before.estado,
            "asignado_a_id": instance_before.asignado_a_id,
            "prioridad": instance_before.prioridad,
        }
        with transaction.atomic():
            ticket = serializer.save()
            actor = self.request.user
            new = {
                "estado": ticket.estado,
                "asignado_a_id": ticket.asignado_a_id,
                "prioridad": ticket.prioridad,
            }
            if old["estado"] != new["estado"]:
                kind = "reopened" if (old["estado"] in ("RESOLVED", "CLOSED") and new["estado"] == "OPEN") else "status_changed"
                self._emit(ticket, kind, actor, {"from": old["estado"], "to": new["estado"]})
            if old["asignado_a_id"] != new["asignado_a_id"]:
                if new["asignado_a_id"] is None:
                    self._emit(ticket, "unassigned", actor, {"from_user_id": old["asignado_a_id"]})
                else:
                    self._emit(ticket, "assigned", actor, {"to_user_id": new["asignado_a_id"]})
            if old["prioridad"] != new["prioridad"]:
                self._emit(ticket, "priority_changed", actor, {"from": old["prioridad"], "to": new["prioridad"]})

    # ---- messages (existing) ----
    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        ticket = self.get_object()
        qs = TicketMessage.objects.filter(ticket=ticket).order_by("created_at")
        return Response(TicketMessageSerializer(qs, many=True).data)

    # ---- pool ----
    @action(detail=False, methods=["get"], url_path="pool")
    def pool(self, request):
        user = request.user
        if not (_is_admin(user) or _is_agent(user)):
            return Response({"detail": "Solo técnicos o admin."}, status=403)
        qs = Ticket.objects.filter(asignado_a__isnull=True).order_by("-created_at")
        return Response(TicketSerializer(qs, many=True, context={"request": request}).data)

    # ---- take ----
    @action(detail=True, methods=["post"], url_path="take")
    def take(self, request, pk=None):
        user = request.user
        if not _is_agent(user):
            return Response({"detail": "Solo técnicos pueden tomar tickets."}, status=403)
        try:
            ticket = Ticket.objects.get(pk=pk)
        except Ticket.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=404)
        if ticket.asignado_a_id and ticket.asignado_a_id != user.id:
            return Response({"detail": "Ya asignado a otro técnico."}, status=409)
        if ticket.asignado_a_id == user.id:
            return Response(TicketSerializer(ticket, context={"request": request}).data)
        with transaction.atomic():
            ticket.asignado_a = user
            ticket.save(update_fields=["asignado_a"])
            self._emit(ticket, "assigned", user, {"self_take": True, "to_user_id": user.id})
        return Response(TicketSerializer(ticket, context={"request": request}).data)

    # ---- events ----
    @action(detail=True, methods=["get"], url_path="events")
    def events(self, request, pk=None):
        ticket = self.get_object()
        return Response(TicketEventSerializer(ticket.events.all(), many=True).data)
