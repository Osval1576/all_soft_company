from rest_framework.routers import DefaultRouter

from .admin_views import ArticleAdminViewSet, ArticleSuggestionAdminViewSet

router = DefaultRouter()
router.register("articles", ArticleAdminViewSet, basename="kb-articles")
router.register("suggestions", ArticleSuggestionAdminViewSet, basename="kb-suggestions")

urlpatterns = router.urls
