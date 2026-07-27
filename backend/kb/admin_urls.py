from rest_framework.routers import DefaultRouter

from .admin_views import ArticleAdminViewSet

router = DefaultRouter()
router.register("articles", ArticleAdminViewSet, basename="kb-articles")

urlpatterns = router.urls
