from rest_framework import mixins, viewsets
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SlaConfig, SlaPolicy, Holiday
from .serializers import SlaConfigSerializer, SlaPolicySerializer, HolidaySerializer


class IsAdminRole(BasePermission):
    message = "Solo administradores."

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return bool(u.is_superuser or getattr(u, "role", None) == "ADMIN")


class ConfigView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(SlaConfigSerializer(SlaConfig.objects.get_solo()).data)

    def patch(self, request):
        cfg = SlaConfig.objects.get_solo()
        ser = SlaConfigSerializer(cfg, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class PoliciesView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(SlaPolicySerializer(SlaPolicy.objects.all().order_by("priority"), many=True).data)

    def patch(self, request):
        # request.data es una lista de {priority, first_response_minutes, resolution_minutes}
        for row in request.data:
            obj = SlaPolicy.objects.filter(priority=row.get("priority")).first()
            if obj is None:
                continue
            ser = SlaPolicySerializer(obj, data=row, partial=True)
            ser.is_valid(raise_exception=True)
            ser.save()
        return Response(SlaPolicySerializer(SlaPolicy.objects.all().order_by("priority"), many=True).data)


class HolidayViewSet(mixins.ListModelMixin, mixins.CreateModelMixin,
                     mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminRole]
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
