from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet, NotificationPreferenceView

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notifications")

# La ruta de preferences va ANTES del router para que no matchee como detail pk.
urlpatterns = [
    path("notifications/preferences/", NotificationPreferenceView.as_view()),
] + router.urls
