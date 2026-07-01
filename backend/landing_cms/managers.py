from django.db import models


class SingletonManager(models.Manager):
    def get_solo(self):
        obj, _ = self.get_or_create(pk=1)
        return obj
