from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from tenancy.scoping import org_users

from .permissions import IsAdmin, IsAdminOrSelf
from .serializers import UserSerializer, UserCreateSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return org_users(self.request.organization)

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)

    def get_permissions(self):
        if self.action in ["list", "create", "destroy"]:
            return [IsAuthenticated(), IsAdmin()]
        if self.action in ["retrieve", "update", "partial_update"]:
            return [IsAuthenticated(), IsAdminOrSelf()]
        return [IsAuthenticated()]