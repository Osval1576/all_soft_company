from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    HeroContent, AboutContent, SiteSettings,
    Feature, TeamMember, Location,
)
from .serializers import (
    HeroSerializer, AboutSerializer, SiteSettingsSerializer,
    FeatureSerializer, TeamMemberSerializer, LocationSerializer,
)


def _cache(resp):
    resp["Cache-Control"] = "public, max-age=60"
    return resp


class _SingletonView(APIView):
    permission_classes = [AllowAny]
    model = None
    serializer_class = None

    def get(self, request):
        obj = self.model.objects.get_solo()
        return _cache(Response(self.serializer_class(obj, context={"request": request}).data))


class HeroPublicView(_SingletonView):
    model = HeroContent
    serializer_class = HeroSerializer


class AboutPublicView(_SingletonView):
    model = AboutContent
    serializer_class = AboutSerializer


class SiteSettingsPublicView(_SingletonView):
    model = SiteSettings
    serializer_class = SiteSettingsSerializer


class _ActiveListView(generics.ListAPIView):
    permission_classes = [AllowAny]

    def get_queryset(self):
        return self.queryset_model.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        return _cache(super().list(request, *args, **kwargs))


class FeatureListView(_ActiveListView):
    queryset_model = Feature
    serializer_class = FeatureSerializer


class TeamListView(_ActiveListView):
    queryset_model = TeamMember
    serializer_class = TeamMemberSerializer


class LocationListView(_ActiveListView):
    queryset_model = Location
    serializer_class = LocationSerializer
