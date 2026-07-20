from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets_t.permissions import IsAdmin
from .branding_serializers import BrandingSerializer
from .branding_services import branding_enabled
from .models import OrganizationBranding


class BrandingView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        org = request.organization
        branding = getattr(org, "branding", None)
        if branding is None:
            branding = OrganizationBranding(organization=org)  # sin persistir
        ser = BrandingSerializer(branding, context={"request": request, "organization": org})
        return Response(ser.data)

    def put(self, request):
        org = request.organization
        if not branding_enabled(org):
            return Response(
                {"detail": "El branding es una función de los planes Pro y Business."},
                status=403)
        branding, _ = OrganizationBranding.objects.get_or_create(organization=org)
        ser = BrandingSerializer(branding, data=request.data, partial=True,
                                 context={"request": request, "organization": org})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)
