import logging

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from django.http import FileResponse
from django.core.exceptions import ValidationError as DjangoValidationError
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Ticket, TicketMessage, TicketEvent
from .serializers import (
    TicketSerializer, TicketCreateSerializer, TicketMessageSerializer,
    TicketEventSerializer,
)
from .validators import validate_attachment
from .permissions import can_access_ticket
from .payloads import message_to_payload

logger = logging.getLogger(__name__)


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
        from notifications.services import notify_for_event
        notify_for_event(ticket, kind, actor, payload or {})

    def perform_create(self, serializer):
        with transaction.atomic():
            ticket = serializer.save()
            self._emit(ticket, "created", self.request.user)

    def perform_update(self, serializer):
        inst = serializer.instance
        old = {
            "estado": inst.estado,
            "asignado_a_id": inst.asignado_a_id,
            "prioridad": inst.prioridad,
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
        qs = Ticket.objects.filter(
            asignado_a__isnull=True,
            estado__in=["OPEN", "IN_PROGRESS"],
        ).order_by("-created_at")
        return Response(TicketSerializer(qs, many=True, context={"request": request}).data)

    # ---- take ----
    @action(detail=True, methods=["post"], url_path="take")
    def take(self, request, pk=None):
        user = request.user
        if not _is_agent(user):
            return Response({"detail": "Solo técnicos pueden tomar tickets."}, status=403)
        try:
            with transaction.atomic():
                ticket = Ticket.objects.select_for_update().get(pk=pk)
                if ticket.asignado_a_id and ticket.asignado_a_id != user.id:
                    return Response({"detail": "Ya asignado a otro técnico."}, status=409)
                if ticket.asignado_a_id == user.id:
                    return Response(TicketSerializer(ticket, context={"request": request}).data)
                ticket.asignado_a = user
                ticket.save(update_fields=["asignado_a"])
                self._emit(ticket, "assigned", user, {"self_take": True, "to_user_id": user.id})
        except Ticket.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=404)
        return Response(TicketSerializer(ticket, context={"request": request}).data)

    # ---- events ----
    @action(detail=True, methods=["get"], url_path="events")
    def events(self, request, pk=None):
        ticket = self.get_object()
        return Response(TicketEventSerializer(ticket.events.all(), many=True).data)

    # ---- attachments ----
    @action(detail=True, methods=["post"], url_path="attachments",
            parser_classes=[MultiPartParser, FormParser])
    def upload_attachment(self, request, pk=None):
        ticket = Ticket.objects.filter(pk=pk).first()
        if ticket is None:
            return Response({"detail": "No encontrado."}, status=404)
        if not can_access_ticket(request.user, ticket):
            return Response({"detail": "Sin acceso al ticket."}, status=403)
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "Falta el archivo."}, status=400)
        try:
            validate_attachment(file)
        except DjangoValidationError as e:
            return Response({"detail": e.messages[0]}, status=400)

        caption = (request.data.get("content") or "").strip()
        msg = TicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            content=caption,
            attachment=file,
            attachment_name=file.name[:255],
            attachment_size=file.size,
            attachment_content_type=getattr(file, "content_type", "") or "",
        )
        payload = message_to_payload(msg)

        layer = get_channel_layer()
        if layer is not None:
            try:
                async_to_sync(layer.group_send)(
                    f"ticket_{ticket.id}", {"type": "chat.message", "message": payload}
                )
            except Exception:
                logger.exception("attachment broadcast failed for ticket %s", ticket.id)

        from notifications.services import dispatch
        try:
            dispatch("new_message", ticket, actor=request.user,
                     extra={"content": caption or file.name})
        except Exception:
            logger.exception("notification dispatch failed for ticket %s", ticket.id)

        return Response(payload, status=201)

    @action(detail=True, methods=["get"],
            url_path=r"attachments/(?P<message_id>[^/.]+)/download")
    def download_attachment(self, request, pk=None, message_id=None):
        ticket = Ticket.objects.filter(pk=pk).first()
        if ticket is None:
            return Response({"detail": "No encontrado."}, status=404)
        if not can_access_ticket(request.user, ticket):
            return Response({"detail": "Sin acceso al ticket."}, status=403)
        msg = TicketMessage.objects.filter(pk=message_id, ticket=ticket).first()
        if msg is None or not msg.attachment:
            return Response({"detail": "Adjunto no encontrado."}, status=404)
        resp = FileResponse(
            msg.attachment.open("rb"),
            content_type=msg.attachment_content_type or "application/octet-stream",
        )
        resp["Content-Disposition"] = f'attachment; filename="{msg.attachment_name}"'
        return resp
