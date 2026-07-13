from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=12, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        self.slug = (self.slug or "").upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
