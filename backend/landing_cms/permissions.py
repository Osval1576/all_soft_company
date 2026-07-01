from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    message = "Solo administradores."

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if u.is_superuser:
            return True
        return getattr(u, "role", None) == "ADMIN"
