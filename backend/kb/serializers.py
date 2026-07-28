from rest_framework import serializers

from .models import Article, ArticleSuggestion


class ArticleSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True, default=None)

    class Meta:
        model = Article
        fields = [
            "id", "title", "slug", "body", "is_published",
            "author", "author_username", "created_at", "updated_at",
        ]
        # organization/author/slug los fija el servidor; nunca vienen del cliente.
        read_only_fields = ["id", "slug", "author", "author_username",
                            "created_at", "updated_at"]


class ArticleSuggestionSerializer(serializers.ModelSerializer):
    source_ticket_ref = serializers.CharField(source="source_ticket.reference",
                                              read_only=True, default=None)

    class Meta:
        model = ArticleSuggestion
        fields = ["id", "title", "body", "status", "source_ticket", "source_ticket_ref",
                  "created_at", "updated_at"]
        # solo se puede editar title/body (para pulir antes de aceptar).
        read_only_fields = ["id", "status", "source_ticket", "source_ticket_ref",
                            "created_at", "updated_at"]
