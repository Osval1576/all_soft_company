from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Ticket
from .serializers import TicketSerializer, TicketCreateSerializer

def role(user):
    return getattr(user, "role", None)

class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        r = role(user)

        if r == "ADMIN":
            return Ticket.objects.all().order_by("-created_at")
        if r == "AGENT":
            return Ticket.objects.filter(asignado_a=user).order_by("-created_at")
        return Ticket.objects.filter(creado_por=user).order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return TicketCreateSerializer
        return TicketSerializer