from rest_framework.routers import DefaultRouter
from .views import TicketViewSet

router = DefaultRouter()
router.register("tickets_t", TicketViewSet, basename="tickets_t")  # si quieres mantener ese path
urlpatterns = router.urls