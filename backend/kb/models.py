from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Article(models.Model):
    """Artículo de la base de conocimiento de un tenant (Fase 3A).

    Scoped por organización: cada org administra su propia KB. El slug se deriva
    del título y es único dentro de la org (sirve para la URL pública/SEO y, más
    adelante, como fuente del agente de deflección RAG de la Fase 3B).
    """
    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.CASCADE,
        related_name="kb_articles",
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, blank=True)
    body = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="kb_articles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"], name="uniq_kb_slug_per_org"),
        ]
        indexes = [models.Index(fields=["organization", "is_published"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "articulo"
            slug = base
            n = 2
            qs = Article.objects.filter(organization=self.organization)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            while qs.filter(slug=slug).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.organization_id}] {self.title}"


class ArticleSuggestion(models.Model):
    """Sugerencia de artículo de KB generada por IA a partir de un ticket resuelto
    (Fase 5.2, KB auto-alimentada). El admin la revisa/edita y la acepta (crea un
    Article publicado) o la descarta. Cierra el loop 3A↔3B: la KB crece sola."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        ACCEPTED = "accepted", "Aceptada"
        DISMISSED = "dismissed", "Descartada"

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="kb_suggestions")
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    source_ticket = models.ForeignKey(
        "tickets_t.Ticket", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="kb_suggestions")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "status"])]

    def __str__(self):
        return f"[{self.organization_id}] sugerencia: {self.title[:40]}"
