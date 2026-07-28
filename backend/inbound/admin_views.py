from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from tenancy.scoping import org_channel_accounts
from tickets_t.permissions import IsAdmin

from .serializers import ChannelAccountSerializer


class ChannelAccountAdminViewSet(viewsets.ModelViewSet):
    """CRUD de cuentas de canal (p. ej. el número de WhatsApp del tenant) para el
    ADMIN de la organización. Scoped por org: un admin solo ve/edita las suyas."""
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ChannelAccountSerializer

    def get_queryset(self):
        return org_channel_accounts(getattr(self.request, "organization", None))

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)
