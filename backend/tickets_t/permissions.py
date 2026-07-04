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


def can_access_ticket(user, ticket):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    r = getattr(user, "role", None)
    if r == "ADMIN" or user.is_superuser:
        return True
    if r == "CUSTOMER":
        return ticket.creado_por_id == user.id
    if r == "AGENT":
        return ticket.asignado_a_id == user.id
    return False