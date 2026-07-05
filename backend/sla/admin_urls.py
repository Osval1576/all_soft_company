from django.urls import path
from rest_framework.routers import DefaultRouter
from . import admin_views as v

router = DefaultRouter()
router.register("holidays", v.HolidayViewSet, basename="sla-holidays")

urlpatterns = [
    path("config/", v.ConfigView.as_view()),
    path("policies/", v.PoliciesView.as_view()),
] + router.urls
