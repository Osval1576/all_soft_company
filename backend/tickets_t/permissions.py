from rest_framework.permissions import BasePermission


def role(user):
    return getattr(user, "role", None)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and role(request.user) == "ADMIN")


class IsAgent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and role(request.user) == "AGENT")


class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and role(request.user) == "CUSTOMER")