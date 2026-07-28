from rest_framework.routers import DefaultRouter

from .admin_views import ChannelAccountAdminViewSet

router = DefaultRouter()
router.register("accounts", ChannelAccountAdminViewSet, basename="channel-accounts")

urlpatterns = router.urls
