from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from tenancy.scoping import org_kb, org_kb_suggestions
from tickets_t.permissions import IsAdmin

from .models import Article, ArticleSuggestion
from .serializers import ArticleSerializer, ArticleSuggestionSerializer


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


class ArticleSuggestionAdminViewSet(viewsets.ModelViewSet):
    """Cola de sugerencias de KB (generadas por IA al resolver tickets, Fase 5.2).

    El admin lista las pendientes, edita título/cuerpo, y las acepta (crea un
    Article publicado) o las descarta. Scoped por org.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ArticleSuggestionSerializer
    http_method_names = ["get", "patch", "post", "head", "options"]  # sin destroy directo

    def get_queryset(self):
        qs = org_kb_suggestions(getattr(self.request, "organization", None))
        st = self.request.query_params.get("status", "pending")
        return qs.filter(status=st) if st != "all" else qs

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Crea un Article publicado con el título/cuerpo actual y marca la
        sugerencia como aceptada."""
        s = self.get_object()
        if s.status == ArticleSuggestion.Status.ACCEPTED:
            return Response({"detail": "Ya fue aceptada."}, status=status.HTTP_409_CONFLICT)
        article = Article.objects.create(
            organization=s.organization, title=s.title, body=s.body,
            is_published=True, author=request.user)
        s.status = ArticleSuggestion.Status.ACCEPTED
        s.save(update_fields=["status", "updated_at"])
        return Response({"article_id": article.id, "slug": article.slug},
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        s = self.get_object()
        s.status = ArticleSuggestion.Status.DISMISSED
        s.save(update_fields=["status", "updated_at"])
        return Response({"status": s.status})
