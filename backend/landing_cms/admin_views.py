from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    HeroContent, AboutContent, SiteSettings,
    Feature, TeamMember, Location,
)
from .permissions import IsAdminRole
from .serializers import (
    HeroSerializer, AboutSerializer, SiteSettingsSerializer,
    FeatureSerializer, TeamMemberSerializer, LocationSerializer,
)


class _SingletonAdminView(APIView):
    permission_classes = [IsAdminRole]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    model = None
    serializer_class = None

    def get(self, request):
        obj = self.model.objects.get_solo()
        return Response(self.serializer_class(obj, context={"request": request}).data)

    def put(self, request):
        obj = self.model.objects.get_solo()
        ser = self.serializer_class(obj, data=request.data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class HeroAdminView(_SingletonAdminView):
    model = HeroContent
    serializer_class = HeroSerializer


class AboutAdminView(_SingletonAdminView):
    model = AboutContent
    serializer_class = AboutSerializer


class SiteSettingsAdminView(_SingletonAdminView):
    model = SiteSettings
    serializer_class = SiteSettingsSerializer


class _OrderedAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @action(detail=False, methods=["post"])
    def reorder(self, request):
        ids = request.data.get("ids", [])
        if not isinstance(ids, list):
            return Response({"detail": "ids must be a list"}, status=400)
        for idx, pk in enumerate(ids):
            self.queryset.filter(pk=pk).update(order=idx)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FeatureAdminViewSet(_OrderedAdminViewSet):
    queryset = Feature.objects.all()
    serializer_class = FeatureSerializer


class TeamAdminViewSet(_OrderedAdminViewSet):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer


class LocationAdminViewSet(_OrderedAdminViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
