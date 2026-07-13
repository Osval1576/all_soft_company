from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'

    def ready(self):
        from config import checks  # noqa: F401  registra los system checks de prod
