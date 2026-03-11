from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .permissions import IsAdmin, IsAdminOrSelf
from .serializers import UserSerializer, UserCreateSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ["list", "create", "destroy"]:
            return [IsAuthenticated(), IsAdmin()]
        if self.action in ["retrieve", "update", "partial_update"]:
            return [IsAuthenticated(), IsAdminOrSelf()]
        return [IsAuthenticated()]