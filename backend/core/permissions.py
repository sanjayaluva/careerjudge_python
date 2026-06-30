"""Reusable base permission classes for role-based access control."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsReadOnly(BasePermission):
    """Allow only GET/HEAD/OPTIONS."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class HasModulePermission(BasePermission):
    """
    Base class for module-scoped permissions.

    Subclasses must set `module` (the module name) and may override `action_map`
    to map DRF action names to permission codenames.

    Example:
        class HasAccountsPermission(HasModulePermission):
            module = "accounts"
            action_map = {
                "list":   "view_user",
                "retrieve": "view_user",
                "create":  "add_user",
                "update":  "change_user",
                "partial_update": "change_user",
                "destroy": "delete_user",
            }
    """

    module: str = ""
    action_map: dict[str, str] = {}

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True

        action = getattr(view, "action", None) or request.method.lower()
        required = self.action_map.get(action)
        if required is None:
            return False
        return request.user.has_perm(f"{self.module}.{required}")
