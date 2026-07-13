from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdminRole

from .models import SlaConfig, SlaPolicy, Holiday
from .serializers import SlaConfigSerializer, SlaPolicySerializer, HolidaySerializer


class ConfigView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        cfg = SlaConfig.objects.get(organization=request.organization)
        return Response(SlaConfigSerializer(cfg).data)

    def patch(self, request):
        cfg = SlaConfig.objects.get(organization=request.organization)
        ser = SlaConfigSerializer(cfg, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class PoliciesView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = SlaPolicy.objects.filter(organization=request.organization).order_by("priority")
        return Response(SlaPolicySerializer(qs, many=True).data)

    def patch(self, request):
        # request.data es una lista de {priority, first_response_minutes, resolution_minutes}
        for row in request.data:
            obj = SlaPolicy.objects.filter(
                organization=request.organization, priority=row.get("priority")).first()
            if obj is None:
                continue
            ser = SlaPolicySerializer(obj, data=row, partial=True)
            ser.is_valid(raise_exception=True)
            ser.save()
        qs = SlaPolicy.objects.filter(organization=request.organization).order_by("priority")
        return Response(SlaPolicySerializer(qs, many=True).data)


class HolidayViewSet(mixins.ListModelMixin, mixins.CreateModelMixin,
                     mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = HolidaySerializer

    def get_queryset(self):
        return Holiday.objects.filter(organization=self.request.organization)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)
