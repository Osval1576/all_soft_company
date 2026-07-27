from rest_framework import serializers

from .models import Article


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
