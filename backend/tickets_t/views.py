from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Ticket, TicketMessage
from .serializers import TicketSerializer, TicketCreateSerializer, TicketMessageSerializer


def role(user):
    return getattr(user, "role", None)


class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    # DRF a veces hace asserts si no hay queryset base; mejor dejarlo definido.
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

    def get_queryset(self):
        user = self.request.user
        r = role(user)

        qs = Ticket.objects.all().order_by("-created_at")

        if r == "ADMIN":
            return qs
        if r == "AGENT":
            return qs.filter(asignado_a=user)
        # CUSTOMER (default)
        return qs.filter(creado_por=user)

    def get_serializer_class(self):
        if self.action == "create":
            return TicketCreateSerializer
        return TicketSerializer

    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        ticket = self.get_object()  # respeta get_queryset (permisos por rol)
        qs = TicketMessage.objects.filter(ticket=ticket).order_by("created_at")
        return Response(TicketMessageSerializer(qs, many=True).data)