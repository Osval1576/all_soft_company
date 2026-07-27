from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from tenancy.scoping import org_kb
from tickets_t.permissions import IsAdmin

from .serializers import ArticleSerializer


class ArticleAdminViewSet(viewsets.ModelViewSet):
    """CRUD de artículos de la KB para el ADMIN del tenant.

    Scoped por org: un admin solo ve/edita los artículos de su organización;
    los de otra org ni siquiera aparecen en el queryset (404, sin fuga).
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ArticleSerializer

    def get_queryset(self):
        return org_kb(getattr(self.request, "organization", None))

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.organization,
            author=self.request.user,
        )
