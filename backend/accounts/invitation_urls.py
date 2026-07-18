from rest_framework.routers import DefaultRouter

from .views import InvitationViewSet

router = DefaultRouter()
router.register("", InvitationViewSet, basename="invitations")
urlpatterns = router.urls
