from django.urls import path
from rest_framework.routers import DefaultRouter
from . import admin_views as v

router = DefaultRouter()
router.register("features", v.FeatureAdminViewSet, basename="adm-features")
router.register("team", v.TeamAdminViewSet, basename="adm-team")
router.register("locations", v.LocationAdminViewSet, basename="adm-locations")

urlpatterns = [
    path("hero/", v.HeroAdminView.as_view()),
    path("about/", v.AboutAdminView.as_view()),
] + router.urls
