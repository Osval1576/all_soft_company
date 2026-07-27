from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "ADMIN"
        )


class IsAdminOrSelf(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        return getattr(request.user, "role", None) == "ADMIN" or obj.id == request.user.id


class IsAdminRole(BasePermission):
    message = "Solo administradores."

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return bool(u.is_superuser or getattr(u, "role", None) == "ADMIN")


class IsPlatformStaff(BasePermission):
    """Solo staff de plataforma (superuser / is_staff).

    Para recursos GLOBALES que no pertenecen a ningún tenant (p.ej. el CMS del
    sitio público). El rol ADMIN es de tenant: un admin de una organización NO
    debe poder editar contenido compartido por todos los tenants (CN-001).
    """
    message = "Solo staff de la plataforma."

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return bool(u.is_superuser or u.is_staff)